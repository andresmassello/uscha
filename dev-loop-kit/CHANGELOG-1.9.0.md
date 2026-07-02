# dev-loop-kit 1.9.0 — adapters `type: gradle` (Kotlin/JVM) y `type: swift` + fixes de los reviews 1.7.0/1.8.0 (2026-07-02)

Los dos adapters más baratos hasta ahora: **CERO parsers nuevos**. Todo es reuso
de formatos ya soportados en paths nuevos. Nota clave: **Kotlin sobre Maven ya
funcionaba con `type: maven`** (`.kt` está en SOURCE_EXT maven desde 1.0) —
`gradle` cubre el caso común Gradle. Smoke suite: 63/63.

## Engine (qa_ledger.py)

### `type: gradle` (Kotlin/JVM + Java-sobre-Gradle)

- Extensiones `.kt .kts .java`. LOC: `src/main` = prod; `src/test` y source
  sets custom (`src/*Test`: integrationTest, functionalTest) = test.
- Coverage: **reusa el parser JaCoCo de maven** (`_jacoco_line_counter`) en los
  paths Gradle (`build/reports/jacoco/test/jacocoTestReport.xml`).
- Tests: **reusa la suma per-clase de surefire** — `maven_test_count` y
  `gradle_test_count` ahora comparten `_perclass_xml_count()`; los
  `build/test-results/**/TEST-*.xml` de Gradle son el mismo formato.
- Linter: **detekt** emite formato checkstyle — `parse_checkstyle(tool="detekt")`
  parametrizado, igual que golangci. `--detekt` explícito o por type;
  combinado = `gradle-qa-gate`.

### `type: swift`

- Extensión `.swift`. LOC: convención SwiftPM (`Sources/` prod, `Tests/` +
  `*Tests.swift`/`*Test.swift` test).
- Coverage: **reusa el parser lcov** (Flutter/node) — `llvm-cov export
  -format=lcov` sobre el `.profdata` de `swift test --enable-code-coverage`.
- Tests: **reusa `junit_test_count`** — `swift test --xunit-output
  reports/junit.xml` emite JUnit directo; el archivo hermano
  `junit-swift-testing.xml` (Swift Testing) se SUMA (ver fixes 1.9.0).
- Linter: **SwiftLint** también emite checkstyle —
  `parse_checkstyle(tool="swiftlint")`. `--swiftlint` o por type;
  combinado = `swift-qa-gate`.

## Fixes del review fresco de 1.7.0 (rust/dotnet)

- **BLOCKER — clippy contaba los summaries de rustc como HIGH fantasma**:
  `1 warning emitted` / `aborting due to N previous errors` son diagnósticos
  REALES (level warning/error, `code:null`, `spans:[]`) que el branch code-null
  convertía en `compile-error` HIGH — el gate rust no podía converger nunca con
  un solo warning MEDIUM vivo. Fix: diagnósticos SIN primary span se saltean
  ANTES del check de code (los compile errors reales siempre traen span).
  Además dedupe por finding ID (cargo re-emite por target lib/bin/test).
- **SARIF**: Roslyn `ErrorLog` emite **v1** salvo `,version=2` — se documenta el
  comando correcto Y el parser gana fallback v1 (`resultFile`/`analysisTarget`);
  resultados suprimidos (`suppressions`/`suppressionStates`) se ignoran (un
  `#pragma warning disable` no puede gatear un build limpio); URIs absolutas
  `file:///` se relativizan contra el repo (IDs estables entre máquinas).
- **Paths dotnet**: `LogFilePath`/`CoverletOutput` relativos resuelven contra el
  PROYECTO DE TEST, no la raíz — comando de ejemplo ahora ancla con `$PWD` y el
  README lo advierte (+ `MergeWith` para multi-proyecto).
- **Junit de nextest**: no existe sin `[profile.default.junit]` en
  `.config/nextest.toml` + copy desde `target/nextest/default/junit.xml` —
  documentado y agregado al `test_command_rust`.
- **Regla 5 saldada**: los fixes de 1.6.0 que entraron sin check propio ahora
  tienen smoke — junit root-max (gotestsum errors solo en root), dedupe de
  bloques del cover profile (-coverpkg), y el summary/dup de clippy (T20/T25).

## Fixes del review fresco de 1.8.0 (cpp)

- **`backtest.cpp` ya no cuenta como test LOC**: el sufijo bare `test.cpp`
  (lowercased) tragaba `backtest/protest/contest.cpp`; ahora el patrón CamelCase
  gtest (`FooTest.cpp`) se matchea case-sensitive, como hace dotnet con
  `Test.cs`. Smoke T25 lo pinnea.
- **`cmake-build-<perfil>` de CLion**: el skip ahora es por prefijo
  (`cmake-build-*`), no solo debug/release — el README ya lo prometía y el
  código no lo cumplía.
- **clang-tidy con paths absolutos**: se relativizan contra el repo
  (`_node_rel`), IDs estables entre checkouts; extensiones `.tpp/.ipp/.inl/
  .mm/.cu` entran al regex (un cert-* en un template header ya no desaparece
  en silencio).

## Fixes del review fresco de 1.9.0 (gradle/swift)

- **detekt y SwiftLint imprimen paths ABSOLUTOS por default** — el branch
  isabs de `parse_checkstyle` colapsaba esos IDs a basename (colisiones entre
  módulos Gradle y archivos homónimos Swift, corrompiendo fixed/new/oscillation
  que se computan sobre sets de IDs). Fix: `parse_checkstyle` gana `base` y
  relativiza SIEMPRE para tools no-java (`_node_rel`), igual que
  eslint/tsc/clang-tidy; `golangci` también lo recibe. `_node_rel` dejó de
  depender de `os.path.isabs` (su veredicto para paths `/posix` en Windows
  cambió entre versiones de Python): intenta `relpath` y descarta si escapa
  del repo. Smokes T27/T28 ahora usan paths absolutos (el default real) y
  asserten IDs repo-relativos.
- **Swift Testing era invisible**: `--xunit-output` escribe XCTest en
  `junit.xml` y Swift Testing en un SEGUNDO `junit-swift-testing.xml` que el
  counter no leía — un paquete Swift 6 (donde Swift Testing es el default)
  medía `tests=0` con `report_found=True` y un failure real no disparaba el
  veto "measured beats narrated": fail-open en la garantía central. Fix:
  `junit_test_count` gana `extra_files` (reportes full-run de sets DISJUNTOS
  que SÍ se suman) y el dispatch swift pasa ambos archivos. Smoke con failure
  real en el archivo swift-testing.
- **detekt fuera del test command**: su default `maxIssues: 0` corta el build
  con UN finding — la corrida de tests leería roja aunque los tests pasen,
  mezclando el gate de lint (que tiene su canal propio) con el de tests.
  `test_command_gradle` queda `./gradlew test jacocoTestReport`.
- **Source sets custom de Gradle**: `src/integrationTest/`, `src/functionalTest/`
  (cualquier `src/*Test`) ahora cuentan como test LOC, no prod.
- README swift: variante Linux de `llvm-cov` (sin `xcrun`) + path del binario
  de tests documentados.

## Contrato de siempre

Reporte ausente = el gate no corrió (jamás acredita fixes). Guard UNMEASURED:
los 9 types linteables. Criterio pendiente por adapter: dry-run de solo lectura
contra un repo real de cada lenguaje.

## Diferido consciente

- rebuild: densidad de asserts. Perfiles A-E mecanizados. Android (Gradle +
  variantes) queda explícitamente FUERA de `type: gradle` hasta un repo real.
