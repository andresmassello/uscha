#!/usr/bin/env python3
"""INV-GOLDEN-01 PreToolUse guard.

Reads one JSON object describing a pending tool call on stdin and signals its
verdict solely through the process exit code:

    exit 0  -> ALLOW   the tool call may proceed
    exit 2  -> BLOCK   the tool call must not proceed (reason on stderr)

The single invariant enforced: an agent may never create, edit, rename or delete
an *approved golden* -- a file whose name carries the marker ``.approved``.
Reading such a file is legitimate and is allowed. The guard fails closed.

Pure stdlib, Python 3.8+. See SPEC.md / ACCEPTANCE.md / CONSTITUTION.md.
"""

import json
import re
import shlex
import sys

# The marker that identifies an approved golden. Matched case-insensitively
# because the filesystems this runs on (Windows, macOS) are.
MARKER = ".approved"

# Tools that cannot write by their nature. A call to one of these is always
# allowed, even when it names a .approved file. Matched case-insensitively.
READ_ONLY_TOOLS = {
    "read",          # file reader
    "grep",          # text search
    "glob",          # path search
    "ls",            # directory listing
    "notebookread",  # notebook reader
    "webfetch",      # web fetch
    "websearch",     # web search
}

# Shell / command tools whose argument is a command line to be analysed.
SHELL_TOOLS = {"bash", "sh", "shell"}

# --- shell command classification -----------------------------------------

# Recognised writer verbs: their visible effect is to create / modify / rename
# / delete a file. Presence of one in a stage that names a golden blocks.
WRITERS = {
    "tee", "cp", "mv", "rm", "dd", "install", "ln", "touch", "mkdir",
    "rmdir", "truncate", "shred", "patch", "unlink", "mktemp", "rsync",
}

# Recognised read-only verbs. A stage whose verb is one of these performs no
# visible write (redirections / write flags are checked separately).
READERS = {
    "cat", "grep", "egrep", "fgrep", "rg", "ag", "head", "tail", "less",
    "more", "ls", "dir", "find", "awk", "sed", "sort", "uniq", "wc", "diff",
    "cmp", "od", "xxd", "hexdump", "stat", "file", "echo", "printf", "cut",
    "tr", "tac", "nl", "column", "jq", "yq", "comm", "strings", "basename",
    "dirname", "realpath", "readlink", "test", "true", "pwd", "date", "which",
    "type", "fold", "rev", "paste", "join", "expand", "unexpand",
}

# General-purpose interpreters / shells. Invoked WITHOUT an output redirection
# and WITHOUT a write flag these are read-only for this guard: any write they
# perform is an indirect write (script / inline expression contents the guard
# cannot inspect), which is out of scope by design.
INTERPRETERS = {
    "python", "python2", "python3", "node", "nodejs", "ruby", "perl", "bash",
    "sh", "zsh", "fish", "dash", "ksh", "php", "lua", "rscript", "deno",
    "bun", "tclsh", "groovy",
}

# Command wrappers to skip past when resolving a stage's real verb.
WRAPPERS = {
    "sudo", "doas", "env", "command", "nice", "nohup", "stdbuf", "ionice",
}

# Tokens that separate a command line into stages / sub-commands.
OPERATORS = {"|", "||", "&&", ";", "&", "(", ")", "\n"}

ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


def block(reason):
    sys.stderr.write("BLOCKED (INV-GOLDEN-01): " + reason + "\n")
    sys.exit(2)


def allow():
    sys.exit(0)


def has_marker_str(text):
    return MARKER in text.lower()


def contains_marker(obj):
    """True if the marker appears anywhere in a nested structure -- keys,
    values, list items, at any depth."""
    if isinstance(obj, str):
        return has_marker_str(obj)
    if isinstance(obj, dict):
        for key, value in obj.items():
            if contains_marker(key) or contains_marker(value):
                return True
        return False
    if isinstance(obj, (list, tuple)):
        return any(contains_marker(item) for item in obj)
    return False


def tokenize(cmd):
    """Tokenise a shell command line, keeping operators and redirections as
    their own tokens. Returns a list, or None if the command cannot be parsed
    (unbalanced quotes, etc.) -- an unparseable command that names a golden is
    treated fail-closed by the caller."""
    try:
        lex = shlex.shlex(cmd, posix=True, punctuation_chars="();<>|&")
        lex.whitespace_split = True
        return list(lex)
    except ValueError:
        return None


