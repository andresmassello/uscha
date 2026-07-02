# dev-loop kit

Orquestador spec-driven + QA multi-repo para Claude Code, con ledger determinístico.
**Seis skills** (`discovery`, `adr-refine`, `dev-loop`, `sys-doc`, `reverse-discovery`,
`characterize`) y un motor de medición (`qa_ledger.py`).

**Para quién:** un operador solo llevando UN cambio no-trivial o con riesgo, mantenido
honesto por un ledger determinístico y un human gate en el merge. NO es para cambios
triviales (un one-liner corre build+test y listo).

## Qué hay adentro

```
dev-loop-kit/
├─ dev-loop.config.json            # config: repos, umbrales, comandos
├─ hooks/
│  └─ block-approved-writes.ps1    # PreToolUse: el agente NO puede escribir .approved (INV-GOLDEN-01)
├─ templates/
│  ├─ CLAUDE.md                    # protocolo permanente del repo
│  ├─ CONSTITUTION.md              # invariantes inviolables (completar dominio)
│  ├─ .gitattributes               # *.approved.* binary — que los fin-de-línea no mientan
│  └─ docs/adr/                    # scaffold ADR
└─ .claude/skills/
   ├─ discovery/                   # idea vaga → grilla 1x1 → CONSTITUTION/SPEC/ADR/ACCEPTANCE…
   ├─ adr-refine/                  # feature conocido: entrevista de precisión → ADR + ACCEPTANCE
   ├─ reverse-discovery/           # brownfield: mapa de HECHOS del sistema existente (no propone forma)
   ├─ characterize/                # captura el golden ejecutando el código ORIGINAL (para en la aprobación humana)
   ├─ dev-loop/
   │  ├─ SKILL.md                  # orquestador: plan → build → QA loop → PR
   │  └─ qa_ledger.py              # medición + ledger + gates (ingest/log-gate/golden-diff/gate-check/pit/simplicity/rebuild)
   └─ sys-doc/                     # (opcional) deck HTML de dos vistas desde el ledger
```

## Flujo punta a punta

`discovery` es el frente para algo nuevo (solo tenés la idea); `adr-refine` es el frente
para un feature conocido; `dev-loop` construye y verifica. Se tocan en el `ACCEPTANCE.md`.

```
/discovery     # solo idea + material de referencia → grilla 1x1 (propone, vos decidís)
   ↓           #   escribe CONTEXT.md, CONSTITUTION.md, SPEC.md, docs/adr/*.md, ACCEPTANCE.md, RISKS.md, HANDOFF.md
/dev-loop      # plan → build → QA loop (fact gates al ledger) → PR (para en el merge)
   ↓
/sys-doc       # (opcional, a pedido) documenta el sistema desde el ledger
```

(Para un feature ya conocido, en vez de `/discovery` usás `/adr-refine`.)

**On-ramp de migración/legacy (perfil E):** el golden es la verdad de campo y se captura
ANTES de tocar nada.

```
/reverse-discovery   # mapa de HECHOS del sistema viejo (endpoints, contratos, dependencias)
   ↓
/characterize        # ejecuta el código ORIGINAL con corpus real → .received → PARA:
   ↓                 #   un HUMANO aprueba los .approved (el agente jamás los escribe — hook)
/dev-loop            # migra; golden-diff byte-compara contra el .approved en cada pass
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

## Instalación

**Opción A — por proyecto** (recomendado para suites multi-repo): copiá `.claude/` al
repo primario y `dev-loop.config.json` a la raíz de ese repo.

```bash
cp -r dev-loop-kit/.claude  <repo-primario>/
cp dev-loop-kit/dev-loop.config.json  <repo-primario>/
chmod +x <repo-primario>/.claude/skills/dev-loop/qa_ledger.py
```

**Opción B — global** (para todos tus repos): copiá los skills a `~/.claude/skills/`.
El `dev-loop.config.json` igual va en la raíz del repo donde corras la run (los `path`
del config son relativos a ahí).

```bash
cp -r dev-loop-kit/.claude/skills/dev-loop  ~/.claude/skills/
cp -r dev-loop-kit/.claude/skills/sys-doc   ~/.claude/skills/
```

## Configurar

Editá `dev-loop.config.json`:

- `repos[]`: nombre, `path` (relativo al repo primario), `type` (`maven`|`flutter`|`python`|`node`).
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
/sys-doc        # genera docs/system-deck.html (CEO + técnico, navegable)
```

## Verificación rápida (dry run del motor, sin el skill)

Para confirmar que el engine parsea bien tus reportes ANTES de confiarle el loop:

```bash
cd <repo-primario>
QL=".claude/skills/dev-loop/qa_ledger.py"

python3 $QL --help                                  # ver subcomandos
python3 $QL init --config dev-loop.config.json      # crea QA-LEDGER.json

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

- Dimensiones/pesos: ADR/acceptance 30, coverage 25, static gate 20, convergencia 15,
  integración 10. El **ADR completion** sale de tu acceptance task list (checkboxes
  `- [x]`/`- [ ]`, solo lectura) — contá el archivo entero (default del CLI); `--section`
  solo si verificaste que el heading matchea exacto (un mismatch cerea la dimensión en silencio).
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
python3 $QL rebuild --mode baseline --config dev-loop.config.json   # → REBUILD-BASELINE.json
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
git diff --unified=0 <base> | python3 $QL simplicity-check --config dev-loop.config.json
python3 $QL simplicity-check --from-git --base main            # usa git por vos
python3 $QL simplicity-check --diff cambios.diff --json        # lo consume sys-doc / CI
```

- Dimensiones/pesos: diff_size 30, nesting 25, abstraction 20, net_growth 15, fan_out 5, blob 5.
- Veredictos: `SIMPLE ≥85` · `ACCEPTABLE ≥65` · `OVERBUILT <65` (exit 1 = BLOCKER: recortá y re-corré).
  Un exceso grosero (2× presupuesto, o anidación muy profunda) capea el score a 60 sí o sí.
- Los flags te dicen qué recortar (guard clauses, tipos/capas especulativos, hunks gigantes).
- Presupuestos en `defaults.simplicity`; ajustables por perfil de riesgo. 2-espacios → `--indent-width 2`.

## Subcomandos del ledger

`init · snapshot · check-coverage · log-step · ingest-gate · log-gate · flag-blocker ·
converged · oscillation · escalate · resolve-escalation · summary · readiness · rebuild ·
simplicity-check · pit-check · gate-check · spec-check · golden-diff` — cada uno con `--help`.

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
cp dev-loop-kit/templates/CLAUDE.md        <repo>/CLAUDE.md        # protocolo permanente del repo
cp dev-loop-kit/templates/CONSTITUTION.md  <repo>/CONSTITUTION.md  # invariantes inviolables (completá dominio)
cp -r dev-loop-kit/templates/docs    <repo>/docs           # scaffold docs/adr
# si usás otros agentes además de Claude Code:  cp <repo>/CLAUDE.md <repo>/AGENTS.md
```

Después, completá el bloque "Adapter del proyecto" del `CLAUDE.md` con los comandos de
build/test/gate de ese stack (es lo único específico del proyecto).

## Verificar que el agente lee el kit

Dentro de Claude Code, pedile:

```
Listá las reglas activas del CLAUDE.md y los skills disponibles.
```

Deberían aparecer las reglas del protocolo y los comandos /discovery /adr-refine
/dev-loop /sys-doc. (Para el toolchain de la máquina: `bash dev-loop-kit/workbench-doctor.sh`.)
