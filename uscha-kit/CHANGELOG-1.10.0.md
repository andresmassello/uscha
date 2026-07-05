# dev-loop-kit 1.10.0 — acceptance trazable: AC-n cierra por testcase MEDIDO (2026-07-02)

Primera mejora del backlog PragProg (M2 de `docs/analisis-pragmatic-programmer.md`;
Topic 50 "Do What Works" + la anécdota Jeffries/Sudoku + Tip 94 "Find Bugs Once").
Ataca el modo de falla típico del agente: **pulir la métrica sin acercarse a la
solución**. El readiness deja de estar dominado por coverage/tests-verdes y pasa a
estar dominado por **criterios de aceptación cerrados con evidencia medida**.
Smoke suite: 68/68.

## La idea (measured beats narrated, ahora a nivel CRITERIO)

- Cada criterio de `ACCEPTANCE.md` lleva un ID estable: `- [ ] AC-01 — cuando X
  entonces Y`.
- Un criterio cierra **MEDIDO** solo cuando existe ≥1 testcase VERDE cuyo nombre
  lleva el tag (`test_ac1_x`, `testAC01X`, `"AC-01: ..."`) en los reportes JUnit
  que el engine ya ingiere — y **ningún** testcase taggeado en rojo (evidencia
  roja veta: fail-closed).
- El checkbox es RELATO; el testcase es HECHO. Un `[x]` sin test verde se
  reporta como `narrated_only` y NO cierra.

## Engine (qa_ledger.py)

- `_parse_acceptance_items()`: parser de checkboxes con ID opcional; IDs
  normalizados por número (`AC-01 == AC_1 == ac1` — los nombres de test de
  python/go no admiten `-`).
- `_ac_tags()`: scan de NOMBRES de testcase en los reportes JUnit por type
  (reusa el selector de ubicaciones vía `_junit_report_files()`, extraído para
  no duplicar la lista — surefire/gradle per-clase, junit-family, dual-file
  swift; flutter no emite JUnit → sus criterios no cierran medido, documentado).
  Boundaries explícitos en el regex del tag: `\b` NO sirve (`_` es word char y
  `test_ac1` quedaría invisible); soporta separador no-alfanumérico y camelCase.
- `readiness`: nueva dimensión **acceptance** (dominante, peso 30) = criterios
  cerrados medidos / criterios totales (un criterio sin ID no puede cerrar →
  cuenta como abierto). Pesos default rebalanceados:
  acceptance 30 · adr 15 · coverage 15 · static 20 · convergencia 10 ·
  integración 10 — el techo a coverage/verde es el anti-Goodhart. JSON expone
  `traceable/ids/measured_closed/narrated_only/measured_unchecked/untagged`;
  warnings en texto para narrated-only y sin-IDs.
- **Fallback legacy**: ACCEPTANCE sin ningún AC-ID → la dimensión cae al ratio
  de checkboxes con warning (adopción incremental, no rotura retroactiva).
- `spec-check --acceptance ACCEPTANCE.md`: la trazabilidad es estructura =
  FACT → bloquea: archivo ausente, cero criterios, CERO criterios trazables,
  IDs duplicados (normalizados). Criterios sueltos sin ID = advisory. Puede
  correr solo (sin `--spec`).

## Skills / docs

- `discovery`: ACCEPTANCE se genera con AC-NN secuenciales, nunca reusados;
  cada criterio pensado para ser cubrible por un test con nombre.
- `dev-loop`: al escribir los tests de un criterio, el tag AC-n va en el nombre
  del test; `spec-check --acceptance` al arrancar.

## Hardening (review fresco pre-commit, 10 hallazgos aplicados)

- `_ac_tags`: el tag ahora lee SOLO el nombre del testcase (nunca classname) —
  un módulo/clase que matchea "ACn" por coincidencia (`test_ac3_flow.py`) ya no
  contamina los OTROS tests del mismo archivo.
- `_AC_ID`: tolera IDs markdown-formateados (`**AC-01**`, `` `AC-01` ``) — antes
  degradaban en silencio a `id=None` y toda la trazabilidad caía a legacy.
- `readiness`: IDs duplicados en ACCEPTANCE cuentan **una sola vez** (antes un
  test verde podía cerrar "medido" tantos criterios como copias del ID).
- `readiness`: config pre-1.10.0 con `readiness_weights` explícitos que no
  conocían `acceptance` ya no la reciben inyectada por default — se excluye
  (peso 0) con warning hasta que el usuario la agregue o taggee AC-IDs (si no,
  duplicaba el peso de `adr` en silencio).
- `readiness`: `--section` sin match ahora avisa (`0 criterios en scope`) en
  vez de zonear en silencio adr+acceptance.
- `readiness`: ledger sin `config.repos` ya no crashea (KeyError) — usa
  `.get("repos", [])` como el resto del comando.
- `spec-check --acceptance`: pipear un SPEC por stdin junto con `--acceptance`
  ya no se descarta en silencio — se lee stdin salvo modo interactivo puro
  acceptance-only.
- `spec-check --acceptance --strict`: los criterios sin AC-ID ahora gatean
  `--strict` (antes el verdict imprimía "OK" con advisories pendientes).
- Documentado (no resuelto): reportes JUnit stale de maven/gradle pueden
  vetear/cerrar un AC sin evidencia vigente — mismo límite que
  `junit_test_count`, ahora con blast radius mayor. Mitigación real (mtime +
  correlación con el árbol de fuentes) diferida.

## Diferido consciente

- El resto del backlog PragProg (M1 regression-capture, M3 ledger atómico,
  M8 secret-scan, M9 tests fuera del presupuesto de simplicity, etc.) sigue en
  `docs/analisis-pragmatic-programmer.md` — una mejora por release.
