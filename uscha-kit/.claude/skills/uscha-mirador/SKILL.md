---
name: uscha-mirador
description: >
  Bird's-eye status view ("mirador") of a spec-loop project: one glance at
  readiness, sub-scores, the phase path, invariants, QA loops and a readiness
  time-lapse. Runs `qa_ledger.py dashboard --json` (read-only, deterministic,
  zero LLM narration), injects that JSON into mirador.template.html, writes
  mirador.html at the project root and opens it. The skill WIRES, it does not
  calculate — every number comes from the ledger (truth-pass: a field with no
  source shows null and the template degrades, never invented). Invoke for
  "mirador", "vista de estado", "bird's-eye", "dashboard del proyecto".
allowed-tools: Read, Write, Glob, Grep, Bash
---

# uscha-mirador — bird's-eye status view

Paints the REAL state of the project at a glance. It does not narrate or estimate: it
wires the JSON the engine emits into the template. Read-only.

## Contract

- **Source of truth:** `qa_ledger.py dashboard --json` — aggregates ONLY state the
  ledger already has (readiness, subscores, phases, specs, adrs, inv, layers, loops,
  snapshots, evidence). A field with no source comes out `null`/`[]`; the template
  degrades. **A datum is never invented.**
- **Template:** `mirador.template.html` (in this folder). The data block lives between
  `/*MIRADOR_DATA_START*/` and `/*MIRADOR_DATA_END*/`; the sample `const DATA` it ships
  with is the **offline fallback**. The skill replaces ONLY that region; it does not
  touch the rest of the HTML.

## Flow

1. **Resolve the engine.** Use the first one that exists:
   - `./.claude/skills/uscha-devloop/qa_ledger.py` (per-project install)
   - `~/.claude/skills/uscha-devloop/qa_ledger.py` (global install)

2. **Resolve the ledger.** `QA-LEDGER.json` in the cwd (or the `--ledger` the user
   points to). If it does not exist, warn: you have to run `uscha-devloop` (or
   `qa_ledger.py init`) first — with no ledger there is no state to look at.

3. **Generate the state JSON** (read-only, writes nothing):
   ```bash
   python3 <engine> dashboard --ledger QA-LEDGER.json --json > .mirador-data.json
   ```
   For the time-lapse: the history is filled with `qa_ledger.py readiness --record`
   (opt-in) at the loop's checkpoints; if nothing has been recorded yet, `snapshots`
   comes out `[]` and the time-lapse stays empty (it is prospective, not backfilled).

4. **Inject into the template.** Read `mirador.template.html`, replace EVERYTHING between
   `/*MIRADOR_DATA_START*/` and `/*MIRADOR_DATA_END*/` (including the old `const DATA`)
   with:
   ```
   /*MIRADOR_DATA_START*/
   const DATA = <the JSON from .mirador-data.json>;
   /*MIRADOR_DATA_END*/
   ```
   Do not touch anything outside that region. Write the result as `mirador.html` at the
   project root.

5. **Open the file** (best-effort, does not fail if it can't — headless/CI):
   - Windows: `start "" mirador.html`
   - macOS: `open mirador.html`
   - Linux: `xdg-open mirador.html`

   ALWAYS print the absolute path of `mirador.html` (even if it can't be opened).

6. **Cleanup:** delete `.mirador-data.json` (temporary).

## Rules

- **Zero computation in the skill.** The numbers come from the ledger. If a panel looks
  empty, it's because the engine doesn't have that source yet (truth-pass), not because
  painting it was missed.
- **Read-only.** The skill does not run gates or modify the ledger. `dashboard` is
  read-only; the only one that writes (opt-in) is `readiness --record`, and that is the
  loop's decision, not this skill's.
- **`mirador.html` is a generated artifact** — suggest adding it to the project's
  `.gitignore`; it regenerates whenever you want.
