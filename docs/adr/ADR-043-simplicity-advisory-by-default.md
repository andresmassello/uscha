---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/.claude/skills/uscha-devloop/SKILL.md
  - uscha-kit/skills/uscha-devloop/SKILL.md
  - uscha-kit/uscha.config.json
  - uscha-kit/templates/CONSTITUTION.md
---
# ADR-043: The simplicity score ADVISES by default — only a declared budget can make it gate, and `max_nesting` is named as the indentation proxy it is

## Status: Proposed

## Context

`simplicity-check` scores a diff against seven budgets and exits 1 on `OVERBUILT`. Every one of
those budgets is a number the KIT chose: 400 added lines, depth 4, 120 lines per hunk. The kit
has a doctrine about numbers like these — 1.17.0 built `thresholds_declared` precisely so a
reader can tell a **requirement** (the human declared it in `uscha.config.json`) from an
**opinion** (the kit's default), and `readiness` labels every threshold with its provenance for
exactly that reason.

`simplicity-check` did not follow it. It printed the honest sentence —

> `(every budget is a kit default — an opinion, not a requirement: declare yours in
> config.defaults.simplicity)`

— and then exited 1 anyway. A project that had adopted no budget at all was stopped by an
opinion, and the same JSON that stopped it reported `budgets_declared: []`. The doctrine was in
the output; the exit code contradicted it.

Two facts made this worse than an aesthetic inconsistency.

**The dominant dimension is a proxy that misfires.** `max_nesting` is 30% of the score, and it
does not measure nesting: it measures **leading indentation on added lines**, divided by
`indent_width`. A wrapped call argument aligned under an open paren, a JSX tree, a multi-line
Java or Kotlin string literal — each reads as deep nesting with no control flow present at all.
The `crit` hard cap floors the score at 60 when `max_nesting` exceeds the budget by more than 3,
so a *six-line* diff whose only sin is a continuation line indented 36 columns scores
`OVERBUILT/60` and exits 1. That is the reproduction that opened this ADR, verbatim, and it is
now the T159 fixture.

**The verdict propagated into the ledger.** The devloop skill persists it with
`log-gate --kind simplicity`, a failing gate caps readiness at 65 and blocks convergence, and
`readiness` reads the persisted state. So a false `OVERBUILT` did not merely print — it stopped
the loop, and the only way out was to edit a diff to satisfy a number nobody had chosen.

## Decision

### 1. Advisory is the default; a gate is a declaration

`simplicity-check` exits **0** and reports its verdict as information, unless the project has
BOTH:

- declared at least one **numeric budget** — in `defaults.simplicity` or on the CLI — and
- set `defaults.simplicity.gate: true` (equivalently, passed `--gate`).

With both, behaviour is exactly what it was: `OVERBUILT` is exit 1 and a BLOCKER.

`gate: true` with **no** budget declared is a **configuration error, exit 2**, naming the key.
A gate with no budget is not a gate — it is the same opinion wearing an exit code, and silently
demoting it to advisory would hide a config the human got wrong. `indent_width` is a *parsing*
parameter and `gate` is the switch itself, so neither counts as a budget: declaring only those
is refused too (`_SIMPLICITY_NON_BUDGET`).

The mode travels in the output. JSON gains `mode: "advisory" | "gate"` beside the existing
`budgets_declared`, and the human line reads
`SIMPLICITY: 60.0/100 — OVERBUILT  (advisory (declare budgets + defaults.simplicity.gate to make it block))`.

**The score does not change.** Not the weights, not the bands, not the hard cap, not the
heavy-dimension floor. The measurement was never the defect; the unearned authority was. A diff
that scored `OVERBUILT/60` before scores `OVERBUILT/60` now — it just no longer stops a project
that never asked it to.

**This is not INV-ADVISORY-01.** That invariant (ADR-014) quarantines **LLM-class judgment**: a
dimension a model scores can never gate, and `log-gate --kind` is a closed vocabulary precisely
so an advisory-class dimension cannot be registered as a gate through that door. Simplicity is
not in that class — it is deterministic arithmetic over a diff, and it may gate the moment a
human declares it. What this ADR fixes is **provenance**, the 1.17.0 rule, applied to the exit
code: a default is an opinion, and only a declaration is a requirement.

This is also the shape `waste-check` has shipped since 1.26.0 (`Advisory by default; gates only
with --gate or defaults.waste.gate`). The two halves of "Reduce / REUSE-FIRST" now behave the
same way, which is one rule for a reader to learn instead of two.

### 2. `max_nesting` is NAMED as the indentation proxy it is

The config key (`max_nesting_depth`) and the metric key (`max_nesting`) are **unchanged** —
breaking them would break every config and every consumer for a labelling fix. What changes is
what the output CALLS it:

- the report row reads `max_nesting (indentation proxy)`;
- a line under the table spells out what it measures;
- the nesting **flag** — the line a human actually acts on — carries the caveat;
- JSON gains `metrics_notes.max_nesting` with the same sentence.

The kit does **not** try to make it language-aware. Doing that honestly needs a parser per
stack, which a stdlib-only engine will not have, and a half-parser would trade a proxy a reader
can discount for a proxy a reader would trust. Naming it is the honest move; guessing is not.

### 3. The ledger can say "measured, but not gating"

`log-gate --verdict advisory` is a third verdict beside `pass`, `fail` and `not-run`. It writes
a static-gate record with **zero** gated findings — so it can neither cap readiness nor block
convergence — stamped `advisory: true`.

The stamp is the point. Persisting an advisory run as `pass` would be a **false clean**: a
reader cannot tell "the gate ran and was green" from "there was no gate", and the second is what
actually happened. So the stamp travels through `_gate_rollup` and every surface reads it:

| surface | a real clean gate | an advisory run |
|---|---|---|
| `readiness` gates line | counted in `N ok` | `· 1 advisory (repo/gate:simplicity)`, never in `N ok` |
| `readiness --json` `gates[]` | `advisory: false` | `advisory: true, blocking: false` |
| mirador / `dashboard --json` subscore | `OK` | `ADVISORY` |
| `top` feed | `pass — clean` | `info — advisory, measured, not gating` |
| readiness cap / convergence | credits the gate | caps nothing, blocks nothing |

The advisory segment of the gates line is **conditional**, so a ledger with no advisory record
prints byte-identically to before.

**Why a third verdict rather than a refusal.** The alternative was to make `log-gate` REFUSE to
persist an advisory run as `pass|fail`. It cannot: `simplicity-check` is a separate process, and
the engine has no way to observe which mode it ran in. A refusal would therefore be enforceable
only on the caller's goodwill, while a named verdict is enforceable on the ledger — every reader
downstream sees the mode as a recorded fact instead of inferring it. The skill is instructed to
use it, and T159 measures what the ledger then reports.

### 4. No risk profile owns it

`RISK_PROFILES` owns three knobs (`qa_tools_order`, `coverage_threshold`, `golden_required`) and
none of them is a simplicity budget. Since no preset tightens these budgets, no preset sets
`gate` either: **turning the gate on stays a human declaration under every profile A–E**, and
`AC-SG-06` reads that from the engine's own table so a preset that starts owning one is caught
the day it does.

`uscha init` (the 2.0.0 generator) writes **no** simplicity block at all, and must not start:
with advisory as the engine default there is no kit intent that differs from it, which is the
only reason `install-uscha.py` writes a knob (ADR-001 as amended). `AC-RP-06` stays green
untouched; `AC-SG-06` asserts the simplicity half from the other side.

## Consequences

- **A project that adopted no budget can no longer be stopped by the kit's opinion.** That is
  the whole finding, and it is the one behaviour change a user will notice.
- **A project that DID declare budgets keeps its gate**, by adding one line
  (`"gate": true`). This is a breaking change for such a project: the gate goes quiet until that
  line is added. It is deliberate — the alternative is inferring intent from the presence of a
  budget, and a budget declared as documentation would then silently become a blocker.
- **The false-clean risk moves, so it is measured.** An advisory that read as `ok` would be
  worse than the original defect: a gate that blocks wrongly is loud, a gate that passes wrongly
  is silent. `AC-SG-04` measures the difference against a control (the same gate logged as a
  real failure) rather than asserting a label.
- **`max_nesting` still misfires** — it is the same proxy. What changed is that the report says
  so, in three places, so a reader discounts it instead of trimming code to satisfy it.
- **The claim moved on six surfaces**: the devloop SKILL (both trees), `uscha-kit/README.md`,
  `templates/CONSTITUTION.md`, the field-manual decks (ES + EN, canonical + deployed) and the
  paper's check table, where `simplicity-check` moves from `blocks` to `advises*` — the column
  that already means "gates only under explicit human declaration".
- **T10 changed.** The historical block that asserted `1.9x budget -> exit 1` now passes
  `--gate`, and asserts the same diff without it exits 0. The score it was pinning (the
  heavy-dimension floor) is untouched.

## What this ADR does NOT decide

- It does not touch the weights, the bands, the hard cap or the heavy-dimension floor.
- It does not make `max_nesting` language-aware, and it does not remove it from the score.
- It does not change `waste-check`, `gate-check`, `golden-diff` or `pit-check`. Their default
  postures are as they were.
- It does not make the advisory verdict available for LLM-judged dimensions. INV-ADVISORY-01's
  closed `--kind` vocabulary is untouched: `--verdict advisory` lets a check that RUNS advisory
  by default (`simplicity`, `waste`) record a non-gating run; it does not let an advisory-class
  dimension enter as a gate, and it is refused for every FACT gate (`AC-SG-08`).

## What is measured (`AC-SG-01..08`)

Smoke **T159**, eight criteria, all over real temp projects and the real engine:

1. `AC-SG-01` — no `defaults.simplicity` at all: exit 0, `mode: advisory`,
   `budgets_declared: []`, and the verdict is STILL `OVERBUILT` (so the case measures a softened
   exit, not a softened score).
2. `AC-SG-02` — declared budget + `gate: true`: `OVERBUILT` exits 1 with `mode: gate`, a diff
   that is not overbuilt exits 0 under the same config, and `--gate` reaches the identical exit.
3. `AC-SG-03` — `gate: true` with only `indent_width` declared: exit 2, the refusal names
   `defaults.simplicity.gate`, and no score is printed.
4. `AC-SG-04` — the ledger half, against a control: an advisory record is named apart on the
   gates line, never folded into `N ok`, carries `advisory: true, blocking: false`, caps nothing
   and does not block convergence — while the SAME gate logged `fail` blocks and turns the line
   red.
5. `AC-SG-05` — the field fixture (six added lines, one 36-column continuation): exit 0, and the
   proxy is named in the report, in the flag and in `metrics_notes`, with both the metric key and
   the config key unchanged.
6. `AC-SG-06` — no `RISK_PROFILES` entry owns a simplicity budget (read from the engine's table),
   `gate` never leaks into `SIMPLICITY_DEFAULTS` where it would count as one, and `init`
   generates no simplicity block into either the config or the ledger.
7. `AC-SG-07` — the **red probe**: the `v2.0.0` engine, run on the AC-SG-01 fixture out of git,
   MUST exit 1 there. Without git or the tagged copy it reports `None` = UNMEASURED, never a
   silent pass.
8. `AC-SG-08` — the boundary: `--verdict advisory` is accepted only for `simplicity` and
   `waste`, the kinds whose default mode IS advisory. `gate-check`, `golden-diff`, `pit-check`
   and `regression` refuse it with exit 2, name the kind, and leave the ledger byte-identical:
   a FACT gate recorded as advisory would be a mandatory gate cleared by goodwill.

## Alternatives considered

- **Fix `max_nesting` instead — make it AST-aware.** Rejected. Honest AST nesting needs a parser
  for each of the nine stacks, which a stdlib-only engine will not have, and it would not fix
  the actual defect: a correct nesting number gated against a budget nobody declared is still an
  opinion with an exit code.
- **Drop the nesting dimension.** Rejected: it is a useful signal at 30% of the score once the
  reader knows what it is. Deleting a measurement to avoid explaining it is the opposite of the
  method.
- **Infer the gate from the presence of budgets — declared budgets imply gating.** Rejected: a
  project that writes its budgets down as documentation would silently acquire a blocker, which
  is the same failure this ADR removes, with a different trigger.
- **Demote `gate: true` with no budget to advisory instead of refusing.** Rejected: it is a
  config the human got wrong, and the kit's rule is that an unmeasurable state is named, never
  silently downgraded (the `<skipped/>` = UNMEASURED discipline).
- **Persist an advisory run as `pass`.** Rejected: the false clean. `pass` means a declared gate
  came back green; an advisory run means there was no gate.
- **Make `log-gate` REFUSE `pass|fail` for a run that was advisory.** Rejected as
  unenforceable: `simplicity-check` is a separate process and the engine cannot observe its
  mode, so the refusal would rest on goodwill. A named verdict rests on the ledger.
- **Ship `gate: true` in risk profile E.** Rejected: no profile owns a simplicity budget, so
  E would be turning on a gate whose numbers are still the kit's opinion — the defect, moved
  behind a preset. A profile may own these budgets later; the day it does, `AC-SG-06` goes red
  and the decision gets made explicitly.
