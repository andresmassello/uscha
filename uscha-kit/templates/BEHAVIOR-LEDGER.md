# Behavior Ledger

The append-only audit trail of every verdict on the legacy system's observed behavior
(ADR-009/010). Rules the engine enforces (`qa_ledger.py curation-check`):

- Exactly six columns per row. Verdict is one of `preserve` / `fix` / `undefined` — anything
  else is malformation, not a fourth state.
- Every verdict names its ADR (`ADR-RD-NNN`): no verdict without its why.
- Append-only, verified against git: reverting a verdict is a NEW row plus a new ADR, never
  an edit. The LATEST row for a candidate wins.

| # | candidate | evidence | confidence | verdict | adr |
|---|-----------|----------|------------|---------|-----|
