---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/.claude/skills/uscha-devloop/SKILL.md
  - uscha-kit/skills/uscha-devloop/SKILL.md
model: required
model_manifest: docs/parallel-slices/models/models.json
---
# ADR-063: Parallel slices -- the engine says which slices of one change can run at once, and the merge decides, not the sum

## Status: Accepted (to ship as 2.17.0) — decided by the owner on 2026-11-17 (an `adr-refine` interview, one batch of eleven questions). The model (repo rule 12) is written before any engine code.

## Context

A change is often cut into slices (S1..Sn). The devloop builds them in series even when several
never touch each other. In the field the owner parallelized slices BY HAND in four separate
projects: one slice per git worktree and branch, one agent session per slice, the merge left to the
human. The decisions taken by eye were always the same three:

1. **Disjoint files.** A slice that touches only its own module runs alongside the others.
2. **Content dependency.** A slice that documents or consumes what another slice is still changing
   waits for it, even with no file in common.
3. **Isolation with history.** A tree that is not a git repository gets a copy plus `git init`
   before an agent touches it; without history there is no worktree, and two agents overwrite each
   other.

The kit saw none of it. It did not know slices ran in parallel, did not check they were disjoint,
and did not require the merge of slice branches that never saw each other to be measured. The
method was absent exactly at the dangerous point. Green per slice does not prove green together.

Options considered for the whole feature:

- A) **A planner**: the engine says what can run, nothing more.
- B) **A guardian**: the engine checks disjointness and measures the integration, but does not plan.
- C) **Both** (chosen): the engine evaluates what can run in parallel and governs what runs.

## Decision

