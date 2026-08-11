---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
---
# ADR-014: Fidelity is a vector of independent dimensions, and an advisory-class dimension can NEVER be registered as blocking

## Status: Accepted

## Context
Diamond's round-trip claim (`discovery(forward(specs)) ≈ specs`) is unmeasurable today, and a
single "semantic fidelity %" would hide everything that matters while inviting exactly the
kind of LLM-judged number the doctrine forbids from gating.

Options considered:
- **A) One blended fidelity score.** Rejected: a blend launders an advisory guess into a
  measured-looking number.
- **B) A vector of independently measured dimensions, with LLM-judged dimensions
  structurally quarantined as advisory.** **Chosen.**

## Decision
`qa_ledger.py fidelity` computes, from artifacts the engine already holds after
discovery + curation:

- `traceability` — share of canonical IDs with a resolvable path to code/tests (reuses the
  existing id/roundtrip machinery; this is the REAL part of the Diamond page today).
- `behavior` — golden/characterization pass rate from ingested evidence (clean-room grade
  where available).
- `contracts` — mechanically comparable interface facts (the Phase-1 `static` extractors'
  output) present in canonical vs present in code: match ratio.
- `curation_closure` — curated OBS / total OBS in the active delta.
- `unexplained_code` — **v0 deliberately crude: unit = source FILE.** Share of files with no
  path to any canonical item or preserved OBS. Symbol granularity is a future milestone,
  said in the docs rather than half-built. Crude and honest beats fine-grained and narrated.
  **Scoped to the delta's bound** (FR-001 finding, user decision): a discovery produced with
  `discover --path <sub>` is measured over `<sub>` only — mixing a bounded delta with a
  repo-wide denominator produced a number (0.93 on the installer field run) that answered a
  question nobody asked. The bound is recorded in the delta, so fidelity reads it and the
  scope is named in every dimension's provenance.
- `semantic` — if a skill-layer LLM comparison is ever wired, its value enters as
  `{class: "advisory"}` and **can never gate**.

**The quarantine is an ENGINE invariant, not a convention** (INV-ADVISORY-01, CONSTITUTION):
the gate/readiness machinery refuses to register any `advisory`-class dimension as blocking —
attempting it is an error, not a configuration. Every dimension carries per-dimension
provenance (which runs/artifacts produced the number), and the measured dimensions are
deterministic: same inputs, same numbers, no LLM anywhere in their path.

## Reasons
- A vector keeps each dimension refutable on its own evidence; a blend is refutable on none.
- Encoding advisory-never-gates in the engine survives context pressure, prompt drift and
  future contributors in a way prose cannot — the INV-GOLDEN-01 lesson applied to judgment.

## Consequences
+ Diamond's round-trip stops being rhetoric: five numbers, each with provenance.
- `unexplained_code` at file granularity over-fires on monolithic files (the golden-coverage
  lesson repeats by design; recorded so nobody reads over-firing as defect).
- A `semantic` dimension that can never gate may look decorative. It is: until measurement
  proves it, that is its honest rank (ADR-011's condition still stands).

## Implementation Plan
- Engine: `fidelity` subcommand; dimension registry with `class: measured|advisory`; the
  refusal path for advisory-as-blocking; per-dimension provenance in the output.
- Tests: smoke criteria `AC-FV-01..05` per the M1 handoff.
- FIELD-RUN-001 target: `uscha-kit/install-uscha.py` — real, bounded, born public (zero
  anonymization burden; the full delta publishes as-is). The private-fleet variant becomes
  FIELD-RUN-002 once the mechanism is proven.

## Verification
- [ ] fidelity emits every v0 dimension with per-dimension provenance (AC-FV-01)
- [ ] a file with no lineage → `unexplained_code` > 0 and the file named (AC-FV-02)
- [ ] configuring any advisory dimension as blocking → engine refusal (AC-FV-03)
- [ ] `curation_closure` < 1.0 iff uncurated OBS exist (AC-FV-04)
- [ ] measured dimensions deterministic: same inputs, same numbers (AC-FV-05)
- [x] fidelity respects the delta's `--path` bound; scope named in provenance (AC-FV-06)
