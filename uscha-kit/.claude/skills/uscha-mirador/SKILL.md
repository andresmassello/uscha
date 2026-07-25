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

## Orientation markers (non-negotiable)

The operator must never have to ask "where am I?" or "what happens now?".

This skill is a **one-shot read-only readout**: its block IS the answer. It therefore does NOT
take the conversational close block — that would be exactly the padding this skill forbids.
It carries the two minimal markers instead.

**Open with a breadcrumb:**

`[uscha · mirador · step <n> → <target>]`

**End with the two routing lines, and nothing else:**

```
Next: <the next action, derived from what this readout just showed>
Run:  <the exact command or skill to invoke>
```

`Next` is **derived** from the state you just read — never copied from a fixed route,
including any `Flow:` line in this file. If nothing is actionable, say that plainly rather
than inventing a step. Keep the CONTENT in the conversation's language and the labels
(`Next`, `Run`) verbatim — the smoke suite checks for them.

## Contract

- **Source of truth:** `qa_ledger.py dashboard --json` — aggregates ONLY state the
  ledger already has (readiness, subscores, phases, acceptance, adrs, inv, layers, loops,
  snapshots, evidence). A field with no source comes out `null`/`[]`; the template
  degrades. **A datum is never invented.**
- **Template:** `mirador.template.html` (in this folder). The data block lives between
  `/*MIRADOR_DATA_START*/` and `/*MIRADOR_DATA_END*/`; the sample `const DATA` it ships
  with is the **offline fallback**. The skill replaces ONLY that region; it does not
  touch the rest of the HTML.
- **Project name (top):** the mirador shows the project name prominently at the top, from
  `config.project` in `uscha.config.json` (set it in `uscha-discovery`); if unset, it falls
  back to the joined repo names (truth-pass — no invented name).
- **Execution policy (bird's-eye):** `dashboard --json` also exposes
  `execution_policy` plus `phase.execution` for each trail node. This is routing metadata
  from `config.defaults.execution_policy` (`method`, `tier`, `model`, `effort`,
  `uncorrelated`), not a score. The template renders it as a separate panel so the human
  sees which methodology/model/effort is selected per phase without mixing it into
  readiness.
- **Discovery intake:** `dashboard --json` carries `discovery_intake` from readiness:
  open `production_findings`, `spec_doubts`, and `spec_change_requests`. The current template keeps the top-level
  verdict honest through readiness/caps; future panels may render the intake directly.
- **ADR experiments:** ADR rows may carry `adr_status: "experiment"`, `review_by`,
  `review_trigger`, `experiment_valid`, `experiment_missing`, and `expired`; top-level
  `adr_experiments` summarizes open/malformed/expired experiments. This is advisory
  visibility for measured hypotheses, not readiness scoring.
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
   - `~/plugins/uscha/skills/uscha-devloop/qa_ledger.py` (Codex plugin install)
   - `~/.codex/skills/uscha-devloop/qa_ledger.py` (Codex raw-skills install)
   - `~/.claude/skills/uscha-devloop/qa_ledger.py` (Claude global install)

2. **Resolve the ledger.** `QA-LEDGER.json` in the cwd (or the `--ledger` the user
   points to). If it does not exist, warn: you have to run `uscha-devloop` (or
   `qa_ledger.py init`) first — with no ledger there is no state to look at.

   (`<skill-dir>` below = this folder: `.claude/skills/uscha-mirador/` per-project, or `~/plugins/uscha/skills/uscha-mirador/` / `~/.codex/skills/uscha-mirador/` / `~/.claude/skills/uscha-mirador/` global.)

3. **(Optional) record this session's telemetry.** For the vendor-telemetry strip, append
   the current Claude Code session to the sidecar:
   ```bash
   python3 <skill-dir>/telemetry-extract.py <path-to-CC-transcript.jsonl>
   ```
   It **upserts by session** (safe to re-run — a watch loop won't inflate the totals). Skip
   this for a pure measured view.

4. **Render `mirador.html`** with the standalone renderer — it runs `dashboard --json`,
   merges the sidecar telemetry if present, injects `const DATA`, writes the file, prints its
   absolute path (`OPEN IT: ...`), and opens it in the default browser **the first time it
   creates the file** (see step 5 — a re-render updates the open tab instead). From the project root,
   with no long paths — `--engine` and `--template` default to the renderer's sibling skill
   files (kit 1.41.2):
   ```bash
   python3 <skill-dir>/mirador-render.py --ledger QA-LEDGER.json
   ```
   The engine stays model-agnostic — telemetry is merged by the renderer (the adapter), NOT
   by `dashboard`. If the ledger is missing, warn and stop (run `uscha-devloop` first). The
   time-lapse feeds from `qa_ledger.py readiness --record` — since kit 1.47.0 the dev-loop
   records at every pass close, so history accumulates without extra ceremony.

5. **Where to look:** the renderer opens `mirador.html` **once — only the first time it is
   created** — and always prints its absolute path on the `OPEN IT:` line; surface that path to
   the operator. Re-rendering (this skill invoked again on a later pass, or the watch loop)
   rewrites the SAME file, and the page's built-in auto-refresh reloads the already-open tab in
   place, so a re-render never spawns a new browser tab. On a fresh session the file is already
   on disk, so nothing pops — open the printed path once, or pass `--open` (`uscha mirador
   --open`) to force a reopen when you closed the tab. `--no-open` suppresses opening
   everywhere and wins over `--open` (headless/CI, or the watch loop, which passes it);
   `--refresh 0` writes a frozen snapshot with no auto-reload.

## For a human at a terminal: `uscha mirador`

The one-liner above is what THIS skill runs. A human who just wants the dashboard — without a
Claude Code session — has a zero-friction verb instead (kit 1.43.0): from the project root,

```bash
uscha mirador            # render + open, defaults to the QA-LEDGER.json convention
uscha mirador --watch    # live second-screen view (auto-refresh, one self-reloading tab)
npx @andresmassello/uscha mirador   # same, no install
```

No python, no paths: the verb resolves the engine, template and ledger on its own.

## Live second-screen view

For a mirador that updates while you keep coding in the terminal, run the watch loop in a
spare terminal and open `mirador.html` on a second monitor (or just use `uscha mirador --watch`):

```bash
# Windows:  powershell -NoProfile -File <skill-dir>\mirador-watch.ps1 -Interval 30
# Unix:     bash <skill-dir>/mirador-watch.sh 30
```

It re-renders `mirador.html` every N seconds (default 30) from the current ledger, rendered
with a matching `<meta http-equiv="refresh">` so the open page reloads on its own — **no
server**. It is only as live as the **ledger**: the picture changes at the dev-loop's
measured checkpoints (snapshots, gates, `readiness --record`), not per keystroke. Honest by
design — it shows measured state, which changes at measured moments.

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
