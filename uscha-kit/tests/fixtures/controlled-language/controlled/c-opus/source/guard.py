#!/usr/bin/env python3
"""INV-GOLDEN PreToolUse guard.

Reads one JSON object describing a pending tool call from stdin and reports a
verdict through the process exit code:

    exit 0  -> ALLOW the tool call
    exit 2  -> BLOCK the tool call (a short reason is written to stderr)

The guard enforces INV-GOLDEN-01 fail-closed: an agent must never create, edit,
rename, or delete an approved golden (a file whose name contains the marker
".approved", matched case-insensitively). Reads are allowed; every writing path
the guard can recognise is blocked.

Scope honesty (see SPEC "Out of scope"): the guard inspects the tool call as
text and structure only. It does NOT run commands, resolve symlinks, or read
script contents, so an INDIRECT write (performed by a script, a runtime, a
symlink, or a child process) is out of its reach. The measured byte-level
control for indirect writes lives elsewhere.

Pure standard library, Python 3.8+.
"""

import json
import re
import shlex
import sys

MARKER = ".approved"

# Verdicts expressed as process exit codes (AC-GH-01).
ALLOW = 0
BLOCK = 2

# Recognised read-only tools: a file reader, a text search, a directory
# listing, a notebook reader, or a web fetch / web search. Names are compared
# case-insensitively (AC-GH-04). SPEC names capabilities, not concrete tool
# identifiers, so this is a conservative allowlist.
READ_ONLY_TOOLS = {
    "read",
    "view",
    "cat",
    "glob",
    "grep",
    "ls",
    "list",
    "listdirectory",
    "notebookread",
    "webfetch",
    "websearch",
    "search",
    "fetch",
}

# Recognised shell / command tools. The command line is carried under
# tool_input["command"] (AC-GH-05).
SHELL_TOOLS = {
    "bash",
    "sh",
    "zsh",
    "fish",
    "shell",
    "cmd",
    "command",
    "powershell",
    "pwsh",
    "exec",
    "run",
    "terminal",
}

# Conservative allowlist of command basenames that only read / display / search.
# Anything NOT here is treated as a potential writer (default-deny). Notable
# exclusions: sed, awk, gawk, perl (in-place edit), tee, dd, cp, mv, rm, touch,
# and any general interpreter (python, ruby, node, bash, sh) which can do
# anything.
READER_COMMANDS = {
    "cat",
    "bat",
    "less",
    "more",
    "head",
    "tail",
    "tac",
    "nl",
    "grep",
    "egrep",
    "fgrep",
    "rg",
    "ag",
    "view",
    "wc",
    "od",
    "xxd",
    "hexdump",
    "strings",
    "cut",
    "sort",
    "uniq",
    "column",
    "tr",
    "comm",
    "look",
    "file",
    "stat",
    "cmp",
    "diff",
    "md5sum",
    "sha256sum",
}

# Operators that separate one command stage from the next in a pipeline or
# sequence. If any stage is a writer, the whole command is a writer (AC-GH-05).
_STAGE_SPLIT = re.compile(r"\|\||&&|;|\||&")


def _deny(reason):
    """Write a short reason to stderr and exit with the BLOCK code."""
    sys.stderr.write("BLOCKED: " + reason + "\n")
    sys.exit(BLOCK)


def _allow():
    sys.exit(ALLOW)


def contains_marker(value):
    """True if the marker appears at any depth in the given value.

    Case-insensitive; recurses through dicts (keys and values), lists, and
    tuples (AC-GH-06).
    """
    if isinstance(value, str):
        return MARKER in value.lower()
    if isinstance(value, dict):
        for key, val in value.items():
            if contains_marker(key) or contains_marker(val):
                return True
        return False
    if isinstance(value, (list, tuple)):
        return any(contains_marker(item) for item in value)
    return False


def command_is_proven_reader(command):
    """True only if a visible signal proves the command reads (never writes).

    Fail-closed (AC-GH-05): any output redirection, any pipeline/sequence stage
    whose command is not on the reader allowlist, or an unparseable command
    means the guard CANNOT prove the command is a reader -> not proven.
    """
    if not isinstance(command, str) or not command.strip():
        return False

    # Any output redirection to a file is a write signal.
    if ">" in command:
        return False

    for stage in _STAGE_SPLIT.split(command):
        stage = stage.strip()
        if not stage:
            # A dangling operator (e.g. trailing '&') yields an empty stage;
            # it carries no proof of being a reader.
            continue
        try:
            tokens = shlex.split(stage, posix=True)
        except ValueError:
            # Unbalanced quotes etc. -> cannot prove reader.
            return False
        if not tokens:
            return False
        # An explicit in-place flag is a write signal regardless of command.
        if any(t == "--in-place" or t.startswith("--in-place=") for t in tokens):
            return False
        basename = tokens[0].replace("\\", "/").split("/")[-1].lower()
        if basename not in READER_COMMANDS:
            return False

    return True


def decide(payload):
    """Return ALLOW or BLOCK for a parsed, shape-valid tool-call object."""
    tool_name = payload["tool_name"]
    tool_input = payload["tool_input"]
    name = tool_name.lower()

    # Read-only tools are always allowed, even when their arguments name an
    # approved golden (AC-GH-03, AC-GH-04).
    if name in READ_ONLY_TOOLS:
        return ALLOW

    # Shell / command tools: default-deny (AC-GH-05).
    if name in SHELL_TOOLS:
        command = tool_input.get("command")
        # If no golden is named anywhere in the arguments, there is nothing to
        # protect -> allow (the guard only governs approved goldens).
        if not contains_marker(tool_input):
            return ALLOW
        # A golden is named: allow only if a visible signal proves the command
        # is a reader; otherwise block (redirection, writer stage, write flag,
        # or simply no proof).
        return ALLOW if command_is_proven_reader(command) else BLOCK

    # Any other tool (write/edit/rename/delete or unknown): if the marker
    # appears at any depth in the arguments, block (AC-GH-02, AC-GH-06,
    # INV-GOLDEN-01). Otherwise allow.
    return BLOCK if contains_marker(tool_input) else ALLOW


def main():
    raw = sys.stdin.read()

    # Fail-closed: invalid JSON is blocked (AC-GH-07).
    try:
        payload = json.loads(raw)
    except (ValueError, TypeError):
        _deny("input is not valid JSON")

    # Fail-closed: wrong-shape input is blocked (AC-GH-07). Expected shape is an
    # object with a string tool_name and an object tool_input.
    if not isinstance(payload, dict):
        _deny("input JSON is not an object")
    if not isinstance(payload.get("tool_name"), str):
        _deny("missing or non-string tool_name")
    if not isinstance(payload.get("tool_input"), dict):
        _deny("missing or non-object tool_input")

    verdict = decide(payload)
    if verdict == ALLOW:
        _allow()
    _deny("tool call would write an approved golden (INV-GOLDEN-01)")


if __name__ == "__main__":
    main()
