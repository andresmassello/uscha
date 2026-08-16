"""The journal: pure double-entry posting logic. No I/O, stdlib only."""


def post(postings):
    """Apply a list of postings to a ledger.

    Each posting is a dict {"id": str, "lines": [{"account": str, "amount": int}, ...]}.
    Returns (balances, rejected):
      - balances: dict of account -> summed amount, for accounts touched by
        at least one accepted posting.
      - rejected: list of ids, in input order, of postings that were rejected
        because they were unbalanced, had fewer than two lines, or reused an
        id already seen earlier in the batch (accepted or rejected).

    Acceptance and arithmetic live here and only here (INV-LG-SEAM-01).
    """
    balances = {}
    rejected = []
    seen_ids = set()

    for posting in postings:
        posting_id = posting["id"]
        lines = posting["lines"]

        if posting_id in seen_ids:
            rejected.append(posting_id)
            continue

        seen_ids.add(posting_id)

        if len(lines) < 2:
            rejected.append(posting_id)
            continue

        total = 0
        for line in lines:
            total += line["amount"]

        if total != 0:
            rejected.append(posting_id)
            continue

        for line in lines:
            account = line["account"]
            balances[account] = balances.get(account, 0) + line["amount"]

    return balances, rejected
