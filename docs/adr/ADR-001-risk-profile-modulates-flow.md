---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/.claude/skills/uscha-devloop/SKILL.md
  - uscha-kit/uscha.config.json
---
# ADR-001: The risk profile modulates the flow (kit-shipped, overridable presets)

## Status: Accepted — **amended 2.0.0: `init` generates a minimal config so the profile is not pre-empted by copied defaults**

## Context
`risk_profile` is declared in `uscha.config.json` but read by **nobody** in `qa_ledger.py`
(verified: zero occurrences). A field retrospective of a real legacy migration (fiscal data,
two Ant repos) named this the deepest finding: the decision of "how much process does this
change deserve" rests entirely on the operator, not the tool — "the difference between a
methodology and a convention."

The engine must let a declared risk level actually change what it enforces. Three shapes were
considered:

- **A) A fixed table in the engine** (profile E ⇒ engine *imposes* golden + judgment-day and
  gates). Rejected: this contradicts the provenance doctrine (kit 1.17.0), where the human
  declares what gates and the engine holds no opinions of its own. It turns "I measure what
  you declare" into "I decide how much process you deserve."
- **B) Presets defined by the user in config.** Rejected: adds nothing — a project can already
  declare `readiness_weights`, `readiness_caps` and `qa_tools_order` by hand, so a name that
  only the local config defines is not a shared, portable concept.
- **C) Kit-shipped presets that EXPAND to the existing declarable knobs, overridable per-knob,
  with provenance.** Chosen.

## Decision
`risk_profile` is a **named preset**, not a new gating mechanism. The kit ships a default
expansion table for profiles `A..E`. At config load the selected profile expands to values for
knobs the config already understands (`qa_tools_order`, `readiness_caps`, `coverage_threshold`,
and the new `golden_required` — see ADR-002). Any knob set **explicitly** in `defaults`
overrides the profile's value for that knob. The gating power the profile confers is exactly
the power a human already has by declaring those knobs — nothing more.

Default expansion table (all overridable per-knob):

| Profile | Meaning | `qa_tools_order` (required to converge) | `golden_required` | `operability.gate` | caps |
|---|---|---|---|---|---|
| A | trivial change | `[code-review]` | no | no | kit defaults |
| B | standard | `[code-review, improve]` | no | no | kit defaults |
| C | sensitive | `[code-review, judgment-day, improve]` | no | **yes** | kit defaults |
| D | high | `[code-review, judgment-day, improve]` | **yes** | **yes** | stricter coverage_threshold |
| E | migration / legacy / fiscal | `[code-review, judgment-day, improve]` | **yes** | **yes** | strictest |

`operability.gate` joined the table in 2.2.0 (ADR-048): on C, D and E a missing CI workflow,
release step, RUNBOOK or seed command is a BLOCKER; on A and B the same four facts are measured
and recorded advisory. It is the first profile-owned knob that lives one level down in
`defaults`, so `_apply_risk_profile` and the origin ladder read DOTTED knob names.

## Reasons
- Kills the "inert" defect: a declared profile now measurably changes the ledger and readiness.
- Doctrine-clean: the profile is a human declaration (config), so it carries provenance and has
  the right to gate — like a declared `readiness_cap`. The engine still holds no opinion it
  imposes; a preset is an overridable default, not a fixed gate.
- Portable: a name means something shared only if the kit defines it; a project still overrides.

## Consequences
+ "profile E" becomes a portable, auditable contract instead of a decoration.
+ Reuses the entire provenance machinery (1.17.0) — no new gating concept.
- The token-saving half ("profile A actually SKIPS judgment-day at run time") is NOT delivered
  here — that is orchestrator behavior in the `uscha-devloop` skill, not deterministic engine
  logic, and is out of scope (see below). This release makes the profile *weigh in the ledger*.

### Amendment (2.0.0): the delivery path had pre-empted the decision

The expansion above was implemented correctly and, in a repo initialised with `uscha init`,
had never taken effect. `init` copied the kit's own `uscha.config.json` — the COMPREHENSIVE
REFERENCE, every knob at the kit's value — into the project, so every kit default arrived as
an **explicit project declaration**, and by this ADR's own per-key rule an explicit declaration
outranks the profile. Measured on 1.99.0: `{}` plus `risk_profile: "A"` resolved
`qa_tools_order` to `[code-review]` (correct); the shipped defaults plus `"A"` resolved it to
the three tools with `_risk_profile_keys` empty — the preset supplied nothing — and the shipped
defaults plus `"E"` measured coverage against 60 instead of 80. What the copy did NOT declare
is what survived: `golden_required` was absent from the reference, so profile E did supply that
one (`_risk_profile_keys = ['golden_required']`, value `True`). A preset whose reach is decided
by which keys the installer happened to omit is not a preset modulating the flow. It was inert
wherever the kit itself had put it, on every knob the kit itself had an opinion about.

