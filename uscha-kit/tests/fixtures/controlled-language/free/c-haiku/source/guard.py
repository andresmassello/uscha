#!/usr/bin/env python3
"""
INV-GOLDEN-01 PreToolUse Guard

Enforces that approved golden files (.approved) can only be read, not written.
Exits 0 to allow, 2 to block. Fail-closed on any uncertainty.
"""

import json
import sys

def is_approved_marker(text: str) -> bool:
    """Check if text contains .approved marker (case-insensitive)."""
    return '.approved' in text.lower()


def contains_approved_anywhere(obj, depth=0, max_depth=50):
    """Recursively check if .approved appears anywhere in an object."""
    if depth > max_depth:
        return False

    if isinstance(obj, str):
        return is_approved_marker(obj)
    elif isinstance(obj, dict):
        for value in obj.values():
            if contains_approved_anywhere(value, depth + 1, max_depth):
                return True
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            if contains_approved_anywhere(item, depth + 1, max_depth):
                return True

    return False


def is_read_only_tool(tool_name: str) -> bool:
    """Return True if tool is read-only by nature."""
    read_only = {
        'read',
        'grep',
        'glob',
        'monitor',
        'webfetch',
        'websearch',
    }
    return tool_name.lower() in read_only


def is_bash_command_safe(command: str) -> bool:
    """
    Check if bash command that mentions .approved is read-only.
    Conservative: prove it's safe or block. Out-of-scope: symlinks,
    indirection, scripts, runtime filename assembly.
    """
    # Reject if there's output redirection
    if '>' in command:
        return False

    # Reject if there are pipes (full stage analysis is out-of-scope)
    if '|' in command:
        return False

    # Reject if there are in-place edit flags
    if '-i' in command or '--in-place' in command:
        return False

    # Check if command starts with a known read-only verb
    cmd_stripped = command.lstrip()
    if not cmd_stripped:
        return False

    cmd_start = cmd_stripped.split()[0].lower()

    # Verbs that are definitively read-only (output to stdout only)
    read_only_verbs = {
        'cat', 'grep', 'rg', 'head', 'tail', 'less', 'more', 'sort', 'uniq',
        'wc', 'file', 'stat', 'od', 'hexdump', 'strings', 'ls', 'eza', 'fd',
        'find', 'locate', 'which', 'type', 'command', 'whereis', 'git',
    }

    return cmd_start in read_only_verbs


def main():
    """Main guard logic."""
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.stderr.write("Invalid JSON\n")
        sys.exit(2)

    # Validate input is an object
    if not isinstance(input_data, dict):
        sys.stderr.write("Input must be a JSON object\n")
        sys.exit(2)

    tool_name = input_data.get('tool_name')
    tool_input = input_data.get('tool_input')

    # Validate tool_name
    if not isinstance(tool_name, str):
        sys.stderr.write("tool_name must be a string\n")
        sys.exit(2)

    # Normalize tool_input
    if tool_input is None:
        tool_input = {}
    elif not isinstance(tool_input, dict):
        sys.stderr.write("tool_input must be a JSON object\n")
        sys.exit(2)

    # Read-only tools always allowed, even if they mention .approved
    if is_read_only_tool(tool_name):
        sys.exit(0)

    # Bash/shell: default-deny; block unless command is proven read-only
    if tool_name.lower() in ('bash', 'shell'):
        command = tool_input.get('command', '')
        if not isinstance(command, str):
            sys.stderr.write("command must be a string\n")
            sys.exit(2)

        if is_approved_marker(command):
            if not is_bash_command_safe(command):
                sys.stderr.write("Cannot write to .approved file\n")
                sys.exit(2)
        sys.exit(0)

    # Any other tool (unknown, write-capable): block if .approved appears
    # anywhere in arguments at any nesting depth
    if contains_approved_anywhere(tool_input):
        sys.stderr.write("Cannot modify .approved file\n")
        sys.exit(2)

    # Allowed
    sys.exit(0)


if __name__ == '__main__':
    main()
