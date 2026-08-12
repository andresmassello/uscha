#!/usr/bin/env python3
"""INV-GOLDEN-01 PreToolUse guard.

Reads one JSON object from stdin describing a pending tool call and decides,
through the process exit code alone, whether that call may proceed:

  exit 0 -- ALLOW
  exit 2 -- BLOCK (a short reason is written to stderr)

The guard protects "approved goldens": any file whose name contains the
marker ".approved" (case-insensitive). A human is the sole author of such a
file (INV-GOLDEN-01) -- an agent may read one freely, but must never create,
edit, rename or delete one.

The guard fails closed: invalid input, an unrecognized shape, or any call
that cannot be proven read-only by a visible textual signal is BLOCKED.

Pure stdlib. Python 3.8+.
"""

import json
import re
import shlex
import sys

MARKER = ".approved"

# --- Tool name classification -------------------------------------------
#
# Read-only tools: cannot write by their nature (file reader, text search,
# directory listing, notebook reader, web fetch/search). Always allowed,
# even when they name a .approved file (AC-GH-04).
READ_ONLY_TOOLS = {
    "read",
    "grep",
    "glob",
    "ls",
    "list",
    "listdir",
    "search",
    "filesearch",
    "textsearch",
    "directorylisting",
    "webfetch",
    "websearch",
    "notebookread",
    "view",
    "cat",
}

# Shell / command tools: their argument is a command string whose effect
# must be reasoned about textually (AC-GH-05).
SHELL_TOOLS = {
    "bash",
    "shell",
    "exec",
    "execute",
    "executecommand",
    "command",
    "runcommand",
    "shellcommand",
    "terminal",
    "cmd",
    "powershell",
    "sh",
}

# --- Shell command classification ----------------------------------------
#
# Verbs that are writers regardless of flags -- a call naming a .approved
# file through one of these is always a write.
WRITE_VERBS = {
    "tee",
    "cp",
    "mv",
    "rm",
    "dd",
    "truncate",
    "install",
    "rename",
    "shred",
}

# Verbs that are readers by nature: no output redirection, no write flag ->
# always a reader for this guard's purposes.
READ_VERBS = {
    "cat",
    "type",
    "more",
    "less",
    "head",
    "tail",
    "grep",
    "egrep",
    "fgrep",
    "rg",
    "ls",
    "dir",
    "wc",
    "diff",
    "stat",
    "file",
    "echo",
    "printf",
    "pwd",
    "sort",
    "uniq",
    "cut",
    "awk",
    "which",
    "env",
    "printenv",
    "date",
    "whoami",
    "hostname",
    "tree",
    "du",
    "df",
    "basename",
    "dirname",
    "xxd",
    "od",
    "strings",
    "md5sum",
    "sha1sum",
    "sha256sum",
    "cksum",
}

# General-purpose interpreters / shells: readers UNLESS a visible write
# signal (redirection or a write flag) is present. Any write they perform
# through script/inline-expression contents is an indirect write, out of
# scope by design.
INTERPRETER_VERBS = {
    "python",
    "python3",
    "python2",
    "node",
    "nodejs",
    "ruby",
    "bash",
    "sh",
    "zsh",
    "ksh",
    "dash",
    "pwsh",
    "powershell",
}

# Verbs that are readers by default but become writers when a specific
# visible flag is present (an "in-place / output write flag" per spec).
WRITE_FLAG_VERBS = {
    "sed": ("-i", "--in-place"),
    "perl": ("-i",),
    "curl": ("-o", "-O", "--output"),
    "wget": ("-O", "--output-document"),
}

# Tokens that separate independent stages of a shell command line. A
# pipeline or sequence blocks if ANY stage is a writer.
STAGE_SEPARATORS = {"|", ";", "&&", "||", "&"}


def contains_marker(value):
    """Recursively search a JSON-decoded value for the .approved marker."""
    if isinstance(value, str):
        return MARKER in value.lower()
    if isinstance(value, dict):
        for k, v in value.items():
            if contains_marker(k) or contains_marker(v):
                return True
        return False
    if isinstance(value, (list, tuple)):
        return any(contains_marker(v) for v in value)
    return False


def _flag_matches(arg, flags):
    for f in flags:
        if arg == f:
            return True
        if f.startswith("--"):
            if arg.startswith(f + "="):
                return True
        elif len(f) == 2:
            # short flag, allow an attached suffix e.g. -i.bak, -ofile
            if arg.startswith(f) and len(arg) > len(f):
                return True
    return False


