"""Keyed record store with CRUD semantics (storage-free, single run).

Reads a JSON array of operations from stdin, prints a JSON array with one
result per operation in order, exits 0.
"""

import json
import sys

REQUIRED_FIELDS = {
    "create": ("key", "value"),
    "read": ("key",),
    "update": ("key", "value"),
    "delete": ("key",),
    "list": (),
}

BAD_OP = {"ok": False, "error": "bad op"}


def ok(result=None):
    return {"ok": True, "result": result}


def err(message):
    return {"ok": False, "error": message}


def apply_op(store, operation):
    if not isinstance(operation, dict):
        return dict(BAD_OP)

    op = operation.get("op")
    if not isinstance(op, str) or op not in REQUIRED_FIELDS:
        return dict(BAD_OP)

    for field in REQUIRED_FIELDS[op]:
        if field not in operation:
            return dict(BAD_OP)

    if op == "list":
        return ok(sorted(store.keys()))

    key = operation["key"]
    if not isinstance(key, str):
        return dict(BAD_OP)

    if op == "create":
        if key in store:
            return err("exists")
        store[key] = operation["value"]
        return ok(None)

    if op == "read":
        if key not in store:
            return err("missing")
        return ok(store[key])

    if op == "update":
        if key not in store:
            return err("missing")
        store[key] = operation["value"]
        return ok(None)

    # op == "delete"
    if key not in store:
        return err("missing")
    del store[key]
    return ok(None)


def main():
    raw = sys.stdin.read()

    try:
        operations = json.loads(raw)
    except Exception:
        print("ERROR")
        return

    if not isinstance(operations, list):
        print("ERROR")
        return

    if not all(isinstance(item, dict) for item in operations):
        print("ERROR")
        return

    store = {}
    results = [apply_op(store, operation) for operation in operations]
    print(json.dumps(results))


if __name__ == "__main__":
    main()
