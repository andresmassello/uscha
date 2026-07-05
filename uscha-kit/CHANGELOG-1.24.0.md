# dev-loop-kit 1.24.0 — plugin de Claude Code (2026-07-03)

El kit ahora se distribuye como **plugin instalable** para Claude Code — el repo es
su propio marketplace. Los schemas se verificaron contra los docs oficiales
(code.claude.com/docs: plugins, plugins-reference, plugin-marketplaces,
discover-plugins) ANTES de escribir una línea — formato de tool real jamás se
inventa. Smoke suite: 140/140.

## Instalación (Opción C, la recomendada para Claude Code)

```
/plugin marketplace add andresmassello/SPEC-LOOP
/plugin install specloop@specloop
```

- Las 7 skills quedan como `specloop:specloop-*` (el namespace del plugin se suma
  al prefijo propio — mismo patrón que sonarqube:sonar-*).
- **El hook INV-GOLDEN-01 se auto-registra** (`hooks/hooks.json` con
  `${CLAUDE_PLUGIN_ROOT}`): desaparece la edición manual de settings.json que la
  instalación global requería. Linux: el hook sigue siendo PowerShell — pwsh +
  ajuste del comando (el doctor lo señala con remedio).
- Updates versionados: el plugin declara `version`, así que `/plugin update`
  solo actualiza con bump de release.
- **Cero reestructuración**: `plugin.json` soporta path custom de skills
  (`"skills": "./.claude/skills/"`) — el layout canónico del kit no cambió, y
  las Opciones A (por proyecto) y B (global copy/junctions) siguen intactas
  para Codex/Gemini/Cursor. El plugin es EMPAQUETADO, no dependencia: el
  agnosticismo no se negocia.

## Qué se agregó

- `dev-loop-kit/.claude-plugin/plugin.json` — manifest (name `specloop`,
  skills path custom, hooks auto-registrados, MIT).
- `dev-loop-kit/hooks/hooks.json` — registro PreToolUse del hook del golden
  vía `${CLAUDE_PLUGIN_ROOT}`.
- `.claude-plugin/marketplace.json` (root del repo) — el marketplace `specloop`
  con source relativo `./dev-loop-kit`.
- **doctor**: tercer modo de instalación detectado (`plugin`, path bajo
  `~/.claude/plugins/`); en modo plugin el hook cuenta como registrado si
  `hooks/hooks.json` existe (auto-registro — settings.json ya no participa).
  JSON expone `plugin_install`.
- **Smoke T44 — el sync de versión ahora es un HECHO**: VERSION =
  config.version = plugin.json.version = marketplace.version, o la suite falla.
  La regla 6 del repo pasa de triple a **quíntuple** (con CHANGELOG).

## Nota para la máquina del autor

Los junctions de la Opción B y el plugin no deben convivir (skills duplicadas):
la máquina donde se desarrolla el kit se queda con junctions (siempre al día con
main); el plugin es el canal para las demás máquinas y terceros.
