# uscha-kit 1.45.0 — the risk profile stops being a decoration (2026-07-21)

Release B of the field retrospective, and its deepest finding: `risk_profile` was declared in
config and read by **nobody** in the engine — "the difference between a methodology and a
convention." Designed front-to-back with `uscha-adr-refine` (five rounds of interrogation
before a line of code); see `docs/adr/ADR-001` and `ADR-002`. Smoke suite: 372/372.

## What it does

### `risk_profile` is a named preset that modulates the flow (ADR-001)
A profile is **not** a fixed table the engine imposes — that would contradict the provenance
doctrine (kit 1.17.0), where the human declares what gates and the engine holds no opinion of
its own. It is a **kit-shipped, overridable preset**: at config load, `risk_profile` expands
into knobs the config already understands (`qa_tools_order`, `coverage_threshold`,
`golden_required`), and any explicit `defaults` key wins per-key. The gating power it confers is
exactly the power a human already has by declaring those knobs — a preset with provenance, not
a new mechanism.

Default table (all overridable):

| Profile | `qa_tools_order` (required to converge) | `golden_required` | coverage_threshold |
|---|---|---|---|
| A | `[code-review]` | no | — |
| B | `[code-review, improve]` | no | — |
| C | `[code-review, judgment-day, improve]` | no | — |
| D | `[code-review, judgment-day, improve]` | **yes** | 70 |
| E | `[code-review, judgment-day, improve]` | **yes** | 80 |

- An **unknown** profile fails loud (`SystemExit`) — a declared risk level is never inert
  (INV-RISK-01, new in `CONSTITUTION.md`).
- **No** `risk_profile` → behavior byte-identical to before (backward compatible).
- The origin of each expanded key is tracked so a cap can label its provenance.

### `golden_required` — a declarable cap for "an approved golden must exist" (ADR-002)
A new readiness knob, declarable by **any** config (profiles D/E preset it on). When active and
**no approved `golden-diff` gate** was ever logged for a repo, the frozen baseline is ABSENT —
a measured fact — and that repo's readiness is capped at **49** (NOT READY, does not pass the
human merge gate). A present-but-FAILED golden is left to the existing BLOCKER path (no
double-cap). Provenance is three-way: `requerimiento (perfil E)` when it came from a profile,
`requerimiento (config)` when declared directly, exposed in `cap_source`.

## Scope
Engine-only. This makes the profile **weigh in the ledger and readiness** — it kills the inert
defect. The token-saving half (the `uscha-devloop` orchestrator actually SKIPPING sub-agents by
profile at run time) is orchestrator behavior, not deterministic engine logic, and is a named
follow-up. The profile does not touch `execution_policy` (routing), is global (not per-repo),
and never auto-classifies risk — the human declares it.

## Regressions
- Smoke **T86**: profile expands the knobs with a provenance marker; explicit config wins;
  unknown profile fails hard.
- Smoke **T87**: `golden_required` caps readiness to 49 when the golden is absent, with the
  right `cap_source` (profile vs config); with an approved golden or an explicit override, it
  does not fire.

## Note on the test suite
The installer/npm smoke checks still hardcode the version string, so this bump updated those
literals.
