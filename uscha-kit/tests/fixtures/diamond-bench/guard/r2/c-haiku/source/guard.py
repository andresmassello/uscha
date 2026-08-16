#!/usr/bin/env python3
"""
INV-GOLDEN PreToolUse Guard (Diamond M4 bootstrap subsystem)

Enforces INV-GOLDEN-01: an agent may never create, edit, rename or delete
an approved golden file. Humans are the sole authors.

Process contract:
  - Reads one JSON object from stdin describing a tool call
  - Exit 0 = ALLOW the call
  - Exit 2 = BLOCK the call (short reason on stderr)

Pure stdlib, Python 3.8+.
"""

import json
import sys
from typing import Any

# Curated set of tools that are provably read-only by design
READ_ONLY_TOOLS = {
    'Read',
    'Grep',
    'Glob',
    'ToolSearch',
    'WebFetch',
    'WebSearch',
    'mcp__Claude_Browser__read_page',
    'mcp__Claude_Browser__read_console_messages',
    'mcp__Claude_Browser__read_network_requests',
    'mcp__Claude_Browser__get_page_text',
    'mcp__Claude_Browser__find',
    'mcp__Claude_Browser__screenshot',
    'mcp__Claude_Browser__tabs_context',
    'mcp__Claude_Browser__preview_list',
    'mcp__Claude_Browser__preview_logs',
    'Monitor',
}


def has_approved_marker(s: str) -> bool:
    """Check if a string contains the .approved marker (case-insensitive)."""
    return '.approved' in s.lower()


def find_approved_in_tree(obj: Any) -> bool:
    """
    Recursively search for .approved marker at any depth in an object tree.

    Handles: strings, dicts, lists, tuples.
    Returns True if the marker is found anywhere.
    """
    if isinstance(obj, str):
        return has_approved_marker(obj)
    elif isinstance(obj, dict):
        for value in obj.values():
            if find_approved_in_tree(value):
                return True
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            if find_approved_in_tree(item):
                return True
    return False


def is_read_only_command(command: str) -> bool:
    """
    Determine if a shell command can be proven read-only.

    Fail-closed: returns False if there is any doubt.
    Blocks:
      - Output redirection (>, >>)
      - Pipes (|) - conservative: any pipeline might write
      - Known write operations (rm, mv, cp, sed, git, etc.)
    """
    # Output redirection is a write
    if '>' in command:
        return False

    # Pipes are conservative-blocked (any stage might write)
    if '|' in command:
        return False

    # Known write operations and flags
    write_patterns = [
        'rm ', 'rmdir ', 'del ', 'move ', 'mv ',
        'copy ', 'cp ', 'sed ', 'awk ',
        'chmod ', 'chown ', 'mkdir ', 'touch ',
        'echo ', 'printf ',
        'git add ', 'git commit ', 'git push ',
        'git reset ', 'git checkout ', 'git rm ', 'git mv ',
    ]

    cmd_lower = command.lower()
    for pattern in write_patterns:
        if pattern in cmd_lower:
            return False

    return True


def guard() -> int:
    """
    Execute the INV-GOLDEN-01 guard logic.

    Returns:
      0 if the tool call is safe (ALLOW)
      2 if the tool call should be blocked (BLOCK)
    """

    # Read and parse JSON from stdin
    try:
        tool_call = json.load(sys.stdin)
    except (json.JSONDecodeError, Exception):
        sys.stderr.write("BLOCK: invalid JSON input\n")
        return 2

    # Validate input object shape
    if not isinstance(tool_call, dict):
        sys.stderr.write("BLOCK: input must be a JSON object\n")
        return 2

    if 'tool_name' not in tool_call or 'tool_input' not in tool_call:
        sys.stderr.write("BLOCK: input missing required fields\n")
        return 2

    tool_name = tool_call['tool_name']
    tool_input = tool_call['tool_input']

    # Validate field types
    if not isinstance(tool_name, str):
        sys.stderr.write("BLOCK: tool_name must be string\n")
        return 2

    if not isinstance(tool_input, dict):
        sys.stderr.write("BLOCK: tool_input must be object\n")
        return 2

    # Check: is this a read-only tool? (case-insensitive match)
    if any(tool_name.lower() == ro.lower() for ro in READ_ONLY_TOOLS):
        # Read-only tools are always allowed
        return 0

    # Check: is this a bash/shell tool?
    if tool_name.lower() in ('bash', 'shell', 'sh'):
        # Bash tools are default-deny if they reference .approved

        if 'command' not in tool_input:
            sys.stderr.write("BLOCK: bash tool missing command\n")
            return 2

        command = tool_input['command']

        if not isinstance(command, str):
            sys.stderr.write("BLOCK: command must be string\n")
            return 2

        # If command names .approved, it must be provably read-only
        if has_approved_marker(command):
            if not is_read_only_command(command):
                sys.stderr.write(
                    "BLOCK: bash command references .approved "
                    "and is not read-only\n"
                )
                return 2

        # Otherwise bash command is OK
        return 0

    # Check: unknown/other tool
    # These are conservative-denied if .approved appears anywhere
    if find_approved_in_tree(tool_input):
        sys.stderr.write(
            f"BLOCK: '{tool_name}' references .approved file\n"
        )
        return 2

    # No .approved marker found, tool is safe
    return 0


if __name__ == '__main__':
    sys.exit(guard())
