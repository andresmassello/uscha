---
name: uscha-characterize
description: >
  Capture a golden / approval suite of a module's CURRENT behavior — the one artifact the
  agent must NOT author. Run the ORIGINAL code with real inputs through a deterministic
  harness, emit .received, and STOP for human approval; never create or edit a .approved
  file. Used before any migration/modernization to freeze pre-change behavior as field
  truth. Invoke for "characterize", "golden-capture", "capturá el comportamiento viejo".
allowed-tools: Read, Write, Glob, Grep, Bash
disable-model-invocation: false
---

# characterize — freeze the current behavior as field truth (the agent does not author it)

The golden suite is the ONE piece of the loop the agent cannot author, and that is exactly
its reason to exist. If you write the golden by reasoning about what the code "should"
return, you encode the same partial understanding that loses logic silently. **You capture
what the code DOES, mechanically, by running it — never what it should do.** You may write
the capture harness; you may NOT create, rename, or edit any `.approved` file.

## First contact (show ONCE, then never again)

**Only when this project has no uscha artifacts yet** -- no `QA-LEDGER.json`, no `SPEC.md` or
`ACCEPTANCE.md`, no `docs/adr/` -- open with this block, then start working. If any of those
exist, the operator already knows the method: skip it entirely and go straight to the
breadcrumb. Repeating it every run would be exactly the ceremony the method forbids.

```
[uscha · characterize · START]
Method: you bring the idea, the method builds the rest. Facts block, guesses advise;
        nothing closes on a checkbox, and the human approves the merge.
Here:   I run the ORIGINAL code against real inputs and freeze what it does today.
Output: tests/golden/*.received -- and I STOP: a HUMAN approves the .approved, never me
Next:   you approve the goldens, then `/uscha-devloop` migrates against them.
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

`[uscha · characterize · <step> → <target>]`

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
[uscha · characterize · CLOSED]
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

## Inputs

- **Target module** + a **corpus source**: a path to input fixtures, or a reference to
  (anonymized) production data. The golden is only worth as much as the corpus (see below).

## Phase 1 — Capture harness (you write this)

Generate a deterministic harness that runs the ORIGINAL module over the corpus and
serializes ALL observable output. Same input → same `.received`, byte for byte.

## Phase 2 — Non-determinism checklist (emit + normalize BEFORE serializing)

Control every one of these, or the diff lies. Output the checklist applied:
- [ ] **Timestamps / dates** — frozen clock or stable placeholder.
- [ ] **Random / seeds** — fixed seed or mocked generator.
- [ ] **Map/set iteration order** — sort keys before serializing.
- [ ] **GUIDs / DB auto-increment** — normalized or excluded from the snapshot.
- [ ] **Concurrency** — thread order must not leak into the output.
- [ ] **Target locale** — decimal separator, date format, culture. **Mandatory and
  explicit.** A golden built on one machine and run on another with a different locale
  breaks entirely (Windows/SQL Server: high risk).
- [ ] **Deterministic serialization** — JSON with sorted keys, fixed float precision,
  explicit encoding. Identical byte-for-byte when behavior is identical.

## Phase 3 — Run the capture

Execute the harness → generate `.received` files.

**Declare volatile fields BEFORE approval (kit 1.15.0).** If the ORIGINAL code emits
values that vary between correct runs and cannot be made deterministic at the source
(timestamps, request ids, GUIDs from a layer you cannot touch), declare scrub rules in
`golden.scrub.json` at the fixtures root:

```json
{ "rules": [
    {"pattern": "\\d{4}-\\d{2}-\\d{2}T[0-9:.+Z-]+", "replace": "<TIMESTAMP>"},
    {"pattern": "requestId=[0-9a-f-]{36}", "replace": "requestId=<UUID>"} ] }
```

`golden-diff` masks BOTH sides with these rules before comparing (text only; binary
stays byte-for-byte) and reports every scrub-match separately (`N via scrub`) — masking
is never invisible. Prefer fixing determinism at the source (Phase 2 checklist); scrub
is for what you genuinely cannot control. The rules file is part of what the human
approves in Phase 4 — gate-check flags any later edit to it (a broadened rule can mask
real divergence).

## Phase 4 — STOP for human approval

Return control to the human to review and approve the `.approved` — and, if present,
`golden.scrub.json` (the scrub rules are contract, same as the goldens). **The skill
ends here.** It does NOT auto-complete approval, and it does NOT create any `.approved`
file.

## Corpus — where the inputs come from (critical)

The golden only protects the paths you exercise; what gets lost is usually a rare path.
Sources, in order of value:
1. **Real production samples** (anonymized if needed) — the true distribution, including
   cases nobody knew existed.
2. **Hand-built edge cases** — known limits (zeros, boundaries, error states, rare
   combinations of inputs).
3. **Inputs of past bugs** — every historical bug is a golden input.
A module whose corpus does not exercise its known branches is marked **PARTIAL**, never
covered.

## Guardrails (non-negotiable)

- The skill STOPS at the approval point (Phase 4); it never creates/renames/edits `.approved`.
- A `PreToolUse` hook on `**/*.approved.*` should make agent writes mechanically impossible
  (see `hooks/block-approved-writes.py` + the settings snippet in the kit).
- `.gitattributes`: `*.approved.* binary` — line endings must not create false diffs
  (Windows/SQL Server).

## Acceptance criteria

- The skill ends at Phase 4 with no `.approved` created or renamed.
- The harness is deterministic (same input → same `.received` byte for byte).
- The output includes the non-determinism checklist that was applied.

## Harness stack

- **Java** → ApprovalTests.Java (`com.approvaltests:approvaltests`, JUnit 5 / JDK 21);
  `JsonApprovals.verifyAsJson()` for structured responses, `WithTimeZone`-style helpers
  to freeze time/locale. For read-only migrations, the "old query vs new query against prod"
  pattern applies.
- **C++ / other** → a fixtures dir + a deterministic serializer + a diff runner (no
  comfortable native ApprovalTests; go custom).
- For system I/O, a fixtures dir + custom runner that normalizes and diffs is often better
  than relying on the library alone.

## Relationship to the other skills

- **reverse-discovery** orchestrates this skill as its Phase 2 (golden capture at the
  boundaries).
- The captured `.approved` is the arbiter that `qa_ledger.py golden-diff` byte-compares
  against during `/uscha-devloop`.
- If you maintain `golden-labels.json`, classify approved fixtures as `intended`,
  `observed-accidental`, or leave them `unknown`; labels explain intent but never
  replace the byte comparison.

## Tracked-markdown / tracked-golden protocol

Never overwrite an existing approved golden. If a `.received` already exists, regenerate it;
if a `.approved` exists, it is the human's — leave it untouched and surface the diff.
