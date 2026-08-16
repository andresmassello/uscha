#!/usr/bin/env python3
"""INV-GOLDEN-01 PreToolUse guard.

Reads one JSON object describing a pending tool call from stdin and decides
whether it may proceed. The verdict travels ONLY through the exit code:

    exit 0 -> ALLOW
    exit 2 -> BLOCK (a short reason is written to stderr)

A human is the sole author of an approved golden: a file whose name carries the
``.approved`` marker. Reads of a golden are legitimate; every writing path the
guard can recognise is blocked. The guard fails CLOSED: unparsable input, an
unexpected shape, or any call that cannot be proven read-only blocks.

Scope: this is a text/structure decision, not a sandbox. Indirect writes (a
script whose contents are never seen, a filename assembled at runtime, a
symlink, a child process) are out of reach by design.
"""

import json
import re
import shlex
import sys

ALLOW = 0
BLOCK = 2

# The golden marker. Matched case-insensitively: the filesystems this runs on
# (Windows, macOS) are.
MARKER = ".approved"

# Tools that cannot write by their nature. A call to one of these is always
# allowed, even when it names a golden. Matched case-insensitively.
READ_ONLY_TOOLS = frozenset(
    {
        "read",
        "glob",
        "grep",
        "ls",
        "list",
        "search",
        "websearch",
        "webfetch",
        "fetch",
        "notebookread",
        "todoread",
    }
)

# Shell tools whose arguments are a free-form command line.
SHELL_TOOLS = frozenset({"bash", "sh", "shell", "zsh", "powershell", "pwsh", "cmd", "run"})

# Shell commands that only read. Anything not on this list is treated as a
# writer -- default-deny.
READ_ONLY_COMMANDS = frozenset(
    {
        "cat",
        "bat",
        "head",
        "tail",
        "less",
        "more",
        "nl",
        "od",
        "xxd",
        "hexdump",
        "strings",
        "wc",
        "grep",
        "egrep",
        "fgrep",
        "rg",
        "ag",
        "ack",
        "ls",
        "eza",
        "exa",
        "dir",
        "find",
        "fd",
        "stat",
        "file",
        "du",
        "df",
        "diff",
        "cmp",
        "md5sum",
        "sha1sum",
        "sha256sum",
        "shasum",
        "cksum",
        "echo",
        "printf",
        "pwd",
        "which",
        "type",
        "basename",
        "dirname",
        "realpath",
        "readlink",
        "sort",
        "uniq",
        "cut",
        "tr",
        "column",
        "jq",
        "yq",
        "awk",
        "gawk",
        "python",
        "python3",
        "node",
        "git",
    }
)

# Commands from READ_ONLY_COMMANDS that are only read-only for a subset of their
# subcommands. Anything else they are asked to do counts as a write.
SUBCOMMAND_ALLOWLIST = {
    "git": frozenset(
        {
            "show",
            "log",
            "diff",
            "status",
            "cat-file",
            "ls-files",
            "ls-tree",
            "blame",
            "rev-parse",
            "describe",
            "grep",
            "shortlog",
            "branch",
            "remote",
            "config",
        }
    ),
}

# Write flags on otherwise-reading tools: the flags editors and formatters use
# to write their result back out instead of to the screen.
WRITE_FLAGS = frozenset(
    {
        "-i",
        "--in-place",
        "-o",
        "--output",
        "--output-file",
        "--write",
        "-w",
        "--write-out",
        "--fix",
        "--fix-in-place",
        "--replace",
        "--save",
        "--outfile",
        "-O",
        "--remote-name",
    }
)

# Any of these characters in a command means it is more than one command, or it
# redirects. Handled by the splitter / redirection scan below.
REDIRECT_RE = re.compile(r"(?<![0-9<>])>{1,2}|[0-9]>&?|<>|>\|")

# Shell metacharacters that split a command line into stages.
SEPARATOR_TOKENS = frozenset({"|", "||", "&&", ";", "&", "|&"})


def has_marker(text):
    """True when the golden marker appears anywhere in ``text``."""
    return MARKER in text.lower()


def walk_strings(value):
    """Yield every string reachable in ``value`` at any nesting depth."""
    stack = [value]
    while stack:
        item = stack.pop()
        if isinstance(item, str):
            yield item
        elif isinstance(item, dict):
            for key, val in item.items():
                if isinstance(key, str):
                    yield key
                stack.append(val)
        elif isinstance(item, (list, tuple)):
            stack.extend(item)


def marker_anywhere(value):
    """True when the marker appears in any string inside ``value``."""
    for text in walk_strings(value):
        if has_marker(text):
            return True
    return False


def split_stages(tokens):
    """Split a token list into stages on shell separators."""
    stages = []
    current = []
    for token in tokens:
        if token in SEPARATOR_TOKENS:
            stages.append(current)
            current = []
        else:
            current.append(token)
    stages.append(current)
    return [stage for stage in stages if stage]


