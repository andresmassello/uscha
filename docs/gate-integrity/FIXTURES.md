# FIXTURES — gate integrity (governed by ADR-055..058)

> **Status (2.10.0):** the G1 rows (F1-01..18 except F1-13's Windows-only half, measured by the
> Windows CI cells), F2-02, F2-03, F2-10, F3-02 and F4-15 are measured by smoke T173 and promoted
> as `AC-GI-*`. The remaining rows belong to the parts still Proposed for 2.11.0.

Concrete scenarios: input (config / ledger / tree) → commands → expected engine output and exit
code. Each row names the draft criterion it feeds (`AC-GI-nn`, promoted to `ACCEPTANCE.md` only
on acceptance). Rows marked **RED (audit)** are the v2.9.0 reproductions that passed and must now
fail closed; rows marked **GREEN** are the happy paths that must stay green. All repos are
generic (`backend-api`, `mobile-app`, repo rule 4); every fixture is a real temp git repo the
ENGINE drives, like T146. `Q` = `python qa_ledger.py`.

Common base (`base-py`): `uscha.config.json` = `{"defaults": {"test_command_python": <CMD>,
"qa_tools_order": ["code-review", "judgment-day", "improve"]}, "repos": [{"name": "backend-api",
"path": "backend-api", "type": "python"}]}`; `backend-api/mod.py`; one commit; `Q init`. `<CMD>`
is a stdlib `python` script under `backend-api/` (`run_tests.py`) that runs real `unittest` cases
and writes `reports/junit.xml` + `reports/coverage.xml` — the "real run" every GREEN row uses.
QA tools resolve as `declared-external` (`qa_tools_external`) so no harness is needed.

---

## 1. G1 — report provenance (ADR-055)

| ID | Kind | Setup → commands | Expected |
|---|---|---|---|
| F1-01 | **RED (audit A-F1)** | `mod.py = return 1/0`, no test file; hand-write `reports/junit.xml` (2 cases `test_AC_01_x`, `test_AC_02_y`) and `coverage.xml` (97%); `Q snapshot`; three bare `log-step`s; commit | `phase --require pr-ready` exit 1, reason names "not born from a recorded test-run" and `test-run --repo backend-api`; `readiness` acceptance UNMEASURED (0/2 measured), the two files listed as `unattested`; `check-terminado` exit 1 "evidence not born from a recorded run: reports/junit.xml" (AC-GI-01, -02, -03) |
| F1-02 | **RED (audit A-F1)** | as F1-01 | `snapshot` prints `contradiction: tests=2 executed with test_loc=0`; `phase` evidence and `readiness` facts list it; it does not change the exit code by itself (AC-GI-04) |
| F1-03 | GREEN | `base-py`, real tests; `Q test-run --repo backend-api`; three clean `log-step`s | `test-run` exit 0, record `TR-1` with `command`, `command_origin: live-config`, `shell`, `exit_code 0`, two `reports` with sha256; snapshot reports carry `run: "TR-1"`, `provenance.status: attested`; `phase --require pr-ready` exit 0; acceptance measured from the run (AC-GI-05) |
| F1-04 | GREEN | F1-03, then `git commit` of the same tree (no source change), `Q snapshot` | still attested, still current: committing the tree the run measured is not a change (§3.5) (AC-GI-06) |
| F1-05 | RED | F1-03, then edit `mod.py` (uncommitted) | `phase` exit 1 "stale: source changed since run TR-1: backend-api/mod.py" WITHOUT a new snapshot (re-derived at read time); `readiness` agrees (AC-GI-07) |
| F1-06 | RED | F1-03, then overwrite `reports/junit.xml` by hand (same name, new bytes) | `phase` exit 1 "evidence changed since snapshot"; `_ac_tags` drops it as unattested; seal exit 1 "altered after ingest" (AC-GI-08) |
| F1-07 | RED | F1-03, then copy an OLD run's `junit.xml` (TR-1) back after a source change and a newer run TR-2 | the copy has a fresh mtime but its run's tree is not current → stale; ADR-039's clock rule no longer rescues it (AC-GI-07) |
| F1-08 | RED | `<CMD>` exits 1 but its reports read 0 failures (a build step after the tests failed) | `test-run` exit 1 `FAILED`; `phase` exit 1 "the test command exited 1 while its reports read green — the reports do not explain the failure" (AC-GI-09) |
| F1-09 | UNMEASURED | `<CMD>` = a command that writes nothing (or rewrites byte-identical XML) | `test-run` exit 2 `NO_REPORT`, the files listed under `unchanged`; known limit of the bytes rule, named (AC-GI-10) |
| F1-10 | UNMEASURED | no `test_command` declared anywhere (frozen nor live) | `test-run` exit 2 "no test command declared for backend-api"; nothing runs; no type default is guessed (AC-GI-10) |
| F1-11 | refusal | `Q test-run --repo backend-api --run "echo x"` | argparse error: `--run` does not exist on `test-run` (AC-GI-11) |
| F1-12 | GREEN | live `uscha.config.json` changes `test_command_python` after `init` | `test-run` uses the live value, records `command_origin: live-config`; `operability`'s `ci` check reads the same value (one derivation) (AC-GI-11) |
| F1-13 | Windows | `<CMD>` as a string on Windows | runs through `cmd.exe`, `shell: cmd` recorded; a list-form `<CMD>` records `shell: argv` and runs identically on all three OS cells (AC-GI-12) |
| F1-14 | Windows | the shipped `test_command_dotnet` (uses `$PWD`) under `cmd.exe` | no report born → `NO_REPORT` exit 2 with the `cmd.exe` shell named; never a false PASS (AC-GI-12) |
| F1-15 | coverage | hand-written `coverage.xml` after a real `test-run` that produced none | `readiness` coverage UNMEASURED "coverage report not born from a recorded run"; `check-coverage` exit 2 (AC-GI-13) |
| F1-16 | legacy | a v2.9.0 ledger (snapshots without `provenance`, no `test_runs`) | loads; `phase` exit 1 "no recorded test-run (evidence predates 2.10.0) — run test-run"; `check-terminado` exit 2 UNMEASURED; after one `test-run`, F1-03's verdicts (AC-GI-14) |
| F1-17 | ritual | this repo with `repos[0].test_command = "bash uscha-kit/tests/smoke-engine.sh"` | `test-run --repo uscha` streams the suite's output, records it, snapshots; `readiness --record` reads attested (AC-GI-15) |
| F1-18 | top `o` | `uscha top`, press `o` | the TUI calls `test-run` for the first repo (one process per keypress); `--rerun-cmd` given → a notice, not executed (AC-GI-15) |

