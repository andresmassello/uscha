import json
import re
import shlex
import sys

MARKER = ".approved"

READ_ONLY_TOOLS = {
    "read",
    "fileread",
    "grep",
    "glob",
    "ls",
    "list",
    "find",
    "search",
    "webfetch",
    "websearch",
    "notebookread",
}

SHELL_TOOLS = {
    "bash",
    "sh",
    "shell",
    "cmd",
    "command",
    "terminal",
    "powershell",
    "pwsh",
}

READ_ONLY_COMMANDS = {
    "cat",
    "type",
    "more",
    "less",
    "head",
    "tail",
    "sed",
    "awk",
    "grep",
    "egrep",
    "fgrep",
    "rg",
    "ripgrep",
    "find",
    "ls",
    "dir",
    "tree",
    "wc",
    "sort",
    "uniq",
    "cut",
    "tr",
    "strings",
    "file",
    "stat",
    "test",
    "where",
    "where.exe",
    "which",
    "select-string",
    "get-content",
    "gc",
    "dir",
    "gci",
    "get-childitem",
}

WRITE_COMMANDS = {
    "tee",
    "cp",
    "copy",
    "xcopy",
    "move",
    "mv",
    "ren",
    "rename",
    "rm",
    "del",
    "erase",
    "unlink",
    "touch",
    "mkdir",
    "rmdir",
    "write-output",
    "out-file",
    "set-content",
    "add-content",
    "new-item",
    "remove-item",
    "move-item",
    "copy-item",
    "rename-item",
    "python",
    "python3",
    "py",
    "perl",
    "ruby",
    "node",
}

WRITE_FLAGS = {
    "-i",
    "--in-place",
    "--inplace",
    "-w",
    "--write",
    "--write-file",
    "--output",
    "--out-file",
    "--outfile",
    "-o",
    "/out",
    "/outfile",
}

SEGMENT_OPERATORS = {"|", "&&", "||", ";"}
REDIRECTION_RE = re.compile(r"(^|[^<])>(?!>)|>>|<>")


def block(reason):
    sys.stderr.write(reason + "\n")
    return 2


def normalize_name(name):
    return re.sub(r"[^a-z0-9]", "", name.lower())


def has_marker_text(value):
    return MARKER in value.lower()


def contains_marker(value):
    if isinstance(value, str):
        return has_marker_text(value)
    if isinstance(value, list):
        return any(contains_marker(item) for item in value)
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str) and has_marker_text(key):
                return True
            if contains_marker(item):
                return True
    return False


def split_executable(token):
    token = token.strip('"\'')
    token = token.replace("\\", "/")
    base = token.rsplit("/", 1)[-1]
    lower = base.lower()
    if lower.endswith(".exe"):
        lower = lower[:-4]
    return lower


def command_has_redirection(command):
    return bool(REDIRECTION_RE.search(command))


def shell_tokens(command):
    lexer = shlex.shlex(command, posix=False)
    lexer.whitespace_split = True
    lexer.commenters = ""
    lexer.wordchars += ".-/:\\"
    return list(lexer)


def split_segments(tokens):
    segments = []
    current = []
    for token in tokens:
        if token in SEGMENT_OPERATORS:
            if not current:
                return None
            segments.append(current)
            current = []
        else:
            current.append(token)
    if current:
        segments.append(current)
    return segments


def token_is_assignment_write(token):
    lower = token.lower()
    if not has_marker_text(lower):
        return False
    if "=" not in token:
        return False
    name = token.split("=", 1)[0].lower().lstrip("-/")
    return name in {"out", "output", "outfile", "path", "literalpath", "destination", "target"}


def segment_is_read_only(segment):
    if not segment:
        return False

    executable = split_executable(segment[0])
    if executable in WRITE_COMMANDS:
        return False
    if executable not in READ_ONLY_COMMANDS:
        return False

    previous = ""
    for token in segment[1:]:
        lower = token.lower().strip('"\'')
        if token in SEGMENT_OPERATORS:
            return False
        if lower in WRITE_FLAGS:
            return False
        if any(lower.startswith(flag + "=") for flag in WRITE_FLAGS):
            return False
        if previous.lower().strip('"\'') in WRITE_FLAGS:
            return False
        if token_is_assignment_write(token):
            return False
        previous = token

    return True


def shell_command_is_read_only(command):
    if not isinstance(command, str) or not command.strip():
        return False
    if not has_marker_text(command):
        return True
    if command_has_redirection(command):
        return False
    try:
        tokens = shell_tokens(command)
    except Exception:
        return False
    if not tokens:
        return False
    segments = split_segments(tokens)
    if not segments:
        return False
    return all(segment_is_read_only(segment) for segment in segments)


def decide(payload):
    if not isinstance(payload, dict):
        return block("blocked: input is not a JSON object")

    tool_name = payload.get("tool_name")
    tool_input = payload.get("tool_input")
    if not isinstance(tool_name, str) or not isinstance(tool_input, dict):
        return block("blocked: expected tool_name string and tool_input object")

    normalized = normalize_name(tool_name)

    if normalized in READ_ONLY_TOOLS:
        return 0

    if normalized in SHELL_TOOLS:
        command = tool_input.get("command")
        if shell_command_is_read_only(command):
            return 0
        if isinstance(command, str) and has_marker_text(command):
            return block("blocked: shell command may write an approved golden")
        return 0

    if contains_marker(tool_input):
        return block("blocked: unknown or write-capable tool touches an approved golden")

    return 0


def main():
    try:
        payload = json.loads(sys.stdin.read())
        return decide(payload)
    except SystemExit:
        raise
    except Exception:
        return block("blocked: invalid or unreadable guard input")


if __name__ == "__main__":
    sys.exit(main())
