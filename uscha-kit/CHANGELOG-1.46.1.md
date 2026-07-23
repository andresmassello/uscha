# uscha-kit 1.46.1 — the statusline reads MEASURED acceptance, never narrated (2026-07-23)

A doctrinal fix to the statusline shipped in 1.46.0, found by dogfooding it on this very repo.
Smoke suite: 375/375.

## The smell
The progress hook counted checkboxes (`- [x]`) in `ACCEPTANCE.md` — the **narrated** progress.
The engine's readiness counts green `AC-nn` testcases — the **measured** acceptance. The two can
diverge, and on this repo they diverged badly: the statusline said **0%** while the ledger said
**83.3% measured** (criteria tested green but not ticked). For a kit whose flag is *measured
beats narrated*, its own at-a-glance summary was reading the wrong side — and could contradict
the mirador.

## The fix (write-once by the engine, read-many by the hook)
The statusline must summarize the ledger, so it now reads the ledger's own truth:

- **Engine**: `readiness --record` persists a compact measured summary into
  `ledger["measured"]` — `{at, score, band, acceptance_done, acceptance_total, next}` — where
  `next` is the first criterion NOT yet closed by a green test. Same opt-in write as
  `readiness_history` (readiness stays read-only by default). `qa_ledger.py:cmd_readiness`.
- **Hook** (`uscha_progress.py`): prefers `ledger["measured"]` — the exact truth the mirador
  shows, so the two can never disagree. Counting checkboxes remains only as the **fallback** for
  a fresh project that has not recorded a measurement yet. The hook stays fast: it never re-runs
  the engine.

Considered and rejected: having the Stop hook run the engine itself (breaks the "fast hook,
never runs tests" design and couples it to locating `qa_ledger.py`), and merely relabeling the
checkbox count as "marked" (honest, but keeps the narrated number as the headline).

Regression: smoke **T90** — checkbox fallback shows 0/2; after `readiness --record` the
statusline shows the MEASURED 1/2, agreeing with the ledger to the decimal.

## Note on the test suite
The installer/npm smoke checks still hardcode the version string, so this bump updated those
literals.
