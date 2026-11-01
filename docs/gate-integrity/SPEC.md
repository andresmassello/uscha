# SPEC — gate integrity (governed by ADR-055..058)

> **Status (2.10.0):** ADR-055 is Accepted and its criteria, with the shipped parts of ADR-056
> (R1), ADR-057 (read-time `phase`) and ADR-058 (the SKILL text), are promoted to `ACCEPTANCE.md`
> as `AC-GI-01..22, -31, -47` (smoke T173). The rest of 056/057/058 stays Proposed for
> 2.11.0 and stays here, with its draft criteria.

> Placement: a multi-ADR feature, so the narrative SPEC and the FIXTURES live in
> `docs/gate-integrity/` while the ADRs are `Proposed` (repo rule 8; `docs/uscha-top/` is the
> model). The draft criteria are `AC-GI-nn`; they move into `ACCEPTANCE.md` only on acceptance.
> Every line number below is `uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py` at v2.9.0
> (3e5ca91); the `uscha-kit/skills/` twin is byte-identical.

---

## 1. The problem, with evidence

A blind two-judge audit of v2.9.0 plus an independent verifier reproduced one class of defect:
**the method can be made to lie** — the engine reaches `pr-ready`, 100% measured acceptance or
`SEALED` from records that do not describe the code. Four groups, each reproduced by command:

| G | Audit ids | What was reproduced | Where |
|---|---|---|---|
| G1 | A-F1 (blocker) | `mod.py = return 1/0`, zero test files, a hand-typed `junit.xml` (2 AC-named cases) and `coverage.xml` (97%), three bare `log-step`s → `phase --require pr-ready` exit 0, readiness `acceptance 100% (2/2)`, `check-terminado` SEALED. The snapshot itself printed `tests=2 ... test_loc=0` and nothing flagged it. | `tests_measured_green` 4034-4040, `_ac_tags` 975-1040, `_sealed_state` 10970-11119 |
| G2 | A-F2, B-F1, B-F2 | (a) `log-step --gated-reported 3`, then the same tool+iteration re-logged `0/0` with no source change → pr-ready. (b) ordered mode: the newest step is `unverified` (tool MISSING) with gated=3 → `_converged` falls back to an older verified clean step → CONVERGED. (c) window mode: three steps of a nonexistent tool, each printed "does not count toward convergence" → CONVERGED. | `_converged` 3938-3963, `cmd_log_step` 2771-2784, `_validate_iteration` 2201-2212 |
| G3 | A-F9, A-F3 | (a) `check-terminado` seals `repos[0]` only: a crash committed in repo #2 after its evidence → `SEALED (repo api)`. (b) `phase` reads the freshness stored at snapshot time: a source edit after the snapshot stays `pr-ready` while `readiness` on the same ledger says "STALE ... discarded". | `_sealed_state` 11007; `_derive_phase` 4034-4036; `_converged` 3973-3977 |
| G4 | A-F6 + field feedback | `escalate` then `resolve-escalation` with no actor → pr-ready; the devloop SKILL (SKILL.md:256-257) tells the AGENT to run it while `uscha-kit/README.md:61` says a human does; `curate` stamps the OS user (6366). Field: an agent opened a ready-for-review PR without running the gate while the ledger said `qa`, and stopped silently after a QA tool call was refused. | `cmd_resolve_escalation` 9402-9422; `cmd_curate` 6339-6375; SKILL Phase 6 |

