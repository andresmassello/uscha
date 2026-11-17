# Model check of ADR-063 (parallel slices) -- input for 2.17.0

A TLA+ model of `../../adr/ADR-063-parallel-slices.md`, written BEFORE 2.17.0 writes the code
(repo rule 12). It is a design artifact: nothing here ships, and nothing here is a claim about the
engine (repo rule 2). **A green config proves no violation OF THE MODEL at its bounds -- not that
the engine is correct.** Each counterexample below is meant to become a RED case (AC-SL-nn) in the
engine's suite, replayed against the real engine.

The model was first written without a shell. The first TLC run (2026-11-17) confirmed the six
rules and broke the open question it was probing: a slice merged into the change branch and then
dropped ships a diff that left its declared paths. The owner amended the ADR the same day (D1-D4,
"Amended after the model" in the ADR). This README describes the AMENDED module; every number in
it is measured.

## The shape

- One change, one repo, three declared slices and three files:
  - `s1` declares `{f1}`;
  - `s2` declares `{f2}` and is `after: s1` (a content dependency between disjoint files);
  - `s3` declares `{f1}`, overlapping `s1`, with no `after` edge (so `after` cannot mask the
    disjointness rule);
  - `lock` is declared by no slice: a lockfile or generated file that a merge may change.
- Content is an opaque version. 0 is the base; each slice writes its own value (`s1` -> 1,
  `s2` -> 2, `s3` -> 3); a merge that changes a file beyond the slice's diff writes 4 (a regenerated
  lockfile, a conflict resolved by hand); a fix made directly on the change branch writes 5.
- A slice starts by forking a worktree from the change branch. Its **diff** is what its branch
  changed since that fork (D4). Its agent may write ANY file, inside or outside the declared paths.
  Because a slice writes only its own value, the branch is encoded as the SET of files it wrote
  (`ed`); the fork snapshot is never read, so it is not stored. That is an exact re-encoding of the
  first module, not an abstraction.
- **Review**: a clean pass over the slice's diff stamps those files in the slice's ledger, refused
  unless every `after` is integrated (`AfterCheck`, decision 4) and every `after`'s merge was in the
  change branch when the slice forked (`AncestryCheck`, D2). The slice ledger has **converged** when
  every file of its diff is stamped. A clean pass over the integration's diff stamps the main ledger.
- **Merge**: the agent merges the slice branch into the change branch. Files of the slice's diff take
  the slice's content; the merge may also change one more file (any file) to 4.
- **slice-integrate** refuses when the slice's ledger has not converged, when its merge is not in the
  change branch (fixed ON), and when its diff leaves its declared paths (`PathLeakCheck`). It then
  carries the slice's stamps into the main ledger (`HashCarry`: only where the integration's content
  equals the reviewed one).
- **slice-drop** is a human act, available on a planned or running slice -- and, with `DropGuard`
  (D1), not on one whose merge is in the change branch.