def tokenize(command):
    """Best-effort POSIX tokenization. Returns None when it cannot be parsed."""
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        return list(lexer)
    except ValueError:
        return None


def strip_env_prefix(stage):
    """Drop leading VAR=value assignments and env/command wrappers."""
    index = 0
    while index < len(stage):
        token = stage[index]
        if re.match(r"^[A-Za-z_][A-Za-z_0-9]*=", token):
            index += 1
            continue
        base = token.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].lower()
        if base in ("env", "command", "nohup", "time", "sudo", "doas", "builtin", "exec"):
            index += 1
            continue
        break
    return stage[index:]


def stage_is_read_only(stage):
    """True only when every part of this single command stage reads."""
    stage = strip_env_prefix(stage)
    if not stage:
        # An empty stage after stripping wrappers is not provably read-only.
        return False

    program = stage[0].rsplit("/", 1)[-1].rsplit("\\", 1)[-1].lower()
    # Strip a Windows-style extension so cat.exe matches cat.
    for suffix in (".exe", ".cmd", ".bat", ".ps1"):
        if program.endswith(suffix):
            program = program[: -len(suffix)]
            break

    if program not in READ_ONLY_COMMANDS:
        return False

    allowed_subcommands = SUBCOMMAND_ALLOWLIST.get(program)
    if allowed_subcommands is not None:
        subcommand = None
        for token in stage[1:]:
            if not token.startswith("-"):
                subcommand = token.lower()
                break
        if subcommand is None or subcommand not in allowed_subcommands:
            return False

    for token in stage[1:]:
        flag = token.split("=", 1)[0]
        if flag in WRITE_FLAGS:
            return False

    return True


def command_is_read_only(command):
    """Default-deny: True only when the whole command line is provably read-only."""
    # Any output redirection writes a file, no matter what precedes it.
    if REDIRECT_RE.search(command):
        return False

    # Command substitution and process substitution hide arbitrary commands.
    if "$(" in command or "`" in command or ">(" in command:
        return False

    tokens = tokenize(command)
    if tokens is None:
        # Unparsable command line: cannot prove it safe.
        return False

    stages = split_stages(tokens)
    if not stages:
        return False

    # Every stage of a pipeline or sequence must read; it is not enough for the
    # command to merely START with a reader.
    for stage in stages:
        if not stage_is_read_only(stage):
            return False

    return True


def decide(payload):
    """Return (exit_code, reason). reason is empty when allowing."""
    if not isinstance(payload, dict):
        return BLOCK, "guard: input is not a JSON object (fail-closed)"

    tool_name = payload.get("tool_name")
    if not isinstance(tool_name, str):
        return BLOCK, "guard: missing or non-string 'tool_name' (fail-closed)"

    tool_input = payload.get("tool_input", {})
    if tool_input is None:
        tool_input = {}
    if not isinstance(tool_input, dict):
        return BLOCK, "guard: 'tool_input' is not an object (fail-closed)"

    name = tool_name.strip().lower()

    # Read-only tools cannot write by their nature: reading field truth is the
    # point of a golden.
    if name in READ_ONLY_TOOLS:
        return ALLOW, ""

    if name in SHELL_TOOLS:
        command = tool_input.get("command", "")
        if not isinstance(command, str):
            # A shell call whose command is not a string cannot be inspected.
            if marker_anywhere(tool_input):
                return BLOCK, (
                    "INV-GOLDEN-01: shell call touches a .approved golden and its "
                    "command could not be inspected (fail-closed)"
                )
            return ALLOW, ""
        if not has_marker(command) and not marker_anywhere(tool_input):
            return ALLOW, ""
        if command_is_read_only(command):
            return ALLOW, ""
        return BLOCK, (
            "INV-GOLDEN-01: command names a .approved golden and could not be "
            "proven read-only; a human is the sole author of an approved golden"
        )

    # Any other tool -- including a write-capable tool this guard has never
    # heard of. The marker anywhere in the arguments, at any depth, blocks.
    if marker_anywhere(tool_input):
        return BLOCK, (
            "INV-GOLDEN-01: tool '%s' references a .approved golden; an agent may "
            "not create, edit, rename or delete field truth" % tool_name
        )

    return ALLOW, ""


def main():
    try:
        raw = sys.stdin.read()
    except Exception:
        sys.stderr.write("guard: could not read stdin (fail-closed)\n")
        return BLOCK

    try:
        payload = json.loads(raw)
    except Exception:
        sys.stderr.write("guard: stdin is not valid JSON (fail-closed)\n")
        return BLOCK

    code, reason = decide(payload)
    if code != ALLOW and reason:
        sys.stderr.write(reason + "\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
