import json
import sys


def main():
    try:
        data = json.loads(sys.stdin.read())
        if not isinstance(data, list):
            raise ValueError

        result = []
        required_keys = {"first", "last", "age"}

        for record in data:
            if not isinstance(record, dict):
                raise ValueError
            if set(record.keys()) != required_keys:
                raise ValueError

            first = record["first"]
            last = record["last"]
            age = record["age"]

            if not isinstance(first, str):
                raise ValueError
            if not isinstance(last, str):
                raise ValueError
            if not isinstance(age, int) or isinstance(age, bool):
                raise ValueError

            result.append({"name": first + " " + last, "adult": age >= 18})

        print(json.dumps(result))
    except Exception:
        print("ERROR")


if __name__ == "__main__":
    main()
