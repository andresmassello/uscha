---
name: discovery
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
  precise canonical term: "Decís 'cuenta' — ¿el Customer o el User? Son cosas distintas."
- **Maintain a glossary in `CONTEXT.md`**, updated inline as each term is resolved. Only
  terms meaningful to domain experts; don't couple it to implementation details.

## The grilling agenda (walk the tree, propose at each step)

Resolve these in order; for each, propose first, then ask. Skip what references already
answer.

1. **Propósito / valor / por qué ahora.** What job does this remove? Cost of not doing it?
2. **Modelo de dominio.** Propose the core entities and their relationships. ("Del dominio
   deduzco estas entidades núcleo: … ¿te cierran o falta alguna?")
3. **Superficie de operaciones / API.** Propose the endpoints/operations and their
   contracts (idempotency, status codes).
4. **Decisiones grandes (→ ADR).** Propose 2–3 architecture options with trade-offs and
   a recommended default: persistence, protocol, idempotency, sync/async, multi-tenancy.
5. **Comportamiento y casos sucios.** Happy path, then failures, retries, partial states,
   concurrency, what must NOT happen.
6. **Restricciones inviolables (→ `CONSTITUTION.md`).** Domain + security + operation
   rules that can't be broken (money to the cent, no numbering gaps, never cross
   environments, secrets never logged, auth). Write/extend `CONSTITUTION.md` with these —
   one invariant per line, with a CWE reference where it maps. They feed the severity gate
   downstream, and a breach is a BLOCKER, never a trade-off.
7. **Out of scope.** Explicit boundaries with forward references.
8. **Acceptance / Definition of Done.** Concrete, checkable criteria + success metrics.
9. **Quality bar (→ config, kit 1.17.0).** "¿Qué nivel de calidad BASTA acá, y qué
   dimensiones son negociables (coverage, perf, seguridad)?" Propose thresholds fit for
   the risk profile (a payments core is not an internal dashboard). What the human
   declares goes into `dev-loop.config.json` (`defaults.coverage_threshold`,
   `defaults.readiness_caps`, `defaults.simplicity`) — a declared threshold reads as
   **requerimiento (config)** in the engine's output; an undeclared one stays a kit
   default (opinion) and is labeled as such. Declaring is committing the config.
10. **Riesgos residuales y dependencias.** What's uncertain, what must exist first.

## Files to write (lazily, inline)

- **`CONTEXT.md`** — domain glossary; create on first resolved term, update as you go.
- **`CONSTITUTION.md`** — project invariants no ADR/SPEC may violate (security with CWE
  refs, domain rules, operation). Create/extend from the "restricciones inviolables" step.
  This is the layer above the ADRs; a breach is a BLOCKER finding downstream.
- **`DOMAIN-MODEL.md`** — the proposed core entities and their relationships (the "shape"
  you proposed and the human approved). Distinct from the glossary: this is the model, not
  the vocabulary.
- **`SPEC.md`** — objetivo/valor, riesgo, scope/out-of-scope, comportamiento,
  entradas/salidas/errores, acceptance, test plan, operación, rollback.
- **`docs/adr/ADR-NNN-<slug>.md`** — one per durable decision. Format: Estado
  (proposed/accepted/deprecated/superseded) · Contexto · Alternativas · Decisión ·
  Consecuencias · **Implementation Plan** (affected paths, patterns to follow, tests to
  write) · **Verification** (`- [ ]` checkboxes a coding agent can check). The
  Implementation Plan makes the ADR an executable spec: the agent implements it without
  asking follow-ups. Number from the highest existing ADR.
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

> "Leé CONTEXT.md, SPEC.md, docs/adr/*.md y ACCEPTANCE.md. Antes de tocar código:
> 1) resumí el comportamiento esperado, 2) marcá ambigüedades o contradicciones,
> 3) proponé plan de archivos + tests. Implementá solo el scope de la SPEC. No cambies
> contratos fuera de SPEC ni edites la SPEC para que tu implementación parezca correcta."

Flow: `/discovery` (idea → package) → `/dev-loop` (build + QA + evidence) → human gate.

## Relationship to adr-refine

`discovery` is the greenfield front: you only have an idea, so the skill PROPOSES the
shape. `adr-refine` is the same interview applied to a KNOWN feature where the shape is
already clear and you only need precision. Both emit the same package; pick by starting
point.

## Tracked-markdown protocol

If a target `.md` already exists and is tracked, ask for its current version before
overwriting — never silently replace real progress.