def _tokenize_command(command):
    """Tokenize a shell command line, splitting operators (|,;,&,>,<) out
    as their own tokens while respecting quoting. Returns None if the
    command cannot be parsed (unbalanced quotes etc.)."""
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        return list(lexer)
    except ValueError:
        return None


def _split_stages(tokens):
    stages = []
    current = []
    for t in tokens:
        if t in STAGE_SEPARATORS:
            stages.append(current)
            current = []
        else:
            current.append(t)
    stages.append(current)
    return [s for s in stages if s]


def _stage_verb_and_args(tokens):
    idx = 0
    # skip leading environment-variable assignments (VAR=value)
    while idx < len(tokens) and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tokens[idx]):
        idx += 1
    if idx < len(tokens) and tokens[idx] == "sudo":
        idx += 1
    if idx >= len(tokens):
        return None, []
    verb = tokens[idx]
    verb_base = verb.replace("\\", "/").rsplit("/", 1)[-1].lower()
    if verb_base.endswith(".exe"):
        verb_base = verb_base[:-4]
    return verb_base, tokens[idx + 1 :]


def _stage_is_reader(tokens):
    """A single pipeline/sequence stage is read-only only if it has no
    visible redirection and its verb is a recognised reader (with no
    matching write flag)."""
    if not tokens:
        return True
    # Any output redirection is a visible writing path.
    if ">" in tokens or ">>" in tokens:
        return False

    verb_base, args = _stage_verb_and_args(tokens)
    if verb_base is None:
        return True

    if verb_base in WRITE_VERBS:
        return False

    if verb_base in WRITE_FLAG_VERBS:
        flags = WRITE_FLAG_VERBS[verb_base]
        if any(_flag_matches(a, flags) for a in args):
            return False
        return True

    if verb_base in READ_VERBS or verb_base in INTERPRETER_VERBS:
        return True

    if verb_base == "find" and any(
        a in ("-delete", "-exec", "-execdir", "-fprint") for a in args
    ):
        return False

    # Unrecognized verb: cannot be proven read-only -> default deny.
    return False


def shell_command_is_read_only(command):
    """Top-level decision for a shell command string that names a
    .approved file: True only if every stage of the command (split on
    pipes/sequencing) is provably read-only."""
    tokens = _tokenize_command(command)
    if tokens is None:
        return False
    stages = _split_stages(tokens)
    if not stages:
        return True
    return all(_stage_is_reader(stage) for stage in stages)


def decide_shell(tool_input):
    command = None
    for key in ("command", "cmd", "script", "shell_command"):
        val = tool_input.get(key)
        if isinstance(val, str):
            command = val
            break

    if command is None:
        # No inspectable command text: fall back to a structural marker
        # search over the whole tool_input, fail-closed.
        if contains_marker(tool_input):
            return False, "shell tool call has no inspectable command text and references a .approved file"
        return True, ""

    if MARKER not in command.lower():
        return True, ""

    if shell_command_is_read_only(command):
        return True, ""
    return False, "shell command names a .approved file and cannot be proven read-only"


def decide_generic(tool_input):
    if contains_marker(tool_input):
        return False, "tool arguments reference a .approved file"
    return True, ""


def decide(tool_name, tool_input):
    name = tool_name.strip().lower()
    if name in READ_ONLY_TOOLS:
        return True, ""
    if name in SHELL_TOOLS:
        return decide_shell(tool_input)
    return decide_generic(tool_input)


def main():
    try:
        raw = sys.stdin.read()
    except Exception:
        sys.stderr.write("failed to read stdin\n")
        sys.exit(2)

    try:
        data = json.loads(raw)
    except Exception:
        sys.stderr.write("stdin is not valid JSON\n")
        sys.exit(2)

    if not isinstance(data, dict):
        sys.stderr.write("expected a JSON object on stdin\n")
        sys.exit(2)

    if "tool_name" not in data or "tool_input" not in data:
        sys.stderr.write("missing tool_name or tool_input field\n")
        sys.exit(2)

    tool_name = data.get("tool_name")
    tool_input = data.get("tool_input")

    if not isinstance(tool_name, str) or not tool_name.strip():
        sys.stderr.write("tool_name must be a non-empty string\n")
        sys.exit(2)

    if not isinstance(tool_input, dict):
        sys.stderr.write("tool_input must be an object\n")
        sys.exit(2)

    allowed, reason = decide(tool_name, tool_input)
    if not allowed:
        sys.stderr.write(reason + "\n")
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
