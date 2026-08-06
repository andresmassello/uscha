---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/.claude/skills/uscha-reverse-discovery/SKILL.md
---
# ADR-009: The agent may author CANDIDATE specs of a legacy system — in quarantine, behind a measured promotion gate

## Status: Accepted

## Context
Reverse discovery (originating handoff: `HANDOFF-REVERSE-DISCOVERY.md`, sanitized here per
INV-ANON-01) adds the brownfield entry mode: legacy codebase → candidate specs → human
curation → forward flow with the legacy as oracle. Its Phase 1 requires the agent to *emit
candidate specs*, each tagged with `evidence` (`test | code | inference`) and `confidence`.

That collides with standing doctrine. The `uscha-reverse-discovery` skill states: *"NEVER
author an inferred SPEC or ADR of the old system; the human writes those reading your facts."*
The rule exists for a documented failure mode: LLM-inferred specs are plausible on the surface
and divergent from reality, and a divergent spec fossilizes bugs as features.

Options considered:
- **A) Keep the prohibition.** Agent produces only facts (system map, golden suite,
  `file:line` refs); the human writes every spec by hand. Maximum protection — and the
  bottleneck that makes the feature unusable at the scale where it matters: a 200-behavior
  legacy means 200 hand-written specs.
- **B) Renegotiate: the agent authors CANDIDATES in quarantine.** **Chosen.**

## Decision
Candidates live in `discovery/` and **are not specs**. Each carries mandatory frontmatter —
`evidence.type` (`test|code|inference`), `evidence.refs` (verifiable `file:line(s)` into the
legacy tree), `confidence` (`high|medium|low`; `inference` is always `low`). **Nothing is
promoted to the contract without a human verdict**, and that gate is **measured by the
engine**, not promised by the skill: a candidate without a verdict in the behavior ledger
(ADR-010) blocks the forward phase, fail-closed. Evidence refs that do not resolve make the
candidate invalid — named, never silently dropped.

The protection is not removed; it **moves**. "Never author" becomes "never promote without
judgment". The human stops authoring *text* and authors *verdicts* — `preserve` / `fix` /
`undefined`, each backed by a short ADR in the target project — which is where human judgment
actually pays. Discovery captures and evidences; **it never judges**: it does not decide
whether a behavior is bug or feature, and it records undesigned edge cases as
`inference/low` like everything else it cannot prove.

**Engine/skill split follows ADR-008 verbatim**: extraction and the curation conversation are
LLM judgment → they live in the `uscha-reverse-discovery` skill (evolved, its doctrine line
rewritten to this ADR). The engine owns only what it can measure: frontmatter validity, ref
resolution, ledger shape, and the promotion gate. There is no `discover` engine subcommand
that reads code and proposes — the engine ingests and verifies, it never generates.

## Reasons
- The quarantine keeps the original rule's *guarantee* (no inference reaches the contract
  ungoverned) while removing its *bottleneck* (the human as typist).
- A gate the engine measures cannot be skipped by a well-meaning skill under context
  pressure; a prose prohibition can. Same reasoning that produced INV-GOLDEN-01's hook.
- The verdict layer — formal, traceable, blocking — is the differentiator no surveyed tool
  has; the prohibition as written forbids the pipeline that leads to it.

## Consequences
+ Brownfield entry becomes usable at real-legacy scale, and every promotion is a recorded
  human act.
+ INV-CURATION-01 (CONSTITUTION) makes the gate non-negotiable above any future ADR.
- The skill's doctrine line changes meaning; its SKILL.md must be rewritten in the same
  change that ships the gate — never before (INV-TRUTH-01: no doc ahead of mechanism).
- Candidate quality is now a real attack surface: a plausible-but-wrong candidate that a
  tired human `preserve`s is the residual risk. Mitigated, not eliminated: evidence refs are
  mandatory and machine-checked, `inference` is always `low`, and low-confidence candidates
  block until explicitly judged.

## Implementation Plan
- Slice 1 (this ADR + ADR-010): candidate frontmatter validation + ref resolution + promotion
  gate in `qa_ledger.py`; `uscha-reverse-discovery` SKILL evolved (emit candidates, run the
  curation conversation, wire verdicts into the ledger).
- Slice 2 (separate release): declared expected divergences in `golden-diff` for `fix`
  verdicts; embedded spec-id; `roundtrip` coverage by id.
- Patterns: strict-shape loader (`_load_scrub_rules` family, exit 2 on malformed); conditional
  dashboard key; sidecar-fed per-criterion acceptance tests.
- Tests: smoke T120+, criteria `AC-RD-nn`.

## Verification
- [ ] candidate with valid frontmatter accepted; malformed frontmatter → exit 2 (AC-RD-01)
- [ ] evidence ref that does not resolve → candidate invalid, named (AC-RD-02)
- [ ] any candidate without a ledger verdict → forward blocked, reason names the candidate (AC-RD-03)
- [ ] feature unused (no `discovery/`, no ledger) → behavior identical to prior release (AC-RD-07)
