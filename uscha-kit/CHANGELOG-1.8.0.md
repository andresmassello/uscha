# dev-loop-kit 1.8.0 — adapter `type: cpp` (2026-07-02)

> Publicado junto con 1.7.0 y 1.9.0 en un único commit (no existe commit
> standalone de 1.8.0); la suite final de ese commit es 63/63. Los fixes que el
> review fresco de este adapter encontró están aplicados y documentados en
> CHANGELOG-1.9.0.

Séptimo lenguaje, UN parser nuevo: clang-tidy. Coverage vía gcovr→Cobertura (reusa
`cobertura_coverage`) y tests vía ctest `--output-junit`/GoogleTest (reusa
`junit_test_count` — el fixture de smoke usa el root PLANO `<testsuite>` para
ejercitar la rama que los demás types no tocan).

## Engine (qa_ledger.py)

- **`type: cpp`** — extensiones `.cpp .cc .cxx .c .h .hpp .hh .hxx`.
- Coverage: `gcovr --cobertura reports/coverage.xml` — **reusa `cobertura_coverage`**.
- Tests: `ctest --test-dir build --output-junit ../reports/junit.xml` (CMake ≥3.21;
  root plano) o `--gtest_output=xml:` (root envuelto) — **reusa `junit_test_count`**,
  ambas formas de root ya soportadas.
- **`parse_clang_tidy()`** — texto (`file:line:col: warning: msg [check-a,check-b]`):
  error→HIGH, warning→MEDIUM; checks de seguridad (`cert-*`, o que contengan
  `security`) con floor HIGH — misma disciplina que findsecbugs/eslint-security.
  Líneas sin `[check]` (diagnósticos crudos del compilador) → rule `diagnostic`.
  IDs con path preservado (`_mk_id_rel`).
- `ingest-gate`: branch cpp (`reports/clang-tidy.txt`, o `--clang-tidy`);
  combinado = `cpp-qa-gate`. Mismo contrato de ausencia.
- Guard UNMEASURED: los 7 types linteables.
- LOC: `test`/`tests` en el path, prefijo `test_` o sufijos `_test.cpp/.cc/.cxx`,
  `Test.cpp`. `SKIP_DIRS` += `cmake-build-debug`, `cmake-build-release`, `_deps`
  (FetchContent) — mismo trade-off global documentado.

## Nota honesta sobre C++

El ecosistema no tiene UNA convención de build (CMake/Bazel/make) — el kit no la
elige: pide que los REPORTES existan (Cobertura + JUnit + texto de clang-tidy) y el
cómo se generan vive en el adapter por-repo (`CLAUDE.md` del proyecto). Es el
contrato de siempre, explícito.

## Criterio pendiente (mismo contrato que python/node/go/rust/dotnet)

Dry-run de solo lectura contra un repo C++ real — entra sin repo de dogfooding.

## Diferido consciente

- rebuild: densidad de asserts. Perfiles A-E mecanizados. cppcheck (`--xml`) como
  segundo linter cpp si un repo real lo pide.
