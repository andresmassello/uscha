# uscha-kit 1.85.1 — the ledger records WHY a score was capped, not only that it was (issue #1) (2026-08-17)

Closes [issue #1](https://github.com/andresmassello/uscha/issues/1), raised from field note 001's
first stated limitation: *"Causes are not persisted per-entry."* `readiness --record` appended
`{at, score}` to `readiness_history` — the score, never the reason — so anyone reading the
time-lapse later had to infer why a number sat at 65 or 35. The engine had already computed the
reason (`cap_reason`, the cap key) and the stale-report set a few lines above the append.

## What changed

Each `readiness_history` entry now carries two more facts, both taken from values the same
readiness call already computed — nothing is re-derived:

- `cap_applied`: `{"reason": <label>, "key": <cap key>}` when a hard cap actually bit (the
  score was above the ceiling and was pulled down to it), or `null` when no cap bit — a cap
  can be *active* (a blocker is open) without *applying* (the raw score was already below the
  ceiling), and `null` states that honestly instead of inventing a reason.
- `stale_discarded`: `{"count": N, "reports": [...up to 8 paths]}` — the JUnit reports the
  freshness rule (kit 1.31.0) discarded as older than the code, so a criterion left UNMEASURED
  by staleness can be traced to the report that caused it.

Additive keys: `at` and `score` are unchanged, and every existing reader (dashboard time-lapse,
statusline) uses `.get()`, so older ledgers and older readers keep working. One smoke check
pins the shape on a recorded entry. No other engine behaviour changes.

Suite: 423 checks; acceptance 147/147 where `coverage.py` is installed.
