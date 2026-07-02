# dev-loop-kit 1.5.0 — adapter `type: node` (TypeScript/JS) (2026-07-02)

El adapter más barato del roadmap: reusa el parser lcov (Flutter) para coverage y el
parser JUnit-envuelto (Python) para tests; lo único nuevo son los parsers de ESLint y
tsc. Smoke suite: 31/31 (24 previos intactos + 7 node).

## Engine (qa_ledger.py)

- **`type: node`** — TypeScript/JS (jest o vitest sobre Node).
- Coverage: `coverage/lcov.info` — **mismo parser que Flutter** (`flutter_coverage`,
  docstring generalizado).
- Test count: **`junit_test_count()`** (renombrado desde `python_test_count` — es de
  familia JUnit, no de lenguaje): jest-junit / `vitest --reporter=junit`, root envuelto
  `<testsuites>` soportado, first-location-wins.
- **`parse_eslint()`** — `eslint --format json`: severity 2 (error) → HIGH,
  1 (warn) → MEDIUM; reglas `security/*` con floor HIGH (como findsecbugs);
  **`fatal: true`** (error de parseo) → HIGH siempre — la lección del `code: null`
  de ruff (1.4.0). `ruleId: null` SIN fatal (directivas eslint-disable sin usar,
  default de ESLint 9) sigue la severidad del mensaje — nunca un falso blocker.
- **`parse_tsc()`** — `tsc --noEmit` texto (`file(line,col): error TSxxxx`):
  error → HIGH (un type error es rotura real); paths Windows con drive soportados.
  **Errores GLOBALES sin archivo** (TS18003/TS5023 — tsconfig roto) → HIGH con
  ubicación `?`: un tsc que no chequeó NADA jamás lee como gate limpio.
- IDs de finding node preservan el path repo-relativo (`_mk_id_rel`): los layouts
  sin `src/` (app/pages con decenas de `page.tsx`/`index.ts`) no colisionan por
  basename; los paths absolutos de eslint se relativizan a la base del repo.
- `ingest-gate`: branch node (`reports/eslint.json` / `reports/tsc.txt`, o
  `--eslint/--tsc`); combinado = `node-qa-gate`. Mismo contrato de ausencia.
- Guard UNMEASURED ampliado: `maven`/`python`/`node`.
- LOC node: test = `__tests__`/`tests`/`test` en el path o `*.test.*`/`*.spec.*`;
  prod = el resto. `SOURCE_EXT` node: `.ts .tsx .js .jsx .mjs .cjs`.
- `SKIP_DIRS` += `coverage` (el lcov-report HTML de jest contiene .js que
  contaminaría el LOC), `.next`, `.turbo`. **Trade-off documentado**: el set es
  global — un paquete fuente legítimamente llamado `coverage/` en cualquier type
  queda fuera del LOC (métrica advisory; la detección de lcov es por glob y no
  se afecta).
- `LICENSE` (MIT) agregada al repo y copiada dentro de `dev-loop-kit/` para que
  el zip la lleve.

## Config / docs

- `test_command_node` + repo de ejemplo `web-app`; version 1.5.0 (triple sync).
- Kit README: tabla TypeScript/JS; SKILL.md types + `npm test`; docs ES/EN
  actualizan tipos y versión vigente.

## Smoke (tests/smoke-engine.sh)

- `repo-d` (`type: node`): lcov 9/10 → 90.0%, junit envuelto → 7 tests,
  LOC prod=4/test=2 (.ts vs .test.ts), eslint (security floor + null fatal HIGH,
  prefer-const MEDIUM → reported=3 gated=2), tsc error → HIGH,
  UNMEASURED pre-ingest → medido post-ingest.

## Criterio pendiente (mismo contrato que el adapter python)

El adapter node NO tiene todavía un repo real de dogfooding detrás — entra por decisión
del autor pensando en el release público (audiencia TS/JS). El dry-run de solo lectura
contra un repo TS/JS real (coverage vs jest, test count exacto, eslint/tsc) queda como
criterio abierto — igual que el dry-run pendiente del adapter python (1.4.0).

## Diferido consciente (sin cambios)

- rebuild: densidad de asserts por test-file. Perfiles A-E mecanizados (`--profile`).
- Roadmap de adapters: Go (golangci-lint emite formato checkstyle — reusable),
  Rust (cargo-llvm-cov emite Cobertura — reusable). Entran cuando haya repo real.
