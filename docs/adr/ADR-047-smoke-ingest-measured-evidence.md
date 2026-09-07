---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/.claude/skills/uscha-devloop/SKILL.md
  - uscha-kit/skills/uscha-devloop/SKILL.md
  - uscha-kit/templates/CONSTITUTION.md
  - uscha-kit/templates/scripts/smoke-report-example.json
---
# ADR-047: The smoke run is measured evidence — executed, never narrated

## Status: Proposed

## Context

The ledger already ingests everything a machine produces on its own: JUnit reports, coverage
files, linter output, the static gate's XML, and since 2.2.0 a CI verdict. One phase of the loop
was still prose. Phase 7 — the smoke list — asked the agent to *produce a concrete manual
smoke-test checklist*, and what came back was a paragraph:

> the jar served /admin · the simulator answered 200 in 6 ms · the catalogue endpoint worked

None of that is evidence. It is a sub-agent narrating, and it is believed because it is written
confidently — the exact shape of failure the rest of this kit exists to refuse. A field report
made the cost concrete:

> Every simulator run returned an empty list, because the database had no rows. The smoke was
> reported as verified.

An empty list is a 200. A narrated smoke cannot distinguish "the endpoint answered correctly"
from "the endpoint answered", and the difference was the whole release. The ledger had no record
of the run at all, so nothing downstream — readiness, convergence, the PR gate — could disagree
with the sentence.

The gap is not that smoke runs are hard to measure. It is that nobody asked the project's own
tool for a machine-readable answer, and prose was accepted in its place.

## Decision

**The smoke run stops being a checklist an agent writes and becomes a REPORT the project's tool
writes, ingested through the same FACT-gate machinery every other gate uses.**

### 1. The contract — the smallest thing a shell script can emit

```json
{"checks": [{"name": "AC-28 the jar serves /admin",
             "ok": true,
             "status": 200,
             "latency_ms": 6,
             "evidence": "curl -sS localhost:8080/admin | head -1"}]}
```

`name` (a non-empty string) and `ok` (a **boolean**) are the whole mandatory surface. `status`
(integer or string), `latency_ms` (a number) and `evidence` (a string) are optional, validated
when present, and **never invented when absent** — a check with no `latency_ms` measured no
latency, which is a different fact from a latency of 0.

`ok: "true"` and `ok: 1` are refused. A contract that coerces is a contract that cannot say what
it measured, and the whole point of this ADR is that the answer must be unambiguous.

### 2. `smoke-ingest` — the subcommand

```
qa_ledger.py smoke-ingest --repo R --report reports/smoke.json [--iteration N] [--json]
```

It validates the contract, counts ok/failed, and persists `gate:smoke` through the SAME
static-gate record `gate-check` and `corpus-run` write — no parallel mechanism, so every reader
downstream already understands it. A failed check is a **BLOCKER**: readiness capped ≤ 65,
convergence blocked, exit 1; a later clean report clears it (latest-per-tool wins). A clean report
is a clean gate at exit 0.

The record carries the MEASUREMENT, not only the verdict:

```
smoke: {report, ok, failed, checks: [{name, ok, status, latency_ms}][:20], failed_names[:20],
        ac, ac_red}
```

so a reader six months later sees WHICH checks ran and what each answered — the facts the
narration used to carry and then lose. The list is capped at 20 because a receipt cites evidence
and is not a dump; the counts and the AC verdicts are computed over EVERY check, so a criterion's
fate never depends on where the display list was cut.

### 3. Refusal beats a guess

Exit 2, naming the first offending check or field: a report that is missing, unreadable, not
valid JSON, not an object, has no `checks` key, has a `checks` that is not a list, holds an
**EMPTY** list, or carries a check that is not an object, has no `name`, has no boolean `ok`, or
has a wrong-typed `status`/`latency_ms`/`evidence`.

The empty list is the one worth naming twice. `{"checks": []}` is a run that verified nothing, and
scoring it as `0 failed → PASS` would be a clean gate manufactured out of an absence — the false
clean this kit refuses everywhere else. An empty smoke is not evidence.

### 4. `smoke` is a FACT kind, and it may NOT run advisory

`log-gate --kind smoke --verdict pass|fail|not-run` is the parity door for a smoke measured
elsewhere (a CI job, a nightly, a human running the paths by hand). `smoke` joins the closed
`--kind` vocabulary (ADR-014, INV-ADVISORY-01) as the second FACT addition after `ci`, and it is
**not** admitted to `ADVISORY_CAPABLE_KINDS`.

