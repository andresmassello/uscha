#!/usr/bin/env python3
"""INV-GOLDEN-01 PreToolUse guard.

Reads one JSON object from stdin describing a pending tool call and decides
whether it may proceed. Verdict is communicated ONLY through the process
exit code:
    0 -> ALLOW
    2 -> BLOCK (a short reason is written to stderr)

Fail-closed posture: any ambiguity, malformed input, or inability to prove a
call is read-only results in a BLOCK.
"""

import json
import re
import sys

MARKER = ".approved"

# Tools that cannot write by their nature. A call to one of these is always
# allowed, even when it names a .approved file, because reading field truth
# is the point. Matched case-insensitively against tool_name.
READ_ONLY_TOOLS = {
    "read",
    "grep",
    "glob",
    "ls",
    "webfetch",
    "websearch",
    "notebookread",
}

# The shell/command tool(s) this guard knows how to reason about textually.
SHELL_TOOLS = {"bash", "shell", "exec", "terminal"}

# Commands that are, by themselves and without an in-place/write flag or
# output redirection, read-only. This is a conservative allowlist: anything
# not on it is treated as unable to be proven safe.
READER_COMMANDS = {
    "cat", "less", "more", "head", "tail",
    "grep", "egrep", "fgrep", "rg", "ag", "ack",
    "find", "ls", "dir", "stat", "file", "wc",
    "diff", "comm", "cmp",
    "md5sum", "sha1sum", "sha256sum", "sha512sum", "cksum",
    "cut", "sort", "uniq", "tr", "column", "jq", "yq",
    "echo", "printf", "pwd", "basename", "dirname",
    "type", "which", "env", "true", "false",
    "xxd", "od", "hexdump", "strings", "tree",
    "realpath", "readlink",
}

# Commands that can never be proven read-only from text alone: general
# purpose interpreters/shells/writers whose real effect depends on script
# content, arguments assembled at runtime, or that are inherently mutating.
# Encountering any of these anywhere in the command is treated as "cannot
# be shown to be read-only" per the spec's default-deny rule.
NEVER_SAFE_COMMANDS = {
    "python", "python3", "python2", "node", "nodejs", "perl", "ruby",
    "php", "bash", "sh", "zsh", "ksh", "dash", "pwsh", "powershell",
    "cmd", "cmd.exe", "osascript", "eval",
    "cp", "mv", "rm", "touch", "mkdir", "rmdir", "tee", "dd", "install",
    "chmod", "chown", "xargs", "sponge", "git", "curl", "wget", "npm",
    "pip", "pip3", "make", "vim", "vi", "nano", "emacs", "code",
    "truncate", "patch",
}

# Segment separators for pipelines/sequences: |, &&, ||, ;, & (single).
# Applied outside of quoted strings only.
_SEGMENT_SPLIT_RE = re.compile(r"\|\||&&|[|;&]")

# Output-redirection detection: any '>' not part of a fd-duplication like
# '2>&1' or '1>&2'. A bare '>' or '>>' targeting a filename is a write.
_REDIRECT_RE = re.compile(r">(?!&)")

# In-place / output-write flags used by otherwise-reading tools
# (sed -i, perl -i, awk -i inplace, gawk --in-place, etc).
_INPLACE_FLAG_RE = re.compile(
    r"(?:^|\s)(-i\b|--in-place\b|-i\.[A-Za-z0-9]+|--in-place=)"
)

_ENV_ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


def block(reason):
    sys.stderr.write("INV-GOLDEN-01 guard: BLOCK - " + reason + "\n")
    sys.exit(2)


def allow():
    sys.exit(0)


def contains_marker(text):
    return MARKER in text.lower()


def scan_for_marker(value):
    """Recursively search any JSON-shaped structure for the golden marker,
    at any nesting depth, in any string (keys or values)."""
    if isinstance(value, str):
        return contains_marker(value)
    if isinstance(value, dict):
        for k, v in value.items():
            if isinstance(k, str) and contains_marker(k):
                return True
            if scan_for_marker(v):
                return True
        return False
    if isinstance(value, (list, tuple)):
        for item in value:
            if scan_for_marker(item):
                return True
        return False
    # numbers, bools, null: nothing to scan
    return False


