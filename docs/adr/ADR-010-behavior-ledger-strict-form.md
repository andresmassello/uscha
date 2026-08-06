---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/.claude/skills/uscha-reverse-discovery/SKILL.md
---
# ADR-010: The behavior ledger is a human-readable markdown table with machine-enforced rules

## Status: Accepted

## Context
ADR-009's promotion gate needs a place where verdicts live. The originating handoff proposes
`BEHAVIOR-LEDGER.md`: an append-only table `candidate → evidence → confidence → verdict →
ADR`. For the gate to be *measured*, the engine must parse it — and the project already has a
"ledger" (`QA-LEDGER.json`) with entirely different rules.

Options considered:
- **A) Markdown table in `BEHAVIOR-LEDGER.md`, parsed by the engine with a strict shape.**
  **Chosen.**
- **B) JSON sidecar** (`behavior-ledger.json`). Easiest to parse, worst to review — and this
  is precisely the artifact the human must read in a PR, because it contains their verdicts.
- **C) Inside `QA-LEDGER.json`.** Rejected outright: the QA ledger is regenerable machine
  state; verdicts are human judgment with history. Mixing them puts the most valuable
  artifact inside the most disposable one.

## Decision
`BEHAVIOR-LEDGER.md` at the target project root. The precedent is `ACCEPTANCE.md` — the
kit's most proven pattern: a document humans read and review in PRs, whose rules the engine
measures.

- **Strict shape.** The engine parses the table; a malformed ledger is `exit 2`, a config
  error — never a silent degrade to "no verdicts", because under ADR-009's gate that silence
  would *unblock* the promotion the gate exists to guard (the `golden.scrub.json` posture).
- **Three verdicts, closed set**: `preserve` (promoted as-is; oracle requires identical
  output), `fix` (promoted describing the *correct* behavior; the oracle divergence is
  declared — consumed by slice 2), `undefined` (excluded from the contract, on record as
  deliberately unspecified). Anything else in the verdict column is malformed, not a fourth
  state.
- **Every verdict names its ADR** (`ADR-RD-NNN` in the target project). A row without an ADR
  ref is malformed — no verdict without its why.
- **Append-only, verified against git**: the rows present in `HEAD`'s version of the file
  must be a byte-identical prefix of the working version. Reverting a verdict is a NEW row
  plus a new ADR, never an edit — same philosophy as escalations, which resolve but never
  disappear. No git available → the append-only check reports UNMEASURED, never pass.

## Reasons
- The verdict table is the audit trail of every decision the legacy embodies — its whole
  value is that a human can read it and a reviewer can diff it. Markdown wins where it counts.
- Strict parsing plus fail-closed makes the human-readable choice safe: the usual cost of
  markdown (silent tolerance of typos) is exactly what `exit 2` removes.
- Naming: the collision with `QA-LEDGER.json` is resolved in documentation, not by
  sacrificing the artifact's legibility; the handoff's public name is kept.

## Consequences
+ One more parsed-markdown contract, on the most battle-tested pattern in the kit.
- A parser to maintain, and a format authors can get wrong — mitigated by the skill emitting
  skeleton rows and by `exit 2` refusing ambiguity.
- Byte-prefix append-only is deliberately blunt: reordering or reformatting old rows counts
  as tampering even when semantically innocent. Accepted — an audit trail that tolerates
  rewriting is not an audit trail.

## Implementation Plan
- Affected paths: `qa_ledger.py` (ledger loader + append-only check + the ADR-009 gate reads
  verdicts from here), `uscha-reverse-discovery` SKILL (curation writes skeleton rows),
  a template in `uscha-kit/templates/`.
- Patterns: `_load_scrub_rules` strictness; `_ac_tags`-style table parsing; git comparison
  via the careful call convention.
- Tests: smoke T120+ (`AC-RD-04..06`).

## Verification
- [ ] malformed ledger (bad column count, unknown verdict, missing ADR ref) → exit 2 (AC-RD-04)
- [ ] editing an existing row → append-only violation detected against HEAD, named (AC-RD-05)
- [ ] the three verdicts produce three distinct, verifiable promotion effects (AC-RD-06)
