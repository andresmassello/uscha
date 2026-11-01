# SPEC 2.11.0 — "nothing vanishes" (governed by ADR-056, -057, -058; Proposed)

> Placement: the 2.11.0 slice of the gate-integrity feature (`SPEC.md` is the whole design;
> 2.10.0 shipped G1, G3a, G2-R1 and the G4 SKILL text). This file supersedes `SPEC.md` §3.3 R2,
> which a model check broke (§2), and narrows the rest of §3.4 and §3.6 to what 2.11.0 builds.
> Line numbers are `uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py` at v2.10.1 (9e9f7ea).
> Draft criteria use `AC-GI-50..` (R2'), `AC-GI-30, -32..36` (seal) and `AC-GI-40..46, -48` (human
> acts and hook) so that none collides with the 24 criteria 2.10.0 shipped.

---

## 1. What 2.11.0 closes

| Gap | Audit id | State at v2.10.1 |
|---|---|---|
| A gated step re-logged clean with no source change converges | A-F2 | open |
| QA steps are not anchored to the tree on disk: review clean, revert to the flagged code, re-test -> `pr-ready` | model finding M1 (§2) | open, and reachable with an honest agent |
| `log-step` stamps the tree it is LOGGED at, not the tree the tool REVIEWED | model finding M2 (§2) | open (there is no stamp yet) |
| `check-terminado` seals `repos[0]` only | A-F9 | open, named in CHANGELOG-2.10.0 |
| `resolve-escalation` and the three `--resolve` commands take no actor and run from the agent's shell | A-F6 | SKILL text shipped (2.10.0); engine open |
| An agent opens a ready-for-review PR while the gate is red | field | SKILL text shipped (2.10.0); hook open |

## 2. Why §3.3 R2 is replaced — the model check

`models/GatedDebt.tla` models R2 exactly as `SPEC.md` §3.3 writes it, for one QA tool in one repo,
and checks one rule the reader agrees to:

> **NoFlaggedBugShips** — `pr-ready` never holds on a code version the LEDGER knows a QA tool
> flagged (a `log-step` with gated findings for that tree), unless the finding was deferred.

TLC (v1.7.4; 3 code versions, at most 5 records) breaks it **with an honest agent**, shortest path
7 steps (`models/chart-as-specified.mmd`):

1. `test-run` measures v0. 2. The tool flags v0. 3. The agent fixes (v1). 4. It logs the gated
step. 5. The tool reviews v1: clean. 6. It logs the clean step. 7. **It reverts to v0.** The run
measured v0, so tests read current again; the latest QA step is clean; `pr-ready`.

Two causes, both structural:

- **M1 — convergence is not anchored to the tree on disk.** Nothing compares the tree the latest
  QA pass reviewed with the tree `phase` is asked about. 2.10.0 re-derives the freshness of TESTS
  at read time (ADR-055); the same principle was never applied to QA REVIEWS. This gap exists in
  2.10.1 today, independently of R2.
- **M2 — a step carries the tree it was LOGGED at, not the tree the tool REVIEWED.** The SKILL
  order (review, fix, test, log) makes those two trees differ on every pass that fixes something,
  and §3.3 tried to recover the "before" with a heuristic baseline (the newest earlier stamp, or
  the step itself when there is none). With no earlier stamp the "before" is the already-fixed
  tree, so a revert counts as movement and closes the debt.

What TLC does not break at the same bounds is three pieces together (§3): **Witness** + **Anchor**
(honest agent: 761,424 distinct states, no violation) + **Memory** (an agent that logs counts no
review produced: 1,607,868 distinct states, no violation). The vacuity control
(`NeverFixedAndReady`, which must break) breaks: a legitimate fix and a deferral still reach
`pr-ready`, so the green is not vacuous. Limits of the check are in §6.

## 3. Design — R2' (ADR-056, redesigned)

### 3.1 Witness: the engine records the tree a review STARTS on

- New subcommand **`qa_ledger.py review-start --repo R --tool T --iteration N`**: records
  `{id: "RV-n", repo, tool, iteration, at, tree, deferred_sha256}` in `ledger["reviews"]` and
  prints the id. `tree` is ADR-055's `_tree_stamp` (2512); `deferred_sha256` is the sha256 of
  `ISSUES-DEFERRED.md` (null when absent). It runs nothing and reviews nothing: it is the
  `test-run` principle (the engine stamps what it can see) applied to the part of a QA pass the
  engine can witness — the moment the tree was handed to the reviewer.
- `log-step` gains **`--review RV-n`**. A step that names an open review of the same repo, tool
  and iteration carries that review's `tree` and `deferred_sha256` as the **reviewed** state; the
  review is closed by that step (one step per review). The step keeps its own log-time stamp
  beside it (useful to the retrospective, never read by the gate).
- A step with no `--review`, or naming an unknown, closed or mismatched review, is recorded
  **unwitnessed** and treated like an unverified step (R1, shipped): it never counts and never
  hides. Legacy steps (pre-2.11, no `reviewed` key) keep their 2.10 semantics and are named once in
  `readiness` ("N steps predate witnessed reviews").

### 3.2 Anchor: convergence is about the tree on disk now

