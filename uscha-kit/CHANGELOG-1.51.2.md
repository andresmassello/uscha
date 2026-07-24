# uscha-kit 1.51.2 — the mirador lives in ONE browser tab (2026-07-24)

Field complaint: the mirador "pops a new browser tab every step". 1.41.3 fixed this for the
**watch** loop, but left the **one-shot** render — the path the agent takes when it renders the
dashboard on each pass — opening a fresh tab every single time. Opening a `file://` through
`os.startfile` / `open` / `xdg-open` always creates a NEW tab, so N renders meant N tabs.
Smoke suite: 388/388.

## Fix — auto-open is tied to the FILE's first materialization, not to the render
`mirador-render.py` now auto-opens **only when it creates the output file**. Every later render
rewrites the same file, and the page carries a `<meta http-equiv="refresh">` — **now on by
default (10s)** rather than opt-in — so the tab that is already open reloads itself in place.
One tab, always current, no matter how many times the mirador is rendered.

- **`--open`** (new): force a reopen when you closed the tab — `pre_existed` tracks the FILE,
  not a live tab, so a deliberate override is needed and now exists (`uscha mirador --open`).
- **`--no-open`** still suppresses everywhere and wins over `--open` (headless/CI, watch loop).
- **`--refresh 0`** opts out of the auto-reload for a frozen snapshot.
- The `OPEN IT: <abs path>` line is still always printed, so nothing is ever hidden.

The watch paths are unchanged in effect: `uscha mirador --watch` and `mirador-watch.sh/.ps1`
already passed `--no-open` and open at most once, so 1.41.3's guarantee holds.

## Also
The suite itself opened a real browser tab on every run (one mirador render lacked
`--no-open`) — the same spam, from the tests. Fixed.

Regression: smoke **T79**, rewritten for the new contract — first materialization opens once,
a re-render opens zero, `--open` forces one, `--no-open` wins over `--open` **and is asserted
on a genuinely fresh file** (on an existing one the first-materialize gate alone would mask a
dropped `--no-open` check), the default injects the meta-refresh, and `--refresh 0` does not.
