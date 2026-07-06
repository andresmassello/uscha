# uscha-kit 1.34.0 — mirador: project name + live second-screen view (2026-07-05)

Two operator asks: (1) the project name, clear at the top; (2) a mirador you can **watch on a
second screen** while you keep coding in the terminal with the agent. Smoke suite: 195/195.

## Project name (from config, shown at the top)

- `dashboard` emits `project` from `uscha.config.json`'s `"project"` (or `"name"`); if unset, it
  falls back to the joined repo names (truth-pass — no invented name). This is the ONE engine
  touch this release: a project name is human-set config metadata, not vendor/LLM data, so the
  engine stays model-agnostic.
- `uscha-discovery` asks the project name **first** and writes it to the config.
- The mirador template shows it as a **prominent title** at the top.

## Live second-screen view

- **`mirador-render.py`** (standalone, in the skill folder): runs `dashboard --json`, merges the
  sidecar telemetry (in the adapter, NEVER the engine), injects `const DATA`, writes
  `mirador.html`. `--refresh N` injects a `<meta http-equiv="refresh">`.
- **`mirador-watch.sh` / `.ps1`**: re-render every N seconds (default 30) from the current
  ledger. Open `mirador.html` on a second monitor; it reloads on its own. **No server.**
- Honest limit: as live as the **ledger** — the picture changes at the dev-loop's measured
  checkpoints (snapshots, gates, `readiness --record`), not per keystroke.

## Watch-safe telemetry (gotcha fix)

`telemetry-extract.py` now **upserts by session** (default key = transcript basename): a refresh
loop re-runs the extractor without duplicating the session's line, so the aggregated totals
never inflate. (Without this, watch mode would over-count tokens every tick.)

## Boundary intact

Telemetry is still vendor-narrated, merged ONLY by the adapter (`mirador-render.py`), never by
`qa_ledger.py`; shown, never gated, never fed into readiness. The template still degrades (no
sidecar → no strip).

## Truth-pass fix: skill-count drift (doctor + plugin)

When `uscha-mirador` shipped (1.32.0), two registries were not updated (caught here):
- `doctor`'s `USCHA_SKILLS` list was missing `uscha-mirador` → it reported `7/7` for 8 skills.
- `plugin.json` / `marketplace.json` **descriptions** said "7 skills / 24 subcommands" (the
  plugin *install* was fine — it points at the skills directory — but the prose was stale).
Both fixed (8 skills / 25 subcommands), and **mechanized** so it can't drift again: smoke
**T57** asserts `USCHA_SKILLS` equals the `uscha-*` skill directories on disk. (The doc-version
gate T52 covers versions; T57 now covers the skill roster.)

## Smoke (T54 upsert + T55 project + T56 render + T57 skill-roster)

Extractor re-run → still ONE line (upsert); config `project` → dashboard emits it, absent →
repo-name fallback; `mirador-render.py` → `mirador.html` carrying the project name, merged
telemetry, and the meta-refresh; the doctor's skill list matches the skills on disk.

The fresh review also caught two robustness gaps in `mirador-render.py` (unguarded `json.loads`
and template read) — now they return a clean error instead of a traceback (it runs in a watch
loop, so a clean non-zero is what the loop expects).