## 2. G2 — the gated-finding lifecycle (ADR-056)

Base: F1-03 (attested, pr-ready).

| ID | Kind | Commands | Expected |
|---|---|---|---|
| F2-01 | **RED (audit A-F2)** | `log-step --tool code-review --iteration 2 --reported 3 --gated-reported 3`; then the same tool + iteration with `0/0`, no file touched | `converged` NOT converged: "code-review: 3 gated findings from step #N still open — no source or ISSUES-DEFERRED.md change since the tree that pass reviewed"; `phase` exit 1 (AC-GI-20) |
| F2-02 | **RED (audit B-F1)** | ordered mode; iteration 1 of `aud-tool` logged with its `SKILL.md` present; `SKILL.md` removed; iteration 2 `--gated-reported 3` → `source=MISSING` | NOT converged: "latest aud-tool step #N is unverified (tool MISSING at log time)"; no fallback to iteration 1; `phase` exit 1 (AC-GI-21) |
| F2-03 | **RED (audit B-F2)** | window mode (no `qa_tools_order`); three `log-step --tool nonexistent-tool` | NOT converged: unverified steps in the window; the printed "does not count toward convergence" is now true (AC-GI-22) |
| F2-04 | GREEN | gated=3 pass during which the agent fixes `mod.py` (source moves between the baseline and the step), `test-run`, then a clean pass (gated 0, files 0) | CONVERGED: the debt closed by measured movement since the baseline (AC-GI-23) |
| F2-05 | GREEN | gated=2, the agent adds two entries to `ISSUES-DEFERRED.md`, clean pass | CONVERGED; `readiness` prints "2 gated findings deferred, not fixed" (AC-GI-24) |
| F2-06 | RED | gated=3 with `--fixed 3` and NO source change, then a clean pass | `log-step` warns "fixed=3 but no source-relevant change since the baseline"; debt open; NOT converged (AC-GI-25) |
| F2-07 | RED | fix during the gated pass, then `git checkout -- mod.py` (revert), clean pass | debt open: content equals the baseline — a revert is no fix (AC-GI-25) |
| F2-08 | edge | the gated step is the first stamped record (no `test-run`/snapshot before) | debt closes only by movement after the gated step; the reason says "no baseline before step #N" (AC-GI-26) |
| F2-09 | legacy | v2.9.0 ledger with a gated step superseded by a clean one (no stamps) | loads; converges as in 2.9.0; `readiness` names "1 pre-2.10 step superseded without measured accounting" (AC-GI-27) |
| F2-10 | GREEN | window mode, every step verified and clean, k=3 | CONVERGED exactly as 2.9.0 (no regression) (AC-GI-22) |

