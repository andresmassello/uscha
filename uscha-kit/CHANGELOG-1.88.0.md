# uscha-kit 1.88.0 — `uscha top` M2: the ledger's feed reaches the terminal, and the board redraws when the disk moves (2026-08-18)

M2 of the terminal projection (SPEC §5): the live feed and mtime polling. ADR-032 amended (M2),
ADR-031's poll checkbox closed; ADR-033 (verdicts) still proposed — that is M3.

## What changed

- **Feed, derived once, in the engine.** `top --json` now fills `events_tail` from
  `ledger["steps"]`: the last 8 steps, newest first, `ts` = HH:MM:SS UTC (never the local zone —
  deterministic), `level ∈ {pass, fail, human, unmeasured, info}` by a fixed map per step kind,
  refined from the record the step points at (a snapshot with red tests → `fail`; a qa-step with
  nothing reported or all fixed → `pass`; a static gate by its result; `gate-not-run` →
  `unmeasured`; escalations, production findings, spec doubts, spec change requests → `human`;
  cleanroom by `ok`; anything unknown → `info`). A missed correlation degrades to the neutral
  level, never to a verdict. `text` is built only from step fields, capped at 72 chars, and every
  control character is stripped in the engine and again in the renderer — this is the one
  free-text field that reaches the terminal, so it is sanitized twice on purpose.
- **Feed pane.** `HH:MM:SS  L  text` with the level letter (`P/F/H/U/I`) carrying the level on the
  plain path and colour only decorating the letter, so plain and coloured frames keep the same
  geometry; three honest labels (`feed · 5/7 · newest first`, `no room at this size`, `no ledger
  step recorded yet`). 80×24 still shortens the feed first.
- **Polling.** The interactive loop re-renders only when a key arrives or a watched file changed
  (`(mtime, size)` snapshot of the ledger), every `--refresh` s (default 2, floor 0.5); a ledger
  caught mid-write keeps the last good board; `r` still forces a reload; `--once` unchanged.
- **Width pass fixed.** Coloured lines were re-fitted after their escapes went in, so a coloured
  80-col frame came out ~9 chars narrower than its golden; the final pass now skips escaped
  lines, and `plain == strip_escapes(coloured)` holds at both sizes.

Measured: `AC-T-11` (T137: ≤8 events, newest-first, the level list across kinds, ts rule,
sanitization, `[]` for a step-less ledger) and `AC-T-12` (T138: the polling primitive flips on
touch and not otherwise, `--refresh` default and floor, the `--once` frame carries every fixture
event, zero ESC on the plain path). Honest scope: `AC-T-12` measures the primitive plus the
rendered frame — the suite has no TTY to drive the loop. All ten golden frames were re-rendered
by `render()` because the feed pane moved.

The blind review of this milestone caught a deleted assertion (the py3.8 byte-identity gate `AC-T-19b`
had stopped measuring) plus six weaker gates; all restored or tightened before this shipped, each with a
mutation that goes red (malformed ledger fields degrade to `info` instead of raising; state-supplied
text can neither widen a line nor carry an escape; the renderer's second sanitizer, the `size` half of
the poll and the 72-char truncation are each exercised).

Suite: 428 checks · 0 fail; acceptance 173/178 (5 UNMEASURED on purpose: `AC-T-13..17`, M3).
