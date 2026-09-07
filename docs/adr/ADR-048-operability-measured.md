---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/.claude/skills/uscha-devloop/SKILL.md
  - uscha-kit/skills/uscha-devloop/SKILL.md
  - uscha-kit/.claude/skills/uscha-discovery/SKILL.md
  - uscha-kit/skills/uscha-discovery/SKILL.md
  - uscha-kit/templates/CONSTITUTION.md
---
# ADR-048: Operability is a MEASURED dimension — CI, release, RUNBOOK and seed are facts in the tree, not phase-8 prose

## Status: Proposed

## Context

A field finding, twice in a row: **release by CI, the reset/seed script and the RUNBOOK arrived
in the last week of two projects.** Not because anybody decided to defer them — because nothing
ever asked. The devloop NAMES them, in phase 8, in prose:

> Phase 8 — Hand off to docs + retrospective

and prose is the one thing this kit has spent its whole life replacing. Every other dimension
that used to live in a checklist — coverage, gate integrity, the golden suite, the stack's
expiry date, the simplicity budget — became something the engine READS. Operability did not, so
"we do that at the end" survived every gate the kit has, in projects running profile E.

The shape is familiar: a **narrated dimension**. A narrated dimension is not a weak gate, it is
an absent one — it produces exactly the same output whether the work was done or forgotten, and
by the time anybody looks, the answer is "next week". The fix has been the same every time:
find the FACT behind the prose and read it.

There is a fact behind each of the four:

- a workflow file whose steps run the repo's own configured test command;
- a workflow that publishes or attaches a release asset;
- a `RUNBOOK.md` that exists and names the four things an operator needs at 3am;
- a seed/reset command the config declares, whose script is actually on disk.

None of these says the work is GOOD. A RUNBOOK with a `## Rollback` heading may hold a wrong
procedure; a workflow that runs `pytest` may test nothing. The engine can see that the artifact
exists and that the question was asked — which is the entire difference between a project that
has thought about rollback and one that has not yet. Confusing those two is what this ADR is
for; pretending to grade them would be the invented judgment ADR-014 refuses.

## Decision

**1. A new subcommand `operability --repo R [--json]`** that verifies FACTS IN THE TREE, never
prose and never a claim. Four checks, each reporting `ok` / `missing` / `unknown` with a detail
that SAYS what it matched, so a human can disagree with the match instead of with a boolean:

| check | what it reads |
|---|---|
| `ci` | a workflow under `.github/workflows/*.yml` whose steps run the repo's **configured** test command (`repos[R].test_command`, else `defaults.test_command_<type>`) — matched verbatim, or its first token beside a test-ish subcommand on the same line |
| `release` | a workflow that publishes or attaches an asset, by a short **documented recogniser list**: `softprops/action-gh-release`, `actions/upload-release-asset`, `gh release create`, `gh release upload`, `gh release`, `npm publish`, `twine upload` |
| `runbook` | `docs/RUNBOOK.md` (or `RUNBOOK.md`, or `defaults.operability.runbook`) exists AND names the four headings — start/boot, config, rollback, smoke — matched case-insensitively in EN and ES (`arranque\|start\|boot`, `config`, `rollback\|reversi`, `smoke\|humo`), NAMING the ones that are absent |
| `seed` | a seed/reset command declared in `repos[R].operability.seed_command` or `defaults.operability.seed_command`, whose script exists on disk when the command names a path |

Both trees are searched, repo path first and the **config root** second, with `realpath` on both
sides — the monorepo lesson `spec-drift` paid for in 2.2.0 (one `.github/` and one RUNBOOK at the
root, `repos[R].path` one level down) and the Windows 8.3 lesson of 2026-08-02, in one helper.
The output NAMES which tree it read.

The command **never executes anything** (ADR-008: the engine is not an executor of
config-supplied shell — it reads the test command, it does not run it) and **its own exit code
is always 0**. Whether the verdict gates is not this command's decision.

**2. GitHub Actions is the only pipeline read, and another one is `unknown`, never a failure.**
A `.gitlab-ci.yml` / `Jenkinsfile` / `azure-pipelines.yml` is NAMED as `unknown ci system`.
Failing it would be a red nobody measured; passing it would be a green nobody measured, and
under a declared gate that second one is the false clean ADR-043 exists to refuse. So the verdict
has three states, not two — see point 4.

**3. The verdict is persisted as `gate:operability` through the existing FACT-gate plumbing**
(`_append_gate_record`), so there is no parallel mechanism: `_gate_open_and_sev` feeds the
readiness cap, `_converged` refuses while the latest record is failing, and the gates rollup
shows it beside every other gate. `log-gate --kind operability` is admitted to the closed `--kind`
vocabulary for parity, so a project whose CI computes the four facts elsewhere can record them
the same way; the subcommand is what normally writes it.

**4. The posture is the PROFILE's, done the 2.0.0 way.** A new knob `defaults.operability.gate`,
`false` by the engine's own default, `true` in risk presets **C, D and E** — which makes it a
profile-OWNED knob, listed in `RISK_PROFILES` and therefore covered by AC-RP-06 (`init` writes no
profile-owned knob) and reported by `doctor` with its origin on the three-rung ladder, exactly
like `coverage_threshold` and `golden_required`.