That asymmetry with `corpus` (ADR-046) is deliberate and is the interesting half of this decision.
`corpus` may run advisory because a percentage is only a verdict once a budget is ADOPTED, and
with no threshold declared there is genuinely no gate. A smoke check has no budget: `ok` is
binary. It answered or it did not. There is no honest advisory reading of it, so admitting one
would be a mandatory gate cleared by goodwill.

### 5. AC closure by check name

A check whose `name` carries an AC tag — `AC-28 the jar serves /admin`, in the **same tag grammar
JUnit testcase names use** (`_ac_tag_ids`, ADR-036; one extractor, so a name cannot close a
criterion in the suite and fail to close it here) — closes that criterion MEASURED **iff** the
check is `ok` **AND** the ingested report's gate is `pass`.

Both halves matter. A green check inside a FAILING report is a green light on a run that did not
hold, and the ledger refuses to read it as one. And a **failed tagged check VETOES**, exactly like
a red JUnit testcase: the veto is evaluated before any green, because the cheapest way to fake a
closed criterion is to put a green beside a red.

`readiness --json` gains `acceptance.smoke_closed` (which ids a green check closed) and
`acceptance.smoke_vetoed` (which ids a failed one holds open — the half a reader cannot infer from
the closed list). The `narrated_only` text gains its smoke clause: a ticked criterion with no green
testcase, no green corpus run and no green smoke check is narration.

### 6. Readiness gets a `smoke` line — and no weight

One conditional line per repo that has ingested a report:

```
--- smoke backend-api: 8/8 checks ok PASS
--- smoke backend-api: 7/8 checks ok, 1 failed (healthz) FAIL
```

plus a conditional `smoke` object in `--json`. **A repo that never ingested one prints nothing and
emits nothing** — the same conditional-silence rule `lifecycle` (ADR-040), `agent_origin` (ADR-044)
and `field` (ADR-046) follow, so every existing project's readiness output is byte-identical to
what it was. There is no new weight and no new cap: a failing smoke already blocks through its
`gate:smoke` record, and this line adds the numbers the gates rollup cannot carry — how many
checks ran, how many answered wrong, and WHICH ones, so the failure is named instead of counted.

### 7. Phase 7 of the devloop produces the report

The devloop skill's phase 7 no longer asks for a prose list. It RUNS the smoke paths with the
project's own tool, has that tool write `reports/smoke.json`, ingests it, and cites the resulting
verdict line in the PR body. `uscha-kit/templates/scripts/smoke-report-example.json` is the
reference report. If a human runs the paths by hand, they still write the report: a checklist a
human ticked is evidence, a checklist an agent narrated is not.

## Consequences

- **The last narrated phase of the loop becomes measured.** "Evidence is executed, not narrated"
  now has an instrument behind it in phase 7, not only a slogan.
- **Nothing existing changes.** No new weight, no new cap, no config key. A project that never
  ingests a report sees the same readiness text and the same JSON payload it saw before, plus two
  additive `acceptance` keys.
- **The closed `--kind` vocabulary grows by one FACT, and the refusal grows with it.** `smoke`
  gates; `--verdict advisory` on it is exit 2. The reason is on the record, so a later reader can
  see why `corpus` may and `smoke` may not.
- **A smoke report is now a project deliverable.** Projects that had no smoke tool must write one
  — a shell script that curls three endpoints and prints JSON is enough. That cost is the point:
  a run nobody automated is a run nobody can check.
- **The AC path widens without loosening.** A criterion can now close on a smoke check, but the
  veto ladder got STRICTER, not looser: a failed tagged check holds a criterion open even beside a
  green testcase.
- **The `log-gate` parity record carries no checks.** A record written through that door has a
  verdict and no `smoke` block, so it gates but produces no smoke line and closes no criterion.
  That is honest: it is a verdict someone reported, not a report the engine read.

## What this ADR does NOT decide

- It does not add a `smoke` readiness dimension or move any weight. A failing smoke caps through
  its gate record; a weighted dimension would move every existing project's score and is owed its
  own argument.
- It does not RUN the smoke. The engine ingests a report; how the paths are exercised is the
  project's problem, and an engine that invented HTTP calls would be inventing the evidence.
- It does not define a check taxonomy (endpoint / flow / device). A `name` and an `ok` are the
  contract; naming conventions are the project's.
