# uscha-kit 2.0.0 — the risk profile had been outranked by the kit's own defaults, in every repo the kit set up (2026-09-07)

## The finding

Reported as U-02 of an external review and reproduced here. `risk_profile` (ADR-001) expands a
named preset into knobs the config already understands, under one rule: **an explicit
declaration wins per key**. That rule was implemented correctly. What nobody had measured was
where the explicit declarations came from.

`uscha init` copied `uscha-kit/uscha.config.json` — the kit's COMPREHENSIVE REFERENCE, every
knob at the kit's value — into the project. So every kit default arrived in the project as an
explicit declaration, and by ADR-001's own rule it outranked the profile. Measured on 1.99.0,
through the shipped installer and the shipped engine:

    1.99.0 + profile A -> qa_tools_order = ['code-review', 'judgment-day', 'improve']
       _risk_profile_keys = []
    1.99.0 + profile E -> coverage_threshold = 60 | golden_required = True
       _risk_profile_keys = ['golden_required']

`_risk_profile_keys` is the engine's own record of what the preset supplied. Under profile A it
is **empty**: that profile owns exactly one knob, `qa_tools_order`, and the copy had already
declared it. So profile A, which exists to say "this change is trivial, run code-review and
stop", still required judgment-day and improve to converge. Profile E fared no better where it
mattered — the copied `coverage_threshold: 60` outranked its 80 — and the one knob it did get
through, `golden_required`, got through only because the reference config happens not to
declare that key. A preset whose reach is decided by which keys the installer omitted is not a
preset modulating the flow. The same config as a bare `{}` plus the profile resolved
correctly — `['code-review']` — which is what makes this a delivery defect rather than a logic
one: the presets worked everywhere except in the repos the kit itself had initialised, which is
every repo that ever ran `uscha init`.

The engine was doing exactly what it was told. The installer was telling it the wrong thing.

## The fix: `init` generates, it no longer copies

`init` now GENERATES a minimal project config. It declares only what the engine cannot derive:
the project name, the repo it detected (name, path, type) with the test command for that type,
and the five knobs whose engine default is absent or differs from the kit's intent —
`acceptance_file` (engine default: none), `id_granularity` (engine default `line`, kit `file`),
`max_iterations` (read by the `uscha-devloop` SKILL, which has no fallback of its own), and the
`fast_path` block (copied whole from the reference) and `integration` (the switch only: its
contract command names a build system, and guessing one is what the generator refuses). Those last two are the
floor under "minimal": the engine defaults both to OFF, so omitting them would make
`fastpath-eval` answer `DENY configured: false` on every fresh project and readiness measure
five dimensions instead of six — generating instead of copying would have turned two shipped
features off in silence. No risk profile owns any of the five. A generated file for a python
repo is 33 lines. It declares **no knob any profile owns**.

The kit's `uscha.config.json` stays where it is and gains a `_comment` saying what it now is:
a reference to read and copy from, never a file to install. Copy a block out of it when you
mean to override the engine default or the preset — which is exactly the decision the copy used
to make for you, silently, for all of them.

Precedence is unchanged, and that is the point: **explicit override > selected profile > engine
default**, in the engine's output and in the skill's review sequence. What changed is that a
project no longer arrives pre-loaded with explicit overrides it never chose.

**What earns the MAJOR.** One thing, and it is a shape change, not a behaviour change: `uscha
init` writes a different file than it used to, so a NEW project's `uscha.config.json` is no
longer the kit's reference and any tooling that assumed the copy will not find it. Nothing in
an existing project changes — configs already on disk are untouched, `readiness --json` over an
existing ledger is byte-identical to 1.99.0 (`AC-RP-04`), and no knob was renamed, removed or
re-defaulted. The version is 2.0.0 because the installer's OUTPUT CONTRACT changed, not because
the engine did.

## The fix is to stop copying — and deliberately NOT to start injecting

