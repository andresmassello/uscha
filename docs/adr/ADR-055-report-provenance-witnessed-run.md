---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/.claude/skills/uscha-devloop/SKILL.md
  - uscha-kit/skills/uscha-devloop/SKILL.md
  - uscha-kit/.claude/skills/uscha-devloop/uscha_top.py
  - uscha-kit/skills/uscha-devloop/uscha_top.py
  - tools/release.py
  - README.md
---
# ADR-055: Test evidence is WITNESSED — the engine runs the project's declared test command and honors only the reports that run wrote

## Status: Accepted (2.10.0)

## Context

The engine ingests JUnit and coverage reports by path (`_junit_files_for`, qa_ledger.py:642;
`coverage()`, :388) and judges them by mtime or content+commit (ADR-039). Nothing ties a report
to a run. The v2.9.0 audit (A-F1, blocker) wrote two XML files by hand over a module that raises
on every call and has no test file: `phase --require pr-ready` exit 0, readiness acceptance 100%,
`check-terminado` SEALED. The snapshot even printed `tests=2 ... test_loc=0`, and no surface
flagged it. `README.md:70-72` promises "a report the agent did not write"; an ingest-only engine
cannot keep that promise, because it cannot tell who wrote a file.

ADR-008 rejected exactly the fix chosen here — "the engine reads `test_command_<type>` from
config and runs it" — on the ground that it turns a config file into a code-execution surface.
This ADR amends that rejection (see Alternatives). It also amends ADR-039 (adds rule c for
attested gate reads; rules a/b remain for unattested and no-git reads) and ADR-037 (`o`).

## Decision

1. **`test-run --repo R [--timeout S] [--json]`**, one atomic command: run, hash, ingest. It
   has no `--run` flag. The command is `_op_test_command` (:4836) — `repos[R].test_command`, else
   `defaults.test_command_<type>` — with ADR-051's live-config precedence per key; `_op_ci` keeps
   reading the same function. Nothing declared → exit 2, nothing runs, no type default guessed.
2. **Born of the run.** The report set (`_junit_files_for` ∪ the coverage paths `coverage()`
   probes) is hashed before and after. A report is born of the run iff it was absent before or
   its bytes changed. Unchanged bytes are not, fail-closed.
3. **Record** `ledger["test_runs"][]`: `id, repo, started_at, ended_at, wall_ms, command,
   command_origin, shell (sh|cmd|argv), platform, commit, dirty, tree, exit_code, status
   (PASSED|FAILED|TIMEOUT|NO_REPORT), reports[{path, kind, sha256, sha256_eol}], unchanged[]`.
   A string command runs through the platform shell (the `cleanroom` contract); a JSON list runs
   as argv with no shell, the portable form. Output streams; a capped tail is kept on failure.
4. **Ingest in the same command**: `_snapshot` (:2405) runs inside `test-run`. Every snapshot
   (also a plain `snapshot`) stamps each report `run: "TR-n" | null` by hash and records
   `tests.provenance {status: attested|partial|unattested}`.
5. **The tree stamp and run-anchored freshness (rule c).** `_tree_stamp` = `{commit,
   src_dirty: {path: blob | "deleted"}}` over the `_src_relevant` porcelain paths (ADR-039's
   machinery: `_seal_git`, `_git_path_list`, `_porcelain_paths`; every path is relative to the
   git root, so no cross-API comparison arises). Two
   stamps hold the same source iff every path in the source-relevant commit diff ∪ both dirty
   maps has the same effective blob — so committing exactly the tree a run measured is not a
   change. An attested report is current iff the tree now has the same source as its run's
   stamp. No git → ADR-039 rule (a). ADR-056 reuses the stamp.
6. **The three gate reads**, one verdict (`_Witness.check`, which `_evidence_live` wraps for `phase`; as
   shipped it also refuses a failed/timed-out run, a run with a deleted sibling report and a run of
   a command no longer declared, on every surface):
   - `_derive_phase` (:4031-4044): JUnit reports attested, current, hash-identical on disk, and
     the run's `exit_code == 0`. A non-zero exit with green reports blocks.
   - `_ac_tags` (:975): a file counts only when its sha256 is a born report of a run whose tree
     is current; otherwise it is listed `unattested`. Acceptance reads UNMEASURED, never 100%.
   - `_sealed_state` (:10970): a named report with `run: null` is a measured break; a snapshot
     without `provenance` (pre-2.10) is UNMEASURED, exit 2.
