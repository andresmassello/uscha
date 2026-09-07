# Also in 2.2.0 — the smoke run as measured evidence: executed, never narrated (ADR-047)

## The finding

The ledger ingests everything a machine produces on its own: JUnit, coverage, linters, the static
gate's XML, and since this release a CI verdict. One phase of the loop was still prose. Phase 7 —
the smoke list — asked the agent to *produce a concrete manual smoke-test checklist*, and what
came back was a paragraph:

> the jar served /admin · the simulator answered 200 in 6 ms · the catalogue endpoint worked

None of that is evidence. It is a sub-agent narrating, and it is believed because it is written
confidently. From the field, the cost:

> **Every simulator run returned an empty list, because the database had no rows. The smoke was
> reported as verified.**

An empty list is a 200. A narrated smoke cannot tell "the endpoint answered correctly" from "the
endpoint answered", and the difference was the release. Worse, the ledger held no record of the
run at all — so readiness, convergence and the PR gate had nothing to disagree with the sentence.

The gap was never that smoke runs are hard to measure. It is that nobody asked the project's own
tool for a machine-readable answer, and prose was accepted in its place.

## `smoke-ingest` — the subcommand

```bash
python3 $QL smoke-ingest --repo <REPO> --report reports/smoke.json
#   [qa_ledger] backend-api/gate:smoke: FAIL — 7/8 checks ok
#     ok   AC-28 the jar serves /admin (status 200, 6 ms)
#     FAIL healthz (status 503)
#     caps readiness <=65 and blocks convergence until a clean smoke
python3 $QL readiness
#   --- smoke backend-api: 7/8 checks ok, 1 failed (healthz) FAIL
```

The contract is the smallest thing a shell script can emit:

```json
{"checks": [{"name": "AC-28 the jar serves /admin", "ok": true, "status": 200,
             "latency_ms": 6, "evidence": "curl -sS localhost:8080/admin | head -1"}]}
```

`name` (a non-empty string) and `ok` (a **boolean**) are the whole mandatory surface. `status`
(integer or string), `latency_ms` (a number) and `evidence` (a string) are optional, validated
when present, and never invented when absent — a check with no `latency_ms` measured no latency,
which is a different fact from a latency of 0. `ok: "true"` and `ok: 1` are refused: a contract
that coerces is a contract that cannot say what it measured.

The record carries the MEASUREMENT, not only the verdict — the report path, the ok/failed counts,
the per-check receipts (name, ok, status, latency) and the failed names, capped at 20 because a
receipt cites evidence and is not a dump. The counts and the AC verdicts are computed over EVERY
check, so a criterion's fate never depends on where the display list was cut.

## Refusal beats a guess

Exit 2, naming the first offending check or field: a report that is missing, unreadable, not valid
JSON, not an object, has no `checks` key, has a `checks` that is not a list, holds an **empty**
list, or carries a check that is not an object, has no `name`, has no boolean `ok`, or has a
wrong-typed `status` / `latency_ms` / `evidence`.

```
[qa_ledger] smoke-ingest: reports/smoke.json: check 2 (the admin page) has no boolean `ok`
            (got 'true') -- a smoke check is a binary fact, and a string, a number or a
            missing key is not a verdict
```

The empty list is the one worth naming twice. `{"checks": []}` is a run that verified nothing, and
scoring it `0 failed → PASS` would manufacture a clean gate out of an absence — the false clean
this kit refuses everywhere else.

## A FACT kind — and it may NOT run advisory

`log-gate --kind smoke --verdict pass|fail|not-run` is the parity door for a smoke measured
elsewhere (a CI job, a nightly, a human running the paths by hand). `smoke` joins the closed
`--kind` vocabulary as the second FACT addition after `ci`, and it is **not** admitted to
`ADVISORY_CAPABLE_KINDS`.

The asymmetry with `corpus` (ADR-046, in this same release) is deliberate and is the interesting
half. `corpus` may run advisory because a percentage is only a verdict once a budget is ADOPTED,
and with no threshold declared there genuinely is no gate. A smoke check has no budget: `ok` is
binary. It answered or it did not. An advisory smoke would be a mandatory gate cleared by
goodwill, so `--verdict advisory --kind smoke` is exit 2.

## A green check closes a criterion — and a failed one VETOES it

A check whose `name` carries an AC tag — `AC-28 the jar serves /admin`, in the **same tag grammar
JUnit testcase names use** — closes that criterion MEASURED **iff** the check is `ok` **and** the
ingested report's gate is `pass`. Both halves matter: a green check inside a failing report is a
green light on a run that did not hold.

And a **failed tagged check vetoes**, exactly like a red JUnit testcase. The veto is evaluated
before any green, because the cheapest way to fake a closed criterion is to put a green beside a
red. `readiness --json` reports both halves — `acceptance.smoke_closed` and
`acceptance.smoke_vetoed` — and the `narrated-only` line gains its smoke clause: a ticked
criterion with no green testcase, no green corpus run and no green smoke check is narration.

## Phase 7 produces the report

The devloop skill's phase 7 no longer asks for a prose list. It RUNS the smoke paths with the
project's own tool, has that tool write `reports/smoke.json`, ingests it, and cites the resulting
verdict line in the PR body instead of a claim that the smoke passed.
`uscha-kit/templates/scripts/smoke-report-example.json` is the reference report — three checks,
one tagged `AC-01`. If a human runs the paths by hand, they still write the report: a checklist a
human ticked is evidence, a checklist an agent narrated is not.

## What is measured — `AC-SI-01..09`, smoke **T164**

Nine criteria over real temp projects and the real engine: the gated fail and its clearing by a
later clean report (`-01`); `narrated_only` → MEASURED through a tagged check, attributed in
`acceptance.smoke_closed` (`-02`); the **veto** — a failed tagged check holds the criterion open
even beside a green one elsewhere, and a green check inside a failing report closes nothing
(`-03`); the empty list refused at exit 2, persisting nothing (`-04`); six refusals naming the
offending check or field (`-05`); the record's receipts, the named failure on the readiness line
and total silence for a repo that ingested nothing (`-06`); the **control pair** — a passing
smoke caps nothing at score 99.0, a failing one on a second repo caps the same ledger at exactly
65 with `BLOCKER` as the reason (`-07`); the `log-gate` parity door and the advisory refusal
(`-08`); and the **red probe** — the `v2.1.0` engine has neither the subcommand, nor the `--kind`,
nor the `smoke` block, nor `acceptance.smoke_closed` (`-09`).

A second probe was run during development and not shipped: forcing every check to read `ok` turns
`AC-SI-01`, `-03`, `-06` and `-07` red. The block measures the verdict, not its own scaffolding.

## Not a breaking change

No new weight, no new cap, no config key, no change to any existing subcommand's behaviour. A
project that never ingests a smoke report sees the same readiness text and the same JSON payload
it saw before, plus two additive `acceptance` keys. Subcommands 54 → 55.

## Not in this release

- **A `smoke` readiness dimension.** A failing smoke caps through its gate record; a weighted
  dimension would move every existing project's score and is owed its own argument.
- **Running the smoke.** The engine ingests a report; how the paths are exercised is the project's
  problem, and an engine that invented HTTP calls would be inventing the evidence.
- **A check taxonomy** (endpoint / flow / device). A `name` and an `ok` are the contract.
- **Flake handling, retries or averaging.** A flaky check reported as `ok` is a lie the ledger
  cannot detect, and averaging it would be the kit manufacturing one.
- **`evidence` as proof.** The string travels for a human reader; the engine gates on `ok` alone,
  because a free-text field is narration again.
