# dev-loop kit

Orquestador spec-driven + QA multi-repo para Claude Code, con ledger determinístico.
**Siete skills** (`uscha-discovery`, `uscha-adr-refine`, `uscha-devloop`, `uscha-sysdoc`, `uscha-reverse-discovery`,
`uscha-characterize`, `uscha-rubric`) y un motor de medición (`qa_ledger.py`).

**Para quién:** un operador solo llevando UN cambio no-trivial o con riesgo, mantenido
honesto por un ledger determinístico y un human gate en el merge. NO es para cambios
triviales (un one-liner corre build+test y listo).

## Qué hay adentro

```
uscha-kit/
├─ uscha.config.json            # config: repos, umbrales, comandos
├─ hooks/
│  └─ block-approved-writes.ps1    # PreToolUse: el agente NO puede escribir .approved (INV-GOLDEN-01)
├─ templates/
│  ├─ CLAUDE.md                    # protocolo permanente del repo
│  ├─ CONSTITUTION.md              # invariantes inviolables (completar dominio)
│  ├─ .gitattributes               # *.approved.* binary — que los fin-de-línea no mientan
│  └─ docs/adr/                    # scaffold ADR
└─ .claude/skills/
   ├─ uscha-discovery/                   # idea vaga → grilla 1x1 → CONSTITUTION/SPEC/ADR/ACCEPTANCE…
   ├─ uscha-adr-refine/                  # feature conocido: entrevista de precisión → ADR + ACCEPTANCE
   ├─ uscha-reverse-discovery/           # brownfield: mapa de HECHOS del sistema existente (no propone forma)
   ├─ uscha-characterize/                # captura el golden ejecutando el código ORIGINAL (para en la aprobación humana)
   ├─ uscha-devloop/
   │  ├─ SKILL.md                  # orquestador: plan → build → QA loop → PR
   │  └─ qa_ledger.py              # medición + ledger + gates (ingest/log-gate/golden-diff/gate-check/pit/simplicity/rebuild)
   ├─ uscha-sysdoc/                     # (opcional) deck HTML de dos vistas desde el ledger
   └─ uscha-rubric/                      # (opcional) grade de la rubrica — adapter fino; el nucleo es agnostico
```

## Flujo punta a punta

`uscha-discovery` es el frente para algo nuevo (solo tenés la idea); `uscha-adr-refine` es el frente
para un feature conocido; `uscha-devloop` construye y verifica. Se tocan en el `ACCEPTANCE.md`.

```
/uscha-discovery     # solo idea + material de referencia → grilla 1x1 (propone, vos decidís)
   ↓           #   escribe CONTEXT.md, CONSTITUTION.md, SPEC.md, docs/adr/*.md, ACCEPTANCE.md, RISKS.md, HANDOFF.md
/uscha-devloop      # plan → build → QA loop (fact gates al ledger) → PR (para en el merge)
   ↓
/uscha-sysdoc       # (opcional, a pedido) documenta el sistema desde el ledger
```

(Para un feature ya conocido, en vez de `/uscha-discovery` usás `/uscha-adr-refine`.)

**On-ramp de migración/legacy (perfil E):** el golden es la verdad de campo y se captura
ANTES de tocar nada.

```
/uscha-reverse-discovery   # mapa de HECHOS del sistema viejo (endpoints, contratos, dependencias)
   ↓
/uscha-characterize        # ejecuta el código ORIGINAL con corpus real → .received → PARA:
   ↓                 #   un HUMANO aprueba los .approved (el agente jamás los escribe — hook)
/uscha-devloop            # migra; golden-diff byte-compara contra el .approved en cada pass
```

## Requisitos

- **Python 3.8+** (solo stdlib — no hay `pip install`). `cloc` NO hace falta; el LOC se
  cuenta en Python.
