# dev-loop-kit 1.27.0 — First-Time Yield: el KPI Lean que ya estaba en los datos (2026-07-04)

Origen: el handoff anti-ceremony+reuse+compliance, ítem 3 (parte pasiva). FTY
(First-Time Yield) es la métrica Lean clásica de calidad de proceso: qué fracción
del trabajo salió bien **al primer intento**, sin reprocesos. El ledger ya tenía los
datos (ciclos, regresiones, escalaciones) — sólo faltaba leerlos. Smoke suite: 161/161.

## Qué hace

- **`summary` reporta `first_time_yield`**: % de repos que pasaron QA **en el primer
  ciclo** — sin segundo pase, sin regresiones nuevas, sin escalación (resuelta o no: una
  intervención humana significa que NO salió a la primera). Derivado 100% de hechos ya
  en el ledger (`node["iterations"]` con su número de ciclo, `new_regressions`,
  `ledger["escalations"]`).
- Aparece en `summary` (texto + `--json` con `by_repo` detallado). Va en la
  retrospectiva.

## Por qué pasivo e informativo (NO gatea)

Cumple la meta-invariante anti-ceremonia (1.25.0): **cero paso humano nuevo** (sale de
datos ya registrados) y **no es otra pantalla** (una línea en el summary que ya existía).
Y es explícitamente **informativo, jamás gate ni dimensión del readiness**: FTY mide el
PROCESO (¿cuánto reproceso hubo?), no el ESTADO del resultado. Meterlo al readiness
confundiría las dos cosas — readiness reporta si el resultado está listo, FTY reporta
qué tan limpio fue el camino. Son ejes distintos y se reportan aparte (como churn).

## Definición (de hechos del ledger)

Un repo cuenta como *first-time yield* sii: entró a QA (tiene iteraciones) **y** su ciclo
máximo es 1 **y** cero `new_regressions` **y** no tuvo escalación. `pct = first_time /
repos_que_entraron_a_QA`. Repos que nunca entraron a QA no cuentan en la base.

## Smoke (T47, 3 checks)

Dos repos: uno limpio al ciclo 1 (first-time), otro que necesitó 2 ciclos → FTY 50%,
visible en texto y `--json`. Y una escalación sobre el repo limpio lo saca del yield
(→ 0%), probando que la intervención humana cuenta como reproceso.

## Nota: compliance-map DIFERIDO

El ítem 3 del handoff traía también `compliance-map` (tabla requisito↔gate para dominios
auditados). Se DIFIERE: es tooling de auditoría sin consumidor auditado real todavía —
construirlo ahora sería especulativo (choca con el YAGNI del propio kit). Entra cuando
haya un consumidor que lo pida; el diseño (proyección del ledger, genérico, "trazabilidad"
no "compliance") ya está pensado en el handoff.
