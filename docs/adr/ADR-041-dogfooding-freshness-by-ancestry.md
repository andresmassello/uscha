---
governs:
  - uscha-kit/tests/_harness.py
  - uscha-kit/tests/smoke-engine.sh
  - tools/release.py
---
# ADR-041: The dogfooding criterion is decided by git ANCESTRY, not by a wall clock — and the release ritual is a script that refuses, not prose a human re-reads

## Status: Accepted (1.96.0)

## Context
Repo rule 9 says the kit's own ledger is measured, not narrated, and `AC-DF-01` is the criterion
that enforces it: the root `QA-LEDGER.json` must be re-recorded in or after the last change to
`qa_ledger.py`. Since 1.93.0 the criterion has had two arms — the commit that last touched the
engine also carries the ledger, **or** `readiness_history[-1].at` is not older than that commit's
committer time.

The second arm compares a **wall clock** written into a JSON file against a **committer
timestamp**, and that single mismatch of units is what deformed the ritual around it. Because the
suite emits the acceptance XML *while it runs*, and the release order is `code commit X` →
`suite` → `snapshot` + `readiness --record` → `ledger commit X+1`, `AC-DF-01` is evaluated at a
moment when the ledger's newest readiness entry is still older than X. So the ritual grew a step
whose only purpose was to move a clock: a **throwaway `readiness --record` before the suite**,
taken on a tree whose tests had not been re-run yet, purely so the criterion would read green
during the run that measures it.

Three costs, all paid, none of them theoretical:

1. **The amend trap.** The pre-record dates the ledger after X, so X may never be amended
   afterwards — an amend re-dates X and orphans the snapshot's commit. That hazard exists only
   because a clock was being kept ahead of a commit. It is written into rule 9 in capitals
   because it has been hit.
2. **The board plots the ritual instead of the product.** Roughly 46% of `readiness_history`
   entries since 2026-08-18 are ritual artifacts: pre-suite records taken with the previous
   release's reports on disk, which cap at "tests red" or dip to 66.7 and then jump back. The
   mirador time-lapse draws them as if they were the project's readiness. Evidence about the
   release procedure is being rendered as evidence about the release.
3. **A green manufactured by a step whose only job is to be green.** The pre-record measures
   nothing new. It is a claim shaped like a measurement — precisely what this repo's doctrine
   exists to refuse.

The information the criterion actually wants is not a time at all. It is an **order**: was the
ledger recorded after the engine changed? Git already answers that exactly, with no clock, no
timezone, and no file the maintainer has to keep ahead of a commit.

## Decision

### 1. `AC-DF-01` is decided by ancestry
`readiness_history[-1].at` is no longer consulted. Let

    engine_c = last commit touching uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
    ledger_c = last commit touching QA-LEDGER.json

then

| relation                                   | verdict                                     |
|--------------------------------------------|---------------------------------------------|
| `ledger_c == engine_c`                      | **PASS** — one commit carried both          |
| `engine_c` is an ancestor of `ledger_c`     | **PASS** — the X → X+1 ritual               |
| `ledger_c` is an ancestor of `engine_c`     | **SKIP = UNMEASURED** — HEAD is the code commit; the evidence lands in the next commit |
| neither contains the other                  | **FAIL** — diverged: the ledger was recorded on a history that does not contain the engine change |
| shallow clone, no git, nothing committed    | **SKIP** — unchanged (a `--depth 1` tree answers HEAD for every path, so it cannot be asked) |

The shallow-clone guard is kept verbatim from 1.93.0 and for the same reason: at depth 1
`git log -1 -- <path>` returns HEAD for every path that exists, so engine and ledger always look
like the same commit and the criterion would pass without measuring anything.

### 2. One implementation, two callers
The decision lives in `uscha-kit/tests/_harness.py` as `dogfood_verdict(root, engine_rel,
ledger_rel)` returning `"pass" | "skip" | "fail" | None` (`None` = the question could not be asked
at all: no git work tree, or neither path has ever been committed). The acceptance emitter
(`PYACC`) and the block that tests the four outcomes (`T150`) call the **same function**. A
criterion whose test re-implements the criterion tests nothing.

### 3. The pre-suite `readiness --record` is deleted
The ritual becomes: code commit X → suite → `snapshot` + `readiness --record` → ledger commit X+1.
Nothing dates a clock ahead of a commit, so nothing can be orphaned by an amend, and
`readiness_history` records only measurements taken on a tree whose suite had just run.

### 4. The ritual is a script that refuses, not prose that is re-read
`tools/release.py` (repo-level, stdlib only, never shipped — `package.json` `files` does not carry
`tools/`) performs the six steps and refuses loudly, naming the invariant it protects.

**X is the CODE commit.** The script does not ask for a pre-made commit and does not make a
bump-only one: step 3 takes the working tree exactly as the human left it — the feature,
the docs, the changelog prose — PLUS the six version surfaces and the regenerated
`SYSTEM-FACTS.json`, and commits them together with `git add -A`. A bump-only X would mean
the feature landed in a commit the script never saw, the suite in step 4 would measure
something other than the commit under review, and I6's advice would have nowhere to point.
The staged list is printed in the plan so nothing lands unseen; anything that must not ship
is the human's to stash or ignore before running. Consequently **a dirty tree is the normal
state at step 1 and is not refused** — I1 asks whether X can be a fast-forward and whether
git is mid-operation, nothing more.

