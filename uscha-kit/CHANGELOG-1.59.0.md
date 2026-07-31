# uscha-kit 1.59.0 — the modes reach the pixel: mirador card + status line (2026-07-31)

1.58.0 shipped the `spec_drift` data contract and — following *under-claim, then wire, then
re-claim* — explicitly marked the mirador rendering as `proposal`: the data shipped before
the pixel, and the docs said so instead of pretending. This release closes that proposal,
for both modes at once (`fast_path` had the same gap since 1.57.0).

## Mirador — one "Fast-path · Spec-drift" card

- `mirador.template.html` gains a card that paints both ledger facts: fast-path verdict
  chips per repo (`ALLOW` green / `ESCALATED` amber / `DENY` red, with the recorded intent)
  and spec-drift rows per document (`SPEC_STALE` red with the newer-file count / `CLEAN`
  green / `UNMAPPED` and `UNTRACKED` muted), with an explicit **advisory** label on the
  spec-drift half — the card makes a ledger fact visible, it never feeds readiness.
- **Absent block = identical view:** the card is hidden entirely when neither key exists in
  `DATA` — the same conditional rule `dashboard --json` follows, now honored at the pixel.
- Verified in a real browser at authoring time (rows, chips, counts, and the hidden state on
  a virgin ledger). Smoke **T115** guards the structure in CI — card markup, renderer, init
  call, conditional degradation, verdict map, advisory label, and no HTML sinks in the new
  renderer (the P0-A DOM-sink posture applies to it too: `textContent` only).

## `/uscha-status` — one spec-drift line

The chat readout gains the twin of its fast-path line: `spec-drift: N stale / M docs
(advisory)` when the ledger carries a run — always labeled advisory, never offered as the
explanation for a blocked phase — and **no line at all** when it does not. Silence is honest
when no mode was requested.

The statusline itself needed no change and got none: it renders `ledger["measured"]`
(phase, loop odometer, acceptance), and neither mode touches those facts — verified against
`uscha_progress.py`, which contains zero references to either key.

## Re-claim

The `proposal` markers from 1.58.0 are removed from `/uscha-mirador`'s SKILL: the claim now
matches what the template draws, because the template now draws it.
