# dev-loop-kit 1.15.0 — scrub del golden master (2026-07-03)

Sexta mejora del backlog PragProg (M7 de `docs/analisis-pragmatic-programmer.md`;
Topic 41 *"no apoyar tests en cosas no confiables"* — timestamps exactos,
ids, posiciones absolutas). Sin esto, cualquier salida del código original con
volátiles vuelve el golden master perma-rojo — y un golden perma-rojo mata la
credibilidad de todo el gate. Smoke suite: 97/97.

## La idea

- `golden.scrub.json` en el root de fixtures declara los volátiles:
  `{"rules": [{"pattern": "<regex>", "replace": "<placeholder>"}]}`.
- `golden-diff` enmascara AMBOS lados (received y approved) antes de comparar —
  solo texto; el binario sigue byte a byte. El match vía scrub se reporta
  **APARTE** (`N via scrub` + conteo de sustituciones por regla): el masking
  jamás es invisible.
- **Cadena de custodia**: las reglas se declaran en characterize (paso nuevo,
  ANTES de la aprobación) y el humano las aprueba junto con los `.approved` —
  son contrato. gate-check flaggea cualquier edición posterior a
  `golden.scrub.json` como señal blanda SIEMPRE visible (`--strict` la gatea):
  una regla ensanchada puede enmascarar divergencia real.
- Archivo de scrub inválido (JSON roto, regex rota) = **exit 2 explícito** —
  el scrub nunca se saltea en silencio.
- Preferencia documentada: arreglar el determinismo EN LA FUENTE (checklist de
  Phase 2 de characterize); el scrub es para lo que genuinamente no se controla.

## Engine (qa_ledger.py)

- `_load_scrub_rules()` / `_scrub()` + integración en `cmd_golden_diff`
  (`matched_scrubbed`, `scrub_rules`, `scrub_substitutions` en el JSON —
  el conteo es del lado RECEIVED; sumar ambos lados duplicaría cada volátil).
- gate-check: lista `scrub_rules_touched` (soft) en veredicto y JSON — cubre
  agregar, modificar y BORRAR el archivo (borrar reglas también es editarlas).
- Shape estricta del archivo: top-level lista, key `rules` ausente o typo =
  exit 2 — un error de forma no puede degradar a "cero reglas" en silencio.

## Hardening (review fresco pre-commit, 4 hallazgos aplicados)

- AttributeError cruda con lista top-level en el scrub file → exit 2 limpio.
- `{}` sin key `rules` cargaba cero reglas en silencio → exit 2.
- Doble conteo de sustituciones (received + approved al mismo dict) → solo
  received.
- Borrado de `golden.scrub.json` no se flaggeaba (el check vivía solo en
  líneas `+`) → también en `-`.

## Smoke

- **T37** — respetando INV-GOLDEN-01: crear un `.approved` es un acto HUMANO
  incluso en tests, así que el path CLEAN-vía-scrub NO se auto-testea (misma
  disciplina que el path CLEAN byte-a-byte desde 1.3.0). Se prueba la mecánica
  a nivel función (enmascara, cuenta, binario intacto, divergencia real no se
  tapa) + los paths CLI sin `.approved`: scrub no fabrica aprobación (DIVERGE
  se mantiene), scrub inválido exit 2, gate-check flaggea ediciones.

## Diferido consciente

- Reglas por-fixture (hoy son por root de fixtures) — si un corpus real lo
  pide, se agrega `"glob"` opcional por regla.
