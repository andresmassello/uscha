---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
---
# ADR-023: Measuring `curation_closure` on bench compilations — the human verdict extended to machine-generated code, one observation at a time (bench-curation v0.1)

## Status: Accepted

## Context
ADR-022 shipped the per-compiler fidelity descriptor with `curation_closure: "UNMEASURED"` —
honest at the time: curation requires a human `preserve|fix|undefined` verdict per observation
(INV-CURATION-01) and no human had curated machine-generated fixture code. This ADR removes the
"had": it gives the human a way to curate bench compilations under the EXACT discipline the M1
gate already enforces, and lets the descriptor report a measured closure where verdicts exist.

What must NOT change:
- **One observation, one human verdict.** `cmd_curate` refuses batch input by design and this
  ADR inherits that refusal verbatim. No bulk path, no default verdict, no agent-authored verdict.
- **Append-only.** A superseding verdict appends; nothing is deleted.
- **UNMEASURED stays the truthful default.** A compilation with zero verdicts reports
  UNMEASURED exactly as today — never 0.0, which would fake a measured judgment of "nothing
  curated is nothing preserved".

What the curable set IS for a compilation: the observations the M1 static extractor already
produces for `static_surface` (deterministic AST, content-addressed ids). The human judges the
same facts the descriptor publishes — no second extraction, no drift between what is shown and
what is judged.

## Decision
- **New subcommand `bench-curate`** (48 → 49; a human-facing verdict recorder earns a
  subcommand — it is an instrument, not an enrichment):
  `bench-curate --bench <dir> --entry <archetype> --dir <c-model> --obs <id>
  --verdict preserve|fix|undefined [--note ...] [--human ...]`.
  It validates the observation id against the entry's compiled source (re-extracted at call
  time — a verdict must judge a real observation), then APPENDS
  `{obs_id, verdict, human, at, note, entry, dir}` to `BENCH-CURATION.json` at the bench root.
  Same refusals as `cmd_curate`: batch input exits 2; unknown obs exits 2; malformed store
  exits 2 (fail-closed, never degrade).
- **`bench-curate --list --entry <a> --dir <d>`** prints the curable observations (id +
  statement + current verdict, if any) so the human sees what awaits judgment. Read-only.
- **`bench --fidelity` reads `BENCH-CURATION.json` if present**: for each compilation,
  `curation_closure` becomes `round(judged/total, 3)` **only when at least one verdict exists
  for that compilation**; otherwise the literal UNMEASURED, unchanged. The raw JSON carries
  `{judged, total}` alongside the share. Verdict logic remains untouched — the descriptor stays
  advisory by construction (AC-FC-03 continues to hold).
- **The agent never writes a verdict.** The build stops after the tooling ships; the measured
  closure appears only after a human runs `bench-curate`. The changelog states which entries
  were human-curated and by whom.

## Reasons
- The UNMEASURED field was named as an absence, not a permanence. Measuring it via the existing
  discipline (not a parallel cheaper one) keeps INV-CURATION-01 intact where it bites hardest:
  code nobody authored is exactly the code most tempting to bulk-approve.
- Re-extracting at verdict time (instead of trusting a stored list) makes tampering visible:
  if the fixture changed since the descriptor was published, the old obs id no longer
  validates and the verdict is refused.

## Consequences
+ The last UNMEASURED dimension of the per-compiler descriptor becomes measurable, entry by
  entry, at the human's pace.
+ The bench gains an append-only human-judgment record, versioned like every other artifact.
- Partial coverage is the steady state (a human curates what a human has time for);
  the mixed report (some entries measured, some UNMEASURED) must render without implying the
  uncurated ones failed.

## Verification
- [ ] `bench-curate` records one verdict per call, appends (supersede keeps the earlier
  record), refuses batch input / unknown obs / malformed store with exit 2 (AC-BC-01)
- [ ] `bench --fidelity` reports measured `curation_closure` (judged/total) for compilations
  with ≥1 verdict and the literal UNMEASURED for the rest; verdicts never change (AC-BC-02)
- [ ] A fixture edit after curation invalidates the stale obs id: `bench-curate` refuses the
  verdict and `--list` shows the divergence (AC-BC-03)
