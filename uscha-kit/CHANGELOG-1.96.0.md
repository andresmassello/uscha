# uscha-kit 1.96.0 — the ritual gets measured: dogfooding freshness by git ancestry, and a release script that refuses (2026-09-02)

No engine behaviour changes in this release. Everything here is about the machinery that
*produces* a release — the criterion that judges it, and the twenty manual steps that performed
it — and about one number on the board getting more honest rather than more green.

The thing that made this release necessary is small and was hiding in plain sight: `AC-DF-01`,
the criterion that enforces "the ledger is re-recorded after the engine changes", compared a
**wall clock** (`readiness_history[-1].at`, a string in a JSON file) against a **committer
timestamp**. Two different units answering one question about **order**. Closing that gap cost a
step nobody would have written on purpose.

## What changed

### The dogfooding criterion asked a clock and paid for it (ADR-041)

Because the suite emits the acceptance report *while it runs*, and the release order is
`code commit X` → suite → `snapshot` + `readiness --record` → `ledger commit X+1`, `AC-DF-01` was
evaluated at a moment when the ledger's newest readiness entry was still older than X. So the
ritual grew a step whose only purpose was to move a clock: **a throwaway `readiness --record`
before the suite**, taken on a tree whose tests had not been re-run yet, so that the criterion
would read green during the very run that measures it.

Three prices, all paid:

1. **The amend trap.** The pre-record dates the ledger after X, so X could never be amended
   afterwards — an amend re-dates X and orphans the snapshot's commit. That hazard existed *only*
   because a clock was being held ahead of a commit. Repo rule 9 wrote it in capitals because it
   had been hit.
2. **The board plotted the ritual instead of the product.** Roughly **46%** of
   `readiness_history` entries since 2026-08-18 are ritual artifacts: pre-suite records taken with
   the previous release's reports on disk, which cap at "tests red" or dip to 66.7 and jump back.
   The mirador time-lapse drew them as if they were readiness. Evidence about the release
   *procedure* was being rendered as evidence about the release.
3. **A green manufactured by a step whose only job was to be green.** The pre-record measured
   nothing new. It was a claim shaped like a measurement.

`AC-DF-01` is now decided by **git ancestry**, and no clock is consulted:

| relation between the two commits | verdict |
|---|---|
| the ledger's commit *is* the engine's commit | **PASS** — one commit carried both |
| the engine's commit is an **ancestor** of the ledger's | **PASS** — the X → X+1 ritual |
| the ledger's commit is an ancestor of the engine's | **UNMEASURED** — HEAD is the code commit; the evidence lands in the next one |
| neither contains the other | **FAIL** — the ledger was recorded on a history that does not contain the engine change |
| shallow clone, or no git | **UNMEASURED** — unchanged from 1.93.0 |

The shallow-clone guard is kept verbatim and for the same reason: at depth 1
`git log -1 -- <path>` returns HEAD for every path that exists, so engine and ledger would always
look like the same commit and the criterion would pass without measuring anything. It is also now
MEASURED rather than asserted (`AC-DF-05`): T150 clones the same fixture history with
`git clone --depth 1` and requires the pair — `pass` read in full, `skip` read at depth 1.
Delete the guard and the shallow clone silently joins the greens, which is exactly what the old
comment claimed could happen and nothing checked.

**Say the cost out loud: when X touches the engine, the code commit X now reports `AC-DF-01` as
UNMEASURED.** That is a real change to what the board shows for at most one commit per release,
and it is more honest than what it replaces. At such an X the ledger genuinely has not been
recorded yet; the honest report of a measurement that has not happened is an absence, and this
repo's whole posture is that absence renders as absence. The green that used to sit there was
manufactured by the pre-record. One honest UNMEASURED replaces one green that measured nothing —
and the tagged ledger commit X+1, the only commit `publish.yml` gates on and the only one a
consumer ever installs, still reads measured. A release whose X does NOT touch `qa_ledger.py` —
this one included — still reads PASS at X: the last engine commit really is an ancestor of the
last ledger commit.

The decision lives in **one** function, `dogfood_verdict` in `uscha-kit/tests/_harness.py`. The
acceptance emitter and the block that tests the outcomes (**T150**) call that same function:
a criterion whose test re-implements the criterion tests nothing. `AC-DF-02..05` drive them over
real temp git repos.

### The release ritual is a script that refuses, not prose a human re-reads (ADR-041)

Repo rule 9 was ~20 manual steps and eight ordering invariants written as prose, executed by hand,
between two fourteen-minute suite runs, once per release. `tools/release.py` performs the six
steps and **refuses**, naming the invariant each refusal protects:

- **I1** the branch is ahead of `origin/main` only, with no merge in progress and no unmerged
  paths;
