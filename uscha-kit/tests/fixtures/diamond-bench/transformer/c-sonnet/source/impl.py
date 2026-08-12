import sys
import json


def main():
    raw = sys.stdin.read()

    try:
        records = json.loads(raw)
    except Exception:
        print("ERROR")
        return 0

    if not isinstance(records, list):
        print("ERROR")
        return 0

    output = []
    for rec in records:
        if not isinstance(rec, dict):
            print("ERROR")
            return 0

        if "first" not in rec or "last" not in rec or "age" not in rec:
            print("ERROR")
            return 0

        first = rec["first"]
        last = rec["last"]
        age = rec["age"]

        if not isinstance(first, str) or not isinstance(last, str):
            print("ERROR")
            return 0

        # bool is a subclass of int in Python; a JSON boolean is not a
        # JSON integer, so it must be rejected explicitly.
        if not isinstance(age, int) or isinstance(age, bool):
            print("ERROR")
            return 0

        output.append({"name": first + " " + last, "adult": age >= 18})

    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
