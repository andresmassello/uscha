#!/usr/bin/env python3
"""Portable Claude PreToolUse hook for INV-GOLDEN-01."""
import json
import sys


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return 0
    tool = payload.get("tool_name")
    target = ""
    if tool in {"Write", "Edit", "NotebookEdit", "MultiEdit"}:
        target = str(payload.get("tool_input", {}).get("file_path", ""))
    elif tool == "Bash":
        target = str(payload.get("tool_input", {}).get("command", ""))
    if ".approved" not in target:
        return 0
    print("BLOCKED by INV-GOLDEN-01: the agent may not write or rename an .approved golden. Emit a .received instead and stop for human approval.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
