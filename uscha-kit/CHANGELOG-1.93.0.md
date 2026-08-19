# uscha-kit 1.93.0 — evidence freshness by content and commit, not by the clock alone; the seal tolerates commits that touch no source (ADR-039) (2026-08-19)

Born from INV-T1's first day on the kit's own board: the release machine read `DONE 0/195 · 195
unmeasured` because a fast-forward merge had re-dated every source file after the suite's JUnit
was written in a worktree, and the freshness rule (1.31.0, mtime vs mtime) threw the evidence
away — honestly, and wrongly about the world: no source had changed. The maintainer approved
ADR-039 as written.

## What changed

- **Two freshness rules; either suffices.** (a) the clock rule, unchanged. (b) **content +
  commit**: a report is FRESH when its current `sha256` equals the one the last snapshot recorded
  for it, that snapshot names the commit it was measured at (ADR-007), and git shows no
  *source-relevant* change since that commit — `git diff --name-only <commit> HEAD` and the
  porcelain status of the repo subtree, both filtered by the engine's ONE source-relevant set
  (`_src_relevant`: `_SRC_EXT` + the adapter's `SOURCE_EXT[repo_type]` + the build/harness set),
  are empty. One helper (`_report_fresh`) decides it for both the snapshot record
  and the read-time tag ingestion, so readiness and `uscha top` can never disagree. Per report the
  record now says `fresh_by: clock | content | stale`; a report fresh by content only says why
  (`content unchanged since <commit>`). No git, no recorded hash, no commit → rule (a) only,
  byte-identical to 1.92.0 (measured: AC-FR-06).
- **The seal tolerates non-source commits (ADR-038 amended).** `sealed.ok` no longer requires
  `HEAD == snapshot commit`: HEAD may differ only by files outside the source set and outside
  the named reports — docs, the ledger, changelogs — and the seal then carries a `note` listing
  them (capped). A source-relevant difference is still `stale seal: source changed since snapshot
  <sha>: <path>`. A snapshot commit that no longer exists stays fail-closed. `check-terminado`
  prints the note; exit codes unchanged.
- **"Source-relevant" is one named set, and it includes the harness.** `_SRC_EXT` (now with
  `.hh`/`.hxx`, which `SOURCE_EXT["cpp"]` already had), the adapter's own `SOURCE_EXT[repo_type]`,
  and the BUILD/HARNESS files that decide what the suite runs — `.sh .bash .ps1 .yml .yaml .toml
  .sql .tf .gradle .cmake` plus `Makefile`, `pom.xml`, `build.gradle`, `package.json`,
  `pyproject.toml`, `setup.py`, `Cargo.toml`, `go.mod`. Outside it on purpose: `.md`, `.json`,
  `.xml`, `.txt`, so the ledger and the reports are non-source by construction.
- **A snapshot may not launder itself.** A snapshot taken on a tree whose tests were NOT re-run
  records `freshness: stale` — and that record is refused as rule (b)'s anchor, or it would answer
  its own question and turn UNMEASURED into GREEN (AC-FR-08).
- **Named limits.** Test inputs kept in extensions outside the set are rule (b)'s blind spot; a
  clock-fresh report whose hash no longer matches still closes criteria while the seal refuses it
  (by design — the seal is what gates TERMINADO); and a repo that lets git rewrite line endings on
  checkout will read `evidence altered` on an untouched file (fix: `* text=auto eol=lf`). All three
  in SPEC §4 and ADR-039.

`AC-FR-01..10` (T147) measure it over temp git repos driven by the engine: a report re-dated but
unchanged reads FRESH by content; a real source edit → STALE; a docs-only commit → FRESH; a `.py`
commit → STALE; an edited report (hash) → STALE whatever the mtimes; no git → identical verdicts
to the previous engine; the seal: docs/ledger-only HEAD → `ok` + note, a source change → `stale
seal` naming the file; a `.sh` or a `pom.xml` committed after the snapshot → STALE and an unsealed
board. The 1.31.0 freshness tests stay green (without a snapshot, rule (b) is inert and a re-dated
report is still stale).

**Honest note on the motivating case.** The kit's own committed ledger did not flip on arrival: its
last snapshot pointed at a commit the release ritual's `squash`+`amend` had rewritten (dangling →
fail-closed), and the carried report had been re-run after that snapshot. The engine was right; the
ritual was wrong. The fixed ritual — commit the code (X), run the suite, `snapshot` at X, then
commit the ledger AND the JUnit it names (X+1) — is what **AC-FR-09** measures end to end, on a
temp repo cloned at X+1 (the very operation that re-dates every file): the evidence reads fresh by
content, `check-terminado` exits 0, and the note names the ledger and the report as the only
things that moved. That the KIT's own board reads sealed is therefore a claim about this release's
ritual, and it holds only if this release followed it — the board says so or it does not; nothing
here decides it in advance.

Suite: 435 checks · 0 fail; acceptance 205/205.
