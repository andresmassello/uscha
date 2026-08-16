---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/tests/fixtures/diamond-bench/*/r2/
---
# ADR-027: Intra-model variance — the same model, the same package, a second time; the bench's inter-compiler numbers get their noise floor (bench-r2 v0.1)

## Status: Accepted

## Context
Every variance number the program has published so far is **inter**-compiler: three different
models, one run each. That number is only interpretable against a floor nobody has measured:
how different are two runs of the SAME model on the SAME canonical package? If opus-vs-opus
differs as much as opus-vs-haiku, "inter-compiler variance" is mostly sampling noise and the
controlled-language deltas (REDUCED −61%, IMPROVED +0.17) sit on sand. If intra-model variance
is much lower, the inter-compiler number measures something real about the models. The bench
has 10 archetypes × 3 models = 30 compilations, and only bootstrap-golden-hook ever got a
second run (`c-opus-r2`, `c-sonnet-r2`, M4).

A design constraint discovered while planning: `bench` treats EVERY `c-*` directory under an
entry as a compilation. Dropping `c-opus-r2` next to `c-opus` would silently change every
existing verdict (n 3→6, min-rate, PARTIAL floor). The second run must live beside the entry,
not inside its compilation set.

## Decision
- **Fixture layout**: each entry gains an optional `r2/` directory holding `c-opus/`,
  `c-sonnet/`, `c-haiku/` — the SAME model, the SAME canonical package, the SAME prompt
  scaffold (`PROMPT-TEMPLATE.md`), a fresh blind dispatch in a later session. `r2/` carries no
  IR or oracle of its own: it is measured against the entry's pinned IR and withheld oracle.
  `bench` ignores `r2/` (it only scans top-level `c-*`) — the existing verdicts are untouched
  by construction, asserted by the suite.
- **New subcommand `bench-r2`** (49 → 50): for every entry with an `r2/`, per model, computes
  the **intra-model distance** between run 1 and run 2 with the SAME structural-distance
  function the bench uses between compilers (LOC / AST-node / import-Jaccard mean —
  `_lang_arm_metrics`'s pairwise term, factored out and reused unchanged), plus each run's
  oracle pass-rate and whether the two runs agree on every oracle case (`behaviour_stable`).
  Per entry it reports `intra_mean` (mean of the per-model distances) beside the entry's
  existing `inter` (the bench's inter-compiler mean over run 1), and the ratio
  `intra_over_inter`. Aggregate: mean ratio across entries, and the count of entries where
  intra ≥ inter (the "noise dominates" cases). Writes `DIAMOND-BENCH-R2.md`; `--json` raw.
- **Verdict per entry, computed**: `SIGNAL` when intra_over_inter < 0.5 (inter-compiler
  variance is at least twice the noise floor), `NOISY` when 0.5 ≤ ratio < 1.0, `NOISE` when
  ratio ≥ 1.0 (same-model reruns differ as much as different models — that entry's
  inter-compiler number carries no information). Aggregate verdict is the majority, stated with
  the counts; ties resolve toward the more cautious reading (NOISE > NOISY > SIGNAL).
  **Precision, stated (1.84.0 review):** the ratio is printed to 2 decimals. The AST-node
  count in `_struct_distance` differs between Python versions (`ast.walk` on 3.8 vs 3.13),
  so a ratio can move by up to ~0.26 across interpreters with no code or model changing
  (measured: scheduler 1.52 on 3.8 vs 1.79 on 3.13). Classes were stable across both on
  this bench; ratios are not point-precise, and an entry within ~0.25 of a threshold is
  borderline. The instrument says so in its own footer. Advisory: no bench verdict changes; the number is a qualifier on the program's
  variance claims, published as such.
- **Blind protocol inherited verbatim**: subagents see only the canonical package; Write-first;
  `unresolved_intent` verbatim from returns; artifacts never edited; the r2 dispatch uses the
  committed scaffold. Compilations validate against the entry IR (`compile-validate`) like any.
- **Scope of this release**: r2 for ALL 10 archetypes × 3 models = 30 fresh blind compilations
  (the bootstrap-golden-hook r2 pair stays where it is; the bench's guard entry gets its own).

## Reasons
- A variance number without its noise floor is a narrated number wearing a decimal point. The
  program has published five controlled-language verdicts on inter-compiler variance; the
  floor is owed before any further variance claim.
- Reusing the exact distance function keeps intra and inter commensurable — the ratio means
  something only if both sides are the same measurement.

## Consequences
+ Every variance-based claim in the program gets a per-entry qualifier (SIGNAL / NOISY /
  NOISE); the controlled-language rows can cite it.
+ 30 more blind compilations become permanent fixtures.
- Thirty dispatches is real cost; the result may say NOISE for some entries — which is the
  point, and it ships either way.

## Verification
- [ ] `bench` output (verdicts, table, JSON) is byte-identical with and without `r2/`
  directories present — r2 never enters the bench's compilation set (AC-R2-01)
- [ ] `bench-r2` reports, per entry with r2, one intra distance per model computed with the
  same function as the bench's inter distance, `behaviour_stable`, `intra_mean`, `inter`,
  `intra_over_inter` and a computed SIGNAL/NOISY/NOISE; entries without r2 report absent, never
  0 (AC-R2-02)
- [ ] All 30 r2 compilations validate against their entry's IR; `unresolved_intent` verbatim
  and non-empty; the aggregate verdict and per-entry classes are pinned over the committed
  fixtures, interpreter-stable (AC-R2-03)