def split_segments(command):
    """Split a shell command into pipeline/sequence segments on unquoted
    |, ||, &&, ;, & . Naive but quote-aware state machine."""
    segments = []
    current = []
    i = 0
    n = len(command)
    quote = None
    while i < n:
        ch = command[i]
        if quote:
            current.append(ch)
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in ("'", '"'):
            quote = ch
            current.append(ch)
            i += 1
            continue
        two = command[i:i + 2]
        if two in ("||", "&&"):
            segments.append("".join(current))
            current = []
            i += 2
            continue
        if ch in ("|", ";", "&"):
            segments.append("".join(current))
            current = []
            i += 1
            continue
        current.append(ch)
        i += 1
    segments.append("".join(current))
    return [s.strip() for s in segments if s.strip()]


def segment_command_name(segment):
    """Extract the leading command name of a pipeline segment, skipping
    env-var assignments and a leading 'sudo'."""
    tokens = segment.split()
    idx = 0
    while idx < len(tokens) and _ENV_ASSIGNMENT_RE.match(tokens[idx]):
        idx += 1
    if idx >= len(tokens):
        return None
    name = tokens[idx]
    if name == "sudo" and idx + 1 < len(tokens):
        name = tokens[idx + 1]
    # Strip a leading path (e.g. /usr/bin/cat -> cat) and any quotes.
    name = name.strip("'\"")
    name = name.replace("\\", "/").rsplit("/", 1)[-1]
    return name.lower()


def is_shell_command_provably_read_only(command):
    """Returns True only when every part of the command can be shown to be
    a read-only operation: no output redirection, no in-place write flags,
    and every pipeline/sequence stage's leading command is on the reader
    allowlist (and never on the never-safe list)."""
    if _REDIRECT_RE.search(command):
        return False
    if _INPLACE_FLAG_RE.search(command):
        return False

    segments = split_segments(command)
    if not segments:
        return False

    for segment in segments:
        name = segment_command_name(segment)
        if name is None:
            return False
        if name in NEVER_SAFE_COMMANDS:
            return False
        if name not in READER_COMMANDS:
            return False
    return True


def main():
    raw = sys.stdin.read()

    try:
        payload = json.loads(raw)
    except (ValueError, TypeError):
        block("stdin was not valid JSON")
        return

    if not isinstance(payload, dict):
        block("input JSON was not an object")
        return

    tool_name = payload.get("tool_name")
    tool_input = payload.get("tool_input")

    if not isinstance(tool_name, str):
        block("tool_name missing or not a string")
        return
    if tool_input is None:
        tool_input = {}
    if not isinstance(tool_input, dict):
        block("tool_input present but not an object")
        return

    tool_key = tool_name.strip().lower()

    # 1. Read-only tools are always allowed.
    if tool_key in READ_ONLY_TOOLS:
        allow()
        return

    # 2. Shell/command tools: default-deny, textual pipeline analysis.
    if tool_key in SHELL_TOOLS:
        command = tool_input.get("command")
        if not isinstance(command, str):
            # No command string to reason about textually: fall back to a
            # recursive marker scan of the whole tool_input, fail-closed.
            if scan_for_marker(tool_input):
                block("shell tool call with no inspectable 'command' string names a .approved path")
                return
            allow()
            return

        if not contains_marker(command):
            allow()
            return

        if is_shell_command_provably_read_only(command):
            allow()
            return

        block("shell command names a .approved path and cannot be proven read-only")
        return

    # 3. Any other tool (including unknown, write-capable tools): block if
    # the marker appears anywhere in the arguments, at any depth.
    if scan_for_marker(tool_input) or contains_marker(tool_name):
        block("tool arguments reference a .approved path via tool '%s'" % tool_name)
        return

    allow()


if __name__ == "__main__":
    main()
