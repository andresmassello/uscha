---
name: dev-loop
description: >
  Spec-driven, multi-repo development + QA orchestrator. Plans from an ADR, builds,
  then runs a severity-gated review loop (code-review / judgment-day / improve) that
  converges instead of looping forever, with tests as a guardrail between passes.
  Auto-triggers characterization tests when JaCoCo line coverage is below threshold.
  Records every step in a deterministic ledger and stops at the merge gate for human
  approval. Invoke for "run the dev loop", "QA this feature", "do the full cycle".
allowed-tools: Read, Edit, Write, Glob, Grep, Bash
disable-model-invocation: false
---

# dev-loop orchestrator

**Who this is for:** a single operator driving one non-trivial or risk-bearing change,
kept honest by a deterministic ledger and a human merge gate. **NOT for trivial or
throwaway work** — a one-file fix or config tweak runs build+test only and skips
discovery/ADR/sys-doc entirely (see the risk-profile table in the playbook, play 03).

You are running a disciplined development + QA cycle across one or more repositories.
The measurement engine is `./.claude/skills/dev-loop/qa_ledger.py` (stdlib Python 3).
**All metrics come from the ledger — never estimate counts from memory.** Run every
QA tool through the ledger so the final retrospective is real. The ledger contract has
two tiers: **measured** records (snapshots, ingest-gate, log-gate — parsed from real
artifacts; these can block) and **self-reported** agent counts (log-step — narration
recorded for the retrospective; a measured red always overrides a narrated green).

## Non-negotiable principles

1. **Converge, don't chase zero.** Block only on findings at or above the severity
   gate (`config.defaults.severity_gate`, default BLOCKER/CRITICAL/HIGH). Everything
   below goes to `ISSUES-DEFERRED.md`, never into the loop. Polishing Medium/Low
   findings forever is the failure mode this skill exists to prevent.
2. **Tests are a guardrail, not a finale.** Run the repo's test command (`mvn test` /
   `flutter test` / `pytest` / `npm test` / `go test` / `cargo test` / `dotnet test` / `ctest` / `./gradlew test` / `swift test`) after every tool pass that changed code. A red suite
   stops the loop.
3. **Generating tests is not running tests.** `/improve test` (writing coverage) runs
   ONCE at the end against stabilized code — never inside the loop. Inside the loop you
   only *run* the existing suite.
4. **Stop at merge.** You create the PR and confirm CI is green. You do NOT merge.
   The human owns the merge gate.
5. **Tracked-markdown protocol.** Before modifying any tracked `.md`
   (CLAUDE.md, plan/delta docs, docs/adr), ask the human for the current version first.
   Those files carry real progress (checkboxes, notes); never regenerate from scratch.
6. **The golden is the one artifact you cannot author.** For migration/legacy work,
   `.approved` fixtures are field truth captured from the ORIGINAL code and approved by
   a HUMAN. You emit `.received` and stop; you never write, edit or rename `.approved`
   (a `PreToolUse` hook denies the write — INV-GOLDEN-01).

## Setup (once per run)

```bash
QL="./.claude/skills/dev-loop/qa_ledger.py"
python3 $QL init --config dev-loop.config.json
```

The config lists every repo and its type (maven|flutter|python|node|go|rust|dotnet|cpp|gradle|swift). In a multi-repo session the
other repos must be mounted via `--add-dir` or `additionalDirectories`; the `path`
fields in the config are relative to where you run `init`.

For migration/legacy (risk profile E) work, also wire the golden invariant once:
install `hooks/block-approved-writes.ps1` (or its bash twin) as a `PreToolUse` hook in
`settings.json`, and add `*.approved.* binary` to `.gitattributes` (ships in
`templates/.gitattributes`) so line endings can't lie in the byte-compare.

## Phase 0 — Plan (ADR-first)

- **Read `CONSTITUTION.md` first (if present).** It lists the project invariants no SPEC
  or ADR may violate. A change that would breach an invariant is a BLOCKER — escalate, do
  not work around it. The CONSTITUTION constrains the whole build.
- The ADR set + `ACCEPTANCE.md` are the input to this loop. They typically come from the
  `adr-refine` skill (the front-half counterpart): `/adr-refine` → ADR set → `/dev-loop`.
- Confirm or write the ADR + PLAN. The plan must state **acceptance criteria** (the
  `ACCEPTANCE.md` checkboxes) and the **severity gate / coverage threshold** up front.
  The loop targets the plan, not "no issues". If acceptance criteria are missing, stop
  and run `adr-refine` first (or ask the human).
- Acceptance criteria become the contract tests in Phase 1.

## Phase 1 — Coverage gate → conditional characterization (per repo)

For each repo, decide whether a safety net exists before any refactoring:

