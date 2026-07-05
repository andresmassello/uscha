# dev-loop-kit 1.21.0 — namespace specloop-* (2026-07-03)

Release de naming, decidida por el humano entre tres opciones (prefijo largo /
prefijo corto / dejar como está): las seis skills pasan de nombres genéricos a
**namespace `specloop-*`**. Nombres como `discovery` o `characterize` eran
squatting del namespace global — cualquier otro kit podía pisarlos (evidencia:
el harness ya desambiguaba proyecto-vs-global con los genéricos). Se hace AHORA
porque es el momento más barato: antes de publicar, renombrar no rompe a nadie.
Sin cambios de engine. Smoke suite: 121/121.

## El mapa de renombres

| Antes | Ahora |
|---|---|
| `/discovery` | `/specloop-discovery` |
| `/adr-refine` | `/specloop-adr-refine` |
| `/reverse-discovery` | `/specloop-reverse-discovery` |
| `/characterize` | `/specloop-characterize` |
| `/dev-loop` | `/specloop-devloop` |
| `/sys-doc` | `/specloop-sysdoc` |

- **El path del engine cambia** (breaking para scripts que lo hardcodeaban):
  `.claude/skills/dev-loop/qa_ledger.py` → `.claude/skills/specloop-devloop/qa_ledger.py`.
  El fallback global (1.20.0) apunta ahora a `~/.claude/skills/specloop-devloop/`.
- **NO cambian**: `dev-loop-kit` (el nombre del kit), `dev-loop.config.json`
  (el archivo de config), los subcomandos del engine, ni el schema del ledger.
- Instalación global: re-crear los junctions/copias con los nombres nuevos
  (los viejos quedan rotos tras el rename de directorios).
- Sweep completo con truth-pass: SKILL.md (frontmatter + referencias cruzadas),
  READMEs, templates/CLAUDE.md, decks ES/EN, playbooks ES/EN, onepagers,
  pitches, skills-referencia, smoke. Los artefactos HISTÓRICOS (audits/*.json,
  changelogs viejos, HANDOFFs de releases pasadas) NO se retro-editan —
  documentan el estado de su época.
