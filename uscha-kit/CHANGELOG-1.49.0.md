# uscha-kit 1.49.0 — the mirador tells what the ledger knows (2026-07-23)

Operator feedback, twice over: a field session reported "empty panels with no reason given",
and dogfooding on this repo landed the same verdict — *"me sabe a poco o confuso"*. Looking at
the rendered page made both complaints concrete: the biggest block was kit metadata identical
across projects, the method's crown jewel (measured acceptance) had no panel at all, and the
loop's story — the reason the kit exists — was one line. Smoke suite: 380/380.

## ACCEPTANCE replaces "Specifications"
The `specs` field had been a hardcoded `[]` since 1.32.0 (comment: the engine tracks AC-nn,
not SPEC-nnn) — a panel that could never fill, on every project, with a hint that read like a
todo. Gone. In its place, the engine's real currency: an **Acceptance — measured** panel,
criterion by criterion, with the status the engine computes (the template paints, never
derives):

- **measured** — closed by a green named test;
- **narrated — sin test** — ticked by hand, no green test backs it;
- **open** — neither.

The data was already inside `cmd_dashboard` (it captures `readiness --json` verbatim); the
release adds per-criterion `items` to the readiness acceptance block and passes the panel
through. When JUnit evidence is stale, the panel says how many reports were discarded and asks
for a re-run — it never presents stale green as current.

## The loop tells its story: burn-down per cycle
`loops[]` entries now carry the repo's REAL derived phase (`_derive_phase`, closing deferred
finding D-01) and a per-cycle `series`: findings reported / gated / fixed / deferred, straight
from the recorded steps. The mirador draws one line per cycle — `gated` hot while > 0, cool at
0 — so reading left to right answers *"is iterating helping?"* without opening the ledger.
**Agent steps only** (same filter as `_converged`): static-gate ingests carry below-gate noise
(a linter's 35 LOWs re-reported on every refresh) that drowned the trend, and the gates
already speak through readiness's own gate line.

## Less noise, honest voids
- **Execution policy demoted** to a collapsed drawer (same mechanism as sub-scores): it is
  kit routing, identical across projects — policy, not project state. It was the largest
  block on the page.
- **Constitution invariants**: a `null` status now renders dashed with "sin gate — no medido".
  A silent blank read as "fine", which is the exact lie the truth-pass forbids.
- The sample fallback DATA in the template was realigned to the real contract (it still
  showed `specs` and loop states the engine never emits).

Regressions: smoke **T95** — per-AC statuses measured/narrated/open, `specs` absent from the
contract, loops carry phase + an agent-only series that a static-gate ingest cannot pollute.
The dashboard contract check (T-mirador) updated to the new shape.
