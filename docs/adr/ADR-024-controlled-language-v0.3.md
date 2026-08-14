---
governs:
  - tests/fixtures/controlled-language/
  - uscha-kit/tests/smoke-engine.sh
---
# ADR-024: Controlled-language v0.3 — replication across archetypes; the single-subsystem REDUCED either generalizes or it does not (controlled-language v0.3)

## Status: Accepted

## Context
The controlled-language arm has produced, in order: MIXED on one subsystem (v0.1, ADR-019),
a perfect null on the control archetype, and — after killing the generation confound with
same-generation re-runs of both arms — REDUCED with a −61% inter-compiler variance delta
(v0.2, ADR-021). That is one deconfounded positive on ONE subsystem (the guard). A single
positive replicates or it is an anecdote; the program's own doctrine (measured beats narrated)
applies to its most publishable number first.

v0.3 is a pure protocol replication: **zero engine change**. `lang-compare` already computes
the behaviour-first verdict; the archetypes, oracles and fixtures already exist in the bench.
What is new is data: fresh, same-generation, blind compilations of both arms for additional
archetypes.

## Decision
- **Replicate the deconfounded protocol on two more bench archetypes** (chosen for contrast
  with the guard: one state-heavy, one data-heavy — `state-machine` and `transformer`).
  *Amended before implementation:* the first draft named `parser`, overlooking that parser
  ALREADY IS a deconfounded datapoint — it served as the v0.2 control (same-generation, both
  arms, NO EFFECT). Re-running it would duplicate an existing measurement, not replicate the
  guard's positive. The parser control instead enters the v0.3 summary as the existing row it
  is. For each new archetype:
  - For each: author an **EARS+STE rewrite** of the canonical package (arm B). The human
    confirms "same semantic content" between arms — the stated limitation of the protocol,
    unchanged from v0.1/v0.2.
  - Dispatch **fresh same-generation blind compilations** of BOTH arms × 3 models
    (2 archetypes × 2 arms × 3 models = 12 runs). The blind rules are inherited verbatim:
    subagents see only the canonical package; Write-first mandate; `unresolved_intent`
    stamped VERBATIM from model returns; compiled artifacts never edited.
  - Judge each pair with the **shared withheld oracle** (byte-identical across arms) via the
    existing `lang-compare` — one verdict per archetype.
- **Report**: one generated report per archetype (existing renderer), plus a hand-written
  `CONTROLLED-LANGUAGE-V03.md` summary table: archetype · verdict · variance delta ·
  pass-rate delta, with the guard's v0.2 REDUCED and the parser control's NO EFFECT included
  as the existing rows they are — the aggregate counts every deconfounded archetype once. The program
  claim updates to "REDUCED in k of n deconfounded archetypes" — whatever k turns out to be.
  **A WORSE or NO EFFECT result publishes with the same prominence as a REDUCED.**
- **Tests**: smoke pins each archetype's verdict and deltas over the committed fixtures
  (AC-CL3-*), version-guarded per interpreter where a compilation's runtime behaviour differs
  by Python version (the 1.78.0 lesson — the fixture is evidence, the pin encodes what the
  instrument measures on each cell).

## Reasons
- One deconfounded positive is the weakest publishable claim in the program; replication is
  the cheapest way to either strengthen it into a pattern or demote it honestly.
- Zero engine change keeps the replication clean: the same instrument, pointed at more data —
  any verdict difference is the data, not the tool.

## Consequences
+ The controlled-language claim gets a sample size; MIXED/REDUCED stops resting on n=1.
+ Twelve more blind compilations become permanent fixtures (variance data for any future arm).
- Twelve blind runs is real dispatch cost, and a null/negative result is a live possibility —
  which is the point, and it ships either way.

## Verification
- [ ] Both new archetype pairs: arms compiled blind, same generation, oracle byte-identical
  across arms; `unresolved_intent` verbatim from model returns (AC-CL3-01)
- [ ] `lang-compare` verdict and deltas pinned per archetype over committed fixtures,
  version-guarded where runtime behaviour differs by interpreter (AC-CL3-02)
- [ ] The v0.3 summary states the aggregate as "k of n" with per-archetype rows; a negative
  archetype appears with the same prominence as a positive (AC-CL3-03)
