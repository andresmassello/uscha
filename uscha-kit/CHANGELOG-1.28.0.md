# dev-loop-kit 1.28.0 — acceptance medido: el "% terminado" que el kit puede firmar (2026-07-05)

Origen: la pregunta del humano — "¿se puede computar un % de proyecto terminado?".
Análisis: un % ponderado por etapa es progreso NARRADO y gameable (choca measured-beats-
narrated + anti-Goodhart). El único "% terminado" honesto es el **acceptance medido**:
criterios cerrados por un test verde name-tagged / total. El ledger ya lo tenía; faltaba
superficiarlo. Smoke suite: 177/177.

## Qué hace

- **`readiness` reporta `acceptance.measured_pct`**: el % de criterios AC cerrados MEDIDO
  (`measured_closed / total`), NO el ratio de checkboxes. En `--json` (campo aditivo) y en
  la **vista default** como una línea: `acceptance medido: 33.3% (1/3 criterios cerrados
  por test verde — medido, no gatea)`.
- **Honesto por construcción**: la línea aparece SOLO con trazabilidad AC-n
  (`acc_traceable and total`). Sin AC-IDs no hay % honesto → no se muestra nada (un %
  sobre checkboxes sin test sería narrado, justo lo que el kit rechaza). `measured_pct`
  es `null` en ese caso.
- **Informativo, jamás gatea**: es una lectura del hecho ya medido, no un gate ni una
  dimensión nueva. Cumple la meta-invariante anti-ceremonia (1.25.0): un número medido
  que "habla cuando importa" (hay criterios trazables), colapsado en readiness.

## Por qué NO un % ponderado por etapa

Se descartó explícitamente: asignar pesos a discovery/build/QA/… y mostrar una barra es
un burndown — progreso narrado ("en fase 5 de 8" no dice si lo hecho está correcto) y
gameable (tildar etapas mueve el número = el "done" prematuro que el método combate). El
"dónde estamos" ya lo da `phase` (FSM derivada); el "cuánto del spec está probado" lo da
este acceptance-%. Dos ejes medidos, ninguno narrado.

## Smoke (T29 extendido, 3 checks)

Sobre el fixture AC-trazable existente (AC-01 verde, AC-02 rojo, AC-03 sin marcar):
`measured_pct == 33.3` en `--json`; la línea `acceptance medido: 33.3%` visible en la
vista default; y —clave— con un ACCEPTANCE sin AC-IDs la línea NO aparece (honesto).