- `gate: false` (A, B, or no profile) → the record is persisted **advisory**: it never joins the
  `N ok` count, caps nothing and blocks nothing. `operability` therefore joins
  `ADVISORY_CAPABLE_KINDS`. This widens WHEN it gates, never WHAT counts as evidence — the line
  INV-ADVISORY-01 draws.
- `gate: true` → any check `missing` persists **fail**: readiness capped ≤65, convergence
  blocked, and `phase --require pr-ready` refuses **naming the missing check**, because
  `static-gate gated=1 (gate:operability:1)` tells a human the gate is red without telling them
  whether to write a workflow or a RUNBOOK.
- `gate: true`, nothing missing, something `unknown` → **advisory**, not `pass`. A pipeline this
  engine cannot read is UNMEASURED, and recording UNMEASURED as a clean gate would hand a
  declared gate a green nobody measured.

Because `init` freezes the expanded profile into the ledger's config, `_resolved_defaults` now
reads `_risk_profile_keys` — written by `_apply_risk_profile` for exactly this purpose, and
already read this way by the golden cap — so a profile-supplied knob is reported as
`profile <X>` on the frozen copy instead of masquerading as a human `override`.

**5. Readiness shows it on one line, conditional on a record existing** (house rule: speak only
when it matters):

```
--- operability: ci ok · release missing · runbook ok · seed missing (advisory)
```

A ledger that never ran the check prints exactly what it printed before.

**6. The skills say so.** The devloop's phase 8 now RUNS `operability` and logs it, and the PR
body cites the line; discovery's grilling agenda gains a day-1 item — *who owns the RUNBOOK and
the seed?* — because the cheapest moment to decide that is before anything is built.

## Consequences

+ Operability stops being a promise and becomes a number a human can read on any project the kit
  governs, on day 1 as easily as in the last week.
+ A project on profile C/D/E now has to write the four artifacts to reach `pr-ready`, which is
  what "high risk" was supposed to mean all along.
+ Profiles A and B change nothing: the check measures and records advisory. A kit that gated
  release + reset + RUNBOOK on every project would be the kit's opinion wearing an exit code —
  the same thing ADR-043 refused for the simplicity budget.
- One more subcommand, and the subcommand count is a published fact: five surfaces move with it.
- The recogniser lists are OPINIONS about how projects publish and reset. They are short,
  documented, and printed in the detail, so a project the list does not fit can see WHY it read
  `missing` instead of guessing.

## What this ADR does NOT decide

- It does not grade the RUNBOOK, the workflow or the seed script. Existence and named sections
  are what a stdlib engine can honestly see; whether the rollback procedure is correct is the
  human's, and it is not pretended here.
- It does not run anything — not the tests, not the seed, not the pipeline.
- It does not read CI systems other than GitHub Actions. Adding one is adding a reader, and a
  reader that guesses is worse than an honest `unknown`.
- It does not make the check mandatory on A or B, and does not let a project turn it into a gate
  by accident: the knob is a declaration.

## Acceptance

Family `AC-OP-01..08`, measured by smoke **T165** over real temp projects:

- **AC-OP-01** — without a CI workflow, `operability` reports `ci: missing`, exits 0, and under
  profile B the record is advisory: non-blocking, never counted as `ok`.
- **AC-OP-02** — under profile E an absent RUNBOOK persists `fail`, the rollup row is blocking,
  and `phase --require pr-ready` refuses NAMING `runbook missing`.
- **AC-OP-03** — the CONTROL PAIR: the same complete tree reads `pass` under E and `advisory`
  under B, with an identical note; readiness prints the one line, and prints nothing at all when
  no record exists.
- **AC-OP-04** — a RUNBOOK that exists but skips a section reports `missing sections (rollback,
  smoke)` and names the file it read.
- **AC-OP-05** — a declared `seed_command` whose script is not on disk reads
  `seed: missing (script not found: scripts/seed.py)`.
- **AC-OP-06** — the generated config declares no `operability` knob, and `doctor` reports
  `effective operability.gate = True` with origin `profile E`, exit code unchanged.
- **AC-OP-07** — a non-Actions CI is NAMED `unknown`, and with nothing missing the record stays
  advisory even under a declared gate.
- **AC-OP-08** — the RED PROBE: the `v2.1.0` engine has no `operability` subcommand, refuses
  `log-gate --kind operability` at the parser, and its `doctor --json` knows no
  `operability.gate`. `None` = UNMEASURED without git.

## Alternatives considered

**Leave it in the devloop prose and trust phase 8.** Rejected: that is the status quo, and the
status quo produced the finding twice.

**Gate it on every profile.** Rejected on the kit's own doctrine (ADR-043): a budget the kit
invented and exits 1 on is an opinion wearing an exit code. The profile is the human's
declaration of how much process this deserves; operability belongs in that declaration.

**Score it 0..100 and feed a readiness dimension.** Rejected: four booleans do not make a
percentage, and a number invented from them would be exactly the narrated metric this replaces.
The gates rollup and one conditional line say everything there is honestly to say.

**Read the RUNBOOK's contents and grade the procedures.** Rejected: that is an LLM judgment, and
an LLM judgment does not become a gate by being important (INV-ADVISORY-01).

**A `runbook-check` plus a `ci-check` plus a `seed-check`.** Rejected: three subcommands for one
question, three rows in five published surfaces, and three records where the human needs one
line. Operability is one dimension.
