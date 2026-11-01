#!/usr/bin/env python3
"""PreToolUse hook for ADR-058 -- a pull request stays a DRAFT while the uscha gate is red.

What it does
------------
Before the agent opens a ready-for-review pull request, it asks the engine. It blocks:

  - `gh pr create` / `gh pr new` without `--draft` / `-d` (`--draft=<false>` counts as no draft),
  - `gh pr ready` (turning a draft into ready-for-review; `gh pr ready --undo` passes),
  - a forge MCP `create_pull_request` whose `draft` is not true, an `update_pull_request` that
    sets `draft: false`, and an MCP "mark ready for review" call,

The shell command is tokenized as the shell would (quotes, operators, comments, `cd` before the
call, `VAR=x` / `env` / `command` prefixes), so a draft whose body holds `|`, `;` or newlines
passes, and a commit message that merely mentions `gh pr create` is not a PR. The ledger is found
up from the cwd, or in a control folder beside the repo that maps it (`"path": "../backend-api"`),
or at `USCHA_LEDGER`.

when the read-only `qa_ledger.py pr-gate --cwd <cwd>` says a repo mapped to the call's cwd is not
`pr-ready`. A draft always passes, and so does every other tool call. "Ready for review" is then
the human's own act in the forge, which the forge authenticates.

What it CANNOT do -- read this before trusting it
-------------------------------------------------
It reads the tool call as TEXT. A `gh api` call, a script that opens the PR, a command word held in
a variable (`$G pr create`), a forge whose MCP tools carry other names (GitLab merge requests), or
a PR opened in a browser get through. It exists only where a blocking pre-tool hook exists (Claude Code); every
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
SHELL_TOOLS = {"bash", "powershell"}
# words that run the next word as the command
WRAPPERS = {"command", "env", "sudo", "exec", "time", "nohup", "builtin", "nice"}
# `gh pr create` flags that take a value: their value is never read as `--draft`
VALUE_FLAGS = {"-t", "--title", "-b", "--body", "-F", "--body-file", "-B", "--base", "-H",
               "--head", "-a", "--assignee", "-l", "--label", "-m", "--milestone", "-p",
               "--project", "-r", "--reviewer", "-T", "--template", "--recover", "-R", "--repo",
               "--hostname"}
TRUE_WORDS = {"1", "t", "true"}           # gh parses booleans like Go's strconv.ParseBool
CREATE = {"create", "new"}                # `gh pr new` is gh's built-in alias of create
MCP_CREATE = {"create_pull_request"}
MCP_UPDATE = {"update_pull_request"}
MCP_READY = {"mark_pull_request_ready_for_review", "mark_pr_ready_for_review",
             "ready_for_review", "mark_ready_for_review"}


def engine_path():
    env = os.environ.get("USCHA_QA_LEDGER")
    if env:
        return env
    here = os.path.dirname(os.path.realpath(__file__))
    # installed: ~/.claude/hooks/ beside ~/.claude/skills/; plugin: <root>/hooks beside <root>/skills
    return os.path.join(os.path.dirname(here), "skills", "uscha-devloop", "qa_ledger.py")


def _norm(p):
    return os.path.normcase(os.path.realpath(p))


def _within(child, parent):
    c, pa = _norm(child), _norm(parent)
    return c == pa or c.startswith(pa.rstrip(os.sep) + os.sep)


def _maps(ledger_path, cwd):
    try:
        with open(ledger_path, encoding="utf-8") as fh:
            repos = (json.load(fh).get("config") or {}).get("repos") or []
    except (OSError, ValueError, AttributeError):
        return False
    base = os.path.dirname(ledger_path)
    return any(isinstance(r, dict) and _within(cwd, os.path.join(base, r.get("path") or "."))
               for r in repos)


def find_ledger(start):
    """A copy of the engine's `_find_ledger_up` (qa_ledger.py): USCHA_LEDGER; else an ancestor's
    QA-LEDGER.json; else one in an immediate child folder of an ancestor whose config maps the
    cwd (the kit's default layout: a control folder beside `../backend-api`)."""
    env = os.environ.get("USCHA_LEDGER")
    if env:
        return env if os.path.isfile(env) else None
    d = os.path.realpath(start)
    while True:
        if os.path.isfile(os.path.join(d, "QA-LEDGER.json")):
            return os.path.join(d, "QA-LEDGER.json")
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    d = os.path.realpath(start)
    while True:
        parent = os.path.dirname(d)
        if parent == d:
            return None
        try:
            kids = sorted(os.listdir(parent))
        except OSError:
            kids = []
        for k in kids:
            cand = os.path.join(parent, k, "QA-LEDGER.json")
            if os.path.isfile(cand) and _maps(cand, start):
                return cand
        d = parent


def _tokens(command):
    text = (command or "").replace("\\\n", " ").replace("\r", "")
    # an unquoted newline separates commands; inside quotes the swap is harmless (same token)
    text = text.replace("\n", " ; ")
    lex = shlex.shlex(text, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    return list(lex)


def _segments(tokens):
    seg = []
    for t in tokens:
        if t and all(ch in "();<>|&" for ch in t):
            if seg:
                yield seg
            seg = []
        else:
            seg.append(t)
    if seg:
        yield seg


def _command_word(seg):
    i = 0
    while i < len(seg):
        t = seg[i]
        if "=" in t and not t.startswith("-") and t.split("=", 1)[0].replace("_", "a").isalnum():
            i += 1                                # VAR=value prefix
        elif t in WRAPPERS:
            i += 1
            while i < len(seg) and seg[i].startswith("-"):
                i += 1                            # the wrapper's own flags
        else:
            return i
    return None


def _gh_request(args):
    """'create' / 'ready' when these gh args ask for a ready-for-review PR, else None."""
    pos, draft, undo, i = [], False, False, 0
    while i < len(args):
        t = args[i]
        if t in VALUE_FLAGS:
            i += 2
            continue
        if t in ("--draft", "-d"):
            draft = True
        elif t.startswith("--draft="):
            draft = t.split("=", 1)[1].lower() in TRUE_WORDS
        elif t == "--undo" or (t.startswith("--undo=") and t.split("=", 1)[1].lower() in TRUE_WORDS):
            undo = True
        elif not t.startswith("-"):
            pos.append(t)
        i += 1
    if len(pos) < 2 or pos[0] != "pr":
        return None
    if pos[1] in CREATE and not draft:
        return "gh pr %s without --draft" % pos[1]
    if pos[1] == "ready" and not undo:
        return "gh pr ready"
    return None


def bash_intent(command, cwd):
    """(the ready-for-review request a shell command makes, or None; the cwd it runs in)."""
    try:
        tokens = _tokens(command)
    except ValueError:
        # unbalanced quoting: fall back to the conservative text reading
        low = (command or "").lower()
        if re.search(r"\bgh\b.*\bpr\s+(create|new|ready)\b", low) and "--draft" not in low:
            return "an unparseable gh pr command", cwd
        return None, cwd
    for seg in _segments(tokens):
        i = _command_word(seg)
        if i is None:
            continue
        word = os.path.basename(seg[i]).lower()
        if word == "cd" and i + 1 < len(seg):
            target = os.path.expanduser(seg[i + 1])
            cwd = target if os.path.isabs(target) else os.path.join(cwd, target)
            continue
        if word in ("gh", "gh.exe"):
            req = _gh_request(seg[i + 1:])
            if req:
                return req, cwd
    return None, cwd


def _truthy(v):
    return v is True or v == 1 or (isinstance(v, str) and v.strip().lower() in TRUE_WORDS)


def _falsy(v):
    return v is False or (v == 0 and v is not False) or (
        isinstance(v, str) and v.strip().lower() in {"0", "f", "false"})


def mcp_intent(name, tool_input):
    low = (name or "").lower()
    if not low.startswith("mcp__"):
        return None
    op = low.rsplit("__", 1)[-1].replace("-", "_")
    if op in MCP_CREATE:
        return None if _truthy(tool_input.get("draft")) else name + " without draft: true"
    if op in MCP_UPDATE:
        return name + " with draft: false" if _falsy(tool_input.get("draft")) else None
    if op in MCP_READY:
        return name
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
    cwd = payload.get("cwd") or os.getcwd()
    if name.lower() in SHELL_TOOLS:
        intent, cwd = bash_intent(tool_input.get("command"), cwd)
    else:
        intent = mcp_intent(name, tool_input)
    if not intent:
        return 0
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
