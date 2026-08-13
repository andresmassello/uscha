#!/usr/bin/env python3
"""
INV-GOLDEN PreToolUse guard: reads JSON from stdin, exits 0 to allow or 2 to block.

Protects approved golden files (.approved marker, case-insensitive) from being written.
Allows read-only tool calls. Defaults to deny for unknown/shell tools.

Implements AC-GH-01 through AC-GH-07 and INV-GOLDEN-01.
"""

import sys
import json
import re


# Recognized read-only tools (case-insensitive)
READ_ONLY_TOOLS = {
    "read",
    "glob",
    "grep",
    "webfetch",
    "websearch",
    "toolsearch",
    "notebookedit",
    "mcp__ccd_session__list_events",
    "mcp__ccd_session__search_session_transcripts",
    "mcp__ccd_session__list_sessions",
    "mcp__ccd_session__get_session",
    "mcp__ccd_session_mgmt__list_events",
    "mcp__ccd_session_mgmt__search_session_transcripts",
    "mcp__ccd_session_mgmt__list_sessions",
    "mcp__ccd_session_mgmt__get_session",
    "mcp__claude_browser__read_page",
    "mcp__claude_browser__read_console_messages",
    "mcp__claude_browser__read_network_requests",
    "mcp__claude_browser__get_page_text",
    "mcp__claude_browser__tabs_context",
    "mcp__claude_browser__preview_list",
    "mcp__claude_browser__preview_logs",
    "mcp__claude-in-chrome__read_page",
    "mcp__claude-in-chrome__read_console_messages",
    "mcp__claude-in-chrome__read_network_requests",
    "mcp__claude-in-chrome__get_page_text",
    "mcp__claude-in-chrome__list_connected_browsers",
    "mcp__visualize__read_me",
    "mcp__plugin_engram_engram__mem_search",
    "mcp__plugin_engram_engram__mem_get_observation",
    "mcp__plugin_engram_engram__mem_context",
    "mcp__plugin_engram_engram__mem_current_project",
    "mcp__plugin_engram_engram__mem_review",
}

APPROVED_MARKER = ".approved"


def is_approved_golden(text: str) -> bool:
    """Check if text contains .approved marker (case-insensitive)."""
    if not isinstance(text, str):
        return False
    return APPROVED_MARKER.lower() in text.lower()


def is_read_only_tool(tool_name: str) -> bool:
    """Check if tool is recognized as read-only (AC-GH-04)."""
    return tool_name.lower() in READ_ONLY_TOOLS


def is_shell_tool(tool_name: str) -> bool:
    """Check if tool is a shell/command tool."""
    return tool_name.lower() in ("bash",)


def has_write_signal(command: str) -> bool:
    """Check if command has visible write signals (redirection, write flags, etc)."""
    if not command:
        return False

    # Output redirection: > >> |
    if re.search(r'>>?\s*\S|\|\s*\S', command):
        return True

    # In-place edit flags: -i, --in-place
    if re.search(r'\s-i\b|\s--in-place\b|\s--inplace\b', command):
        return True

    # Output/file write flags: -o, --out, --output, --file
    if re.search(r'\s-o\b|\s--out\b|\s--output\b|\s--file\b', command):
        return True

    return False


def looks_like_reader_only(command: str) -> bool:
    """Check if command looks like it only reads (visible reader signals)."""
    if not command:
        return False

    reader_patterns = [
        r'\bcat\b',
        r'\bgrep\b',
        r'\brg\b',
        r'\bls\b',
        r'\beza\b',
        r'\bfind\b',
        r'\bhead\b',
        r'\btail\b',
        r'\bwc\b',
        r'\bfile\b',
        r'\bstat\b',
    ]

    return any(re.search(pattern, command, re.IGNORECASE) for pattern in reader_patterns)


def contains_marker_anywhere(obj) -> bool:
    """Recursively check if APPROVED_MARKER appears anywhere in nested structure."""
    if isinstance(obj, str):
        return is_approved_golden(obj)
    elif isinstance(obj, dict):
        for key, value in obj.items():
            if contains_marker_anywhere(key) or contains_marker_anywhere(value):
                return True
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            if contains_marker_anywhere(item):
                return True
    return False


