# uscha-kit 2.10.0 — witnessed evidence: only a report born of a recorded `test-run` counts, read at read time (ADR-055) (2026-10-31)

## What changed

A blind two-judge audit of v2.9.0 reproduced one class of defect: the engine could be made to lie.
Two hand-typed XML files (a JUnit with two AC-named cases, a coverage report at 97%) over a module
that raises on every call, with no test file at all, reached `phase --require pr-ready` exit 0,
readiness acceptance 100% and `check-terminado` SEALED (A-F1). The engine ingested reports BY PATH
and could not tell who wrote a file. 2.10.0 makes it the witness:

- **`qa_ledger.py test-run --repo R [--timeout S] [--json]`** — one atomic command: run, hash,
  ingest. It runs the test command the PROJECT declared (`repos[R].test_command`, else
  `defaults.test_command_<type>`; the live `uscha.config.json` beside the ledger wins per key over
  the frozen copy, ADR-051's precedence), hashes the report set (the JUnit files the engine ingests
  plus the coverage reports it reads) before and after, and records the run in
  `ledger["test_runs"]`: id, command, origin, shell (`sh` / `cmd` / `argv`), platform, commit, the
  source-tree stamp, exit code, status (PASSED / FAILED / TIMEOUT / NO_REPORT), the reports it WROTE
  and the ones it left unchanged. Then it snapshots, in the same call. There is **no `--run` flag**:
  a command chosen per call is exactly the hole this closes. Nothing declared → exit 2, nothing runs,
  no type default is guessed. A report is "born of the run" only when it was absent before or its
  bytes changed; identical bytes are not, fail-closed.
- **Every gate honors only a report born of a recorded run that is still current.** `phase`
  (tests measured green), the acceptance count (`_ac_tags`, which reads JUnit live) and the seal
  (`check-terminado`, `top --json`) all ask one function. A hand-written, hand-copied or
  hand-overwritten report is listed as unattested and the criterion reads UNMEASURED, never 100%.
  "Still current" is run-anchored (ADR-039 amended, rule c): the source-relevant content of the tree
  now equals the content the run measured — so committing exactly the tree a run measured is not a
  change, and an old report copied back with a fresh mtime is stale. A run whose exit code was
  non-zero while its reports read green blocks: the reports do not explain the failure.
- **`phase` re-derives freshness at read time** (A-F3). It used to read the verdict stored at
  snapshot time, so a source edit after the snapshot stayed `pr-ready` while `readiness` on the same
  ledger said stale. `phase`, `converged` and `readiness` now read the same live derivation.
- **An unverified QA step never counts and never hides** (ADR-056 R1, ADR-051 as written). Ordered
  mode builds the cycle from the latest SEEN step per tool: a newest step whose tool was MISSING at
  log time blocks with its own reason and is no longer replaced by an older verified one (B-F1).
  Window mode refuses any unverified step inside the window, and a tool whose newest step is
  unverified (B-F2) — `log-step` already printed "does not count toward convergence"; now it is true.
- **Coverage is witnessed the same way.** Readiness's coverage dimension and `check-coverage` read a
  coverage report only when a recorded, current run wrote it; otherwise UNMEASURED (exit 2 for
  `check-coverage`), with the reason named. Coverage still does not gate `pr-ready`.
- **The contradiction tripwire** — tests executed with `test_loc == 0` — is printed by `test-run`
  and `snapshot` and listed by `phase` and `readiness`. It is advisory: Rust inline tests produce it
  legitimately. Provenance is the gate.
- **CI-only suites** (owner decision Q2): `repos[R].test_site: "ci"` changes only the local wording
  — the gate for R is the CI job that runs the same `test-run` + `phase --require pr-ready` against
  the committed ledger — and points the agent at a DRAFT PR locally. There is no attestation path.
- **The clean-room record** gains `run` and `setup` (A-F4, folded): the command that produced the
  verdict is in the record.