- Para que `ingest-gate` y el coverage funcionen, tu build Maven tiene que emitir los
  reportes (tu `java-qa-gate` ya tiene los plugins; estos son los paths que el ledger
  espera):

  | dato        | plugin / goal                                   | archivo |
  |-------------|--------------------------------------------------|---------|
  | coverage    | `jacoco-maven-plugin` (`report`)                 | `target/site/jacoco/jacoco.xml` (o `jacoco-aggregate/`) |
  | test count  | `maven-surefire-plugin` / `failsafe`             | `target/surefire-reports/TEST-*.xml` |
  | checkstyle  | `maven-checkstyle-plugin` (`checkstyle`)         | `target/checkstyle-result.xml` |
  | pmd         | `maven-pmd-plugin` (`pmd`)                        | `target/pmd.xml` |
  | spotbugs+fsb| `spotbugs-maven-plugin` (+ findsecbugs)          | `target/spotbugsXml.xml` |

  Flutter: coverage de `coverage/lcov.info` (`flutter test --coverage`);
  el test count es aproximado (cuenta `test(`/`testWidgets(`).

  Python (`type: python`, kit 1.4.0):

  | dato        | comando                                           | archivo |
  |-------------|---------------------------------------------------|---------|
  | coverage    | `pytest --cov --cov-report=xml:reports/coverage.xml` | `coverage.xml` o `reports/coverage.xml` (Cobertura) |
  | test count  | `pytest --junitxml=reports/junit.xml`             | `reports/junit.xml` (root envuelto `<testsuites>` soportado) |
  | ruff        | `ruff check --output-format=json > reports/ruff.json` | `reports/ruff.json` (S*/E9*/F82*→HIGH · B*→MEDIUM · resto→LOW) |
  | mypy        | `mypy src > reports/mypy.txt`                     | `reports/mypy.txt` (error→HIGH · warning→MEDIUM · note→INFO) |

  `ingest-gate` los encuentra solo por type del repo, o con `--ruff/--mypy` explícitos.
  Contrato idéntico al Java: reporte ausente = el gate no corrió (jamás acredita fixes).

  TypeScript/JS (`type: node`, kit 1.5.0):

  | dato        | comando                                           | archivo |
  |-------------|---------------------------------------------------|---------|
  | coverage    | `jest --coverage` (o vitest con reporter lcov)    | `coverage/lcov.info` (mismo parser que Flutter) |
  | test count  | `jest-junit` / `vitest --reporter=junit`          | `reports/junit.xml` o `junit.xml` (root envuelto soportado) |
  | eslint      | `eslint . --format json > reports/eslint.json`    | `reports/eslint.json` (error→HIGH · warn→MEDIUM · `security/*` floor HIGH · ruleId null→HIGH) |
  | tsc         | `tsc --noEmit > reports/tsc.txt`                  | `reports/tsc.txt` (error TS → HIGH) |

  `ingest-gate` los encuentra por type del repo, o con `--eslint/--tsc` explícitos.
  Mismo contrato de ausencia.

  Go (`type: go`, kit 1.6.0):

  | dato        | comando                                           | archivo |
  |-------------|---------------------------------------------------|---------|
  | coverage    | `go test -coverprofile=coverage.out ./...`        | `coverage.out` (cover profile nativo — % por SENTENCIAS, la convención Go) |
  | test count  | `gotestsum --junitfile reports/junit.xml -- ./...`| `reports/junit.xml` (JUnit envuelto soportado) |
  | golangci    | `golangci-lint run --output.checkstyle.path=reports/golangci.xml` (v2; en v1: `--out-format checkstyle > ...`) | `reports/golangci.xml` (formato checkstyle: error→HIGH · warning→MEDIUM; incluye gosec si está habilitado) |

  `ingest-gate` lo encuentra por type del repo, o con `--golangci` explícito. Los tests
  `_test.go` viven junto al código (convención Go) — el LOC los clasifica por sufijo.
  `vendor/` y `testdata/` quedan fuera del LOC. Mismo contrato de ausencia.
  **Ojo severidades**: golangci-lint emite `severity=error` para TODO salvo que
  configures reglas `severity:` — sin eso, hasta los nits de estilo gatean como HIGH;
  configurá severidades (o un set de linters magro) para que MEDIUM exista de verdad.

  Rust (`type: rust`, kit 1.7.0):

  | dato        | comando                                           | archivo |
  |-------------|---------------------------------------------------|---------|
  | coverage    | `cargo llvm-cov --cobertura --output-path reports/coverage.xml` | `reports/coverage.xml` (Cobertura — mismo parser que Python) |
  | test count  | `cargo nextest run` + copy (ver nota)             | `reports/junit.xml` (JUnit envuelto soportado) |
  | clippy      | `cargo clippy --message-format=json > reports/clippy.json` | `reports/clippy.json` (JSONL: error→HIGH · warning→MEDIUM · `code:null` compile-error→HIGH; summaries sin span ignorados) |

  `ingest-gate` con `--clippy` explícito o por type. Los tests inline `#[cfg(test)]`
  cuentan como LOC prod (limitación documentada); `tests/` = integración.
  **Ojo junit**: nextest NO emite JUnit por default — hay que habilitarlo en
  `.config/nextest.toml` (`[profile.default.junit] path = "junit.xml"`) y el archivo
  cae en `target/nextest/default/junit.xml`; copialo a `reports/junit.xml`
  (`cp target/nextest/default/junit.xml reports/junit.xml`, ya incluido en el
  `test_command_rust` de ejemplo).

  C#/.NET (`type: dotnet`, kit 1.7.0):

  | dato        | comando                                           | archivo |
  |-------------|---------------------------------------------------|---------|
  | coverage    | coverlet.msbuild: `/p:CollectCoverage=true /p:CoverletOutputFormat=cobertura /p:CoverletOutput=$PWD/reports/coverage.xml` | `reports/coverage.xml` (Cobertura) |
  | test count  | `dotnet test --logger "junit;LogFilePath=$PWD/reports/junit.xml"` (paquete JUnitXml.TestLogger) | `reports/junit.xml` |
  | roslyn      | `dotnet build /p:ErrorLog="reports/analysis.sarif,version=2"` | `reports/analysis.sarif` (SARIF: error→HIGH · warning→MEDIUM · note→INFO; suprimidos ignorados) |

  `ingest-gate` con `--sarif` explícito o por type. SARIF es el formato universal de
  análisis estático — el parser sirve para cualquier tool que lo emita.
  **Ojo paths**: `LogFilePath` y `CoverletOutput` relativos resuelven contra el
  directorio del PROYECTO DE TEST, no la raíz del repo — por eso los `$PWD`
  (anclaje absoluto). Con varios proyectos de test, mergeá (`/p:MergeWith`) o un
  reporte por proyecto. `ErrorLog` sin `,version=2` emite SARIF **v1**; el parser
  tiene fallback v1, pero pedí v2 (la coma requiere las comillas).

  C++ (`type: cpp`, kit 1.8.0):

  | dato        | comando                                           | archivo |
  |-------------|---------------------------------------------------|---------|
  | coverage    | `gcovr --cobertura reports/coverage.xml` (sobre gcov) | `reports/coverage.xml` (Cobertura — mismo parser) |
  | test count  | `ctest --test-dir build --output-junit ../reports/junit.xml` (CMake ≥3.21) o `--gtest_output=xml:...` | `reports/junit.xml` (root plano Y envuelto soportados) |
  | clang-tidy  | `clang-tidy <files> > reports/clang-tidy.txt`     | `reports/clang-tidy.txt` (error→HIGH · warning→MEDIUM · `cert-*`/security floor HIGH) |

  `ingest-gate` con `--clang-tidy` explícito o por type. El build system (CMake/
  Bazel/make) es del adapter por-repo — el kit solo pide que los reportes existan.
  `cmake-build-*` (cualquier perfil de CLion) y `_deps` quedan fuera del LOC.

  Kotlin/JVM con Gradle (`type: gradle`, kit 1.9.0) — **Kotlin sobre Maven ya
  funciona con `type: maven`** (`.kt` cuenta desde siempre; JaCoCo/Surefire no
  distinguen lenguaje JVM). Este type es para el caso común Gradle:

  | dato        | comando                                           | archivo |
  |-------------|---------------------------------------------------|---------|
  | coverage    | `./gradlew test jacocoTestReport`                 | `build/reports/jacoco/test/jacocoTestReport.xml` (JaCoCo — mismo parser que maven) |
  | test count  | (mismo `./gradlew test`)                          | `build/test-results/**/TEST-*.xml` (per-clase, como surefire) |
  | detekt      | `./gradlew detekt` **por separado** (ver nota)    | `build/reports/detekt/detekt.xml` (formato checkstyle: error→HIGH · warning→MEDIUM; paths absolutos relativizados) |

  `ingest-gate` con `--detekt` explícito o por type. Sirve igual para Java-sobre-
  Gradle. LOC: `src/main` = prod; `src/test` Y source sets custom (`src/
  integrationTest`, `src/functionalTest` — cualquier `src/*Test`) = test
  (`.kt`/`.kts`/`.java`). El requisito JaCoCo: `jacoco` plugin +
  `jacocoTestReport { reports { xml.required = true } }`.
  **Ojo detekt**: NO lo encadenes al test command — su default es `maxIssues: 0`,
  o sea que UN finding corta el build y la corrida de tests leería roja aunque
  los tests pasen. Corré `./gradlew detekt` aparte, antes del `ingest-gate`
  (el gate de lint tiene su propio canal).

  Swift (`type: swift`, kit 1.9.0):

  | dato        | comando                                           | archivo |
  |-------------|---------------------------------------------------|---------|
  | coverage    | `swift test --enable-code-coverage` + `llvm-cov export -format=lcov ... > coverage/lcov.info` | `coverage/lcov.info` (lcov — mismo parser que Flutter/node) |
  | test count  | `swift test --xunit-output reports/junit.xml`     | `reports/junit.xml` **+ `reports/junit-swift-testing.xml`** (se SUMAN — ver nota) |
  | swiftlint   | `swiftlint lint --reporter checkstyle > reports/swiftlint.xml` | `reports/swiftlint.xml` (formato checkstyle: error→HIGH · warning→MEDIUM; paths absolutos relativizados) |

  `ingest-gate` con `--swiftlint` explícito o por type. LOC: convención SwiftPM
  (`Sources/` = prod, `Tests/` + `*Tests.swift` = test). El export lcov necesita
  el paso `llvm-cov export` contra el binario de tests (el `.profdata` solo no
  alcanza) — dejalo en el `test_command_swift` de tu repo; en macOS es
  `xcrun llvm-cov`, en Linux `llvm-cov` pelado (y el binario vive en
  `.build/debug/<Pkg>PackageTests.xctest`).
  **Ojo Swift Testing**: `--xunit-output` escribe los resultados de XCTest en
  `junit.xml` y los de **Swift Testing** (el default de Swift 6) en un SEGUNDO
  archivo `junit-swift-testing.xml` — el engine suma AMBOS; si solo leyera el
  primero, un paquete Swift 6 mediría `tests=0` y un failure real quedaría
  invisible (fail-open).

