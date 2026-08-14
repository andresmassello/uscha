"""Record-shape transformer.

Reads one JSON value from standard input, prints one line to standard output,
exits with code 0.

A record is a JSON object with exactly the fields `first` (string),
`last` (string), and `age` (integer). An output object is a JSON object with
the fields `name` (string) and `adult` (boolean).

When the input is a JSON array of records, the program prints a JSON array of
output objects. When the input is a malformed input, the program prints exactly
`ERROR`.
"""

import json
import sys


def is_record(value):
    """Return True when the value is a record.

    A record is a JSON object carrying exactly the fields `first`, `last`, and
    `age`, with `first` and `last` strings and `age` an integer. A boolean is
    not an integer here: `bool` is a subclass of `int` in Python, and the spec
    fixes `age` as an integer, so booleans are rejected.
    """
    if not isinstance(value, dict):
        return False
    if set(value.keys()) != {"first", "last", "age"}:
        return False
    if not isinstance(value["first"], str):
        return False
    if not isinstance(value["last"], str):
        return False
    age = value["age"]
    if isinstance(age, bool) or not isinstance(age, int):
        return False
    return True


def map_record(record):
    """Map one record to one output object."""
    return {
        "name": record["first"] + " " + record["last"],
        "adult": record["age"] >= 18,
    }


def transform(value):
    """Return the list of output objects, or None when the input is malformed."""
    if not isinstance(value, list):
        return None
    output = []
    for element in value:
        if not is_record(element):
            return None
        output.append(map_record(element))
    return output


def main():
    raw = sys.stdin.read()
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        sys.stdout.write("ERROR\n")
        return 0
    result = transform(value)
    if result is None:
        sys.stdout.write("ERROR\n")
        return 0
    sys.stdout.write(json.dumps(result) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
