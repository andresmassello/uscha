# uscha-kit 1.32.0 — /mirador: vista bird's-eye + `dashboard --json` (2026-07-05)

La 8va skill (`uscha-mirador`) y un subcomando nuevo (`dashboard`, el 25º) que pinta el
estado del proyecto de un vistazo. **Read-only, determinista, cero narración del LLM.**
Smoke suite: 189/189.

## Pieza 1 — `qa_ledger.py dashboard [--json]`

Agrega SOLO estado que el ledger YA tiene al contrato `DATA` del template mirador
(readiness, subscores, phases, specs, adrs, inv, capas, loops, snapshots, evidence).
`--json` imprime el objeto; sin flags, un veredicto de una línea.

**Truth-pass estricto — under-claim, then wire.** Un campo sin fuente en el ledger sale
`null`/`[]` (el template degrada), **nunca se inventa**. La honestidad primero:

- **Real hoy**: `readiness` (score/band, reusando `readiness --json` VERBATIM — mismo KPI,
  sin drift), `subscores.coverage`, `subscores.{simplicity,waste,rebuild,golden}` desde
  los gates persistidos (`_gate_rollup`; `val` = null porque el ledger guarda pass/fail,
  no un score 0-100), `loops` (iters + estado por repo), `inv` (7 nombres fijos; status
  del gate donde mapea, si no null), `project`, `phases` (proyección determinista del
  readiness sobre los 8 nodos).
- **`null`/`[]` por diseño** (el engine no lo trackea): `specs` (trackea `AC-nn`, no
  `SPEC-nnn`), `capas` (no puntúa las 6 capas de verdad), `evidence` (steps[] es log
  plano). Cada uno destraba un panel el día que exista la fuente — quedan en el backlog.

## Add-ons aprobados (baratos y honestos)

- **ADRs** (`adrs`): glob read-only de `docs/adr/*.md` (`--adr-dir` configurable) — id de
  un token `ADR-<n>`, título del primer heading, status de una línea `Status:`. `[]` si no
  hay dir.
- **Time-lapse prospectivo** (`snapshots`): `readiness --record` (opt-in) persiste el
  readiness del momento en `ledger.readiness_history`. `readiness` sigue **read-only por
  default**; el historial se llena **solo hacia adelante** (no se backfillea). El dashboard
  lo consume, nunca escribe. `reached` = proyección determinista del score (como la band).

## Pieza 2 — skill `uscha-mirador`

`SKILL.md` + `mirador.template.html`. Flujo: corre `dashboard --json` → inyecta ese JSON
en el template reemplazando la región entre `/*MIRADOR_DATA_START*/` y
`/*MIRADOR_DATA_END*/` → escribe `mirador.html` en la raíz del proyecto → lo abre
best-effort (`start`/`open`/`xdg-open`), sin fallar en headless/CI. El demo del template
queda como **fallback offline**. El skill cablea, no calcula: los números vienen del ledger.

## Smoke (T53, 4 checks)

Contrato completo con las 12 claves; `specs`/`capas` `[]` (truth-pass); `adrs` del glob
(accepted→done, proposed→prog); `readiness` del dashboard == `readiness --json` (sin
drift); `snapshots` vacío hasta `readiness --record`, luego poblado (add-on prospectivo);
`inv` mapea el gate persistido por su kind REAL (`pit-check`→Tests efectivos, no un typo
mudo — hallazgo del review fresco).
