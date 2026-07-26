---
name: uscha-rubric
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

# uscha-rubric — grade the non-testable against versioned criteria (adapter)

**Architecture note (read this first).** You are the Claude Code ADAPTER of a
vendor-neutral layer. The core is: `RUBRIC.md` (versioned criteria) + the JSON
contract + `qa_ledger.py rubric-ingest` (stdlib, runs anywhere). ANY runner can be
the grader — this skill just wraps the neutral prompt so Claude Code users get it
in one command. Never add Claude-specific behavior to the contract.

## First contact (show ONCE, then never again)

**Only when this project has no uscha artifacts yet** -- no `QA-LEDGER.json`, no `SPEC.md` or
`ACCEPTANCE.md`, no `docs/adr/` -- open with this block, then start working. If any of those
exist, the operator already knows the method: skip it entirely and go straight to the
breadcrumb. Repeating it every run would be exactly the ceremony the method forbids.

```
[uscha · rubric · START]
Method: you bring the idea, the method builds the rest. Facts block, guesses advise;
        nothing closes on a checkbox, and the human approves the merge.
Here:   I grade what tests cannot: conventions, error handling, API ergonomics, doc quality -- against your versioned RUBRIC.md.
Output: a graded verdict ingested into the ledger (advisory unless you declared it a gate)
Next:   back to `/uscha-devloop`, or the human gate if the loop already converged.
Stop:   say so at any point -- whatever is already written stays.
```

**Bilingual by construction.** The labels (`START`, `Method`, `Here`, `Output`, `Next`,
`Stop`) stay VERBATIM in English -- they are the method's vocabulary and the smoke suite checks
for them mechanically, which is only possible if they never move. The wording after each label
is the canonical English; **render it in the operator's language**. If they are writing to you
in Spanish, the whole block reads in Spanish under English labels. Do not translate the labels,
do not leave the content in English when they are not writing in English.

Unlike the close block, `Next` here MAY name the nominal route: on a first run there is no
measured state to derive from yet, so the nominal path is the honest answer. From the close
block onward, derived state wins.

## Orientation markers (non-negotiable)

The operator must never have to ask "where am I?" or "what happens now?". Two markers, always.
They are navigation, not ceremony: one line per turn, one block at the end.

**Open every turn with a breadcrumb**, then the content:

`[uscha · rubric · <step> → <target>]`

- `<step>` — `Q<n>` for a question, `pass <n>` for a loop iteration, `step <n>` otherwise.
  Count what has actually happened. **Never write a denominator** (`Q4/12`): this phase
  converges, its length is not known in advance, and an invented total is exactly the kind of
  narrated number the method forbids. **When the ledger already measures the count** (the QA
  loop's `loop_count`), use the measured number — never keep a parallel tally of your own.
- `<target>` — the artifact this turn feeds (`SPEC`, `ADR-003`, `ACCEPTANCE`, `LEDGER`,
  `RECEIVED`, ...). Drop `→ <target>` only when the turn genuinely feeds none.

**Close with the close block ONCE, when the skill finishes** — not on every turn. Ending
without it is a defect, even when the phase converged cleanly:

```
[uscha · rubric · CLOSED]
Produced: <files actually written, or "nothing">
Blocks:   <what stands between here and the next phase, or "nothing">
Next:     <the next action, and why it is that one>
Run:      <the exact command or skill to invoke>
```

This is **not** the implementation handoff some skills also emit: that one is a prompt for
whoever implements next, this one is navigation for the human operator, and both can appear.

`Blocks` and `Next` are **derived from the state you just produced** — never copied from a
fixed route, **including any `Flow:` line in this file**. Those lines are the nominal path;
open ADR experiments, an unclosed spike, an unapproved golden or a red gate all change what
genuinely comes next, and the derived answer wins. If the next phase cannot start yet, name it
and say exactly what unblocks it.

Keep the CONTENT in the conversation's language, but keep the labels (`CLOSED`, `Produced`,
`Blocks`, `Next`, `Run`) verbatim — they are the method's vocabulary and the smoke checks them.

## Protocol

1. **Locate the rubric**: `defaults.rubric.file` in `uscha.config.json`, else
   `./RUBRIC.md`. If absent, offer to create one from `templates/RUBRIC.md` and STOP
   (the criteria are the human's to approve — propose, don't impose).
2. **Validate structure first** (facts block):

```bash
QL="./.claude/skills/uscha-devloop/qa_ledger.py"
[ -f "$QL" ] || QL="$HOME/.codex/skills/uscha-devloop/qa_ledger.py"
[ -f "$QL" ] || QL="$HOME/plugins/uscha/skills/uscha-devloop/qa_ledger.py"
[ -f "$QL" ] || QL="$HOME/.claude/skills/uscha-devloop/qa_ledger.py"
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

- `uscha-devloop` runs this in Phase 3b alongside gate-check when a rubric exists.
- `uscha-discovery` / `uscha-adr-refine` are where the human's quality criteria
  crystallize — a RUBRIC.md can be drafted there (step: quality bar).