```bash
python3 $QL snapshot --repo <REPO> --phase pre
python3 $QL check-coverage --repo <REPO>     # exit 0 = OK, exit 1 = BELOW threshold
```

- **Coverage >= threshold:** the existing suite is the guardrail. Skip to Phase 2.
- **Coverage < threshold (or no report):** write **characterization / contract tests
  at the boundary** (public API, endpoints, input→output behavior) — NOT internals.
  These must survive refactoring. The ADR acceptance criteria are the spec for these.
  **Have the human review these tests before trusting them as a gate** — a test that
  passes for the wrong reason poisons the whole loop.
- **Migration/legacy (profile E): capture the golden BEFORE touching anything.** Run
  the `characterize` skill (or `reverse-discovery` for a whole-system map first): it
  executes the ORIGINAL code against a real input corpus, emits `.received` fixtures,
  and STOPS for the human to approve them as `.approved`. No approved golden = no
  migration build. This is the baseline `golden-diff` gates against in Phase 3.

## Phase 2 — Build

Implement per the PLAN. Commit per logical step with conventional commits
(`feat:`, `fix:`, `refactor:`…) so the trail is reviewable and revertible.

### ADR discipline during build

- **Consult before touching governed areas.** Before working on an area covered by an
  accepted ADR, read it and follow its Implementation Plan (affected paths, patterns,
  tests). Also re-check `CONSTITUTION.md`: if the change would breach an invariant, stop
  and escalate — a constitution breach is a BLOCKER and is never resolved silently in code.
  If the code contradicts the ADR, flag it to the human — never resolve the conflict
  silently in code.
- **Proactive ADR triggers — stop and propose an ADR** when you are about to: introduce
  a new dependency, create a new architectural pattern others must follow, choose between
  real alternatives with non-obvious trade-offs, or contradict an accepted ADR. Tell the
  human the decision, why it matters, and ask whether to capture it. If no, leave a short
  `// ADR-not-taken: <why>` comment and move on.
- **Link code ↔ ADR.** When implementing a decision, add one lightweight comment at the
  entry point: `// ADR: <slug> — see docs/adr/ADR-NNN-<slug>.md`. This makes supersede
  safe (you can find all code an ADR governs).
- **Never edit the SPEC/ADR to make the implementation look correct.** If reality forces
  a change, amend the SPEC (version it) and return to Ready.

## Phase 2b — Simplicity gate ("Reduce")

Before the QA loop, check the change isn't overbuilt. This is the CONSTITUTION's
**Simplicidad** invariant made deterministic — diff minimality, nesting depth and new
abstractions, scored over the diff (not AST cyclomatic complexity; honest proxies):

```bash
git diff --unified=0 <base> | python3 $QL simplicity-check --config dev-loop.config.json
# or: python3 $QL simplicity-check --from-git --base <base>
```

Reads `SIMPLICITY: NN/100 — SIMPLE | ACCEPTABLE | OVERBUILT`. **OVERBUILT (exit 1) is a
BLOCKER**: reduce first (guard clauses, drop speculative types/layers, split giant hunks)
and re-run — do not carry it into the QA loop or converge on it. The flags tell you exactly
what to cut. Budgets live in `config.defaults.simplicity` (tighten per risk profile). For a
2-space codebase pass `--indent-width 2`.

**Tests are OUTSIDE the budget** (kit 1.11.0): test files (the 9 stack conventions) are
counted and reported apart (`test_lines_added`) but never gate — writing tests must not
push a diff toward OVERBUILT (deleting them is already blocked by gate-check). A good
project can have MORE test code than production code.

**Persist the verdict** so convergence and readiness see it (facts block through the
ledger, not through your goodwill):

```bash
python3 $QL log-gate --repo <REPO> --iteration <N> --kind simplicity \
  --verdict <pass|fail> [--note "OVERBUILT: +612 lines vs 400 budget"]
```

## Phase 3 — QA loop (per repo)

Run the tools in `config.defaults.qa_tools_order` (default: code-review → judgment-day
→ improve). One pass of all tools = one cycle. After **each** tool pass:

1. Apply only fixes at/above the severity gate. Send the rest to `ISSUES-DEFERRED.md`.
2. Run the repo test command. If red and the fix isn't obvious → escalate.
3. Log the agent QA tools (code-review / judgment-day / improve) with `log-step`,
   using counts from each tool's own summary. These counts are **self-reported
   narration** (recorded for churn/retrospective); the blocking signals in this loop
   are the MEASURED records — ingest-gate, log-gate, snapshots:

```bash
python3 $QL log-step --repo <REPO> --tool <code-review|judgment-day|improve> \
  --iteration <N> \
  --reported <total findings> --gated-reported <findings at/above gate> \
  --fixed <fixed this pass> --deferred <sent to backlog> --suppressed <false positives> \
  --tests-passed <true|false> --files-changed <count> \
  --fingerprint <stable,finding,ids>   # enables oscillation detection
```

