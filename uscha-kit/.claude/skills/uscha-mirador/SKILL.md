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
- **Session telemetry (optional, vendor-reported):** if `.uscha/telemetry.jsonl` exists,
  the skill aggregates it and MERGES a `telemetry` object into `DATA`. This is the ONE
  panel that is **narrated by the vendor (Claude Code), not measured by the engine** —
  tokens, wall time, model, effort — so it renders in a **segregated strip** labeled as
  such, never mixed with the measured panels. `dashboard --json` NEVER emits it; it enters
  only through this adapter. Absent file → no strip (degrades). This is the doctrinal
  line: telemetry is neither a fact-gate nor a guess-advisor, so it must not dilute
  *measured beats narrated*.

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

4. **Merge session telemetry (optional, vendor-reported).** If `.uscha/telemetry.jsonl`
   exists, read it (one JSON object per line, schema below) and aggregate into a single
   object, then add it to the state JSON under the key `telemetry`:
   ```
   telemetry = { source: "Claude Code",
                 sessions: <line count>,
                 tokens_in: <sum>, tokens_out: <sum>, ms: <sum wall-time>,
                 model: <the model, or a "+"-joined list if several>,
                 effort: <the latest effort>,
                 by_model: [ {model}, ... ] }
   ```
   The engine's `dashboard` NEVER produces this — it is vendor telemetry, wired in ONLY
   here. If the file is absent, do NOT add the key (the strip stays hidden). To record the
   current session before reading, run `telemetry-extract.py` on the Claude Code transcript
   (see **Session telemetry** below). Aggregate across lines: sum `tokens_in`/`tokens_out`/
   `ms`, count lines as `sessions`, and MERGE `by_model` (sum tokens per model) so the strip
   can break the cost down per LLM.

5. **Inject into the template.** Read `mirador.template.html`, replace EVERYTHING between
   `/*MIRADOR_DATA_START*/` and `/*MIRADOR_DATA_END*/` (including the old `const DATA`)
   with:
   ```
   /*MIRADOR_DATA_START*/
   const DATA = <the dashboard JSON, with the `telemetry` key merged in if present>;
   /*MIRADOR_DATA_END*/
   ```
   Do not touch anything outside that region. Write the result as `mirador.html` at the
   project root.

6. **Open the file** (best-effort, does not fail if it can't — headless/CI):
   - Windows: `start "" mirador.html`
   - macOS: `open mirador.html`
   - Linux: `xdg-open mirador.html`

   ALWAYS print the absolute path of `mirador.html` (even if it can't be opened).

7. **Cleanup:** delete `.mirador-data.json` (temporary). Keep `.uscha/telemetry.jsonl` —
   it is the persistent sidecar, not a temp file.

## Session telemetry — sidecar contract

`.uscha/telemetry.jsonl` is an **append-only** file, one JSON object per session/run:

```jsonl
{"at": "2026-07-05T23:40:00Z", "model": "claude-opus-4-8", "tokens_in": 240000, "tokens_out": 41000, "ms": 4200000, "by_model": [{"model": "claude-opus-4-8", "tokens_in": 240000, "tokens_out": 41000}], "note": "mirador build"}
```

`effort` and `note` are **optional** and are NOT produced by `telemetry-extract.py` (a Claude
Code transcript carries no reliable effort label) — add them by hand if you want them; the
strip shows `—` when `effort` is absent. `by_model` is per-**tokens** (session-level `ms` only).

- **Who writes it:** the AGENT / operator, NEVER the engine (the engine is model-agnostic
  and cannot see tokens). Two honest sources:
  - **`telemetry-extract.py <transcript.jsonl>`** (shipped in this skill folder): parses a
    Claude Code session transcript — each assistant turn carries a `usage` block
    (`input_tokens` / `cache_*_input_tokens` / `output_tokens`) and a `model` — sums per
    model, computes wall time from the timestamps, and appends one line (with a `by_model`
    breakdown). Real, vendor-native data. Best-effort: unknown/older schemas degrade, never
    crash; no usage found → nothing appended.
  - **Manual append**: paste the session's numbers from Claude Code's own cost view.
- **Persistence:** the file itself IS the history (portable, diffable, greppable). Add it to
  the project's `.gitignore` — it is per-machine telemetry, not repo state. (A pure-client
  alternative is `localStorage` inside `mirador.html`, but the sidecar survives regeneration,
  so it is the default.)
- **Boundary (non-negotiable):** this is the ONLY place vendor-narrated numbers enter the
  mirador. They are shown, never gated, never fed into readiness — telemetry answers "what
  did it cost", the measured panels answer "is it correct". Keep them apart.

## Rules

- **Zero computation in the skill.** The numbers come from the ledger. If a panel looks
  empty, it's because the engine doesn't have that source yet (truth-pass), not because
  painting it was missed.
- **Read-only.** The skill does not run gates or modify the ledger. `dashboard` is
  read-only; the only one that writes (opt-in) is `readiness --record`, and that is the
  loop's decision, not this skill's.
- **`mirador.html` is a generated artifact** — suggest adding it to the project's
  `.gitignore`; it regenerates whenever you want.
