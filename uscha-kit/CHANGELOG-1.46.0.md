# uscha-kit 1.46.0 — a progress statusline, generic and auto-wired (2026-07-21)

The progress statusline (the colored bars at the bottom of Claude Code) was a prototype living
inside a single consumer project (ANTI-FARO), full of that project's specifics. This
generalizes it into the kit and makes the installer wire it, so a project gets a live progress
readout with **zero** `settings.json` editing. Smoke suite: 374/374.

## Generic, config-driven scripts
`templates/scripts/uscha_statusline.py` (the renderer) and `uscha_progress.py` (the Stop-hook
refresher) carry **no** project-specific data. Everything that used to be hardcoded — the
tracked repo, its label, its roadmap, its build priority — now comes from `uscha.config.json`:

```jsonc
"repos": [{
  "name": "myproj", "path": ".", "type": "python", "label": "MY PROJECT",
  "roadmap": [ {"name": "01 Core", "path": "src/core.py"}, ... ],
  "build_priority": ["02 API", "01 Core"]
}]
```

The refresher reads REAL numbers only — acceptance from `ACCEPTANCE.md` (tolerant of `AC-01`
and `**AC-01**`), tests/coverage from the ledger snapshot, roadmap items counted as built when
their file actually exists and is non-trivial. Truth-pass: a missing source leaves its field
null. The renderer degrades to an **empty** line (hidden) when there is no data — no hardcoded
fallback ever.

## Auto-wired by `uscha init`
`init` now also copies the two scripts to the project's `.claude/scripts/` and MERGES into
`.claude/settings.json`, without clobbering:
- `statusLine` → `python .claude/scripts/uscha_statusline.py` (added only if absent; an
  existing DIFFERENT statusLine is reported as a conflict, never overwritten — `--force` to
  replace);
- a `Stop` hook → `python .claude/scripts/uscha_progress.py` (appended only if not already
  registered; idempotent).

Commands are by name with forward slashes (Windows eats backslashes in the statusLine command;
absolute paths are brittle across machines). A clean repo initializes fully; a repo with a
conflicting file stays per-file (kit 1.44.1) and the settings merge still runs.

## Regressions
- Smoke **T88**: the scripts are generic (config-driven, no ANTI-FARO), render with the
  config's label, and degrade to empty with no data.
- Smoke **T89**: `init` wires `statusLine` + Stop hook + scripts, is idempotent, and never
  clobbers a foreign `statusLine`.
- Smoke **T85** updated: `init` now writes the scripts + `settings.json` alongside the templates.

## Note
Migrating the ANTI-FARO consumer to the kit's version (dropping its local prototype) is the
consumer's job, out of this repo. Making the statusline command auto-detect `python`/`py -3`
like the npm router is a possible follow-up.
