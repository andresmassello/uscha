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

`proposed-honest.cfg` (Witness + Anchor + Memory, honest agent): 761,424 distinct states, no
error -- Witness + Anchor alone already hold for an honest agent. `proposed-lying-agent.cfg`
(the agent may log counts no review produced): 1,607,868 distinct states, no error; Memory is
what closes it. `proposed-vacuity-control.cfg` checks `NeverFixedAndReady`, which MUST break: a
legitimate fix and a deferral still reach `pr-ready`, so the green above is not vacuous.

Cost to decide: with Memory, a tool's false positive on unchanged code stays blocked until it is
deferred -- which is what the method already asks.

## Reproduce

```sh
curl -sSLo tla2tools.jar https://github.com/tlaplus/tlaplus/releases/download/v1.7.4/tla2tools.jar
# sha256 936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88
java -cp tla2tools.jar tlc2.TLC -config as-specified.cfg GatedDebt.tla
```

The chart comes from the `statechart` skill of `cursor/plugins` (pstack, MIT), run with
`TLA2TOOLS=<jar> JAVA=java statechart GatedDebt.tla --config as-specified.cfg --view view.mjs`.