## Instalación

**Opción A — por proyecto** (recomendado para suites multi-repo): copiá `.claude/` al
repo primario y `uscha.config.json` a la raíz de ese repo.

```bash
cp -r uscha-kit/.claude  <repo-primario>/
cp uscha-kit/uscha-devloop.config.json  <repo-primario>/
chmod +x <repo-primario>/.claude/skills/uscha-devloop/qa_ledger.py
```

**Opción B — global** (kit 1.20.0: para todos tus repos, existentes y nuevos): copiá
las SEIS skills a `~/.claude/skills/` y el hook a `~/.claude/hooks/` + registralo en
`~/.claude/settings.json` (snippet en el header del .ps1) — así INV-GOLDEN-01 rige en
todos los proyectos. Las skills resuelven el engine primero en el proyecto y caen a
`~/.claude/skills/uscha-devloop/qa_ledger.py` si no hay instalación local.

```bash
for s in uscha-discovery uscha-adr-refine uscha-reverse-discovery uscha-characterize uscha-devloop uscha-sysdoc uscha-rubric; do
  cp -r "uscha-kit/.claude/skills/$s" ~/.claude/skills/
done
mkdir -p ~/.claude/hooks && cp uscha-kit/hooks/block-approved-writes.ps1 ~/.claude/hooks/
```

