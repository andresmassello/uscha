---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/.claude/skills/uscha-devloop/SKILL.md
  - uscha-kit/skills/uscha-devloop/SKILL.md
---
# ADR-056: A gated finding leaves the ledger only through MEASURED movement — and an unverified QA step never counts, never hides

## Status: Proposed — **R1 (an unverified step never counts, never hides) shipped in 2.10.0; R2' (witnessed reviews, anchored convergence, the debt on reviewed trees, redesigned after a model check) proposed for 2.11.0**

## Context

`_converged` (qa_ledger.py:3927-3990) builds the cycle from step records and sums
`gated_reported`. Three ways to make gated findings vanish were reproduced on v2.9.0:

- **A-F2.** A step with `--gated-reported 3`, then the SAME tool and iteration re-logged `0/0`
  with no file touched → pr-ready. In ordered mode the latest step per tool wins (:3945-3946);
  `_validate_iteration` (:2201-2212) allows an equal iteration; nothing compares trees.
- **B-F1.** Ordered mode keeps `latest_verified` beside `latest_seen` (:3944-3948) and builds the
  cycle from `latest_verified` (:3957). A newer `unverified` step (tool MISSING) with gated=3 is
  skipped and an older verified clean step stands in → CONVERGED.
- **B-F2.** Window mode (:3960-3963) takes `agent[-k:]` with no `unverified` filter. Three steps
  of a nonexistent tool converge, each printed "does not count toward convergence" (:2783-2784).

ADR-051:99-100 already says an unverified step "does **not** count toward `_converged`", and
the devloop SKILL (SKILL.md:24-26) already calls `log-step` counts "self-reported ... narration".
`README.md:131-132` says gated findings "are fixed, the rest go to ISSUES-DEFERRED.md".

## Decision

**R1 — unverified never counts and never hides** (plain fixes of ADR-051 as written):
- Ordered mode builds the cycle from `latest_seen`. A tool whose latest step is `unverified` is
  blocked with its own reason; there is no fallback to an older verified step.
- Window mode: any `unverified` step inside `agent[-k:]` blocks, and in both modes a tool whose
  newest step is `unverified` blocks.

**R2' — witnessed reviews, anchored convergence, a debt on reviewed trees** (redesigned for
2.11.0 after a model check; `docs/gate-integrity/SPEC-2.11.0.md` §3, `models/GatedDebt.tla`):
- **Witness.** `review-start --repo R --tool T --iteration N` records `RV-n` with the tree stamp
  (ADR-055) and the sha256 of `ISSUES-DEFERRED.md`. `log-step --review RV-n` carries that REVIEWED
  state; a step without a valid open review of the same repo/tool/iteration is **unwitnessed** and,
  like an unverified step (R1), never counts and never hides.
