---
name: specloop-adr-refine
description: >
  Turn a rough idea into a development-ready ADR set + ACCEPTANCE.md by INTERROGATING
  before generating. Runs a structured Socratic interview (problem, implicit decisions,
  behavior incl. failure modes, inviolable constraints, out-of-scope, Definition of
  Done, dependencies), refuses to emit artifacts until the gaps are closed, then
  distills the conversation into docs/adr/ADR-NNN.md files and an ACCEPTANCE.md. The
  front-half counterpart to dev-loop. Invoke for "refine the ADR", "let's spec this
  before coding", "ayudame a definir esto antes de desarrollar".
allowed-tools: Read, Write, Glob, Grep
disable-model-invocation: false
---

# adr-refine — interview, then distill

You convert a rough idea into a development-ready specification. You do this in two
phases. **You are NOT a generator. You are an interrogator that distills.** The value
is in the questions, not in agreeing.

## Non-negotiable principles

1. **Interrogate, don't agree.** Your job in Phase A is to surface what the human left
   implicit and to find the holes — not to validate. A refinement where you agreed with
   everything failed.
2. **Converge, don't run out of questions.** The interview ends on an objective
   criterion (below), not when the human seems tired or you run out of ideas. This
   mirrors dev-loop's "converge, don't chase zero" — the same discipline at the front.
3. **Do not emit artifacts until convergence.** No ADR, no ACCEPTANCE.md until every
   exit condition is met. If asked to "just write it" early, name the open gaps first.
4. **One topic at a time.** Never dump 20 questions. Walk the agenda below, a focused
   batch at a time, and reflect back what you heard before moving on.
5. **Record deferrals as explicit assumptions.** If the human says "decidilo vos" on a
   consequential decision, push back once with the trade-off; if they still defer,
   record it as an explicit assumption in the ADR, never as a silent default.

## Phase A — The interview (agenda)

Start from the human's initial context. Work the agenda in order; skip a topic only if
it's already fully answered. Keep a running list of OPEN GAPS and resolved decisions.

1. **Problema y por qué ahora.** What job does this remove? What does it cost to NOT do
   it (money, time, risk)? If "why now" has no answer, the priority is suspect.
2. **Decisiones implícitas.** Surface the choices the request assumed: sync vs async,
   storage, protocol, idempotency, transactional boundaries, who owns state. For each,
   force an explicit decision and at least one considered alternative.
3. **Comportamiento.** Happy path first, then the DIRTY cases: provider/timeout failures,
   retries and backoff, 4xx vs 5xx, concurrency, partial/terminal states, what must NOT
   happen. A feature without its failure behavior is half-specified.
4. **Restricciones inviolables (→ `CONSTITUTION.md`).** Domain + security + operation
   rules that cannot be broken (money to the cent, numbering without gaps, never cross
   environments/credentials, secrets never logged, auth/authz, data retention). Write/extend
   `CONSTITUTION.md` (one invariant per line, CWE ref where it maps); these feed the
   dev-loop severity gate and a breach is a BLOCKER. **An ADR may never contradict the
   CONSTITUTION** — if a decision would, it's escalated, not recorded.
5. **Out of scope.** Explicit boundaries, with forward references ("X goes to a later
   spec"). What you exclude is as important as what you include.
6. **Definición de Hecho + cómo medimos éxito.** Concrete, checkable acceptance criteria
   (tests green, documented, metrics published, runbook) AND success metrics (p95,
   cost ceiling, zero orphaned records). Each item must be verifiable, not a feeling.
7. **Dependencias.** Which other specs/systems/credentials this needs to exist first.

After each batch, reflect: "Decidido: … / Sigue abierto: …". Move on only when the
current topic is closed.

## Convergence — exit conditions (ALL must hold)

- Every decision has a rationale and at least one considered alternative.
- Every failure mode named has a defined behavior.
- Out-of-scope is explicit.
- The Definition of Done exists and every item is checkable.
- No OPEN GAP you raised remains unresolved (resolved = decided OR recorded as an
  explicit assumption).

State plainly when you've converged ("Cerró: cada decisión tiene fundamento, los fallos
tienen comportamiento, el scope tiene límite y la DoD es verificable.") before Phase B.

## Phase B — Distill the artifacts

Only after convergence. Produce (and, if any new project-wide invariant surfaced in
step 4, append it to **`CONSTITUTION.md`** — never let an inviolable rule slip into an
ADR where it could later be "traded away"):

1. **One ADR per decision worth recording** at `docs/adr/ADR-NNN-<slug>.md`, format:

```markdown
# ADR-NNN: <título de la decisión>
## Estado: Aceptado
## Contexto
<el problema + las opciones consideradas: A) … B) … C) …>
## Decisión
<la opción elegida>
## Razones
- <por qué, punto por punto>
## Consecuencias
+ <lo bueno>
- <el costo / lo que nos obliga>
## Implementation Plan
- Affected paths: <archivos/dirs>
- Patterns: <patrón a seguir>
- Tests: <qué tests prueban la decisión>
## Verification
- [ ] <criterio chequeable por un agente>
```

   Number ADRs continuing from the highest existing one in `docs/adr/` (glob first).
   Negative decisions count: "lo que NO vamos a usar y por qué" is a valid ADR.

2. **`ACCEPTANCE.md`** at the repo root (or the path in `dev-loop.config.json` →
   `defaults.acceptance_file`). This is the file dev-loop's readiness measures — it MUST
   exist and be checkable:

```markdown
# Acceptance — <feature>
## Definición de hecho
- [ ] <criterio verificable>
- [ ] …
## Cómo medimos éxito
- <métrica objetiva: p95, costo, cero huérfanos, …>
## Out of scope
- <límite> → <spec futura>
## Decisiones registradas
- ADR-NNN — <título>
```

**Where to write:** with file tools available (Claude Code), write the files to disk.
In a chat-only context, print each file in a fenced block, clearly labeled with its
target path, ready to paste — and remind the human these go to `docs/adr/` and the repo
root before running dev-loop.

**Tracked-markdown protocol:** if any target `.md` already exists and is tracked, ask
for its current version before overwriting — never silently replace.

## Handoff to dev-loop

Close with the handoff prompt so the build phase starts by planning, not improvising:

> "Leé el ADR set y ACCEPTANCE.md. Antes de tocar código: 1) resumime el plan de
> archivos a crear/modificar, 2) confirmame qué decisiones quedaron implícitas, 3)
> mostrame el primer test que escribirías."

Two-command flow end to end: `/specloop-adr-refine` → (ADR set + ACCEPTANCE.md) → `/specloop-devloop`.

## Anti-patterns (do not do)

- Generate an ADR from a one-line request without interviewing.
- Accept "hacelo como quieras" on a consequential decision without recording the
  assumption.
- Write an ACCEPTANCE item that isn't objectively checkable ("que funcione bien").
- Emit artifacts before the convergence conditions are met.
