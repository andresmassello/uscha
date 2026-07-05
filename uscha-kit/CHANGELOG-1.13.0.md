# dev-loop-kit 1.13.0 — ledger atómico: checksum de integridad (2026-07-03)

Cuarta mejora del backlog PragProg (M3 de `docs/analisis-pragmatic-programmer.md`;
Topic 34 *"los recursos compartidos mutables incluyen ARCHIVOS"*). Todo el
edificio "measured beats narrated" se apoya en `QA-LEDGER.json` — y hasta hoy
ese JSON podía corromperse o mutarse en silencio. Smoke suite: 85/85.

## La idea

- La **escritura ya era atómica** (write-temp + `os.replace`, desde antes) —
  lo que faltaba era el otro lado: detectar al CARGAR que el archivo quedó
  inconsistente.
- `_save` ahora escribe un campo `integrity` con **sha256 canónico** del
  contenido (claves ordenadas — el hash no depende del orden del dict).
- `_load` **verifica** el checksum cuando el campo existe: una mutación externa
  (edición a mano, merge accidental) o una escritura parcial **bloquea** con
  mensaje de recuperación (`git checkout -- QA-LEDGER.json`). Aceptar una
  edición externa deliberada = borrar el campo `integrity` (acto humano
  explícito, mismo espíritu que INV-GOLDEN-01).
- JSON corrupto/truncado = hecho bloqueante con mensaje claro, **no un
  traceback crudo**.
- **Legacy**: ledgers pre-1.13.0 sin `integrity` cargan sin verificar
  (adopción incremental, no rotura retroactiva). `init` re-inicializa sobre
  un ledger corrupto sin leerlo.

## Diferido consciente

- File-lock inter-proceso (la parte "opcional" de M3): omitido — stdlib
  portable Windows/Linux no lo da barato (`fcntl` no existe en Windows) y el
  loop es single-writer por diseño. Si aparece un caso real de escritura
  concurrente, se re-evalúa.
- El baseline de `rebuild` (artefacto aparte) no lleva checksum — mismo
  candidato si el rebuild gana peso.
