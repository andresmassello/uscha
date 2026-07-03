# dev-loop-kit 1.19.0 — spikes formales: descartable por contrato (2026-07-03)

Décima y ÚLTIMA mejora del backlog PragProg (M10 de
`docs/analisis-pragmatic-programmer.md`; Tip 21 *"Prototype to Learn"* +
Topic 37 *"It's Playtime!"*). Con esta release, **las 10 mejoras del cruce con
The Pragmatic Programmer están resueltas** — 8 implementadas directas y 2
resueltas con decisión humana explícita entre opciones (M5 procedencia, M4 FSM
derivada). Convención elegida por el humano: prefijo **`spike/*`**.
Smoke suite: 121/121.

## La idea (la versión ejecutable de "make it clear this code is disposable")

- Un riesgo de incertidumbre ALTA en discovery dispara la pregunta: "¿amerita
  un spike time-boxed antes de congelar la SPEC?" (paso 10 de la agenda).
- El spike corre en una rama `spike/*` y su ÚNICO output legítimo es un
  **ADR con lecciones** — hechos que alimentan la SPEC, jamás código mergeable.
- El contrato es ejecutable, estilo INV-GOLDEN-01: `phase --require pr-ready`
  **rechaza cualquier rama `spike/*`** aunque los hechos del ledger den
  pr-ready — "escribí el ADR y arrancá limpio en una rama normal". Sin
  `--require` solo informa (consultar no gatea). Resuelve la tensión con
  Stone Soup sin romper spec-first.

## Engine (qa_ledger.py)

- `_spike_branch()`: `git symbolic-ref --short -q HEAD` (funciona antes del
  primer commit; detached HEAD o directorio sin git = sin veto, disclosed).
- `phase --require pr-ready`: veto de spike ANTES del veredicto; JSON expone
  `spike_branch`.

## Smoke

- **T41**: repo pr-ready por hechos PERO en `spike/*` → exit 1 con el mensaje
  del contrato · consulta sin `--require` → informa sin gatear · rama normal
  → pr-ready vuelve a pasar.

## El backlog PragProg, cerrado

M2 (1.10.0) · M9 (1.11.0) · M8 (1.12.0) · M3 (1.13.0) · M6 (1.14.0) ·
M7 (1.15.0) · M1 (1.16.0) · M5 (1.17.0) · M4 (1.18.0) · M10 (1.19.0).
Cada release: smoke verde → review fresco → hallazgos aplicados → triple
sync → commit único. Lo diferido consciente de cada una vive en su CHANGELOG.
