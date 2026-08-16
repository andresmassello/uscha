"""Keyed record store — CRUD semantics over an in-memory map, storage-free.

Reads one JSON array of operations from stdin, prints one JSON array of results
(one per operation, in order) to stdout, exits 0. Malformed input prints ERROR.

Traceability: AC-CS-01..AC-CS-06, INV-CS-STRICT-01.
"""

import json
import sys

OK_NULL = {"ok": True, "result": None}


def _err(reason):
    return {"ok": False, "error": reason}


def _bad_op():
    # AC-CS-06: unknown op, or an op missing a field its verb requires.
    return _err("bad op")


def _apply(store, operation):
    """Run one operation against the store, returning its result object.

    INV-CS-STRICT-01: a failed operation is a value, never an exception that
    aborts the batch. Every path through here returns a result object.
    """
    if not isinstance(operation, dict):
        return _bad_op()

    op = operation.get("op")
    if not isinstance(op, str):
        return _bad_op()

    if op == "list":
        # AC-CS-05: current keys, lexicographic order.
        return {"ok": True, "result": sorted(store.keys())}

    key = operation.get("key")
    if not isinstance(key, str):
        return _bad_op()

    if op == "create":
        # AC-CS-01: create is not upsert. Absence of "value" is a bad op, but a
        # present-and-null "value" is a legitimate JSON value to store.
        if "value" not in operation:
            return _bad_op()
        if key in store:
            return _err("exists")
        store[key] = operation["value"]
        return dict(OK_NULL)

    if op == "read":
        # AC-CS-02
        if key not in store:
            return _err("missing")
        return {"ok": True, "result": store[key]}

    if op == "update":
        # AC-CS-03: update never inserts.
        if "value" not in operation:
            return _bad_op()
        if key not in store:
            return _err("missing")
        store[key] = operation["value"]
        return dict(OK_NULL)

    if op == "delete":
        # AC-CS-04: after removal the key is free again for create.
        if key not in store:
            return _err("missing")
        del store[key]
        return dict(OK_NULL)

    return _bad_op()


def main():
    raw = sys.stdin.read()
    try:
        operations = json.loads(raw)
    except Exception:
        print("ERROR")
        return

    # AC-CS-06: the batch itself must be an array; anything else is ERROR.
    if not isinstance(operations, list):
        print("ERROR")
        return

    store = {}
    results = [_apply(store, operation) for operation in operations]
    print(json.dumps(results))


if __name__ == "__main__":
    main()
