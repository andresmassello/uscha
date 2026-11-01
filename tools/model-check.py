#!/usr/bin/env python3
"""Model-checked designs (ADR-059): the repo-level check and the CI runner.

  python tools/model-check.py check [--root DIR]
      No Java. Every ADR numbered >= 059 declares `model:` in its frontmatter; a `required` one
      points at a well-formed `models.json`; every manifest has a `ci` config and a vacuity config,
      and every AC id a config replays exists in ACCEPTANCE.md and in the smoke suite. A deep run
      recorded against an older `.tla` is an ADVISORY warning. Exit 0 clean, 1 findings.

  python tools/model-check.py run --tier ci --jar tla2tools.jar [--root DIR]
      Runs every config of that tier with TLC and compares each verdict with the manifest's
      `expect`. The jar must match the pinned sha256 before anything runs. A config over the
      measured limit (60 s) or past the timeout (120 s) is red, naming it. Exit 0 / 1.
      `--tlc-cmd "<command>"` replaces java+jar (the suite drives the logic with a stub).

What a green model proves: TLC found no violation OF THE MODEL at its declared bounds. It does not
prove the engine matches the model -- the RED cases each config `replays` are the only link.
Repo-level: this file is not shipped in the kit package.
"""
import argparse
import glob
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time

TLC_VERSION = "1.7.4"
TLC_URL = ("https://github.com/tlaplus/tlaplus/releases/download/v%s/tla2tools.jar"
           % TLC_VERSION)
TLC_SHA256 = "936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88"
FIRST_GATED_ADR = 59             # ADR-059: ADRs 001-058 are not retrofitted (stated boundary)
LIMIT_S = 60                     # measured budget per `ci` config
TIMEOUT_S = 120                  # hard stop per config
SCHEMA = "uscha/models@1"
EXPECT_RX = re.compile(r"^(no-error|violated:\s*([A-Za-z_][A-Za-z0-9_]*))$")
VIOLATED_RX = re.compile(r"Invariant\s+([A-Za-z_][A-Za-z0-9_]*)\s+is violated")
ADR_RX = re.compile(r"ADR-(\d{3})-[^/\\]*\.md$")


