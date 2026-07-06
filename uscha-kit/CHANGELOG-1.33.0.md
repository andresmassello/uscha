# uscha-kit 1.33.0 — mirador session telemetry (tokens / time / model, per-model) (2026-07-05)

The mirador gains a **session-telemetry** strip: how many tokens, how much wall time, which
model(s), at what effort — with a **per-model breakdown** (so you can see if the expensive
model is being burned on cheap work). Smoke suite: 190/190.

**The engine is UNTOUCHED.** `qa_ledger.py` stays model-agnostic and never sees a token —
this is vendor telemetry (Claude Code), and it enters ONLY through the mirador skill (the
vendor adapter). No new subcommand; 25 stays 25.

## What ships (all in the `uscha-mirador` skill)

- **Segregated strip in `mirador.template.html`**: labeled *"Claude Code · session telemetry —
  vendor-reported, narrated not measured"*, dashed border, at the foot — **visually apart** from
  the measured panels. Shows totals (tokens in/out, wall time, effort, sessions) and, when more
  than one model was used, a **per-model row** (`opus-4-8  240k → 41k · 1.3h`).
- **`telemetry-extract.py`** (shipped in the skill folder, stdlib, standalone): parses a Claude
  Code session transcript (`*.jsonl`) — each assistant turn's `usage` (`input_tokens` +
  `cache_*` + `output_tokens`) and `model` — sums per model, computes wall time from the
  timestamps, and appends ONE line to the sidecar. Best-effort: bad/old schemas degrade, never
  crash; no usage → nothing appended.
- **Sidecar contract** `.uscha/telemetry.jsonl` (append-only, one JSON object per session, with a
  `by_model` breakdown). Portable, greppable, git-ignorable. Chosen over `localStorage` because a
  real inspectable artifact is coherent with the doctrine — you can audit where the number came
  from. The skill reads it, aggregates across lines (merging `by_model` per model), and merges a
  `telemetry` object into `DATA` before injection.

## The doctrinal boundary (non-negotiable)

Telemetry is **narrated by the vendor, not measured by the engine**. It is neither a fact-gate
nor a guess-advisor — so it is **shown, never gated, never fed into readiness**, and rendered in
a strip kept apart from the measured panels. Telemetry answers *"what did it cost"*; the measured
panels answer *"is it correct"*. Mixing them would dilute *measured beats narrated* — so they stay
apart. The mirador template also degrades: no sidecar → no strip (verified running the page's JS
under Node, with and without telemetry).

## Also

- The `mirador.template.html` UI is now in **English** (it was the last Spanish-only product HTML;
  the ES/EN decks stay bilingual by design).

## Smoke (T54)

A synthetic 2-model transcript → `telemetry-extract.py` → the sidecar line sums tokens
(input + cache) and output correctly, computes wall time from the timestamps, and carries a
2-entry `by_model` breakdown; a corrupt line is skipped, not fatal.
