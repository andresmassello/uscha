# dev-loop-kit 1.20.0 — instalación global (2026-07-03)

Release chica de instalabilidad: el kit ahora puede instalarse UNA vez en
`~/.claude/` y quedar disponible para todos los proyectos, existentes y nuevos.
Sin cambios de engine. Smoke suite: 121/121.

## Qué cambia

- **Resolución portable del engine**: `dev-loop` y `sys-doc` resuelven
  `qa_ledger.py` primero en el proyecto (`./.claude/skills/dev-loop/`) y caen a
  la instalación global (`~/.claude/skills/dev-loop/`) si no hay local. La
  instalación por proyecto sigue teniendo precedencia (un proyecto puede pinnear
  su versión del kit copiándolo local).
- **Instalación global documentada completa** (README § Instalación, Opción B):
  las SEIS skills (antes el snippet copiaba solo dev-loop y sys-doc — quedó de
  cuando eran las únicas dos) + el hook `block-approved-writes.ps1` a
  `~/.claude/hooks/` con registro en `~/.claude/settings.json`, para que
  INV-GOLDEN-01 rija en todos los proyectos.
- **Qué sigue siendo por-proyecto** (estado, no instalable — ahora explícito):
  `dev-loop.config.json` (los `path` son relativos a la raíz de la run, y la
  quality bar declarada del humano vive ahí — 1.17.0), `QA-LEDGER.json`,
  `ACCEPTANCE.md`, y el `.gitattributes` de templates para migración.
- Nota para la máquina donde se DESARROLLA el kit: junction/symlink por skill al
  repo canónico en vez de copia — global siempre al día con main.

## Diferido consciente

- Un comando `install.sh`/`install.ps1` empaquetado: hoy son dos líneas de shell
  documentadas; si el on-ramp real (dogfooding) muestra fricción, se mecaniza.
