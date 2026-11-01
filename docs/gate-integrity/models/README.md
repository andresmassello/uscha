# Model check of ADR-056 R2 (the gated-finding debt) -- input for 2.11.0

The design that came out of it is `../SPEC-2.11.0.md` §3 (R2'); its RED cases are
`../FIXTURES.md` §2b.

A TLA+ model of the design in `../SPEC.md` §3.3, checked with TLC BEFORE 2.11.0 writes the
code. It is a design artifact: nothing here ships, and nothing here is a claim about the engine
(repo rule 2). Each path TLC finds becomes a RED case in the suite once the code exists, and is
replayed against the real engine there -- a path the code does not reproduce means the model is
wrong until shown otherwise.

## Rule

`NoFlaggedBugShips`: `pr-ready` never holds on a code version the LEDGER knows a QA tool flagged
(a `log-step` with gated findings for that tree), unless the finding was deferred in
`ISSUES-DEFERRED.md`.

## Findings (TLC v1.7.4, bounds: 3 code versions, one QA tool, one repo, at most 5 records)

1. **As specified (`as-specified.cfg`) the rule breaks in 7 steps, with an honest agent**:
   test-run measures v0; the tool flags v0; the agent fixes (v1) and logs the finding; the tool
   reviews v1 clean and the agent logs it; the agent reverts to v0. The test-run measured v0, so
   tests read current again, and the latest QA step is clean: `pr-ready` on the flagged code.
   This gap is not new: QA steps are not anchored to the tree on disk in 2.10.0 either (2.10.0
   re-derives the freshness of TESTS at read time, not of QA reviews). See
   `chart-as-specified.mmd`.
2. **`log-step` stamps the tree when the step is LOGGED, not the tree the tool REVIEWED**: review
   v1, revert, then log, and the clean verdict reads as a verdict on v0. With no baseline before
   a gated step the SPEC uses the step's own (already fixed) stamp as "before", so a revert counts
   as movement and closes the debt.

## The design TLC does not break (same bounds)

- **Witness**: the engine stamps the tree when a review STARTS (the `test-run` principle of
  ADR-055 applied to QA reviews); a step carries the reviewed tree, and a step with no recorded
  start is not evidence.
- **Anchor**: convergence requires the latest QA step to have reviewed the tree on disk now.
- **Memory**: a clean step on content the ledger already saw flagged contradicts the record and
  counts for nothing.

`proposed-honest.cfg` (Witness + Anchor + Memory, honest agent): 926,106 distinct states, no
error -- Witness + Anchor alone already hold for an honest agent. `proposed-lying-agent.cfg`
(the agent may log counts no review produced): 1,914,237 distinct states, no error; Memory is
what closes it. (The first run read 761,424 and 1,607,868; the counts grew when the model gained
the `flagged` ground truth and the deferral state a review starts on. Same verdicts.) `proposed-vacuity-control.cfg` checks `NeverFixedAndReady`, which MUST break: a
legitimate fix and a deferral still reach `pr-ready`, so the green above is not vacuous.

Cost to decide: with Memory, a tool's false positive on unchanged code stays blocked until it is
deferred -- which is what the method already asks.

## The design as shipped in 2.11.0 (`V211 = TRUE`)

A fresh review of the 2.11.0 code found two moves the first model did not allow: the agent may
**remove** a deferral it added (`Undefer`), and may log a **gated** step with no review
(`LogUnwitnessedGated`; the engine opens a debt on the state it was logged at). Extended with both,
TLC broke the rule twice more -- each fixed in the engine and replayed as a RED case in T174:

3. **Removing a deferral read as deferring** (`AC-GI-64`): defer, log a gated step, remove the
   deferral, review the same source clean. The two reviewed states differ only in
   `ISSUES-DEFERRED.md`, and "the deferral file changed" closed the debt. Fix: a deferral closes a
   debt only when the clean review SAW a deferral file.
4. **A stale review closes the debt, then removing the deferral makes the clean verdict "new"**
   (`AC-GI-65`, 10 steps): a review of v1 starts, the source returns to v0, a gated step is logged
   on v0, the v1 review is logged clean (different source: the debt closes), the deferral is
   removed, and a clean verdict on v0 no longer equals the gated one (deferral state differs), so
   Memory let it through. Fix: with no deferral file on disk a clean verdict on a flagged source
   contradicts the record whatever deferral state the gated verdict saw.

`shipped-2.11.0.cfg` (everything TRUE, lying agent): **46,976,202 distinct states, no error**.
`shipped-2.11.0-vacuity.cfg` checks `NeverFixedAndReady`, which breaks: a deferral still reaches
`pr-ready`. Limit the binary model cannot express: in the engine a deferral is the sha256 of a
file, so editing `ISSUES-DEFERRED.md` (present, different) to drop one entry while keeping others
still reads as a deferral -- the engine cannot tell which finding a line defers.

## The manifest (ADR-059, 2.13.0)

`models.json` is the first manifest under ADR-059: it declares, per `.cfg`, the verdict TLC must
give, a tier, and the RED case that replays each counterexample.

- **`ci` tier** (MaxLog=4, run by the CI `models` job on every push, blocking the publish):
  `ci-shipped` (no error), `ci-vacuity` (MUST break), and four teeth configs that MUST break --
  `ci-as-specified` (the first design: AC-GI-50, -51), `ci-lies-without-memory` (AC-GI-52),
  `ci-without-both-fixes` (AC-GI-64) and `ci-without-memory-fix` (AC-GI-65). Measured 1-42 s each
  locally (the 42 s with the suite running alongside); the whole tier took 23 s on the CI runner
  (2026-11-01).
- **`deep` tier** (MaxLog=5, by hand): the original configs, with the date, the distinct states and
  the sha256 of `GatedDebt.tla` AND the `.cfg` they were measured against; a newer module or
  config makes `tools/model-check.py check` print an advisory. The hash is written by whoever ran
  it -- it says what a result was measured against, not that it was.

`DeferFix` and `MemoryFix` name the two fixes TLC forced in 2.11.0. Building the teeth configs found
that reverting `DeferFix` ALONE is not a violation at MaxLog=4: Memory already refuses that path. The
engine keeps both rules; `ci-without-both-fixes` is the teeth config for AC-GI-64 for that reason.

```sh
python tools/model-check.py check                                   # no Java
python tools/model-check.py run --tier ci --jar tla2tools.jar       # TLC, pinned sha256
python tools/model-check.py run --tier deep --jar tla2tools.jar     # by hand, ~9 min
```

## Reproduce

```sh
curl -sSLo tla2tools.jar https://github.com/tlaplus/tlaplus/releases/download/v1.7.4/tla2tools.jar
# sha256 936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88
java -cp tla2tools.jar tlc2.TLC -config as-specified.cfg GatedDebt.tla
java -cp tla2tools.jar tlc2.TLC -config shipped-2.11.0.cfg -workers 2 GatedDebt.tla   # ~7 min
```

The chart comes from the `statechart` skill of `cursor/plugins` (pstack, MIT), run with
`TLA2TOOLS=<jar> JAVA=java statechart GatedDebt.tla --config as-specified.cfg --view view.mjs`.
