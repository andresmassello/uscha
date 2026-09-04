import json
import sys


_MISSING = object()


def _reject_constant(name):
    raise ValueError("invalid JSON constant: " + name)


def _ok(result=None):
    return {"ok": True, "result": result}


def _err(error):
    return {"ok": False, "error": error}


def _string_field(operation, field):
    value = operation.get(field, _MISSING)
    if not isinstance(value, str):
        return _MISSING
    return value


def _execute(operations):
    store = {}
    results = []

    for operation in operations:
        op = operation.get("op")

        if op == "create":
            key = _string_field(operation, "key")
            if key is _MISSING or "value" not in operation:
                results.append(_err("bad op"))
            elif key in store:
                results.append(_err("exists"))
            else:
                store[key] = operation["value"]
                results.append(_ok())

        elif op == "read":
            key = _string_field(operation, "key")
            if key is _MISSING:
                results.append(_err("bad op"))
            elif key in store:
                results.append(_ok(store[key]))
            else:
                results.append(_err("missing"))

        elif op == "update":
            key = _string_field(operation, "key")
            if key is _MISSING or "value" not in operation:
                results.append(_err("bad op"))
            elif key in store:
                store[key] = operation["value"]
                results.append(_ok())
            else:
                results.append(_err("missing"))

        elif op == "delete":
            key = _string_field(operation, "key")
            if key is _MISSING:
                results.append(_err("bad op"))
            elif key in store:
                del store[key]
                results.append(_ok())
            else:
                results.append(_err("missing"))

        elif op == "list":
            results.append(_ok(sorted(store.keys())))

        else:
            results.append(_err("bad op"))

    return results


def main():
    try:
        raw = sys.stdin.read()
        operations = json.loads(raw, parse_constant=_reject_constant)
    except Exception:
        print("ERROR")
        return

    if not isinstance(operations, list):
        print("ERROR")
        return

    if any(not isinstance(operation, dict) for operation in operations):
        print("ERROR")
        return

    results = _execute(operations)
    sys.stdout.write(json.dumps(results, separators=(",", ":")))


if __name__ == "__main__":
    main()
