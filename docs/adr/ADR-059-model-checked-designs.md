---
governs:
  - CLAUDE.md
  - docs/adr/INDEX.md
  - uscha-kit/tests/smoke-engine.sh
  - .github/workflows/smoke.yml
  - .github/workflows/publish.yml
  - tools/model-check.py
model: not-needed -- a static check over files plus one CI job that runs a pinned tool; no state an agent can walk through to defeat a rule (origin: agent, confirmed: 2026-11-01)
# ADR-040: the tools this decision fixes, with their support dates (CI and the maintainer's
# machine only -- the kit package gains no dependency)
lifecycle:
  - component: Eclipse Temurin (Java)
    version: "21"
    eol: 2029-12-31
    source: https://adoptium.net/support
    checked: 2026-11-01
  - component: TLA+ tools (tla2tools.jar)
    version: "1.7.4"
    eol: unknown
    source: https://github.com/tlaplus/tlaplus/releases
    checked: 2026-11-01
---
# ADR-059: A design with state and rules is MODEL-CHECKED before it is built — and the decision to model or not is written down, never forgotten

## Status: Accepted (2.13.0) — decided by the owner on 2026-11-01 (an `adr-refine` interview). Repo-level: nothing here ships in the kit package until a later ADR promotes it.

## Context

In 2.11.0 a TLA+ model of the gated-finding debt (`docs/gate-integrity/models/GatedDebt.tla`),
checked with TLC before the code existed, broke the first design with an HONEST agent in 7 steps;
after the code and a fresh review, the extended model found two more holes that neither the code
nor the reviewer had seen. Each counterexample was replayed against the real engine as a RED case
(AC-GI-50..52, -64, -65). The value did not come from "running TLC". It came from three things
together: a rule the reader agrees to, written apart from the design (`NoFlaggedBugShips`); a model
that allows moves the design had not imagined (a lying agent, a removed deferral); and the replay
of every counterexample as a measured case. Without the replay a model is one more opinion.

All three depended on someone remembering. In 2.12.0 the PR hook (ADR-058) was not modelled and
nobody noticed: there was no place where the absence was visible. The pain this ADR removes is
exactly that -- **the next feature with state forgets the step**.

Considered options:

- **A) Text only.** "If the ADR has state and rules, model it" in `adr-refine` and the devloop
  SKILL. Cheap; it is the mechanism that already failed -- it depends on someone reading it.
- **B) A written, checked decision.** Every new ADR declares `model: required` or
  `model: not-needed -- <reason>`; a repo-level check refuses an ADR without the field, and a
  `required` without its model, its bounded CI run and its counterexample cases. It does not force
  a model; it forces a DECISION, auditable with its reason.
- **C) A heuristic.** The engine guesses "this ADR has state" from words or structure. A guess
  presented as a fact, with false positives and negatives. Rejected.

Scope considered: the kit's users (A), only the kit's own development (B), or B first and A once a
second real case exists (C). One case today -- ours. Generalising from one case is the shape the
method refuses, and A also brings a Java dependency into a stdlib-only package.

## Decision

Option B, at repo level first (scope C). Promotion into the kit is a later ADR.

1. **Every ADR numbered 059 or higher declares `model:` in its frontmatter**, one of:
   - `model: required` plus `model_manifest: <path to models.json>`;
   - `model: not-needed -- <reason>`. Written by the agent, the line carries `(origin: agent)`
     (ADR-044) and stays an unconfirmed item until the human appends `confirmed: YYYY-MM-DD`.
   ADRs 001-058 are not retrofitted (the boundary is the number, stated). A new repo rule 12 in
   `CLAUDE.md` says so, and our `adr-refine` interview asks the question because the repo's
   CLAUDE.md requires it -- the shipped skill is not changed by this ADR.
2. **A model lives beside its feature** (repo rule 8): `docs/<feature>/models/`, with a
   `models.json` manifest naming its ADR, its `.tla` module(s) and, per `.cfg`:
   `expect` (`no-error` or `violated: <Invariant>`), `tier` (`ci` or `deep`), and for each
   counterexample the design was changed for, the `AC id` of the RED case that replays it.
   Every manifest carries at least one `ci` config and one **vacuity** config -- an invariant that
   MUST be violated, so a green is never green because nothing can happen.
3. **CI runs the `ci` tier** in one job (ubuntu) with Eclipse Temurin 21 and `tla2tools.jar` from a
   **tagged** TLA+ release pinned by sha256 (v1.7.4 today; never the rolling pre-release, whose
   jar is rebuilt per commit and changes checksum). Each `ci` config must finish in **60 s
   measured**; the job's timeout is 120 s per config; exceeding it is red, naming the config
   ("tighten it or mark it deep"), never a flake. The job **blocks**: `publish.yml` does not
   publish while it is red.
4. **The `deep` tier is run by hand**; its result (date, distinct states, verdict) is recorded in
   the model's README as a local measurement, never as a gate. The suite warns -- advisory -- when
   the `.tla` changed after the recorded deep run.
5. **The suite's check needs no Java** and runs in all six cells: the field on every ADR >= 059; a
   `required` ADR's manifest present and well-formed, with a `ci` and a vacuity config; every AC id
   the manifest names present in `ACCEPTANCE.md` and measured by the smoke suite.
6. **GatedDebt (2.11.0) is the first manifest**, at MaxLog=4 for the `ci` tier and MaxLog=5 as
   `deep`. Not a retroactive gate on ADR-056: the precedent that proves the mechanism on day one.

## Failure behavior

