# dev-loop-kit 1.2.4

## Nuevo: gate-check (integridad del gate — "no gamear al que mide")
- Comando `qa_ledger.py gate-check`: detecta si un diff DEBILITA el aparato de medición.
  - **BLOCKER (exit 1):** tests borrados o deshabilitados, thresholds de coverage/mutation bajados.
  - **Revisar (soft):** supresiones de lint agregadas, asserts removidos en tests. `--strict` los gatea.
  - Lee diffs formato git (`--from-git` / `--diff` / stdin). stdlib pura.
- Implementa en CÓDIGO la invariante "Integridad del gate" de la CONSTITUTION (antes solo texto).
- (Osmani, "Agentic Code Review": los red-flags para revisores humanos; el detector automático
  y el principio "el aparato no lo modifica el cambio que mide" son síntesis del kit.)
