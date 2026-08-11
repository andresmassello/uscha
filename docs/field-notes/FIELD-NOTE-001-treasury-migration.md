# FIELD NOTE 001 — Legacy treasury migration: what the ledger caught

**Status:** real project, anonymized. Numbers are exact and sourced from the project's `QA-LEDGER.json`, `ACCEPTANCE.md` and git history. Causal attributions that are inferred rather than recorded are labeled as such — see Limitations.
**Project shape:** migration of a legacy PHP treasury system (heavily customized legacy codebase) to Java/Spring Boot + SQL Server + React. Risk profile E (migration). 6 treasury modules, 12 ADRs, 12 constitution invariants, 21 acceptance criteria, 48 golden fixtures captured from the legacy system, 44 backend tests at the end, ~2 days of ledger activity across 5 squash-merged PRs.
**Honesty first:** this system is **not in production**. Final readiness 79.4 (IN PROGRESS); the two open criteria (AC-13, AC-14) are the human cutover gates, by design. This note is not "we shipped a treasury system in two days" — it is a record of every time the measured graph contradicted a claimed or apparent "done".

---

## The headline number

The agent checked **19 of 21** acceptance checkboxes. The engine accepted **16**.

The other 3 were checked but had no green test naming them — the ledger classifies them *narrated-only* and refuses to count them ("measured beats narrated: does not close"). A checkbox is a claim. Evidence is a test run the engine ingested. The gap between 19 and 16 is the entire thesis of the tool in one line.

## Five catches, from the ledger

**A — Readiness pinned at 49/NOT-READY through 10 consecutive green snapshots.** Tests grew 15 → 40 (all passing), coverage ~80%, across nearly 8 hours — and the readiness score did not move from 49 in 10 consecutive records. It jumped to 82.6 only immediately after the golden-diff gate was recorded (48/48 CLEAN). *Attribution inferred, numbers exact:* config had `golden_required=true` under risk profile E; the per-entry cap reason is not persisted (see Limitations and the engine follow-up below). Green tests were not allowed to stand in for the one piece of evidence the risk profile demanded.

**B — Constitution BLOCKER: money endpoints with no auth.** The treasury modules (ledger, invoices, accounts) were built and green when the constitution gate recorded 1 BLOCKER: INV-12, "no auth/authz on any endpoint yet". Readiness capped. Closed five iterations later with evidence: per-group `@PreAuthorize` on every module controller plus an `AuthzContractTest` proving allow/deny/admin-bypass. Tests-green said done; an inviolable invariant said no.

**C — Adversarial review over green code, round 1:** with `tests_passed=true`, a code-review pass reported 18 findings, **7 at or above the severity gate** (BLOCKER/CRITICAL/HIGH) on the money paths. 5 fixed, 8 deferred with rationale into `ISSUES-DEFERRED.md`.

**D — Adversarial review over green code, round 2:** again with tests green: 6 findings, 2 gated — **#1 BLOCKER: ETL not row-atomic** (one bad row aborted the entire migration) and **#2 HIGH: session fixation (CWE-384)**. Both fixed; 3 MEDIUM deferred with rationale.

**E — Stale evidence discarded; the score collapsed twice.** On re-recording readiness, the engine refused JUnit reports older than the code: the score dropped 82.6-range → **53.5**, then recovered to 82.6 only after re-running the suite on fresh evidence; the same pattern repeated the next day (**54.0** → 79.4). Two snapshots sit in the ledger marked `freshness=stale`. *Attribution inferred from the dip-then-recover pattern; scores exact.* Yesterday's green is not today's green.

## What tests-green alone would have shipped

Reading B, C, D together: a treasury system with **no authentication on money endpoints, a non-atomic migration ETL, and a session-fixation vulnerability — all with every test passing.** None of these were caught by the test suite. They were caught by the constitution gate and by adversarial review passes whose findings enter the same ledger as everything else. That is the practical difference between "the agent ran tests" and "the graph is measured".

## Limitations (read before quoting)

1. **Causes are not persisted per-entry.** The ledger records scores and iterations, not structured "cap applied" / "N stale reports discarded" events. Cases A and E carry exact numbers but inferred causes, and they are labeled so here.
2. **False dones are undercounted.** Only rejections that left a ledger event are counted. Agent self-corrections before recording state leave no trace; the true number of premature "done"s is probably higher.
3. **Review find-counts are self-reported** by the review pass into the ledger; they were not independently re-verified for this note.
4. **Coverage overstates confidence where it matters most:** 73.75% is JaCoCo line coverage on unit tests against H2, not SQL Server. Decimal/dialect fidelity of the money modules on the real engine is explicitly deferred (Testcontainers MSSQL in `ISSUES-DEFERRED.md`).
5. **Golden fixtures freeze the legacy system's behavior** (byte-deterministic capture, 46/47 identical across two runs, 1 declared scrub). The new system's fidelity is proven through AC-tagged tests, not byte-diff — "regressions caught by golden against the new system" is not a claim this project can make in byte terms.
6. **Squash-merges collapsed history:** 6 commits on main underrepresent real iteration counts; per-feature loop counts were not recorded.

## Engine follow-up this project generated

Limitation 1 is a product finding, not just a caveat: the engine should persist structured events for **readiness caps (with reason)** and **stale-evidence discards (with count)** so that the next field note's Cases A and E are recorded, not inferred. Filed as an improvement against the kit.

---

*Method: [Uscha](https://uscha.dev) — spec-driven development with a deterministic QA ledger where facts block and narration advises. This note was extracted read-only from the project's artifacts; the extraction request and its rules are published alongside the kit.*