Lo que sigue siendo POR PROYECTO (estado, no instalable): `uscha.config.json` en la
raíz del repo donde corras la run (los `path` son relativos a ahí — y tu quality bar
declarada vive ahí), el `QA-LEDGER.json`, el `ACCEPTANCE.md`, y para trabajo de
migración el `.gitattributes` de `templates/` (`*.approved.* binary`).

> En la máquina donde DESARROLLÁS el kit, en vez de copiar conviene un junction/symlink
> de cada skill al repo canónico — global siempre al día con main, cero re-instalación
> por release: `cmd /c mklink /J "%USERPROFILE%\.claude\skills\uscha-devloop" "<repo>\uscha-kit\.claude\skills\uscha-devloop"` (una por skill).

**Opción C — plugin de Claude Code** (kit 1.24.0, la recomendada si usás Claude Code):
el repo es su propio marketplace y el hook INV-GOLDEN-01 se auto-registra al instalar
(cero edición de settings.json). Las skills quedan como `uscha:uscha-*`.

```
/plugin marketplace add andresmassello/uscha
/plugin install uscha@uscha
```

Updates: `/plugin update uscha@uscha` cuando haya release nuevo (el plugin declara
`version`, así que solo actualiza con bump). Linux: el hook es PowerShell — instalá pwsh
(el doctor te da el link) y ajustá el comando del hook si hace falta. El resto de los
runtimes (Codex, Gemini CLI, Cursor) siguen usando la Opción A/B — el plugin es
empaquetado, no dependencia.

