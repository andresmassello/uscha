import json
import sys


def main():
    raw = sys.stdin.read()

    try:
        ops = json.loads(raw)
    except (ValueError, TypeError):
        print("ERROR")
        return 0

    if not isinstance(ops, list):
        print("ERROR")
        return 0

    store = {}
    results = []

    for op in ops:
        if not isinstance(op, dict):
            results.append({"ok": False, "error": "bad op"})
            continue

        op_name = op.get("op")

        if op_name == "list":
            results.append({"ok": True, "result": sorted(store.keys())})
            continue

        if op_name not in ("create", "read", "update", "delete"):
            results.append({"ok": False, "error": "bad op"})
            continue

        if "key" not in op or not isinstance(op["key"], str):
            results.append({"ok": False, "error": "bad op"})
            continue

        key = op["key"]

        if op_name in ("create", "update") and "value" not in op:
            results.append({"ok": False, "error": "bad op"})
            continue

        if op_name == "create":
            if key in store:
                results.append({"ok": False, "error": "exists"})
            else:
                store[key] = op["value"]
                results.append({"ok": True, "result": None})

        elif op_name == "read":
            if key in store:
                results.append({"ok": True, "result": store[key]})
            else:
                results.append({"ok": False, "error": "missing"})

        elif op_name == "update":
            if key in store:
                store[key] = op["value"]
                results.append({"ok": True, "result": None})
            else:
                results.append({"ok": False, "error": "missing"})

        elif op_name == "delete":
            if key in store:
                del store[key]
                results.append({"ok": True, "result": None})
            else:
                results.append({"ok": False, "error": "missing"})

    print(json.dumps(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
