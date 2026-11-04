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
  that suite (`model_check.suite_pattern` / `--suite-pattern` set a stricter regex). A `*template*`
  file in `docs/adr` is not read as an ADR.
- **`model-check --run --tier ci|deep`** runs TLC with the project's JDK and `tla2tools.jar` v1.7.4
  verified by sha256 (`model_check.jar` / `jar_sha256` / `java` override), or the runner the project
  declares in `model_check.tlc_cmd`. Without the jar, without Java, or when TLC cannot start, the
  models read **UNMEASURED** (exit 2), never passed; a jar that is not the pin is refused (exit 1)
  and runs nothing. Each config's run is recorded in the ledger (`model_runs`: verdict, time, runner,
  and the sha256 of its module, its `.cfg` and its manifest entry), stale once any of them changes;
  `--no-record` runs without recording.
- **`readiness`** prints a `--- models` line only for a project that declared `from_adr`: ADRs
  without the field, broken manifests, required models not run, stale or red, and agent-written
  `not-needed` the human has not confirmed. **Advisory** by default; with `"model_check": {"mode":
  "gate"}` they block `pr-ready`, named.
- **`uscha init`** writes `"model_check": {"from_adr": ...}` into the generated config -- `ADR-001` on
  a repo with no ADRs, the next free number on one that has them, so nothing already written is
  retrofitted; a re-run keeps a block already declared. **`doctor`** proposes it to a project
  initialised before 2.15.0 that has ADRs, and names a block it cannot read.
- **The `uscha-adr-refine` skill** (both twins) asks the question when the project declares the
  boundary, and the `CLAUDE.md` template carries the rule.
- **This repo**: `tools/model-check.py` is now a thin wrapper over the engine (the same command line,
  the repo's boundary ADR-059 and its suite, nothing recorded); the CI `models` job stays its gate.

## Also fixed: skill templates travel with the skill

Found in a real project: the installed `uscha-rubric` skill said "create one from
`templates/RUBRIC.md`", but the installer copies each skill's folder only and `init` never copies a
rubric, so the template and the grader prompt existed nowhere the agent could read. The agent
reverse-engineered the format from the engine's parser and wrote its own template into the global
install. Now each skill carries the templates it names, in its own `templates/` folder:
`uscha-rubric` (`RUBRIC.md`, `rubric-grader-prompt.md`), `uscha-adr-refine` and `uscha-discovery`
(`ADR-stack-template.md`), `uscha-devloop` (`smoke-report-example.json`). `uscha-kit/templates/`
stays the canonical source; the copies are byte-identical (AC-TP-02). `doctor` names the rubric
template's real path on that install. Pinned by `AC-TP-01..03` (smoke T179), red first.

**After upgrading,** reinstall the skills (`install --target ...`). If an agent wrote its own
`uscha-rubric/templates/RUBRIC.md` into the installed skill, the reinstall replaces it with the
kit's; a project's own `RUBRIC.md` is never touched.

## Behavior changes on upgrade (read before upgrading)

- None for an existing project until it declares `model_check.from_adr`: `readiness` and `phase`
  read exactly as before (AC-MK-01). `doctor` adds one advisory warning proposing the boundary to a
  project that has ADRs.
- A project created with `uscha init` from 2.15.0 on gets the rule from `ADR-001`, advisory.
- The published subcommand count moves from 62 to 63 (`model-check`), with its row in both
  command-reference docs.

## Closed before release (fresh review)

A fresh review of the first cut found ways through the gate; each is now a RED case (AC-MK-09..14):

- **Any `--tlc-cmd` was evidence.** A fake TLC printing the right lines passed a gate. Now only the
  declared runner records -- the pinned jar or `model_check.tlc_cmd` -- and an old record from
  another runner, or from a jar that is no longer the pin, reads "not run".
- **A run survived a manifest edit.** Changing a config's `expect` after the run left it "ok". The
  record now carries the entry's sha256; an edit makes it stale.
- **An unconfirmed agent `not-needed` was never named**, although the ADR promised it. Now it is a
  problem, a block under a gate.
- **An unreadable block switched the check off silently.** A typo in `from_adr` or `"Gate"` with a
  capital read as "never opted in". Now the block is named, fails closed under a gate, the mode is
  read case-blind, and a live `"advisory"` cannot downgrade a gate frozen in the ledger.
- **The port weakened the repo's suite rule** (any quoted id counted, a prose mention included). The
  wrapper passes the 2.13.0 pattern again.
- **Smaller:** the kit's own `ADR-stack-template.md` blocked a gated project; a `[]` manifest ended in
  a traceback; a symlinked ledger path, and on Windows a temp dir in 8.3 form (`RUNNER~1`) that read
  every recorded run as "not run" (CI caught it; both sides are now `realpath`); a re-run of `init` after the first ADR reported a conflict;
  `readiness` said "they BLOCK" with zero problems; the acceptance file is read from the config.

## Honest limits

- A green model proves that TLC found no violation OF THE MODEL at its bounds. The RED case each
  counterexample replays is the only link to the code -- and, as 2.14.0 showed, a model can be
  wrong in what it cannot express.
- Java is the project's dependency for `--run`; the kit installs neither Java nor the jar, and the
  release ritual does not run TLC.
- The suite measures `--run`'s logic with a stub TLC; real verdicts are measured where a project
  runs it (in this repo, the CI `models` job).
- A recorded run proves that the declared runner printed that verdict. The config and the ledger are
  files the agent can write: declaring a fake `tlc_cmd` is a visible edit in git, not something the
  engine can refuse.

## How it is pinned

`AC-MK-01..14` (smoke T178), each red first -- 01..08 against 2.14.1 (except AC-MK-01, which pins
that nothing changes for a project that never opted in), 09..14 against the first cut of 2.15.0.

## Evidence

Suite: __SUITE__ checks · 0 fail; acceptance __ACC__.
