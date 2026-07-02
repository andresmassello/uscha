# HANDOFF: Adapter `type: python` para el engine de spec-loop (qa_ledger.py)

> Diseño generado en la sesión PILOT-PROJECT (2026-07-02), persistido acá por la sesión SpecLoop
> que lo ejecuta. **Leer junto con `HANDOFF_python-adapter_ADDENDUM.md`** (revisión
> verificada contra el engine: 2 bugs A1/A2 + ya-cubierto A3 + CLI A4 + SKIP_DIRS A5).

## Contexto

PILOT-PROJECT va a ser el caso de dogfooding real de spec-loop (el pendiente declarado del README
de SpecLoop). Bloqueante: `qa_ledger.py` v1.3.0 solo soporta `type: maven|flutter` —
PILOT-PROJECT es Python (pytest + ruff + mypy + coverage.py). Sin adapter, `snapshot`/
`check-coverage`/`ingest-gate` no pueden medir PILOT-PROJECT y el loop no tiene evidencia.

## Diseño del adapter

Target: `dev-loop-kit/.claude/skills/dev-loop/qa_ledger.py` (stdlib-only, Python 3.8+).

### 1. Registro de tipo
- `SOURCE_EXT`: agregar `"python": {".py"}`.

### 2. Coverage — `python_coverage(repo_path)`
- Parser de `coverage.xml` (formato Cobertura, lo emite `pytest --cov --cov-report=xml`).
  Atributos del root: `lines-covered` / `lines-valid` / `line-rate`.
- Paths de búsqueda: `coverage.xml`, `reports/coverage.xml`.
- Mismo shape de retorno que `maven_coverage()`: `{covered, missed, pct, report_found}`.
  Reporte ausente ⇒ `report_found: False` (UNMEASURED — nunca inventar ceros).
- Dispatch en `coverage()`: `elif repo_type == "python"`.

### 3. Test count — `python_test_count(repo_path)`
- Parser de JUnit XML de `pytest --junitxml=reports/junit.xml`; paths de búsqueda
  `reports/junit.xml`, `junit.xml`, `reports/TEST-*.xml`.
- ⚠ Ver ADDENDUM A2: el root de pytest es `<testsuites>` envuelto — manejar ambas formas.
- Shape: `{total, executed, failures, errors, skipped, passed, report_found}` (exacto).
- Dispatch en `test_count()`.

### 4. LOC y clasificación de paths
- Test: `"tests" in parts` o filename `test_*.py` / `*_test.py`.
- Prod: `.py` bajo `src/` (layout src) o paquete raíz, que no sea test.
- Excluir del walk (ver ADDENDUM A5): `.venv`, `venv`, `.tox`, `__pycache__`,
  `.mypy_cache`, `.ruff_cache`, `.pytest_cache` — sumar a `SKIP_DIRS` global.

### 5. Static gate — familia de parsers Python (diferido de 1.3.0)
- `parse_ruff(path)`: `ruff check --output-format=json > reports/ruff.json`.
  Mapping a `SEVERITY_ORDER`: reglas `S*` (bandit/security) y `E9*`/`F82*` → HIGH;
  `B*` (bugbear) → MEDIUM; resto → LOW.
  Finding id: `ruff:{code}:{file}[:{line}]` respetando `id_granularity`.
- `parse_mypy(path)`: `mypy src --no-error-summary > reports/mypy.txt` (formato
  `file:line: error: msg [code]`): `error` → HIGH, `note` → INFO.
  Finding id: `mypy:{code}:{file}[:{line}]`.
- Integrar a `ingest_gate()` con el branch python (ver ADDENDUM A4: flags `--ruff`/
  `--mypy` + búsqueda default por type del repo). Mismo contrato: reporte ausente =
  gate no corrió (no acredita fixes).

### 6. Config — `dev-loop.config.json`
- `defaults.test_command_python`:
  `pytest --cov --cov-report=xml:reports/coverage.xml --junitxml=reports/junit.xml`
- Ejemplo en `repos[]`: `{"name":"data-lib","path":"../data-lib","type":"python"}`.

### 7. Smoke tests — `tests/smoke-engine.sh`
- Agregar `repo-c` (`type: python`) al config sintético.
- Fixtures: `coverage.xml` Cobertura mínimo, `junit.xml` mínimo (formato ENVUELTO),
  `ruff.json` con 1 finding HIGH + 1 LOW, `mypy.txt` con 1 error; árbol
  `repo-c/src/pkg/mod.py` + `repo-c/tests/test_mod.py`.
- Checks nuevos: snapshot python (coverage % y test count correctos), ingest-gate
  (severidades mapeadas, gated count correcto), UNMEASURED cuando falta el reporte
  (ver ADDENDUM A1: guard de readiness debe incluir python), LOC prod/test bien
  clasificado.
- Regla 5 del repo: smoke en verde ANTES del commit; checks nuevos en el MISMO commit.

### 8. Versionado y docs (reglas 2, 3 y 6 del CLAUDE.md)
- `VERSION` 1.3.0 → **1.4.0** + `CHANGELOG-1.4.0.md` + `dev-loop.config.json`
  coherentes, mismo commit.
- Truth-pass: tabla de reportes del `dev-loop-kit/README.md` — fila Python
  (coverage.xml / junit.xml / ruff.json / mypy.txt). Docs que mencionen los stacks
  soportados (`maven|flutter`): actualizar ES y EN juntos.

## Criterios de éxito (definidos ANTES de correr — pueden dar que NO)

1. `bash dev-loop-kit/tests/smoke-engine.sh` exit 0, incluyendo los checks python nuevos.
2. Dry-run contra PILOT-PROJECT real (solo lectura, desde la sesión PILOT-PROJECT): `init` + `snapshot
   --repo faro` + `check-coverage` + `ingest-gate` + `summary` producen datos correctos
   — coverage % coincide con el reporte de pytest-cov (±0.1), test count = el real
   (hoy 177), findings de ruff/mypy = 0 (repo limpio) sin marcar UNMEASURED.
3. Reporte ausente ⇒ UNMEASURED, jamás 0 inventado (verificado por check de smoke).
4. Ningún cambio rompe maven/flutter: los checks existentes del smoke siguen verdes.

## Después de esto (fases separadas, sesión PILOT-PROJECT)

Consumir el kit 1.4.0 — copiar skills + config con `type: python`, generar los reportes
y correr el dry-run del criterio 2. Recién entonces: on-ramp (CONSTITUTION desde los
principios del proyecto) y, más adelante, el Rebuild Test en worktree limpio.
