# dev-loop-kit 1.2.3

## Fixes (qa_ledger.py) — verificados por doble review adversarial (judgment-day, 2 rondas, 0 critical)
- pit-check: NON_VIABLE + RUN_ERROR excluidos del denominador (antes inflaban el score y
  podían tirar un BELOW-GATE falso). Nuevo campo `excluded`.
- simplicity-check: parser robusto con máquina de estados `in_hunk` — una línea agregada
  `++ x` (que en el diff aparece como `+++ x`) ya no se confunde con un header y deja de
  perder el conteo del resto del hunk.
- simplicity-check: skip-set más angosto (`_SIMPLICITY_SKIP`) — código en paquetes
  `generated`/`out`/`bin`/`dist` ya no se descarta del budget.

## Nuevo (CONSTITUTION.md)
- Invariante "Integridad del gate — no gamear al que mide": un diff que debilita el aparato
  de medición (tests/lint/thresholds) o reescribe una masa de asserts = BLOCKER; checker
  no-correlacionado para alto blast-radius. (Osmani, "Agentic Code Review".)

## Limitación conocida (documentada)
- simplicity-check espera diffs formato git (`diff --git` por archivo, como `git diff` y
  `--from-git`). Un `diff -u` plano de POSIX sin esos headers miscuenta archivos después
  del primero. Usar `--from-git` o `git diff > file`.
