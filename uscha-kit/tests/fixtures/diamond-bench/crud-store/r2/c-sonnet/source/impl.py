import json
import sys


def main():
    raw = sys.stdin.read()
    try:
        ops = json.loads(raw)
    except (ValueError, TypeError):
        print("ERROR")
        return

    if not isinstance(ops, list):
        print("ERROR")
        return
    for op in ops:
        if not isinstance(op, dict):
            print("ERROR")
            return

    store = {}
    results = []

    for op in ops:
        name = op.get("op")

        if name == "create":
            if "key" not in op or "value" not in op:
                results.append({"ok": False, "error": "bad op"})
                continue
            key = op["key"]
            if not isinstance(key, str):
                results.append({"ok": False, "error": "bad op"})
                continue
            if key in store:
                results.append({"ok": False, "error": "exists"})
            else:
                store[key] = op["value"]
                results.append({"ok": True, "result": None})

        elif name == "read":
            if "key" not in op:
                results.append({"ok": False, "error": "bad op"})
                continue
            key = op["key"]
            if not isinstance(key, str):
                results.append({"ok": False, "error": "bad op"})
                continue
            if key in store:
                results.append({"ok": True, "result": store[key]})
            else:
                results.append({"ok": False, "error": "missing"})

        elif name == "update":
            if "key" not in op or "value" not in op:
                results.append({"ok": False, "error": "bad op"})
                continue
            key = op["key"]
            if not isinstance(key, str):
                results.append({"ok": False, "error": "bad op"})
                continue
            if key in store:
                store[key] = op["value"]
                results.append({"ok": True, "result": None})
            else:
                results.append({"ok": False, "error": "missing"})

        elif name == "delete":
            if "key" not in op:
                results.append({"ok": False, "error": "bad op"})
                continue
            key = op["key"]
            if not isinstance(key, str):
                results.append({"ok": False, "error": "bad op"})
                continue
            if key in store:
                del store[key]
                results.append({"ok": True, "result": None})
            else:
                results.append({"ok": False, "error": "missing"})

        elif name == "list":
            results.append({"ok": True, "result": sorted(store.keys())})

        else:
            results.append({"ok": False, "error": "bad op"})

    print(json.dumps(results))


if __name__ == "__main__":
    main()