7. **Coverage** is witnessed the same way; readiness and `check-coverage` read only an attested,
   current coverage report (else UNMEASURED, exit 2). Coverage still does not gate `pr-ready`.
8. **Contradiction tripwire** `tests.executed > 0 ∧ test_loc == 0`: printed by
   `test-run`/`snapshot`, listed in `phase` evidence and `readiness` facts — advisory.
9. **Consumers.** `uscha top`'s `o` calls `test-run` (ADR-037 amended; `--rerun-cmd` ignored with
   a notice for one release). `tools/release.py` steps 4-5 become one `test-run`; this repo
   declares `repos[0].test_command = "bash uscha-kit/tests/smoke-engine.sh"`. The clean-room
   record gains `run`/`setup` (A-F4).
10. **CI-only suites**: CI runs the same `test-run` + `phase --require pr-ready` against the
    committed ledger. `repos[R].test_site: "ci"` changes only the local wording and makes the
    agent open drafts (ADR-058). There is no attestation path.
11. **Claims re-stated**: `README.md:70-72` becomes "a report born from a run the engine
    witnessed"; the trust boundary (the declared command) is written beside it. `README.md:155-156`
    (smoke) is under-claimed until smoke has the same witness.

## Alternatives

- **Keep ADR-008's rejection; re-claim only + tripwire** (the synthesis's minimum). Honest, but
  leaves the blocker open by design. Rejected by the owner.
- **`--run "<cmd>"` per call** (ADR-008's contract). The agent picks the command, so a command
  that echoes XML is attested. Rejected: A-F4 again.
- **Fall back to the kit's type default** when the project declares none. Guessing what a suite
  is — the thing ADR-008 refuses. Rejected.
- **mtime inside the run window** as the "born" test. Any later `touch` forges it. Rejected.
- **Grandfather pre-2.10 evidence.** That is the hand-written XML A-F1 used. Rejected (owner Q1).
- **A human "attests" a CI run / import a CI artifact.** The first is G1 with a signature; the
  second needs network and a forge API the stdlib engine does not have. Deferred.

**Why ADR-008's objection no longer holds:** the command is already in config and already read
(`_op_ci`); INV-RIGOR-02 already makes config a reviewed artifact; only `test-run` executes it,
it prints the command first, and every read-only subcommand still executes nothing.

## Consequences

+ A-F1 fails closed on all three surfaces; "Stale evidence is discarded" (README:141) becomes
  true for the gate.
+ The record tells a reviewer which command, at which tree, on which OS, with which exit code.
- The engine now executes declared shell. Stated, not hidden; one subcommand.
- Upgrade cost: one `test-run` per repo; ~48 hand-written JUnit suite fixtures move to a
  declared fixture command.
- Teams whose suite cannot run locally get `qa` locally until CI measures.

## Out of scope

`smoke-ingest` JSON and `log-gate --kind ci --ref` (same class, next); proving a command tests
anything; a concurrent writer during the run window; the shipped `test_command_dotnet` `$PWD`
under `cmd.exe` (named, not fixed); `test-run --all` for one command covering several repos.

## Acceptance (promoted to ACCEPTANCE.md in 2.10.0, smoke T173; AC-GI-16 shipped probe, AC-GI-17 `test_site: ci` and AC-GI-18..20 fresh-review reproductions added on promotion)

- AC-GI-01..03 — the A-F1 reproduction fails closed: `phase` exit 1, acceptance UNMEASURED,
  `check-terminado` exit 1, each naming `test-run`.
- AC-GI-04 — the `test_loc == 0` contradiction is shown on snapshot, phase and readiness.
- AC-GI-05, -06 — a real run is attested and pr-ready; committing that tree keeps it current.
- AC-GI-07, -08 — a source edit, a hand-overwritten report or a restored old report reads stale
  at read time.
- AC-GI-09 — non-zero exit with green reports blocks.
- AC-GI-10 — NO_REPORT and undeclared command are exit 2; nothing is guessed.
- AC-GI-11 — `--run` does not exist; the live config value is used and recorded.
- AC-GI-12 — the shell is recorded; list form runs without a shell on all three OS cells.
- AC-GI-13 — unattested coverage is UNMEASURED; `check-coverage` exit 2.
- AC-GI-14 — a v2.9.0 ledger loads; its evidence is refused until one `test-run`.
- AC-GI-15 — the release ritual and `uscha top` `o` go through `test-run`.
