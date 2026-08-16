"""The journal: pure double-entry posting logic.

Owns acceptance and arithmetic (ADR-001, INV-LG-SEAM-01). Performs no I/O and
knows nothing about JSON, stdin or the shape of the outside world.
"""


def post(postings):
    """Apply a batch of already-shape-validated postings.

    Each posting is a dict {"id": str, "lines": [{"account": str,
    "amount": int}, ...]}.

    A posting is accepted when it has at least two lines, its amounts sum to
    exactly 0, and its id has not been seen earlier in the batch. Anything else
    is rejected: its id is recorded and none of its lines touch any balance
    (INV-LG-BALANCE-01 — the sum of all balances stays 0).

    Returns (balances, rejected_ids): balances maps every account touched by an
    accepted posting to the sum of its amounts, and rejected_ids lists the ids
    of rejected postings in input order.
    """
    balances = {}
    rejected = []
    seen = set()

    for posting in postings:
        posting_id = posting["id"]
        lines = posting["lines"]

        if posting_id in seen:
            rejected.append(posting_id)
            continue
        seen.add(posting_id)

        if len(lines) < 2 or sum(line["amount"] for line in lines) != 0:
            rejected.append(posting_id)
            continue

        for line in lines:
            account = line["account"]
            balances[account] = balances.get(account, 0) + line["amount"]

    return balances, rejected
