#!/usr/bin/env python3
"""The uscha release ritual, as a program that refuses (ADR-041).

Repo rule 9 used to be ~20 manual steps and eight ordering invariants written as prose, with the
most dangerous one -- never amend X after the record -- in capitals because it had been hit. Prose
a human re-reads between two 14-minute suite runs is not an instrument. This is.

    python tools/release.py 1.96.0 --message-file msg.txt --tag

Six steps. Every refusal names the invariant it protects and exits non-zero:

    I1  the branch is ahead of origin/main only, with no merge in progress and no
        unmerged paths -- X can be a fast-forward, so nothing has to be rebased first
    I2  the human wrote uscha-kit/CHANGELOG-<X.Y.Z>.md, it still carries the placeholder line,
        and v<X.Y.Z> is not already tagged
    I3  the six version surfaces move together (exactly one hit per file), SYSTEM-FACTS.json is
        regenerated, `facts --write` rewrites every RECOGNISED published claim to the derived
        fact, and the `facts --check` that follows is green -- a claim the writer cannot express
        is still a refusal, because I3 was never about being able to fix a claim
    I4  the suite runs at X with no source-relevant path dirty, and a non-zero exit is a refusal
    I5  the evidence is recorded AFTER X, and X's identity has not moved since (the amend trap)
    I6  X+1 carries evidence only: no source-relevant path in its staged set
    I7  check-terminado prints SEALED at X+1
    I8  the tag is created only on X+1, right after the push; publish.yml waits for the tag's
        own six-cell smoke run and refuses on red, so a red tag is a wait, never a publish
        (--wait-ci also polls the branch push's run before tagging: opt-in, off by default)

X is the CODE commit: the working tree as the human left it -- the feature, the docs, the
changelog prose -- PLUS the six version surfaces and the regenerated `SYSTEM-FACTS.json`, staged
with `git add -A` and committed together. The script does not ask for a pre-made commit and does
not make a bump-only one; it prints the staged list in the plan so the human sees exactly what X
will carry before it exists.

What this program does NOT do, on purpose: it does not write the changelog prose, it does not
invent a claim the fact table cannot derive (since 1.97.0 it rewrites the RECOGNISED ones with
`facts --write` and still refuses on whatever is left), and it does not create the GitHub release.
The human writes, the human approves; the script enforces the order.

Repo-level and NEVER shipped: `package.json` `files` carries `bin/`, `uscha-kit/`, `README.md` and
`LICENSE`, not `tools/`. A bug here can cost a release; it cannot reach an installed kit.

Stdlib only, Python 3.8+, Windows/Linux/macOS.
"""

import argparse
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import time

# A dry run must write NOTHING, and importing the engine by path (`src_relevant`) would drop a
# __pycache__ beside it. Bytecode caching buys nothing for one import per process.
sys.dont_write_bytecode = True

REPO = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
ENGINE = os.path.join(REPO, "uscha-kit", ".claude", "skills", "uscha-devloop", "qa_ledger.py")
STATE = os.path.join(REPO, ".uscha-release-state.json")
GATED_LIST = os.path.join(REPO, "tools", "facts-gated-files.txt")
FACTS_OUT = "SYSTEM-FACTS.json"

# The line the human leaves in the changelog for step 5 to fill. Its presence is the receipt that
# the prose was written BEFORE the numbers existed -- a changelog whose counts were typed by hand
# is a claim, not a measurement.
PLACEHOLDER = "Suite: __SUITE__ checks · 0 fail; acceptance __ACC__."
COUNTS = "Suite: %d checks · %d fail; acceptance %s."
LEDGER_MSG = ("chore(ledger): %s ritual -- snapshot + readiness recorded after the code commit, "
              "suite counts in the changelog")

# The SIX version surfaces (repo rule 6). The root uscha.config.json is deliberately NOT here:
# its `version` field was a seventh surface read only by a cosmetic doctor line, and it was
# dropped in 1.96.0 rather than kept in step with five files it had nothing to do with.
SURFACES = (
    os.path.join("uscha-kit", "VERSION"),
    os.path.join("uscha-kit", "uscha.config.json"),
    os.path.join("uscha-kit", ".claude-plugin", "plugin.json"),
    os.path.join("uscha-kit", ".codex-plugin", "plugin.json"),
    os.path.join(".claude-plugin", "marketplace.json"),
    "package.json",
)

SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
RESULTADO = re.compile(r"^RESULTADO:\s*(\d+)\s+ok\s*.\s*(\d+)\s+fail", re.M)
ACCEPTANCE = re.compile(r"^ACCEPTANCE:\s*(\d+/\d+)", re.M)


class Refused(Exception):
    """A named invariant said no."""

    def __init__(self, inv, message):
        Exception.__init__(self, message)
        self.inv = inv


def refuse(inv, message):
    raise Refused(inv, message)


# --------------------------------------------------------------------------- #
# plumbing
# --------------------------------------------------------------------------- #
def run(argv, cwd=None, env=None):
    """One child process, captured, from a LIST -- no shell, so nothing here can be word-split
    or glob-expanded. The one exception in this file is the suite command in step 4, which is a
    command line the human supplied and is run with shell=True on purpose."""
    merged = None
    if env:
        merged = dict(os.environ)
        merged.update(env)
    return subprocess.run(argv, cwd=cwd or REPO, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                          errors="replace", env=merged)


def git(*argv):
    """git, with stderr kept SEPARATE from stdout.

    `run()` merges the two so a failing suite or engine prints readably. git must not: it writes
    advice and warnings to stderr -- "LF will be replaced by CRLF the next time Git touches it"
    is the one that bit -- and a merged stream feeds those lines straight into `porcelain()` and
    `staged_paths()`, where a WARNING becomes a phantom path. That turned one dirty file into a
    refusal for an "unmerged path" whose name was an English sentence (caught by T151's
    AC-RL-01 negative arm, which asserts a dirty tracked file passes preflight)."""
    try:
        return subprocess.run(["git"] + list(argv), cwd=REPO, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, text=True, encoding="utf-8",
                              errors="replace")
    except OSError as exc:
        refuse("git failure", "git %s could not run: %s" % (" ".join(argv), exc))


def git_msg(r):
    """Everything git said, for a message a human reads -- stdout and stderr, in that order."""
    return ((r.stdout or "") + (r.stderr or "")).strip()


def git_out(*argv):
    r = git(*argv)
    return r.stdout.strip() if r.returncode == 0 else ""


def git_lines(*argv):
    """git output split into lines with NO whitespace stripped off the blob.

    `git_out` strips, and `git status --porcelain` puts the status in the first two COLUMNS:
    stripping the blob eats the leading space of the FIRST line only, so `line[3:]` then
    returned `claude-plugin/marketplace.json` for ` M .claude-plugin/marketplace.json` -- one
    mangled path per report, always the first, and a refusal that names a path which does not
    exist is worse than one that names none."""
    r = git(*argv)
    return r.stdout.splitlines() if r.returncode == 0 else []


def read(path):
    # newline="" on BOTH sides: universal-newline translation would silently rewrite a CRLF
    # file to LF on a targeted one-token replace, and a version bump that also re-writes every
    # line ending is not a targeted replace.
    with io.open(path, encoding="utf-8", newline="") as fh:
        return fh.read()


def write(path, body):
    with io.open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(body)


def say(*parts):
    print(" ".join(str(p) for p in parts))
    sys.stdout.flush()


def load_state():
    try:
        return json.loads(read(STATE))
    except (OSError, ValueError):
        return {}


def save_state(state):
    write(STATE, json.dumps(state, indent=2, sort_keys=True) + "\n")


def head_identity():
    """The pair that makes an amend detectable: the sha AND the committer date. An amend keeps
    neither, so either half moving is the same refusal -- and recording both says which."""
    line = git_out("log", "-1", "--format=%H %cI", "HEAD")
    parts = line.split()
    return (parts[0], parts[1]) if len(parts) == 2 else (None, None)


def unquote(part):
    """One path as git names it. `-c core.quotepath=false` keeps non-ASCII literal, but a path
    with a space, a quote or a control character still comes back C-quoted; the quotes are
    stripped and any escape inside is left as-is. That can only fail to MATCH, which withholds a
    pass -- never grants one."""
    part = part.strip()
    if len(part) >= 2 and part[0] == '"' and part[-1] == '"':
        part = part[1:-1]
    return part.replace("\\", "/")


def porcelain():
    """Every path git reports as dirty, rename destinations included."""
    out = []
    for line in git_lines("-c", "core.quotepath=false", "status", "--porcelain", "-uall"):
        if len(line) < 4:
            continue
        for part in line[3:].split(" -> "):
            path = unquote(part)
            if path:
                out.append(path)
    return out


