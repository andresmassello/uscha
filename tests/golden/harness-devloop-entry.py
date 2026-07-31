#!/usr/bin/env python3
"""Golden harness for AC-FP-08: freeze the engine's entry behavior WITHOUT a fast_path config.

Runs a canonical minimal session (init -> log-step -> readiness -> phase -> converged) against
a fixed fixture, normalizes the volatile fields (timestamps, absolute paths, interpreter
version), and writes tests/golden/devloop-entry.received.json.

The point: after fastpath-eval ships, a config WITHOUT a fast_path block must produce
byte-identical output to this capture. The agent never writes the .approved -- a human
approves the .received (INV-GOLDEN-01).
"""
import io
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
ENGINE = os.path.join(ROOT, "uscha-kit", ".claude", "skills", "uscha-devloop", "qa_ledger.py")
OUT = os.path.join(HERE, "devloop-entry.received.json")


def normalize(text, workdir):
    """Strip everything that legitimately differs between runs."""
    t = text
    # ISO timestamps (with or without Z / offset)
    t = re.sub(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?", "<TS>", t)
    # compact run ids (YYYYMMDD-HHMMSS)
    t = re.sub(r"\b\d{8}-\d{6}\b", "<RUNID>", t)
    # the temp workdir, both slash styles, plus its 8.3/resolved variants by basename
    for p in {workdir, workdir.replace("\\", "/"), os.path.realpath(workdir),
              os.path.realpath(workdir).replace("\\", "/")}:
        t = t.replace(p, "<WORK>")
    t = t.replace(ROOT.replace("\\", "/"), "<REPO>").replace(ROOT, "<REPO>")
    # interpreter version
    t = re.sub(r"\b3\.\d+\.\d+\b", "<PYVER>", t)
    # tmp dir basenames that survive path replacement
    t = re.sub(r"tmp[a-z0-9_]+", "<TMP>", t)
    return t


def main():
    work = tempfile.mkdtemp(prefix="golden-entry-")
    repo = os.path.join(work, "repo-x")
    os.makedirs(repo)
    io.open(os.path.join(repo, "mod.py"), "w", encoding="utf-8", newline="\n").write(
        "def alta():\n    return True\n")
    io.open(os.path.join(work, "ACCEPTANCE.md"), "w", encoding="utf-8", newline="\n").write(
        "# ACCEPTANCE\n\n- [ ] AC-01 — alta valida\n")
    # deliberately NO fast_path block: this is the behavior being frozen
    cfg = {"defaults": {"acceptance_file": "ACCEPTANCE.md"},
           "repos": [{"name": "repo-x", "path": "repo-x", "type": "python"}],
           "integration": {"enabled": False}}
    io.open(os.path.join(work, "c.json"), "w", encoding="utf-8", newline="\n").write(
        json.dumps(cfg, indent=2))

    steps = [
        ("init",      ["init", "--config", "c.json", "--out", "L.json"]),
        ("log-step",  ["log-step", "--ledger", "L.json", "--repo", "repo-x",
                       "--tool", "code-review", "--iteration", "1", "--tests-passed", "true"]),
        ("readiness", ["readiness", "--ledger", "L.json", "--json"]),
        ("phase",     ["phase", "--ledger", "L.json", "--repo", "repo-x"]),
        ("converged", ["converged", "--ledger", "L.json", "--repo", "repo-x"]),
    ]
    capture = {"_what": "engine entry behavior with NO fast_path config (pre-ADR-003 anchor)",
               "steps": []}
    for name, args in steps:
        r = subprocess.run([sys.executable, ENGINE] + args, cwd=work,
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        capture["steps"].append({
            "step": name,
            "exit": r.returncode,
            "stdout": normalize(r.stdout, work),
            "stderr": normalize(r.stderr, work),
        })
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(
        json.dumps(capture, indent=2, ensure_ascii=False) + "\n")
    print("[harness] wrote %s (%d steps)" % (OUT, len(steps)))
    print("[harness] a HUMAN approves this capture; the agent must not.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