## 2b. G2 R2' — witnessed reviews, Anchor, Memory (ADR-056 as redesigned in SPEC-2.11.0.md)

The §2 rows F2-01 and F2-04..F2-09 were written for the R2 that `models/GatedDebt.tla` broke; they
are superseded by the rows below (F2-02, F2-03 and F2-10 shipped in 2.10.0 as AC-GI-21/-22). The
first four rows are the TLC paths, replayed against the real engine as RED cases. Base: `base-py`
with a declared test command, every QA tool declared external; "review(T)" = `review-start --repo
backend-api --tool T --iteration N`, then the agent's tool pass, then `log-step ... --review RV-n`.

| ID | Kind | Commands | Expected |
|---|---|---|---|
| F2-11 | **RED (TLC M1)** | `test-run` (v0); review(T) flags v0 (gated 1); fix to v1; `log-step --review` gated 1; review(T) on v1 clean, logged; `git checkout` back to v0; `test-run` | `phase` exit 1: "the last review ... saw a different source than the tree now"; the shipped probe (v2.10.1 engine, same tree, steps logged without `--review`) reaches `pr-ready` (AC-GI-50) |
| F2-12 | **RED (TLC M2)** | review(T) starts on v1 (clean); the agent reverts to v0 BEFORE logging; logs the clean step | the step carries the REVIEWED tree (v1): Anchor refuses on v0; the open debt from a v0 flag stays open (AC-GI-51) |
| F2-13 | **RED (TLC Lies)** | after F2-11's flag on v0, a `review-start` on v0 then `log-step --review ... --gated-reported 0` (a clean pass that contradicts the flag) | Memory: "reports 0 gated findings on exactly the content step #n flagged" -- NOT converged (AC-GI-52) |
| F2-14 | **RED (A-F2)** | gated step, then the same tool+iteration re-logged 0/0 with no `--review` | the re-log is unwitnessed: it never counts and never hides; the debt stays open (AC-GI-53) |
| F2-15 | GREEN (vacuity) | review flags v0; fix to v2; `test-run`; log gated; review v2 clean; log clean | CONVERGED, `pr-ready` (AC-GI-54) |
| F2-16 | GREEN (deferral) | review flags v0; add an entry to `ISSUES-DEFERRED.md`; review v0 again, logged clean | CONVERGED; `readiness` prints "1 gated finding deferred, not fixed"; Memory does not fire (the deferred file differs) (AC-GI-55) |
| F2-17 | GREEN | a docs-only commit after convergence | still CONVERGED (Anchor compares source-relevant content only) (AC-GI-56) |
| F2-18 | legacy | a v2.10.1 ledger (steps without `reviewed`) | loads; converges as in 2.10.1 until a witnessed step of the tool exists; `readiness` names "N steps predate witnessed reviews" (AC-GI-57) |
| F2-19 | refusal | `log-step --review RV-9` naming an unknown, closed, or other-tool review | recorded unwitnessed, named; never counts (AC-GI-58) |

## 3. G3 — every repo, at read time (ADR-057)

Base `two-repo`: repos `backend-api` (`backend-api/`) and `mobile-app` (`mobile-app/`), both
python, both F1-03 green and attested, everything committed.

| ID | Kind | Commands | Expected |
|---|---|---|---|
| F3-01 | **RED (audit A-F9)** | commit `return 1/0` into `mobile-app/m.py` after its evidence | `check-terminado` exit 1, line `mobile-app: UNSEALED — stale seal: source changed since snapshot ...: mobile-app/m.py`; aggregate UNSEALED (AC-GI-30) |
| F3-02 | **RED (audit A-F3)** | same, plus an uncommitted edit | `phase --repo mobile-app --require pr-ready` exit 1 (re-derived, no snapshot needed); `readiness` says the same (AC-GI-31) |
| F3-03 | GREEN | `two-repo` untouched | `check-terminado` exit 0, one SEALED line per repo; `top --json` `terminado.sealed.ok: true` with `repos[]` of two (AC-GI-32) |
| F3-04 | UNMEASURED | `two-repo` where `mobile-app` was never snapshotted | exit 2, `mobile-app: UNMEASURED — no snapshot recorded yet` (used to read SEALED) (AC-GI-33) |
| F3-05 | contract | single-repo `base-py`, sealed and unsealed states | `top --json` `terminado.sealed` byte-identical to 2.9.0 (no `repos` key); the golden frames of AC-CT-10 / AC-T-24 unmoved (AC-GI-34) |
| F3-06 | nested | repo `backend-api` at `.` and `mobile-app` at `mobile-app/`; `mobile-app`'s reports | not counted as `backend-api` dirt (exemption union); a source change in `mobile-app/` breaks both seals, named per repo (AC-GI-35) |
| F3-07 | GREEN | commit touching only docs after the snapshot | sealed with ADR-039's `note`, per repo (no regression) (AC-GI-36) |