| Event | Behavior |
|---|---|
| TLC's verdict differs from `expect` | red, naming config, expected and obtained invariant, first 15 lines of the trace. A `no-error` that breaks means the design moved: update the model or the code, never the manifest to go green |
| jar download fails, or its sha256 differs | red, fail-closed, after ONE retry; the jar is cached by sha256 |
| a `ci` config exceeds 120 s | red, naming it: tighten the bounds or mark it `deep` |
| missing/malformed manifest, missing `.cfg`, no `ci` or no vacuity config | red in the main suite (six cells, no Java) |
| an AC id in the manifest absent from `ACCEPTANCE.md` or the smoke suite | red in the main suite |
| an ADR >= 059 without `model:` | red in the main suite, naming the ADR |
| `model: not-needed` written by the agent, unconfirmed | an unconfirmed agent-origin item, printed by `readiness` (ADR-044's advisory line) |
| deep result older than the latest change to the `.tla` | advisory warning, names the model |

## Measured before deciding (2026-11-01, GatedDebt, TLC v1.7.4, 2 workers, the suite running alongside)

| config | MaxLog=4 | MaxLog=5 |
|---|---|---|
| shipped-2.11.0 (expect no-error) | 42 s, 2,936,010 states | 500 s, 46,976,202 states |
| shipped-2.11.0-vacuity (expect violated) | 1 s | 1 s |
| as-specified (expect violated) | 2 s | 1 s |
| proposed-lying-agent (expect no-error) | 3 s | 15 s |

The bound keeps its teeth: with both 2.11.0 fixes reverted, or the Memory fix alone, MaxLog=4
still finds the hole (1 s and 2 s). So `ci` = MaxLog=4 and `deep` = MaxLog=5.

**Found while building it** (the manifest's teeth configs, 2026-11-01): with the Memory fix in place,
reverting the deferral-closure fix alone is NOT a violation at MaxLog=4 -- Memory already refuses
that path. The engine keeps both rules (defense in depth, and AC-GI-64 pins the closure message);
the manifest's teeth config for AC-GI-64 therefore reverts both, and says why. The model gained two
constants, `DeferFix` and `MemoryFix`, so the fixes TLC forced are named in the model itself.

## Stack and lifecycle

The machine-readable block is in this ADR's frontmatter (ADR-040).

Temurin 21 is listed "at least Dec 2029" (Adoptium's own wording: a floor, not a date). The TLA+
tools publish no support window; `eol: unknown` is a named absence. Both live only in CI and on the
maintainer's machine -- the kit package gains no dependency.

## Reasons

- The absence of a decision becomes visible, which is the pain named; the decision itself stays
  human, with its reason on record.
- The replay as a RED case is what makes a model evidence instead of narration; the manifest makes
  that link checkable.
- The bounded `ci` tier keeps the six-cell suite pure Python and keeps CI time sane; the vacuity
  config keeps a green honest.

## Consequences

+ The next feature with state cannot silently skip the step.
+ A model drifting from the design turns CI red instead of rotting in `docs/`.
- One more CI job, Java on one runner, and a pinned jar to bump by hand.
- Writing `not-needed` costs one line and one human confirmation per ADR.
- **What a green model proves:** TLC found no violation OF THE MODEL at the declared bounds. It
  does not prove the engine matches the model; the RED replays are the only link, and every
  published claim says so (repo rule 2).

## Out of scope

- Promoting to the kit (the shipped `adr-refine` skill, user projects, Java in the package) -> a
  later ADR, once a second real case exists.
- Generating statecharts/diagrams from the `.tla` -> later, optional (the pstack `statechart`
  skill stays available by hand).
- PlusCal, Apalache, and liveness/temporal properties -> safety invariants only.
- Checking that the model matches the code -> not attempted; the RED replay is the link.

## Implementation Plan

- Affected paths: `CLAUDE.md` (rule 12), `tools/model-check.py` (runs a manifest's tier, compares
  verdicts, prints traces), `docs/gate-integrity/models/models.json` + `ci` cfgs at MaxLog=4,
  `.github/workflows/smoke.yml` (the `models` job), `.github/workflows/publish.yml` (waits on it),
  `uscha-kit/tests/smoke-engine.sh` (the no-Java check), `ACCEPTANCE.md`, `docs/adr/INDEX.md`.
- Patterns: the AC-03 repo-level scan (every tracked file); `publish.yml`'s existing wait on the
  tag's run; ADR-044's markers for the unconfirmed `not-needed`.
- Tests: the RED cases below, each red before the code exists.

## Verification (promoted into ACCEPTANCE.md in 2.13.0)

- [ ] AC-MC-01 -- an ADR numbered >= 059 without `model:` turns the suite red, naming the ADR; ADRs
  <= 058 are not read.
- [ ] AC-MC-02 -- `model: not-needed -- <reason> (origin: agent)` is reported by `readiness` as an
  unconfirmed agent-origin item, and stops being reported once `confirmed: YYYY-MM-DD` is appended.
- [ ] AC-MC-03 -- `model: required` without its manifest, or a manifest without a `ci` config or
  without a vacuity config, turns the suite red, naming what is missing.
- [ ] AC-MC-04 -- an AC id named in a manifest that is absent from `ACCEPTANCE.md` or from the
  smoke suite turns the suite red.
- [ ] AC-MC-05 -- `run` compares every verdict with `expect`, prints the trace when they differ and
  turns a config over the limit red (measured in the suite with a stub TLC); the `models` job runs
  GatedDebt's `ci` tier, whose teeth configs revert the 2.11.0 fixes and MUST break.
- [ ] AC-MC-06 -- a jar whose sha256 differs from the pin: red, and TLC never runs.
- [ ] AC-MC-07 -- a `.tla` changed after its recorded deep run: an advisory warning naming the
  model; the exit code does not change.
- [ ] AC-MC-08 -- `publish.yml` does not publish while the tag's `models` job is red.