**Verificá la instalación con `doctor`** (kit 1.22.0, espíritu flutter doctor —
Windows y Linux, output ASCII, exit 1 solo con errores):

```bash
python3 ~/.claude/skills/uscha-devloop/qa_ledger.py doctor
# o, por proyecto:  python3 ./.claude/skills/uscha-devloop/qa_ledger.py doctor
```

Chequea: Python >=3.8 · git · las 6 skills junto al engine (frontmatter
verificado) · el hook INV-GOLDEN-01 (presente + registrado en settings.json +
intérprete powershell/pwsh) · y si hay `uscha.config.json` en el cwd:
config parseable, ACCEPTANCE con AC-IDs, integridad del ledger, las skills de
QA de `qa_tools_order` (el loop las orquesta sin traerlas) y el toolchain
primario de cada repo por type (su ausencia es AVISO — puede vivir solo en CI).

## Configurar

Editá `uscha.config.json`:

- `repos[]`: nombre, `path` (relativo al repo primario), `type` (`maven`|`flutter`|`python`|`node`|`go`|`rust`|`dotnet`|`cpp`|`gradle`|`swift`).
- `defaults.coverage_threshold`: dispara la fase de characterization si está por debajo.
- `defaults.severity_gate`: qué severidades bloquean (default BLOCKER/CRITICAL/HIGH).
- `defaults.id_granularity`: `line` o `file` (default `file`: más estable si refactorizás mucho).
- `defaults.acceptance_file`: ruta de la **acceptance task list** (checkboxes markdown) que alimenta el ADR completion del readiness. Default `ACCEPTANCE.md`.
- `defaults.constitution_file`: ruta de la **CONSTITUTION** (invariantes inviolables). Default `CONSTITUTION.md`.
- `defaults.rebuild.coverage_tolerance`: puntos de coverage que el rebuild puede bajar sin penalizar (default 5).
- `defaults.readiness_weights` / `readiness_caps` / `static_gate_zero_at`: pesos y topes del KPI.
- `defaults.max_iterations`, `tools_per_cycle`, comandos de test.

## Multi-repo: montar los otros repos

El skill corre desde el repo primario; los demás se montan en la sesión:

```bash
cd <repo-primario>
claude --add-dir ../backend-api --add-dir ../mobile-app
```

(o `additionalDirectories` en `.claude/settings.json`).

## Usar

Dentro de Claude Code, invocá el orquestador (con el ADR/PLAN ya listo o pedíselo):

```
/dev-loop
```

El skill maneja las fases solo: plan → coverage gate → (characterization si hace falta)
→ build → QA loop per-repo → integración → verify → PR (para en el merge, lo aprobás
vos) → smoke list. Loguea cada paso en `QA-LEDGER.json`. Al final:

```
/uscha-sysdoc        # genera docs/system-deck.html (CEO + técnico, navegable)
```

## Verificación rápida (dry run del motor, sin el skill)

Para confirmar que el engine parsea bien tus reportes ANTES de confiarle el loop:

```bash
cd <repo-primario>
QL=".claude/skills/uscha-devloop/qa_ledger.py"

python3 $QL --help                                  # ver subcomandos
python3 $QL init --config uscha.config.json      # crea QA-LEDGER.json

# corré tu build con los reportes, después:
python3 $QL snapshot      --repo backend-api --phase pre
python3 $QL check-coverage --repo backend-api       # exit 0 = OK, 1 = bajo umbral
python3 $QL ingest-gate   --repo backend-api --iteration 1
python3 $QL summary                                 # resumen humano
python3 $QL summary --json                          # lo consume sys-doc
```

