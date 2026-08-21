---
name: uscha-discovery
description: >
  Front of the methodology for greenfield work. From a general idea (plus optional
  reference docs, URLs, PDFs, or an existing codebase), grill the user ONE question at
  a time — each with your recommended answer — PROPOSING the system shape (domain model,
  API/operation surface, architecture options) so the human approves instead of authors.
  Write the spec package (CONTEXT.md, SPEC.md, docs/adr/*.md, ACCEPTANCE.md, RISKS.md,
  HANDOFF.md) directly to the repo as decisions crystallize. Invoke for "discovery",
  "modelá esto desde una idea", "solo tengo la idea, no sé el cómo todavía".
allowed-tools: Read, Write, Glob, Grep, WebFetch
disable-model-invocation: false
---

# discovery — from a bare idea to a writable spec package

The human brings the idea, the constraints and the reference material. **You bring the
shape.** Your job is to interrogate until there is a shared system shape, and to write
the documents as you go — not to ask the human to design the system for you.

## First contact (show ONCE, then never again)

**Only when this project has no uscha artifacts yet** -- no `QA-LEDGER.json`, no `SPEC.md` or
`ACCEPTANCE.md`, no `docs/adr/` -- open with this block, then start working. If any of those
exist, the operator already knows the method: skip it entirely and go straight to the
breadcrumb. Repeating it every run would be exactly the ceremony the method forbids.

```
[uscha · discovery · START]
Method: you bring the idea, the method builds the rest. Facts block, guesses advise;
        nothing closes on a checkbox, and the human approves the merge.
Here:   I grill you ONE question at a time, each with my recommended answer. You decide.
Output: CONTEXT.md · SPEC.md · docs/adr/*.md · ACCEPTANCE.md · RISKS.md
Next:   `/uscha-devloop` builds against the package. No code until the package exists.
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

`[uscha · discovery · <step> → <target>]`

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
[uscha · discovery · CLOSED]
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

## Non-negotiable principles

1. **One question at a time, each WITH your recommended answer.** This is the inversion
   that makes discovery work: you propose (entities, endpoints, architecture, a default
   decision), the human confirms or corrects. Never dump a list of 20 questions, and
   never ask the human to supply structure you can propose yourself.
2. **Explore instead of asking.** If a reference doc/URL/PDF, the existing codebase, or
   an existing `CONTEXT.md`/`docs/adr/` can answer a question, read it first. Only ask
   the human what genuinely requires their judgment.
3. **Propose the shape.** From the idea + references, propose the core entities, the
   operation/API surface, and 2–3 architecture options with trade-offs. Walk the design
   tree branch by branch, resolving dependencies between decisions one at a time.
4. **Grill, don't agree.** Surface contradictions, fuzzy/overloaded terms, missing
   failure modes and unstated constraints. A discovery where you agreed with everything
   failed.
5. **Write files lazily and inline.** Create a file only when you have something real to
   write, and update it the moment a decision crystallizes — don't batch to the end.

## Inputs

- **The idea** (required): what the human wants to achieve. It doesn't have to be
  complete or well-formed.
- **Reference material** (optional): manuals, PDFs, URLs, API specs. Read them with
  WebFetch/Read before proposing — they are how you propose an accurate shape.
- **Existing codebase** (optional): if present, explore it; respect `CONTEXT.md` and
  existing ADRs.

## Domain awareness (explore first)

- Look for `CONTEXT.md` (domain glossary), `CONSTITUTION.md` (project invariants) and
  `docs/adr/` and read them. The CONSTITUTION constrains every shape you propose — never
  propose anything that would violate it.
- **Sharpen fuzzy language.** When the human uses a vague or overloaded term, propose a
  precise canonical term: "You say 'account' — the Customer or the User? They're different things."
- **Maintain a glossary in `CONTEXT.md`**, updated inline as each term is resolved. Only
  terms meaningful to domain experts; don't couple it to implementation details.

## The grilling agenda (walk the tree, propose at each step)

Resolve these in order; for each, propose first, then ask. Skip what references already
answer.

0. **Project name (first).** The very first thing you ask: "What do we call this?" Write the
   answer to `uscha.config.json` as `"project": "<name>"` (create the config if absent). The
   mirador shows it prominently at the top and the dashboard reads it from there; if unset it
   falls back to the joined repo names.
1. **Purpose / value / why now.** What job does this remove? Cost of not doing it?
2. **Domain model.** Propose the core entities and their relationships. ("From the domain
   I deduce these core entities: … do they work for you, or is one missing?")
3. **Operation / API surface.** Propose the endpoints/operations and their
   contracts (idempotency, status codes).
4. **Stack and lifecycle (MANDATORY — before any stack/architecture decision is
   recorded).** The stack is not a given ("we use X"): it is a decision with an EXPIRY
   DATE. A major version is a family; support is granted to a MINOR line, for a window,
   by an upstream nobody in the room controls. Ask these one at a time, each with your
   recommended answer, and **FETCH the dates from the official source AS YOU ASK — never
   answer from memory**; record the URL and the day you checked:
   (a) the EXACT version of every runtime/framework/store (JDK, web framework, ORM, DB,
   Node, bundler, broker, cache) and its OSS/LTS end-of-support date, cited;
   (b) support window vs the declared go-live AND the expected operating life — does the
   line stay patched for the whole operation? If not, move it up BEFORE building: a major
   upgrade days before the milestone is the most expensive one there is;
   (c) major dependencies and the upgrade policy — who approves one, and when it is
   scheduled (aligned with the dev-loop's "zero new dependencies without approval");
   (d) development and observability tools the operator wants from day one (consoles, APM,
   admin UIs) — they CONSTRAIN versions, so ask early or they force the upgrade;
   (e) compatibility with reused legacy modules — the minimum version they support.
   The answers distil into the stack ADR with the dates INSIDE it, as the machine-readable
   `lifecycle:` frontmatter block (`component` / `version` / `eol` / `source` / `checked`,
   ISO dates; `eol: unknown` is allowed and reads as a NAMED absence, never a pass) — see
   `templates/docs/adr/ADR-stack-template.md`. The SPEC declares the milestone it is
   compared against: frontmatter `go_live: YYYY-MM-DD` or a `**Go-live:** YYYY-MM-DD` line.
   `qa_ledger.py spec-check` then reports, per component, `ok` / `expires before go-live` /
   `no EOL cited` / `no source cited` — ADVISORY, it never gates. It can see that a date
   was CITED; it cannot see whether the citation is TRUE. That part is yours.
5. **Big decisions (→ ADR).** Propose 2–3 architecture options with trade-offs and
   a recommended default: persistence, protocol, idempotency, sync/async, multi-tenancy.
6. **Behavior and dirty cases.** Happy path, then failures, retries, partial states,
   concurrency, what must NOT happen.
7. **Inviolable constraints (→ `CONSTITUTION.md`).** Domain + security + operation
   rules that can't be broken (money to the cent, no numbering gaps, never cross
   environments, secrets never logged, auth). Write/extend `CONSTITUTION.md` with these —
   one invariant per line, with a CWE reference where it maps. They feed the severity gate
   downstream, and a breach is a BLOCKER, never a trade-off.
8. **Out of scope.** Explicit boundaries with forward references.
9. **Acceptance / Definition of Done.** Concrete, checkable criteria + success metrics.
10. **Quality bar (→ config, kit 1.17.0).** "What level of quality is ENOUGH here, and which
   dimensions are negotiable (coverage, perf, security)?" Propose thresholds fit for
   the risk profile (a payments core is not an internal dashboard). What the human
   declares goes into `uscha.config.json` (`defaults.coverage_threshold`,
   `defaults.readiness_caps`, `defaults.simplicity`) — a declared threshold reads as
   **requerimiento (config)** in the engine's output; an undeclared one stays a kit
   default (opinion) and is labeled as such. Declaring is committing the config.
11. **Residual risks and dependencies.** What's uncertain, what must exist first.
    For each HIGH-uncertainty risk, ask (kit 1.19.0, Tip 21 'Prototype to Learn'):
    "Does it warrant a time-boxed spike before freezing the SPEC?" A spike runs on a
    `spike/*` branch and its ONLY legitimate output is an **ADR with lessons**
    (facts that feed the SPEC) — never mergeable code. The contract is executable:
    `phase --require pr-ready` refuses any `spike/*` branch, INV-GOLDEN-01 style.

## Files to write (lazily, inline)

- **`CONTEXT.md`** — domain glossary; create on first resolved term, update as you go.
- **`CONSTITUTION.md`** — project invariants no ADR/SPEC may violate (security with CWE
  refs, domain rules, operation). Create/extend from the "restricciones inviolables" step.
  This is the layer above the ADRs; a breach is a BLOCKER finding downstream.
- **`DOMAIN-MODEL.md`** — the proposed core entities and their relationships (the "shape"
  you proposed and the human approved). Distinct from the glossary: this is the model, not
  the vocabulary.
- **`SPEC.md`** — objective/value, risk, scope/out-of-scope, behavior,
  inputs/outputs/errors, acceptance, test plan, operation, rollback.
- **`docs/adr/ADR-NNN-<slug>.md`** — one per durable decision. Format: Status
  (proposed/accepted/**experiment**/deprecated/superseded) · Context · Alternatives · Decision ·
  Consequences · **Implementation Plan** (affected paths, patterns to follow, tests to
  write) · **Verification** (`- [ ]` checkboxes a coding agent can check). The
  Implementation Plan makes the ADR an executable spec: the agent implements it without
  asking follow-ups. Number from the highest existing ADR. Use `Status: Experiment` only
  for a bounded, reversible hypothesis that needs real feedback; include `Hypothesis`,
  `Feedback Signal`, `Review By` or `Review Trigger`, `Promote Criteria`, and
  `Rollback / Supersede Criteria`.
