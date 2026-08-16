# ACCEPTANCE — two-module ledger

- [ ] AC-LG-01 a balanced posting (amounts sum to 0, ≥ 2 lines) is accepted and its lines
  update the balances of its accounts.
- [ ] AC-LG-02 an unbalanced posting, or one with fewer than two lines, is rejected: its id is
  in `rejected`, none of its lines touch any balance, and other postings are unaffected.
- [ ] AC-LG-03 a posting whose id was already seen in the batch (accepted or rejected) is
  rejected.
- [ ] AC-LG-04 balances list only accounts touched by accepted postings; `rejected` is in input
  order; an empty batch yields `{"balances": {}, "rejected": []}`.
- [ ] AC-LG-05 shape problems (not an array, non-object element, missing/mistyped id/lines/
  account/amount, boolean where an integer is required) print exactly `ERROR`.
- [ ] AC-LG-06 the system is two units: `source/model.py` (no I/O, `post(postings) ->
  (balances, rejected)`) and `source/cli.py` (I/O + shape validation, imports model); the CLI
  never computes a balance (ADR-001).