Si `snapshot`/`ingest-gate` dicen "no report found", es que el build todavía no generó
los XML — corré `mvn test` con los plugins activos primero.

## Readiness KPI (al terminar cualquier tarea)

Muestra el estado de "listo para release" como score 0..100, **basado en estado del
resultado, no en esfuerzo gastado**:

```bash
python3 $QL readiness --acceptance ACCEPTANCE.md
python3 $QL readiness --json            # lo consume sys-doc (widget semáforo)
```

- Dimensiones/pesos: **acceptance trazada (MEDIDA) 30**, ADR/checkboxes 15, coverage 15,
  static gate 20, convergencia 10, integración 10. El **ADR completion** sale de tu
  acceptance task list (checkboxes `- [x]`/`- [ ]`, solo lectura) — contá el archivo
  entero (default del CLI); `--section` solo si verificaste que el heading matchea
  exacto (un mismatch cerea la dimensión en silencio).
- **Trazabilidad (kit 1.10.0, la dimensión dominante)**: cada criterio lleva ID estable
  — `- [ ] AC-01 — cuando X entonces Y`. Un criterio cierra MEDIDO solo cuando existe
  ≥1 testcase VERDE con su tag en el nombre (`test_ac1_x` / `testAC01X` / `"AC-01: ..."`
  — se normaliza por número: `AC-01 == AC_1 == ac1`) en los reportes JUnit ya ingeridos,
  y ningún testcase taggeado en rojo. El checkbox es RELATO; el testcase es HECHO: un
  `[x]` sin test verde aparece como `narrated_only` y NO cierra. Anti-Goodhart: el agente
  ya no puede subir el KPI puliendo coverage — solo cerrando criterios con tests con
  nombre. `spec-check --acceptance ACCEPTANCE.md` valida la estructura como FACT (cero
  criterios trazables o IDs duplicados = BLOCKED). Sin IDs: cae al ratio de checkboxes
  con warning (legacy, adopción incremental). Flutter no emite JUnit: sus criterios no
  cierran medido (limitación documentada).
- Un repo linteable cuyo static gate **nunca corrió** puntúa esa dimensión UNMEASURED (0.0)
  — el silencio no es éxito.
- **Hard caps** (pisan el techo): tests en rojo → ≤35, BLOCKER/CRITICAL abierto → ≤65,
  escalación sin resolver → ≤75 (se sostiene hasta `resolve-escalation`, un evento registrado).
- Bandas: `<50 NOT READY` · `50–79 IN PROGRESS` · `80–94 RELEASE CANDIDATE` · `95–100 READY`.
- Multi-repo: per-repo y agregado (min() para blockers, ponderado por LOC para calidad).
- Los ciclos/regresiones son **churn** (salud del proceso), se reportan aparte y nunca
  suben el readiness.

## Rebuild test (completitud de la SPEC)

Pregunta distinta al ledger: no "¿pasó este build?" (corrección) sino "¿la SPEC alcanza
para regenerar el sistema?" (completitud). Para perfiles C+/E o periódico en CI.

```bash
# 1) en el tree ORIGINAL: capturá la firma que el rebuild debe igualar
python3 $QL rebuild --mode baseline --config uscha.config.json   # → REBUILD-BASELINE.json
# 2) en un tree LIMPIO / sesión nueva: regenerá SOLO el código de producción desde
#    SPEC/ADR/ACCEPTANCE, PRESERVANDO los tests, y corré la suite.
# 3) puntuá el tree regenerado contra la baseline
python3 $QL rebuild --mode compare --baseline REBUILD-BASELINE.json   # exit 0 = COVERS
python3 $QL rebuild --mode compare --baseline REBUILD-BASELINE.json --json   # lo consume sys-doc
```

- Dimensiones/pesos: tests 60, acceptance 20, coverage 15, surface 5. La señal dominante
  es la **suite preservada**: un test que pasaba y falla en el código regenerado = comportamiento
  que la SPEC dejó implícito.
- Veredictos: `COVERS ≥90` · `PARTIAL ≥70` · `DIVERGE <70`. El score lista los **gaps**
  concretos — metelos de vuelta en la SPEC y re-corré. La divergencia es hueco de spec, no bug de código.

## Simplicity gate — "Reduce" (minimalidad del cambio)

