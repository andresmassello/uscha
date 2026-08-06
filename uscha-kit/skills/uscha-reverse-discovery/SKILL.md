---
name: uscha-reverse-discovery
description: >
  Brownfield front of the methodology, for migrating/modernizing an EXISTING system. The
  inverse of discovery: the system already exists and its behavior IS the truth, so you
  EXTRACT facts instead of proposing shape. Produce ONLY facts — a system map (endpoints,
  contracts, dependency graph, module candidates via static analysis) and a golden suite
  captured mechanically at the boundaries — plus CANDIDATE specs in quarantine
  (discovery/, evidence + confidence mandatory), which NEVER promote without a human
  verdict in BEHAVIOR-LEDGER.md (ADR-009, INV-CURATION-01: the engine measures the gate).
  Invoke for "reverse-discovery",
  "migrar/modernizar este sistema", "caracterizar el sistema viejo antes de tocarlo".
allowed-tools: Read, Write, Glob, Grep, Bash
disable-model-invocation: false
---

# reverse-discovery — extract the facts of an existing system before migrating it

`uscha-discovery` is greenfield: you only have an idea, so you PROPOSE the shape. This is the
opposite. The system already runs; its observable behavior is the ground truth. **Facts
first, always — and what cannot be fact yet becomes a CANDIDATE in quarantine: evidenced,
confidence-tagged, and promoted to the contract only by a human verdict (ADR-009).**

## First contact (show ONCE, then never again)

**Only when this project has no uscha artifacts yet** -- no `QA-LEDGER.json`, no `SPEC.md` or
`ACCEPTANCE.md`, no `docs/adr/` -- open with this block, then start working. If any of those
exist, the operator already knows the method: skip it entirely and go straight to the
breadcrumb. Repeating it every run would be exactly the ceremony the method forbids.

```
[uscha · reverse-discovery · START]
Method: you bring the idea, the method builds the rest. Facts block, guesses advise;
        nothing closes on a checkbox, and the human approves the merge.
Here:   I EXTRACT facts and CANDIDATES from the system that already exists. Candidates stay quarantined until YOUR verdict promotes them.
Output: SYSTEM-MAP.md · DISCOVERY-SUMMARY.md -- endpoints, contracts, dependency graph,
        module candidates + discovery/ candidates + BEHAVIOR-LEDGER.md. The verdicts are yours.
Next:   `/uscha-characterize` freezes current behavior and a HUMAN approves the golden;
        only judged candidates reach the migration SPEC; the golden stays the oracle.
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

## The one non-negotiable: quarantine, not judgment (ADR-009)

A system map (from static analysis) and a golden suite (byte-captured) are FACTS —
verifiable, not opinions. What you read out of the code beyond that is a CLAIM, and an
LLM's claim about legacy code is plausible on the surface and divergent from reality —
the exact blind spot the golden exists to counter. The old rule banned authoring such
claims outright; ADR-009 renegotiated it: **you may author them as CANDIDATES, in
quarantine, and you may NEVER judge or promote them.**

- Every candidate lives in `discovery/`, with mandatory frontmatter: `evidence.type`
  (`test | code | inference`), `evidence.refs` (real `file:line(s)` — the engine resolves
  them; a ref that does not resolve makes the candidate invalid, named), and `confidence`
  (`inference` is ALWAYS `low`).
- **You capture; you do not judge.** Never decide whether a behavior is bug or feature —
  that is the verdict (`preserve` / `fix` / `undefined`), it belongs to the human, and it
  lands in `BEHAVIOR-LEDGER.md` with an ADR per verdict. You may present a candidate with
  its evidence and ASK; you may write the skeleton row once the human decides; the verdict
  itself is theirs.
- The gate is MEASURED, not promised: `qa_ledger.py curation-check` blocks the forward flow
  while any candidate lacks a verdict (INV-CURATION-01) — and a malformed candidate or a
  tampered ledger blocks harder (`exit 2`), because "could not validate" must never read
  as judged.
- The ledger is append-only (verified against git): reverting a verdict is a NEW row plus a
  new ADR, never an edit.

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

## Phase 3 — Candidates (claims, quarantined)

For every observable behavior the map + golden surface, emit one candidate file in
`discovery/` (`NNN-short-slug.md`): frontmatter per the section above, then a short
description of the behavior — what it does, not whether it should. Undesigned edge cases
are captured too, as `inference`/`low`. Then run:

```bash
python qa_ledger.py curation-check --repo <name>
```

Echo its output verbatim — it names invalid candidates and everything awaiting verdict.
The skill wires; the engine measures.

## Phase 4 — Curation (the human's verdicts)

Present one candidate at a time: the behavior, its evidence refs, its confidence. Ask for
the verdict. On each answer, append the ledger row (`| # | candidate | evidence |
confidence | verdict | ADR-RD-NNN |`) and write the skeleton `ADR-RD-NNN` (5-10 lines:
context, evidence, verdict, consequence) for the human to complete. Re-run `curation-check`
after the pass: exit 0 means every candidate is judged and the quarantine is clear.

## Phase 5 — Summary (facts, no opinion)

Write `DISCOVERY-SUMMARY.md`: the system map + the golden coverage report (which boundaries
are captured and approved, which are PARTIAL and why). This is the fact base the human reads
to write the migration SPEC. Do not editorialize.

## What you do NOT do (the human's job)

- Do NOT record a verdict, promote a candidate, or skip the ledger — the quarantine gate
  is the human's, and the engine measures it (INV-CURATION-01).
- Do NOT write the migration SPEC — only judged candidates feed it, and the human writes it.
- Do NOT decide the NEW structure (module boundaries, shared kernel, sync vs events). Those
  are forward decisions → `/uscha-adr-refine`.

## Guardrails

- `.approved` files are sacred and human-approved; the agent is mechanically forbidden from
  writing them (a `PreToolUse` hook on `**/*.approved.*` should enforce it).
- `.gitattributes`: `*.approved.* binary` (line endings must not create false diffs).
- Corpus insufficient → PARTIAL. Never claim coverage you did not exercise.

## Convergence — finish when

The map is complete (every boundary and dependency accounted for, or explicitly marked
unknown), the golden is captured and **human-approved**, every candidate has a verdict
(`curation-check` exits 0 — measured, not remembered), and the coverage report states
what is covered vs PARTIAL. State plainly that the facts are ready, then hand off.

## Handoff

> "Read SYSTEM-MAP.md, DISCOVERY-SUMMARY.md and BEHAVIOR-LEDGER.md, and inspect the
> approved golden. The facts are measured; the verdicts are yours and recorded. Now write
> the migration SPEC from the JUDGED candidates — `preserve` == golden must match, `fix` ==
> divergence declared by its ADR, `undefined` == out of contract — and take the partition
> decisions via /uscha-adr-refine."

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