- **`ACCEPTANCE.md`** — Definition of Done as `- [ ]` checkboxes + success metrics. This
  is the file the readiness KPI measures downstream. Give EVERY criterion a stable
  traceable ID: `- [ ] AC-01 — when X then Y` (sequential, never reused). Downstream,
  a criterion only closes MEASURED when a green testcase carries its tag in the name
  (`test_ac1_x` / `testAC01X` / `"AC-01: ..."`) — write criteria so each one is
  coverable by at least one named test.
- **`RISKS.md`** — residual risks, assumptions, points needing human approval.
- **`HANDOFF.md`** — what to read before coding + hard "no hacer" rules + required evidence.

## Offer ADRs sparingly

Only write an ADR when ALL three hold (otherwise it's noise that buries the important ones):
1. **Hard to reverse** — changing your mind later has real cost.
2. **Surprising without context** — a future reader will wonder "why this way?".
3. **A real trade-off** — there were genuine alternatives and you chose one for reasons.

## Convergence — finish when

A shared system shape exists: entities, operations and big decisions taken (or recorded
as explicit assumptions), every failure mode has defined behavior, out-of-scope is
explicit, and the DoD is checkable. State plainly that it converged, then write/finalize
the package and the handoff.

## Handoff

End with the implementation handoff (works for a human, an agent, or CI):

> "Read CONTEXT.md, SPEC.md, docs/adr/*.md and ACCEPTANCE.md. Before touching code:
> 1) summarize the expected behavior, 2) flag ambiguities or contradictions,
> 3) propose a file plan + tests. Implement only the SPEC's scope. Do not change
> contracts outside the SPEC, and do not edit the SPEC to make your implementation look correct."

Flow: `/uscha-discovery` (idea → package) → `/uscha-devloop` (build + QA + evidence) → human gate.

That route is the **nominal** one, not the answer: the `Next:`/`Run:` you emit in the close block are DERIVED from the state you actually produced, and override it whenever an open experiment, an unclosed spike, an unapproved golden or a red gate stands in between.

## Relationship to adr-refine

`uscha-discovery` is the greenfield front: you only have an idea, so the skill PROPOSES the
shape. `uscha-adr-refine` is the same interview applied to a KNOWN feature where the shape is
already clear and you only need precision. Both emit the same package; pick by starting
point.

## Tracked-markdown protocol

If a target `.md` already exists and is tracked, ask for its current version before
overwriting — never silently replace real progress.
