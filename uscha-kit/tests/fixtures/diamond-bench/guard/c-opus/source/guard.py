#!/usr/bin/env python3
"""INV-GOLDEN-01 PreToolUse guard.

A fail-closed guardrail: it reads one JSON object describing a pending tool
call on stdin and decides, purely through its exit code, whether the call may
touch an approved golden.

    exit 0  -> ALLOW  (the tool call may proceed)
    exit 2  -> BLOCK  (a short reason is written to stderr)

An approved golden is any file whose name carries the ".approved" marker
(matched case-insensitively). A human is its sole author: reads are legitimate
and pass; every recognisable writing path (create / edit / rename / delete) is
blocked. When the guard cannot prove a call safe, it blocks.

Pure stdlib, Python 3.8+.
"""

import json
import re
import shlex
import sys

MARKER = ".approved"

# Tools that cannot write by their nature. A call to one of these is always
# allowed, even when it names a golden -- reading field truth is the point.
# Matched case-insensitively.
READ_ONLY_TOOLS = {
    "read",
    "grep",
    "glob",
    "ls",
    "notebookread",
    "webfetch",
    "websearch",
}

# Shell / command tools: their command string can do anything, so they get the
# default-deny treatment.
SHELL_TOOLS = {
    "bash",
    "sh",
    "shell",
    "zsh",
}

# Command verbs we are willing to recognise as read-only. A shell command that
# names a golden is only allowed when every stage's verb is in this set (and no
# stage carries a write flag or redirection). Anything not listed -- including
# interpreters (python, node, ruby, perl), copy/move/remove, editors, and
# writers like tee -- is treated as a WRITE.
READ_ONLY_VERBS = {
    "cat", "bat", "head", "tail", "less", "more", "view", "nl", "tac", "rev",
    "od", "xxd", "hexdump", "strings", "wc", "cksum", "sum",
    "sha1sum", "sha256sum", "sha512sum", "md5sum",
    "grep", "egrep", "fgrep", "zgrep", "rg", "ag", "ack",
    "find", "fd", "ls", "dir", "eza", "exa", "tree",
    "stat", "file", "cmp", "diff", "colordiff", "comm",
    "printf", "echo", "true", "false", "pwd",
    "realpath", "readlink", "dirname", "basename",
    "sort", "uniq", "cut", "tr", "column", "join", "paste",
    "expand", "unexpand", "fold", "sed", "awk", "gawk", "nawk",
    "jq", "yq", "test", "date",
}

# Reader verbs that nonetheless have a documented "write my result out" flag.
# Scoped per verb so we do not misread an innocent flag on another tool
# (e.g. `grep -o` is only-matching, not an output-to-file write).
WRITE_FLAG_PREFIXES_BY_VERB = {
    "sed": ("-i", "--in-place"),
    "gsed": ("-i", "--in-place"),
    "sort": ("-o", "--output"),
}

_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_SHELL_OPERATORS = {"|", "||", "&&", ";", "&", "|&", "(", ")", "\n"}


def _block(reason):
    sys.stderr.write("INV-GOLDEN-01 guard: BLOCK -- %s\n" % reason)
    sys.exit(2)


def _allow():
    sys.exit(0)


def contains_marker(obj):
    """True if the ".approved" marker appears anywhere in the structure --
    in any string, at any depth (dict keys and values, list items)."""
    if isinstance(obj, str):
        return MARKER in obj.lower()
    if isinstance(obj, dict):
        for key, value in obj.items():
            if contains_marker(key) or contains_marker(value):
                return True
        return False
    if isinstance(obj, (list, tuple)):
        return any(contains_marker(item) for item in obj)
    return False


def _verb_of(token):
    """Bare command name, lowercased, path stripped."""
    return re.split(r"[\\/]", token)[-1].lower()


def command_is_provably_readonly(command):
    """Return (True, None) only if the command can be shown to be entirely
    read-only. Otherwise (False, reason). Default-deny: treat the command as a
    write unless every part of it is a recognised read-only operation."""
    # Command substitution can hide an arbitrary write we cannot see.
    if "`" in command or "$(" in command:
        return False, "command substitution could hide a write"

    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        return False, "command could not be parsed"

    # Any output redirection can create or overwrite a golden.
    for token in tokens:
        if ">" in token:
            return False, "output redirection can write a golden"

    # Split into pipeline / sequence stages; every stage must be a reader.
    stages = []
    current = []
    for token in tokens:
        if token in _SHELL_OPERATORS:
            if current:
                stages.append(current)
                current = []
        else:
            current.append(token)
    if current:
        stages.append(current)

    for stage in stages:
        index = 0
        # Skip leading environment assignments (FOO=bar cmd ...).
        while index < len(stage) and _ASSIGN_RE.match(stage[index]):
            index += 1
        if index >= len(stage):
            continue
        verb = _verb_of(stage[index])
        if verb not in READ_ONLY_VERBS:
            return False, "stage runs non-read-only command %r" % verb
        # Reader with a write-back flag is a writer.
        prefixes = WRITE_FLAG_PREFIXES_BY_VERB.get(verb)
        if prefixes:
            for flag in stage[index + 1:]:
                if any(flag == p or flag.startswith(p) for p in prefixes):
                    return False, "%r used with an output/in-place write flag" % verb

    return True, None


def decide(payload):
    """Given the parsed tool-call object, either allow (return) or block
    (never returns)."""
    if not isinstance(payload, dict):
        _block("input is not a JSON object")

    tool_name = payload.get("tool_name")
    if not isinstance(tool_name, str):
        _block("missing or non-string tool_name")

    name = tool_name.lower()
    tool_input = payload.get("tool_input")
    if tool_input is None:
        tool_input = {}

    # 1) Read-only tools: always allowed, even when they name a golden.
    if name in READ_ONLY_TOOLS:
        _allow()

    # 2) Shell / command tools: default-deny.
    if name in SHELL_TOOLS:
        command = tool_input.get("command") if isinstance(tool_input, dict) else None
        if isinstance(command, list):
            command = " ".join(str(part) for part in command)
        if not isinstance(command, str):
            # Cannot read the command. If a golden marker is anywhere in the
            # arguments we cannot prove the call safe, so block; otherwise
            # nothing golden is touched.
            if contains_marker(tool_input):
                _block("shell call without a readable command names a golden")
            _allow()
        if MARKER not in command.lower():
            # The command does not name a golden at all.
            _allow()
        ok, reason = command_is_provably_readonly(command)
        if ok:
            _allow()
        _block("shell command touches a golden: %s" % reason)

    # 3) Any other tool (including unknown, write-capable ones): if the marker
    # appears anywhere in the arguments, block. An unknown tool must not slip a
    # golden write through merely by being unknown.
    if contains_marker(tool_input):
        _block("tool %r references a golden in its arguments" % tool_name)

    _allow()


def main():
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except (ValueError, TypeError):
        _block("stdin was not valid JSON")
    decide(payload)


if __name__ == "__main__":
    main()