- **The devloop SKILL** (both twins): a PR request in any wording runs `phase --require pr-ready`
  for every repo FIRST; when red, the agent shows the missing facts and asks ONE question — run the
  QA loop first, or open a DRAFT PR listing them — and never opens a ready-for-review PR while red;
  pushing a branch is not opening a PR. A QA step that could not run (permission denied, tool
  missing, crash) is reported to the human at that moment, and no step is logged for it.
  `test-run` is the only way test evidence is produced, and closing an escalation is a human act:
  the agent STOPs and asks the human to run `resolve-escalation`.
- **Consumers.** `uscha top`'s `o` runs the engine's `test-run` for the first configured repo
  (ADR-037 amended): one engine process per keypress, the command the project declared;
  `--rerun-cmd` is accepted and IGNORED with a notice for this one release. The release ritual's
  step 4 is `qa_ledger.py test-run --repo uscha` (step 5 keeps `readiness --record`; every refusal
  stays), and this repo's root `uscha.config.json` declares
  `repos[0].test_command = "bash uscha-kit/tests/smoke-engine.sh"`. `--suite-cmd` is gone from
  `tools/release.py`.

## Closed before release (fresh review)

A fresh-context review of this release reproduced four more ways past the gates, each now a red
case in T173 with teeth against the pre-fix engine, and all closed in ONE verdict
(`_Witness.check`) that `phase`, the acceptance count, the seal and coverage read alike:

- a command swapped in the live `uscha.config.json` for one run and reverted afterwards (git
  never shows it): a run counts only while its recorded command IS the command declared now
  (AC-GI-18);
- a FAILED or TIMEOUT run with green reports still counted for acceptance and the seal; the
  exit-code rule now holds on every surface (AC-GI-19);
- deleting the red report of two a run wrote, then re-snapshotting: a run's reports count all
  together or not at all (AC-GI-20);
- a run recorded with no tree (a repo with no commit yet) sealed once committed: when git can
  answer, "cannot compare" is not current (AC-GI-20).

Also from that review: the per-run git answers are memoised (100 reports: `phase` 7.7 s -> 0.3 s);
`test-run --repo integration` runs only `integration.test_command` (a per-type default is a repo's
unit suite, never the contract tests) and measures where `snapshot` measures it; `uscha top` runs
`test-run` from the ledger's directory; the kit README's subcommand list gains `test-run`.

## Behavior changes on upgrade (read before upgrading)

- **Evidence ingested before 2.10.0 fails closed until one `test-run` per repo** (owner decision
  Q1). Old ledgers LOAD unchanged (`test_runs` absent reads as none), but a snapshot with no
  provenance never satisfies `pr-ready`, acceptance or the seal: `phase` names "predates 2.10.0" and
  `test-run --repo R`, `check-terminado` exits 2 UNMEASURED. The cure is one `test-run`.
- **A report written by anything other than a recorded `test-run` is not evidence**: running the
  suite by hand and then `snapshot` no longer moves a gate. Replace that step in scripts and CI with
  `test-run`.
- **Window and ordered convergence refuse unverified steps**, including steps of a tool name that
  does not resolve. Declare an external tool in `defaults.qa_tools_external` if it is one.
- **Coverage from an unrecorded report reads UNMEASURED**, and readiness says so by name.
- A test command that writes byte-identical reports on every run reads NO_REPORT the second time
  (the bytes rule, named in ADR-055). Real emitters stamp a time; this repo's acceptance emitter now
  writes the standard JUnit `timestamp` attribute for exactly this reason.

## Migration note

1. Make sure `uscha.config.json` declares the test command (`repos[].test_command` or
   `defaults.test_command_<type>`); prefer a JSON list on mixed Windows/POSIX teams. The shipped
   `test_command_dotnet` uses `$PWD`, which `cmd.exe` does not expand (named, not fixed).
2. Run `qa_ledger.py test-run --repo <R>` once per repo.
3. CI-only suites: run `test-run` + `phase --require pr-ready` in CI against the committed ledger;
   declare `test_site: "ci"`.

## Pins that moved, on purpose

- **The `uscha top` fixtures** (`tests/fixtures/uscha-top/fixture-*/QA-LEDGER.json`) gain the
  `test_runs` record a 2.10.0 ledger carries for their reports (recorded without a tree: they never
  lived in a work tree), and every suite block that reads them in place now reads a copy outside
  git (`_harness.fixture_tmp`). Their `top --json` projection is byte-identical to the v2.9.0
  engine's over the original fixtures (checked on all three), and the golden frames did not move.
