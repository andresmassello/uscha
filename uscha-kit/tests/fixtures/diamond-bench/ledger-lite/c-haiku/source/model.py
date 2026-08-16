def post(postings):
    """
    Process a batch of postings and return (balances, rejected_ids).

    A posting is accepted if:
    - Its id has not been seen before (in accepted or rejected postings)
    - It has at least 2 lines
    - The sum of its line amounts is exactly 0

    Only accepted postings modify account balances. Rejected postings are isolated.

    Args:
        postings: list of dicts, each with 'id' (str) and 'lines' (list of line dicts).
                  Each line dict has 'account' (str) and 'amount' (int).

    Returns:
        tuple: (balances dict {account: sum_of_amounts}, list of rejected posting ids in order)
    """
    balances = {}
    rejected = []
    seen_ids = set()

    for posting in postings:
        posting_id = posting['id']
        lines = posting['lines']

        # Rejection: duplicate id (already seen, accepted or rejected)
        if posting_id in seen_ids:
            rejected.append(posting_id)
            seen_ids.add(posting_id)
            continue

        # Rejection: insufficient lines (need at least 2)
        if len(lines) < 2:
            rejected.append(posting_id)
            seen_ids.add(posting_id)
            continue

        # Rejection: posting is not balanced (amounts don't sum to 0)
        total = sum(line['amount'] for line in lines)
        if total != 0:
            rejected.append(posting_id)
            seen_ids.add(posting_id)
            continue

        # Acceptance: apply all line amounts to their accounts
        seen_ids.add(posting_id)
        for line in lines:
            account = line['account']
            if account not in balances:
                balances[account] = 0
            balances[account] += line['amount']

    return balances, rejected