- It does not schedule the smoke, retry a flaky check, or average runs. A flaky check reported as
  ok is a lie the ledger cannot detect, and averaging it would be the kit manufacturing one.
- It does not accept `evidence` as proof. The string travels on the report for a human reader; the
  engine gates on `ok` alone, because a free-text field is narration again.
- It does not touch `corpus-run`, `gate-check` or `golden-diff`. This is the phase-7 evidence
  class, not a replacement for any of them.

## What is measured (`AC-SI-01..09`)

Smoke **T164**, nine criteria, over real temp projects and the real engine:

1. `AC-SI-01` — a report with one `ok: false` check exits 1 and persists a gated, non-advisory
   `gate:smoke` record naming the failed check; it is blocking in the gates rollup, and a later
   clean report clears it.
2. `AC-SI-02` — a ticked `AC-28` with no evidence reports `narrated_only`; a check named
   `AC-28 ...` in a passing report closes it MEASURED and attributes it in
   `acceptance.smoke_closed`.
3. `AC-SI-03` — a FAILED tagged check VETOES: it holds `AC-28` open even though a green check in
   another repo closed it, and it is reported in `acceptance.smoke_vetoed`. A green check inside a
   FAILING report closes nothing at all.
4. `AC-SI-04` — an EMPTY `checks` list refuses at exit 2 naming what was empty, and persists no
   record.
5. `AC-SI-05` — a check without a boolean `ok` (`"true"`, `1`) refuses at exit 2 NAMING the check;
   so do a check with no `name`, a report with no `checks` key, malformed JSON, and a missing file.
   Nothing is persisted.
6. `AC-SI-06` — the record carries the measurement (report path, counts, per-check receipts with
   status), the readiness line NAMES the failed check, exactly one line is printed, and a repo that
   ingested nothing produces no entry, no line and no `smoke` key.
7. `AC-SI-07` — the CONTROL PAIR: a passing smoke caps nothing (score 99.0, `cap_reason` null) and
   a failing one on another repo caps the same ledger at exactly 65 with `BLOCKER` named.
8. `AC-SI-08` — `log-gate --kind smoke` accepts pass/fail/not-run and a fail blocks;
   `--verdict advisory` is REFUSED at exit 2 saying why.
9. `AC-SI-09` — the **red probe**: the `v2.1.0` engine has neither `smoke-ingest`, nor
   `--kind smoke`, nor a `smoke` block, nor `acceptance.smoke_closed`. Without git or the tagged
   copy it reports `None` = UNMEASURED, never a silent pass.

A second, unshipped probe was run during development: forcing every check to read `ok` turns
`AC-SI-01`, `-03`, `-06` and `-07` red. The block measures the verdict, not its own scaffolding.

## Alternatives considered

- **Keep the prose checklist and ask the agent to be careful.** Rejected: that is the status quo,
  and it is what shipped an empty list as "verified". Discipline is not an instrument.
- **Have the engine RUN the smoke (curl a list of endpoints).** Rejected: the engine would be
  authoring the evidence, and a kit that invents HTTP calls is a kit that invents results. The
  project owns the run; the engine owns the record.
- **Accept the agent's prose and parse it into checks.** Rejected outright. Parsing narration back
  into facts launders it — the sentence would gain an exit code without gaining a measurement.
- **Admit `smoke` to `ADVISORY_CAPABLE_KINDS` for symmetry with `corpus`.** Rejected: symmetry is
  not a reason. `corpus` runs advisory because a percentage needs an adopted budget; `ok` is
  binary and has none, so an advisory smoke would be a gate cleared by goodwill.
- **Score an empty `checks` list as a pass (0 failed).** Rejected: it manufactures a clean gate
  out of an absence — the UNMEASURED-is-not-zero discipline, in the direction where it would be
  most convincing and most wrong.
- **Require `evidence` on every check.** Rejected: a mandatory free-text field is narration with a
  schema, and projects would fill it to satisfy the validator. `ok` is what gates.
- **A new `smoke` readiness dimension weighted alongside coverage.** Rejected for this release,
  for ADR-046's reason: a weighted dimension moves every existing project's score on upgrade and
  must be argued on its own.
- **Reuse `log-gate --kind gate-check` instead of a new kind.** Rejected: it would bury a smoke
  failure inside the static-analysis gate, and the whole value here is that the failed CHECK is
  named.