- **AC-FA-03 and AC-FR-06** (byte identity against v1.86.1 and v1.92.0) read that same copy; the
  anchor tags do not move. AC-FR-06's no-git repo now prints two 2.10.0 lines, both normalised BY
  NAME in the pin and nothing else: `acceptance medido: UNMEASURED (0/N ...)` where v1.92.0 printed
  a measured-looking `0.0% (0/N ...)` (the count is still compared), and the advisory
  `contradiction` line (dropped).
- **AC-T-25..29** (`uscha top` `o`): restated for `test-run` — no `--rerun-cmd` refusal, one
  `test-run` call instead of the human's command plus `snapshot`, and THREE spawn sites in the module
  where there were four.
- **AC-CT-*, AC-FR-*, AC-AU-03, AC-CO-11, AC-CX-01, AC-CU-01, AC-CR-06, AC-RD-03/07, AC-FA-05 and
  the readiness/phase blocks T29-T96**: their hand-placed report fixtures now become evidence
  through a declared command (`tests/_witness.py`: the engine's own inventory stashes them, a
  declared command restores them, and the engine's before/after hash sees them born). AC-SG-04 and
  AC-FF-05 declare their placeholder QA tools external: they relied on unverified steps counting in
  the window, which is B-F2.
- **AC-FU-02** names the first-use guide's `test-run` line out of scope, as it already did the
  `pytest` line: it executes the project's declared test command.
- `tools/release.py` AC-RL-03 expects the fake suite's JUnit report in X+1 beside the ledger and
  the changelog (it is evidence, as in the real ritual).
- The published subcommand count moves from 57 to 58 (`facts --write`), and both command-reference
  docs gain the `test-run` row.

## Honest limits

- **The declared command is trusted.** Provenance proves "this command ran at this tree and wrote
  these bytes", not that it tests anything. A command that echoes XML is attested — and it is a
  config diff a reviewer reads; the contradiction tripwire names its `test_loc == 0` shape.
- A concurrent writer during the run window is indistinguishable from the command.
- The tree is stamped BEFORE the run. A test command that writes source-extension files git does
  not ignore (generated code) makes its own run read stale; ignore them in git, or generate them
  outside the test command.
- `smoke-ingest` JSON and `log-gate --kind ci --ref` are still files or claims at a path.
- **Proposed for 2.11.0, not in this release:** the seal covering EVERY configured repo (in a
  multi-repo project `check-terminado` still seals repo #1 only — `phase` per repo is already
  correct, and the SKILL gates every repo, so the merge gate is honest; only the TERMINADO line is
  not), the gated-finding debt (a gated step re-logged clean with no source change still converges,
  A-F2), `--human`/`--note` and the agent-marker refusal on the human acts, and the PR hook.

## How it is pinned

`AC-GI-01..22, -31, -47` (smoke T173), each over real temp git repos the engine drives
under an isolated HOME: the A-F1 reproduction refused on all three surfaces, a SHIPPED PROBE
(AC-GI-16: the v2.9.0 engine reaches `pr-ready` on the same tree, the current one refuses), a
ledger the v2.9.0 engine wrote (AC-GI-14), the green path, commit-is-not-a-change, read-time
staleness, hand-overwritten and restored reports, the exit-code rule, NO_REPORT and the undeclared
command, the live-config derivation, the shell record, unattested coverage, the ritual and `o`,
`test_site: ci`, B-F1, B-F2, A-F3 per repo, and the SKILL text in both twins.

## Evidence

One full run of the final tree, empty HOME, parallel default (4 jobs on a 4-core Linux box,
coverage.py present): 408 s, exit 0, `RESULTADO: 464 ok · 0 fail`, `ACCEPTANCE: 408/409`. The one
criterion unmeasured is AC-DF-01, by design at a commit that touches the engine (ADR-041: it reads
measured at the ledger commit X+1). T173 was also run against the pre-fix engine and against the
v2.9.0 engine to confirm its red cases fail there. The six-cell CI run is the owner's to dispatch.

Suite: 464 checks · 0 fail; acceptance 408/409.
