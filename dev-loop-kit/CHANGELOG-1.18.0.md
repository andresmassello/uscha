# dev-loop-kit 1.18.0 — phase: la FSM derivada del workflow (2026-07-03)

Novena mejora del backlog PragProg (M4 de `docs/analisis-pragmatic-programmer.md`;
Topic 29 *"Juggling the Real World"* — FSM como tabla de datos). Resuelta con
decisión humana explícita entre tres opciones: **FSM derivada** (ni la FSM
declarada del análisis original, ni solo-pr-gate, ni diferir).
Smoke suite: 117/117.

## La idea (measured beats narrated, aplicado a la FSM misma)

- El reframe clave: una FSM donde el agente DECLARA "entro a build/qa" es
  **estado narrado** — exactamente lo que el kit combate. Acá el estado se
  **COMPUTA** de los hechos del ledger; no existen transiciones ilegales que
  validar porque no hay nada que declarar.
- Reglas de derivación (precedencia): **escalated** (escalación abierta — el
  acto humano pendiente pisa todo) → **pr-ready** (convergencia + tests verdes
  medidos + 0 BLOCKER/CRITICAL) → **qa** (pasos registrados sin converger) →
  **build** (snapshots medidos, sin QA) → **plan** (ledger virgen).
- La "tabla de estados × eventos" del análisis original se convierte en estas
  reglas de derivación — documentadas en el código como datos, no prosa.

## Engine (qa_ledger.py)

- `phase --repo X` (subcomando 21): imprime el estado derivado CON su
  evidencia. `--require pr-ready` sale 1 si los hechos no alcanzan, listando
  exactamente qué falta ("el estado no se negocia, se construye"). JSON:
  `{phase, evidence, required, satisfied}`.
- `dev-loop` Phase 6: el PR se gatea con `phase --require pr-ready` ANTES de
  abrirse — la transición ilegal "PR sin convergencia" del análisis original
  ahora es un hecho bloqueante mecánico, que era todo el punto de M4.

## Smoke

- **T40**: ciclo de vida completo derivado — virgen→plan · snapshot→build ·
  QA sin converger→qa · pr-ready con findings abiertos→exit 1 · escalación
  abierta→escalated (pisa todo) · convergido+limpio→pr-ready.

## Diferido consciente

- El estado es per-repo; un estado agregado feature-level (todos los repos
  pr-ready + integración verde) se deriva componiendo — si el dogfooding lo
  pide como comando propio, se agrega.