La invariante **Simplicidad** de la CONSTITUTION hecha gate determinístico: puntúa el *diff*
(no CC por AST — son proxies medibles: minimalidad, anidación, abstracciones nuevas).

```bash
git diff --unified=0 <base> | python3 $QL simplicity-check --config uscha.config.json
python3 $QL simplicity-check --from-git --base main            # usa git por vos
python3 $QL simplicity-check --diff cambios.diff --json        # lo consume sys-doc / CI
```

- Dimensiones/pesos: diff_size 35, nesting 30, net_growth 20, fan_out 8, blob 7
  (abstraction NO pesa en el score — es proxy adivinón, queda como métrica + flag advisory).
- Veredictos: `SIMPLE ≥85` · `ACCEPTABLE ≥65` · `OVERBUILT <65` (exit 1 = BLOCKER: recortá y re-corré).
  Un exceso grosero (2× presupuesto, o anidación muy profunda) capea el score a 60 sí o sí.
- **Tests FUERA del presupuesto** (kit 1.11.0): los archivos de test (convenciones de los
  9 stacks) se cuentan y reportan aparte (`test_lines_added`) pero no gatean — escribir
  tests nunca empuja el diff a OVERBUILT (borrarlos ya lo bloquea gate-check).
- Los flags te dicen qué recortar (guard clauses, tipos/capas especulativos, hunks gigantes).
- Presupuestos en `defaults.simplicity`; ajustables por perfil de riesgo. 2-espacios → `--indent-width 2`.

## Subcomandos del ledger

`doctor · init · snapshot · check-coverage · log-step · ingest-gate · log-gate · flag-blocker ·
converged · oscillation · escalate · resolve-escalation · summary · readiness · rebuild ·
simplicity-check · pit-check · gate-check · spec-check · golden-diff · regression-check ·
phase · rubric-ingest · doctor` — cada uno con `--help`.

Los **fact gates** (golden-diff, gate-check, pit-check, simplicity) se PERSISTEN con
`log-gate`: un fail bloquea convergencia y capea readiness ≤65 vía el ledger. Una violación
de CONSTITUTION se registra con `flag-blocker` (mismo efecto, hasta `--resolve`).

## Notas

- **No mergea solo.** Crea el PR y para; el merge lo hacés vos.
- **Protocolo `.md` trackeado.** Antes de tocar CLAUDE.md / docs de plan/delta / docs/adr,
  el skill pide la versión actual del archivo (no regenera y pisa progreso real).
- `ingest-gate` acredita un fix solo si el reporte EXISTE y vino limpio; un reporte
  ausente = el gate no corrió (no inventa ceros).

## Armado del workbench (setup genérico)

Antes de usar los skills necesitás el toolchain base (Claude Code + Python + git/gh +
los skills instalados). Está todo en **`WORKBENCH.md`**: instalación, verificación y
actualización, sin lo específico de cada stack (Java/MSSQL/linters = adapter por repo).

- Qué tengo instalado:  `bash workbench-doctor.sh`
- Versión del kit:      `cat VERSION`

## Plantillas para el repo (que el repo quede "methodology-ready")

El kit instala los skills; estas plantillas dejan el **repo** listo. Copialas a la raíz
del repo donde vas a trabajar:

```
cp uscha-kit/templates/CLAUDE.md        <repo>/CLAUDE.md        # protocolo permanente del repo
cp uscha-kit/templates/CONSTITUTION.md  <repo>/CONSTITUTION.md  # invariantes inviolables (completá dominio)
cp -r uscha-kit/templates/docs    <repo>/docs           # scaffold docs/adr
# si usás otros agentes además de Claude Code:  cp <repo>/CLAUDE.md <repo>/AGENTS.md
```

Después, completá el bloque "Adapter del proyecto" del `CLAUDE.md` con los comandos de
build/test/gate de ese stack (es lo único específico del proyecto).

## Verificar que el agente lee el kit

Dentro de Claude Code, pedile:

```
Listá las reglas activas del CLAUDE.md y los skills disponibles.
```

Deberían aparecer las reglas del protocolo y los comandos /uscha-discovery /uscha-adr-refine
/uscha-devloop /uscha-sysdoc. (Para el toolchain de la máquina: `bash uscha-kit/workbench-doctor.sh`.)
