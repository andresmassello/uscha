---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/.claude/skills/uscha-adr-refine/SKILL.md
  - uscha-kit/skills/uscha-adr-refine/SKILL.md
  - uscha-kit/templates/CLAUDE.md
  - tools/model-check.py
model: not-needed -- it reuses the witnessed-run pattern of ADR-055 and an advisory/gate switch with no state of its own (origin: agent, confirmed: 2026-11-04)
---
# ADR-061: The kit ships the model check -- every ADR from a declared point on decides whether it needs a model, and a witnessed TLC run is evidence the project can make a gate

## Status: Accepted (2.15.0) — decided by the owner on 2026-11-04 (an `adr-refine` interview). Promotes ADR-059 (repo-level) into the kit.

## Context

ADR-059 (2.13.0) made the decision to model a written, checked field on every ADR of THIS repo,
and deferred the kit until a second real case existed. It now has two: GatedDebt (2.11.0), and
DeferralById (2.14.0), modelled before the code -- where the model broke the 2.11-2.13 rule and a
rule without human confirmation, and a fresh review then found a hole the model could not express
(an id reused by a later finding), which became a teeth config. The value, seen twice: the written
decision, and the replay of every counterexample as a RED case. Running TLC is the cheap part; Java
is a real cost.

Considered for the kit: (i) the rule only (the shipped `adr-refine` asks; the `CLAUDE.md` template
carries it) -- the rule falls back to text that is forgotten; (ii) the rule and the checker in the
engine; (iii) also a CI workflow template -- the kit imposes CI for nothing else. Chosen: ii.
Gating: (i) a gate in every project; (ii) advisory by default, a gate only when the project
declares it. Chosen: ii, the posture of ADR-043 (simplicity) and `golden_required`.

## Decision

1. **The engine owns the check.** `qa_ledger.py model-check` validates, without Java, every ADR from
   the declared point on and every `docs/**/models/models.json` manifest (ADR-059's rules: the
   `model:` field, `ci` + vacuity configs, a safety invariant beyond `TypeOK`, each counterexample
   replaying an AC id present in `ACCEPTANCE.md`). `model-check --run --tier ci|deep` runs TLC.
   `tools/model-check.py` becomes a thin wrapper over the engine: one source, no drift.
2. **Java and TLC are the project's.** `--run` needs `java` and `tla2tools.jar` with the pinned
   sha256 (TLC v1.7.4 in the engine; `model_check.jar` / `model_check.jar_sha256` override it), or
   a runner the project DECLARES in `model_check.tlc_cmd`. Without Java or the jar the run is
   **UNMEASURED** (exit 2), never a pass; a jar that is not the pin is refused (exit 1). The kit
   installs neither; the kit's package gains no dependency.