- **pr-ready** (the engine's view): a non-empty integration diff, every declared slice integrated or
  dropped (`WholeDelivery`), every file of the integration diff stamped at its current content
  (review tiers on), and a test-run that saw the change branch as it is now (`IntegrationSuite`;
  off: the slice runs of the integrated slices count). The integration run is a flag that every
  change to the branch resets, so a branch that returns to an earlier tree reads untested -- stricter
  than the engine's tree compare. No verdict here depends on it: a test-run is enabled whenever the
  flag is off, so every state a tree compare would let pass the gate is reached one step later with
  every other variable equal; with `IntegrationSuite` on the gate itself requires the flag, and with
  it off the tooth breaks on a path with no such return.
- **The agent obeys slice-plan's disjointness and `max_parallel`, not its `after` column.** The ADR
  has no refusal for an overlap (decision 3 is a read-only readout), so the model has to assume it;
  an `after` IS refused by the engine (decision 4, D2), so the model does not assume it: the agent
  may fork `s2` at any time, and only the review refusals stand in its way.
- Bounds, `ci`: `MaxEdits = 3` (slice writes plus change-branch fixes), `MaxSliceEdits = 1` (one
  file per slice diff), `MaxPar = 2`. Every other action is bounded by its guard: a stamp or a run
  fires only when it would change something; a slice starts, merges and integrates once.

## Rules (the safety properties)

| # | property | invariant | source |
|---|---|---|---|
| 1 | never pr-ready with a declared slice neither integrated nor dropped | `WholeDelivered` | decision 7 |
| 2 | never two overlapping slices running at once | `NoOverlapRunning` | decision 3 |
| 3 | never a slice reviewed before every `after` is integrated | `AfterRespected` | decision 4 |
| 4 | never a gate pass with an integration file whose content no real review saw | `ReviewedContent` | decision 6 |
| 5 | never a gate pass without a test-run on the integration commit | `IntegrationTested` | decision 6 |
| 6 | never an integrated slice whose diff left its declared paths | `NoLeakIntegrated` | decision 4 |
| 7 | never a slice reviewed whose fork lacks an `after` slice's merge | `BuiltOnAfter` | D2 |
| 8 | never a gate pass shipping a merged slice's diff that left its declared paths | `NoLeakShips` | D1 |

Plus `CapRespected` (`max_parallel`). Properties 4 and 5 are stated over GROUND TRUTH the engine
does not read: `seen` (the contents a real review saw, per file) and the integration run. The gate
reads the stamps (`irev`) and, with `IntegrationSuite` off, the slice runs. That is what lets
`HashCarry` and `IntegrationSuite` off break them. Property 3 changed meaning with the amendment:
it was "never STARTED before", which only restated the obedient agent's guard; it is now the
engine's refusal, "never reviewed before". Property 7 restates `AncestryCheck`'s guard, the same
way 2 and 6 restate theirs; its tooth shows that the `integrated` check alone does not imply it.

## Configs and measurements

TLC v1.7.4 (`TLC2 Version 2.19 of 08 August 2024`), 16-core Windows box, 2026-11-17, final module.
Times are wall time including JVM start. No-error configs ran with `-workers auto` (what
`model-check.py run` passes); counterexample configs with `-workers 1`, so the printed trace is the
shortest one. The two large `ci` configs were also timed with `-workers 2`, a stand-in for a
2-core CI runner: `ci-shipped` 18.3 s, `ci-reachable` 16.2 s.

| config | in manifest | expect | distinct states | seconds | result |
|---|---|---|---|---|---|
| `ci-shipped.cfg` (everything on, the 8 rules + cap) | yes, `ci` | no-error | 812,126 | 8.0 | no error |
| `ci-vacuity.cfg` (`HashCarry = FALSE`) | yes, `ci`, vacuity | violated: ReviewedContent | 72,769 | 2.7 | violated, 9 states |
| `ci-reachable.cfg` (everything on) | yes, `ci`, vacuity | violated: NeverDeliveredThroughMerge | 811,430 | 20.5 (auto: 7.0) | violated, 18 states |
| `ci-all-dropped.cfg` (everything on, D3) | yes, `ci`, vacuity | violated: NeverAllDroppedReady | 11,882 | 1.5 | violated, 7 states |
| `deep-shipped-maxslice3.cfg` (`MaxSliceEdits = 3`: the first module's bound) | yes, `deep` | no-error | 1,025,388 | 8.8 | no error (2 workers: 33.2 s) |
| `deep-shipped-maxedits4.cfg` (`MaxEdits = 4`, `MaxSliceEdits = 4`) | yes, `deep` | no-error | 6,892,376 | 43.9 | no error |
| `tooth-without-hash-carry.cfg` | no (needs AC-SL-09) | violated: ReviewedContent | 72,769 | 2.9 | violated, 9 states |
| `tooth-without-disjoint.cfg` | no (needs AC-SL-04) | violated: NoOverlapRunning | 15 | 1.1 | violated, 3 states |
| `tooth-without-after.cfg` | no (needs AC-SL-05) | violated: AfterRespected | 9,135 | 1.5 | violated, 7 states |
| `tooth-without-path-leak.cfg` | no (needs AC-SL-06) | violated: NoLeakIntegrated | 2,523 | 1.4 | violated, 6 states |
| `tooth-without-integration-suite.cfg` | no (needs AC-SL-10) | violated: IntegrationTested | 122,203 | 3.7 | violated, 9 states |
| `tooth-without-whole-delivery.cfg` | no (needs AC-SL-11) | violated: WholeDelivered | 8,909 | 1.7 | violated, 7 states |
| `tooth-without-drop-guard.cfg` (was `probe-drop-after-merge`) | no (needs AC-SL-15) | violated: NoLeakShips | 97,510 | 2.8 | violated, 9 states |
| `tooth-without-ancestry.cfg` | no (needs AC-SL-16) | violated: BuiltOnAfter | 59,836 | 2.4 | violated, 9 states |
| `ci-shipped` with `DisjointCheck = FALSE`, checking 4 + 5 (not kept) | -- | -- | 1,094,706 | 8.4 | no error |
| `ci-shipped` with `AfterCheck = FALSE`, checking 4 + 5 (not kept) | -- | -- | 918,272 | 7.7 | no error |
| `ci-shipped` with `AncestryCheck = FALSE`, checking 4 + 5 (not kept) | -- | -- | 870,918 | 6.1 | no error |
| `ci-shipped` with `PathLeakCheck = FALSE`, checking 4 + 5 (not kept) | -- | -- | 1,509,606 | 9.8 | no error |
| `ci-shipped` with `DropGuard = FALSE`, checking 4 + 5 (not kept) | -- | -- | 4,673,100 | 27.0 | no error |
| first module, `ci-shipped` at `MaxEdits = 3` (before the amendment, not kept) | -- | -- | 5,314,872 | 53 | no error |
| amended module before the re-encodings, `MaxSliceEdits = 1` (not kept) | -- | -- | 9,735,002 | 75 | no error |
| first module, `probe-drop-after-merge` (before the amendment, not kept) | -- | -- | 109,086 | 3 | violated: NoLeakShips, 9 states |

Every violated config lists `TypeOK` and exactly ONE other invariant, so the verdict names the rule
the config is about. Every tooth breaks at the `ci` bound.

### Why the `ci` bound is what it is, and what it loses

The first module's `ci-shipped` took 53 s on this box with 16 workers: no margin against the 60 s
`ci` limit on a 2-4-core runner, and the amendment GREW the space: with the agent free to fork `s2`
early, the amended module took 9,735,002 states / 75 s even at `MaxSliceEdits = 1`. Three changes
bring it to 8.0 s (18.3 s with 2 workers):

1. **Two exact re-encodings.** A slice branch is the set of files it wrote, not a fork snapshot plus
   a tree (the snapshot is never read); a slice run is a flag, reset by the slice's next write.
   Neither changes a verdict.
2. **The integration run is a flag** reset by every change to the branch (see "The shape": stricter
   than a tree compare, no verdict depends on it).
3. **`MaxSliceEdits = 1`**: one file per slice diff. This is the one real loss: no slice in `ci`
   writes two files, so a slice that writes inside AND outside its paths, or a merge that keeps one
   reviewed file and rewrites another of the same slice, is checked only by `deep`.

The first two alone bring the first module's bound to 1,025,388 states (`deep-shipped-maxslice3`,
8.8 s with 16 workers, 33.2 s with 2): too close to the limit on a slow runner, so it is `deep`.

**The `ci` bound is not vacuous.** `ci-reachable` reaches pr-ready at the `ci` bound with all three
slices integrated AND a file whose content a merge made still in the change; `ci-all-dropped`
reaches pr-ready with every slice dropped; every tooth breaks at it.

### The vacuity and reachability controls (TLC traces)

Each line is the action TLC names and the variables it changed, copied from its output.

- **`ci-vacuity`** (`HashCarry` off, 9 states): Start `s1`; Drop `s2`; Drop `s3`; Edit
  `ed=[s1 |-> {"f1"}, ...]`; Review `rv=[s1 |-> {"f1"}, ...]`, `seen=[f1 |-> {1}, ...]`; Merge
  `chg=[f1 |-> 4, f2 |-> 0, lock |-> 0]` (the merge resolved `f1` by hand); Integrate
  `irev=[f1 |-> 4, f2 |-> 9, lock |-> 9]` (the sum is believed); TestRunInt: pr-ready with `f1` at a
  content no review saw.
- **`ci-reachable`** (everything on, 18 states): Start `s1`; Edit `f1`; Review; Merge
  `chg=[f1 |-> 1, ...]`; Integrate; Start `s2` (`forkOk` TRUE: `s1` merged); Start `s3`; Edit `s2`
  `f2`; Review `s2`; Edit `s3` `f1`; Review `s3` (`seen=[f1 |-> {1, 3}, ...]`); Merge `s2`; Integrate
  `s2`; Merge `s3` `chg=[f1 |-> 4, f2 |-> 2, lock |-> 0]` (the conflict with `s1`'s `f1` resolved by
  hand); Integrate `s3` (nothing carries: `f1` is not what `s3` reviewed); IntReview
  `irev=[f1 |-> 4, f2 |-> 2, lock |-> 9]`, `seen=[f1 |-> {1, 3, 4}, ...]`; TestRunInt: pr-ready. The
  hash rule's re-review path is reachable, not a wall.
- **`ci-all-dropped`** (everything on, D3, 7 states): Drop `s1`; Drop `s2`; Drop `s3`; IntEdit
  `chg=[f1 |-> 5, f2 |-> 0, lock |-> 0]`; IntReview `irev=[f1 |-> 5, ...]`, `seen=[f1 |-> {5}, ...]`;
  TestRunInt: pr-ready with every slice dropped, through the ordinary rules. No new rule is needed.

### The teeth and the AC-SL case each will replay

The AC-SL numbers follow the order of ADR-063's Verification list (AC-SL-01 = byte-identical
without slices, ..., AC-SL-14 = per-slice ledgers, then the three items the amendment appended:
AC-SL-15 drop refusal, AC-SL-16 ancestry, AC-SL-17 all-dropped converges). They are a PROPOSAL
until the RED cases exist. Each tooth enters `models.json` only with its `replays`, the ADR-062
precedent: `check` refuses a counterexample config that replays no AC id, and refuses an id that
ACCEPTANCE and the suite do not carry.

