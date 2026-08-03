# ADR-007: Evidence records the commit and tree state it was measured at; the worktree clean-room is deferred

## Status: Accepted

## Context
The engine can say *"tests green"* but not *"green **at what**"*. Freshness is computed from
file **mtimes** (`_test_evidence_provenance`), and nothing binds a snapshot to a commit. So
evidence produced against a dirty working tree is recorded as measured, with full provenance —
provenance that is true of the **tree**, not of the **commit that will merge**. A dirty tree
can make a suite pass while the candidate commit alone would fail, and the ledger cannot see
the difference.

The originating handoff proposed solving this with a **git-worktree clean-room**: check the
candidate SHA into a throwaway worktree, run the suite there, ingest the reports as a third
evidence grade (`NARRATED < MEASURED < MEASURED-CLEANROOM`), and block the PR step on it.

Options considered:
- **A) Ship the worktree clean-room now**, as the handoff specifies (`mode: "final"`, on by
  default). Rejected for this release — see the deferral below.
- **B) Bind evidence to a commit and a tree state; nothing more.** **Chosen.**
- **C) Do nothing; CI already checks out clean.** Rejected: true for *this* repo, false for the
  kit's users, and it leaves the ledger unable to answer a question it should be able to answer.

## Decision

**Every snapshot records where it came from.** `_snapshot` — the single ingestion choke point —
stamps `origin: {commit, dirty}` measured from `git rev-parse HEAD` and `git status
--porcelain` in the repo path.

- **Untracked files count as dirty** (plain `--porcelain`). An untracked file the suite depends
  on *is* the contamination case, and treating untracked as invisible is a mistake this engine
  already paid for in 1.57.0.
- **Absence is named.** No git, no repo, unreadable → both fields `null`. `dirty: null` must
  never read as clean; that distinction is the entire reason the field exists.
- **Advisory only.** `dashboard --json` carries `evidence_origin` **when a snapshot has one**,
  `snapshot` prints `origin=<sha8>/<clean|dirty|unknown>`, and `/uscha-status` says one line
  when the latest evidence was measured dirty. `cmd_readiness`, `_derive_phase` and
  `_converged` are untouched: no score moves, nothing blocks.

**The worktree clean-room gate is DEFERRED**, and this ADR records why rather than leaving the
handoff's Phase 2 silently unbuilt:

1. **It could not be built as specified.** `AC-CR-03` (a new commit makes prior clean-room
   evidence stale) and `AC-CR-04` (worktree SHA == candidate SHA) both require evidence bound
   to a SHA — which did not exist. This ADR is that prerequisite, not an alternative to it.
2. **It solves a narrower slice than it appears.** A local worktree runs on the same machine,
   OS and shell. The two red CI cells this repo paid for (bash 3.2 on macOS, Windows 8.3 short
   paths) are *environment variance* — a different failure class — and would have been green in
   a local clean-room. For this repo the clean checkout already exists: CI, across six
   environment cells, and nothing is tagged without it.
3. **Its residual value is real but narrow**: a tree that is *clean* yet whose suite depends on
   a gitignored artifact. Worth catching — for projects with no CI, worth quite a lot — but not
   worth a full rebuild on every pre-PR gate until someone hits it.

**If it is ever built, it ships OFF by default** — `absent block = feature off`, the convention
now established three times (`fast_path`, `spec_drift`, `forbid_when_golden_touched`). The
handoff's `mode: "final"` default would change the PR gate for every upgrading user, which
INV-RIGOR-02 reserves for a human declaration.

## Reasons
- A ledger that records *what* was measured but not *where* is one honest step from a false
  "done"; the fix is small and belongs at the choke point, not in a new subsystem.
- Recording a fact costs nothing to anyone who ignores it; a gate costs everyone who upgrades.
- Deferring with the reasons written down is what let Phase 1.5 be picked up cleanly from
  ADR-004 rather than re-litigated (see ADR-006).

## Consequences
+ "Was this evidence measured on a dirty tree?" becomes answerable, per snapshot, mechanically.
+ The prerequisite for the clean-room gate exists whenever it is wanted; `AC-CR-03`/`AC-CR-04`
  become constructible.
- `origin` is a **claim about the repo path**, not about the whole workspace: a multi-repo
  ledger stamps each repo separately, and a change outside every configured repo path is
  invisible to it. Named here rather than discovered later.
- Two extra `git` calls per snapshot. Negligible, and they degrade to `null` rather than fail.
- Knowing a tree was dirty does **not** tell you the evidence is wrong — only that it was not
  produced from a commit alone. Escalating that to a verdict is exactly the guess this ADR
  refuses to make.

## Implementation Plan
- Affected paths: `qa_ledger.py` (`_evidence_origin`, `_origin_label`, the `origin` key in
  `_snapshot`, the `cmd_snapshot` print, the conditional `evidence_origin` in `cmd_dashboard`),
  `uscha-kit/.claude/skills/uscha-status/SKILL.md`, kit `README.md`, twins for all.
- Patterns: the careful git-call convention (`cwd=`, `encoding="utf-8"`, `errors="replace"`,
  returncode inspection) used by `cmd_fastpath_eval`; the conditional dashboard key used by
  `fast_path` and `spec_drift`.
- Tests: smoke **T118** feeding `AC-EP-01..04` through the sidecar pattern of T113/T114/T117.

## Verification
- [ ] snapshot in a clean repo → `origin.commit` == HEAD, `dirty` false (AC-EP-01)
- [ ] snapshot with an uncommitted change → same commit, `dirty` true (AC-EP-02)
- [ ] snapshot outside a git repo → both null, no crash, and `dirty` is not false (AC-EP-03)
- [ ] readiness score numerically identical to before the field existed (AC-EP-04)
