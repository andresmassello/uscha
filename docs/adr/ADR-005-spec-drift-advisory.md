# ADR-005: Spec drift is detected mechanically and reported as advisory — never gated

## Status: Accepted

## Context
The ledger detects stale *evidence* (a report older than the code it certifies) but not stale
*specs*: a `SPEC.md` or ADR older than the code it governs rots silently. This is the #1
category-level criticism of spec-driven development — the spec maintenance tax — and uscha had
no mechanical answer.

Options considered:
- **A) Gate on drift** (stale spec blocks readiness). Rejected: whether a spec still "covers"
  newer code is a *relevance judgment*. Commit dates are a heuristic proxy — a guess. Per the
  core principle, facts block and guesses advise; gating on a guess would be the method
  violating itself.
- **B) Advisory detection from commit dates, with explicit mapping.** Chosen.
- **C) Semantic drift analysis** (diff the code against the spec's claims). Rejected for now:
  requires an LLM judgment inside the engine, which the engine constitutionally does not do.

## Decision
New subcommand `qa_ledger.py spec-drift`:

- **Mapping is explicit**: a `governs:` list of globs in the frontmatter of `SPEC.md` and each
  `docs/adr/*.md`. No frontmatter → the file reports **`UNMAPPED`** — which, per house style,
  is *not* the same as "no drift". Absence of a mapping is absence of measurement.
- **Signal**: last git commit date of the spec vs. the newest commit date of any governed
  file. Governed code newer than its spec by more than `spec_drift.max_lag_days` (config,
  default **30**) → **`SPEC_STALE`**, listing the files newer than the spec.
- A spec not yet committed reports **`UNTRACKED`** (no date to compare — stated, not guessed).
- The run is recorded in the ledger (`spec_drift`, latest state) so the mirador can surface an
  advisory row. **No readiness impact. No gate. Exit code 0 always.** A stale spec is a prompt
  for a human conversation, not a blocked pipeline.

## Reasons
- Commit-date lag is cheap, deterministic, stdlib-and-git only — and honest about being a
  proxy: it detects *"nobody touched the spec while its code moved"*, not *"the spec is wrong"*.
- `UNMAPPED` as a distinct verdict makes the coverage of the mapping itself visible — an
  unmapped spec cannot silently pass as fresh.

## Consequences
+ The spec-maintenance tax becomes visible on the dashboard instead of accruing silently.
+ Zero new ceremony for projects that ignore it: no frontmatter → UNMAPPED rows, nothing gates.
- Someone editing a spec merely to silence the advisory refreshes the date without improving
  the content. Accepted: the advisory prompts a human look; it cannot verify substance.
- Globs must be maintained as the tree moves. UNMAPPED surfaces the decay.

## Implementation Plan
- Affected paths: `qa_ledger.py` (subcommand + dashboard passthrough), example
  `uscha.config.json` (`spec_drift.max_lag_days`), mirador SKILL.md contract bullet, kit README.
- Patterns: glob→regex via the existing `_fp_glob_re`; dates via `git log -1 --format=%ct`.
- Tests: smoke T114 → AC-SD-01..04 fed into the acceptance emission per-criterion (the T113
  sidecar pattern).

## Verification
- [ ] governed file newer than spec beyond lag → `SPEC_STALE` with the newer files listed (AC-SD-01)
- [ ] spec newer than all governed files → no advisory (AC-SD-02)
- [ ] spec without `governs:` frontmatter → `UNMAPPED`, distinct from clean (AC-SD-03)
- [ ] advisory present → readiness score numerically unchanged (AC-SD-04)
