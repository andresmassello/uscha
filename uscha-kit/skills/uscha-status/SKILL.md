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

## Before the readout: are the installed skills older than the kit? (2.2.0)

A field report found `~/.claude/skills/uscha-*` still on 1.54.0 while the kit in the repo was
1.97.0. An entire discovery ran on prose three months stale and NOTHING said so, because a
SKILL.md carried no version to compare. Since 2.2.0 every generated orientation block opens with
`<!-- uscha kit: X.Y.Z ... -->`, so the comparison is mechanical. Do it FIRST, before the
breadcrumb:

1. Run the engine's own check — it reads the marker out of every installed `SKILL.md` and
   compares it against the kit's `VERSION`:

   ```
   python <kit>/.claude/skills/uscha-devloop/qa_ledger.py doctor --json
   ```

   Read `skills_installed`: one row per install root the installer writes to (Claude
   `~/.claude/skills/`, Codex `~/plugins/uscha/skills/`, pi `~/.agents/skills/`, and the other
   Agent-Skills roots), each with `status`, `installed` and `kit`. `doctor` exits 0 whether or
   not anything is outdated — this reports, it never gates.
2. If any row reads `outdated`, print exactly ONE line ABOVE the breadcrumb, then continue
   normally:

   ```
   SKILLS OUTDATED: installed 1.54.0 < kit 2.2.0 -- run `python install-uscha.py install --target claude`
   ```

   Where the installed block predates 2.2.0 and carries no marker at all, `installed` is null:
   say `installed <no kit: marker, pre-2.2.0>` rather than inventing a version.
3. `not installed` is NOT a finding — the kit installs one agent at a time, and six absent roots
   are the normal shape of a healthy machine. Say nothing about them.

Advisory, always: the line never blocks the readout, never changes a number, and the block below
prints exactly as it would have. What it removes is the silence.

Honest limit: an installed skill that predates 2.2.0 does not carry these instructions, so on
that surface the warning cannot come from the skill itself. The `doctor` seam is the instrument
that still works there — it runs from any kit checkout and reads the installs from outside.

<!-- uscha:orientation-block:begin -->
<!-- uscha kit: 2.6.0 -- generated region: edit tools/skill-blocks/, then run `python tools/gen-skill-blocks.py` (never this block by hand) -->

## Orientation markers (non-negotiable)

The operator must never have to ask "where am I?" or "what happens now?".

This skill is a **one-shot read-only readout**: its block IS the answer. It therefore does NOT
take the conversational close block — that would be exactly the padding this skill forbids.
It carries the two minimal markers instead.

**No statusline (kit 2.4.0): the visible reply IS the statusline.** On a surface with no live
statusline — Codex, pi, a plain terminal — this readout IS the operator's only signal, so it
MUST appear in the visible reply text, never only inside a collapsed tool-call log.

**Open with a breadcrumb:**

`[uscha · status · step <n> → <target>]`

**End with the two routing lines, and nothing else:**

```
Next: <the next action, derived from what this readout just showed>
Run:  <the exact command or skill to invoke>
```

`Next` is **derived** from the state you just read — never copied from a fixed route,
including any `Flow:` line in this file. If nothing is actionable, say that plainly rather
than inventing a step. Keep the CONTENT in the conversation's language and the labels
(`Next`, `Run`) verbatim — the smoke suite checks for them.
<!-- uscha:orientation-block:end -->

## Contract

- **Read-only over persisted facts.** Never run `readiness`, tests, or gates. The
  numbers come from what the loop already recorded; if nothing was recorded, SAY SO
  — never measure on the fly, never invent.
- **Source, in order:**
  1. If `.claude/scripts/uscha_progress.py` exists, run it (fast: it parses JSON +
     one .md, never runs tests), then read `.claude/uscha-progress.json`. Since kit
     1.48.1 that file carries everything this block needs: `measured_at`, `score`,
     `band`, `acceptance_source`, and the full per-repo `repos` odometer.
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
  and `done/total`, tagged from `acceptance_source`: `(measured)` or
  `(narrated — checkboxes)` · tests · coverage. Build the bar with `█`/`░` (12 cells).
- **next**: the first criterion not closed by a green test (from `next`).
- **loops**: only for multi-repo projects — one entry per repo from the `repos`
  map: name, phase, `×N`, and `plateau ⚠` when `stalled` is true.
- **roadmap**: only if the config declares one (`roadmap_done/roadmap_total/next`).
- **recorded**: `measured_at` + `score`/`band` of the last `--record`. This is
  WHEN the evidence was captured — facts do not move without new evidence. If the
  field is absent (nothing recorded yet), omit the line; never guess a timestamp.

**Fast-path mode (ADR-003):** if the ledger carries `fast_path` entries, add ONE line to the
block with the latest verdict per repo (`fast-path: ALLOW (intent...)` / `ESCALATED`). Absent
entries → no line at all: silence is honest when no mode was requested.

**Evidence origin (ADR-007):** if the latest snapshot was measured on a DIRTY tree, add ONE
line: `evidence: measured dirty at <sha8> - not from the commit alone`. Say nothing when the
tree was clean (the normal case needs no words) and nothing when it is `null` (unmeasurable,
and inventing a state is worse than silence). This never explains a blocked phase: it scores
nothing and gates nothing.

**Spec-drift (ADR-005):** if the ledger carries a `spec_drift` run, add ONE line:
`spec-drift: N stale / M docs (advisory)` — or `spec-drift: no drift measured` when zero are
stale. Always label it advisory; it never explains a blocked phase. Absent key → no line.

**Clean-room (ADR-008):** if the ledger carries `clean_room` runs, add ONE line with the
latest run per repo: `clean-room: GREEN @ <sha8> (12.3s)` / `RED @ <sha8>`. When the gate is
declared (`mode: "final"`) and the latest run does not match the current HEAD, append
`(stale for gate)`. Absent key → no line.

**Roundtrip (ADR-009 slice 2):** if the ledger carries a `roundtrip` run, add ONE line:
`roundtrip: N/M promoted traceable by uscha-spec id (advisory)`. Absent key → no line —
silence is honest when the loop was never measured.

## Degradation (honest, specific)

- `measured` missing entirely → print: *"No measurement recorded yet — the trail
  feeds from `readiness --record` (the devloop runs it at every pass close; you can
  also run it manually)."* Then show the narrated checkbox count if ACCEPTANCE.md
  exists, labeled as narrated.
- Ledger missing → *"No QA-LEDGER.json — run the devloop (or `uscha init`) first."*
- Never pad the block with explanations; the block IS the answer. Add prose only
  when the human asks a follow-up.
