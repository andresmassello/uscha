import sys
import json


def transform(data):
    if not isinstance(data, list):
        return None

    results = []
    for element in data:
        if not isinstance(element, dict):
            return None
        if "first" not in element or "last" not in element or "age" not in element:
            return None

        first = element["first"]
        last = element["last"]
        age = element["age"]

        if not isinstance(first, str) or not isinstance(last, str):
            return None
        if not isinstance(age, int) or isinstance(age, bool):
            return None

        results.append({
            "name": first + " " + last,
            "adult": age >= 18,
        })

    return results


def main():
    raw = sys.stdin.read()

    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        print("ERROR")
        return

    output = transform(data)

    if output is None:
        print("ERROR")
        return

    print(json.dumps(output))


if __name__ == "__main__":
    main()