- **I1** the branch is ahead of `origin/main` only, with no merge in progress and no unmerged
  paths;
- **I2** the human wrote `uscha-kit/CHANGELOG-<X.Y.Z>.md`, it still carries the placeholder line,
  and `v<X.Y.Z>` is not already tagged;
- **I3** the six version surfaces move together (exactly one hit per file), `SYSTEM-FACTS.json` is
  regenerated, and `facts --check` is green — a drifted published claim is a refusal, never an
  auto-edit;
- **I4** the suite runs at X with no source-relevant path dirty, and a non-zero exit is a refusal;
- **I5** the evidence is recorded after X and X's identity has not moved since it was made (the
  amend trap, now caught by the script instead of remembered by the maintainer);
- **I6** X+1 carries evidence only: no source-relevant path in its staged set, and the advice
  is actionable: commit it into X first, or drop it;
- **I7** `check-terminado` prints SEALED at X+1, and main advances by a PUSH, never a
  checkout: the ritual runs in a worktree per release (rule 9) and main is checked out in
  the primary tree, so `git checkout main` fails there every time. The script pushes
  `HEAD:main` and lets the SERVER enforce the fast-forward, then moves the local ref only
  when no worktree holds it (otherwise it prints the `git -C <path> merge --ff-only <sha>`
  for the human);
- **I8** the tag is created only on X+1 and only once the `smoke` run for that exact SHA is
  completed and successful.

The human still writes the changelog prose, still owns the published claims, and still approves
the tag. The script owns the mechanical order that was previously eight sentences of prose.

## Consequences

+ The criterion measures the thing it names — order — with the instrument that already records
  order. No clock, no timezone, no pre-record.
+ The amend trap disappears as a hazard because the thing it endangered (a clock kept ahead of a
  commit) no longer exists; the script additionally refuses on it (I5) rather than trusting a
  maintainer to remember a rule written in capitals.
+ `readiness_history` stops carrying ritual noise, so the mirador time-lapse plots the product.
+ Eight prose invariants become eight named refusals with exit codes.
+ The tagged ledger commit X+1 — the only commit `publish.yml` gates on, and the only one a
  consumer ever installs — reads measured, exactly as before.
+ A ledger recorded on a history that does not contain the engine change now reads FAIL. The
  clock rule could not see that case at all: two parallel branches merged, neither commit
  containing the other, and a timestamp says nothing about containment.

− **When X touches the engine, the code commit X reports `AC-DF-01` as UNMEASURED.** This is a
  change to what the board shows for at most one commit per release, and it is stated rather than
  hidden: at such an X the ledger genuinely has not been recorded yet, and the honest report of a
  measurement that has not happened is an absence. The green that used to appear there was
  manufactured by the pre-record. One honest UNMEASURED replaces one green that measured nothing.
  A release whose X does NOT touch `qa_ledger.py` — a docs, suite or tooling release, 1.96.0
  itself among them — still reads PASS at X: the last engine commit is genuinely an ancestor of
  the last ledger commit.
− `tools/release.py` is a new surface that can itself be wrong. It is measured
  (`AC-RL-01..05`, T151) and it is not shipped, so a bug in it can cost a release but can never
  reach an installed kit. Two bugs in it were caught by its own tests and its dry run before it
  ever ran a release: a `.strip()` over the whole `git status --porcelain` blob that mangled the
  first path, and git's advice on stderr being parsed as paths.
− A dirty tree is no longer refused at step 1, so the human is responsible for what the working
  tree contains when they run the script. The staged list printed in step 3's plan is the
  mitigation, and it is a weaker one than a refusal: it informs, it does not stop.

## What this ADR does NOT decide
Whether `facts --check` should be able to WRITE the published claims it finds drifted (deferred to
1.97.0: this release refuses and names them). Nor anything about the seal or the freshness rules —
ADR-038 and ADR-039 are untouched, and `_src_relevant` remains the single definition of "a change
that invalidates a test run", imported by the script rather than re-typed.

## What is measured (`AC-DF-02..05`, `AC-RL-01..06`)
- `AC-DF-02..05` — T150 drives the outcomes over real temp git repos through the same
  `dogfood_verdict` the emitter calls: same-commit PASS, X → X+1 PASS, HEAD-is-X SKIP,
  diverged FAIL, a non-git tree `None` (UNMEASURED, never a silent pass), and — `AC-DF-05` —
  the SAME history read in full (PASS) and through a real `git clone --depth 1` (SKIP), which is
  what makes the shallow guard measured rather than merely asserted.
- `AC-RL-01..06` — T151 drives `tools/release.py` over throwaway fixture repos. `--dry-run`
  suffices for the two refusals that need no commits: `AC-RL-01` (I1: a diverged branch, a
  half-done merge, and the negative — a DIRTY tree ahead of `origin/main` passes) and
  `AC-RL-02` (I2: changelog, placeholder, existing tag). The other three need commits to exist,
  so they are REAL local runs on forks of the fixture: `AC-RL-03` the two commit shapes
  (X = surfaces + facts + the uncommitted feature; X+1 = ledger + changelog counts), `AC-RL-04`
  the amend trap (I5), `AC-RL-05` a source-relevant path in X+1's staged set (I6), and
  `AC-RL-06` the whole ritual driven from a real `git worktree add` with main checked out in
  the primary tree — the push lands on `origin/main`, the busy local ref is left alone,
  and nothing is checked out. That case is also where I7 is measured end to end, since it is
  the only one that runs all six steps.
