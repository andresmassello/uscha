# WRONG on purpose (ADR-029 discrimination fixture): cli never imports model: rejects everything
"""The journal: pure logic, no I/O. The ONLY place a balance is computed (ADR-001)."""


def post(postings):
    """postings: list of {"id": str, "lines": [{"account": str, "amount": int}, ...]},
    already shape-validated by the caller. Returns (balances, rejected_ids)."""
    balances = {}
    rejected = []
    seen = set()
    for p in postings:
        pid = p["id"]
        if pid in seen:
            rejected.append(pid)
            continue
        seen.add(pid)
        lines = p["lines"]
        if len(lines) < 2 or sum(ln["amount"] for ln in lines) != 0:
            rejected.append(pid)
            continue
        for ln in lines:
            balances[ln["account"]] = balances.get(ln["account"], 0) + ln["amount"]
    return balances, rejected
