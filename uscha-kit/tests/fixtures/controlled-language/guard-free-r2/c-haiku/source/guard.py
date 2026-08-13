#!/usr/bin/env python3
"""INV-GOLDEN-01 PreToolUse Guard: enforces fail-closed protection of approved golden files."""

import sys
import json
import re


def main():
    # AC-GH-07: Fail-closed on invalid input
    try:
        data = json.load(sys.stdin)
    except:
        sys.stderr.write("Invalid JSON input\n")
        sys.exit(2)

    # AC-GH-07: Fail-closed on wrong object shape
    if not isinstance(data, dict):
        sys.stderr.write("Input must be a JSON object\n")
        sys.exit(2)

    if "tool_name" not in data or "tool_input" not in data:
        sys.stderr.write("Missing tool_name or tool_input field\n")
        sys.exit(2)

    tool_name = str(data.get("tool_name", "")).lower()
    tool_input = data.get("tool_input")

    # AC-GH-07: Fail-closed on wrong tool_input type
    if not isinstance(tool_input, dict):
        sys.stderr.write("tool_input must be an object\n")
        sys.exit(2)

    # AC-GH-04: Read-only tools are always allowed
    read_only_tools = {
        "read",
        "grep",
        "glob",
        "webfetch",
        "websearch",
        "mcp__ccd_session__read_widget_context",
        "mcp__claude_browser__read_page",
        "mcp__claude_browser__read_console_messages",
        "mcp__claude_browser__read_network_requests",
        "mcp__claude_browser__get_page_text",
    }

    if tool_name in read_only_tools:
        sys.exit(0)

    # Helper: Check for .approved marker recursively (case-insensitive)
    def has_approved(obj):
        if isinstance(obj, str):
            return ".approved" in obj.lower()
        elif isinstance(obj, dict):
            return any(has_approved(v) for v in obj.values())
        elif isinstance(obj, (list, tuple)):
            return any(has_approved(item) for item in obj)
        return False

    # AC-GH-06: For non-shell tools, .approved anywhere in args blocks the call
    if tool_name not in {"bash", "powershell", "shell"}:
        if has_approved(tool_input):
            sys.stderr.write("Tool attempted to access approved golden file\n")
            sys.exit(2)
        sys.exit(0)

    # AC-GH-05: For shell/command tools, default-deny when .approved is mentioned
    command = tool_input.get("command", "")
    if not isinstance(command, str):
        sys.stderr.write("Command must be a string\n")
        sys.exit(2)

    # AC-GH-03: If no .approved mentioned, always allow
    if ".approved" not in command.lower():
        sys.exit(0)

    # Command names a .approved file — check if it's read-only

    # AC-GH-05: Block output redirection (>, >>, |)
    if ">" in command or "|" in command:
        sys.stderr.write("Output redirection or pipe with .approved file\n")
        sys.exit(2)

    # AC-GH-05: Block in-place edit flags (-i, -i.bak, -i~, etc.)
    if re.search(r"\s-i\b", command):
        sys.stderr.write("In-place edit flag with .approved file\n")
        sys.exit(2)

    # AC-GH-05: Default-deny unless proven read-only
    # Extract first token (the command name)
    tokens = command.strip().split()
    if tokens:
        first_cmd = tokens[0].lower()
        # Remove directory path components (Unix and Windows)
        first_cmd = first_cmd.replace("\\", "/").split("/")[-1]

        # Whitelist of commands that are definitively read-only
        read_only_commands = {
            "grep",
            "rg",
            "cat",
            "head",
            "tail",
            "wc",
            "sort",
            "uniq",
            "ls",
            "find",
            "pwd",
            "stat",
            "file",
            "git",
            "awk",
            "sed",
        }

        if first_cmd in read_only_commands:
            # AC-GH-03: Reading a .approved file is allowed
            sys.exit(0)

    # AC-GH-07: Cannot prove read-only, block (fail-closed)
    sys.stderr.write("Cannot prove command is read-only\n")
    sys.exit(2)


if __name__ == "__main__":
    main()
