---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/skills/uscha-devloop/qa_ledger.py
---
# ADR-035: The facts `uscha top` renders as `—` in v0.1 are deferred on purpose — each needs new append-only engine persistence, and this ADR records the shape so the field is wired before it is re-claimed, never the other way round

## Status: Proposed

## Context
ADR-032 types five fields nullable because the ledger cannot honestly compute them today, and the
TUI renders each as `—`. This is the repo's under-claim-then-wire discipline (rule 2): the honest
`—` ships in v0.1; this ADR is where the *wiring* is designed so a later version can turn each `—`
into a real number without ever inventing one in between. Each item below is a distinct, deferred
piece of engine work with its own risk; none is folded silently into `uscha top`'s v0.1 scope.

The sixth item is different in kind: it is not a missing datum but a regex boundary that decides
whether `uscha top`'s **own** acceptance criteria can ever be JUnit-measured. It is recorded here as
the "position (b)" the audit (B.1, E.2) flagged, kept explicitly out of v0.1.

## Decision (all items: Proposed, deferred — not implemented in v0.1)

**1. Per-observation first-seen timestamp (unblocks `age_hours` and `medians.verdict_min`).**
CANDIDATE-DELTA.json carries no per-observation `at`, and the file is rewritten wholesale on every
`discover` run (L4389-4390), so `mtime` is not a valid first-seen proxy (audit A/`age_hours`, E.5).
Proposed shape: a **new ledger dict keyed by OBS id** (append-only, written once when an OBS id is
first observed, never reset on a no-op re-`discover`), e.g. `ledger["obs_first_seen"][obs_id] = at`.
`age_hours` then = `now − first_seen`; `medians.verdict_min` = median over OBS of `(curation[].at −
first_seen)`. Risk: the "still the same OBS vs. newly appeared" distinction must be exact (OBS ids
are content-addressed, ADR-013, so this is tractable) or ages reset spuriously.

**2. Obligation-count burn-up (unblocks `burnup.kind:"count"`).**
`readiness_history` (L8238) persists a blended **score**, not a count of `MEASURED_PASS` obligations
(audit A/`burnup_weeks`, E.6). Proposed: `readiness --record` additionally appends
`{at, measured_closed, total}` alongside `score`. `uscha top` would then emit `burnup.kind:"count"`;
until then it emits `kind:"score"` and the TUI labels it as score, never as closed-obligation count.

**3. `drift_pct` aggregate (unblocks `drift_pct`).**
`spec_drift` stores per-file verdicts (`CLEAN/SPEC_STALE/UNMAPPED/…`), no aggregate (audit
A/`drift_pct`, E.7). A percentage (e.g. `SPEC_STALE / mapped`) is a **new metric definition**, not an
extraction. If adopted it gets its own AC naming the formula; v0.1 emits `null`.

**4. Designed `spec_pin` (hardens `spec_pin`).**
v0.1 shows git `HEAD` labelled *not clean-room verified* (ADR-032). A designed pin — a recorded
commit that an obligation table is *guaranteed* to be measured against — is a real engine concept
worth its own decision (audit E.1). Deferred; v0.1's labelled-HEAD proxy is the honest interim.

**5. General-project TRACED (unblocks the `TRACED` rung and `obligations[].trace`).**
`_rt_ids_in`/`_RT_ID_RE` (L6238) already find `AC-\d+` references in source text, but are wired only
inside `bench-roundtrip`'s bench-fixture scan (audit A/`trace`, E.3). They are generic regex helpers;
the deferred work is calling them over a general project's git-tracked files (new wiring, not new
logic) so `state:"TRACED"` and a real `trace[]` become computable. Until then `counts.traced:0`,
`trace:[]`, and the rung renders UNMEASURED-class gray (ADR-032).

**6. `_AC_TAG` widening to the `AC-<FAMILY>-<n>` family — position (b), deferred (audit B.1, E.2).**
`_AC_ID`/`_AC_TAG` match only bare `AC-<digits>`; letter-infixed families (`AC-T-01`, and this repo's
own `AC-FP-01`, `AC-SD-01`, …) do **not** enter the measured pipeline. `uscha top`'s own ACs are
therefore numbered `AC-T-nn` and close through **bespoke smoke-suite assertions and golden frames**
(the kit's own precedent — ADR-034), exactly as every other family-prefixed criterion in this repo
already does. Widening `_AC_TAG` to `AC-[A-Z]+-\d+` so these families become JUnit-*measured* is a
real engine change carrying its own smoke obligation (repo rule 5) and its own blast radius (it would
retroactively change how the kit's own `AC-FP`/`AC-SD`/… criteria are counted). It is recorded here as
future work, deliberately **not** taken for v0.1 — v0.1 does not depend on it. **Curated
2026-08-17 (maintainer):** confirmed — `AC-T-nn` close via smoke assertions now; the widening ships as
its **own engine release** with its own ADR revision and curation (the retroactive re-count of the
kit's 23 family prefixes deserves its own turn), never coupled to any `uscha top` milestone.

## Consequences / Risks
+ Every `—` in v0.1 has a designed path to a real value; none will be back-filled by invention.
+ Items 1-3 share one root — the ledger persists too little history — and could ship together as one
  "richer append-only history" change if the maintainer prefers, each still with its own AC.
- Each item is real, non-trivial engine work with append-only and re-run-idempotence risk; bundling
  any of it into `uscha top` v0.1 would break the milestone gates (ADR-031/spec) and the truth-pass.
- Item 6, if ever taken, changes measured counts kit-wide; it must be its own change with its own
  golden anchoring of the before-state, not a rider on this feature.

## Verification
- [ ] nothing in this ADR is implemented in v0.1: every deferred field renders `-` or its gray class (AC-T-03, AC-T-05, AC-T-06, AC-T-10; INV-TOP-05)
- [ ] each item, when taken up, arrives with its own ADR revision and its own AC-T criteria before code (rule: under-claim, then wire, then re-claim)

## What this ADR does NOT decide
- Whether any of these is actually scheduled — this only records the honest shape so a later change
  can wire it. Each becomes its own accepted ADR + AC when taken.
- The v0.1 contract — ADR-032 (which stands on its own with every one of these as `null`/empty).