Nothing about the precedence changes — it is still explicit override > selected profile >
engine default, and that ordering is why the copy was fatal. What changes is the delivery:
`init` now **generates** a minimal config (identity, the detected repo and its test command,
and only the knobs whose engine default is absent or differs from the kit's intent — which
includes the `fast_path` block, copied whole, and the `integration` switch, because the engine defaults
both to OFF and dropping them would have turned two shipped features off in silence). The
reference config stays in the kit, documented as a reference and no longer copied. `doctor`
prints the effective value of each profile-owned knob with its origin (`override` /
`profile <X>` / `default`), reading `ENGINE_DEFAULTS` for the bottom rung, and reports an
override that supersedes a profile as INFORMATION: declaring a knob by hand is the documented
way to bend a preset, never an error.

The fix is to stop COPYING, and deliberately not to start INJECTING. An earlier draft of this
change materialized `ENGINE_DEFAULTS` into `defaults` at config load so a minimal config would
carry the kit's values explicitly. The golden captured for `AC-FP-08` — the engine's entry
behavior frozen before fast-path existed — refused it, and it was right to: with
`coverage_threshold: 60` written in, `thresholds_declared.coverage_threshold` flipped from
`false` to `true`, and the kit's own default started reporting as a human requirement. That is
exactly what the provenance machinery (1.17.0) exists to keep apart, and exactly the confusion
that made the copied config outrank the profile — the same mistake pointed the other way.
`ENGINE_DEFAULTS` is therefore a REPORTING table: `doctor` reads it, `init` never writes it,
and a knob nobody declared stays absent everywhere the engine reads it. `qa_tools_order`'s
entry is `None` for the same reason: with no list declared, convergence falls back to a window
of `--tools-per-cycle` agent steps, so there is no default list to name.

Existing projects are untouched. A config that already carries the full copy keeps every value
it has — `readiness --json` over such a fixture differs from the 1.99.0 engine only by the
`acceptance` keys a later release DECLARED (2.2.0: `corpus_closed`, `smoke_closed`,
`smoke_vetoed`, each named in the block and empty without evidence) and
`init` freezes the same `defaults`, key for key (`AC-RP-04`) — because a value equal to a
former default is indistinguishable from a value a
human chose, and authorship cannot be recovered from equality. Those projects adopt the presets
by DELETING the keys they never meant to declare; `doctor`'s origin column names them, and the
kit README's config section carries the migration.

## Out of scope (this release)
- The `uscha-devloop` skill actually skipping sub-agents by profile (the token saving). Follow-up.
- Any effect on `execution_policy` (tier/model/effort) — that is routing metadata, not gates.
- Per-repo profiles — the profile is global (`defaults`) for now.
- Auto-classification of a change's risk — the human declares it; the engine never guesses.

## Implementation Plan
- Affected paths: `uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py` (+ distributable twin
  `uscha-kit/skills/uscha-devloop/qa_ledger.py`); `uscha-kit/tests/smoke-engine.sh`.
- Pattern: at config load (the `defaults` validation block, ~line 1571), after reading
  `defaults`, look up `RISK_PROFILES[risk_profile]` (a module constant) and MERGE its keys
  UNDER the explicit `defaults` (explicit wins). Track which keys came from the profile so the
  cap/threshold provenance can label them `requerimiento (perfil <X>)` vs `requerimiento
  (config)` — reuse the 1.17.0 `declared_caps`/`cap_source` mechanism.
- Unknown `risk_profile` → `SystemExit` with the list of valid profiles (mirror the existing
  invalid-config errors). Absent `risk_profile` → no merge, behavior byte-identical to today.
- `golden_required` handling: ADR-002.
- Tests: smoke T86+ (see Verification).

## Verification
- [ ] With no `risk_profile`, `readiness --json` is byte-identical to the pre-change engine
  for the same ledger (no regression).
- [ ] `risk_profile: "E"` with no explicit `qa_tools_order` expands to the three tools, and
  convergence requires all three.
- [ ] `risk_profile: "A"` expands to `[code-review]`; a repo converges without judgment-day
  having run.
- [ ] An explicit `defaults.qa_tools_order` overrides the profile's list (explicit wins).
- [ ] `risk_profile: "Z"` (unknown) exits nonzero with a clear message.