3b. **Fact gates — on every pass that changed code**, run gate-check (did the change
weaken the measuring apparatus?) and, for migration work, golden-diff (does behavior
still match the human-approved baseline?). Then PERSIST each verdict with `log-gate`
— a failing fact gate blocks convergence and caps readiness ≤65 through the ledger:

```bash
python3 $QL gate-check --from-git --base <base> --repo <REPO>   # exit 1 = BLOCKER
python3 $QL log-gate --repo <REPO> --iteration <N> --kind gate-check --verdict <pass|fail>

python3 $QL golden-diff [--dir <fixtures-root>]   # exit 0 CLEAN · 1 DIVERGE · 2 NOT-RUN
python3 $QL log-gate --repo <REPO> --iteration <N> --kind golden-diff \
  --verdict <pass|fail|not-run>   # not-run records the absence — it is never green
```

(pit-check stays on its scheduled/incremental tier — CONSTITUTION §Tests efectivos —
but when a PIT report EXISTS and fails the gate, persist it the same way:
`log-gate --kind pit-check --verdict fail`.)

4. The **static analysis gate** (`java-qa-gate`: Checkstyle/PMD/SpotBugs/FindSecBugs)
   is NOT counted by hand. Run the gate so its XML reports are written, then ingest
   them — the ledger parses the reports, normalizes severities to the common gate
   scale, splits FindSecBugs (SECURITY) out from SpotBugs, and computes the real
   `fixed` count by diffing finding-IDs against the previous run:

```bash
# run your java-qa-gate first (it must emit:
#   target/checkstyle-result.xml, target/pmd.xml, target/spotbugsXml.xml)
python3 $QL ingest-gate --repo <REPO> --iteration <N>
# one static-gate step is logged per linter; pass --combined to merge into one.
```

