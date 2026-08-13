#!/usr/bin/env python3
"""INV-GOLDEN-01 PreToolUse guard.

Reads one JSON object describing a pending tool call on stdin and signals its
verdict through the process exit code only:

    exit 0 -> ALLOW   the tool call may proceed
    exit 2 -> BLOCK   the tool call must not proceed (reason on stderr)

The guard protects "approved goldens": files whose name carries the ``.approved``
marker. A human is the sole author of such a file. Reads are allowed; every
writing path the guard can recognise is blocked. The posture is fail-closed:
unparsable input, unexpected shape, or an unprovable call all block.

This guard inspects the tool call as text/structure only. It is a guardrail
against accident and casual shortcut, not a sandbox.

Pure stdlib, Python 3.8+.
"""

import json
import re
import shlex
import sys

# --------------------------------------------------------------------------
# The marker
# --------------------------------------------------------------------------

MARKER = ".approved"

ALLOW = 0
BLOCK = 2


def has_marker(text):
    """True when the ``.approved`` marker appears in ``text`` (case-insensitive)."""
    if not isinstance(text, str):
        return False
    return MARKER in text.lower()


# --------------------------------------------------------------------------
# Tool families
# --------------------------------------------------------------------------

# Tools that cannot write by their nature. A call to one of these is always
# allowed, even when it names a golden: reading field truth is the point.
READ_ONLY_TOOLS = frozenset(
    {
        "read",
        "readfile",
        "read_file",
        "view",
        "cat",
        "grep",
        "search",
        "glob",
        "find",
        "ls",
        "list",
        "listdir",
        "list_dir",
        "list_files",
        "notebookread",
        "notebook_read",
        "webfetch",
        "web_fetch",
        "fetch",
        "websearch",
        "web_search",
    }
)

# Shell / command tools: their argument is an arbitrary command line, so they
# get the dedicated default-deny command analysis.
SHELL_TOOLS = frozenset(
    {
        "bash",
        "sh",
        "shell",
        "zsh",
        "cmd",
        "powershell",
        "pwsh",
        "run",
        "runcommand",
        "run_command",
        "execute",
        "exec",
        "terminal",
    }
)


# --------------------------------------------------------------------------
# Shell command analysis
# --------------------------------------------------------------------------

# Commands that only read. Anything not on this list is treated as a writer.
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
        "file",
        "stat",
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
        "tree",
        "find",
        "fd",
        "diff",
        "cmp",
        "comm",
        "md5sum",
        "sha1sum",
        "sha256sum",
        "shasum",
        "cksum",
        "sort",
        "uniq",
        "cut",
        "column",
        "type",
        "echo",
        "printf",
        "pwd",
        "which",
        "basename",
        "dirname",
        "realpath",
        "readlink",
        "jq",
        "yq",
        "git",  # narrowed below: only read-only subcommands survive
    }
)

# Read-only ``git`` subcommands. Any other subcommand makes git a writer.
GIT_READ_ONLY_SUBCOMMANDS = frozenset(
    {
        "status",
        "log",
        "show",
        "diff",
        "blame",
        "branch",
        "cat-file",
        "ls-files",
        "ls-tree",
        "rev-parse",
        "describe",
        "grep",
        "shortlog",
        "reflog",
        "config",  # only without a write; handled by flag scan below
    }
)

# Flags that make an otherwise-reading tool write its result back out.
IN_PLACE_FLAGS = frozenset(
    {
        "-i",
        "--in-place",
        "-w",
        "--write",
        "--write-changes",
        "--fix",
        "--fix-in-place",
        "--inplace",
        "-o",
        "--output",
        "--output-file",
        "--out",
        "--out-file",
        "-O",
        "--remote-name",
        "--save",
        "--overwrite",
        "--replace",
        "-p",  # patch/apply style writers
    }
)

# Redirection operators: a command that redirects its output to a file can
# create or overwrite a golden.
REDIRECT_RE = re.compile(r"(?<![0-9<>])>|>>|>\||<>|&>|\d+>")

# Separators that split a command line into independently-executed stages.
STAGE_SEPARATORS = ("|", "||", "&&", ";", "\n", "&")


