# CHANGELOG 1.35.0 — execution policy routing

## La idea

Uscha ya medía el estado, y Mirador ya mostraba telemetría observada de modelo/tiempo/tokens. Faltaba una capa distinta: **la política de ejecución** que le dice al operador qué está haciendo el método en cada fase y qué tier/modelo/effort conviene usar.

## Nuevo

- `defaults.execution_policy` en `uscha.config.json`:
  - `default`: tier/model/effort base.
  - `phases.<idea|disc|spec|adr|build|qa|verify|prod>`: `method`, `tier`, `model`, `effort`, `uncorrelated`.
- Nuevo subcomando read-only:
  - `qa_ledger.py execution-policy --phase qa`
  - `qa_ledger.py execution-policy --json`
- `dashboard --json` agrega:
  - `execution_policy` top-level.
  - `phase.execution` en cada nodo del trail.
- Mirador renderiza un panel **Execution policy** con metodología/tier/model/effort por fase.
- `uscha-devloop` ahora exige imprimir una línea antes de arrancar cada fase para que el humano vea la intención del método y la selección de modelo/effort.

## Doctrina

Esto **no** es un gate y **no** entra al score de readiness. Es metadata de orquestación/costo/riesgo. La regla sigue intacta: facts block, guesses advise; la política guía la ejecución, la evidencia decide.

## Smoke

- `bash uscha-kit/tests/smoke-engine.sh`: 199 ok / 0 fail.
- Nuevos checks:
  - T58: `execution-policy` devuelve metodología/model/effort y `dashboard` lo expone sin contaminar readiness.
  - T59: `mirador-render` preserva el panel bird's-eye de execution_policy.
