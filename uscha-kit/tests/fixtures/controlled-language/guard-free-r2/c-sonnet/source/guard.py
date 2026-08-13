#!/usr/bin/env python3
"""INV-GOLDEN-01 PreToolUse guard.

Reads one JSON object from stdin describing a pending tool call and decides
whether it may proceed. The verdict is communicated ONLY through the process
exit code:
    0 -- ALLOW
    2 -- BLOCK (a short reason is written to stderr)

Fail-closed posture: anything the guard cannot positively prove safe is
blocked. This module never raises past main(); every error path resolves to
a BLOCK decision.
"""

import json
import re
import sys

# --- The marker that identifies an approved golden -----------------------

APPROVED_MARKER = ".approved"


def has_marker(text):
    """Case-insensitive substring check for the approved-golden marker."""
    if not isinstance(text, str):
        return False
    return APPROVED_MARKER in text.lower()


def contains_marker_anywhere(value):
    """Recursively scan a JSON-shaped value (dict/list/str/scalar) for the
    approved-golden marker in any string, at any nesting depth."""
    if isinstance(value, str):
        return has_marker(value)
    if isinstance(value, dict):
        return any(contains_marker_anywhere(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return any(contains_marker_anywhere(v) for v in value)
    return False


# --- Tool name normalization ----------------------------------------------

def normalize_name(name):
    if not isinstance(name, str):
        return ""
    return re.sub(r"[\s_\-]+", "", name.strip().lower())


# Tools that cannot write by their nature: readers, search, listing,
# web fetch/search, notebook readers. Always allowed, even naming a golden.
READ_ONLY_TOOLS = {
    "read", "readfile", "viewfile", "cat",
    "grep", "search", "textsearch", "codesearch", "ripgrep",
    "glob", "filesearch", "find",
    "ls", "list", "listdir", "listdirectory", "directorylisting",
    "websearch", "webfetch", "fetch", "urlfetch",
    "notebookread", "readnotebook", "jupyterread",
    "bashoutput", "readconsole",
}

# Tool names treated as "a shell / command tool" per the spec's example
# (Bash). Aliases are a best-effort extension of the single named example.
SHELL_TOOLS = {
    "bash", "shell", "sh", "exec", "runcommand", "terminal", "cmd", "powershell",
}


def classify_tool(tool_name):
    n = normalize_name(tool_name)
    if n in READ_ONLY_TOOLS:
        return "read_only"
    if n in SHELL_TOOLS:
        return "shell"
    return "other"


# --- Shell command analysis ------------------------------------------------

# Commands that are known to be read-only: they cannot, by themselves,
# create/modify/rename/delete a file. Anything not in this set is treated
# as a WRITE per the default-deny rule ("every part of it" must be proven
# read-only).
READ_ONLY_COMMANDS = {
    "cat", "head", "tail", "less", "more",
    "grep", "egrep", "fgrep", "rg", "ag", "ack",
    "ls", "dir", "wc", "file", "stat",
    "md5sum", "sha1sum", "sha256sum", "sha512sum", "shasum", "cksum",
    "od", "xxd", "hexdump", "strings",
    "which", "where", "type",
    "pwd", "basename", "dirname", "realpath", "readlink",
    "echo", "printf", "true", "false", "sleep", "tree", "nl", "tac",
}

# Flags that turn an otherwise-reading tool into a writer (in-place edit,
# explicit output/write target). Matched as whole tokens or prefixes.
WRITE_FLAG_TOKENS = {
    "-i", "--in-place", "--in_place",
    "-w", "--write", "--overwrite", "--fix", "--save",
    "-o", "--output",
}
WRITE_FLAG_PREFIXES = ("-i", "--in-place", "--in_place")

# Shell operators that split a command line into sequential stages.
STAGE_SPLIT_RE = re.compile(r"(?:\|\||&&|\||;|\n)")

# Output-redirection detector: a bare '>' or '>>' , optionally preceded by
# a file descriptor number, that is not part of '=>' or '->' style arrows.
REDIRECTION_RE = re.compile(r"(?<![=\-])\d{0,2}>{1,2}(?!=)")

ENV_ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=\S*$")


def strip_leading_env_assignments(tokens):
    i = 0
    while i < len(tokens) and ENV_ASSIGNMENT_RE.match(tokens[i]):
        i += 1
    return tokens[i:]


def stage_command_name(stage):
    tokens = stage.strip().split()
    tokens = strip_leading_env_assignments(tokens)
    if not tokens:
        return None
    cmd = tokens[0]
    # strip a path prefix
    cmd = re.split(r"[\\/]", cmd)[-1]
    # strip a windows-style extension
    cmd = re.sub(r"\.(exe|bat|cmd|sh)$", "", cmd, flags=re.IGNORECASE)
    return cmd.lower()


def has_write_flag(command):
    for tok in command.split():
        low = tok.lower()
        if low in WRITE_FLAG_TOKENS:
            return True
        for prefix in WRITE_FLAG_PREFIXES:
            if low.startswith(prefix) and low != "-input":
                return True
    return False


def shell_command_is_proven_read_only(command):
    """True only if every stage of the pipeline is a recognised read-only
    command, with no output redirection and no write flags anywhere."""
    if REDIRECTION_RE.search(command):
        return False
    if has_write_flag(command):
        return False

    stages = [s for s in STAGE_SPLIT_RE.split(command) if s.strip()]
    if not stages:
        return False

    for stage in stages:
        name = stage_command_name(stage)
        if name is None or name not in READ_ONLY_COMMANDS:
            return False
    return True


# --- Decision logic ---------------------------------------------------------

class Block(Exception):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def decide(payload):
    if not isinstance(payload, dict):
        raise Block("input is not a JSON object")

    if "tool_name" not in payload or not isinstance(payload.get("tool_name"), str):
        raise Block("missing or invalid 'tool_name' field")

    tool_name = payload["tool_name"]
    tool_input = payload.get("tool_input", {})
    if tool_input is None:
        tool_input = {}
    if not isinstance(tool_input, (dict, list, str)):
        raise Block("invalid 'tool_input' field")

    kind = classify_tool(tool_name)

    if kind == "read_only":
        return  # always allowed, even naming a golden

    if kind == "shell":
        command = None
        if isinstance(tool_input, dict):
            command = tool_input.get("command")
        if not isinstance(command, str):
            # No inspectable command text: fall back to the conservative
            # "any other tool" rule below.
            if contains_marker_anywhere(tool_input):
                raise Block("shell call with unreadable command text names an approved golden")
            return

        if not has_marker(command):
            return  # golden not named at all -> nothing to protect here

        if shell_command_is_proven_read_only(command):
            return

        raise Block("shell command names an approved golden and cannot be proven read-only")

    # Any other tool, including unknown write-capable tools: block if the
    # marker appears anywhere in the arguments, at any depth.
    if contains_marker_anywhere(tool_input):
        raise Block("tool arguments name an approved golden")
    return


def main():
    raw = sys.stdin.read()

    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        sys.stderr.write("BLOCK: stdin is not valid JSON\n")
        sys.exit(2)

    try:
        decide(payload)
    except Block as b:
        sys.stderr.write("BLOCK: " + b.reason + "\n")
        sys.exit(2)
    except Exception as e:  # fail-closed on any unexpected error
        sys.stderr.write("BLOCK: guard error: " + str(e) + "\n")
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
