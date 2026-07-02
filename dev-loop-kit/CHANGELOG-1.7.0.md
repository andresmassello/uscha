# dev-loop-kit 1.7.0 — adapters `type: rust` y `type: dotnet` (2026-07-02)

> Publicado junto con 1.8.0 y 1.9.0 en un único commit (no existe commit
> standalone de 1.7.0); la suite final de ese commit es 63/63. Los fixes que
> el review fresco de este adapter encontró (blocker de clippy incluido)
> están aplicados y documentados en CHANGELOG-1.9.0.

Dos adapters en un release porque ambos REUSAN la infraestructura existente:
coverage vía Cobertura (`cobertura_coverage`, renombrado desde `python_coverage`) y
tests vía `junit_test_count`. Nuevo de verdad: `parse_clippy` (JSONL de cargo) y
`parse_sarif` (SARIF v2 — el formato universal de análisis estático). Incluye los
fixes del review fresco de 1.6.0.

## Rust (`type: rust`)

- Coverage: `cargo llvm-cov --cobertura --output-path reports/coverage.xml` —
  **reusa `cobertura_coverage`** sin cambios.
- Tests: cargo-nextest con reporter junit — **reusa `junit_test_count`**.
- **`parse_clippy()`** — `cargo clippy --message-format=json` (JSON Lines):
  `error`→HIGH, `warning`→MEDIUM; **`code: null`** (error de compilación de rustc,
  no un lint) → HIGH siempre — la lección del ruff/tsc, tercera aplicación.
  Los IDs preservan el path del span primario (`_mk_id_rel`).
- LOC: `tests/` = integración; los tests inline `#[cfg(test)]` cuentan como prod
  (limitación documentada de la clasificación por path). `target/` ya estaba en
  SKIP_DIRS (cargo y maven comparten el nombre).

## C#/.NET (`type: dotnet`)

- Coverage: coverlet.msbuild → Cobertura — **reusa `cobertura_coverage`**.
- Tests: `dotnet test --logger "junit;LogFilePath=reports/junit.xml"`
  (JUnitXml.TestLogger) — **reusa `junit_test_count`**.
- **`parse_sarif()`** — SARIF v2 (Roslyn vía `dotnet build /p:ErrorLog=...`):
  `error`→HIGH, `warning`→MEDIUM, `note`→INFO. El parser sirve para CUALQUIER
  herramienta que emita SARIF (semgrep, CodeQL, etc.) — inversión, no solo .NET.
- LOC: proyectos `*.Tests/` y archivos `*Test(s).cs` = test. SKIP_DIRS += `obj`,
  `TestResults`.

## Fixes del review fresco de 1.6.0 (incluidos acá)

- **BLOCKER**: la tabla Go del kit README había pisado el heading `## Instalación`
  — restaurado.
- **HIGH**: el comando documentado de golangci-lint usaba el flag v1
  (`--out-format`), **eliminado en golangci-lint v2** (2025) — documentado el flag
  v2 (`--output.checkstyle.path=...`) con fallback v1.
- **MEDIUM**: gotestsum pone `errors` SOLO en el root `<testsuites>` (un paquete
  que no compila tenía errors>0 invisibles) — `junit_test_count` ahora toma
  `max(root, suma de hijos)` por contador.
- **LOW**: `go_coverage` dedupea bloques repetidos (perfiles `-coverpkg` merged);
  IDs de golangci preservan el path repo-relativo (basename colisionaba en repos
  Go idiomáticos); nota de severidades de golangci en README.

## Trade-off documentado (global, igual que `coverage/` en 1.5.0)

`vendor/`, `testdata/`, `obj/`, `TestResults/` en SKIP_DIRS son globales: un paquete
fuente legítimamente llamado así en OTRO type queda fuera del LOC (métrica advisory;
la detección de reportes es por glob/paths y no se afecta).

## Nota estructural (regla de tres, re-evaluada en el 7º type)

Siete types y los dispatchers siguen siendo ifs por FORMATO (jacoco / cobertura /
lcov / cover-profile · surefire / junit / aproximado). El refactor a perfiles
declarativos sigue sin pagar: no eliminaría los parsers (el costo real) y agregaría
indirección. Se re-evalúa si un type necesita MEZCLAR formatos por config.

## Criterio pendiente (mismo contrato que python/node/go)

Dry-run de solo lectura contra repos Rust/.NET reales — ambos adapters entran sin
repo de dogfooding detrás.

## Diferido consciente (sin cambios)

- rebuild: densidad de asserts. Perfiles A-E mecanizados.
- C++: viable (gcovr emite Cobertura/lcov — parsers existentes; gtest/catch2 emiten
  JUnit; clang-tidy necesitaría un parser tipo mypy) — entra cuando haya repo real.
