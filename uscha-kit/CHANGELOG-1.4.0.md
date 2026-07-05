# dev-loop-kit 1.4.0 — adapter `type: python` (2026-07-02)

El desbloqueante del dogfooding: el engine ahora mide repos Python (pytest + ruff +
mypy + coverage.py). Diseño: `docs/HANDOFF_python-adapter_dev-loop-kit.md` +
`docs/HANDOFF_python-adapter_ADDENDUM.md` (los 2 bugs A1/A2 de la revisión están
incorporados). Smoke suite: 24/24 (17 existentes maven/flutter intactos + 7 python).

## Engine (qa_ledger.py)

- **`python_coverage()`** — Cobertura `coverage.xml` (`pytest --cov --cov-report=xml`),
  atributos `lines-covered`/`lines-valid`; primer match gana (`coverage.xml`,
  `reports/coverage.xml`). Reporte ausente o ilegible ⇒ `report_found: False`
  (UNMEASURED — jamás un número inventado).
- **`python_test_count()`** — JUnit XML de `pytest --junitxml`. **Maneja el root
  ENVUELTO** (`<testsuites><testsuite …>`, familia xunit2 del pytest moderno) además
  del root plano — leer atributos del wrapper contaría 0 en silencio (ADDENDUM A2).
- **`parse_ruff()`** — `ruff check --output-format=json`; severidades: `S<dígito>`
  (bandit/security, anclado para no pisar SIM/SLF/SLOT) y `E9*`/`F82*` (errores
  reales) → HIGH, `B<dígito>` (bugbear) → MEDIUM, resto → LOW. **`code: null`**
  (syntax error del ruff moderno ≥0.5) → HIGH siempre — sin esto, la rotura real
  pasaba el gate como LOW en silencio (hallazgo del review de contexto fresco).
- **`parse_mypy()`** — salida de texto (`file:line: error: msg [code]`);
  error → HIGH, warning → MEDIUM, note → INFO.
- **`ingest-gate`** — branch por `type` del repo: python busca `reports/ruff.json` /
  `reports/mypy.txt` (o `--ruff`/`--mypy` explícitos); combinado se loguea como
  `python-qa-gate`. Mismo contrato de ausencia que Java.
- **Guard UNMEASURED ampliado** (ADDENDUM A1): `static_unmeasured` ahora aplica a
  `maven` Y `python` — un repo python cuyos linters nunca corrieron puntúa 0.0 en la
  dimensión static, no 1.0 (habría reintroducido "el silencio es éxito" justo en el
  repo del dogfooding).
- **LOC python**: test = `tests/`/`test/` en el path o `test_*.py`/`*_test.py`;
  prod = el resto de los `.py` (src layout o paquete raíz). `SKIP_DIRS` suma
  `.venv`, `venv`, `.tox`, `__pycache__`, `.mypy_cache`, `.ruff_cache`,
  `.pytest_cache` (sin esto, el LOC contaría el virtualenv entero).
- `_rel_src()` reconoce paths repo-relativos `src/...` (como los emiten ruff/mypy)
  para IDs de finding estables. **Nota de migración**: si un linter Java emitía paths
  relativos `src/...` (poco común — checkstyle/PMD suelen emitir absolutos), sus
  finding-IDs cambian en 1.4.0; un ledger no debería cruzar el upgrade — re-baselinear
  con un ingest fresco después de actualizar.
- `SOURCE_EXT`: `"python": {".py"}`; `.py` también en `generic`.

## Ya cubierto sin cambios (ADDENDUM A3)

- simplicity-check: `.py` ya estaba en `_SIMPLICITY_CODE_EXT`.
- gate-check: ya reconocía `test_*.py`, `def test_`, `# noqa`, `# type: ignore`.

## Config / docs

- `dev-loop.config.json`: `test_command_python` + repo de ejemplo `data-lib`; version 1.4.0.
- Kit README: tabla de reportes Python; SKILL.md y docs actualizan
  `maven|flutter` → `maven|flutter|python`; refs de versión vigente → 1.4.0 (ES+EN).

## Smoke (tests/smoke-engine.sh)

- `repo-c` (`type: python`) con fixtures sintéticos: Cobertura 8/10 → 80.0%,
  junit ENVUELTO → 5 tests, LOC prod=3/test=2, ruff 2 findings (1 gateado),
  mypy 1 error (gateado), UNMEASURED pre-ingest → medido post-ingest.

## Criterio pendiente (fase piloto)

Criterio 2 del HANDOFF — dry-run de solo lectura contra el repo piloto real
(coverage ±0.1 vs pytest-cov, test count exacto, ruff/mypy en 0 sin UNMEASURED).
Se corre desde la sesión del proyecto piloto consumiendo este kit.

## Diferido consciente (sin cambios desde 1.3.0)

- rebuild: densidad de asserts por test-file en la firma.
- Perfiles A-E mecanizados (`--profile`).