def _split_stages(command):
    """Split a command line into stages on pipes and sequencing operators.

    Purely textual and deliberately crude: the point is that EVERY stage must
    be provably read-only, so an over-split (extra stages) can only make the
    guard stricter, never laxer.
    """
    stages = []
    current = []
    quote = None
    i = 0
    n = len(command)
    while i < n:
        ch = command[i]
        if quote:
            current.append(ch)
            if ch == quote:
                quote = None
            elif ch == "\\" and i + 1 < n:
                i += 1
                current.append(command[i])
            i += 1
            continue
        if ch in ("'", '"'):
            quote = ch
            current.append(ch)
            i += 1
            continue
        if ch == "\\" and i + 1 < n:
            current.append(ch)
            i += 1
            current.append(command[i])
            i += 1
            continue
        if ch in ("|", "&", ";", "\n"):
            # consume a run of the operator characters
            stages.append("".join(current))
            current = []
            while i < n and command[i] in ("|", "&", ";", "\n"):
                i += 1
            continue
        current.append(ch)
        i += 1
    if quote:
        # Unbalanced quoting: we cannot analyse this reliably.
        return None
    stages.append("".join(current))
    return [s for s in stages if s.strip()]


def _tokenize(stage):
    """Best-effort POSIX tokenization of one stage; None when unparsable."""
    try:
        return shlex.split(stage, posix=True)
    except ValueError:
        return None


def _strip_path(word):
    """Reduce ``/usr/bin/cat`` or ``C:\\bin\\cat.exe`` to ``cat``."""
    base = word.replace("\\", "/").rsplit("/", 1)[-1]
    if base.lower().endswith(".exe"):
        base = base[:-4]
    return base.lower()


def _has_redirection(stage):
    """True when the raw stage text carries an output redirection.

    Quoted regions are skipped so that ``grep '>' file`` is not a redirect.
    """
    quote = None
    i = 0
    n = len(stage)
    while i < n:
        ch = stage[i]
        if quote:
            if ch == quote:
                quote = None
            elif ch == "\\" and i + 1 < n:
                i += 1
            i += 1
            continue
        if ch in ("'", '"'):
            quote = ch
            i += 1
            continue
        if ch == "\\" and i + 1 < n:
            i += 2
            continue
        if ch == ">":
            return True
        i += 1
    return False


def _stage_is_read_only(stage):
    """True only when this single stage can be PROVEN read-only."""
    if _has_redirection(stage):
        return False

    tokens = _tokenize(stage)
    if not tokens:
        return False

    # Command substitution / expansion hides a whole other command line.
    for tok in tokens:
        if "$(" in tok or "`" in tok or "${" in tok:
            return False

    # Skip leading environment assignments (FOO=bar cmd ...) and simple
    # prefixes that do not change the writing nature of what follows.
    idx = 0
    while idx < len(tokens):
        tok = tokens[idx]
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tok):
            idx += 1
            continue
        if _strip_path(tok) in ("env", "command", "nohup", "time", "sudo", "doas"):
            idx += 1
            continue
        break
    if idx >= len(tokens):
        return False

    argv = tokens[idx:]
    name = _strip_path(argv[0])

    if name not in READ_ONLY_COMMANDS:
        return False

    # An in-place / output-write flag turns a reader into a writer.
    for tok in argv[1:]:
        low = tok.lower()
        if low in IN_PLACE_FLAGS:
            return False
        # long flags carrying a value, e.g. --output=x.approved
        if low.startswith("--"):
            head = low.split("=", 1)[0]
            if head in IN_PLACE_FLAGS:
                return False
        # bundled short flags, e.g. -ni for sed
        elif low.startswith("-") and len(low) > 1 and not low.startswith("--"):
            for chunk in low[1:]:
                if ("-" + chunk) in IN_PLACE_FLAGS:
                    return False

    if name == "git":
        sub = None
        for tok in argv[1:]:
            if tok.startswith("-"):
                continue
            sub = tok.lower()
            break
        if sub is None or sub not in GIT_READ_ONLY_SUBCOMMANDS:
            return False
        if sub == "config":
            # `git config key value` writes; only reads are allowed.
            rest = [t for t in argv[1:] if not t.startswith("-")][1:]
            if len(rest) > 1:
                return False

    return True


