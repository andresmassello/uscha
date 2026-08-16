# CONSTITUTION — two-module ledger

- **INV-LG-BALANCE-01 — the journal never goes out of balance.** The sum of all balances is
  0 after any batch: only balanced postings are ever applied, and rejection touches nothing.
- **INV-LG-SEAM-01 — balances are computed in exactly one place.** The model owns acceptance
  and arithmetic; the CLI owns I/O and shape. No balance is ever computed outside `model.post`.
