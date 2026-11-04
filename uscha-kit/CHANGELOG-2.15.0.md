# uscha-kit 2.15.0 — the kit ships the model check: from a declared ADR on, every design decides whether it needs a model, and a witnessed TLC run is evidence (ADR-061)

## What changed

ADR-059 (2.13.0) made "does this design need a model?" a written, checked decision in THIS repo
and deferred the kit until a second real case existed. DeferralById (2.14.0) was that case: modelled
before the code, it broke the old deferral rule and a rule without human confirmation, and a fresh
review then found a hole the model could not express, which became a teeth config. 2.15.0 ships the
mechanism to every project, as the project's choice.

- **`qa_ledger.py model-check`** -- without Java: every ADR from `model_check.from_adr` on must
  declare `model: required` (with `model_manifest:` under `docs/<feature>/models/`) or `model:
  not-needed -- <reason>`; every manifest must declare a `ci` config, a vacuity config that MUST
  break, a safety invariant beyond `TypeOK`, and the AC id (a checkbox criterion in the acceptance
  file) of the RED case each counterexample replays. `--suite FILE` also requires each id quoted in
  that suite.
- **`model-check --run --tier ci|deep`** runs TLC with the project's JDK and `tla2tools.jar` v1.7.4
  verified by sha256 (`model_check.jar` / `jar_sha256` / `java` override). Without a pinned jar or
  without Java the models read **UNMEASURED** (exit 2), never passed. Each config's run is recorded
  in the ledger (`model_runs`: verdict, time, and the sha256 of its module and `.cfg`), stale once
  either changes; `--no-record` runs without recording.
- **`readiness`** prints a `--- models` line only for a project that declared `from_adr`: ADRs
  without the field, broken manifests, and required models not run, stale or red. **Advisory** by
  default; with `"model_check": {"mode": "gate"}` they block `pr-ready`, named.
- **`uscha init`** writes `"model_check": {"from_adr": ...}` into the generated config -- `ADR-001` on
  a repo with no ADRs, the next free number on one that has them, so nothing already written is
  retrofitted. **`doctor`** proposes it to a project initialised before 2.15.0 that has ADRs.
- **The `uscha-adr-refine` skill** (both twins) asks the question when the project declares the
  boundary, and the `CLAUDE.md` template carries the rule.
- **This repo**: `tools/model-check.py` is now a thin wrapper over the engine (the same command line,
  the repo's boundary ADR-059 and its suite, nothing recorded); the CI `models` job stays its gate.

## Behavior changes on upgrade (read before upgrading)

- None for an existing project until it declares `model_check.from_adr`: `readiness` and `phase`
  read exactly as before (AC-MK-01). `doctor` adds one advisory warning proposing the boundary to a
  project that has ADRs.
- A project created with `uscha init` from 2.15.0 on gets the rule from `ADR-001`, advisory.
- The published subcommand count moves from 62 to 63 (`model-check`), with its row in both
  command-reference docs.

## Honest limits

- A green model proves that TLC found no violation OF THE MODEL at its bounds. The RED case each
  counterexample replays is the only link to the code -- and, as 2.14.0 showed, a model can be
  wrong in what it cannot express.
- Java is the project's dependency for `--run`; the kit installs neither Java nor the jar, and the
  release ritual does not run TLC.
- The suite measures `--run`'s logic with a stub TLC; real verdicts are measured where a project
  runs it (in this repo, the CI `models` job).

## How it is pinned

`AC-MK-01..08` (smoke T178), each red against 2.14.1 first except AC-MK-01, which pins that nothing
changes for a project that never opted in.

## Evidence

Suite: __SUITE__ checks · 0 fail; acceptance __ACC__.
