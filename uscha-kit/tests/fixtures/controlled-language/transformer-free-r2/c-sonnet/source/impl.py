import json
import sys


def main():
    try:
        raw = sys.stdin.read()
        parsed = json.loads(raw)
    except Exception:
        print("ERROR")
        return

    if not isinstance(parsed, list):
        print("ERROR")
        return

    result = []
    for record in parsed:
        if not isinstance(record, dict):
            print("ERROR")
            return
        if "first" not in record or "last" not in record or "age" not in record:
            print("ERROR")
            return

        first = record["first"]
        last = record["last"]
        age = record["age"]

        if not isinstance(first, str) or not isinstance(last, str):
            print("ERROR")
            return
        if not isinstance(age, int) or isinstance(age, bool):
            print("ERROR")
            return

        result.append({"name": first + " " + last, "adult": age >= 18})

    print(json.dumps(result))


if __name__ == "__main__":
    main()
