---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/.claude/skills/uscha-devloop/SKILL.md
  - uscha-kit/uscha.config.json
---
# ADR-001: The risk profile modulates the flow (kit-shipped, overridable presets)

## Status: Accepted

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

| Profile | Meaning | `qa_tools_order` (required to converge) | `golden_required` | caps |
|---|---|---|---|---|
| A | trivial change | `[code-review]` | no | kit defaults |
| B | standard | `[code-review, improve]` | no | kit defaults |
| C | sensitive | `[code-review, judgment-day, improve]` | no | kit defaults |
| D | high | `[code-review, judgment-day, improve]` | **yes** | stricter coverage_threshold |
| E | migration / legacy / fiscal | `[code-review, judgment-day, improve]` | **yes** | strictest |

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
