# uscha-kit 1.43.0 — `uscha mirador`: one command, no python, no paths (2026-07-18)

Adoption fix. Bringing up the mirador for a running project meant typing
`python <long-skill-path>/mirador-render.py --ledger QA-LEDGER.json` — friction that pushed
users away. The kit already had an npm/npx router (`bin/uscha.js`) forwarding to
`install-uscha.py`; it was missing one verb. Smoke suite: 361/361.

## New: the `mirador` verb

From the root of any project that has a `QA-LEDGER.json`:

```
uscha mirador                        # render + open the dashboard
uscha mirador --watch                # live second-screen view (auto-refresh, one tab)
npx @andresmassello/uscha mirador    # same, zero install
```

No python, no paths, no flags required. The verb:
- resolves the renderer inside the kit (either skill-tree layout), which self-resolves its own
  engine + template siblings;
- defaults the ledger to the `QA-LEDGER.json` convention in the current directory
  (`--ledger` to point elsewhere);
- one-shot renders and opens the file; `--watch` opens ONE self-reloading tab and re-renders
  every `--interval` seconds (default 30) WITHOUT re-opening — no browser-tab spam (honors the
  1.41.3 live-mode rule);
- fails clearly (exit 1) when the ledger is missing, instead of a stack trace.

`install-uscha.py:cmd_mirador` (exposed through the existing `bin/uscha.js` router).
Regression: smoke **T81**.

## Docs
`INSTALL.md` gains a "See the dashboard (mirador)" section; the uscha-mirador `SKILL.md`
leads its human/terminal path with `uscha mirador`.

## Note on the test suite
The installer/npm smoke checks still hardcode the version string, so this bump updated those
literals. A follow-up could have them read `VERSION` dynamically.