Severity normalization: Checkstyle error→HIGH / warning→MEDIUM; PMD priority
1→BLOCKER … 5→LOW; SpotBugs priority 1→HIGH / 2→MEDIUM / 3→LOW; FindSecBugs
(category SECURITY) floored to HIGH. A report file that EXISTS but is empty credits the
fix; an ABSENT report is not treated as clean (means the gate didn't run).

**End-of-cycle checks (advisory — you make the final call):**

```bash
python3 $QL converged   --repo <REPO> --tools-per-cycle <count>   # exit 0 = converged
python3 $QL oscillation --repo <REPO> --tool <tool>               # exit 1 = oscillating
```

Convergence requires ALL of: the latest agent step of EVERY tool in `qa_tools_order`
clean (zero gated findings, zero files changed, tests green — padding the window with
extra clean steps does not help, and a red snapshot vetoes a narrated green), AND the
latest static-gate run of every linter clean at the gate level, AND every persisted
fact gate (`gate:*`, `blocker:*` records from log-gate/flag-blocker) clean. A clean
agent cycle alone does not converge if any measured gate still flags something.

- **Converged** → leave the loop for this repo.
- **Not converged** → next cycle, up to `config.defaults.max_iterations`.

## Phase 4 — Integration / contract pass (multi-repo)

After each repo converges individually, run the cross-repo layer with all repos mounted.
Run the integration/contract test command from the config and treat contract breakages
as gated findings. Log under `--repo integration`. This is the second layer of your
two-layer QA architecture; per-repo green does not imply the seams are green.

## Phase 5 — Verify (coverage generation, once)

Now that code is stable:

```bash
# /improve test  → write the fine-grained coverage you deferred earlier
# Then run the full suite and regenerate coverage reports.
python3 $QL snapshot --repo <REPO> --phase post   # for every repo + integration
```

Full suite must be green and coverage at/above threshold before proceeding.

## Phase 5b — Rebuild test (optional; risk profile C+/E or periodic CI)

Completeness of the SPEC, not correctness of the build: is the spec package enough to
regenerate the system from scratch? Worth running for critical/legacy work or on a
schedule, not every feature.

```bash
# 1) capture the signature of the system as it stands now
python3 $QL rebuild --mode baseline --config dev-loop.config.json
# 2) in a CLEAN tree / fresh session, regenerate PRODUCTION code from SPEC/ADR/
#    ACCEPTANCE only, PRESERVING the test suite, then run the tests.
# 3) score the regenerated tree against the baseline
python3 $QL rebuild --mode compare --baseline REBUILD-BASELINE.json   # exit 0 = COVERS
```

The dominant signal is the preserved suite: tests that passed originally but fail on
regenerated code are behavior the SPEC left implicit. Verdicts: COVERS (≥90), PARTIAL
(≥70), DIVERGE (<70). Feed the listed gaps back into the SPEC, then re-run — divergence
is a spec gap, not a code bug.

## Phase 6 — PR (stop at merge)

- Ensure conventional-commit history is clean.
- Open the PR(s). Confirm CI is green.
- **STOP.** Present the PR link(s) and wait for the human to merge.

## Phase 7 — Smoke list

Produce a concrete manual smoke-test checklist (real user paths / endpoints / device
flows for this change), so the human can verify the system behaves as intended.

## Phase 8 — Hand off to docs + retrospective

```bash
python3 $QL summary           # human-readable
python3 $QL summary --json    # machine-readable, consumed by the sys-doc skill
```

**Readiness KPI — show this after finishing ANY task, not only full runs.** It measures
the STATE of the result (not effort spent), as a weighted score 0..100 with hard caps:

```bash
python3 $QL readiness --acceptance <ACCEPTANCE.md> --tools-per-cycle <count>
```

Dimensions and default weights: acceptance (traced, MEASURED) 30, ADR/checkbox
completion 15, coverage 15, static gate 20, convergence 10, integration 10. A
lint-capable repo whose static gate NEVER ran scores that dimension UNMEASURED (0.0) —
silence is not success. Hard caps override the weighted score: tests red → ≤35,
BLOCKER/CRITICAL open → ≤65, unresolved escalation → ≤75 (held until
`resolve-escalation` — a recorded event, not an implication). A `CONSTITUTION.md`
breach does NOT reach the engine by itself: **you MUST log it** —
`flag-blocker --repo <REPO> --kind constitution --note "<invariant breached>"` — and
once logged it caps readiness ≤65 and blocks convergence until `--resolve`. Bands:
<50 NOT READY, 50–79 IN PROGRESS, 80–94 RELEASE CANDIDATE, 95–100 READY.

**Acceptance traceability (the DOMINANT dimension — kit 1.10.0).** Each ACCEPTANCE
criterion carries a stable ID: `- [ ] AC-01 — when X then Y`. A criterion counts as
CLOSED only when ≥1 GREEN testcase whose name carries the tag (`test_ac1_x`,
`testAC01X`, `"AC-01: ..."` — IDs normalize by number, `AC-01 == AC_1 == ac1`) exists
in the ingested JUnit reports AND no tagged testcase is red. The checkbox is the
NARRATIVE; the testcase is the FACT — a checked box without a green tagged test shows
up as `narrated_only` and does NOT close (measured beats narrated, per criterion).
So: when you write the tests for a criterion, put its AC-n in the test name; run
`spec-check --acceptance ACCEPTANCE.md` up front (zero traceable criteria / duplicate
IDs block as structural FACTS). Files without IDs fall back to the checkbox ratio
with a warning (legacy mode — adopt incrementally).

ADR completion is parsed from the **acceptance task list** (markdown `- [x]`/`- [ ]`),
read-only — set the path via `config.defaults.acceptance_file` or `--acceptance`. Count
the WHOLE file (the CLI default); only pass `--section` if you have verified the heading
text matches your template exactly — a mismatched section silently zeroes a heavy
dimension. Always present the headline WITH the dimension breakdown AND the capping
blocker, so it's clear what's missing, not just the number. Cycles/regressions are churn
(process health) and are reported separately — they never raise readiness.

Optionally (on request — reporting, not part of the verified build) invoke the `sys-doc`
skill to generate the two-view HTML deck. Finish with a retrospective drawn FROM the
ledger summary: total steps, %fixed per tool, coverage, prod LOC vs test LOC, test
count, tests/kLOC, plus concrete methodology improvements.

## Escalation contract — STOP and ask the human when:

- The iteration cap is hit without convergence.
- Oscillation is detected (a finding set keeps returning).
- A previously-passing test now fails and the fix is non-trivial.
- Two tools give contradictory directives on the same code.
- A fix would require an architectural decision (ADR-level change).
- A change would breach the `CONSTITUTION.md` (an inviolable invariant) — never trade it
  away; changing the constitution is a separate, explicit human decision.

Record every escalation, and record its CLOSURE — the readiness cap holds until the
human resolves it:

```bash
python3 $QL escalate --repo <REPO> --reason "<what blocked + what you need from me>"
# ... human reviews/decides ...
python3 $QL resolve-escalation --repo <REPO> --note "<how it was closed>"
```

A CONSTITUTION breach is escalated AND flagged as a first-class blocker:

```bash
python3 $QL flag-blocker --repo <REPO> --kind constitution --note "<invariant breached>"
# after the human decision:  flag-blocker --repo <REPO> --kind constitution --resolve
```

Never auto-merge, never silently exceed the iteration cap, never fix below the gate to
make the number look better.
