# uscha-kit 1.31.0 — freshness de evidencia + gate de doc-version (2026-07-05)

Origen: review externo (Codex) que encontró al kit fallando su **propia** regla de
truth-pass. Dos findings reales, un aprendizaje meta: *lo que no mecanizás, deriva*.
Smoke suite: 185/185.

## #3 — Freshness de evidencia (el que ataca el core)

`gate-check`/`readiness` cerraban o vetaban un AC por el testcase JUnit sin chequear si
el reporte estaba **vigente**. Un `TEST-*.xml` viejo (surefire/gradle no lo limpian sin
`clean`) podía mantener un AC en falso-verde o vetarlo en falso-rojo. Evidencia stale
no es evidencia — atacaba directo "la evidencia decide".

- **`_ac_tags` descarta reportes STALE**: un reporte más viejo que el código fuente del
  repo (correlación `mtime(fuente) > mtime(reporte)`) se DESCARTA. Un AC respaldado solo
  por reportes stale queda **UNMEASURED** — el mismo patrón honesto que el engine ya usa
  para coverage/static que no corrió, nunca falso-verde ni falso-rojo.
- **Por qué correlación con la fuente y no advisory** (a diferencia de waste/deps): acá
  honrar evidencia stale rompería el núcleo del método. La correlación no tiene falso
  positivo en el flujo real (editar → testear deja el reporte como lo más nuevo) y sí
  detecta el caso peligroso (tests no re-corridos). Sin fuente que correlacionar (repo
  sin código) → nunca marca stale (evita falso positivo).
- Campo `stale_reports` en `readiness --json` + advisory en la vista default.
- **Scope honesto**: `junit_test_count` (el conteo *aproximado*) mantiene el límite —
  su blast radius es menor (no cierra ACs). Diferido, documentado en el código.

## #1/#2 — Doc drift + gate de doc-version (el meta-fix)

El README raíz declaraba v1.24.0 / 23 subcomandos / 139 smoke mientras el engine estaba
en 1.30.0 / 24 / 181; el README del kit copiaba un `uscha-devloop.config.json` inexistente
y decía "6 skills" (son 7). El sync era QUÍNTUPLE pero solo cubría 5 archivos-máquina;
los README se truth-passeaban por **disciplina, no por máquina** — y la disciplina derivó.

- **READMEs corregidos** (raíz + kit): versión, conteo de subcomandos, cadena de
  changelog, filename del config, conteo de skills, y el título `# dev-loop kit` →
  `# uscha-kit` (miss del rebrand).
- **`gate de doc-version` mecanizado** (smoke T52): un marcador invisible
  `<!-- uscha:version -->` en la línea canónica de versión de cada README; el smoke
  verifica que coincida con `VERSION`. Robusto sin falso positivo: la cadena de changelog
  lista todas las versiones históricas legítimamente, así que solo se gatea la línea
  marcada. Esto extiende el T44 (sync quíntuple) a los docs.

## Lo que NO entró del review (con criterio)

- **#4 CONSTITUTION detección-por-agente**: by-design y documentado; muchos invariantes ya
  se mecanizan (simplicity/waste/gate/golden/pit). Un evento "constitution reviewed" es
  candidato futuro, no urgente.
- **#5 contrato de QA vendor-neutral** + **#8 acoplar cierre de AC ↔ pit-check**: válidos,
  doctrina-consistentes; van al backlog (el mecanismo #8 ya existe — falta el acople).
- **#6 separar spec canónica del adapter Claude**: higiene de docs, no defecto.
- **#7 partir `qa_ledger.py`**: NO. Partir un archivo estable con 185 smoke checks es el
  "refactor de lo que no está roto" que el propio CLAUDE.md prohíbe; YAGNI hasta que la
  concentración cause un bug real.

## Smoke (T51 + T52, 4 checks)

T51: reporte fresco → AC-1 cierra medido, `stale_reports` vacío (sin falso positivo);
código más nuevo → reporte STALE descartado, AC-1 UNMEASURED; advisory visible.
T52: los dos READMEs declaran la versión actual (drift de docs = exit 1).
