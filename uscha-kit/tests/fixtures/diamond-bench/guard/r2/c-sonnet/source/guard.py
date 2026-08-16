"""INV-GOLDEN-01 PreToolUse guard.

Reads one JSON object from stdin describing a pending tool call and decides,
purely through the process exit code, whether that call may proceed:

  exit 0 -- ALLOW
  exit 2 -- BLOCK (a short reason is written to stderr)

The guard protects "approved goldens": any file whose name contains the
case-insensitive marker ".approved". A human is the sole author of such a
file -- an agent may read one freely, but must never create, edit, rename or
delete one. See the canonical package for the full specification.

Pure standard library. Python 3.8+.
"""

import json
import os
import re
import shlex
import sys

APPROVED_MARKER = ".approved"

# Tools that cannot write by their nature: reading a file, searching text,
# listing a directory, fetching/searching the web, reading a notebook. Always
# allowed, even when they name an approved golden -- reading field truth is
# legitimate. Matched case-insensitively against tool_name.
READ_ONLY_TOOLS = {
    "read",
    "readfile",
    "read_file",
    "grep",
    "search",
    "search_files",
    "grep_search",
    "glob",
    "glob_file_search",
    "list_files",
    "ls",
    "list_dir",
    "list_directory",
    "directory_list",
    "webfetch",
    "web_fetch",
    "websearch",
    "web_search",
    "notebookread",
    "notebook_read",
    "find",
}

# Tools that are shell/command tools by name even when their call happens to
# carry no "command" argument this time. Matched case-insensitively.
SHELL_TOOL_NAMES = {
    "bash",
    "shell",
    "sh",
    "exec",
    "execute",
    "execute_command",
    "run_command",
    "terminal",
    "powershell",
    "cmd",
}

# Base commands recognised as read-only when invoked with no write flag and
# no output redirection. Anything not on this list cannot be shown to be
# read-only, so a stage that runs it is treated as a write (default-deny).
READERS = {
    "cat", "less", "more", "head", "tail",
    "grep", "egrep", "fgrep", "rg", "ag",
    "find", "fd", "ls", "dir",
    "wc", "diff", "cmp", "file", "stat",
    "md5sum", "sha1sum", "sha256sum", "sha512sum", "cksum",
    "echo", "printf", "type", "which", "pwd",
    "basename", "dirname", "readlink", "realpath",
    "xxd", "od", "hexdump", "strings",
    "jq", "awk", "sed", "tree", "du", "nl", "tac",
    "sort", "uniq", "cut", "tr", "column",
}

# For these, "-i" / "--ignore-case" means case-insensitive matching, not
# in-place write -- unlike sed/perl/awk where "-i" rewrites the file.
GREP_LIKE = {"grep", "egrep", "fgrep", "rg", "ag"}

# Flags treated as "this reader is being told to write its result out"
# rather than to standard output.
WRITE_FLAG_EXACT = {"-i", "-o", "-w", "--write", "--in-place"}
WRITE_FLAG_PREFIXES = ("-i.", "--in-place=", "--output", "-o=")

_ENV_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=.*$")
_REDIRECTION = re.compile(r"[12]?>>?|&>")
_STAGE_SPLIT = re.compile(r"&&|\|\||[;|\n]")


def block(reason):
    sys.stderr.write("BLOCK: " + reason + "\n")
    sys.exit(2)


def allow():
    sys.exit(0)


def has_approved_marker(text):
    return APPROVED_MARKER in text.lower()


def contains_approved(obj):
    """Recursively search arbitrary JSON-shaped arguments for the marker."""
    if isinstance(obj, str):
        return has_approved_marker(obj)
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(key, str) and has_approved_marker(key):
                return True
            if contains_approved(value):
                return True
        return False
    if isinstance(obj, list) or isinstance(obj, tuple):
        return any(contains_approved(item) for item in obj)
    return False


def stage_base_command(tokens):
    idx = 0
    while idx < len(tokens) and _ENV_ASSIGNMENT.match(tokens[idx]):
        idx += 1
    if idx >= len(tokens):
        return None, []
    base = tokens[idx]
    base_name = os.path.basename(base).lower()
    if base_name.endswith(".exe"):
        base_name = base_name[:-4]
    return base_name, tokens[idx + 1:]


def stage_is_write(stage_text):
    """True if this single pipeline stage cannot be proven read-only."""
    if _REDIRECTION.search(stage_text):
        return True
    try:
        tokens = shlex.split(stage_text, posix=True)
    except ValueError:
        # Unbalanced quotes etc: cannot parse, so cannot prove safe.
        return True
    if not tokens:
        return False
    base_name, rest = stage_base_command(tokens)
    if base_name is None:
        return True
    if base_name not in READERS:
        return True
    grep_like = base_name in GREP_LIKE
    for tok in rest:
        if grep_like and tok in ("-i", "--ignore-case"):
            continue
        if tok in WRITE_FLAG_EXACT:
            return True
        if tok.startswith(WRITE_FLAG_PREFIXES):
            return True
    return False


def shell_command_is_write(command):
    """True if the shell command cannot be proven read-only w.r.t. goldens."""
    if not has_approved_marker(command):
        return False  # nothing approved is named; not this guard's concern
    stages = _STAGE_SPLIT.split(command)
    for stage in stages:
        stage = stage.strip()
        if not stage:
            continue
        if stage_is_write(stage):
            return True
    return False


def main():
    try:
        raw = sys.stdin.read()
    except Exception:
        block("could not read standard input")
        return

    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        block("standard input is not valid JSON")
        return

    if not isinstance(data, dict):
        block("top-level JSON input must be an object")
        return

    tool_name = data.get("tool_name")
    tool_input = data.get("tool_input")

    if not isinstance(tool_name, str) or not tool_name.strip():
        block("missing or malformed tool_name")
        return
    if not isinstance(tool_input, dict):
        block("missing or malformed tool_input")
        return

    name_lower = tool_name.strip().lower()

    # Read-only tools: always allowed, even if they name an approved golden.
    if name_lower in READ_ONLY_TOOLS:
        allow()
        return

    command = tool_input.get("command")

    is_shell_tool = name_lower in SHELL_TOOL_NAMES or isinstance(command, str)

    if is_shell_tool:
        if isinstance(command, str):
            if shell_command_is_write(command):
                block("shell command names an approved golden and cannot be proven read-only")
                return
            allow()
            return
        # Named as a shell tool but no usable command string was supplied:
        # fall back to the conservative generic scan below.
        if contains_approved(tool_input):
            block("shell-type tool call has no readable command; approved marker present in arguments")
            return
        allow()
        return

    # Any other tool, including unknown write-capable ones: block if the
    # approved marker appears anywhere in the arguments, at any depth.
    if contains_approved(tool_input):
        block("approved marker found in arguments of a non-read-only tool")
        return

    allow()


if __name__ == "__main__":
    main()
