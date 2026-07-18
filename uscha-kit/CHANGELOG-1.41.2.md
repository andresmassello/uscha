# uscha-kit 1.41.2 — mirador launch UX (2026-07-18)

A usability release for the mirador (the bird's-eye dashboard). No engine measurement
logic changed; this makes the mirador honest about "not ready" and trivial to launch from
inside a running project — "nada de magia oculta". Smoke suite: 357/357.

## Fixes

### 1 — "NOT READY" no longer reads as "hasn't started" (readiness title)
The mirador mapped the `NOT READY` band (score 0–49) to a fixed title `"Todavia no arranca"`
("hasn't started yet"). But a project at, say, readiness 22 HAS started — it simply lacks
enough **measured** evidence. The wording contradicted the score right next to it. Fix: the
`NOT READY` title is now score-aware — `"Todavia sin evidencia medida"` only at score 0, and
`"En construccion -- evidencia insuficiente"` above 0. The dead fixed entry was removed from
`_MIRADOR_TITLE` so the old wording cannot reappear. `qa_ledger.py:cmd_dashboard`.
Regression: smoke **T78**.

## Launch UX

### 2 — `mirador-render.py` self-resolves its siblings
`--engine` (the `qa_ledger.py` path) and `--template` (the mirador HTML) now default to the
renderer's **sibling** skill files. From any project you can run the renderer — or
`/uscha-mirador` — with just `--ledger`, no long absolute paths. `mirador-render.py:main`.

### 3 — the rendered mirador opens itself, and always prints where it is
After writing `mirador.html` the renderer opens it in the default browser (best-effort:
`os.startfile` on Windows, `open`/`xdg-open` elsewhere — never fails on headless/CI) and
prints the **absolute path** on an `OPEN IT:` line. A new `--no-open` flag suppresses the
auto-open; the live-watch loop (`mirador-watch.sh`/`.ps1`) and the smoke suite pass it so
they never spawn browser tabs on every refresh. `mirador-render.py`.

## Note on the test suite
The installer/npm smoke checks still hardcode the version string, so this bump updated those
literals (T44, T66/T67 assertions). A follow-up could have them read `VERSION` dynamically.
