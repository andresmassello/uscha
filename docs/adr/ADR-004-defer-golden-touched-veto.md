---
# a NEGATIVE decision: it defers a veto, so it governs no source. Declared
# explicitly so spec-drift reports NO-CODE rather than 'nobody mapped this'.
governs: []
---
# ADR-004: The golden-touched veto is deferred until a golden↔source mapping exists

## Status: Accepted
<!-- Still accurate: Phase 1 did ship without the veto. The condition this ADR
     named -- "deferred until characterize records a coverage mapping" -- is now planned
     in ADR-006 (the mapping is DERIVED BY MEASUREMENT, the veto is opt-in). Not superseded
     until that ships and its AC-GM criteria close green. -->

## Context
The fast-path handoff proposed `forbid_when_golden_touched`: deny the shortcut when the diff
touches any file *covered by* a golden suite. Implementing that requires the engine to answer
"which source files does this golden cover?" — and it cannot: `uscha-characterize` freezes
behavior and `golden-labels.json` classifies fixtures (`intended` / `observed-accidental`), but
**no artifact records which source modules a golden exercises**. Verified against the engine
before deciding (`_golden_label()` matches by fixture path only).

Options considered:
- **A) Defer the veto; rely on `protected_paths` for the direct case.** Chosen.
- **B) Coarse veto: any repo containing goldens → `DENY`.** Rejected: zero false ALLOWs, but
  it kills fast-path exactly in migration repos — the profile where uscha is most used.
- **C) Build the mapping now, inside Phase 1.** Rejected: it is a feature of its own (capture
  must record coverage; already-approved goldens have none and would be `UNMAPPED`, which per
  house style may NOT be read as "no golden touched" — that would be a false ALLOW). Folding
  it in doubles Phase 1 and delays the value that needs no mapping.

## Decision
Phase 1 ships **without** `forbid_when_golden_touched`. The direct case — the diff touching a
golden fixture itself — is already denied by `**/*.approved` in the default `protected_paths`.
The fine-grained case (touching *source code that a golden exercises*) is deferred until
characterize records a coverage mapping at capture time.

## Reasons
- A gate that cannot be measured must not be shipped as if it measured (rule 2:
  under-claim, then wire, then re-claim).
- The partial protection that IS measurable today (fixture paths) ships today.

## Consequences
+ Phase 1 stays small and every shipped signal is genuinely measured.
- A fast-path change can silently modify source that a golden covers; `golden-diff` still
  catches the divergence, but only when it next runs — later than a veto would have.
- Adds a future work item: characterize records `covers:` at capture; existing goldens
  migrate as `UNMAPPED` (distinct from "covers nothing").

## Implementation Plan
- Affected paths: none now (that is the point). Future: `uscha-characterize` SKILL.md +
  harness output, `qa_ledger.py fastpath-eval`.
- Tests: AC-FP-04 is reserved in ACCEPTANCE.md as deferred, so the numbering in the original
  handoff stays traceable.

## Verification
- [ ] `fast_path` config carries no `forbid_when_golden_touched` key in Phase 1, and docs make
  no claim about golden-covered sources (only about fixture paths).
- [ ] `**/*.approved` present in default `protected_paths` and exercised by AC-FP-03.
