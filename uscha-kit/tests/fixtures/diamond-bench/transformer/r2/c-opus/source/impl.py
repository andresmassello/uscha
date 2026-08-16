"""Record-shape transformer.

Reads one JSON array of person records from standard input and prints one
line: the transformed JSON array, or exactly ERROR on any malformed input.

Each record {"first": str, "last": str, "age": int} maps to
{"name": first + " " + last, "adult": age >= 18}, in input order.
"""

import json
import sys

ERROR = "ERROR"


def transform_record(record):
    """Map one record to its output object, or raise ValueError if malformed."""
    if not isinstance(record, dict):
        raise ValueError("record is not an object")

    for field in ("first", "last", "age"):
        if field not in record:
            raise ValueError("missing field")

    first = record["first"]
    last = record["last"]
    age = record["age"]

    if not isinstance(first, str) or not isinstance(last, str):
        raise ValueError("name field is not a string")
    # bool is a subclass of int in Python; a boolean age is not an integer age.
    if not isinstance(age, int) or isinstance(age, bool):
        raise ValueError("age is not an integer")

    return {"name": first + " " + last, "adult": age >= 18}


def transform(payload):
    """Map a decoded payload to the output list, or raise ValueError."""
    if not isinstance(payload, list):
        raise ValueError("input is not a JSON array")
    return [transform_record(record) for record in payload]


def main():
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except ValueError:
        print(ERROR)
        return 0

    try:
        result = transform(payload)
    except ValueError:
        print(ERROR)
        return 0

    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
