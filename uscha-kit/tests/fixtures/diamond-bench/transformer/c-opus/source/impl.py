import sys
import json


def _fail():
    print("ERROR")
    sys.exit(0)


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        _fail()
        return

    # Input that is not a JSON array -> ERROR (AC-TR-04).
    if not isinstance(data, list):
        _fail()
        return

    out = []
    for rec in data:
        # A record that is not an object -> ERROR (AC-TR-05).
        if not isinstance(rec, dict):
            _fail()
            return

        # Missing any of first/last/age -> ERROR (AC-TR-05).
        if "first" not in rec or "last" not in rec or "age" not in rec:
            _fail()
            return

        first = rec["first"]
        last = rec["last"]
        age = rec["age"]

        # first/last must be strings (AC-TR-05).
        if not isinstance(first, str) or not isinstance(last, str):
            _fail()
            return

        # age must be an integer (AC-TR-05). bool is a subclass of int; reject it.
        if not isinstance(age, int) or isinstance(age, bool):
            _fail()
            return

        # AC-TR-01: name = first + space + last. AC-TR-02: adult = age >= 18.
        # INV-TR-ORDER-01 / AC-TR-03: append in input order, one per record.
        out.append({"name": first + " " + last, "adult": age >= 18})

    print(json.dumps(out))
    sys.exit(0)


if __name__ == "__main__":
    main()
