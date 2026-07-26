#!/usr/bin/env python3
"""PreToolUse hook for INV-GOLDEN-01 -- a BEST-EFFORT guard, not a sandbox.

What it does
------------
Stops the obvious ways an agent writes, renames or deletes an approved golden
fixture, so the human stays the only author of field truth. Reads are allowed on
purpose: golden-diff has to read the file it compares against.

What it CANNOT do -- read this before trusting it
-------------------------------------------------
It inspects the tool call as TEXT. It cannot know a command's real filesystem
effects, so any indirect write gets through: a Python or Node one-liner that
assembles the filename from pieces, a script whose contents it never sees, a
symlink pointing at the golden, a process spawned by another process. Treat this
as a guardrail against accident and casual shortcut -- NOT as a security boundary
against an adversarial agent. The measured control is `golden-diff`, which
compares bytes; this hook only lowers the odds of ever needing it.

It also only exists where a blocking pre-tool hook exists. `install-uscha.py`
registers it for the Claude target only; every Agent-Skills target
(codex/pi/cursor/copilot/gemini/cline) reports `golden_guard: advisory`, which is
the doctor telling the truth rather than implying a guard it cannot see.

Posture
-------
FAIL-CLOSED. An unparseable payload blocks instead of allowing: a guard that
opens when it is confused is not a guard. Matching is case-insensitive, because
Windows and macOS filesystems are.
"""
import json
import re
import sys

GOLDEN = ".approved"

BLOCK_MSG = (
    "BLOCKED by INV-GOLDEN-01: the agent may not create, edit, rename or delete an "
    "approved golden. The approved file is field truth -- a HUMAN signs it. Emit a "
    ".received instead and stop for human approval."
)

# Tools that cannot write. Reading a golden is legitimate (golden-diff does it).
READ_ONLY_TOOLS = {"read", "grep", "glob", "notebookread", "websearch", "webfetch",
                   "ls", "listdirectory"}

# Shell words that read without modifying. Anything NOT here is treated as a write.
READ_ONLY_SHELL = {
    "cat", "less", "more", "head", "tail", "grep", "egrep", "fgrep", "rg", "ag",
    "diff", "cmp", "wc", "md5sum", "sha1sum", "sha256sum", "shasum", "file", "stat",
    "od", "xxd", "hexdump", "strings", "awk", "cut", "sort", "uniq", "tr", "column",
    "echo", "printf", "test", "true", "false", "ls", "find", "basename", "dirname",
    "git", "python", "python3", "py", "node", "bash", "sh", "env", "which", "type",
}
# ... except these, which are how a "reader" still writes.
WRITE_FLAGS = {"-i", "--in-place", "-o", "--output", "-w", "--write"}


def _touches_golden(text):
    return GOLDEN in str(text).lower()


def _bash_writes(command):
    """True when a shell command plausibly WRITES a golden. Default-deny: anything
    this cannot prove is read-only counts as a write."""
    low = command.lower()
    # any redirection at all in a command naming a golden -- `cat a.approved > b.approved`
    # starts with a reader and still writes one.
    if ">" in low:
        return True
    if any(w in WRITE_FLAGS for w in low.split()):
        return True
    # EVERY segment of the pipeline must start with a known reader. Splitting on the
    # separators FIRST matters: an earlier version blanked them before looking, so it only
    # ever saw the first verb and `echo x | tee y.approved` read as a plain `echo`.
    segments = re.split(r"\|\||&&|[|;&]", low)
    verbs = []
    for seg in segments:
        words = seg.split()
        if words:
            verbs.append(words[0].split("/")[-1].split("\\")[-1])
    if not verbs:
        return True
    return not all(v in READ_ONLY_SHELL for v in verbs)


def decide(payload):
    """Return True to BLOCK."""
    tool = str(payload.get("tool_name", "")).strip().lower()
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        tool_input = {}
    if tool == "bash" or tool == "shell":
        command = tool_input.get("command", "")
        return _touches_golden(command) and _bash_writes(str(command))
    if tool in READ_ONLY_TOOLS:
        return False
    # Any other tool: if a golden appears ANYWHERE in its arguments, block. Unknown
    # write-capable tools must not slip through just because they are unknown.
    def walk(v):
        if isinstance(v, str):
            return _touches_golden(v)
        if isinstance(v, dict):
            return any(walk(x) for x in v.values())
        if isinstance(v, (list, tuple)):
            return any(walk(x) for x in v)
        return False
    return walk(tool_input)


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        # FAIL-CLOSED: previously this returned 0 (allow), so a malformed payload
        # silently disabled the guard.
        print("BLOCKED by INV-GOLDEN-01: the hook could not read its input, so it "
              "cannot prove this call is safe (fail-closed).", file=sys.stderr)
        return 2
    if not isinstance(payload, dict):
        print("BLOCKED by INV-GOLDEN-01: unexpected hook payload shape (fail-closed).",
              file=sys.stderr)
        return 2
    if decide(payload):
        print(BLOCK_MSG, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
