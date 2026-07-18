# uscha-kit 1.41.3 — mirador live-view no longer spams browser tabs (2026-07-18)

A hotfix for a regression shipped in 1.41.2. Smoke suite: 358/358.

## Fix

### mirador-render auto-open + `--refresh` spawned a new browser tab every cycle (HIGH, regression)
1.41.2 made `mirador-render.py` auto-open the rendered file in the browser. But the live
second-screen view (`mirador-watch`, and any render with `--refresh N`) injects a
`<meta http-equiv="refresh">` so a single open tab **reloads itself** every N seconds — and
the renderer is re-invoked each cycle. Auto-opening on every invocation therefore spawned a
**new browser tab on every refresh** (30s → a wall of tabs), making the machine unusable while
a watch loop ran. The `--no-open` flag was not enough on its own: a watch process started
before 1.41.2 calls the renderer without it.

Fix: auto-open is now suppressed whenever `--refresh > 0` (live mode) — the meta-refresh owns
the reload, in one tab. Auto-open remains for a genuine **one-shot** render (`/uscha-mirador`
with no `--refresh`), and `--no-open` still suppresses it everywhere. The `OPEN IT: <abs path>`
line is always printed, so the live view is one manual open away and never hidden.
`mirador-render.py:main`. Regression: smoke **T79** (live → 0 opens, one-shot → 1, `--no-open`
→ 0).

Because the renderer is a fresh subprocess each cycle, a running watch loop picks up this fix
on its **next** render with no restart — and for a link/junction skill install (the renderer
lives in this repo), no reinstall either. A copy-mode install needs a reinstall to get the
fixed file.

## Note on the test suite
The installer/npm smoke checks still hardcode the version string, so this bump updated those
literals. A follow-up could have them read `VERSION` dynamically.
