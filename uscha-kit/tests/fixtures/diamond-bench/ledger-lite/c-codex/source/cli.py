import json
import sys

import model


def _is_valid_posting(value):
    if not isinstance(value, dict):
        return False
    if not isinstance(value.get("id"), str):
        return False

    lines = value.get("lines")
    if not isinstance(lines, list):
        return False

    for line in lines:
        if not isinstance(line, dict):
            return False
        if not isinstance(line.get("account"), str):
            return False
        if type(line.get("amount")) is not int:
            return False

    return True


def _load_postings(text):
    try:
        data = json.loads(text)
    except ValueError:
        return None

    if not isinstance(data, list):
        return None

    for posting in data:
        if not _is_valid_posting(posting):
            return None

    return data


def main():
    postings = _load_postings(sys.stdin.read())
    if postings is None:
        print("ERROR")
        return 0

    balances, rejected = model.post(postings)
    print(json.dumps({"balances": balances, "rejected": rejected}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
