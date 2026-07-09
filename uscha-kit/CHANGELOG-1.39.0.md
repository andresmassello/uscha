# uscha-kit 1.39.0 ? universal machine installer

## Added

- `install-uscha.py`: one stdlib machine installer for Codex and Claude.
  - Codex target creates a personal local plugin at `~/plugins/uscha` and updates `~/.agents/plugins/marketplace.json`.
  - Claude target installs global skills/hooks under `~/.claude`.
  - Supports `install`, `doctor`, `version`, `init`, `--dry-run`, testable `--home`, and `--mode copy|link`.
- Codex plugin manifest at `.codex-plugin/plugin.json` for plugin-first adoption.
- Skill fallback examples now include Codex plugin/raw-skill install paths, not only `~/.claude`.

## Verification

- Smoke target: 222/222 green.
