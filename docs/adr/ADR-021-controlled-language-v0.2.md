---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
---
# ADR-021: The controlled-language experiment grows a control arm and kills its confound — a converged archetype where NO EFFECT is the expected reading, and a re-scaffolded free-prose arm that isolates authoring from prompt (controlled-language v0.2)

## Status: Accepted

## Context
v0.1 (ADR-019, kit 1.76.0) measured a **MIXED** result on the guard: EARS+STE cut
inter-compiler variance −51% but did not reduce `unresolved_intent` and cost −2.9% mean
pass-rate. Two limitations were named at ship and both are now due:

1. **The prompt confound.** arm A reused M4's round-1 compilations, whose prompt scaffolding
   was close to — but not byte-identical with — the EARS arm's. The −51% could, in principle,
   be partly scaffolding. The review called this "asserted, not bounded."
2. **No control.** Every measured comparison so far ran on the one archetype with known
   divergence. An instrument that has only ever shown effects where effects were hoped for has
   never demonstrated it can show **nothing** — the null the verdict machinery treats as
   first-class has never been exercised on real data.

**Falsifiable expectations (stated before running, so the data can embarrass them):**
- **(a) Control arm.** The parser is a converged archetype (3/3 oracle-green from free prose in
  the bench). Re-authoring it in EARS+STE and recompiling blind should yield **NO EFFECT** —
  green stays 3/3 (nothing to improve) and the deltas stay within margins. If `lang-compare`
  shows `REDUCED` here it may be measuring prompt-shape or noise, not authoring; if it shows
  `WORSE`, EARS harmed a healthy spec. Either deviation is a finding about the *instrument or
  the language*, reported as measured.
- **(b) Confound kill.** Recompiling the guard's **free-prose** canonical with prompt
  scaffolding **byte-matched** to the EARS arm's (same template, only the canonical text
  differs) isolates authoring. If fresh-free vs controlled still shows the variance reduction,
  the v0.1 signal survives its confound; if the reduction collapses, v0.1's −51% was partly
  scaffolding and the honest number replaces it. **Both outcomes ship.**

## Decision
- **Arm layout** (under `uscha-kit/tests/fixtures/controlled-language/`):
  `parser-free/` (the bench parser's canonical, pinned IR, oracle, and its three existing blind
  compilations, byte-copied — provenance noted) · `parser-controlled/` (an EARS+STE re-expression
  of the same parser content, its own pinned IR, the **byte-identical** parser oracle, three new
  blind compilations) · `guard-free-r2/` (the guard's free-prose canonical/IR/oracle byte-copied
  from `free/`, three NEW blind compilations whose prompt scaffolding is byte-matched to the
  controlled arm's template).
- **Six new blind compilations** (Opus/Sonnet/Haiku × 2 arms), Write-first mandate, verbatim
  `unresolved_intent`, `compile-validate` against each arm's pinned IR. The parser comparison is
  scaffolding-matched **by construction** (both arms use the current template); the guard
  comparison becomes scaffolding-matched **by re-run**.
- **Two `lang-compare` runs recorded**: `parser-free` vs `parser-controlled` (the control) and
  `guard-free-r2` vs `controlled` (the de-confounded v0.1 question). Each lands in its own
  GENERATED file — `CONTROLLED-LANGUAGE-CONTROL.md` and `CONTROLLED-LANGUAGE-DECONFOUNDED.md` —
  beside the v0.1 `CONTROLLED-LANGUAGE-REPORT.md`, which stays as the confounded first run
  (amended at implementation: the reports are engine-generated and banner-marked, so a
  hand-merged multi-experiment file would violate its own do-not-hand-edit banner; three
  generated files keep every number a run artifact and the CHANGELOG narrates across them).
- **No engine change expected.** `lang-compare` already computes everything; the re-authoring
  honesty guard (byte-identical oracle) applies to both new comparisons. Smoke T129 extends to
  pin the two new measured verdicts once measured.

## Reasons
- A control that can show nothing is what makes the instrument's somethings credible.
- Killing the named confound converts v0.1's "well beyond plausible scaffolding noise"
  (assertion) into a measured comparison — the difference between defending a number and
  replacing it.

## Consequences
+ Whatever the outcomes, the controlled-language claim gains what it lacked: a null baseline
  and a de-confounded effect size.
- Six more compilations; the parser-controlled EARS authoring is one more chance to smuggle
  content — the byte-identical-oracle guard and the review watch it.

## Verification
- [ ] parser-controlled is an EARS+STE re-expression with its own IR (differs from
  parser-free's) while the oracle is byte-identical; all six new compilations compile-validate;
  no compiler input references any oracle (AC-CL2-01)
- [ ] the control comparison (parser-free vs parser-controlled) runs and its measured verdict
  and deltas are recorded and pinned in the suite (AC-CL2-02)
- [ ] the de-confounded comparison (guard-free-r2 vs controlled) runs with byte-matched
  scaffolding; its measured verdict and deltas are recorded and pinned, and the report names
  what happened to v0.1's −51% (survived, shrank, or collapsed) (AC-CL2-03)
- [ ] CONTROLLED-LANGUAGE-REPORT.md carries both experiments plus the re-labelled v0.1 run;
  every number traces to a run (AC-CL2-04)
