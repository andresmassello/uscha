---
# a NEGATIVE decision: it rejects a proposed component, so it governs no source.
governs: []
---
# ADR-011: There is no shared behavior-extraction engine — spec-drift and reverse discovery stay separate instruments

## Status: Accepted

## Context
The originating handoff mandates a common module: *"spec-drift and discovery share the
behavior→spec extraction engine; drift invokes it incrementally, discovery in full mode. Do
not duplicate logic."* The mandate rests on a factual error: it was written imagining a
spec-drift that performs semantic extraction. The spec-drift that shipped (ADR-005, 1.58.0)
compares **git commit dates** between specs and the code they govern — deterministic,
advisory, ~150 lines of stdlib. There is no extraction engine to share and no API to adapt to.

Options considered:
- **A) Build the common module now.** A behavior→spec extraction component consumed by both
  features. Rejected: it would turn spec-drift — deliberately cheap, deterministic, advisory —
  into a client of an LLM component, the exact engine-executes-judgment inversion ADR-008
  just refused for the clean-room. "Don't duplicate" is false economy when the two share
  nothing: one compares timestamps, the other reads code and proposes.
- **B) Negative decision: no shared engine, reasons on record.** **Chosen.**

## Decision
Extraction is **skill** work (LLM, judgment), per ADR-009. Spec-drift stays exactly as built
(engine, dates, advisory). The handoff's conceptual identity — *"drift detection is reverse
discovery running incrementally; a legacy system is 100% drift"* — is recorded here as an
equivalence of **idea**, not of implementation: the same problem at different scales, served
by different instruments because one *advises about staleness* and the other *proposes
content*.

Re-unification is not forbidden — it is deferred behind a condition, the ADR-004 pattern: if
the slice-2 roundtrip ever grows semantic matching that proves itself by measurement, the
unification gets its own ADR with that evidence in hand. Until then, obeying a document that
never saw the code would be cargo cult.

## Reasons
- The mandate's premise is false in this codebase; building to it would manufacture the
  dependency it imagines.
- Advisory-cheap and generative-expensive have different failure economics: spec-drift can
  run on every mirador refresh precisely because it costs nothing and cannot hallucinate.
  Chaining it to an extraction component forfeits both properties.
- A deferral with named conditions has already proven it gets picked up cleanly (ADR-004 →
  ADR-006).

## Consequences
+ Spec-drift keeps its contract: deterministic, advisory, zero LLM, zero readiness impact.
+ Reverse discovery designs its extraction free of a compatibility constraint with a
  120-line date-diff.
- The conceptual symmetry stays unimplemented, and the "one engine, two cadences" line must
  NOT appear in published docs as a description of the mechanism (INV-TRUTH-01) — it is a
  vision statement until measurement says otherwise.

## Implementation Plan
- Nothing to build. This ADR constrains: no extraction module lands in `qa_ledger.py`, and
  spec-drift's implementation is not modified by the reverse-discovery slices.
- Tests: none of its own; ADR-009/010's regression criterion (AC-RD-07) already asserts
  spec-drift behavior is untouched.

## Verification
- [ ] slice-1 diff leaves `cmd_spec_drift` and its tests byte-untouched (checkable in review;
  AC-RD-07 covers the behavioral half)