- **I2** `uscha-kit/CHANGELOG-X.Y.Z.md` exists, still carries the `Suite: __SUITE__ …` placeholder
  line, and `vX.Y.Z` is not already tagged;
- **I3** the six version surfaces move together (exactly one hit per file), `SYSTEM-FACTS.json` is
  regenerated, and `facts --check` is green;
- **I4** the suite runs at X with no source-relevant path dirty, and a non-zero exit is a refusal;
- **I5** the evidence is recorded after X and X's identity has not moved since — the amend trap,
  now caught by the script instead of remembered by the maintainer;
- **I6** X+1 carries evidence only: no source-relevant path in its staged set — commit it into
  X first, or drop it;
- **I7** `check-terminado` prints SEALED at X+1, and main advances by a push, not a checkout;
- **I8** the tag is created only on X+1 and only once the `smoke` run for that exact SHA is
  completed and successful.

**X is the code commit, not a bump-only one.** Step 3 takes the working tree exactly as the
human left it — the feature, the docs, the changelog prose — plus the six surfaces and the
regenerated `SYSTEM-FACTS.json`, and commits them together, printing the staged list first. A
dirty tree is therefore the *normal* state at step 1 and is not refused; I1 asks only whether X
can be a fast-forward and whether git is mid-operation. The alternative — refusing until the
human has already committed the feature — would make the script grade a commit it never made,
and would make I6's "commit them into X first" advice impossible to follow.

Three things it deliberately does **not** do. It does not write the changelog prose — the
placeholder line is the receipt that the prose was written before the numbers existed. It does not
edit a published claim: a `facts --check` drift is printed and refused, and the human edits it
(`facts --write` is 1.97.0). It does not create the GitHub release; it prints the command.

Two smaller design notes worth stating. It **imports** `_src_relevant` from the engine by path
rather than re-typing the extension tables — one definition of "a change that invalidates a test
run" (ADR-039), not two — and it **parses** the `facts --check` file list out of
`site/sync-docs.sh` rather than keeping a second copy, because a second copy is a guarantee that
one day the release gates on a page the deploy does not. It is repo-level and **never shipped**:
`package.json` `files` carries `bin/`, `uscha-kit/`, `README.md` and `LICENSE`, not `tools/`, so a
bug in it can cost a release but can never reach an installed kit. **T151** drives it over throwaway fixture repos — real git trees
with a bare origin, the six surfaces, a copy of the engine and a fake suite command. `--dry-run`
is enough for the two checks that need no commits (I1 and I2); the others make real local
commits on forks of the fixture, because an amend trap and a staged-set refusal cannot be
observed without commits. The last, `AC-RL-06`, drives all six steps from a real
`git worktree add` with main checked out in the primary tree — the shape rule 9 actually
prescribes — and is where I7 is measured end to end (`AC-RL-01..06`).

**Why the script never checks anything out.** Rule 9 says a worktree per release, and in a
worktree `git checkout main` fails with `fatal: 'main' is already checked out at ...`. A first
draft of step 6 did exactly that, so it would have refused with `git failure` on every real
release — this one included. Main now advances by `git push origin HEAD:main`, which is the
better mechanism anyway: the SERVER is the only party that can enforce the fast-forward, and it
owns the ref that matters. The local `main` is a convenience, moved with `update-ref` only when
`git worktree list --porcelain` shows no worktree holding it; otherwise the script prints the
`git -C <path> merge --ff-only <sha>` for the human and leaves it alone.

### The seventh version surface is gone

Repo rule 6 says six version surfaces and smoke **T44** gates six. The repo-root
`uscha.config.json` carried a seventh `version` field that nothing gated and exactly one line
read: a cosmetic `doctor` header. Predictably it drifted — `docs/CROSS-PLATFORM.md` has carried
**N-6** ("repo-root `uscha.config.json` says 1.44.0 vs kit 1.50.1 … a one-line cleanup") since
1.50.1. The field is removed rather than re-synchronised: a number kept in step by hand with five
files it has nothing to do with is a chore that buys nothing. The engine is untouched — `doctor`
already read it with a `'?'` fallback, and for a CONSUMER project that does declare a version it
still prints one. `uscha-kit/uscha.config.json` — the config template a consumer copies — stays a
version surface and stays one of the six.

## Migration

None. No engine change, no shipped file changed behaviour, no acceptance semantics changed for any
project but this one. For maintainers of this repo the ritual changes: leave the work
uncommitted, write the changelog with the placeholder, update the published claims, and run
`python tools/release.py X.Y.Z --message-file <msg> --tag`.

Suite: __SUITE__ checks · 0 fail; acceptance __ACC__.