3. **A run is witnessed** (ADR-055's pattern): `--run` records, per config, the manifest, the
   config, the sha256 of the module and the config, the verdict, the time and the TLC version, in
   the ledger (`model_runs`), with the runner and the sha256 of the config's manifest entry. A
   record whose module, `.cfg` or entry changed since is stale. Only the DECLARED runner records
   (the pinned jar, or the declared `tlc_cmd`): an ad-hoc `--tlc-cmd` runs and prints, and records
   nothing (2.15.0 fresh review: a fake TLC passed a gate).
4. **The boundary is declared.** The rule applies from `model_check.from_adr` (`ADR-NNN`). `uscha
   init` writes it into the generated config: `ADR-001` on a repo with no ADRs, the next free
   number on one that has them (decided while implementing: running `init` is the human's act, and
   "from the next one" is the same boundary `doctor` would propose). For a project initialised
   before 2.15.0, `doctor` proposes the next free number and the human writes it. Without the key
   nothing is read: a project that never opted in sees exactly what it saw before. A re-run of
   `init` keeps a block already declared: the boundary is fixed once. A block that is present but
   cannot be read is named, never silently off, and fails closed when its mode says gate.
5. **Advisory by default.** `readiness` names, only when present: ADRs from the boundary without
   `model:`; broken manifests; `required` models with no recorded run, a stale one, or a red one; an
   unconfirmed agent-written `not-needed` (ADR-044's line already). With
   `model_check.mode: gate` (read case-blind; the stricter of the live config and the ledger's
   frozen copy wins), any of them blocks `pr-ready`, named.
6. **The shipped `adr-refine` asks the question** when the project declares `from_adr`, and the
   `CLAUDE.md` template carries the rule; the agent may write `not-needed`, marked `origin: agent`.
7. **This repo keeps ADR-059's arrangement** (decided while implementing): `tools/model-check.py`
   is a wrapper that passes the repo's boundary (`ADR-059`) and suite to the engine and records
   nothing; the CI `models` job stays the gate; the repo's own `uscha.config.json` declares no
   `model_check`, so its `readiness` is unchanged. The wrapper also asks for strict ADR names and
   the 2.13.0 suite rule (a replayed id must be emitted as `res["ID"]`); the kit's default only
   needs the id quoted in the suite (`model_check.suite_pattern` changes it), and skips a
   `*template*` file in `docs/adr`. Declaring it would make readiness name every
   model "not run", because the release ritual does not run TLC (the release machine need not have
   Java).

## Reasons

- The decision stops being text once it ships with a checker the project can read in `readiness`.
- Advisory first: no project that is running today turns red on upgrade.
- A witnessed run is what lets `readiness` say "the models ran and are green" instead of trusting it.

## Consequences

+ A project can adopt the method's strongest design tool without adopting its CI.
- Java is a real dependency for anyone who wants `--run`; without it the dimension reads UNMEASURED.
- **What a green model proves:** no violation OF THE MODEL at its bounds. The RED replays are the
  only link to the code, and every claim says so (repo rule 2).
- **What a recorded run proves:** that the declared runner printed that verdict for those inputs.
  The ledger and the config are files the agent can write: declaring a fake `tlc_cmd` is an edit
  visible in git, not something the engine can refuse.

## Out of scope

- A CI workflow template for user projects -> later, if asked.
- Installing Java or the jar -> never: the project's toolchain, like its test command.
- PlusCal, Apalache, liveness -> safety invariants only, as in ADR-059.
- Retroactivity: ADRs before `from_adr` are not read.

## Implementation Plan

- Affected paths: `qa_ledger.py` (both twins: `model-check`, `model_runs`, the readiness facts and
  lines, the gate in `_derive_phase`), `tools/model-check.py` (a wrapper), the `adr-refine` SKILL
  twins, `templates/CLAUDE.md`, `uscha.config.json` (template), the root config (`from_adr`,
  `mode: gate`), the command references, READMEs.
- Patterns: ADR-055's witnessed run; ADR-043's advisory-unless-declared; ADR-044's marker.
- Tests: the RED cases below, each red against 2.14.1 first.

## Verification (promoted into ACCEPTANCE.md in 2.15.0)

- [ ] AC-MK-01 -- without `model_check.from_adr` a project's `readiness` and `phase` read exactly as
  in 2.14.1 (byte-identical lines), whatever its ADRs say.
- [ ] AC-MK-02 -- with `from_adr` set, an ADR at or after it without `model:` is named by `readiness`
  (advisory: `phase` unchanged); one before it is not read.
- [ ] AC-MK-03 -- `model-check` (no Java) refuses a broken manifest exactly as `tools/model-check.py`
  did in 2.14.1; the wrapper's output and exit code equal the engine's.
- [ ] AC-MK-04 -- `model-check --run` with a jar whose sha256 is not the pin is refused and runs
  nothing; without `java`, the required model reads UNMEASURED.
- [ ] AC-MK-05 -- a run (stub TLC) is recorded in `model_runs` with the inputs' sha256; editing the
  `.cfg` afterwards makes `readiness` name it stale.
- [ ] AC-MK-06 -- a red recorded run is named by `readiness`; with `mode: gate` it blocks `pr-ready`
  naming the config, and with the default mode it does not.
- [ ] AC-MK-07 -- `uscha init` writes `model_check.from_adr`: `ADR-001` on a repo with no ADRs, the
  next free number on one that has them; `doctor` proposes it to a project that has ADRs and no key.
- [ ] AC-MK-08 -- both `adr-refine` SKILL twins and `templates/CLAUDE.md` carry the question and the
  rule.
- [ ] AC-MK-09..14 -- the 2.15.0 fresh review, each a RED case first: an ad-hoc runner is not
  evidence; a manifest-entry edit makes a run stale; an unconfirmed agent `not-needed` blocks a gate;
  an unreadable block fails closed (mode case-blind, no live downgrade of a frozen gate); the ADR
  template, a symlinked path and a `[]` manifest are handled; a re-run of `init` keeps the block.
