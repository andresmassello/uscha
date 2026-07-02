# ADDENDUM al HANDOFF del adapter Python (revisión verificada contra el engine real)

**Contexto:** la sesión del proyecto piloto escribe (o escribió) el diseño del adapter `type: python`
en `docs/HANDOFF_python-adapter_dev-loop-kit.md`. Esta revisión se hizo desde una sesión
con contexto profundo del engine (la que cableó v1.3.0) verificando cada claim contra
`dev-loop-kit/.claude/skills/dev-loop/qa_ledger.py` en HEAD. **La sesión ejecutora debe
leer AMBOS documentos** — el handoff (diseño) y este addendum (correcciones + ya-cubierto).

Veredicto general del diseño: **sólido y aprobado** — shapes de retorno correctos,
atributos Cobertura correctos, split de sesiones correcto, versionado 1.4.0 correcto.
Los puntos de abajo lo completan.

---

## A1. (ALTA — bug si se omite) El guard UNMEASURED hardcodea maven

`qa_ledger.py` línea 1028, en `_repo_readiness()`:

```python
static_unmeasured = rtype == "maven" and not _latest_static_by_tool(node)
```

Al volver python ingest-capable (parsers ruff/mypy), esta condición DEBE pasar a:

```python
static_unmeasured = rtype in ("maven", "python") and not _latest_static_by_tool(node)
```

Si no se toca: un repo `type: python` cuyos linters nunca corrieron puntúa
`static_dim = 1.0` — se reintroduce el bug "el silencio es éxito" (corregido en 1.3.0)
exactamente en el repo del dogfooding. Actualizar también el comentario de las líneas
1025-1027 ("maven — the type the ingest parsers support"). Agregar check de smoke:
repo python SIN reportes de linter ⇒ readiness muestra UNMEASURED (no 1.0).

## A2. (ALTA — count silencioso en 0 si se omite) El root del JUnit de pytest

`maven_test_count()` lee los atributos directo del root del XML (`root.get("tests")`)
— funciona con Surefire porque su root ES `<testsuite>`. El `--junitxml` de pytest
(familia xunit2, default moderno) envuelve: `<testsuites><testsuite tests="...">`.
Reusar la lógica a ciegas ⇒ test count = 0 en silencio. `python_test_count()` debe
manejar ambas formas:

```python
root = ET.parse(f).getroot()
suites = [root] if root.tag == "testsuite" else root.findall("testsuite")
# sumar tests/failures/errors/skipped sobre suites
```

El fixture sintético del smoke debe usar el formato ENVUELTO
(`<testsuites><testsuite .../></testsuites>`) para pinnear este caso.

## A3. (confirmado — NO duplicar trabajo) Ya cubierto por el engine

- `.py` YA está en `_SIMPLICITY_CODE_EXT` (línea 1251) → simplicity-check funciona
  para diffs Python sin cambios.
- `gate-check` YA es python-aware: `test_*.py`/`_test.py` en `_gc_is_test_file`,
  `def test_\w+` en `_GC_TESTDEF`, `# noqa` / `# type: ignore` / `# pylint: disable`
  en `_GC_SUPPRESS` → sin cambios.

## A4. (deletrear la superficie CLI) ingest-gate es Java-específico hoy

Los flags actuales son `--checkstyle/--pmd/--spotbugs` y los paths de búsqueda default
son de Maven. El branch python necesita explícitamente:

- flags nuevos: `--ruff <path>` y `--mypy <path>` (mismo patrón que los Java);
- búsqueda default consciente del type del repo (`cfg["type"] == "python"` ⇒ buscar
  `reports/ruff.json`, `ruff.json`, `reports/mypy.txt`, `mypy.txt`; NO los paths Java);
- mismo contrato de ausencia: reporte ausente = el gate no corrió (el último estado
  queda en pie; jamás acredita fixes).

## A5. (fijar la lista de SKIP_DIRS — el diseño ya lo detecta)

Confirmado: SKIP_DIRS (líneas 61-64) hoy NO excluye nada de Python. Lista a sumar:
`.venv`, `venv`, `.tox`, `__pycache__`, `.mypy_cache`, `.ruff_cache`, `.pytest_cache`.
Es el set global (compartido con maven/flutter) — agregar ahí es seguro y correcto.

---

*Regla de la casa aplicada: esta revisión vive en un archivo versionado, no en el
chat de una sesión. La sesión ejecutora la cruza con `git log` y greps — no con memoria.*
