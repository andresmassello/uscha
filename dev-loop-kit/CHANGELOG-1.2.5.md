# dev-loop-kit 1.2.5 — destilación ("gates de hechos bloquean, adivinadores de prosa avisan")

## Nuevo: golden-diff + INV-GOLDEN-01 (golden/approval testing)
- `qa_ledger.py golden-diff`: byte-compara `*.received.*` vs `*.approved.*`. Cualquier no-match
  o `.received` sin `.approved` = DIVERGE (exit 1). Es un HECHO, no un juicio. Nunca toca `.approved`.
- Invariante `INV-GOLDEN-01` (CWE-440) en CONSTITUTION: en migraciones, golden capturado ANTES de
  tocar el módulo; el golden lo captura un script sobre el código ORIGINAL, el agente no lo authorea.
- (Del HANDOFF de golden testing — pendiente a mano: skill `characterize`, hook PreToolUse que bloquee
  escrituras a `.approved`, `.gitattributes *.approved.* binary`, y decisión de stack del harness.)

## Destilación (distinción hechos vs adivinanza)
- `spec-check` → **ADVISORY** por defecto (heurística sobre prosa): reporta, NO bloquea. `--strict` gatea.
- `simplicity-check` → el regex de "abstracciones" (falsos positivos con records/DTOs) sale del score y
  del hard-cap; queda como métrica/flag informativa. Los caps numéricos (líneas/archivos/anidación) siguen gateando.

## Fixes de spec-check (judgment-day Ronda 1, 2 jueces, 2 critical + 4 warnings, todos resueltos)
- Code-fence tracking (un `# Exclusions` dentro de ```` ``` ```` ya no cuenta), setext headings,
  checkbox vacío no cuenta como criterio, `_SC_ACCEPT` anclado (no "Success/Exit criteria"),
  `\d` suelto ya no exime vago, stack ambiguo podado + scopeado a criterios, vagos en español sumados.

## Gates: hechos (bloquean) vs prosa (avisan)
- BLOQUEAN (leen hechos): golden-diff, pit-check, gate-check, readiness/rebuild, caps de simplicity.
- AVISAN (heurística): spec-check, abstracciones de simplicity.
