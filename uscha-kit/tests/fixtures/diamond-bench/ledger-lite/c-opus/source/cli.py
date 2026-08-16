"""The entry point: stdin -> shape validation -> model.post -> stdout.

Owns I/O and SHAPE only (ADR-001, INV-LG-SEAM-01). It never computes a balance
and never decides acceptance; that is the model's.
"""

import json
import sys

import model


def _is_int(value):
    # JSON booleans are Python bools, and bool is a subclass of int: not integers.
    return isinstance(value, int) and not isinstance(value, bool)


def _valid_line(line):
    if not isinstance(line, dict):
        return False
    if not isinstance(line.get("account"), str) or "account" not in line:
        return False
    if "amount" not in line or not _is_int(line["amount"]):
        return False
    return True


def _valid_posting(posting):
    if not isinstance(posting, dict):
        return False
    if "id" not in posting or not isinstance(posting["id"], str):
        return False
    if "lines" not in posting or not isinstance(posting["lines"], list):
        return False
    return all(_valid_line(line) for line in posting["lines"])


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        print("ERROR")
        return

    if not isinstance(data, list) or not all(_valid_posting(p) for p in data):
        print("ERROR")
        return

    balances, rejected = model.post(data)
    print(json.dumps({"balances": balances, "rejected": rejected}))


if __name__ == "__main__":
    main()
