"""Record-shape transformer.

Reads a JSON array of person records from standard input and prints a JSON
array of reshaped records to standard output. Any malformed input yields the
single token ERROR. The process always exits 0.

Mapping (per record):
    {"first": s, "last": s, "age": i} -> {"name": first + " " + last,
                                          "adult": age >= 18}

Order is preserved (INV-TR-ORDER-01): one output object per input record, in
input order, never reordered, dropped, or duplicated.
"""

import json
import sys


def transform(records):
    """Map the input array to the output array.

    Raises ValueError if the input is not a well-formed array of records.
    """
    # AC-TR-04: the top-level value must be a JSON array. bool is not a
    # concern here (it is not a list), but the type check is exact on list so
    # that objects, strings, and numbers are rejected.
    if not isinstance(records, list):
        raise ValueError("input is not a JSON array")

    out = []
    # AC-TR-03 / INV-TR-ORDER-01: a straight forward pass over the input,
    # appending exactly one object per record, preserves order by construction.
    # An empty input list yields an empty output list.
    for record in records:
        # AC-TR-05: a record must be a JSON object.
        if not isinstance(record, dict):
            raise ValueError("record is not an object")

        # AC-TR-05: all three fields must be present.
        for field in ("first", "last", "age"):
            if field not in record:
                raise ValueError("record is missing a required field")

        first = record["first"]
        last = record["last"]
        age = record["age"]

        # AC-TR-05: first/last must be strings.
        if not isinstance(first, str) or not isinstance(last, str):
            raise ValueError("first/last is not a string")

        # AC-TR-05: age must be an integer. JSON booleans decode to Python
        # bool, which is a subclass of int, so bool is excluded explicitly:
        # true is not an integer age. Floats (including 18.0) are rejected as
        # not integers.
        if isinstance(age, bool) or not isinstance(age, int):
            raise ValueError("age is not an integer")

        # AC-TR-01: name is first, one space, last.
        # AC-TR-02: adult is the boolean age >= 18 (18 -> True, 17 -> False).
        out.append({"name": first + " " + last, "adult": age >= 18})

    return out


def main():
    # Read the whole of standard input: the contract is one JSON value.
    try:
        raw = sys.stdin.read()
    except Exception:
        print("ERROR")
        return

    try:
        value = json.loads(raw)
    except Exception:
        # Not parseable as JSON at all (includes empty input).
        print("ERROR")
        return

    try:
        result = transform(value)
    except ValueError:
        # AC-TR-05: the whole batch fails; nothing partial has been printed
        # because output is emitted only after the full transform succeeds.
        print("ERROR")
        return

    # AC-TR-06: only structure and values are fixed; this formatting choice is
    # free. One line, as the contract requires.
    print(json.dumps(result))


if __name__ == "__main__":
    main()
    sys.exit(0)