`_converged` (4530) additionally requires, for every tool in the cycle (ordered: each listed tool;
window: each tool of the window), that its latest witnessed step **reviewed** a tree with the same
source-relevant content as the tree now (ADR-055's `_src_moved` (2554), at read time — the
`_Witness` memoisation (2688) is reused). Otherwise: `"code-review: the last review (RV-7, step
#12) saw a different source than the tree now: backend-api/mod.py -- run the review again"`.
Committing exactly the reviewed tree is not a change (§3.5 of SPEC.md); a docs-only change is not
a change; a revert to a different tree is.

### 3.3 The debt, on reviewed trees

- A witnessed step of tool T with `gated_reported = G > 0` opens a debt on its **reviewed** state
  (tree + `deferred_sha256`). The reviewed state IS the "before" — no heuristic baseline.
- The debt closes when a later witnessed step of T reports `gated_reported == 0` on a reviewed
  state that differs from the debt's: different source-relevant content (a fix) or a different
  `ISSUES-DEFERRED.md` (a deferral; `readiness` prints "N gated findings deferred, not fixed").
- An open debt blocks convergence in both modes, outside any window, named with tool, count, step
  and review id. `--fixed` / `--deferred` never close a debt (narration, SKILL two-tier contract).

### 3.4 Memory: a clean verdict cannot contradict the record

A witnessed clean step of T whose reviewed state (source content AND `ISSUES-DEFERRED.md`) equals
the reviewed state of an earlier gated step of T counts for nothing: `"code-review: step #15
reports 0 gated findings on exactly the content step #12 flagged with 3 -- the record contradicts
itself; fix, or defer in ISSUES-DEFERRED.md"`. This is what holds against an agent that narrates a
clean pass it never ran (the model's `Lies`); its cost is §5 Q6.

### 3.5 What R2' does NOT do

It does not prove the review ran (only that a tree was handed to it, and that the narrated result
is consistent with every other narrated result on the same content), and it does not prove a fix
addresses a specific finding. Movement plus a fresh witnessed review is the claim, nothing more.

## 4. The rest of the slice (unchanged in substance from SPEC.md)

- **G3b — the seal covers every configured repo** (ADR-057 §2-5): per-repo verdict lines,
  aggregate exit code, `repos[]` in `top --json` only when more than one repo is configured
  (single-repo output byte-identical), nested-path exemption union. `AC-GI-30, -32..36`.
- **G4 engine — human acts** (ADR-058 §5): `--human NAME --note TEXT` on `resolve-escalation` and
  the three `--resolve` commands (`cmd_resolve_escalation` 10040 and siblings), records
  `resolved_by`, `resolution_note`, `human_declared`, refuses under `CLAUDECODE=1`; `curate`
  (6977) records `human_source`. `AC-GI-40..42`.
- **G4 hook — `guard-pr-gate.py` + `pr-gate --cwd`** (ADR-058 §3, owner Q3 = draft-only),
  `pr-opened-not-ready` event (§2). `AC-GI-43..46, -48`.

## 5. Questions for the owner

5. **Anchor scope.** After the loop converges, any source-relevant edit makes the last review
   stale until the tool runs again (docs-only edits do not). *Recommended: yes* — an unreviewed
   source change is exactly M1; the cost is one more pass of each tool after a late edit.
6. **Memory.** A tool's false positive on unchanged code stays blocking until it is deferred.
   *Recommended: yes* — deferral is the method's existing path for a finding the human accepts.
7. **Witness shape.** A separate `review-start` call before each tool pass (the SKILL calls it),
   and `log-step --review` required for a step to count. *Recommended: yes*; the alternative
   (stamping inside `log-step`) is M2 again.
8. **Slicing.** 2.11.0 = R2' + G3b (one engine theme: which records the gate may skip); 2.12.0 =
   G4 engine + hook. *Recommended: yes* — the hook ships an installer change and its own probes.

## 6. Honest limits of the model check

- Bounds: 3 code versions, one QA tool, one repo, at most 5 ledger records. Several tools, several
  repos and longer histories are not explored; R2' is written per tool and per repo so the bound
  maps onto the design, but that is an argument, not a check.
- The model abstracts "a tool flags a version" as ground truth; a real tool is fallible. Memory's
  false-positive cost (Q6) is the price of that abstraction meeting reality.
- The model describes the DESIGN. Once 2.11.0 exists, each TLC path is replayed against the real
  engine as a RED case (FIXTURES §2b); a path the engine does not reproduce means the model is
  wrong until shown otherwise.

- **No git.** A reviewed tree cannot be compared without git, so the debt degrades to 2.10
  semantics there (a later clean step closes it) and `readiness` names each such closure; Anchor
  and Memory are skipped for the same reason. Decided while implementing (the model assumes git).

## 7. Delivery

| Area | Engine | Suite | Docs/SKILL | Total |
|---|---|---|---|---|
| R2' (review-start, --review, unwitnessed, Anchor, debt, Memory, legacy) | ~260 | ~320 (T174: the TLC paths as RED cases + a shipped probe vs v2.10.1) | ~80 (SKILL Phase 3 order, README claim) | **~660** |
| G3b seal every repo | ~120 | ~180 | ~40 | **~340** |
| **2.11.0 if Q8 = yes** | | | | **~1,000** |
| G4 engine + hook (2.12.0) | ~210 | ~260 | ~90 | **~560** |
