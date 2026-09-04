import json
import sys


def _bad_op():
    return {"ok": False, "error": "bad op"}


def _ok_null():
    return {"ok": True, "result": None}


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

    if any(not isinstance(operation, dict) for operation in operations):
        print("ERROR")
        return

    store = {}
    results = []

    for operation in operations:
        op = operation.get("op")

        if op == "create":
            if "key" not in operation or "value" not in operation or not isinstance(operation["key"], str):
                results.append(_bad_op())
                continue

            key = operation["key"]
            if key in store:
                results.append({"ok": False, "error": "exists"})
            else:
                store[key] = operation["value"]
                results.append(_ok_null())

        elif op == "read":
            if "key" not in operation or not isinstance(operation["key"], str):
                results.append(_bad_op())
                continue

            key = operation["key"]
            if key in store:
                results.append({"ok": True, "result": store[key]})
            else:
                results.append({"ok": False, "error": "missing"})

        elif op == "update":
            if "key" not in operation or "value" not in operation or not isinstance(operation["key"], str):
                results.append(_bad_op())
                continue

            key = operation["key"]
            if key in store:
                store[key] = operation["value"]
                results.append(_ok_null())
            else:
                results.append({"ok": False, "error": "missing"})

        elif op == "delete":
            if "key" not in operation or not isinstance(operation["key"], str):
                results.append(_bad_op())
                continue

            key = operation["key"]
            if key in store:
                del store[key]
                results.append(_ok_null())
            else:
                results.append({"ok": False, "error": "missing"})

        elif op == "list":
            results.append({"ok": True, "result": sorted(store.keys())})

        else:
            results.append(_bad_op())

    print(json.dumps(results, separators=(",", ":")))


if __name__ == "__main__":
    main()
