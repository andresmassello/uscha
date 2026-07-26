---
name: uscha-reverse-discovery
description: >
  Brownfield front of the methodology, for migrating/modernizing an EXISTING system. The
  inverse of discovery: the system already exists and its behavior IS the truth, so you
  EXTRACT facts instead of proposing shape. Produce ONLY facts — a system map (endpoints,
  contracts, dependency graph, module candidates via static analysis) and a golden suite
  captured mechanically at the boundaries. NEVER author an inferred SPEC or ADR of the old
  system; the human writes those reading your facts. Invoke for "reverse-discovery",
  "migrar/modernizar este sistema", "caracterizar el sistema viejo antes de tocarlo".
allowed-tools: Read, Write, Glob, Grep, Bash
disable-model-invocation: false
---

# reverse-discovery — extract the facts of an existing system before migrating it

`uscha-discovery` is greenfield: you only have an idea, so you PROPOSE the shape. This is the
opposite. The system already runs; its observable behavior is the ground truth. **You do
not invent anything — you characterize what is already there, as facts.**

## First contact (show ONCE, then never again)

**Only when this project has no uscha artifacts yet** -- no `QA-LEDGER.json`, no `SPEC.md` or
`ACCEPTANCE.md`, no `docs/adr/` -- open with this block, then start working. If any of those
exist, the operator already knows the method: skip it entirely and go straight to the
breadcrumb. Repeating it every run would be exactly the ceremony the method forbids.

```
[uscha · reverse-discovery · START]
Method: you bring the idea, the method builds the rest. Facts block, guesses advise;
        nothing closes on a checkbox, and the human approves the merge.
Here:   I EXTRACT facts from the system that already exists. I never invent its spec -- you write that reading my facts.
Output: SYSTEM-MAP.md · DISCOVERY-SUMMARY.md -- endpoints, contracts, dependency graph,
        module candidates. Facts only: the SPEC and the ADRs are yours to write.
Next:   `/uscha-characterize` freezes current behavior and a HUMAN approves the golden;
        only then do you write the migration SPEC, reading these facts + that golden.
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

`[uscha · reverse-discovery · <step> → <target>]`

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
[uscha · reverse-discovery · CLOSED]
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

## The one non-negotiable: produce ONLY facts

A system map (from static analysis) and a golden suite (byte-captured) are FACTS —
verifiable, not opinions. **You do NOT author a SPEC of "what it does" or ADRs of "why it
is built this way."** Those are inference, and if the agent writes them it encodes its own
(mis)reading of the code — the exact blind spot the golden exists to counter. The golden
is field truth; a SPEC the agent writes about legacy code is a claim. So this skill emits
facts, and the human infers meaning from them.

If you catch yourself writing a requirement or a rationale, stop: that belongs to the human
(and to `/uscha-adr-refine` for the FORWARD decisions), not here.

## Phase 1 — Map (fact)

Static analysis only. Extract, and write to `SYSTEM-MAP.md`:
- **Boundaries**: every public endpoint / operation / message topic, with its contract
  (request/response schema, status codes, idempotency where observable).
- **Dependency graph**: who calls whom (service→service, module→module, DB, external APIs).
  Flag cycles and hubs.
- **Module candidates**: current package/service structure and natural seams (this is
  observation of the CURRENT layout, NOT a proposal for the new one).
Everything here must be traceable to code. No "this seems to…", no guessed intent.

## Phase 2 — Characterize (fact)

Capture the golden at the system boundaries by running the ORIGINAL code with REAL inputs.
Delegate to the `uscha-characterize` skill; if it is not installed, follow its contract inline:
- Write a deterministic capture harness (you MAY author the harness).
- Normalize every non-determinism source before serializing: timestamps, seeds, map/set
  iteration order, GUIDs/auto-increment, concurrency, **the target locale**, and use
  deterministic serialization (sorted keys, fixed float precision, explicit encoding).
- Run the capture → `.received`. **STOP.** Return control to the human to review and
  approve the `.approved`.
- **You NEVER create, rename, or edit a `.approved` file** (INV-GOLDEN-01). It is field
  truth; only a human approves it.
- Corpus in order of value: real/recorded production inputs → hand-built edge cases →
  inputs of past bugs. A boundary whose corpus does not exercise its known branches is
  marked **PARTIAL**, never covered.

## Phase 3 — Summary (facts, no opinion)

Write `DISCOVERY-SUMMARY.md`: the system map + the golden coverage report (which boundaries
are captured and approved, which are PARTIAL and why). This is the fact base the human reads
to write the migration SPEC. Do not editorialize.

## What you do NOT do (the human's job)

- Do NOT write a SPEC of the old system's behavior — the golden IS the executable spec.
- Do NOT write ADRs of the old system's implicit decisions.
- Do NOT decide the NEW structure (module boundaries, shared kernel, sync vs events). Those
  are forward decisions → `/uscha-adr-refine`.

## Guardrails

- `.approved` files are sacred and human-approved; the agent is mechanically forbidden from
  writing them (a `PreToolUse` hook on `**/*.approved.*` should enforce it).
- `.gitattributes`: `*.approved.* binary` (line endings must not create false diffs).
- Corpus insufficient → PARTIAL. Never claim coverage you did not exercise.

## Convergence — finish when

The map is complete (every boundary and dependency accounted for, or explicitly marked
unknown), the golden is captured and **human-approved**, and the coverage report states
what is covered vs PARTIAL. State plainly that the facts are ready, then hand off.

## Handoff

> "Read SYSTEM-MAP.md and DISCOVERY-SUMMARY.md, and inspect the approved golden. These are
> FACTS about the current system. Now write the migration SPEC — behavior == golden,
> structure == the new module boundaries — and take the partition decisions via /uscha-adr-refine.
> Do not treat any of my output as a requirement or a rationale; those are yours to decide."

Flow (migration): `uscha-reverse-discovery` (facts) → human writes SPEC + `/uscha-adr-refine` (forward
module decisions) → `/uscha-devloop` (restructure; `golden-diff` + `ApplicationModules.verify()`
stay green the whole way) → readiness + human gate.

That route is the **nominal** one, not the answer: the `Next:`/`Run:` you emit in the close block are DERIVED from the state you actually produced, and override it whenever an open experiment, an unclosed spike, an unapproved golden or a red gate stands in between.

## Relationship to the other skills

- **discovery** (greenfield): you PROPOSE the shape from an idea. **reverse-discovery**
  (brownfield): you EXTRACT facts from a running system. Opposite direction, opposite trust
  model.
- **characterize**: the golden-capture sub-step this skill orchestrates in Phase 2.
- **adr-refine**: where the FORWARD decisions (the new module boundaries) are taken — this
  skill deliberately does not.

## Why this skill is safe by construction

It lives entirely on the FACTS side of the facts-vs-prose line: static analysis and
byte-capture, both verifiable. Unlike a prose-heuristic gate, there is no interpretation to
get wrong — so there is nothing fragile to break. If a step would require guessing, it has
left this skill's scope.

## Tracked-markdown protocol

If `SYSTEM-MAP.md` / `DISCOVERY-SUMMARY.md` already exist and are tracked, ask for the
current version before overwriting — never silently replace real progress.
