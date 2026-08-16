"""Entry point: reads stdin, validates SHAPE only, calls model.post, prints."""

import sys
import json

import model


def _is_valid_amount(value):
    # JSON booleans are a subtype of int in Python; the spec explicitly
    # excludes them from counting as a valid integer amount.
    return isinstance(value, int) and not isinstance(value, bool)


def _parse_postings(data):
    """Validate SHAPE of the parsed JSON value.

    Returns a list of postings on success, or None if the shape is invalid
    (the caller prints ERROR in that case). This function never inspects
    amounts for balance and never decides acceptance/rejection of a
    posting on ledger grounds - only on shape grounds.
    """
    if not isinstance(data, list):
        return None

    postings = []
    for item in data:
        if not isinstance(item, dict):
            return None

        if "id" not in item or "lines" not in item:
            return None

        posting_id = item["id"]
        lines = item["lines"]

        if not isinstance(posting_id, str):
            return None
        if not isinstance(lines, list):
            return None

        validated_lines = []
        for line in lines:
            if not isinstance(line, dict):
                return None
            if "account" not in line or "amount" not in line:
                return None

            account = line["account"]
            amount = line["amount"]

            if not isinstance(account, str):
                return None
            if not _is_valid_amount(amount):
                return None

            validated_lines.append({"account": account, "amount": amount})

        postings.append({"id": posting_id, "lines": validated_lines})

    return postings


def main():
    raw = sys.stdin.read()

    try:
        data = json.loads(raw)
    except ValueError:
        print("ERROR")
        return 0

    postings = _parse_postings(data)
    if postings is None:
        print("ERROR")
        return 0

    balances, rejected = model.post(postings)
    print(json.dumps({"balances": balances, "rejected": rejected}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