def resolve_verb(words):
    """The effective command verb of a stage, skipping leading VAR=val
    assignments and known wrappers. Returns a lowercase basename, or None."""
    for word in words:
        if ASSIGN_RE.match(word):
            continue
        base = word.replace("\\", "/").rsplit("/", 1)[-1].lower()
        if base in WRAPPERS:
            continue
        return base
    return None


def has_write_flag(verb, words):
    """A visible in-place / output write flag on this stage."""
    for word in words[1:]:
        low = word.lower()
        if low == "--in-place" or low.startswith("--in-place="):
            return True
        if low == "--output" or low.startswith("--output="):
            return True
    # sed / perl -i (and -i.bak, combined short clusters like -ni) mean the
    # tool rewrites its input file in place.
    if verb in ("sed", "perl"):
        for word in words[1:]:
            if word.startswith("-") and not word.startswith("--"):
                if "i" in word[1:]:
                    return True
    return False


def decide_shell(cmd):
    """Default-deny classification of a shell command that may touch a golden.
    Allows only when every visible path is read-only."""
    if not has_marker_str(cmd):
        allow()  # command does not name a golden -> nothing to protect

    tokens = tokenize(cmd)
    if tokens is None:
        block("shell command names an approved golden and cannot be parsed")

    # Walk tokens: split into stages, and inspect redirections as we go.
    stages = []
    current = []
    i = 0
    n = len(tokens)
    while i < n:
        tok = tokens[i]
        if ">" in tok:
            # Output redirection (>, >>, >&, 1>, 2> ...). The target file is the
            # next word token; writing it as a golden is a write.
            j = i + 1
            while j < n and tokens[j] in OPERATORS:
                j += 1
            if j < n:
                target = tokens[j]
                if has_marker_str(target):
                    block("output redirection writes an approved golden")
                i = j + 1
            else:
                i += 1
            continue
        if tok == "<":
            # Input redirection: reading is legitimate; skip its target.
            i += 2
            continue
        if tok in OPERATORS:
            if current:
                stages.append(current)
                current = []
            i += 1
            continue
        current.append(tok)
        i += 1
    if current:
        stages.append(current)

    # Every stage must be provably read-only, else block (default-deny).
    for words in stages:
        if not words:
            continue
        verb = resolve_verb(words)
        if verb is None:
            block("command shape naming an approved golden is not read-only")
        if verb in WRITERS:
            block("writer command '%s' targets an approved golden" % verb)
        if has_write_flag(verb, words):
            block("write flag on '%s' rewrites an approved golden" % verb)
        if verb in READERS or verb in INTERPRETERS:
            continue
        # Unknown verb: cannot be shown to be read-only -> block.
        block("command '%s' cannot be proven read-only over an approved golden"
              % verb)

    allow()


def main():
    raw = sys.stdin.read()

    # Fail closed on anything that is not the expected JSON object shape.
    try:
        payload = json.loads(raw)
    except Exception:
        block("input on stdin is not valid JSON")

    if not isinstance(payload, dict):
        block("input is valid JSON but not an object")

    tool_name = payload.get("tool_name")
    if not isinstance(tool_name, str):
        block("input object has no valid 'tool_name'")

    tool_input = payload.get("tool_input", {})
    name = tool_name.strip().lower()

    # Read-only tools: always allowed, even when they name a golden.
    if name in READ_ONLY_TOOLS:
        allow()

    # Shell / command tools: analyse the command string, default-deny.
    if name in SHELL_TOOLS:
        command = ""
        if isinstance(tool_input, dict):
            candidate = tool_input.get("command")
            if isinstance(candidate, str):
                command = candidate
        elif isinstance(tool_input, str):
            command = tool_input
        decide_shell(command)  # exits

    # Any other tool -- including unknown, write-capable ones. If the marker
    # appears anywhere in the arguments, block.
    if contains_marker(tool_input):
        block("tool '%s' would touch an approved golden" % tool_name)

    allow()


if __name__ == "__main__":
    main()
