# uscha-kit 2.1.0 — the simplicity gate stopped loops with a budget nobody had declared (2026-09-07)

## The finding

Reported as U-01 of an external review, reproduced on 1.99.0 and unchanged on 2.0.0.

`simplicity-check` scores a diff against seven budgets and exits 1 on `OVERBUILT`. Every one of
those numbers is a value the KIT chose — 400 added lines, nesting depth 4, 120 lines per hunk —
and the kit has a doctrine about numbers like these. 1.17.0 built `thresholds_declared` so a
reader can tell a **requirement** (declared by the human in `uscha.config.json`) from an
**opinion** (the kit's default), and `readiness` labels every threshold with its provenance for
exactly that reason.

`simplicity-check` printed the doctrine and then contradicted it:

    SIMPLICITY: 60.0/100 - OVERBUILT
      max_nesting             9 / 4
      (every budget is a kit default - an opinion, not a requirement:
       declare yours in config.defaults.simplicity)
      ! nesting 9 > 4 - aplanar: guard clauses / extraer funcion (CWE-1124)
    exit 1        budgets_declared: []

That is the real reproduction, and the diff that produced it is **six added lines**:

    +result = some_function(argument_one,
    +                                    argument_two,
    +                                    argument_three)
    +def f():
    +    return 1

One file. No new type. No block deeper than one. What scored 9 is the continuation line indented
36 columns — because `max_nesting` does not measure nesting. It measures **leading indentation on
added lines**, divided by `indent_width`. It is 30% of the score, and the hard cap floors the
result at 60 when it exceeds its budget by more than three, so a wrapped call argument alone is
enough to reach `OVERBUILT`. The field note that opened the review says the same thing from the
other end: *"el proxy de anidamiento se dispara con JSX y con literales multilinea en Java."*

And the verdict did not merely print. The `uscha-devloop` skill persists it with
`log-gate --kind simplicity`, a failing fact gate caps readiness at 65 and blocks convergence,
and `readiness` reads the persisted state — so an opinion the project had never adopted stopped
the loop, and the only way out was to edit a diff to satisfy a number nobody had chosen.

## The fix: the score advises; only a declaration can make it gate

`simplicity-check` now exits **0** and reports its verdict as information, unless the project has
BOTH declared at least one numeric budget AND set `defaults.simplicity.gate: true` (or passed
`--gate`). With both, behaviour is exactly what it was: `OVERBUILT` is exit 1 and a BLOCKER.

`gate: true` with **no** budget declared is a configuration error — exit 2, naming the key. A
gate with no budget is not a gate; it is the same opinion wearing an exit code, and silently
demoting it to advisory would hide a config the human got wrong. `indent_width` is a parsing
parameter and `gate` is the switch itself, so declaring only those does not satisfy the
requirement either.

The mode travels: JSON gains `mode: "advisory" | "gate"` beside the existing `budgets_declared`,
and the human line reads `OVERBUILT  (advisory (declare budgets + defaults.simplicity.gate to
make it block))`.

**The score did not change.** Not the weights, not the bands, not the hard cap, not the
heavy-dimension floor. A diff that scored `OVERBUILT/60` before scores `OVERBUILT/60` now. The
measurement was never the defect; the unearned authority was — which is also why this is not
INV-ADVISORY-01. That invariant (ADR-014) quarantines LLM-class *judgment*, and simplicity is
deterministic arithmetic that may gate the moment a human declares it. What moved is
**provenance**, the 1.17.0 rule, applied to an exit code.

It is also the posture `waste-check` has had since 1.26.0. The two halves of "Reduce /
REUSE-FIRST" now behave the same way, which is one rule to learn instead of two.

## `max_nesting` is named as the proxy it is

The config key (`max_nesting_depth`) and the metric key (`max_nesting`) are **unchanged** —
breaking them for a labelling fix would break every config and every consumer. What changed is
what the output calls it: the report row reads `max_nesting (indentation proxy)`, a line under
the table spells out what it measures, the nesting **flag** — the line a human actually acts on —
carries the caveat, and JSON gains `metrics_notes.max_nesting` with the same sentence.

The kit does **not** make it language-aware. Doing that honestly needs a parser per stack, which
a stdlib-only engine will not have, and a half-parser would trade a proxy a reader can discount
for a proxy a reader would trust.

## The ledger can now say "measured, but not gating"

The consumer half is the one that could have gone wrong quietly. An advisory verdict persisted as
`pass` would be a **false clean**: a reader cannot tell "the gate ran and was green" from "there
was no gate", and the second is what happened. A gate that blocks wrongly is loud; a gate that
passes wrongly is silent.

So `log-gate --verdict advisory` is a third verdict beside `pass`, `fail` and `not-run`. It
writes a static-gate record with zero gated findings — it can neither cap readiness nor block
convergence — stamped `advisory: true`, and every surface reads the stamp:

| surface | a real clean gate | an advisory run |
|---|---|---|
| `readiness` gates line | counted in `N ok` | `· 1 advisory (repo/gate:simplicity)`, never in `N ok` |
| `readiness --json` `gates[]` | `advisory: false` | `advisory: true, blocking: false` |
| mirador subscore | `OK` | `ADVISORY` |
| `top` feed | `pass — clean` | `info — advisory, measured, not gating` |

The advisory segment is conditional, so a ledger with no advisory record prints byte-identically
to before. It is a named verdict rather than a refusal for a reason worth stating: `log-gate`
cannot observe which mode a separate `simplicity-check` process ran in, so a refusal would rest
on the caller's goodwill while a named verdict rests on the ledger.

## No risk profile owns it

`RISK_PROFILES` owns three knobs and none is a simplicity budget, so no preset sets `gate`
either: turning the gate on stays a human declaration under every profile A–E. `AC-SG-06` reads
that from the engine's own table, so a preset that starts owning one goes red the day it does and
the decision gets made explicitly. `uscha init` writes no simplicity block and must not start —
with advisory as the engine default there is no kit intent that differs from it, which is the
only reason the 2.0.0 generator writes a knob at all. `AC-RP-06` (T158) is unchanged and green.

## What is measured

Smoke **T159**, `AC-SG-01..08`, over real temp projects and the real engine: the advisory default
(exit 0, `mode: advisory`, `budgets_declared: []`, and the verdict still `OVERBUILT` — the case
measures a softened exit, never a softened score); the declared gate unchanged (exit 1, and a
clean diff still exit 0 under the same config); the refusal (exit 2, key named, no score
printed); the ledger half against a control (the same gate logged `fail` blocks and turns the
line red, so the advisory half measures a difference rather than an absence); the field fixture
with the proxy named in report, flag and JSON and both keys unchanged; the profile/installer
pins; and `AC-SG-07`, the **red probe** — the `v2.0.0` engine run on the AC-SG-01 fixture must
exit 1 there, and reports UNMEASURED rather than passing when git or the tagged copy is absent;
and `AC-SG-08`, the boundary the fresh review asked for — `--verdict advisory` is accepted only
for `simplicity` and `waste`, and `gate-check`/`golden-diff`/`pit-check`/`regression` refuse it
with exit 2 and an untouched ledger, because a FACT gate recorded as advisory would be a
mandatory gate cleared by goodwill.

Two probes were run against this release's own engine before it shipped: restoring the 2.0.0 exit
rule turns AC-SG-01, -02, -05 and -07 red, and folding the advisory back into the `ok` count
turns AC-SG-04 red. A criterion that cannot go red measures nothing.

T10 changed with the behaviour: the historical `1.9x budget -> exit 1` check now passes `--gate`,
and asserts the same diff without it exits 0. The score it pins (the heavy-dimension floor) is
untouched.

Acceptance goes 258 → 266 criteria; nothing was dropped.

## The claim moved where it was published

Repo rule 2, in the same change: the devloop SKILL (both skill trees), `uscha-kit/README.md`,
`templates/CONSTITUTION.md`, the field-manual decks in both languages (canonical and deployed
copies, equal changed-line counts so `AC-VC-02` stays green) and the paper's check table, where
`simplicity-check` moves from `blocks` to `advises*` — the column that already means "gates only
under explicit human declaration (configuration or flag)".

## Breaking change, and who it breaks

A project that HAD declared simplicity budgets and relied on the gate loses it until it adds one
line, `"gate": true`. This is deliberate. The alternative — inferring the gate from the presence
of budgets — would mean a project that wrote its budgets down as documentation silently acquired
a blocker, which is the same failure this release removes with a different trigger.

## Not in this release

`max_nesting` is not fixed, because it is not broken — it is a proxy, and it now says so. Making
it AST-aware needs nine parsers a stdlib-only engine will not have, and a correct nesting number
gated against a budget nobody declared would still be an opinion with an exit code.

Suite: 450 checks · 0 fail; acceptance 265/266.
