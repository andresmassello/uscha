def post(postings):
    """Apply a batch of validated postings and return (balances, rejected_ids)."""
    balances = {}
    rejected = []
    seen_ids = set()

    for posting in postings:
        posting_id = posting["id"]

        if posting_id in seen_ids:
            rejected.append(posting_id)
            continue

        seen_ids.add(posting_id)
        lines = posting["lines"]

        if len(lines) < 2 or sum(line["amount"] for line in lines) != 0:
            rejected.append(posting_id)
            continue

        for line in lines:
            account = line["account"]
            balances[account] = balances.get(account, 0) + line["amount"]

    return balances, rejected