def command_is_read_only(command):
    """True only when EVERY stage of the command line is provably read-only."""
    if not isinstance(command, str) or not command.strip():
        return False
    stages = _split_stages(command)
    if not stages:
        return False
    for stage in stages:
        if not _stage_is_read_only(stage):
            return False
    return True


# --------------------------------------------------------------------------
# Generic argument walk
# --------------------------------------------------------------------------


def marker_anywhere(value):
    """True when the marker appears anywhere in a nested value."""
    stack = [value]
    seen = 0
    while stack:
        seen += 1
        if seen > 100000:  # pathological input: fail closed
            return True
        item = stack.pop()
        if isinstance(item, str):
            if has_marker(item):
                return True
        elif isinstance(item, dict):
            for key, sub in item.items():
                if isinstance(key, str) and has_marker(key):
                    return True
                stack.append(sub)
        elif isinstance(item, (list, tuple)):
            stack.extend(item)
    return False


def collect_command(tool_input):
    """Pull the command line out of a shell tool's arguments."""
    if not isinstance(tool_input, dict):
        return None
    for key in ("command", "cmd", "command_line", "script"):
        value = tool_input.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, list) and all(isinstance(p, str) for p in value):
            return " ".join(value)
    return None


# --------------------------------------------------------------------------
# The decision
# --------------------------------------------------------------------------


def decide(payload):
    """Return (exit_code, reason). ``reason`` is empty when allowing."""
    if not isinstance(payload, dict):
        return BLOCK, "INV-GOLDEN-01: input is not a JSON object; blocking (fail-closed)."

    tool_name = payload.get("tool_name")
    if not isinstance(tool_name, str) or not tool_name.strip():
        return BLOCK, "INV-GOLDEN-01: missing or invalid 'tool_name'; blocking (fail-closed)."

    tool_input = payload.get("tool_input", {})
    if tool_input is None:
        tool_input = {}
    if not isinstance(tool_input, (dict, list)):
        return BLOCK, "INV-GOLDEN-01: 'tool_input' is not an object; blocking (fail-closed)."

    name = tool_name.strip().lower()

    # 1. Read-only tools: always allowed, marker or not.
    if name in READ_ONLY_TOOLS:
        return ALLOW, ""

    # 2. Shell / command tools: default-deny on the command text.
    if name in SHELL_TOOLS:
        command = collect_command(tool_input)
        if command is None:
            # A shell call we cannot read: block only if a golden is named
            # anywhere in its arguments; otherwise it cannot touch one by name.
            if marker_anywhere(tool_input):
                return (
                    BLOCK,
                    "INV-GOLDEN-01: shell call names an approved golden but its "
                    "command could not be read; blocking (fail-closed).",
                )
            return ALLOW, ""
        if not has_marker(command):
            return ALLOW, ""
        if command_is_read_only(command):
            return ALLOW, ""
        return (
            BLOCK,
            "INV-GOLDEN-01: command names an approved golden (.approved) and "
            "could not be proven read-only; a human is the sole author of an "
            "approved golden.",
        )

    # 3. Any other tool, including unknown write-capable ones: conservative.
    if marker_anywhere(tool_input):
        return (
            BLOCK,
            "INV-GOLDEN-01: tool '%s' references an approved golden (.approved) "
            "in its arguments; agents may not create, edit, rename or delete "
            "an approved golden." % tool_name,
        )

    return ALLOW, ""


def main():
    try:
        raw = sys.stdin.read()
    except Exception:
        sys.stderr.write("INV-GOLDEN-01: could not read stdin; blocking (fail-closed).\n")
        return BLOCK

    try:
        payload = json.loads(raw)
    except Exception:
        sys.stderr.write("INV-GOLDEN-01: stdin is not valid JSON; blocking (fail-closed).\n")
        return BLOCK

    try:
        code, reason = decide(payload)
    except Exception:
        sys.stderr.write(
            "INV-GOLDEN-01: guard could not evaluate the call; blocking (fail-closed).\n"
        )
        return BLOCK

    if code != ALLOW:
        sys.stderr.write(reason.rstrip() + "\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
