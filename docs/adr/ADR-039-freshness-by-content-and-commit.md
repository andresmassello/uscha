---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/skills/uscha-devloop/qa_ledger.py
---
# ADR-039: Evidence freshness is decided by CONTENT and COMMIT, not by the clock alone — a report is current when no source changed since the run that produced it, whatever the files' mtimes say; and the seal tolerates commits that touch no source

## Status: Accepted (1.93.0; approved as written by the maintainer 2026-08-19)

## Context
The freshness rule (1.31.0) discards a JUnit report older than the newest source file of its repo
(mtime vs mtime, 1 s tolerance). Cheap, no git needed, and it catches the dangerous case: editing
code and not re-running the tests. But mtimes measure *when a file was written to disk*, not
*whether its content changed* — and three ordinary operations rewrite every file's mtime without
changing a byte of source: a fresh clone or CI checkout, a `git worktree add`, a merge or rebase
that re-checks files out. The day INV-T1 shipped (1.92.0), the maintainer's own board read
`DONE 0/195 · 195 unmeasured` on the release machine: the fast-forward merge had re-dated the
sources after the suite's JUnit was written in a worktree, and the rule — honestly — threw the
evidence away. CI and the worktree where the suite ran read 195/195 at the same commit.

The seal (ADR-038) has the mirror problem at the commit level: `sealed.ok` requires `HEAD ==
evidence_origin.commit`. In the self-applied repo the ledger lives *inside* the commit it
describes, so the release commit is always one ahead of the snapshot it carries — the board
reads `stale seal` forever on the machine that released, although no source changed. And two
1.92.0 ingredients make a better rule possible now: every ingested report carries its `sha256`
(ADR-038) and every snapshot carries the commit it was measured at (ADR-007).

## Decision
- **Two freshness rules, either suffices; both are measured, neither is narrated.**
  (a) **Clock** — unchanged: report mtime ≥ newest source mtime (tolerance 1 s). No git needed.
  (b) **Content + commit** — a report is FRESH when: its current `sha256` equals the one the last
  snapshot recorded for it; the last snapshot recorded `evidence_origin.commit`; and git shows no
  *source-relevant* change since that commit — `git diff --name-only <commit> HEAD -- <repo
  subtree>` filtered by the engine's own source-extension set (`_SRC_EXT`) is empty, and
  `git status --porcelain -uall -- <repo subtree>` filtered the same way is empty. A report that
  fails (a) but passes (b) is fresh and says why (`fresh: content unchanged since <commit>`); a
  report that fails both is stale, as today. No git → (a) only, as today. A report without a
  recorded hash (pre-1.92.0 snapshot) → (a) only.
- **The seal tolerates non-source commits.** `sealed.ok` is `true` when the repo subtree is
  clean, every named report hashes to its record, and — instead of `HEAD == commit` — HEAD
  differs from `evidence_origin.commit` only by files outside the source-extension set and
  outside the report set (docs, the ledger, changelogs). The seal then carries a `note`:
  `HEAD <short> differs from snapshot <short> by non-source files only: <list, capped>`. A
  source-relevant difference is still `stale seal`, with the first offending path named.
  `check-terminado` exit codes unchanged (0 / 1 / 2).
- **One definition of "source-relevant" for both rules** — `_src_relevant()`, and widening it is
  a change to both rules at once, never to one. It is the union of three named sets: the engine's
  `_SRC_EXT`; the per-adapter `SOURCE_EXT[repo_type]` the clock rule narrows to (unioned in rather
  than assumed to be contained — `.hh`/`.hxx` were in one and not the other until 1.93.0, and are
  now in both); and the BUILD/HARNESS set, because a commit that rewrites what the suite runs
  changes what a green report means as surely as editing the code under test — extensions
  `.sh .bash .ps1 .yml .yaml .toml .sql .tf .gradle .cmake` plus the basenames `Makefile`,
  `pom.xml`, `build.gradle`, `package.json`, `pyproject.toml`, `setup.py`, `Cargo.toml`,
  `go.mod`. Deliberately OUTSIDE it, and this is the whole point of the tolerant seal:
  `.md`, `.json`, `.xml`, `.txt` — docs, changelogs, and the ledger and JUnit reports
  themselves, which are non-source by construction.
- **A snapshot may not launder itself.** `snapshot` records the tree as it is, so on a repo whose
  code moved and whose tests were never re-run it honestly writes `freshness: stale` — and that
  record must never become rule (b)'s anchor, or it would answer its own question (its commit is
  HEAD, its hash was taken over that very file) and turn UNMEASURED into GREEN. A snapshot whose
  own verdict was `stale`, and any report entry it marked `fresh_by: stale`, is no anchor at all.
- **Explicit under-claim.** Neither rule reads test *semantics*: a green report whose tests were
  weakened in a commit that IS source-relevant is stale (good); a green report whose fixtures
  live in an extension outside `_SRC_EXT` can be misjudged fresh — the set is the limit, and it
  is named in the SPEC sentence that describes freshness.

## What would be measured (draft, `AC-FR-01..07`)
- a report older by mtime than a source it did not change (touch/merge re-date) reads FRESH by
  (b) with the reason; the same report after a real source edit (content) reads STALE; after a
  commit touching only docs → FRESH; after a commit touching a `.py` → STALE.
- a report whose sha256 no longer matches its record is STALE even if mtimes say fresh.
- no git → (a) only, byte-identical verdicts to 1.92.0 on every existing fixture.
- seal: HEAD moved by docs/ledger only → `ok: true` + note; by a source file → `stale seal`
  naming it; the self-applied repo's release commit reads sealed on the release machine.
- `readiness`/`top`/`dashboard` outputs on every committed fixture byte-identical except where a
  previously-stale report is now fresh by (b) — listed in the CHANGELOG, not discovered.

## Consequences / Risks
+ Clones, worktrees, merges and CI checkouts stop un-measuring green evidence; the self-applied
  board reads the truth on the release machine too.
- One git call per ingested report set at read time (diff + status, bounded by the repo subtree).
- A project that keeps its tests' inputs in an extension outside the source-relevant set gets
  rule (b)'s blind spot; the rule is named, the set is configurable only by changing the engine
  (on purpose).
- The two rules can disagree, and the disagreement is BY DESIGN: a report that is clock-fresh but
  whose bytes no longer match the recorded hash still closes criteria (rule (a) never consulted a
  hash and does not start now), while the seal reads `evidence altered after ingest` and refuses.
  Acceptance measures whether the tests were re-run after the code; the seal is what gates
  TERMINADO, and that is the surface where the swapped log is caught.

## What this ADR does NOT decide
Semantic freshness (which tests a source change invalidates) — out of scope; the spec-drift
instrument and the round trip already cover the spec↔code side.
