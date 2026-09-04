import json
import re
import shlex
import sys

MARKER_RE = re.compile(r"\.approved", re.IGNORECASE)

READ_ONLY_TOOL_KEYS = {
    "read",
    "reader",
    "fileread",
    "filereader",
    "grep",
    "rg",
    "ripgrep",
    "glob",
    "ls",
    "list",
    "dir",
    "find",
    "search",
    "textsearch",
    "directorylisting",
    "listdirectory",
    "webfetch",
    "fetch",
    "websearch",
    "notebookread",
    "notebookreader",
    "todoread",
}

SHELL_TOOL_KEYS = {
    "bash",
    "shell",
    "sh",
    "command",
    "terminal",
    "cmd",
    "powershell",
    "pwsh",
    "runcommand",
    "exec",
}

READ_ONLY_COMMANDS = {
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
    "ripgrep",
    "findstr",
    "select-string",
    "ls",
    "dir",
    "gci",
    "get-childitem",
    "find",
    "wc",
    "sort",
    "uniq",
    "cut",
    "awk",
    "sed",
    "jq",
    "python",
    "python3",
    "py",
}

WRITER_COMMANDS = {
    "tee",
    "cp",
    "copy",
    "xcopy",
    "robocopy",
    "mv",
    "move",
    "ren",
    "rename",
    "rm",
    "remove-item",
    "del",
    "erase",
    "unlink",
    "touch",
    "mkdir",
    "md",
    "rmdir",
    "rd",
    "write-output",
    "out-file",
    "set-content",
    "add-content",
    "new-item",
    "format-inplace",
    "perl",
}

READ_ONLY_SHELL_BUILTINS = {
    "echo",
    "printf",
    "pwd",
    "cd",
    "test",
}

WRITE_FLAG_PATTERNS = (
    re.compile(r"^-[^-].*i"),
    re.compile(r"^--in-place(?:=.*)?$"),
    re.compile(r"^--inplace(?:=.*)?$"),
    re.compile(r"^--write(?:=.*)?$"),
    re.compile(r"^--write-back(?:=.*)?$"),
    re.compile(r"^--output(?:=.*)?$"),
    re.compile(r"^--out(?:=.*)?$"),
    re.compile(r"^-o.+"),
)

CONTROL_OPERATORS = {"|", "||", "&&", ";", "&", "(" , ")"}
REDIRECTION_RE = re.compile(r"(^|[^<])>>?|<<?|\d>>?|\d<")
ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


def block(reason):
    sys.stderr.write(reason + "\n")
    raise SystemExit(2)


def allow():
    raise SystemExit(0)


def normalized_name(value):
    return re.sub(r"[^a-z0-9]", "", value.lower())


def contains_marker(value):
    if isinstance(value, str):
        return MARKER_RE.search(value) is not None
    if isinstance(value, dict):
        return any(contains_marker(k) or contains_marker(v) for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return any(contains_marker(item) for item in value)
    return False


def shell_tokens(command):
    lexer = shlex.shlex(command, posix=True, punctuation_chars="|&;()<>")
    lexer.whitespace_split = True
    lexer.commenters = ""
    return list(lexer)


def has_redirection(command, tokens):
    if REDIRECTION_RE.search(command):
        return True
    return any(token in {">", ">>", "<", "<<"} or re.fullmatch(r"\d?>+|\d?<+", token) for token in tokens)


def command_basename(token):
    token = token.strip().strip('"\'')
    if not token:
        return ""
    token = token.replace("\\", "/")
    base = token.rsplit("/", 1)[-1].lower()
    for suffix in (".exe", ".cmd", ".bat", ".ps1"):
        if base.endswith(suffix):
            base = base[:-len(suffix)]
    return base


def split_stages(tokens):
    stages = []
    current = []
    for token in tokens:
        if token in CONTROL_OPERATORS:
            if current:
                stages.append(current)
                current = []
            if token in {"(", ")"}:
                return None
        elif token in {">", ">>", "<", "<<"} or re.fullmatch(r"\d?>+|\d?<+", token):
            return None
        else:
            current.append(token)
    if current:
        stages.append(current)
    return stages


def first_command_token(stage):
    index = 0
    while index < len(stage) and ASSIGNMENT_RE.match(stage[index]):
        index += 1
    if index >= len(stage):
        return ""
    if stage[index].lower() in {"env", "command"}:
        index += 1
        while index < len(stage) and (ASSIGNMENT_RE.match(stage[index]) or stage[index].startswith("-")):
            index += 1
    if index >= len(stage):
        return ""
    return stage[index]


def has_write_flag(command, args):
    command = command.lower()
    for arg in args:
        low = arg.lower()
        if any(pattern.match(low) for pattern in WRITE_FLAG_PATTERNS):
            return True
        if low in {"-i", "-ibak", "-i.bak", "/i", "/y"}:
            return True
    if command in {"sed", "perl"}:
        return any(arg.lower().startswith("-i") for arg in args)
    return False


def stage_is_read_only(stage):
    raw_command = first_command_token(stage)
    command = command_basename(raw_command)
    if not command:
        return False
    args = stage[stage.index(raw_command) + 1:] if raw_command in stage else stage[1:]
    if command in WRITER_COMMANDS:
        return False
    if has_write_flag(command, args):
        return False
    if command in READ_ONLY_COMMANDS or command in READ_ONLY_SHELL_BUILTINS:
        return True
    return False


def shell_command_is_read_only(command):
    if not MARKER_RE.search(command):
        return True
    try:
        tokens = shell_tokens(command)
    except ValueError:
        return False
    if not tokens:
        return False
    if has_redirection(command, tokens):
        return False
    stages = split_stages(tokens)
    if not stages:
        return False
    return all(stage_is_read_only(stage) for stage in stages)


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        block("blocked: invalid JSON input")

    if not isinstance(payload, dict):
        block("blocked: input must be a JSON object")

    tool_name = payload.get("tool_name")
    tool_input = payload.get("tool_input")
    if not isinstance(tool_name, str) or not isinstance(tool_input, dict):
        block("blocked: expected tool_name string and tool_input object")

    tool_key = normalized_name(tool_name)

    if tool_key in READ_ONLY_TOOL_KEYS:
        allow()

    if tool_key in SHELL_TOOL_KEYS:
        command = tool_input.get("command")
        if not isinstance(command, str):
            block("blocked: shell tool input lacks a command string")
        if shell_command_is_read_only(command):
            allow()
        block("blocked: shell command touches .approved and is not proven read-only")

    if contains_marker(tool_input):
        block("blocked: tool arguments touch .approved")

    allow()


if __name__ == "__main__":
    main()
