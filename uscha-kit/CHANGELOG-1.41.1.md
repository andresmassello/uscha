# uscha-kit 1.41.1 — adversarial-review hardening (2026-07-11)

An independent adversarial review of the 1.41.0 "safety hardening" release (4 parallel
reviewers, each tasked to REFUTE the safety claims) confirmed three real defects — two of
them in the engine's core "measured beats narrated" promise. Fixed here, each with a
regression check that fails without the fix. Smoke suite: 355/355.

## Fixes

### 1 — `pr-ready` accepted a JUnit that LIES (HIGH, core-promise)
`_junit_counts` read `tests`/`failures`/`errors` from the `<testsuite>` **attributes** and
never reconciled them against the actual `<testcase>`/`<failure>`/`<error>` **elements**. A
report declaring `failures="0"` while containing a real `<failure>` element read as all-green
and could satisfy `pr-ready`. Fix: honor the child elements, fail-closed —
`failures = max(attr, element_failures)`, same for errors. A present failure can no longer be
attribute-declared away. Attribute-only summary suites (no `<testcase>` elements — the form
many emitters legitimately use) keep their counts, so real adapters are unaffected.
`qa_ledger.py:_junit_counts`. Regression: smoke **T69b**.

### 2 — integration readiness trusted the single last event (MEDIUM-HIGH, core-promise)
The integration dimension read `integ_steps[-1]`, so a trailing green test-only step masked
an earlier FAILING integration gate (dim → 1.0). Fix: green now requires **0 open gated
findings across the latest record per integration tool** AND the latest test event passing —
so a failing gate is not masked, while a same-tool re-run that clears the gate is still seen.
`qa_ledger.py:cmd_readiness`. Regression: smoke **T69c**. (The 1.41.0 CHANGELOG claimed WU4
fixed this; the code still used `integ_steps[-1]` — the claim was inaccurate.)

### 3 — Codex install rollback destroyed the pre-existing plugin (HIGH, data loss)
`install_codex` gated its restore on `swapped` (only true after BOTH the backup-move and the
install-move succeeded), then the `finally` deleted the backup unconditionally. If the
`stage → plugin_root` swap failed after the original was moved to backup (a real Windows AV /
locked-handle failure on reinstall), the restore was skipped and the `finally` deleted the
only surviving copy — silently. Fix: gate the restore on the **backup existing** (not on
`swapped`), and drop the backup only on SUCCESS (never in `finally`), so a failure restores
the original and a hard interrupt leaves it intact. Mirrors the Claude path, which already did
this. `install-uscha.py:install_codex`. Regression: smoke **T77b**. (This is exactly the
"rollback leaves partial state" category 1.41.0 claimed to close — it closed it for Claude,
not Codex.)

## Honest limits (not fixed here, by design)
- A JUnit `<testsuite tests="3"/>` with ZERO `<testcase>` elements is still credited as 3
  tests. This is the same trust the engine extends to any tool-emitted summary (a coverage %
  in a coverage report), and closing it would reject the legitimate attribute-only reports
  many emitters produce. The defense against a **forged** bare report is the "evidence
  captured by execution" invariant (the SKILL runs the real test command; the agent does not
  hand-write the XML) + the human merge gate — not per-report forgery detection.

## Also
- `docs/skills-referencia.html` + `-EN.html`: stale "24 subcommands" → 29 (truth-pass).

## Note on the test suite
The installer/npm smoke checks hardcode the version string, so a version bump requires
updating those literals (done here). A follow-up could have them read `VERSION` dynamically.
