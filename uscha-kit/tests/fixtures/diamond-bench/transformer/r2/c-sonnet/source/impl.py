import sys
import json


def main():
    raw = sys.stdin.read()

    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        print("ERROR")
        return

    if not isinstance(data, list):
        print("ERROR")
        return

    result = []
    for record in data:
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