The published claims these contradict: `README.md:70-72` ("backed by a report the agent did not
write"), `:141-142` ("Stale evidence ... is discarded, not honored"), `:131-132` (gated findings
"are fixed, the rest go to ISSUES-DEFERRED.md"), ADR-051:99-100 (an unverified step "does
**not** count toward `_converged`"), ADR-038 (the seal binds "the tracked repo's subtree").

Out of this release's scope (same audit, other classes, listed so nothing reads as forgotten):
A-F4 (clean-room command not recorded — folded into G1 as one field, §3.1), A-F5, A-F7/B-F6,
A-F8, A-F10, A-F11, A-F12, A-F13, A-F14, B-F3, B-F4, B-F5. Also out, though it is the G1 class:
`smoke-ingest` JSON and `log-gate --kind ci --ref` are still files/claims at a path (§7).

## 2. Principles

1. **A gate reads the world as it is now.** Every gate surface (`phase`, `readiness`,
   `check-terminado`, `top`) re-derives at read time through ONE function per fact; a stored
   verdict is a claim about a tree that has moved (ADR-038's own rule, applied to `phase`).
2. **Evidence is witnessed, not found.** The engine still never writes a report — the project's
   tool does — but it now runs the declared command and honors only reports that run wrote.
3. **Narration never closes a measured fact.** `log-step` counts stay narration (SKILL.md:24-26);
   they may describe, never discharge, a gated finding.
4. **Absence and contradiction are named.** No run, no stamp, no baseline → UNMEASURED with the
   reason, never a pass; a contradiction (tests without test code) is shown, not silently scored.
5. **A human act is declared, recorded, and kept out of the agent's hands** as far as the
   harness allows — and the record says exactly what it does and does not prove.

## 3. Design

### 3.1 G1 — report provenance (ADR-055)

**New subcommand** `qa_ledger.py test-run --repo R [--timeout SECONDS] [--json]`. One atomic
command: run, hash, ingest. There is **no `--run` flag**: an agent-chosen command is A-F4 again.

1. **Command source — one derivation.** `_op_test_command` (4836-4849): `repos[R].test_command`,
   else `defaults.test_command_<type>`, extended with ADR-051's live-config precedence (the live
   `uscha.config.json` beside the ledger wins per key, then the frozen copy). `_op_ci` keeps
   reading the same function. Nothing declared → exit 2 UNMEASURED ("no test command declared
   for R") — the kit never falls back to a type default the project did not write. `uscha init`
   already writes `defaults.test_command_<type>` for a RECOGNISED repo type (install-uscha.py
   ~1002-1005, under `if repo_type:`); an undetected type gets no command and hits F1-10 until
   the human declares one (§5).
2. **Inventory before.** The report set = `_junit_files_for(path, type)` (642) ∪ the paths
   `coverage()` probes (388-399). For each: absent, or `sha256` (`_sha256_evidence`, 7030).
   Plus a **tree stamp** (§3.5) and `_evidence_origin` (2363).
3. **Run.** A string runs through the platform shell (`/bin/sh`, `cmd.exe` on Windows — the
   `cleanroom` contract, 5368-5375); a JSON **list** runs as argv with no shell (the portable
   form). Output streams to the terminal; the record keeps a capped tail on failure only.
4. **Inventory after.** A report is **born of the run** iff it exists after and was absent
   before or its bytes changed. Unchanged bytes are not born of it, fail-closed (`unchanged`).
5. **Record** `ledger["test_runs"][]`: `{id: "TR-n", repo, started_at, ended_at, wall_ms,
   command, command_origin: live-config|frozen, shell: sh|cmd|argv, platform, commit, dirty,
   tree, exit_code, status: PASSED|FAILED|TIMEOUT|NO_REPORT, reports: [{path, kind:
   junit|coverage, sha256, sha256_eol}], unchanged: [paths]}`.
6. **Ingest.** The same command then calls `_snapshot` (2405); the step carries `via:
   "test-run"`. Exit 0 PASSED · 1 FAILED/TIMEOUT · 2 NO_REPORT or nothing declared.

**Snapshot stamping.** `_snapshot` (both entry points) stamps each report entry with `run:
"TR-n"` when its sha256 equals a born report of a recorded run of that repo, else `run: null`,
and adds `tests.provenance: {status: attested|partial|unattested, runs, unattested[]}`. A plain
`snapshot` of untouched run-born files stays attested (the release ritual re-snapshots).

**Run-anchored freshness (rule c).** An attested report is current iff the source-relevant
content of the tree now equals the content the run measured (§3.5, `_src_relevant` 771). This
is stricter than ADR-039's clock rule (a copied old report has a new mtime) and needs no mtime.
No git → ADR-039 rule (a) only, as today, but attestation is still required.

**The three read sites A-F1 passes through** — all three, in the first slice:
- `_derive_phase` (4031-4044): `tests_measured_green` additionally requires every JUnit report
  of the last snapshot to be attested, current (rule c), hash-identical on disk, and the run's
  `exit_code == 0` (a non-zero exit with green reports blocks: "the reports do not explain the
  failure"). The reason names the remedy: `test-run --repo R`.
- `_ac_tags` (975-1040): a JUnit file counts only if its current sha256 is a born report of a
  run whose tree is still current; otherwise it joins `stale` under its own label
  ("unattested: not born from a recorded test-run"). Acceptance reads UNMEASURED, not 100%.
- `_sealed_state` (10970): a report the last snapshot names with `run: null` is a measured
  break ("evidence not born from a recorded run: <path>"); a pre-2.10 snapshot with no
  `provenance` key is UNMEASURED (exit 2), the same posture as a pre-1.92 snapshot with no hash.

**Coverage.** Same witness, same hash rule. Readiness's coverage dimension and `check-coverage`
read a coverage report only when it is attested and current; otherwise UNMEASURED (exit 2 for
`check-coverage`, the ADR-049 code). Coverage still does not gate `pr-ready` — it never did.

**The contradiction tripwire.** `tests.executed > 0` with `loc.test_loc == 0` is printed by
`test-run`/`snapshot`, listed in `phase` evidence and in `readiness` facts as `contradiction`,
and is **advisory**: Rust inline `#[cfg(test)]` tests legitimately produce it (`_is_test_path`,
the documented rust limitation at 1170-1173), and a heuristic that can be wrong advises
(INV-ADVISORY-01's spirit). The gate is provenance.

**Clean-room (A-F4, folded).** The clean-room record gains `run` and `setup` — the same
provenance field, one line each; the `--run` contract of ADR-008 is unchanged.

### 3.2 Decisions for G1 (chosen marked ●)

| Question | Alternatives | Chosen and why |
|---|---|---|
| Where the command comes from | (a) `--run` per call; (b) config per repo, else per-type default the project wrote; (c) kit type default when undeclared | ● (b). (a) recreates G1 by choice of command; (c) is guessing, which ADR-008 refuses. A config edit is a diff a reviewer reads — INV-RIGOR-02 already says config is reviewed like code. |
| ADR-008 rejected "the engine runs `test_command_<type>`" | keep the rejection; amend it | ● amend (ADR-055). The objection was "a config file becomes a code-execution surface". The command is already in config and already read (`_op_ci`); only `test-run` executes it, it prints it first, and every read-only subcommand (`phase`, `readiness`, `top`, `check-terminado`) still executes nothing. |
| What "born of the run" means | mtime inside the run window; bytes changed; delete reports before running | ● bytes changed or newly present. mtime is forgeable by any later `touch`; deleting user files is not the engine's to do. Limit: an emitter that writes byte-identical output twice reads `unchanged` → UNMEASURED (FIXTURES F1-09). |
| Tests that only run in CI | (a) UNMEASURED forever; (b) a human "attests" a CI run; (c) import a CI artifact; (d) CI is the measuring site | ● (d), minimal: CI runs the SAME `test-run` + `phase --require pr-ready` against the committed ledger as a required check; `repos[R].test_site: "ci"` only changes the local wording ("the gate for R is the CI job") and makes the agent open a DRAFT. (b) is G1 with a signature; (c) needs network and a forge API the stdlib engine does not have — future work. Requires the project to commit `QA-LEDGER.json`. Q2 for the owner. |
| Legacy evidence (pre-2.10) | grandfather; fail closed | ● fail closed: old ledgers LOAD unchanged, but a snapshot without provenance never satisfies `pr-ready`, acceptance or the seal. Precedent: ADR-051 made a FACT block under every profile with no knob. Migration is one `test-run` per repo. Q1 for the owner. |
| `tests>0 ∧ test_loc==0` | block everywhere; block except rust; advisory | ● advisory (above). |

### 3.3 G2 — the gated-finding lifecycle (ADR-056)

> **Superseded for 2.11.0 (R2 only):** a TLA+ model check broke the R2 below with an honest
> agent; the redesign (witnessed reviews, Anchor, Memory) is `SPEC-2.11.0.md` §3, and the model is
> `models/`. R1 shipped in 2.10.0 as written.

**R1 — unverified never counts, and never hides (plain fixes of ADR-051:99-100 as written).**
- Ordered mode (3944-3957): the cycle is built from the **latest seen** step per listed tool,
  not the latest verified. If that step is `unverified`, the tool is blocked with its own
  reason; there is no fallback to an older verified step (B-F1).
- Window mode (3960-3963): any `unverified` step inside `agent[-k:]` blocks; and in both modes
  a tool whose newest step is `unverified` blocks (B-F2). `log-step`'s message (2783-2784)
  becomes true.

**R2 — a gated finding leaves only through measured movement (new decision).**
- `log-step` stamps the step with the tree stamp (§3.5) plus `deferred_sha256` of
  `ISSUES-DEFERRED.md` (absent → null).
- A step of tool T with `gated_reported = G > 0` opens a **debt** anchored at its **baseline**:
  the newest tree stamp recorded in that repo before the step (a `test-run`, `snapshot`,
  `log-step` or gate record) — the tree the tool reviewed. The SKILL order (fix → test →
  log-step, SKILL Phase 3 steps 1-3) means the gated step's own stamp already contains that
  pass's fixes, so the baseline, not the step, is the "before".
- The debt closes when a later step of T reports `gated_reported == 0` **and**, between the
  baseline and that step, the source-relevant content changed (a fix) or `ISSUES-DEFERRED.md`
  changed (a deferral). A deferral of a gated finding is shown in `readiness` as such ("2
  gated findings deferred, not fixed") — README:131-132 says gated findings are fixed.
- Self-reported `--fixed/--deferred` never close a debt. `log-step` warns at log time when it
  sees `--fixed > 0` with no measured movement.
- An open debt blocks `_converged` in both modes regardless of the window, named: "code-review:
  3 gated findings from step #12 still open — no source or ISSUES-DEFERRED.md change since the
  tree that pass reviewed". A revert (fix, then undo) reads as no movement — correct.
- No baseline (the gated step is the repo's first stamped record) → the debt closes only by
  movement after the step itself, and the reason says so.
- **Legacy steps** (no stamp, pre-2.10) keep their semantics (latest-wins) and are named once
  in `readiness` ("N pre-2.10 steps superseded without measured accounting"). Debts are
  computed for stamped gated steps only.
- Same `(tool, iteration)` re-log stays allowed (ADR-051's documented remedy is "re-log the
  step"); R2 judges it like any supersession.

Decision: R2 with measured movement ● vs. "fixed+deferred ≥ gated suffices" (the synthesis's
suggestion). Rejected: it lets narration discharge a measured fact, contradicting the two-tier
contract the SKILL already states. Limit stated in §6: movement proves the code moved, not that
it moved because of that finding — the re-review on moved code is what judges the fix.

### 3.4 G3 — every repo, at read time (ADR-057, amends ADR-038)

- **Phase re-derives** (A-F3): 4034-4036 and 3973-3977 stop reading
  `snapshots[-1].tests.freshness.status` and call the read-time derivation of §3.1 (one
  function, `_evidence_live(ledger, repo)`), the same one `_ac_tags` uses. Two surfaces, one
  answer — the 1.48.1 sin is the one ADR-039 already named.
- **The seal covers every configured repo** (A-F9): `_sealed_state` evaluates each repo
  (`integration` excluded) and aggregates: `ok` false if any false, else null if any null, else
  true. `check-terminado` prints one line per repo and exits on the aggregate (0/1/2 unchanged).
- **Contract** (`top --json` `terminado.sealed`, ADR-032): the top-level `{ok, reasons, commit,
  repo, note}` is the aggregate — `repo`/`commit` of the first non-sealed repo, `reasons`
  prefixed `[name]` — plus a `repos[]` detail key **only when more than one repo is
  configured**, so single-repo output and the golden frames stay byte-identical.
- **Nested repo paths** (a repo at `.` and another at `web/`): the dirty-check exemption is the
  union of every repo's named reports plus the ledger; the outer repo's seal also breaks on the
  inner repo's source changes, honestly (its path covers them).
- Behavior change named in the CHANGELOG: a multi-repo project where only repo #1 was ever
  snapshotted used to read SEALED; it now reads UNMEASURED (exit 2) naming the other repo.

### 3.5 Shared: the tree stamp and content-equivalence

`_tree_stamp(repo_path, type)` = `{commit, src_dirty: {path: blob-sha | "deleted"}}` over
`_src_relevant(_porcelain_paths(git status --porcelain -uall -- .))`, blobs from one
`git hash-object --stdin-paths` call. **Same source content** between stamps A and B iff, for
every path in `_src_relevant(git diff --name-only A.commit B.commit)` ∪ keys(A.src_dirty) ∪
keys(B.src_dirty), A's effective blob (dirty map, else `A.commit:path`) equals B's. Committing
a dirty tree therefore does NOT read as a change (a test-run on a dirty tree survives the commit
of exactly that tree). Built only from ADR-039's machinery (`_seal_git`, `_git_path_list`,
`_porcelain_paths`, `_src_relevant`); paths compared after `os.path.realpath` on both sides
(the 8.3 gotcha). No git → null → each caller's documented fallback.

### 3.6 G4 — human acts and the PR protocol (ADR-058)

- **(a) PR-request protocol (SKILL Phase 6, text).** When the human asks for a PR in any
  wording ("push and open the PR"), the agent runs `phase --require pr-ready` for every repo
  FIRST. Green → the Phase 6 checklist. Red → show the missing facts verbatim and ask ONE
  question: run the QA loop first (recommended), or open a DRAFT PR with the missing facts in
  its body. Never a ready-for-review PR while red. Pushing a branch is not opening a PR.
- **(b) The exception path** — Q3 for the owner. ● **Draft-only**: while red the agent opens
  drafts only; "ready for review" is the human's own click in the forge, which the forge
  authenticates — stronger than any `--human` string. The engine records the draft as an event
  `pr-opened-not-ready {repo, at, commit, phase, missing[], requested_by, note, origin: agent}`
  (ADR-044 vocabulary) that `readiness` and the retrospective surface and never count as
  normal. Alternative designed in ADR-058: `pr-override --human --note`, HEAD-pinned, that lets
  the hook allow a non-draft PR — it collides with INV-RIGOR-02's letter and needs a
  CONSTITUTION carve-out.
- **(c) PreToolUse hook** `uscha-kit/hooks/guard-pr-gate.py` (Claude Code only): blocks `gh pr
  create` without `--draft/-d`, `gh pr ready`, and forge-MCP create/update calls with `draft`
  not true, when the read-only `qa_ledger.py pr-gate --cwd <cwd>` says no repo mapped to the
  cwd is pr-ready. No `QA-LEDGER.json` up the cwd → ALLOW (the hook is global). Ledger found
  but engine missing or erroring → BLOCK, naming it (the golden hook's fail-closed posture).
- **(d) Proactive report (SKILL Phase 3).** When a QA tool call cannot run (permission denied,
  tool missing, crash), the agent says so at that moment: which step, that the loop is
  incomplete, that the repo cannot reach pr-ready until it runs — and logs no step for it.
- **(e) Human acts.** `resolve-escalation` and the `--resolve` of `spec-doubt`,
  `spec-change-request`, `production-finding` — exactly the four branches that lift
  `escalated` in `_derive_phase` (4010-4029) — require `--human NAME --note TEXT`, record
  `resolved_by`, `resolution_note`, `human_declared: true`, and refuse when the process
  environment carries a known agent-shell marker (`CLAUDECODE=1`, measured in Claude Code's
  Bash tool on 2026-10-20). The SKILL says STOP and ask the human to run it (SKILL.md:256-257
  and :849 rewritten). `curate` keeps its OS-user default for the `uscha top` VERDICTS flow but
  records `human_source: flag|os-user`.
- **Why no "smoke test of agent output"**: an agent's reply is sampled — a test over it is
  flaky or pins one model's phrasing. What is deterministic is what the agent receives (SKILL
  text, pinned by assertions over both twins), what bounds it (the hook, pinned by JSON payload
  probes), and what the engine records (pinned by fixtures).

## 4. Backward compatibility

- Every pre-2.10 ledger **loads unchanged**: `test_runs` absent = `[]`; snapshots without
  `provenance`, steps without `tree`, escalations without `resolved_by` are read as legacy.
- What changes on upgrade, named in the CHANGELOG: `phase` is not `pr-ready`, acceptance reads
  UNMEASURED and `check-terminado` exits 2 until one `test-run` per repo; window/ordered
  convergence refuses unverified steps; a multi-repo seal now covers every repo.
- The integrity checksum covers the new keys through the normal `_save`; no schema bump.
- `uscha top`'s `o` rerun (`_snapshot_call`, uscha_top.py 1050; `--rerun-cmd`, 1388) calls
  `test-run` instead of the human's command plus `snapshot`; `--rerun-cmd` is accepted and
  ignored with a notice for one release (ADR-037 amended by ADR-055).

## 5. Migration note for existing projects

1. Make sure `uscha.config.json` declares the test command (`repos[].test_command` or
   `defaults.test_command_<type>`); prefer a JSON list on mixed Windows/POSIX teams. Note the
   shipped `test_command_dotnet` uses `$PWD`, which `cmd.exe` does not expand.
2. Run `qa_ledger.py test-run --repo <R>` once per repo; replace any "run tests, then
   `snapshot`" step in scripts or CI with it.
3. CI-only suites: run `test-run` + `phase --require pr-ready` in CI against the committed
   ledger; declare `test_site: "ci"`.
4. Human acts now need `--human` and `--note`, from a human's terminal.
5. **This repo**: the root config declares no test command (`_op_test_command` resolves None
   for `uscha`), so `repos[0].test_command` must become `bash uscha-kit/tests/smoke-engine.sh`
   (what CI runs, `.github/workflows/smoke.yml:126`), and `tools/release.py` steps 4-5 (suite at
   513, `snapshot` at 564) become one `test-run` — or the dogfooding ledger reads unattested.

## 6. Honest limits — what remains trusted, and why

- **The declared command.** Provenance proves "this command ran at this tree and wrote these
  bytes", not that the command tests anything. A command that `echo`es XML is attested; it is
  also a config diff a reviewer reads, and the tripwire names its `test_loc == 0` shape.
- **A concurrent writer** during the run window (a background process) is indistinguishable
  from the command. The agent waits on the call; a deliberate race is not detected.
- **Narration stays narration.** Step counts, `--fixed`, finding fingerprints: recorded, never
  closing. Movement proves the code moved, not why.
- **`--human` is declared, not authenticated.** It proves a name was typed and, with the marker
  check, that the call did not run in a shell carrying a known agent marker. An agent can unset
  the variable — a deliberate act, visible in its command text — and Codex/pi/other harnesses
  have no marker the engine knows (UNMEASURED there). The forge's own "ready for review" click
  is the only authenticated human act in this design.
- **The hook exists only on Claude Code**, inspects text, and misses `gh api` calls and PRs
  opened in a browser. Codex/pi rely on the SKILL.
- **Not covered**: `smoke-ingest` JSON, `log-gate --kind ci --ref`, a stripped `integrity` key
  (A-F10, disclosed by design).

## 7. Delivery plan

Estimates are changed lines per copy; the engine and SKILL twins double the raw diff.

| Area | Engine | Suite | Docs/SKILL/other | Total |
|---|---|---|---|---|
| G1 provenance (+G3a phase re-derivation, +A-F4 field) | ~380 | ~550 (new T-block + migrating ~48 hand-written JUnit fixtures and the 14 `--require pr-ready` sites to `test-run`) | ~150 (README re-claims, SKILL, release.py, root config, uscha_top `o`) | **~1,080** |
| G3b seal every repo | ~120 | ~180 | ~40 | **~340** |
| G2 R1 (plain fixes) | ~25 | ~80 | ~10 | **~115** |
| G2 R2 (supersession) | ~130 | ~220 | ~30 | **~380** |
| G4 SKILL text (a, d, e-text) | — | ~60 (pinned assertions) | ~70 | **~130** |
| G4 engine + hook (b, c, e) | ~210 | ~260 (incl. payload probes) | ~90 (installer, doctor, CONSTITUTION if Q3=A) | **~560** |

**Recommendation — two releases, the blocker first:**
- **2.10.0 "witnessed evidence"** ≈ 1,330: G1 + G3a + G2-R1 + G4 SKILL text. Closes A-F1
  everywhere (phase, acceptance, seal), A-F3, B-F1, B-F2, and the field behavior. G3a is the
  same lines G1 touches; R1 is a plain fix of a written claim; the SKILL text costs no engine.
- **2.11.0 "nothing vanishes"** ≈ 1,280: G3b + G2-R2 + G4 engine/hook. They share the tree
  stamp G1 introduces and all read "which records the gate may skip".
- Residual between them: in a multi-repo project `check-terminado` still seals repo #1 only
  (A-F9). `phase` per repo is already correct in 2.10.0, and the SKILL tells the agent to gate
  every repo, so the merge gate is honest; only the TERMINADO line is not.
- Lighter alternative if 2.10.0 must be smaller: G1 + G3a only (~1,080); R1 and the SKILL text
  slide to 2.11.0 and B-F2 (high, the window default) stays open one more release.
- Shipping costs that ride with G1/G3 and are already inside the estimates: the `## Status:`
  lines AND INDEX rows of the amended ADR-008, -037, -038 and -039 move together (AC-DC-04
  compares them verbatim); byte-identity pins that legitimately move (AC-FR-*, AC-FA-03,
  AC-FR-06, AC-CT-*) are listed in the CHANGELOG, not discovered red; `test-run` (2.10.0) and
  `pr-gate` (2.11.0) move the published subcommand count through `facts --write` (I3).
- Why not all four at once (~2,600): one ritual with the largest suite migration in the kit's
  history and two unrelated risk surfaces; a red cell would hold the blocker fix hostage.

## 8. Questions for the owner

1. **Legacy evidence fails closed** (pre-2.10 snapshots never satisfy pr-ready/acceptance/seal
   until one `test-run`)? *Recommended: yes* — it is a FACT, ADR-051 is the precedent, and a
   grandfather path is exactly the hand-written XML A-F1 used.
2. **CI-only suites**: CI as the measuring site (`test_site: "ci"`, drafts locally), or leave
   them UNMEASURED in 2.10.0 and design artifact import later? *Recommended: CI as the
   measuring site* — no new trust, ~25 lines.
3. **Exception path for a red PR**: draft-only (the forge click is the human act) or a recorded
   `pr-override --human --note` that allows a non-draft PR (needs an INV-RIGOR-02 carve-out)?
   *Recommended: draft-only* — authenticated by the forge, constitution untouched.
4. **Slicing**: 2.10.0 = G1+G3a+R1+SKILL text, 2.11.0 = the rest? *Recommended: yes.*
