# uscha-kit 2.17.0 -- parallel slices: the engine says which slices of one change can run at once, and the merge decides, not the sum

Three new subcommands and one new file, found by watching the owner parallelize slices by hand in
four separate projects (ADR-063). A project with no `SLICES.md`, no `slices` config and no slice
record in its ledger is unchanged, except for the rename note under Behavior changes: every output is
byte-identical to 2.16.1 (AC-SL-01 compares the real v2.16.1 engine on a project without
`review_tiers`).

## What changed

- **`SLICES.md` declares the slices.** Beside `uscha.config.json`, one `## <id>` block per slice with
  `paths:` (required, globs relative to the slice's repo path), `acceptance:`, `after:` and `repo:`.
  Prose and unknown lines are ignored. It is refused (exit 2, naming the slice) for a slice with no
  paths, a duplicate id, an unknown `after`, an `after` cycle, a `repo` the config does not declare,
  or an absolute or `..` path. The optional `slices` block of the config (`parallel`: `offer` by
  default or `auto`; `max_parallel`: 5) is read live, like `review_tiers`.
- **`slice-plan [--json]` (read-only).** Each slice with its status (`planned`, `running` when branch
  `slice/<id>` exists, `integrated`, `dropped`) and the slices that can start now: every `after`
  integrated, globs disjoint from every running slice of the same repo and from those already picked,
  at most `max_parallel` running. A startable slice is marked `offer`, or `launchable` under `auto`
  (launch ONLY what is marked). `blocked_by` names `after:<id>`, `overlap:<id>` or `cap`. **The engine
  launches nothing**: no worktree, no session, no merge; git is only read.
- **One ledger per slice.** Slice S writes `QA-LEDGER.S.json` on its own branch, so slice ledgers never
  conflict at merge. `review-start` and `log-step` on it refuse (exit 2, naming both slices) while an
  `after` slice is not integrated in the main ledger, or is integrated but its merge is not an
  ancestor of the slice's branch (D2). In a slice project (a `slices` config or integration records)
  a slice ledger with no `SLICES.md` beside it is refused too, naming the slice and the file, instead
  of skipping the guard (AC-SL-21).
- **`slice-integrate --slice S`**, on the change branch. Refuses (exit 2, ledger unchanged), in this
  order: the slice tip is not an ancestor of HEAD; the slice ledger has not converged; the slice's own
  diff leaves its declared paths, named `S -> path`. The own diff is the slice's branch since its
  fork, never the merge commit's diff (D4), so a lockfile the merge regenerated is not a path leak.
  It is read without rename detection, so moving a file from outside the slice's paths into them is a
  deletion outside the paths and is refused (AC-SL-18). Only the slice's own ledger is exempt: a
  slice whose own diff touches the main ledger is refused, naming the slice and the file, because it
  could carry forged integration records (AC-SL-20). Otherwise the main ledger records the
  integration.
- **The gate is measured on the integration.** `phase --require pr-ready` also needs every declared
  slice integrated or dropped, for any repo of a slice project, plus the test-run at the integration
  commit it always needed (slice runs do not count). Under `review_tiers`, a slice's clean review
  carries into the main ledger only for the files whose content hash is the one reviewed; a file the
  merge changed (a regenerated lockfile, a conflict the agent resolved) is unreviewed, is named, and is
  the scope of the next review. Without `review_tiers` nothing carries.
- **`slice-drop --slice S --human NAME --note TEXT`** is a human act (exit 2 under CLAUDECODE) and a
  recorded scope change. It refuses a slice whose merge is already in the change branch (D1): its tip
  is an ancestor of HEAD and a file of its own diff still holds the slice content. Revert the merge
  first. A slice that started but whose branch was deleted after the merge is refused too, naming
  `slice/<id>`: the engine cannot prove the content is out, so restore the branch first (its tip is in
  `git reflog`) and the ordinary check then applies (AC-SL-19). "Started" means its ledger
  `QA-LEDGER.<id>.json` is on disk or in the history of HEAD, or a first-parent merge subject names
  `slice/<id>`; a slice that never started still drops. A git call that errors counts as merged. A change whose every slice was dropped converges under the ordinary rules
  (D3).
- The devloop `SKILL.md` gains a Parallel slices section: how to read `slice-plan`, `offer` versus
  `auto`, a worktree and a session per slice, `--no-ff` merges in `after` order, `slice-integrate`,
  "revert first", and the copy + `git init` way out for a tree that is not a git repository.
- ADR-063 was modelled in TLA+ first (`docs/parallel-slices/models/`): the model broke a drop after a
  merge, which is why `slice-drop` has its guard. AC-SL-01..17 replay its counterexamples; AC-SL-18..22 pin the review findings. The
  subcommand count is 67.

## Behavior changes on upgrade (read before upgrading)

- Nothing slice-related for a project with no `SLICES.md`, no `slices` config and no slice record in
  its ledger. One shared change: the change's file list (`review_tiers` tier, review scope) is now read
  without rename detection, so a committed rename lists its source path too (a deleted source counts
  as changed). A project with `review_tiers` and a committed rename can therefore see the old path in
  its tier or scope; a project without `review_tiers` is unaffected.
- In a slice project (a `SLICES.md` beside the ledger) `SLICES.md` and every `QA-LEDGER*.json` beside
  the ledger are bookkeeping, not review content: they no longer move a review's tree.
- A `slices` config key, or slice records in the ledger, with no `SLICES.md` beside the ledger keeps
  `phase --require pr-ready` closed (the slices cannot be measured).
- Any file named `QA-LEDGER.<id>.json` beside a `SLICES.md` is read as slice `<id>`'s ledger: an id the
  file does not declare is refused at `review-start` / `log-step`.

## Honest limits

- **The model does not cover** the revert path D1 asks for (a merged slice can never be dropped in the
  model, and whether a revert really removes the content is not checked), a slice branch that merges
  the change branch in again (re-sync), multi-repo slices, `offer` versus `auto`, the `SLICES.md`
  refusals, the per-slice ledger layout, or the path without `review_tiers`. The AC-SL cases replay its
  counterexamples against the engine and are the only link. A green model proves no violation OF THE
  MODEL at its bounds.
- **Glob overlap is conservative.** Two globs overlap when the literal prefix before the first wildcard
  of one is a prefix of the other's. A glob that starts with a wildcard overlaps everything. A false
  overlap only delays a launch; the rule never says two slices are disjoint when they are not.
- **Slice convergence is judged at the slice tip**, by the cycles the slice ledger recorded, because
  other slices merging legitimately move the change tree. It does not read the test-run bytes of a
  shared checkout: the integration suite is the gate for the sum.
- The `after` ancestry check (D2) holds when both slices live in the same repo; across repos only
  "integrated" is checked. The check reads HEAD of the slice's repo, so run it in the slice's worktree.
- A slice merged by fast-forward cannot be integrated: the engine finds the slice's own diff by its
  merge commit, so merge with `git merge --no-ff`. A merge the engine cannot find counts as merged for
  `slice-drop`, which fails closed.
- Once integrated, a slice is not re-checked for content: reverting its merge afterwards is caught
  only while its tip leaves the change branch, not by the content it removed.
- The hash carry needs `review_tiers` and a base branch that resolves; without either nothing carries
  and the integration pays a full review, so parallelism then buys build time only.
- The ledgers of a slice living in a repo outside the git root of the project are not committed with
  it: moving them is the agent's job.
- The carry is per tool and per slice: a tool is credited only with the files of the slices that carried THAT tool, and only the tools the slice's convergence vouched for (its tier's tools) carry. Each later `slice-integrate` appends a newer carry, which re-flags a file an integration review already cleared if a later merge moved it again: fail-closed, at the price of a re-review per integration.
- Dropping a slice an `after` slice depends on leaves the dependent blocked (`after:<id>`) until
  `SLICES.md` is edited.
- **Files changed only by a merge commit (an evil merge) are not path-checked, by design (D4):** the
  own diff is the slice's, never the merge commit's. Under `review_tiers` the hash carry marks such a
  file unreviewed; without `review_tiers` only the integration suite covers it.
- The slice ledger is read from the working copy: run `slice-integrate` and the guards with the slice
  ledger checked out as the slice committed it. A tool credited by a quick-tier slice is never
  credited to a standard-tier tool (AC-SL-22 pins both integration orders).
- A slice that started and whose branch was deleted without a merge (abandoned) is refused by
  `slice-drop` too, as the engine cannot tell it from a merged one: restore the branch to drop it.
- Residual hole in that guard: a merged slice whose branch was deleted, with no slice ledger on disk or
  in the history of HEAD and a merge subject that does not contain `slice/<id>`, still drops. The
  engine finds nothing that says the slice ever started.

## Evidence

Suite: __SUITE__ checks · 0 fail; acceptance __ACC__.