The first version of this patch did the obvious symmetric thing: a new `ENGINE_DEFAULTS` table
materialized into `defaults` at config load, so a minimal config would carry the kit's values
explicitly and the ledger would freeze the effective settings in full. It was written, it was
green on the new family, and the golden killed it.

`AC-FP-08` freezes the engine's ENTRY behaviour — a canonical `init -> log-step -> readiness ->
phase -> converged` session over a config that declares almost nothing — captured before
fast-path existed and approved by a human. Against the injecting engine it read:

    - "thresholds_declared": { "coverage_threshold": false }
    + "thresholds_declared": { "coverage_threshold": true }
    - "convergence_reasons": ["only 1 agent steps (need a full cycle of 3)"]
    + "convergence_reasons": ["agent tools never ran: judgment-day,improve"]

The first line is the one that matters. `thresholds_declared` is the provenance machinery of
1.17.0: it tells a human requirement apart from a kit default by KEY PRESENCE. Writing the kit's
own 60 into `defaults` made it report as something a human had required. That is the exact
confusion that let a copied config outrank the profile, pointed the other way — and it would
have arrived inside the release that fixes it.

So `ENGINE_DEFAULTS` stays, and it is a REPORTING table: `doctor` reads it for the bottom rung
of the ladder, `init` never writes it, and a knob nobody declared stays ABSENT everywhere the
engine reads it — resolving through the inline fallbacks it always had. Its `qa_tools_order`
entry is `None` for the same honesty: with no list declared, convergence falls back to a window
of `--tools-per-cycle` agent steps, so there is no default list to name and `doctor` says
`not declared` instead of inventing one. The golden was not edited, and it was never going to
be: the agent may not write an `.approved` (INV-GOLDEN-01), which is why the hook exists and why
it is the design that moved.

## `doctor` says what is in force, and where it came from

The diagnostic that would have caught this in a minute. `qa_ledger.py doctor` now prints each
profile-owned knob with its effective value and its origin, and `--json` carries the same under
`risk_profile` and `effective`:

    [OK] risk profile: E
         effective settings below - precedence: override > profile > default
    [OK] effective qa_tools_order = code-review, judgment-day, improve
         origin: profile E
    [OK] effective coverage_threshold = 60
         origin: override - this override supersedes profile E (information: an explicit
         declaration is how a preset is bent)
    [OK] effective golden_required = True
         origin: profile E

An override that supersedes a profile is INFORMATION, not a warning and not an error:
declaring a knob by hand is the documented way to bend a preset. The same resolution feeds the
QA-skills check further down, so a profile-A project no longer reports judgment-day and improve
as missing skills it needs. No new command, no new flag, no recurring confirmation — the
existing `doctor` block, four lines longer.

Resolving the profile inside `doctor` came with a trap the review caught before release.
`_apply_risk_profile` raises `SystemExit` on an unknown profile (INV-RISK-01: a declared risk
level is never inert, and `init` refuses such a config), and the config block's existing
`except SystemExit` sat around the WHOLE block — so `risk_profile: "Z"` would have made a
diagnostic go blind exactly when it is needed, abandoning the toolchain, rubric and ledger
checks below and flipping the verdict to ERROR/exit 1 where 1.99.0 said WARN/exit 0. The catch
is now local to the resolution: one named line (`unknown risk profile 'Z' - no preset applied`),
`effective` reported as `null`, every other check still run, and the verdict left where 1.99.0
had it. A new REPORT may not silently raise an existing exit code. Pinned in T42.

The same section's "no config here" hint used to say *copy the kit `uscha.config.json` to the
repo root* — the instruction that produced this defect one project at a time. It now points at
`uscha init` and says why the copy is the wrong move.

## The skill's side is a STATIC instruction check, not agent evidence

The `uscha-devloop` SKILL.md now tells the orchestrator to read the EFFECTIVE order rather than
the config file — `doctor --json` reports it as `effective.qa_tools_order` with its origin, and
the ledger froze the same value at `init` — and states that a profile-A project runs
`code-review` only, must not invoke judgment-day or improve, and must not wait for them to
converge. That is a **static instruction check**: this release asserts what the skill file
instructs, not what a real agent executed. The engine half is measured; the orchestrator half is
written down. Saying otherwise would be the narration this kit exists to refuse.

## Existing projects: nothing is deleted, nothing moves

A config that already carries the full copy keeps every value in it. `readiness --json` over the
same ledger is byte-identical between the `v1.99.0` engine and this one, and `init` freezes the
same `defaults` key for key (`AC-RP-04`). This is
not conservatism for its own sake: a value equal to a former default is indistinguishable from a
value a human chose, and authorship cannot be recovered from equality. An installer that
"cleaned up" the copy would be guessing about the one thing it must not guess about.

So the migration is manual and it is three lines. `doctor` names the keys — they read
`origin: override` — and you delete the ones you never meant to declare:

    {
      "defaults": {
    -   "coverage_threshold": 60,
    -   "qa_tools_order": ["code-review", "judgment-day", "improve"],
    +   "risk_profile": "A",
        "acceptance_file": "ACCEPTANCE.md"
      }
    }

The kit README's config section carries the same example, and ADR-001's amendment records why
the deletion is the human's.

## `init` also does slightly more than it did

It detects the repo's toolchain from the one marker file each build system leaves at its root
(`pom.xml`, `pubspec.yaml`, `go.mod`, `Cargo.toml`, `Package.swift`, `build.gradle`,
`pyproject.toml`/`setup.py`, `CMakeLists.txt`, `package.json`, `*.csproj`/`*.sln`) and writes
that one repo with its test command. Nothing recognised means `repos: []` and a human who
declares them — never a guess. The old behaviour was ten example repos pointing at
`../backend-api` and friends, every one of which had to be deleted by hand.

Idempotence and the conflict rules are unchanged: the generated bytes are deterministic, so a
second `init` on an untouched project reports `unchanged`, and a config the user edited is
reported as a conflict and left alone (`AC-RP-05`, the T85 idiom). T85 itself, T89 and T72's
conflict trio are green.

## Verification

New family `AC-RP-01..06`, smoke `T158`, sidecar `.rp-cases.json`. Four of the six are RED
against the v1.99.0 installer and engine and green against this one:

    BAD AC-RP-01,AC-RP-02,AC-RP-03,AC-RP-06 | AC-RP-01: qa_tools_order=None, expected
    [code-review] ; AC-RP-06: generated config declares profile-owned knob(s):
    coverage_threshold, qa_tools_order

The other two cannot be red before the change and are not pretended to be. `AC-RP-04` is a
NO-REGRESSION pin — it asserts the old behaviour survives, so it is green on both sides by
construction — and `AC-RP-05` pins the `init` guarantees that must SURVIVE generation, likewise
green before and after. A preservation pin dressed up as a red would be a fixture measuring the
wrong thing, which is the 1.98.1 lesson.

`AC-RP-04` reads the tagged `v1.99.0` engine out of git; without it (no git, a shallow clone,
an extracted kit) it reports None = UNMEASURED, never a silent pass. Both of its halves are
timing-free — one ledger read by both engines, and two inits compared on `defaults` only — so
the case can never measure whether the runner crossed a second boundary.

`AC-RP-06` is the criterion that would have caught the original defect, and it is deliberately
not about values: it asserts the generated config declares NO knob any preset owns, whatever
that knob's value would have been. The owned set is read from the engine's own `RISK_PROFILES`
table, so a knob added to a preset later is covered the day it is added.

Acceptance goes 252 → 258 criteria; nothing was dropped. `ADR-001`'s Status line carries the
amendment and the `docs/adr/INDEX.md` row copies it verbatim, as `AC-DC-04` requires.

## Not in this release

The `uscha-devloop` skill actually SKIPPING sub-agents by profile is still what ADR-001 called
it in 1.45.0: orchestrator behaviour, not deterministic engine logic. It is instructed here and
measured nowhere, and the token saving stays an out-of-scope claim until an arm measures it.

Suite: 448 checks · 0 fail; acceptance 257/258.
