---
name: specloop-rubric
description: >
  Grade the change against the versioned RUBRIC.md (the ACCEPTANCE of the
  non-testable: conventions, error-handling sanity, API ergonomics, doc quality)
  and ingest the verdict into the ledger. This skill is a THIN ADAPTER for
  Claude Code: the portable core is templates/rubric-grader-prompt.md (works on
  Codex, Gemini CLI, Cursor, raw API, or a human) + the vendor-neutral JSON
  contract that `qa_ledger.py rubric-ingest` validates. Advisory by default;
  gates only when the human declares it. Invoke for "grade the rubric",
  "evaluá la rúbrica", "rubric pass".
allowed-tools: Read, Write, Glob, Grep, Bash
disable-model-invocation: false
---

# specloop-rubric — grade the non-testable against versioned criteria (adapter)

**Architecture note (read this first).** You are the Claude Code ADAPTER of a
vendor-neutral layer. The core is: `RUBRIC.md` (versioned criteria) + the JSON
contract + `qa_ledger.py rubric-ingest` (stdlib, runs anywhere). ANY runner can be
the grader — this skill just wraps the neutral prompt so Claude Code users get it
in one command. Never add Claude-specific behavior to the contract.

## Protocol

1. **Locate the rubric**: `defaults.rubric.file` in `dev-loop.config.json`, else
   `./RUBRIC.md`. If absent, offer to create one from `templates/RUBRIC.md` and STOP
   (the criteria are the human's to approve — propose, don't impose).
2. **Validate structure first** (facts block):

```bash
QL="./.claude/skills/specloop-devloop/qa_ledger.py"
[ -f "$QL" ] || QL="$HOME/.claude/skills/specloop-devloop/qa_ledger.py"
python3 $QL spec-check --rubric RUBRIC.md    # exit 1 = fix the rubric before grading
```

3. **Grade with ISOLATED context** — follow `templates/rubric-grader-prompt.md` to
   the letter: read ONLY the diff + RUBRIC.md (not the maker's reasoning, not the PR
   body). For every criterion emit `pass|fail`; **evidence `file:line` is mandatory
   for any verdict that affects the score** (a positive's pass, a negative's fail) —
   without it the engine discards the verdict. Anchors calibrate you; when in doubt,
   fail (the optimist bias is the failure mode this layer exists to counter).
4. **Write the contract JSON** to `reports/rubric-grade.json`:

```json
{"criteria": [{"id": "RB-01", "verdict": "pass",
               "evidence": "src/x.py:42 — ...", "note": "..."}]}
```

5. **Ingest** (the ledger validates IDs, applies evidence-or-nothing, computes the
   weighted score vs threshold, and persists — advisory by default):

```bash
python3 $QL rubric-ingest --repo <REPO> --report reports/rubric-grade.json \
  --iteration <N>            # add --gate ONLY if the human declared it
```

A below-threshold score with the gate declared (config `defaults.rubric.gate: true`
or `--gate`) blocks convergence and caps readiness ≤65 through the existing ledger
plumbing. Without the declaration it advises — never silently escalate it yourself.

## Non-negotiables

- **Maker ≠ grader**: never grade a change you authored in this same context. Run
  the grade in a fresh/isolated pass (that separation is the entire value).
- **Evidence-or-nothing**: a verdict without a `file:line` citation does not count —
  the engine enforces it, you comply with it.
- The rubric file is the HUMAN's criterion: propose edits, never rewrite it silently
  (tracked-markdown protocol applies).
- This layer never replaces the hard gates (tests, golden, gate-check, simplicity):
  it is the structured-guess layer — facts block, guesses advise.

## Relationship to the other skills

- `specloop-devloop` runs this in Phase 3b alongside gate-check when a rubric exists.
- `specloop-discovery` / `specloop-adr-refine` are where the human's quality criteria
  crystallize — a RUBRIC.md can be drafted there (step: quality bar).
