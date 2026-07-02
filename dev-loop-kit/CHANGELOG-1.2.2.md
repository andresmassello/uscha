# dev-loop-kit 1.2.2

## Fixes (simplicity-check)
- **[BLOCKER] `--from-git` crasheaba en Windows** — `subprocess.run` sin `encoding`
  decodificaba el diff con cp1252 y reventaba (UnicodeDecodeError → None.splitlines).
  Fix: `encoding="utf-8", errors="replace"`.
- **Salida en mojibake en consola Windows** — `main()` fuerza `stdout/stderr` a UTF-8.
- **No filtraba por tipo de archivo** — medía docs/config/resources como código
  (inflaba lines/nesting; falsos OVERBUILT). Ahora solo cuenta código
  (`_SIMPLICITY_CODE_EXT` + `SKIP_DIRS`), y reporta cuántos archivos salteó.

## Nuevo: `pit-check` (mutation testing)
- Gate de EFECTIVIDAD de tests (coverage miente): ingesta el `mutations.xml` de PIT,
  reporta mutation score + **test-strength** (matados/cubiertos) + hotspots.
- Invariante **Tests efectivos** agregada a `templates/CONSTITUTION.md`.
- Tier scheduled/incremental (PIT es caro), no inner loop.
