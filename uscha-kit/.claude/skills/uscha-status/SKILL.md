---
name: uscha-status
description: >
  One-glance progress readout of a uscha project, rendered IN CHAT — for surfaces
  where the statusline is not visible (Claude Desktop, Codex, plain terminals, CI
  logs). Reads the same measured facts the statusline reads (ledger["measured"],
  refreshed via uscha_progress.py) and prints a compact block: derived phase, loop
  odometer, measured acceptance bar, tests, next criterion, roadmap. Read-only:
  it NEVER runs tests, gates or readiness — it renders persisted evidence or says
  honestly that there is none. Invoke for "uscha status", "/uscha-status",
  "como vamos", "where are we", "progreso".
allowed-tools: Read, Bash, Glob
---

# uscha-status — the statusline, on demand, in chat

Three zoom levels exist in the kit: the **statusline** (passive, every turn), this
skill (**pull** — one screen when the human asks), and the **mirador** (bird's-eye
HTML). This skill exists because some surfaces never show a statusline; the answer
is the same data, printed in chat when requested.

## Contract

- **Read-only over persisted facts.** Never run `readiness`, tests, or gates. The
  numbers come from what the loop already recorded; if nothing was recorded, SAY SO
  — never measure on the fly, never invent.
- **Source, in order:**
  1. If `.claude/scripts/uscha_progress.py` exists, run it (fast: it parses JSON +
     one .md, never runs tests), then read `.claude/uscha-progress.json`.
  2. Else read `QA-LEDGER.json` directly: `measured` (summary + per-repo odometer)
     and, for tests/coverage, the last snapshot of the tracked repo.
  3. No `uscha.config.json` → this is not a uscha project; say so and stop.
- **Measured beats narrated.** If `measured` is absent and only ACCEPTANCE
  checkboxes exist, you may show the checkbox count but label it **narrated
  (checkboxes)** and recommend feeding the trail: the devloop records at every pass
  close (kit 1.47.0); a manual `readiness --record` also works.

## Output (one compact block, nothing else)

Render ONE fenced block, max ~8 lines. Omit any line whose datum is null — a
missing source shrinks the block, it never becomes "n/a" noise. Shape:

```
USCHA — qa ×3 · ██████████░░ 83% AC 5/6 (measured) · tests 42✓ · cov 71%
next → AC-5: every published ES doc has its EN twin
loops   backend-api qa ×3 · mobile-app build (plateau ⚠ on backend-api if flagged)
roadmap 3/7 · next → 02 API
recorded 2026-07-23 · score 35 NOT READY
```

Line guide:
- **Header**: label · derived phase (+`×loops` when > 0) · acceptance bar with `%`
  and `done/total`, tagged `(measured)` or `(narrated — checkboxes)` · tests ·
  coverage. Build the bar with `█`/`░` (12 cells).
- **next**: the first criterion not closed by a green test (from `measured.next`).
- **loops**: only for multi-repo projects — one entry per repo from
  `measured.repos`: name, phase, `×N`, and `plateau ⚠` when `stalled` is true.
- **roadmap**: only if the config declares one (`roadmap_done/roadmap_total/next`).
- **recorded**: the `at` timestamp + score/band of the last `--record`. This is
  WHEN the evidence was captured — facts do not move without new evidence.

## Degradation (honest, specific)

- `measured` missing entirely → print: *"No measurement recorded yet — the trail
  feeds from `readiness --record` (the devloop runs it at every pass close; you can
  also run it manually)."* Then show the narrated checkbox count if ACCEPTANCE.md
  exists, labeled as narrated.
- Ledger missing → *"No QA-LEDGER.json — run the devloop (or `uscha init`) first."*
- Never pad the block with explanations; the block IS the answer. Add prose only
  when the human asks a follow-up.
