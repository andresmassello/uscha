# uscha-kit 1.66.0 — the advisories reach the user who never asks (2026-08-06)

A visibility release, born from an audit question: *does any of this actually reach the
user?* The mechanisms of the closed loop were complete and measured — and unevenly wired to
the surfaces a human actually looks at. Two gaps, both of the same species: an advisory
nobody runs is an advisory nobody sees.

## `roundtrip` persists

The report used to evaporate on exit — invisible to the mirador, the status readout and the
dashboard, which defeats the point of an advisory. It now records its latest state to the
ledger (the `spec_drift` pattern: no step counter, no gate record), `dashboard --json`
carries `roundtrip` **only when a run exists** (virgin-ledger schema unchanged — the
conditional-key rule, five keys strong), and `/uscha-status` prints one line:
`roundtrip: N/M promoted traceable by uscha-spec id (advisory)`. Absent key → no line.
Measured by `AC-RD-12`.

## The devloop runs `spec-drift` at pass close

Spec-drift existed, was measured, and was surfaced on three read surfaces — **for anyone who
had ever typed the command.** Nobody runs it automatically, and the user this advisory exists
for is precisely the one who never types it: the one whose specs rot in silence. The devloop
skill now runs it right after `readiness --record` at every pass close — milliseconds,
deterministic, exit 0 always, so zero added ceremony — and mentions any `SPEC_STALE` doc in
its close block as advisory context. The skill wires; the engine still never gates on a
guess.

## What the fresh review caught

- **CRITICAL, second recurrence of a known class**: the new pass-close instruction made the
  devloop run `spec-drift --repo integration` -- and `cmd_spec_drift` had no guard for the
  SYNTHETIC `integration` scope, so the "exit 0 always" advisory crashed with a config error
  on every multi-repo pass. Same class as the 1.63.0 clean-room CRITICAL. Two recurrences
  turn the pattern into a helper: `_scope_path` now guards the scope for all three
  curation-family commands (`spec-drift`, `curation-check`, `roundtrip`), and `AC-RD-13`
  measures them against the scope directly.
- The changelog's own "six keys strong" was a miscount: the conditional dashboard rule is
  five keys strong. Fixed here, which is as meta as a truth-pass gets.

Suite: 406 checks. Acceptance: **55/55** where `coverage.py` is installed.
