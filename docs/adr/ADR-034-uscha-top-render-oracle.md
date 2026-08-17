---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/uscha_top.py
  - uscha-kit/skills/uscha-devloop/uscha_top.py
  - uscha-kit/tests/fixtures/uscha-top/
  - uscha-kit/tests/smoke-engine.sh
---
# ADR-034: `render(state, size)` is a pure function and its oracle is golden frames — the same discipline the kit uses on itself, so a cheating renderer that shows 100% is caught by a snapshot, not by trust

## Status: Proposed

## Context
Decision #5, and handoff §1.5: `render(state, size) -> list[str]` is a pure function with no I/O.
Input (the keyboard) is a mockable layer; the terminal driver is not tested, the dispatch is. The
oracle is *golden frames*: the list of lines `render()` produces over a fixed JSON fixture at a fixed
size, snapshotted in the repo and asserted byte-identical.

This mirrors how the kit already proves itself: family-prefixed criteria in this repo close through
`smoke-engine.sh`'s own embedded `res["AC-..."] = ...` python-dict assertions, not through JUnit
ingestion (audit B.1). `uscha top`'s ACs follow that same precedent (see ADR-035 for why, and for the
future-work alternative of widening `_AC_TAG`). The golden-frame assertions live in the smoke suite
like every other family here.

## Decision
- **`render(state, size)` is pure**: it takes the parsed `top --json` object (the `state`) and a
  `(cols, rows)` size, returns `list[str]`, and performs no file read, no clock read, no subprocess,
  no environment lookup. Everything time- or environment-dependent is already resolved in the JSON by
  `cmd_top` (ADR-032). This is what makes the frame reproducible.
- **The oracle is golden frames.** For each fixture (FIXTURES.md) at each size, the exact list of
  lines is snapshotted under `uscha-kit/tests/fixtures/uscha-top/golden/` and asserted byte-identical
  by the smoke suite. A mismatch is a red criterion.
- **Two canonical sizes: 100×32 and 80×24.** 100×32 is the reference layout; 80×24 is the degradation
  floor — the layout must not break and the feed shortens first (the board and header are never the
  first thing sacrificed).
- **Negative honesty frames are first-class fixtures**, not incidental: a 23/24-PASS + 1-UNMEASURED
  fixture must render `96%` with the `· 1 unmeasured` suffix and never `100%`. This frame exists
  specifically to fail a renderer that rounds or drops the unmeasured obligation — it discriminates
  the cheating implementation (INV-TOP-01, INV-TOP-02).
- **Keyboard dispatch is tested through a mockable input layer.** The driver (`termios`/`msvcrt`) is
  not under test; the dispatch table (which key produces which state transition or which `curate`
  call) is. A test feeds a scripted key sequence and asserts the resulting state transitions and the
  exact `curate` argv emitted (no real ledger write needed for the dispatch assertion; the byte-equal
  write is a separate fixture, below).
- **The write-equivalence fixture** asserts the record the TUI's verdict path appends is byte-identical
  to a manual `qa_ledger.py curate` call with the same arguments (ADR-033). This is the proof that the
  TUI reimplements no append logic.

## Consequences / Risks
+ A pure `render()` plus golden frames makes the whole UI a deterministic, diffable artifact — the
  same property the ledger itself has. UI regressions surface as line diffs in review.
+ The honesty invariants are testable without a terminal: they are assertions over `render()` output.
- Golden frames are brittle by design — any intentional layout change updates the snapshots in the
  same commit (repo rule 5: engine/behavior change carries its smoke check). That brittleness is the
  point; it makes silent visual drift impossible.
- The golden frames are ASCII/VT text; they must stay ASCII-safe in the `.ps1`-adjacent sense is
  **not** required (these are fixtures, not shipped PowerShell), but the smoke suite that asserts them
  must parse under bash 3.2 — no `${`, no backticks, no quote inside a bracket expression in the
  heredocs that build the assertions (CLAUDE.md known gotcha).

## Verification
- [ ] `render(state, size)` is pure; golden frames byte-identical over fixtures at 100x32 and 80x24 (AC-T-19)
- [ ] honesty negative fixture (23/24 PASS + 1 UNMEASURED) renders 96% with the suffix, never 100% (AC-T-23, INV-TOP-01)

## What this ADR does NOT decide
- The JSON the renderer consumes — ADR-032.
- The verdict write it dispatches — ADR-033.
- The AC-id family the golden-frame criteria are numbered in, and whether they are ever JUnit-measured
  — ADR-035.
- The visual palette beyond the color-by-state contract already fixed in the spec (INV/AC level).
