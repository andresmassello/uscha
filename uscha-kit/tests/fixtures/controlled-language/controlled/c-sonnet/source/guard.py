#!/usr/bin/env python3
"""PreToolUse guard enforcing INV-GOLDEN-01.

Reads one JSON object from stdin describing a pending tool call and reports
its verdict through the process exit code:
  - exit 0  -> allow the tool call
  - exit 2  -> block the tool call (a short reason is written to stderr)

The guard is fail-closed: anything it cannot prove safe is blocked. It
inspects the tool call as text/structure only; it never runs a command,
resolves a symlink, or inspects script content (see SPEC.md "Out of scope").
"""

import json
import re
import sys

MARKER = ".approved"

# Tool names recognised as read-only regardless of their arguments.
# Matched case-insensitively against tool_name.
READ_ONLY_TOOLS = {
    "read",
    "grep",
    "glob",
    "ls",
    "notebookread",
    "webfetch",
    "websearch",
}

# Tool names recognised as shell/command tools whose arguments carry a
# command line under tool_input["command"]. Matched case-insensitively.
SHELL_TOOLS = {
    "bash",
    "shell",
    "sh",
    "cmd",
    "powershell",
    "exec",
    "execute",
    "terminal",
    "command",
    "runcommand",
    "run_command",
}

# Command names recognised as readers (no side effect on file content) when
# they appear as a pipeline/sequence stage's leading word. Case-insensitive.
READER_COMMANDS = {
    "cat",
    "less",
    "more",
    "head",
    "tail",
    "grep",
    "egrep",
    "fgrep",
    "rg",
    "ag",
    "wc",
    "diff",
    "file",
    "stat",
    "md5sum",
    "sha1sum",
    "sha256sum",
    "shasum",
    "xxd",
    "od",
    "strings",
    "type",
    "findstr",
    "ls",
    "dir",
    "find",
    "tree",
    "jq",
    "awk",
    "sed",
    "printf",
    "echo",
}

# In-place / output write flags: presence anywhere in a shell command that
# names an approved golden forces a block, regardless of which stage carries
# the flag.
WRITE_FLAG_RE = re.compile(r"(?:^|\s)(-i\b|--in-place\b|-o\b|--output\b|-w\b)")

# Redirection to a file (>, >>) but not a stream duplication like 2>&1.
REDIRECT_RE = re.compile(r">>?(?!&)")

STAGE_SPLIT_RE = re.compile(r"\|\||&&|\||;")


def _block(reason):
    sys.stderr.write(reason + "\n")
    sys.exit(2)


def _allow():
    sys.exit(0)


def _contains_marker(text):
    return MARKER in text.lower()


def _deep_contains_marker(value):
    if isinstance(value, str):
        return _contains_marker(value)
    if isinstance(value, dict):
        return any(_deep_contains_marker(v) for v in value.values())
    if isinstance(value, list):
        return any(_deep_contains_marker(v) for v in value)
    return False


def _stage_command_name(stage):
    stage = stage.strip()
    if not stage:
        return None
    first = stage.split()[0]
    # Strip a path prefix so "/bin/cat" and "cat" match the same way.
    name = first.replace("\\", "/").split("/")[-1]
    return name.lower()


def _shell_command_is_reader(command):
    if REDIRECT_RE.search(command):
        return False
    if WRITE_FLAG_RE.search(command):
        return False

    stages = STAGE_SPLIT_RE.split(command)
    saw_stage = False
    for stage in stages:
        name = _stage_command_name(stage)
        if name is None:
            continue
        saw_stage = True
        if name == "find" and ("-delete" in stage or "-exec" in stage):
            return False
        if name not in READER_COMMANDS:
            return False
    return saw_stage


def main():
    raw = sys.stdin.read()

    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        _block("guard: input is not valid JSON")
        return

    if not isinstance(data, dict):
        _block("guard: input JSON is not an object")
        return

    tool_name = data.get("tool_name")
    tool_input = data.get("tool_input")

    if not isinstance(tool_name, str) or not isinstance(tool_input, dict):
        _block("guard: input does not match the expected {tool_name, tool_input} shape")
        return

    tool_key = tool_name.strip().lower()

    if tool_key in READ_ONLY_TOOLS:
        _allow()
        return

    if tool_key in SHELL_TOOLS:
        command = tool_input.get("command")
        if not isinstance(command, str):
            _block("guard: shell/command tool call has no command text")
            return
        if not _contains_marker(command):
            _allow()
            return
        if _shell_command_is_reader(command):
            _allow()
            return
        _block(
            "guard: command names an approved golden and cannot be proven a "
            "reader (redirection, write flag, or a writer pipeline stage)"
        )
        return

    # Every other tool (including writers like an edit/write tool, and any
    # tool this guard does not otherwise recognise): block if the marker
    # appears anywhere in the arguments, at any depth.
    if _deep_contains_marker(tool_input):
        _block("guard: tool call references an approved golden file")
        return

    _allow()


if __name__ == "__main__":
    main()