1. **Declared in `SLICES.md`**, a human-readable file with one block per slice:
   - `id`;
   - `paths` (globs, relative to the slice's repo);
   - `acceptance` (AC ids);
   - `after` (slice ids it depends on);
   - optional `repo` (a repo name from `uscha.config.json`; default, the change's repo).

   ACCEPTANCE stays the contract of WHAT is delivered. `SLICES.md` is HOW it is split. A project
   with no `SLICES.md` and no `slices` config is unchanged, byte for byte.

2. **Configuration.** `slices` is read live from `uscha.config.json`, the ADR-051 / ADR-062
   precedent, with two keys:
   - `parallel`: `offer` (default) or `auto`.
     - With `offer` the agent proposes the parallel launch and the human says yes.
     - With `auto` the agent launches without asking, but ONLY what the engine measured as
       launchable, never its own reading that slices "look independent".
   - `max_parallel` (default 5).

3. **`slice-plan` is a read-only readout** (text and `--json`). It lists the slices that can start
   now:
   - declared paths disjoint from every running slice (in the same repo);
   - every `after` integrated;
   - at most `max_parallel` running;
   - each marked `offer` or `launchable` per the mode.

   **The engine never launches anything**: no worktree, no session, no merge (ADR-008: the engine
   measures and refuses, it does not execute). Creating worktrees and sessions is the agent's or the
   platform's job.

4. **Refusals, before and after.**
   - Before: a slice whose `after` is not integrated is refused at its first review step
     (`review-start` / `log-step`).
   - After: `slice-integrate --slice S` refuses, naming the cause, when any of these holds:
     - the slice's ledger has not converged;
     - its merge is not an ancestor of the change branch;
     - its diff touches a path outside its declared globs (named `S → path`).

   `SLICES.md` itself is refused, naming the slice, when any of these holds:
   - a slice has no paths;
   - an id is duplicated;
   - an `after` names an unknown slice;
   - the `after` relation has a cycle;
   - a `repo` is not in the config.

5. **Evidence per slice, integration in the main ledger.** Each slice writes
   `QA-LEDGER.<slice>.json` on its own branch, so slice ledgers never conflict at merge. The agent
   merges each slice branch into the change branch, in `after` order. `slice-integrate` records
   the integration in the main ledger. Only a human merges to `main`.

6. **The gate is measured on the integration (hard rule).**
   - **Suite.** pr-ready requires a test-run on the integration commit. Slice runs do not count.
   - **Review carry.** A slice's clean review pass carries into the integration ONLY for files whose
     content is identical to what was reviewed, compared by hash. Any file the merge changed
     relative to the reviewed content stays unreviewed and blocks the gate: a lockfile, a generated
     file, a conflict resolved by the agent. This requires `review_tiers` (ADR-062), the only source
     of per-file review stamps. Without `review_tiers` nothing carries: the integration converges
     under the ordinary rules, slower but honest.
   - **Conflicts.** A textual conflict is resolved by the agent with no special path. By the hash
     rule, the resolved files are re-reviewed.

7. **Incremental integration, whole delivery.** Slices that converged are integrated in dependency
   order, each integration measured. The change's pr-ready requires EVERY declared slice integrated.
   Dropping a stuck slice is a scope change and a human act: `slice-drop --slice S --human NAME
   --note TEXT` exits 2 under CLAUDECODE, and the act is recorded.

8. **Multi-repo.** A slice with `repo:` lives and integrates in that repo. Slices in different repos
   are disjoint by construction. The change's gate requires every repo's integrations. A slice whose
   repo is not a git repository is refused, naming it: without a commit there is no evidence
   (ADR-007). The way out (copy, `git init`, base commit) is documented in the devloop SKILL, and is
   done by the agent or the human, never by the engine.

## Amended after the model (2026-11-17)

The model (`docs/parallel-slices/models/`, repo rule 12) was written before any engine code and run
with TLC v1.7.4 the same day. It confirmed the six rules of decisions 3-7 and broke the open
question it was probing: **a slice merged into the change branch and then dropped ships its diff
without ever passing `slice-integrate`** -- including a diff that left its declared paths. Review
and the integration suite still gate that diff, so the evidence holds; what fails is the
declaration: the change ships a path no slice declared. The counterexample, verbatim from TLC (the
first module, `probe-drop-after-merge.cfg`, `-workers 1`; under each state, the variables it
changed, copied from TLC's output):

```
Error: Invariant NoLeakShips is violated.
State 1: <Initial predicate>
State 2: <Start line 91, col 3 to line 98, col 76 of module SlicePlan>
  /\ status = [s1 |-> "running", s2 |-> "planned", s3 |-> "planned"]
State 3: <Drop line 160, col 3 to line 162, col 86 of module SlicePlan>
  /\ status = [s1 |-> "running", s2 |-> "dropped", s3 |-> "planned"]
State 4: <Drop line 160, col 3 to line 162, col 86 of module SlicePlan>
  /\ status = [s1 |-> "running", s2 |-> "dropped", s3 |-> "dropped"]
State 5: <Edit line 102, col 3 to line 108, col 83 of module SlicePlan>
  /\ br = [ s1 |-> [f1 |-> 0, f2 |-> 1, lock |-> 0],
    s2 |-> [f1 |-> 0, f2 |-> 0, lock |-> 0],
    s3 |-> [f1 |-> 0, f2 |-> 0, lock |-> 0] ]
  /\ edits = 1
State 6: <Merge line 133, col 3 to line 141, col 77 of module SlicePlan>
  /\ mf = [s1 |-> {"f2"}, s2 |-> {}, s3 |-> {}]
  /\ chg = [f1 |-> 0, f2 |-> 1, lock |-> 0]
  /\ merged = [s1 |-> TRUE, s2 |-> FALSE, s3 |-> FALSE]
State 7: <Drop line 160, col 3 to line 162, col 86 of module SlicePlan>
  /\ status = [s1 |-> "dropped", s2 |-> "dropped", s3 |-> "dropped"]
State 8: <IntReview line 174, col 3 to line 177, col 82 of module SlicePlan>
  /\ irev = [f1 |-> 9, f2 |-> 1, lock |-> 9]
  /\ seen = [f1 |-> {}, f2 |-> {1}, lock |-> {}]
State 9: <TestRunInt line 181, col 3 to line 183, col 86 of module SlicePlan>
  /\ intRun = [f1 |-> 0, f2 |-> 1, lock |-> 0]
```

`s1` (declared `{f1}`) writes `f2`, is merged, and is dropped; an integration review and an
integration test-run then pass the gate with every slice dropped and `s1`'s out-of-paths diff in
the change. **Decided by the owner after the model (2026-11-17):**

- **D1 (amends decision 7).** `slice-drop` refuses a slice whose merge is already in the change
  branch, naming it. To drop such a slice, its merge is reverted first. *Reason:* a drop is a scope
  change, and a merged slice is no longer out of scope -- its content is in the change, so it must
  pass `slice-integrate` (convergence, path check) or leave the branch. The model's
  `tooth-without-drop-guard` is the trace above; with D1 `NoLeakShips` holds.
- **D2 (amends decision 4).** The `after` refusal at the first review step requires each `after`
  slice's merge to be an ANCESTOR of the dependent slice's branch (`git merge-base --is-ancestor`),
  not only integrated. *Reason:* an `after` edge exists because the dependent slice needs its
  dependency's CONTENT; "integrated" says the dependency reached the change branch, not that the
  dependent slice was built on it. An agent that forks the dependent slice early and reviews it
  once the dependency is integrated passes the `integrated` check with a slice that never saw the
  content (`tooth-without-ancestry`, 9 states). Both checks stay: without the `integrated` check a
  slice built on a merged but unconverged dependency is reviewed (`tooth-without-after`, 7 states).
- **D3 (clarifies decision 7, no new rule).** All slices dropped is allowed. The change then
  converges under the ordinary rules: the hash rule and the integration suite already cover
  anything on the branch, and each drop is a recorded human act. The model reaches pr-ready with
  every slice dropped through a fix, an integration review and an integration test-run
  (`ci-all-dropped`, 7 states).
- **D4 (implementation note on decision 4, not a new decision).** "Its diff" at `slice-integrate`
  is the slice branch's diff since its fork, not the merge commit's diff. *Reason:* the merge commit
  may regenerate a lockfile or resolve a conflict; read as the slice's diff, that file would be a
  path leak and decision 4 would refuse what decision 6 means to re-review under the hash rule.

**What the model shows, and at which bounds.** One repo, three slices, three files; the agent obeys
slice-plan's disjointness (no refusal exists for an overlap) but NOT its `after` column (the engine
refuses that at review). Checked with no error at the `ci` bound (one file per slice diff, three
writes in total: 812,126 states) and by hand at the first module's bound (three files per slice
diff, 1,025,388 states) and at four writes (6,892,376 states). Each of the eight rules breaks its
property when dropped alone; the five plan rules (disjointness, `after`, ancestry, path check, drop
guard) each leave "every shipped content was reviewed" unbroken when dropped alone (measured at
the `ci` bound; "a test-run on the integration" holds there by construction, since the gate requires
it): they protect the plan and the declaration, the hash rule and the integration suite protect the
evidence.

**What the model does not cover.**
- Multi-repo slices (decision 8), the SLICES.md parse refusals, `offer` vs `auto`, the per-slice
  ledger layout (decision 5), and the path without `review_tiers`.
- The revert D1 asks for: a merged slice can never be dropped in the model, and whether a revert
  really removes the slice's content is not checked.
- A slice branch that merges the change branch in after its fork: the model decides ancestry at the
  fork, so it is stricter than D2's check on the slice branch; an early-forked dependent slice is a
  dead end there (no liveness property is checked).
- Hash identity per file, one value per slice, one value per merge change and per fix; at the `ci`
  bound a slice's diff is one file. A green model proves no violation OF THE MODEL at its bounds;
  the AC-SL replays are the only link to the engine.

## Reasons

- **C over A or B.** A planner alone opens a hole in the evidence. A guardian alone leaves the owner
  deciding by eye, which is what the field showed.
- **`offer` by default.** Launching N sessions spends tokens and machine time, and the human should
  see it coming. `auto` is earned per project.
- **Declared, then verified.** A declaration nobody checks is a promise. Inferring slices from diffs
  answers "can I parallelize?" only after building, too late.
- **A ledger per slice** keeps evidence traveling with the commit (ADR-007/039). A single ledger
  outside git would lose that. A single versioned ledger would conflict on every merge.
- **Hash carry** avoids re-reviewing everything, but never believes the sum.
- **Incremental, whole** keeps finished slices moving without letting the contract shrink by itself:
  "ship without the hard part" is exactly the shortcut uscha exists to block.
- **No pause on conflicts.** The hash rule already guarantees that nothing the agent resolved
  escapes review; a human act there would protect nothing new.
- **`max_parallel` = 5** caps the cost of `auto`.

## Consequences

+ The pattern the owner repeated by hand in four projects becomes measured: which slices run,
  whether they stayed in their lanes, whether the merge is green.
+ Projects without slices are untouched, byte for byte.
- A new file (`SLICES.md`) and new subcommands (`slice-plan`, `slice-integrate`, `slice-drop`),
  so more surface.
- Without `review_tiers` the integration pays a full review; parallelism then buys build time only.
- Declared globs must be maintained; a slice that grows beyond them is refused at integration until
  its declaration is widened (and re-planned).

## Out of scope

- The engine launching worktrees, sessions or merges.
- Parallelism across DIFFERENT changes; this covers the slices of one change.
- Inferring slices from code or diffs.
- Distributing slices across machines or other vendors' agents with new guarantees: it works, but
  the engine sees only git and the ledger.

## Dependencies

- ADR-062 (review pace) for per-file review stamps (hash carry).
- ADR-007 / ADR-039 (evidence bound to commit and content).
- ADR-051 (live config read).
- ADR-008 (the engine never executes).
- No new runtime dependency: stdlib only.

## Implementation Plan

- Affected paths: both `qa_ledger.py` copies; both devloop `SKILL.md` copies (outside the generated
  orientation region); `uscha-kit/README.md`; the doc HTML ES/EN; `ACCEPTANCE.md`; the smoke suite
  (a new unit with its own sidecar); `docs/parallel-slices/models/`.
- Order (rule 12, then TDD):
  1. `SlicePlan.tla` with its manifest: ci config, a vacuity config without the hash rule that MUST
     break, and teeth for each refusal;
  2. RED cases `AC-SL-nn` against the current kit;
  3. the engine;
  4. docs ES/EN;
  5. the CHANGELOG.
- Patterns: live config read as `review_tiers`; human acts via `_human_act`; refusals exit 2 naming
  the slice and the rule.
- Tests: one RED case per Verification item below; each model counterexample replayed by an AC id.

## Verification (to be written as AC-SL-nn with the RED cases)

- [ ] Without `slices` config and `SLICES.md`, every output is byte-identical to the previous kit.
- [ ] `SLICES.md` refuses, naming the slice:
  - a slice without paths;
  - a duplicate id;
  - an unknown `after`;
  - an `after` cycle;
  - a `repo` not in the config.
- [ ] `slice-plan` (text and `--json`, read-only) lists the startable slices: disjoint, no pending
  `after`, at most `max_parallel`.
- [ ] Two slices with overlapping globs never appear together as parallel in `slice-plan`.
- [ ] A slice whose `after` is not integrated is refused at `review-start` / `log-step`.
- [ ] `slice-integrate` refuses a slice whose diff leaves its declared paths, naming `S → path`.
- [ ] `slice-integrate` refuses a slice whose ledger has not converged.
- [ ] `slice-integrate` refuses a slice whose merge is not an ancestor of the change branch.
- [ ] Under `review_tiers`, a clean slice pass carries only for files whose content hash is
  unchanged; a file the merge changed is unreviewed and blocks the gate.
- [ ] pr-ready requires a test-run on the integration commit; slice runs do not count.
- [ ] pr-ready requires every declared slice integrated. `slice-drop` is a human act (exit 2 under
  CLAUDECODE) and is recorded.
- [ ] A `repo:` slice integrates in its repo, and the gate requires every repo's integrations. A
  non-git repo is refused, naming it.
- [ ] `offer` vs `auto` is shown per slice in `slice-plan`, read live, default `offer`.
- [ ] Per-slice ledgers (`QA-LEDGER.<slice>.json`) do not conflict at merge.
- [ ] `slice-drop` refuses a slice whose merge is already in the change branch, naming it (D1).
- [ ] The `after` refusal at `review-start` / `log-step` is by ancestry: a slice whose `after`
  slice is integrated but whose merge is not an ancestor of the slice branch is refused (D2).
- [ ] A change whose every slice was dropped converges under the ordinary rules: a fresh review
  of the integration diff and a test-run on the integration commit reach pr-ready (D3).
- Success metric: on a three-slice disjoint demo, time to pr-ready drops against the serial run,
  and zero path leaks pass the gate.