- **Anchor.** Convergence requires, per tool, that its latest witnessed step reviewed a tree with
  the same source-relevant content as the tree now (read-time, ADR-055's comparison).
- **Debt.** A witnessed gated step opens a debt on its reviewed state; a later witnessed clean
  step of the same tool on a different reviewed state (source moved, or `ISSUES-DEFERRED.md`
  moved -- printed as a deferral) closes it. `--fixed`/`--deferred` never close it.
- **Memory.** A witnessed clean step on exactly the reviewed state an earlier gated step of the
  same tool flagged contradicts the record and counts for nothing.
- **Legacy**: steps without a reviewed state keep 2.10 semantics until the tool's first witnessed
  step; `readiness` names them.

*History -- the R2 first proposed here (kept, because the reason it was replaced is the lesson).*
> **R2 — gated debt, closed by measured movement** (new):
> - `log-step` stamps each step with the tree stamp of ADR-055 plus `deferred_sha256` (the
>   sha256 of `ISSUES-DEFERRED.md`, null when absent). Gate records (`log-gate`, `ingest-gate`)
>   carry the same stamp.
> - A step of tool T with `gated_reported = G > 0` opens a debt anchored at its **baseline**: the
>   newest stamp recorded in that repo before the step (test-run, snapshot, step or gate record) —
>   the tree the tool reviewed. The SKILL's order (fix → test → log-step) means the step's own
>   stamp already contains that pass's fixes; the baseline is the "before".
> - The debt closes when a later step of T reports `gated_reported == 0` and, between the baseline
>   and that step, the source-relevant content changed (a fix) or `ISSUES-DEFERRED.md` changed (a
>   deferral). A deferral is printed by `readiness` as "N gated findings deferred, not fixed".
> - `--fixed` / `--deferred` never close a debt; `log-step` warns when `--fixed > 0` arrives with
>   no measured movement since the baseline.
> - An open debt blocks convergence in both modes, outside any window, named with tool, count and
>   step number. A revert reads as no movement.
> - No baseline → the debt closes only by movement after the gated step itself, said so.
> - Equal `(tool, iteration)` re-logs stay allowed (ADR-051's remedy "re-log the step"); R2 judges
>   them like any supersession.
> - **Legacy**: steps without a stamp keep 2.9.0 semantics (deliberately not "closed by
>   accounting": no narrated closing rule enters the engine); debts are computed for stamped gated
>   steps only; `readiness` names "N pre-2.10 steps superseded without measured accounting".

*Why it was replaced:* TLC broke `NoFlaggedBugShips` against that R2 with an honest agent in 7
steps (flag v0, fix, log, review v1 clean, log, revert to v0, re-test): nothing anchored the QA
verdict to the tree on disk (M1), and a step's stamp was the tree it was LOGGED at, not the tree
the tool REVIEWED, so the "baseline" heuristic counted a revert as movement (M2).

## Alternatives

- **`fixed + deferred >= gated` closes the debt** (synthesis item 2). Cheapest, but it lets
  narration discharge a measured fact — the exact thing the two-tier contract (SKILL.md:24-26)
  forbids. Rejected. Legacy steps keep plain latest-wins, so no narrated closing rule enters
  the engine at all.
- **Refuse an equal `(tool, iteration)` re-log.** Breaks ADR-051's documented remedy for a step
  logged while its tool was MISSING. Rejected; R2 makes the re-log harmless instead.
- **"Source changed" between the gated step and the clean step** (not from the baseline). Blocks
  the normal flow: the fixes of the gated pass are already in the gated step's stamp, so a clean
  re-pass sees no change. Rejected -- and the baseline heuristic that replaced it was itself
  broken by the model check; R2' removes the need for both by recording the REVIEWED tree.
- **Anchor alone, without Witness** (the cheapest fix of M1). TLC still breaks it with an honest
  agent in 8 steps: review v1, revert, log -- the clean verdict lands on v0. Rejected.
- **Witness + Anchor without Memory.** Holds for an honest agent; an agent that narrates a clean
  pass it never ran on flagged content still converges. Rejected while counts stay narration.
- **Match findings by fingerprint** across steps. Fingerprints are optional and agent-written.
  Rejected as the gate; they still feed `oscillation`.

## Consequences

+ A-F2, B-F1 and B-F2 fail closed; "padding the window" cannot hide a gated finding either.
+ Deferring a gated finding stays possible and becomes visible.
- Movement proves the code moved, not that it moved because of that finding; a trivial edit
  satisfies R2. The re-review of the moved code is what judges the fix — stated as a limit.
- `log-step` costs one `git status` + one batched `git hash-object` per call.

## Out of scope

Proving that a fix addresses a specific finding; static-gate records (`ingest-gate` already
diffs finding ids, :2787); `oscillation` semantics.

## Acceptance

R1 shipped in 2.10.0 as AC-GI-21 (B-F1) and AC-GI-22 (B-F2) in `ACCEPTANCE.md`. R2' (draft,
rule 8; ids chosen not to collide with the shipped AC-GI-20): AC-GI-50..58, one per row of
`docs/gate-integrity/FIXTURES.md` §2b -- the TLC paths M1, M2 and Lies and the A-F2 re-log as RED
cases with a shipped probe against v2.10.1; the vacuity, deferral, docs-only and legacy rows as
GREEN; a malformed `--review` as a named refusal.
