#!/usr/bin/env python3
"""PreToolUse hook for ADR-058 -- a pull request stays a DRAFT while the uscha gate is red.

What it does
------------
Before the agent opens a ready-for-review pull request, it asks the engine. It blocks:

  - `gh pr create` without `--draft` / `-d`,
  - `gh pr ready` (turning a draft into ready-for-review; `gh pr ready --undo` passes),
  - a forge MCP `create_pull_request` whose `draft` is not true, and an `update_pull_request`
    that sets `draft: false`,

when the read-only `qa_ledger.py pr-gate --cwd <cwd>` says a repo mapped to the call's cwd is not
`pr-ready`. A draft always passes, and so does every other tool call. "Ready for review" is then
the human's own act in the forge, which the forge authenticates.

What it CANNOT do -- read this before trusting it
-------------------------------------------------
It reads the tool call as TEXT. A `gh api` call, a script that opens the PR, or a PR opened in a
browser get through. It exists only where a blocking pre-tool hook exists (Claude Code); every
other target reports `pr_guard: advisory`. The measured control is still `phase --require
pr-ready`; this hook only makes the field failure (an agent opening a ready PR while the ledger
read `qa`) take a deliberate act instead of an accident.

Posture
-------
GLOBAL and FAIL-CLOSED where it matters. No `QA-LEDGER.json` up the cwd -> allow (this is not a
uscha project). A ledger found but the engine missing or failing, or an unparseable payload ->
block, naming the cause: a guard that opens when it is confused is not a guard.
"""
import json
import os
import re
import shlex
import subprocess
import sys

TAG = "BLOCKED by ADR-058 (uscha PR gate)"
PR_CREATE = re.compile(r"\bgh\s+pr\s+create\b")
PR_READY = re.compile(r"\bgh\s+pr\s+ready\b")
SEGMENTS = re.compile(r"&&|\|\||[;|\n]")


def engine_path():
    env = os.environ.get("USCHA_QA_LEDGER")
    if env:
        return env
    here = os.path.dirname(os.path.realpath(__file__))
    # installed: ~/.claude/hooks/ beside ~/.claude/skills/; plugin: <root>/hooks beside <root>/skills
    return os.path.join(os.path.dirname(here), "skills", "uscha-devloop", "qa_ledger.py")


def find_ledger(start):
    d = os.path.realpath(start)
    while True:
        if os.path.isfile(os.path.join(d, "QA-LEDGER.json")):
            return os.path.join(d, "QA-LEDGER.json")
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def _is_draft(tokens):
    for t in tokens:
        if t in ("--draft", "-d") or (t.startswith("--draft=") and t.lower() != "--draft=false"):
            return True
    return False


def bash_intent(command):
    """The ready-for-review request a shell command makes, or None."""
    for seg in SEGMENTS.split(command or ""):
        if PR_READY.search(seg):
            if "--undo" in seg:
                continue
            return "gh pr ready"
        if PR_CREATE.search(seg):
            try:
                tokens = shlex.split(seg)
            except ValueError:
                tokens = seg.split()
            if not _is_draft(tokens):
                return "gh pr create without --draft"
    return None


def mcp_intent(name, tool_input):
    low = (name or "").lower()
    if not low.startswith("mcp__"):
        return None
    flat = low.replace("-", "_")
    if "create_pull_request" in flat or "createpullrequest" in flat:
        return None if tool_input.get("draft") is True else name + " without draft: true"
    if "update_pull_request" in flat or "updatepullrequest" in flat:
        return name + " with draft: false" if tool_input.get("draft") is False else None
    return None


def block(msg):
    print("%s: %s" % (TAG, msg), file=sys.stderr)
    return 2


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return block("the hook could not read its input, so it cannot prove this call is not a "
                     "ready-for-review PR (fail-closed).")
    if not isinstance(payload, dict):
        return block("unexpected hook payload shape (fail-closed).")
    name = payload.get("tool_name") or ""
    tool_input = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
    if name == "Bash":
        intent = bash_intent(tool_input.get("command"))
    else:
        intent = mcp_intent(name, tool_input)
    if not intent:
        return 0
    cwd = payload.get("cwd") or os.getcwd()
    if find_ledger(cwd) is None:
        return 0                               # not a uscha project: the hook is global
    eng = engine_path()
    if not os.path.isfile(eng):
        return block("%s, and the uscha engine was not found at %s -- the gate cannot be read, "
                     "so the PR is not opened ready-for-review (fail-closed)." % (intent, eng))
    try:
        r = subprocess.run([sys.executable, eng, "pr-gate", "--cwd", cwd], stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, text=True, encoding="utf-8",
                           errors="replace", timeout=120)
    except (OSError, subprocess.SubprocessError) as exc:
        return block("%s, and `pr-gate` could not run: %s (fail-closed)." % (intent, exc))
    try:
        verdict = json.loads(r.stdout)
    except ValueError:
        return block("%s, and `pr-gate` exited %s without a verdict: %s (fail-closed)."
                     % (intent, r.returncode, (r.stderr or r.stdout).strip()[-300:]))
    if verdict.get("ok") is True and r.returncode == 0:
        return 0
    red = [x for x in verdict.get("repos") or [] if not x.get("ready")]
    lines = []
    for x in red:
        lines.append("%s is not pr-ready (phase %s)" % (x.get("repo"), x.get("phase")))
        lines.extend("    - " + str(m) for m in (x.get("missing") or [])[:4])
    if not lines:
        lines.append("the gate is not pr-ready (pr-gate exit %s)" % r.returncode)
    return block("%s while the gate is red:\n  %s\nOpen it as a DRAFT (`gh pr create --draft`, or "
                 "draft: true) with the missing facts in its body, and record it with "
                 "`qa_ledger.py pr-opened-not-ready --repo <REPO> --requested-by <NAME> --note "
                 "\"...\"` -- or run the QA loop first. 'Ready for review' is the human's act in "
                 "the forge." % (intent, "\n  ".join(lines)))


if __name__ == "__main__":
    raise SystemExit(main())
