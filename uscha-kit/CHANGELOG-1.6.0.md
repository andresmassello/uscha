# dev-loop-kit 1.6.0 — adapter `type: go` (2026-07-02)

Tercer adapter consecutivo donde el costo baja porque el engine habla FORMATOS, no
lenguajes: el linter reusa `parse_checkstyle` (golangci-lint emite checkstyle) y los
tests reusan `junit_test_count` (gotestsum emite JUnit). Lo único nuevo: el parser del
cover profile nativo de Go. Smoke suite: 37/37 (31 previos intactos + 6 go).

## Engine (qa_ledger.py)

- **`type: go`**.
- **`go_coverage()`** — cover profile nativo (`go test -coverprofile=coverage.out`):
  formato `import/path/file.go:S.C,E.C numStatements hitCount`; cobertura por
  **SENTENCIAS** (la convención Go, no líneas). First match: `coverage.out`,
  `cover.out`, `reports/coverage.out`. Profile vacío (solo línea `mode:`) → 0.0
  fail-closed, nunca un verde inventado.
- Test count: **reusa `junit_test_count`** vía `gotestsum --junitfile` (root envuelto
  ya soportado).
- Linter: **reusa `parse_checkstyle` parametrizado** (`tool="golangci"`) — golangci-lint
  `--out-format checkstyle`; error→HIGH, warning→MEDIUM; gosec entra por el mismo
  reporte si está habilitado en la config del linter. Los IDs de finding llevan
  `golangci:` (los de Java siguen `checkstyle:` — sin migración de IDs).
- `ingest-gate`: branch go (`reports/golangci.xml` / `golangci.xml`, o `--golangci`);
  combinado = `go-qa-gate`. Mismo contrato de ausencia.
- Guard UNMEASURED: `maven`/`python`/`node`/`go`.
- LOC go: test = sufijo `_test.go` (la convención — los tests viven junto al código);
  prod = el resto. `SKIP_DIRS` += `vendor` (dependencias vendorizadas explotarían el
  LOC) y `testdata` (fixtures no compilables).

## Config / docs

- `test_command_go` (gotestsum + coverprofile) + repo de ejemplo `api-svc`;
  version 1.6.0 (triple sync).
- Kit README: tabla Go; SKILL.md types + `go test`; docs ES/EN tipos y versión.

## Smoke (tests/smoke-engine.sh)

- `repo-e` (`type: go`): cover profile 3/5 sentencias → 60.0%, gotestsum junit → 4
  tests, LOC prod=4/test=2 (`_test.go` junto al código), golangci checkstyle
  (error gateado HIGH + warning MEDIUM), UNMEASURED pre-ingest → medido post-ingest.

## Nota estructural (regla de tres cumplida)

Con 5 types, los dispatchers siguen siendo ifs de 3 ramas y cada adapter nuevo reusó
parsers existentes — la presión para refactorizar `type` → perfiles de reporte
(cobertura+junit+linters como config, no código) existe pero todavía no duele. Si
entra un 6º type o un type necesita MEZCLAR formatos, ese es el momento.

## Criterio pendiente (mismo contrato que python/node)

Dry-run de solo lectura contra un repo Go real — el adapter entra sin repo de
dogfooding detrás, mismo criterio abierto que 1.4.0/1.5.0.

## Diferido consciente (sin cambios)

- rebuild: densidad de asserts por test-file. Perfiles A-E mecanizados (`--profile`).
- Rust: cargo-llvm-cov emite Cobertura (reusa `python_coverage`) + cargo-nextest emite
  JUnit — entra cuando haya repo real.
