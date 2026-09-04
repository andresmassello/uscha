import json
import sys


REQUIRED_FIELDS = {"first", "last", "age"}


def fail():
    sys.stdout.write("ERROR\n")


def valid_record(value):
    if not isinstance(value, dict):
        return False
    if set(value.keys()) != REQUIRED_FIELDS:
        return False
    if not isinstance(value["first"], str):
        return False
    if not isinstance(value["last"], str):
        return False
    if not isinstance(value["age"], int) or isinstance(value["age"], bool):
        return False
    return True


def transform(records):
    output = []
    for record in records:
        if not valid_record(record):
            return None
        output.append({
            "name": record["first"] + " " + record["last"],
            "adult": record["age"] >= 18,
        })
    return output


def main():
    try:
        data = json.loads(sys.stdin.read())
    except Exception:
        fail()
        return

    if not isinstance(data, list):
        fail()
        return

    result = transform(data)
    if result is None:
        fail()
        return

    sys.stdout.write(json.dumps(result, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
