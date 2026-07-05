# uscha-kit 1.29.0 — rebrand: spec-loop -> Uscha (2026-07-05)

La metodologia se renombra a **Uscha**. Rebrand completo: la marca, las 7 skills
(specloop-* -> uscha-*, comandos /uscha-discovery etc.), el plugin (specloop -> uscha),
el kit (dev-loop-kit -> uscha-kit), el config (dev-loop.config.json -> uscha.config.json)
y el paper (docs/paper/uscha-paper.*). Cambio BREAKING: los slash-commands cambian de
prefijo.

## Que NO cambio
- Los subcomandos de qa_ledger.py (readiness, waste-check, gate-check, ...) y el propio
  qa_ledger.py: nombres neutros, sin marca.
- El hook block-approved-writes.ps1: nombre neutro.
- Los CHANGELOGs historicos y audits/: registro, se dejan verbatim.
- El remoto GitHub (SPEC-LOOP) y la carpeta local del checkout: fuera de alcance (rename
  de repo/filesystem es otra operacion).

## Verificacion
- Smoke 177/177 (la suite y sus paths se actualizaron al nuevo kit).
- Sync quintuple 1.29.0 (T44).
- rg --hidden 'spec.?loop' sin colgados fuera de los historicos protegidos.