## 4. G4 — human acts and the PR protocol (ADR-058)

Engine rows run under `env -u CLAUDECODE` unless stated. Hook rows pipe JSON payloads to the
hook on stdin and read the exit code — nothing is executed.

| ID | Kind | Input | Expected |
|---|---|---|---|
| F4-01 | **RED (audit A-F6)** | `escalate`, then `resolve-escalation --repo backend-api` | exit 2 "resolve-escalation is a human act: --human NAME and --note TEXT are required"; phase stays `escalated` (AC-GI-40) |
| F4-02 | GREEN | `resolve-escalation --repo backend-api --human "R. Owner" --note "ADR-012 written"` | exit 0; record carries `resolved_by`, `resolution_note`, `human_declared: true`; `readiness`/retrospective print who and when (AC-GI-40) |
| F4-03 | tripwire | F4-02 with `CLAUDECODE=1` in the environment | exit 2 "refused: this shell carries an agent marker (CLAUDECODE) — ask the human to run it in their own terminal"; nothing written (AC-GI-41) |
| F4-04 | same family | `spec-doubt --resolve`, `spec-change-request --resolve`, `production-finding --resolve` without `--human/--note`, and with `CLAUDECODE=1` | each refused like F4-01 / F4-03 (AC-GI-41) |
| F4-05 | legacy | v2.9.0 ledger with a resolved escalation lacking `resolved_by` | loads; shown as "resolved (actor not recorded, pre-2.10)" (AC-GI-42) |
| F4-06 | curate | `curate` with and without `--human` | records `human_source: flag` / `os-user`; behavior otherwise unchanged; `uscha top` VERDICTS still works (AC-GI-42) |
| F4-07 | hook RED | payload `Bash` `gh pr create --title x`, cwd in `base-py` whose phase is `qa` | hook exit 2, message lists the missing facts and the two legitimate paths (QA loop, or a DRAFT) (AC-GI-43) |
| F4-08 | hook RED | `gh pr ready 12` under the same ledger | exit 2 — draft-then-ready is not a bypass (AC-GI-43) |
| F4-09 | hook GREEN | `gh pr create --draft ...` (and `-d`) under the same ledger | exit 0 (AC-GI-44) |
| F4-10 | hook GREEN | `gh pr create ...` with phase `pr-ready` for the mapped repo | exit 0 (AC-GI-44) |
| F4-11 | hook GREEN | any payload in a directory tree with no `QA-LEDGER.json` | exit 0 — the hook is global and must not touch other projects (AC-GI-45) |
| F4-12 | hook fail-closed | ledger present, engine absent; and an unparseable payload | exit 2 naming the cause (AC-GI-45) |
| F4-13 | hook MCP | `mcp__github__create_pull_request` with `draft: false` / absent, phase `qa` | exit 2; with `draft: true` → exit 0 (AC-GI-43) |
| F4-14 | event | the agent records `pr-opened-not-ready` after a human-chosen draft | event with `commit`, `phase`, `missing[]`, `requested_by`, `origin: agent`; `readiness` prints it as an exception, never as normal; phase unchanged (AC-GI-46) |
| F4-15 | SKILL pin | both `SKILL.md` twins | contain the PR-request protocol (gate first; one question; never ready-for-review while red), the proactive "a QA step could not run" rule in Phase 3, and "STOP and ask the human" at the old :256-257 and :849 sites; the twins stay byte-identical (AC-GI-47) |
| F4-16 | install | Claude target install / uninstall | registers / removes `guard-pr-gate.py` beside the golden hook; `doctor` reports `pr_guard: enforced` on Claude, `advisory` on every Agent-Skills target (AC-GI-48) |

## 5. Determinism notes

- Run timing is recorded but never asserted; assertions read status, exit codes and hashes.
- `<CMD>` scripts write fixed XML bytes from real test outcomes, except where a row needs a
  byte change (F1-09 pins the identical-bytes limit on purpose).
- The `CLAUDECODE` marker is stripped by the harness for every engine row except F4-03/F4-04;
  the suite itself runs under Claude Code on the maintainer's box and must not inherit it.
