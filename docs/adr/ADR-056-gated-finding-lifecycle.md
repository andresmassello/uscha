---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/.claude/skills/uscha-devloop/SKILL.md
  - uscha-kit/skills/uscha-devloop/SKILL.md
---
# ADR-056: A gated finding leaves the ledger only through MEASURED movement — and an unverified QA step never counts, never hides

## Status: Proposed — **R1 (an unverified step never counts, never hides) shipped in 2.10.0; R2 (the gated-finding debt) proposed for 2.11.0**

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

**R2 — gated debt, closed by measured movement** (new):
- `log-step` stamps each step with the tree stamp of ADR-055 plus `deferred_sha256` (the
  sha256 of `ISSUES-DEFERRED.md`, null when absent). Gate records (`log-gate`, `ingest-gate`)
  carry the same stamp.
- A step of tool T with `gated_reported = G > 0` opens a debt anchored at its **baseline**: the
  newest stamp recorded in that repo before the step (test-run, snapshot, step or gate record) —
  the tree the tool reviewed. The SKILL's order (fix → test → log-step) means the step's own
  stamp already contains that pass's fixes; the baseline is the "before".
- The debt closes when a later step of T reports `gated_reported == 0` and, between the baseline
  and that step, the source-relevant content changed (a fix) or `ISSUES-DEFERRED.md` changed (a
  deferral). A deferral is printed by `readiness` as "N gated findings deferred, not fixed".
- `--fixed` / `--deferred` never close a debt; `log-step` warns when `--fixed > 0` arrives with
  no measured movement since the baseline.
- An open debt blocks convergence in both modes, outside any window, named with tool, count and
  step number. A revert reads as no movement.
- No baseline → the debt closes only by movement after the gated step itself, said so.
- Equal `(tool, iteration)` re-logs stay allowed (ADR-051's remedy "re-log the step"); R2 judges
  them like any supersession.
- **Legacy**: steps without a stamp keep 2.9.0 semantics (deliberately not "closed by
  accounting": no narrated closing rule enters the engine); debts are computed for stamped gated
  steps only; `readiness` names "N pre-2.10 steps superseded without measured accounting".

## Alternatives

- **`fixed + deferred >= gated` closes the debt** (synthesis item 2). Cheapest, but it lets
  narration discharge a measured fact — the exact thing the two-tier contract (SKILL.md:24-26)
  forbids. Rejected. Legacy steps keep plain latest-wins, so no narrated closing rule enters
  the engine at all.
- **Refuse an equal `(tool, iteration)` re-log.** Breaks ADR-051's documented remedy for a step
  logged while its tool was MISSING. Rejected; R2 makes the re-log harmless instead.
- **"Source changed" between the gated step and the clean step** (not from the baseline). Blocks
  the normal flow: the fixes of the gated pass are already in the gated step's stamp, so a clean
  re-pass sees no change. Rejected (this is why the baseline exists).
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

## Acceptance (draft, not in ACCEPTANCE.md — rule 8)

- AC-GI-20 — the A-F2 reproduction is NOT converged and names the open debt.
- AC-GI-21 — the B-F1 reproduction is NOT converged; no fallback to an older verified step.
- AC-GI-22 — the B-F2 reproduction is NOT converged; an all-verified clean window still is.
- AC-GI-23 — a fix during the gated pass, then a clean pass → converged.
- AC-GI-24 — a deferral closes the debt and is printed as a deferral.
- AC-GI-25 — `--fixed` with no movement, or a revert, leaves the debt open (with the warning).
- AC-GI-26 — no baseline → closes only by movement after the gated step, named.
- AC-GI-27 — a v2.9.0 ledger loads and converges as before, legacy supersessions named.