| tooth | breaks | AC-SL | shortest trace (TLC, `-workers 1`) |
|---|---|---|---|
| `tooth-without-hash-carry` | `ReviewedContent` | AC-SL-09 | the `ci-vacuity` path, 9 states |
| `tooth-without-disjoint` | `NoOverlapRunning` | AC-SL-04 | Start `s1`; Start `s3`: 3 states |
| `tooth-without-after` | `AfterRespected` | AC-SL-05 | Start `s1`; Edit `f1`; Merge `s1` (unreviewed, so not integrated); Start `s2` (`forkOk` TRUE); Edit; Review `s2`: 7 states |
| `tooth-without-path-leak` | `NoLeakIntegrated` | AC-SL-06 | Start `s1`; Edit `f2`; Review; Merge; Integrate: 6 states |
| `tooth-without-integration-suite` | `IntegrationTested` | AC-SL-10 | Start `s1`; Drop `s2`; Drop `s3`; Edit `f1`; Review; TestRunSlice; Merge; Integrate: 9 states |
| `tooth-without-whole-delivery` | `WholeDelivered` | AC-SL-11 | Start `s1`; Edit `f1`; Review; Merge; Integrate; TestRunInt, with `s2` and `s3` still planned: 7 states |
| `tooth-without-drop-guard` | `NoLeakShips` | AC-SL-15 | Start `s1`; Drop `s2`; Drop `s3`; Edit `f2` (outside its paths); Merge `s1`; Drop `s1`; IntReview; TestRunInt: 9 states |
| `tooth-without-ancestry` | `BuiltOnAfter` | AC-SL-16 | Start `s1`; Start `s2` (`forkOk` FALSE: `s1` not merged); Edit `s1`; Review `s1`; Edit `s2`; Merge `s1`; Integrate `s1`; Review `s2` (passes the `integrated` check): 9 states |

