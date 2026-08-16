import sys
import json

def main():
    try:
        # Read all stdin as JSON
        input_str = sys.stdin.read()
        operations = json.loads(input_str)

        # Validate input is an array
        if not isinstance(operations, list):
            print("ERROR")
            sys.exit(0)

        # In-memory store, starting empty
        store = {}
        results = []

        for op_obj in operations:
            # Validate operation is a dict
            if not isinstance(op_obj, dict):
                results.append({"ok": False, "error": "bad op"})
                continue

            op = op_obj.get("op")

            if op == "create":
                if "key" not in op_obj or "value" not in op_obj:
                    results.append({"ok": False, "error": "bad op"})
                else:
                    key = op_obj["key"]
                    if key in store:
                        results.append({"ok": False, "error": "exists"})
                    else:
                        store[key] = op_obj["value"]
                        results.append({"ok": True, "result": None})

            elif op == "read":
                if "key" not in op_obj:
                    results.append({"ok": False, "error": "bad op"})
                else:
                    key = op_obj["key"]
                    if key in store:
                        results.append({"ok": True, "result": store[key]})
                    else:
                        results.append({"ok": False, "error": "missing"})

            elif op == "update":
                if "key" not in op_obj or "value" not in op_obj:
                    results.append({"ok": False, "error": "bad op"})
                else:
                    key = op_obj["key"]
                    if key in store:
                        store[key] = op_obj["value"]
                        results.append({"ok": True, "result": None})
                    else:
                        results.append({"ok": False, "error": "missing"})

            elif op == "delete":
                if "key" not in op_obj:
                    results.append({"ok": False, "error": "bad op"})
                else:
                    key = op_obj["key"]
                    if key in store:
                        del store[key]
                        results.append({"ok": True, "result": None})
                    else:
                        results.append({"ok": False, "error": "missing"})

            elif op == "list":
                keys = sorted(store.keys())
                results.append({"ok": True, "result": keys})

            else:
                # Unknown operation
                results.append({"ok": False, "error": "bad op"})

        # Output results as JSON array
        print(json.dumps(results))
        sys.exit(0)

    except (json.JSONDecodeError, ValueError):
        print("ERROR")
        sys.exit(0)
    except Exception:
        print("ERROR")
        sys.exit(0)

if __name__ == "__main__":
    main()