def staged_paths():
    return [q for q in (unquote(p) for p in
                        git_lines("-c", "core.quotepath=false", "diff", "--cached",
                                  "--name-only")) if q]


def src_relevant(paths):
    """The engine's own definition of "a change that invalidates a test run" (ADR-039),
    IMPORTED rather than re-typed. Two copies of that table would be two answers to one
    question, and the whole point of `_src_relevant` is that there is one."""
    spec = importlib.util.spec_from_file_location("uscha_engine_for_release", ENGINE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module._src_relevant(paths)


def facts_gated_sections():
    """`tools/facts-gated-files.txt`, split into its two sections, or None when unreadable.

    ONE list, three readers (this script, `site/sync-docs.sh`, the suite's T0-live). Until
    1.97.0 there were two hand-maintained lists with different scopes, and the difference was a
    real hole rather than a tidiness complaint: the release wrote the six `site/docs/` copies --
    build output that `sync-docs.sh` deletes with `rm -rf site/docs` and regenerates from
    `docs/` -- while their canonical twins were only ever checked. A rewrite that lands in the
    copy and not in the source is undone by the next deploy."""
    try:
        lines = read(GATED_LIST).splitlines()
    except OSError:
        return None
    out, section = {"canonical": [], "deployed": []}, None
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            for name in out:
                if stripped[1:].strip().lower().startswith(name):
                    section = name
            continue
        if section is None:
            return None      # a path before any section header: unclassified, so UNMEASURED
        out[section].append(stripped)
    return out if out["canonical"] else None


def facts_check_files():
    """Every gated path, canonical section first. Written AND checked: the copies move with
    their sources, so the tree is consistent between a release and the next deploy."""
    sections = facts_gated_sections()
    if not sections:
        return None
    return sections["canonical"] + sections["deployed"]


def engine(*argv):
    return run([sys.executable, ENGINE] + list(argv),
               env={"PYTHONIOENCODING": "utf-8"})


# --------------------------------------------------------------------------- #
# step 1 -- preflight (I1, I2)
# --------------------------------------------------------------------------- #
def step1(args, dry):
    say("[1] preflight")
    if not SEMVER.match(args.version):
        refuse("usage", "%r is not a X.Y.Z version" % args.version)
    if git_out("rev-parse", "--is-inside-work-tree") != "true":
        refuse("I1", "%s is not a git work tree" % REPO)

    # A DIRTY TREE IS THE NORMAL STATE HERE and is NOT refused: the working tree -- the feature,
    # the docs, the changelog prose -- IS what X commits, together with the bump. What I1
    # protects is that X can be a fast-forward and that git is not mid-operation.
    if git("rev-parse", "-q", "--verify", "MERGE_HEAD").returncode == 0:
        refuse("I1", "a merge is in progress (MERGE_HEAD exists). Finish or abort it: a release "
                     "commit taken mid-merge carries a half-resolved tree.")
    unmerged = [unquote(x) for x in
                git_lines("-c", "core.quotepath=false", "diff", "--name-only",
                          "--diff-filter=U")]
    if unmerged:
        refuse("I1", "unmerged path(s): %s. Resolve them first." % ", ".join(unmerged[:5]))

    if dry:
        say("    would run: git fetch --tags origin (skipped: a dry run touches no network)")
    elif git("fetch", "--tags", "origin").returncode != 0:
        refuse("I1", "`git fetch --tags origin` failed -- the merge-base and the tag check "
                     "below would be answered against a stale remote, which is not an answer.")
    origin_main = git_out("rev-parse", "origin/main")
    if not origin_main:
        refuse("I1", "origin/main does not resolve -- the branch cannot be shown to be ahead "
                     "of it, and UNMEASURED is not a pass.")
    base = git_out("merge-base", "origin/main", "HEAD")
    if base != origin_main:
        refuse("I1", "HEAD has diverged from origin/main (merge-base %s, origin/main %s): "
                     "rebase or merge first, then release." % (base[:7], origin_main[:7]))

    tag = "v" + args.version
    if git("rev-parse", "-q", "--verify", "refs/tags/" + tag).returncode == 0:
        refuse("I2", "%s already exists -- a version is released once." % tag)

    changelog = os.path.join("uscha-kit", "CHANGELOG-%s.md" % args.version)
    full = os.path.join(REPO, changelog)
    shown = changelog.replace(os.sep, "/")
    if not os.path.isfile(full):
        refuse("I2", "%s is missing. The human writes the prose; this script only fills in the "
                     "counts." % shown)
    if PLACEHOLDER not in read(full):
        refuse("I2", "%s does not carry the placeholder line %r. Its presence is the receipt "
                     "that the prose was written before the numbers existed." % (shown,
                                                                                 PLACEHOLDER))

    say("    branch ahead of origin/main only, no merge in progress, %s carries the "
        "placeholder, %s free" % (shown, tag))
    return {"changelog": changelog}


# --------------------------------------------------------------------------- #
# step 2 -- the six surfaces + SYSTEM-FACTS + the claims gate (I3)
# --------------------------------------------------------------------------- #
def current_version():
    return read(os.path.join(REPO, SURFACES[0])).split()[-1].strip()


def step2(args, dry):
    say("[2] version surfaces + SYSTEM-FACTS + facts --check")
    old = current_version()
    target = args.version

    if old == target:
        # a resumed run, or a bump already applied by hand: verify the six AGREE rather than
        # replacing nothing and calling it done
        disagree = [rel for rel in SURFACES
                    if target not in read(os.path.join(REPO, rel))]
        if disagree:
            refuse("I3", "already at %s but these surfaces do not carry it: %s"
                   % (target, ", ".join(disagree)))
        say("    six surfaces already at %s (no-op)" % target)
    else:
        for rel in SURFACES:
            path = os.path.join(REPO, rel)
            body = read(path)
            hits = body.count(old)
            if hits != 1:
                refuse("I3", "%s contains %d occurrence(s) of %s, expected exactly 1 -- a "
                             "blind replace here would move something that is not the version."
                       % (rel, hits, old))
            if not dry:
                write(path, body.replace(old, target))
        say("    %s -> %s in %d surfaces%s"
            % (old, target, len(SURFACES), " (dry run: not written)" if dry else ""))

    if dry:
        say("    would run: qa_ledger.py facts --out %s" % FACTS_OUT)
    else:
        r = engine("facts", "--out", FACTS_OUT)
        if r.returncode != 0:
            refuse("engine failure", "facts --out failed:\n%s" % r.stdout.strip())
        say("    " + r.stdout.strip())

    files = facts_check_files()
    if not files:
        refuse("I3", "could not parse tools/facts-gated-files.txt (missing, empty, or a path "
                     "outside both sections); an unparsed claim set is UNMEASURED, not green.")
    # Since 1.97.0 the bump also REWRITES the claims it can derive. Before that a version bump
    # was ~25 hand edits across these files and this step could only print the drift and hand it
    # back -- work with no judgement in it, done between two fourteen-minute suite runs.
    if dry:
        say("    would run: qa_ledger.py facts --write over %d file(s)" % len(files))
    else:
        w = engine(*(["facts", "--write"] + files))
        say("    " + w.stdout.strip().replace("\n", "\n    "))
        if w.returncode != 0:
            # rc 2 = a file in the gated set could not be read at all. That is an UNMEASURED
            # claim set, not a clean one -- and the --check below reads with errors="replace",
            # so it could pass while the file is unreadable. Refuse here instead.
            refuse("I3", "`facts --write` exited %d: the claim set could not be fully written. "
                         "Fix the file(s) it named and re-run." % w.returncode)
    # The gate is still the CHECK, run on its own. `--write` only touches the claims the engine
    # recognises; a missing subcommand table row or a claim phrased in prose survives it, and a
    # release that fixed what it could and shipped the rest would be exactly the self-graded
    # evidence this repo refuses everywhere else.
    r = engine(*(["facts", "--check"] + files))
    if r.returncode != 0:
        say("    " + r.stdout.strip().replace("\n", "\n    "))
        refuse("I3", "published claims still disagree with the derived facts after "
                     "`facts --write` (%d file(s) checked) -- these are the ones the writer "
                     "does not recognise. Edit them by hand and re-run." % len(files))
    say("    " + r.stdout.strip())
    return {}


# --------------------------------------------------------------------------- #
# step 3 -- the code commit X: the working tree AND the bump, together
# --------------------------------------------------------------------------- #
def step3(args, dry):
    say("[3] commit X")
    # X is the CODE commit. `git add -A` takes the working tree exactly as the human left it --
    # feature, docs, changelog prose -- plus step 2's six surfaces and SYSTEM-FACTS.json, and
    # commits them as ONE thing. Anything that must not ship is the human's to stash or ignore
    # BEFORE running this; the staged list is printed so nothing lands unseen.
    if dry:
        planned = sorted(set(porcelain()))
        say("    would commit X with %d path(s):" % len(planned))
        for path in planned[:20]:
            say("      " + path)
        if len(planned) > 20:
            say("      ... and %d more" % (len(planned) - 20))
        if not args.message_file:
            say("    (a real run also needs --message-file: this script does not author a "
                "commit message)")
        return {}

    if not args.message_file:
        refuse("usage", "--message-file is required for the code commit: this script does not "
                        "author a commit message.")
    msg_path = os.path.abspath(args.message_file)
    if not os.path.isfile(msg_path):
        refuse("usage", "--message-file %s does not exist" % msg_path)
    if git("add", "-A").returncode != 0:
        refuse("git failure", "git add -A failed")
    staged = staged_paths()
    if not staged:
        refuse("usage", "nothing to commit as X: the working tree is clean and step 2 changed "
                        "no file, so there is no release here.")
    say("    X carries %d path(s): %s%s"
        % (len(staged), ", ".join(staged[:6]),
           "" if len(staged) <= 6 else ", ... (+%d more)" % (len(staged) - 6)))
    r = git("commit", "-F", msg_path)
    if r.returncode != 0:
        refuse("git failure", "git commit failed:" + chr(10) + git_msg(r))
    sha, when = head_identity()
    say("    X = %s (%s)" % (sha[:7], when))
    return {"code_commit": {"sha": sha, "committed": when}}


# --------------------------------------------------------------------------- #
# step 4 -- the suite (I4)
# --------------------------------------------------------------------------- #
def step4(args, dry, state):
    say("[4] suite")
    recorded = (state.get("code_commit") or {}).get("sha")
    sha, _when = head_identity()
    if recorded and sha != recorded:
        refuse("I4", "HEAD is %s but X was recorded as %s -- the suite must measure X, not "
                     "whatever came after it." % ((sha or "?")[:7], recorded[:7]))

    if dry:
        # X does not exist in a dry run, so every source path is legitimately dirty: it is
        # what X WOULD carry. Asserting cleanliness here would refuse on the plan's own premise.
        say("    would verify that no source-relevant path is dirty at X")
    else:
        dirty_src = src_relevant(porcelain())
        if dirty_src:
            refuse("I4", "source-relevant paths are dirty, so a green report would measure "
                         "bytes no commit carries: %s" % ", ".join(dirty_src[:5]))

    cmd = args.suite_cmd or ("bash uscha-kit/tests/smoke-engine.sh")
    if dry:
        say("    would run: %s (PYTHON=%s)" % (cmd, sys.executable))
        return {}
    say("    running: %s" % cmd)
    r = subprocess.run(cmd, cwd=REPO, shell=True, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                       errors="replace",
                       env=dict(os.environ, PYTHON=sys.executable,
                                PYTHONIOENCODING="utf-8"))
    tail = "\n".join(r.stdout.splitlines()[-15:])
    if r.returncode != 0:
        refuse("I4", "the suite exited %d. A red suite is a refusal, never a note.\n%s"
               % (r.returncode, tail))
    m_res, m_acc = RESULTADO.search(r.stdout), ACCEPTANCE.search(r.stdout)
    if not m_res or not m_acc:
        refuse("I4", "the suite exited 0 but printed no RESULTADO/ACCEPTANCE line -- counts "
                     "that cannot be read cannot be published.\n%s" % tail)
    checks, fails, acc = int(m_res.group(1)), int(m_res.group(2)), m_acc.group(1)
    if fails:
        refuse("I4", "the suite reports %d failing check(s)" % fails)
    say("    RESULTADO: %d ok, %d fail; ACCEPTANCE: %s" % (checks, fails, acc))
    return {"suite": {"checks": checks, "fails": fails, "acceptance": acc}}


# --------------------------------------------------------------------------- #
# step 5 -- record the evidence, then commit X+1 (I5, I6)
# --------------------------------------------------------------------------- #
def step5(args, dry, state):
    say("[5] snapshot + readiness --record, then commit X+1")
    recorded = state.get("code_commit") or {}
    sha, when = head_identity()
    if recorded:
        if sha != recorded.get("sha") or when != recorded.get("committed"):
            refuse("I5", "X moved after it was recorded: was %s (%s), HEAD is now %s (%s). An "
                         "amend re-dates X and orphans the snapshot's commit -- the trap rule 9 "
                         "used to write in capitals."
                   % (str(recorded.get("sha"))[:7], recorded.get("committed"),
                      (sha or "?")[:7], when))
    suite = state.get("suite") or {}
    if not suite and not dry:
        refuse("I4", "no suite counts recorded -- step 4 has not run for this release.")

    if dry:
        say("    would run: qa_ledger.py snapshot --repo uscha; qa_ledger.py readiness --record")
    else:
        for argv in (["snapshot", "--repo", "uscha"], ["readiness", "--record"]):
            r = engine(*argv)
            if r.returncode != 0:
                refuse("engine failure", "qa_ledger.py %s failed:\n%s" % (" ".join(argv), r.stdout.strip()))
            say("    " + r.stdout.strip().splitlines()[-1])

    changelog = os.path.join("uscha-kit", "CHANGELOG-%s.md" % args.version)
    full = os.path.join(REPO, changelog)

    if dry:
        say("    would fill the placeholder in %s and commit X+1 as %r"
            % (changelog.replace(os.sep, "/"), LEDGER_MSG % args.version))
        return {}

    if git("add", "-A").returncode != 0:
        refuse("git failure", "git add -A failed")
    offending = src_relevant(staged_paths())
    if offending:
        # BEFORE the counts are written: a refusal here must leave the changelog placeholder
        # intact, or the human has to undo an edit the script made on its way to saying no.
        git("reset", "-q")
        refuse("I6", "X+1 would carry source-relevant path(s): %s. The ledger commit carries "
                     "evidence, never code -- commit them into X first, or drop them."
               % ", ".join(offending[:5]))

    body = read(full)
    if PLACEHOLDER in body:
        write(full, body.replace(PLACEHOLDER,
                                 COUNTS % (suite["checks"], suite["fails"],
                                           suite["acceptance"])))
        git("add", "--", changelog)
        say("    %s: counts written" % changelog.replace(os.sep, "/"))
    staged = staged_paths()
    if not staged:
        refuse("I6", "nothing to commit as X+1: neither the ledger nor the changelog moved.")
    r = git("commit", "-m", LEDGER_MSG % args.version)
    if r.returncode != 0:
        refuse("git failure", "X+1 commit failed:" + chr(10) + git_msg(r))
    ledger_sha, _ = head_identity()
    say("    X+1 = %s (%d path(s): %s)"
        % (ledger_sha[:7], len(staged), ", ".join(staged[:5])))
    return {"ledger_commit": ledger_sha}


# --------------------------------------------------------------------------- #
# step 6 -- seal, push, tag (I7, I8)
# --------------------------------------------------------------------------- #
def main_worktree():
    """The path of the worktree that has `refs/heads/main` checked out, or None.

    This exists because the kit's own ritual runs in a WORKTREE per release (repo rule 9), where
    main is checked out in the primary tree. `git checkout main` there fails with
    "fatal: 'main' is already checked out at <path>" -- so the script never checks anything out;
    it asks who holds the ref and leaves that worktree alone.

    `git worktree list --porcelain` emits one block per worktree: a `worktree <path>` line, then
    `HEAD <sha>`, then `branch <ref>` (absent when detached)."""
    path = None
    for line in git_lines("worktree", "list", "--porcelain"):
        if line.startswith("worktree "):
            path = line[len("worktree "):].strip()
        elif line.strip() == "branch refs/heads/main":
            return path
    return None


def smoke_conclusion(sha):
    """(status, conclusion, url) for the `smoke` run of this SHA, or None when GitHub did not
    answer. An API error and "no run exists" look the same from here, so an error is never
    read as an answer -- the same posture publish.yml takes."""
    r = run(["gh", "run", "list", "--commit", sha, "--workflow", "smoke",
             "--limit", "20", "--json", "status,conclusion,url"])
    if r.returncode != 0:
        return None
    try:
        runs = json.loads(r.stdout)
    except ValueError:
        return None
    if not isinstance(runs, list) or not runs:
        return ("none", "none", "")
    latest = runs[0]
    return (latest.get("status") or "", latest.get("conclusion") or "none",
            latest.get("url") or "")


# GitHub takes a while to REGISTER a workflow run after a push -- minutes, not seconds, when
# the queue is busy. Two empty samples a minute apart is not "there is no run", it is "we asked
# too early", and treating it as an answer refuses a release that was about to be measured.
EMPTY_GRACE_MINUTES = 5


def wait_for_smoke(sha, minutes=45):
    empty = 0
    for i in range(minutes):
        answer = smoke_conclusion(sha)
        if answer is None:
            say("    gh did not answer (%d/%d) -- an API error is not an answer; retrying"
                % (i + 1, minutes))
        else:
            status, conclusion, url = answer
            if status == "none":
                empty += 1
                if empty >= EMPTY_GRACE_MINUTES:
                    refuse("I8", "the smoke run for %s never appeared: %d consecutive empty "
                                 "samples over %d minutes. main is already pushed, so check "
                                 "Actions and re-run with --from-step 6 once the run is "
                                 "listed." % (sha[:7], empty, EMPTY_GRACE_MINUTES))
                say("    no smoke run listed for %s yet (%d/%d, grace %d/%d)"
                    % (sha[:7], i + 1, minutes, empty, EMPTY_GRACE_MINUTES))
            else:
                empty = 0
                if status != "completed":
                    say("    smoke for %s is %s (%d/%d)" % (sha[:7], status, i + 1, minutes))
                elif conclusion == "success":
                    say("    smoke green for %s: %s" % (sha[:7], url))
                    return
                else:
                    refuse("I8", "the smoke run for %s completed %r (%s). These exact bytes "
                                 "are measured RED; tagging them would publish a belief."
                           % (sha[:7], conclusion, url))
        time.sleep(60)
    refuse("I8", "%d minutes of polling and the smoke run for %s never reported a completed "
                 "status. Waiting forever is not a safer default." % (minutes, sha[:7]))


def step6(args, dry, state):
    say("[6] seal, push, tag")
    if dry:
        # X+1 does not exist in a dry run, so the seal has nothing to bind to yet. Running
        # check-terminado here would measure the CURRENT HEAD and refuse on the plan's premise.
        say("    would verify: check-terminado prints SEALED at X+1")
        say("    would push HEAD:main to origin (never a checkout: the ritual runs in a "
            "worktree), then %s"
            % ("tag v" + args.version + " and push it (publish.yml gates on the tag's six-cell run)" if args.tag
               else "stop -- no --tag, so nothing is published"))
        return {}
    r = engine("check-terminado")
    if r.returncode != 0:
        refuse("I7", "check-terminado exited %d at X+1 -- the evidence is not bound to this "
                     "code state:\n%s" % (r.returncode, r.stdout.strip()))
    say("    " + r.stdout.strip().splitlines()[0])

    if args.no_push:
        say("    --no-push: stopping before the merge. The tag, if any, is yours to create.")
        return {}

    branch = git_out("rev-parse", "--abbrev-ref", "HEAD")
    head = git_out("rev-parse", "HEAD")
    if branch == "main":
        if git("push", "origin", "main").returncode != 0:
            refuse("git failure", "git push origin main failed")
        say("    pushed main (%s) to origin" % head[:7])
    else:
        # NOTHING is ever checked out here. The ritual runs in a worktree per release and main
        # lives in the primary tree, so `git checkout main` would fail every time with
        # "already checked out at ...". Push HEAD straight AT the branch and let the SERVER
        # enforce the fast-forward -- it is the only party that can, and it is the one that
        # matters. The local ref is a convenience, moved only when no worktree holds it.
        origin_main = git_out("rev-parse", "origin/main")
        if not origin_main:
            refuse("I1", "origin/main does not resolve, so a fast-forward cannot be shown.")
        if git("merge-base", "--is-ancestor", origin_main, head).returncode != 0:
            refuse("I1", "%s does not contain origin/main (%s): the push would not be a "
                         "fast-forward. Rebase or merge first."
                   % (head[:7], origin_main[:7]))
        if git("push", "origin", "HEAD:main").returncode != 0:
            refuse("git failure", "git push origin HEAD:main failed")
        say("    pushed %s to origin/main (fast-forward, from branch %s)" % (head[:7], branch))
        holder = main_worktree()
        if holder:
            say("    local main is checked out at %s -- left alone. Fast-forward it there:"
                % holder)
            say("      git -C %s merge --ff-only %s" % (holder, head))
        elif git("update-ref", "refs/heads/main", head).returncode != 0:
            refuse("git failure", "git update-ref refs/heads/main failed")
        else:
            say("    local main fast-forwarded to %s" % head[:7])

    if not args.tag:
        say("    no --tag: the tag is not created. Nothing is published until it is.")
        return {}
    tag = "v" + args.version
    if args.wait_ci:
        wait_for_smoke(head)
    else:
        say("    tagging right after the push: publish.yml waits for the tag's own six-cell smoke "
            "run and refuses on red (1.98.1; --wait-ci polls the branch run first).")
    if git("tag", "-a", tag, "-m", "uscha-kit " + args.version, head).returncode != 0:
        refuse("git failure", "git tag %s failed" % tag)
    if git("push", "origin", tag).returncode != 0:
        refuse("git failure", "git push origin %s failed" % tag)
    say("    tagged %s at %s and pushed." % (tag, head[:7]))
    say("    GitHub release stays manual, on purpose. Run:")
    say("      gh release create %s --title \"uscha-kit %s\" "
        "--notes-file uscha-kit/CHANGELOG-%s.md" % (tag, args.version, args.version))
    return {}


# --------------------------------------------------------------------------- #
STEPS = (step1, step2, step3, step4, step5, step6)


def build_parser():
    p = argparse.ArgumentParser(
        prog="release.py",
        description="Run the uscha release ritual, refusing on I1..I8 (ADR-041).")
    p.add_argument("version", help="the release version, X.Y.Z")
    p.add_argument("--message-file", default=None,
                   help="file holding the commit message for the code commit X (required "
                        "from step 3: this script does not author one)")
    p.add_argument("--suite-cmd", default=None,
                   help="override the suite command (default: bash "
                        "uscha-kit/tests/smoke-engine.sh with PYTHON set to this interpreter)")
    p.add_argument("--from-step", type=int, default=1, choices=range(1, 7),
                   help="resume at this step (state carries X's identity and the suite counts)")
    p.add_argument("--to-step", type=int, default=6, choices=range(1, 7),
                   help="stop after this step")
    p.add_argument("--dry-run", action="store_true",
                   help="write NOTHING: run every read-only check, report each verdict, print "
                        "the plan for the write steps, exit 0")
    p.add_argument("--no-push", action="store_true", help="stop step 6 before merge and push")
    p.add_argument("--wait-ci", action="store_true",
                   help="poll the branch push's smoke run before tagging (off by default since "
                        "1.98.1: publish.yml already gates on the tag's six-cell run)")
    p.add_argument("--no-wait-ci", action="store_true",
                   help="accepted for compatibility; this is the default since 1.98.1")
    p.add_argument("--tag", action="store_true",
                   help="create and push the annotated tag v<X.Y.Z> on X+1")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    dry = args.dry_run
    if dry:
        say("DRY RUN: nothing is written, nothing is committed, nothing leaves this machine.")
    state = load_state() if args.from_step > 1 else {}
    if state.get("version") not in (None, args.version):
        say("note: dropping state left by release %s" % state.get("version"))
        state = {}
    state["version"] = args.version
    if args.from_step > args.to_step:
        say("usage: --from-step %d is after --to-step %d, so no step would run."
            % (args.from_step, args.to_step))
        sys.exit(2)

    refusals = 0
    for n in range(args.from_step, args.to_step + 1):
        step = STEPS[n - 1]
        try:
            if n in (1, 2, 3):
                produced = step(args, dry)
            else:
                produced = step(args, dry, state)
        except Refused as exc:
            refusals += 1
            head = "WOULD REFUSE" if dry else "REFUSED"
            say("")
            say("%s -- %s: %s" % (head, exc.inv, exc))
            if dry:
                say("    (dry run: continuing to report the rest)")
                continue
            sys.exit(2)
        state.update(produced or {})
        if not dry:
            save_state(state)
    if dry:
        say("")
        say("dry run complete: %d check(s) would refuse." % refusals)
        return
    say("")
    say("done. State in %s -- delete it once the release is out."
        % os.path.basename(STATE))


if __name__ == "__main__":
    main()