`ci-all-dropped` is the control for AC-SL-17 (all slices dropped, pr-ready under the ordinary
rules); it may carry `replays: ["AC-SL-17"]` once that case exists. The replays of AC-SL-07
(unconverged) and AC-SL-08 (merge not an ancestor) have no tooth: both refusals are fixed ON.

## What the model says, read honestly

- **Two rules carry the evidence: `HashCarry` and `IntegrationSuite`.** With every other rule on,
  each one's absence lets the gate pass on something nothing measured (a content no review saw, an
  untested integration). These are the teeth with weight.
- **The plan rules -- `DisjointCheck`, `AfterCheck`, `AncestryCheck`, `PathLeakCheck`, `DropGuard`
  -- protect the PLAN and the declaration, not the evidence.** Measured at the `ci` bound: turning
  any ONE of them off leaves property 4 unbroken (the five "not kept" rows above). Property 5 is in
  those rows too, but with `IntegrationSuite` on the gate requires the integration run, so it holds
  by construction there; only property 4 is a measurement. Each
  tooth breaks the property that restates its own rule. Their value is that what ships is what was
  declared and built in order: the dropped-after-merge leak (property 8) passes review and tests
  and still ships a diff no declaration covered.
- **`AfterCheck` and `AncestryCheck` are both needed at this bound.** Without ancestry, a slice
  forked before its dependency was merged passes the `integrated` check later; without `after`, a
  slice built on a merged but unconverged (never integrated) dependency is reviewed.