def rel(root, p):
    return os.path.relpath(p, root).replace(os.sep, "/")


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def frontmatter(path):
    """The `key: value` lines of a leading `---` block (top-level keys only)."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().split("\n")
    if not lines or lines[0].strip() != "---":
        return None
    out = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return out
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$", line)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return None


def load_manifest(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh), None
    except (OSError, ValueError) as exc:
        return None, str(exc)


def manifests(root):
    return sorted(glob.glob(os.path.join(root, "docs", "**", "models", "models.json"),
                            recursive=True))


def check_manifest(root, path, acceptance, smoke, findings, advisories):
    """Findings for one manifest; returns the manifest (or None)."""
    m, err = load_manifest(path)
    where = rel(root, path)
    if m is None:
        findings.append("%s: unreadable manifest (%s)" % (where, err))
        return None
    if m.get("schema") != SCHEMA:
        findings.append("%s: schema is %r, expected %r" % (where, m.get("schema"), SCHEMA))
    base = os.path.dirname(path)
    module = m.get("module")
    mod_path = os.path.join(base, module) if isinstance(module, str) else None
    if not mod_path or not os.path.isfile(mod_path):
        findings.append("%s: module %r does not exist" % (where, module))
    configs = m.get("configs") if isinstance(m.get("configs"), list) else []
    if not configs:
        findings.append("%s: no configs" % where)
    has_ci = has_vacuity = False
    for c in configs:
        cfg = c.get("cfg") if isinstance(c, dict) else None
        tag = "%s: %s" % (where, cfg)
        if not isinstance(cfg, str) or not os.path.isfile(os.path.join(base, cfg)):
            findings.append("%s: the .cfg does not exist" % tag)
            continue
        tier, expect = c.get("tier"), c.get("expect")
        if tier not in ("ci", "deep"):
            findings.append("%s: tier is %r, expected ci or deep" % (tag, tier))
        if not isinstance(expect, str) or not EXPECT_RX.match(expect.strip()):
            findings.append("%s: expect is %r, expected no-error or violated: <Invariant>"
                            % (tag, expect))
        if tier == "ci":
            has_ci = True
            if c.get("vacuity") and isinstance(expect, str) and expect.startswith("violated"):
                has_vacuity = True
        if c.get("vacuity") and not (isinstance(expect, str) and expect.startswith("violated")):
            findings.append("%s: a vacuity config must expect a violation -- a vacuity "
                            "control that cannot break proves nothing" % tag)
        for ac in c.get("replays") or []:
            if not re.search(r"(?<![A-Z0-9-])" + re.escape(ac) + r"(?![0-9])", acceptance):
                findings.append("%s: replays %s, which is not in ACCEPTANCE.md" % (tag, ac))
            if ac not in smoke:
                findings.append("%s: replays %s, which the smoke suite does not measure"
                                % (tag, ac))
        if tier == "deep" and mod_path and os.path.isfile(mod_path):
            meas = c.get("measured") or {}
            if meas.get("model_sha256") != sha256_file(mod_path):
                advisories.append("%s: the recorded deep run predates the current %s -- run it "
                                  "again by hand and record the result" % (tag, module))
    if configs and not has_ci:
        findings.append("%s: no `ci` config -- nothing would run in CI" % where)
    if configs and not has_vacuity:
        findings.append("%s: no `ci` vacuity config (an invariant that MUST break) -- a green "
                        "could be green because nothing can happen" % where)
    return m


def cmd_check(args):
    root = os.path.realpath(args.root)
    findings, advisories = [], []
    acc_path = os.path.join(root, "ACCEPTANCE.md")
    smoke_path = os.path.join(root, "uscha-kit", "tests", "smoke-engine.sh")
    acceptance = open(acc_path, encoding="utf-8").read() if os.path.isfile(acc_path) else ""
    smoke = open(smoke_path, encoding="utf-8").read() if os.path.isfile(smoke_path) else ""
    checked = {}
    for path in manifests(root):
        checked[os.path.realpath(path)] = check_manifest(root, path, acceptance, smoke,
                                                         findings, advisories)
    n_adr = 0
    for path in sorted(glob.glob(os.path.join(root, "docs", "adr", "ADR-*.md"))):
        m = ADR_RX.search(path)
        if not m or int(m.group(1)) < FIRST_GATED_ADR:
            continue
        n_adr += 1
        adr = "ADR-" + m.group(1)
        fm = frontmatter(path)
        value = (fm or {}).get("model")
        if not value:
            findings.append("%s: no `model:` in its frontmatter -- declare `model: required` "
                            "(with `model_manifest:`) or `model: not-needed -- <reason>` "
                            "(repo rule 12, ADR-059)" % rel(root, path))
            continue
        if value.startswith("required"):
            mpath = (fm or {}).get("model_manifest")
            if not mpath:
                findings.append("%s: `model: required` without `model_manifest:`"
                                % rel(root, path))
                continue
            full = os.path.realpath(os.path.join(root, mpath))
            if not os.path.isfile(full):
                findings.append("%s: model_manifest %s does not exist" % (rel(root, path), mpath))
                continue
            man = checked.get(full)
            if man is None and full not in checked:
                man = check_manifest(root, full, acceptance, smoke, findings, advisories)
            if man is not None and man.get("adr") != adr:
                findings.append("%s: its manifest names %r, not %s"
                                % (rel(root, path), man.get("adr"), adr))
        elif value.startswith("not-needed"):
            reason = re.sub(r"\(origin:[^)]*\)", "", value[len("not-needed"):])
            if not re.search(r"[A-Za-z0-9]", reason):
                findings.append("%s: `model: not-needed` without a reason" % rel(root, path))
        else:
            findings.append("%s: `model:` is %r -- expected required or not-needed"
                            % (rel(root, path), value))
    for a in advisories:
        print("MODEL-CHECK advisory: " + a)
    for f in findings:
        print("MODEL-CHECK: " + f)
    print("MODEL-CHECK: %d manifest(s), %d ADR(s) >= %03d checked, %d finding(s), %d advisory"
          % (len(checked), n_adr, FIRST_GATED_ADR, len(findings), len(advisories)))
    return 1 if findings else 0


def verdict_of(output):
    m = VIOLATED_RX.search(output)
    if m:
        return "violated: " + m.group(1)
    if "No error has been found" in output:
        return "no-error"
    return "tlc-error"


def trace_head(output, n=15):
    lines = output.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("Error:") or "is violated" in line:
            return lines[i:i + n]
    return lines[-n:]


def cmd_run(args):
    root = os.path.realpath(args.root)
    if args.tlc_cmd:
        base_cmd = shlex.split(args.tlc_cmd)
    else:
        if not args.jar or not os.path.isfile(args.jar):
            print("MODEL-CHECK: no tla2tools.jar at %r -- download v%s from %s"
                  % (args.jar, TLC_VERSION, TLC_URL))
            return 1
        got = sha256_file(args.jar)
        if got != TLC_SHA256:
            print("MODEL-CHECK: %s has sha256 %s, the pin is %s (TLC v%s) -- refusing to run "
                  "an unverified model checker" % (args.jar, got, TLC_SHA256, TLC_VERSION))
            return 1
        base_cmd = [args.java, "-XX:+UseParallelGC", "-cp", os.path.realpath(args.jar),
                    "tlc2.TLC", "-workers", "auto"]
    red, ran = [], 0
    for path in manifests(root):
        m, err = load_manifest(path)
        if m is None:
            red.append("%s: unreadable manifest (%s)" % (rel(root, path), err))
            continue
        base = os.path.dirname(path)
        for c in m.get("configs") or []:
            if c.get("tier") != args.tier:
                continue
            ran += 1
            tag = "%s: %s" % (rel(root, path), c.get("cfg"))
            meta = tempfile.mkdtemp(prefix="uscha-tlc-")
            cmd = base_cmd + ["-config", c["cfg"]] + (
                [] if args.tlc_cmd else ["-metadir", meta]) + [m.get("module", "")]
            t0 = time.time()
            try:
                r = subprocess.run(cmd, cwd=base, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                                   errors="replace", timeout=args.timeout)
                out, timed_out = r.stdout, False
            except subprocess.TimeoutExpired as exc:
                out = exc.stdout or ""
                if isinstance(out, bytes):
                    out = out.decode("utf-8", "replace")
                timed_out = True
            except OSError as exc:
                red.append("%s: TLC could not start (%s)" % (tag, exc))
                continue
            finally:
                elapsed = time.time() - t0
            if timed_out:
                red.append("%s: past the %ds timeout -- tighten the bounds or mark it deep"
                           % (tag, args.timeout))
                continue
            got, want = verdict_of(out), c.get("expect", "").strip()
            line = "%s: %s in %.1fs" % (tag, got, elapsed)
            if got != want:
                red.append("%s, expected %s\n    %s" % (line, want,
                                                       "\n    ".join(trace_head(out))))
            elif args.tier == "ci" and elapsed > args.limit:
                red.append("%s -- over the %ds measured limit: tighten the bounds or mark it "
                           "deep" % (line, args.limit))
            else:
                print("MODEL-CHECK ok   " + line)
    for r_ in red:
        print("MODEL-CHECK FAIL " + r_)
    print("MODEL-CHECK: %d %s config(s) run, %d red" % (ran, args.tier, len(red)))
    if ran == 0:
        print("MODEL-CHECK: nothing ran -- no %s config in any manifest is not a pass"
              % args.tier)
        return 1
    return 1 if red else 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    pc = sub.add_parser("check")
    pc.add_argument("--root", default=".")
    pr = sub.add_parser("run")
    pr.add_argument("--root", default=".")
    pr.add_argument("--tier", choices=("ci", "deep"), default="ci")
    pr.add_argument("--jar", default=None)
    pr.add_argument("--java", default="java")
    pr.add_argument("--tlc-cmd", default=None)
    pr.add_argument("--timeout", type=int, default=TIMEOUT_S)
    pr.add_argument("--limit", type=int, default=LIMIT_S)
    args = p.parse_args(argv)
    return cmd_check(args) if args.cmd == "check" else cmd_run(args)


if __name__ == "__main__":
    sys.exit(main())
