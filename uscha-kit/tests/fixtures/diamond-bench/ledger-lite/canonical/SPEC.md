# SPEC — a two-module ledger (Diamond bench archetype: multi-unit system with a decided seam)

A program made of TWO source files that posts a batch of double-entry postings to accounts and
prints the resulting balances. The only compiler input; describes behaviour, not an
implementation and not a test case. **This system has exactly two units — see the ADR in this
package for the seam between them; the compiler must produce both files.**

## Contract

- **Units:** `source/model.py` (the journal: pure logic, no I/O) and `source/cli.py` (the entry
  point: reads stdin, imports `model`, prints). Run as `python cli.py` from the `source/`
  directory (so `import model` resolves).
- **Input:** standard input is a JSON array of postings. A posting is an object
  `{"id": <string>, "lines": [{"account": <string>, "amount": <integer>}, ...]}`.
- **Output:** print one JSON object to standard output and exit 0:
  `{"balances": {<account>: <integer>, ...}, "rejected": [<id>, ...]}` — balances of every
  account that appears in at least one ACCEPTED posting (accounts only touched by rejected
  postings do not appear), and the ids of rejected postings in input order. On any malformed
  input, print exactly `ERROR`.

## The journal (`model`)

- A posting is **balanced** when the sum of its `amount`s is exactly 0 and it has at least two
  lines. `model.post(postings)` accepts a list of already-validated postings and returns
  `(balances, rejected_ids)`.
- An unbalanced posting, or one with fewer than two lines, is **rejected**: its id goes to
  `rejected`, none of its lines touch any balance. Rejection isolates: other postings in the
  batch are unaffected.
- A posting with a **duplicate id** (an id already accepted or rejected earlier in the batch)
  is rejected.
- Accepted postings apply in input order; a balance is the sum of that account's amounts over
  all accepted postings. Zero-amount lines are legal (they touch the account with 0).
- The model performs no I/O and knows nothing about JSON or stdin.

## The entry point (`cli`)

- Reads the whole of stdin, parses JSON, validates the SHAPE (array of objects with string
  `id`, array `lines` of objects with string `account` and integer `amount` — JSON booleans
  are not integers), calls `model.post`, prints the result. The CLI never computes a balance
  and never decides acceptance — that is the model's.

## Errors

- Input that is not a JSON array, an element that is not an object, missing/mistyped `id`,
  `lines`, `account` or `amount`, an empty `lines` array on a structurally valid posting is
  NOT an error (it is a rejection: fewer than two lines) → only SHAPE problems are `ERROR`,
  for the whole input.

## Out of scope (state honestly; do not implement)

No persistence, no currencies, no dates, no account hierarchy. The JSON output's formatting is
not fixed by this spec — only its structure and values are.