- **Disjointness has no refusal in the ADR.** Property 2 holds only because the modelled agent obeys
  slice-plan's disjointness. An agent that starts two overlapping slices anyway is not modelled;
  measured, the hash rule and the integration suite still hold the gate without `DisjointCheck`.

## The open questions of the first module, and where they went

1. **Merge, then drop** -- broken by TLC (`probe-drop-after-merge`, now `tooth-without-drop-guard`).
   Answered by D1: `slice-drop` refuses a slice whose merge is in the change branch; revert first.
2. **All slices dropped** -- answered by D3: allowed; the change converges under the ordinary rules
   (`ci-all-dropped`).
3. **"Started" vs "reviewed"** -- answered by D2: the `after` refusal requires each `after` merge to
   be an ancestor of the slice branch. The model no longer assumes the agent obeys the plan's
   `after` column, which is what lets the tooth show it.
4. **What "its diff" means at slice-integrate** -- answered by D4: the slice branch's diff since its
   fork, not the merge commit's diff (the model's `Diff`).

## Limits of the abstraction (what the model does not cover)

- **One repo.** Decision 8 (multi-repo, non-git refusal) is not modelled.
- **No revert.** D1's way out ("revert the merge first, then drop") is not modelled: a merged slice
  can never be dropped here. Whether a revert really removes the slice's content (a later merge may
  depend on it) is the engine's and the human's problem, not checked.
- **No re-sync of a slice branch.** A slice branch never merges the change branch after its fork, so
  ancestry is decided at the fork. In git a slice forked early could merge the change branch in and
  then pass D2's ancestry check; the model is stricter than the engine there. An early-forked
  dependent slice is a dead end in the model (it cannot review and, once merged, cannot be dropped):
  not a safety violation, but no liveness property is checked either.
- **slice-plan itself is not modelled**: the agent obeys its disjointness and `max_parallel`, and
  the readout's `after` column is not consulted at all. `offer` vs `auto` is not modelled (both
  launch only what the agent decides here).
- **`max_parallel` never binds.** With this shape at most two slices can run together under
  `DisjointCheck`, and `MaxPar = 2`.
- **Hash identity is per file.** A file whose content equals a reviewed content counts as reviewed,
  whatever changed around it. Interactions across files are the integration suite's job; the model
  has no bugs, only stamps.
- **No review tiers off.** The ADR's "without `review_tiers` nothing carries" path is not modelled;
  every config is the `review_tiers` case.
- **The SLICES.md refusals** (no paths, duplicate id, unknown `after`, cycle, unknown repo) are
  parse-time checks, not state; not modelled.
- **The ancestor refusal at slice-integrate is fixed ON** and abstracted to a boolean (`merged`): the
  change branch never loses a merge (no reset, no force-push, no revert).
- **Each slice writes a single value**, so an edit after a review on the same file is not
  distinguishable from the reviewed content; per-slice review currency is ADR-062's model's ground.
- **Merge changes and change-branch fixes each write a single value** (4 and 5). A second lockfile
  regeneration or a second fix is the same content as the first.
- **The `ci` bound has one file per slice diff** (`MaxSliceEdits = 1`); multi-file slice diffs are
  checked only by the `deep` configs.
- **A slice test-run exists only with `IntegrationSuite = FALSE`**, the only gate that reads it (a
  state reduction: with the rule on, no invariant can tell it apart).
- **Per-slice ledgers not conflicting at merge** (decision 5) is a file-layout fact, not modelled.

## Reproduce

```sh
python tools/model-check.py check                                   # no Java
python tools/model-check.py run --tier ci --jar tla2tools.jar       # TLC, pinned sha256
python tools/model-check.py run --tier deep --jar tla2tools.jar --timeout 600   # by hand
# the teeth are NOT in the manifest until their AC-SL cases exist, so `run` does not run them --
# by hand (-workers 1: the shortest trace), each prints "Invariant <Name> is violated":
cd docs/parallel-slices/models
for c in tooth-without-hash-carry tooth-without-disjoint tooth-without-after \
         tooth-without-ancestry tooth-without-path-leak tooth-without-integration-suite \
         tooth-without-whole-delivery tooth-without-drop-guard; do
  java -cp tla2tools.jar tlc2.TLC -workers 1 -config $c.cfg -metadir <tmp>/$c SlicePlan.tla
done
```