def check_shell_command(command: str) -> tuple[bool, str]:
    """
    Check a shell/bash command for write operations on approved goldens.
    Returns (allowed: bool, reason: str)

    AC-GH-05: Shell default-deny (redirection, write flag, writer pipeline stage).
    """
    if not command:
        return False, "Shell command is empty"

    # If mentions an approved golden
    if is_approved_golden(command):
        # Block if has write signals (redirection, output flags, etc.)
        if has_write_signal(command):
            return False, "Shell command writes to approved golden file"

        # If is a pipeline, check each stage
        if "|" in command:
            stages = command.split("|")
            for stage in stages:
                stage = stage.strip()
                if has_write_signal(stage):
                    return False, "Shell pipeline stage has write signal on approved golden"

        # If cannot prove it's a reader, block (fail-closed)
        if not looks_like_reader_only(command):
            return False, "Cannot prove command only reads approved golden"

        return True, ""

    # General shell command: if it looks like a write and we can't prove otherwise, deny
    if has_write_signal(command):
        return False, "Shell command has write signal (default-deny)"

    # If looks like a reader, allow
    if looks_like_reader_only(command):
        return True, ""

    # Default deny for shell commands (fail-closed)
    return False, "Shell command cannot be proven safe (default-deny)"


def check_tool_call(tool_name: str, tool_input: dict) -> tuple[bool, str]:
    """
    Check if tool call is allowed.
    Returns (allowed: bool, reason: str)

    Implements:
    - AC-GH-02: create/edit/rename/delete marker file -> block
    - AC-GH-03: read-only of marker file -> allow
    - AC-GH-04: read-only tools always allowed
    - AC-GH-05: shell default-deny
    - AC-GH-06: unknown tool with marker -> block
    """

    # AC-GH-04: Read-only tools are ALWAYS allowed
    if is_read_only_tool(tool_name):
        return True, ""

    # AC-GH-05: Shell/command tools (default-deny)
    if is_shell_tool(tool_name):
        command = tool_input.get("command", "")
        return check_shell_command(command)

    # AC-GH-06: Unknown tools that mention marker anywhere in arguments
    if contains_marker_anywhere(tool_input):
        return False, f"Tool references approved golden file (marker in arguments)"

    # AC-GH-02: Check for write-ish tool names with approved golden in file_path
    write_tool_names = {"write", "edit", "agent"}
    if any(wt in tool_name.lower() for wt in write_tool_names):
        if "file_path" in tool_input:
            if is_approved_golden(tool_input["file_path"]):
                return False, "Tool would write approved golden file"

    # Unknown tools: fail-closed (INV-GOLDEN-01)
    return False, f"Unknown tool (fail-closed)"


def main():
    """Main entry point: read JSON from stdin, validate, exit with verdict."""
    try:
        # AC-GH-01: Read JSON from stdin
        input_text = sys.stdin.read()
        if not input_text or not input_text.strip():
            sys.stderr.write("No input provided\n")
            sys.exit(2)
        data = json.loads(input_text)
    except json.JSONDecodeError:
        # AC-GH-07: fail-closed on non-JSON
        sys.stderr.write("Invalid JSON input\n")
        sys.exit(2)
    except Exception:
        # AC-GH-07: fail-closed on any read error
        sys.stderr.write("Error reading input\n")
        sys.exit(2)

    # AC-GH-07: fail-closed on wrong shape
    if not isinstance(data, dict):
        sys.stderr.write("Input must be a JSON object\n")
        sys.exit(2)

    if "tool_name" not in data or "tool_input" not in data:
        sys.stderr.write("Input must contain 'tool_name' and 'tool_input'\n")
        sys.exit(2)

    tool_name = data.get("tool_name")
    tool_input = data.get("tool_input")

    if not isinstance(tool_name, str):
        sys.stderr.write("'tool_name' must be a string\n")
        sys.exit(2)

    if not isinstance(tool_input, dict):
        sys.stderr.write("'tool_input' must be an object\n")
        sys.exit(2)

    # Check the tool call
    allowed, reason = check_tool_call(tool_name, tool_input)

    # AC-GH-01: Exit 0 to allow, 2 to block; reason to stderr on block
    if allowed:
        sys.exit(0)
    else:
        if reason:
            sys.stderr.write(reason + "\n")
        sys.exit(2)


if __name__ == "__main__":
    main()
