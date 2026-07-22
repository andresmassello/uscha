# ADR-002: `golden_required` — a declarable cap for "an approved golden must exist"

## Status: Accepted

## Context
The field retro asked, verbatim, that a high-risk profile "block if the approved golden is
missing." Today that is not expressible: the golden is only a gate you *log* (`golden-diff`);
there is no readiness **precondition** that says "without an approved golden, you do not pass."
Verified: no `requires_golden` / golden precondition exists in `qa_ledger.py`.

This must not become profile-only magic. The doctrine (ADR-001) is that a profile only sets
knobs a human could set directly — so the primitive has to be a **declarable knob in its own
right**, usable by any config, that the profile presets merely turn on.

Options for "block":
- **A) Cap readiness to a low ceiling** when the golden is missing — reuses the existing
  `readiness_caps` machinery and its provenance labels. Chosen.
- **B) Hard-zero** (readiness = 0 until a golden exists). Rejected: a new mechanism outside the
  cap pattern, more brutal without being more correct — a cap to 49 already means NOT READY,
  which does not pass the human merge gate.

## Decision
Add `golden_required` (boolean) as a declarable readiness knob, available to **any** config
(not only via a profile). When `golden_required` is active for a repo AND **no approved
`golden-diff` gate is recorded** in the ledger for that repo, cap that repo's readiness at
**49** (NOT READY), with `cap_source` labelled `requerimiento (perfil <X>)` when it came from a
profile, or `requerimiento (config)` when declared directly.

Two facts kept distinct:
- **Golden ABSENT** (no `golden-diff` gate ever logged) → the `golden_required` cap fires. "You
  did not even capture a golden."
- **Golden PRESENT but FAILED** (`golden-diff` verdict = fail) → already handled by the existing
  gate machinery (a red golden-diff blocks convergence / caps via the blocker path).
  `golden_required` does NOT overlap that case.

## Reasons
- Delivers the retro's headline ask.
- Doctrine-clean: "does an approved `golden-diff` gate exist in the ledger?" is a **measured
  fact**, not a guess — facts may block. And it is a human declaration (config), so it carries
  provenance and has the right to gate.
- Separable from ADR-001: any project can declare `golden_required: true` without using a
  profile; profiles D/E simply preset it on.

## Consequences
+ A brownfield migration cannot reach RELEASE CANDIDATE without first freezing the pre-change
  behavior as an approved golden — the exact discipline the golden exists to enforce.
- One more cap to reason about; documented alongside the existing `readiness_caps`.

## Implementation Plan
- Affected paths: same as ADR-001 (`qa_ledger.py` + twin, `smoke-engine.sh`).
- Pattern: in the per-repo scoring (the function that assembles `caps_active`, ~line 2815),
  when the merged `golden_required` is truthy for the repo, check the ledger for an approved
  `golden-diff` gate (verdict pass) on that repo; if none, append a cap
  `("golden requerido: sin golden aprobado", 49)` to `caps_active`, so the existing
  `_apply_caps` applies the ceiling and `cap_reason`/`cap_source` surface it. Provenance:
  reuse the `declared_caps` set so the label distinguishes profile-origin from config-origin.
- Validation: `golden_required` must be a boolean in config validation, alongside the existing
  `readiness_weights`/`readiness_caps` checks.
- Tests: smoke T87 (see Verification).

## Verification
- [ ] `risk_profile: "E"` (or `golden_required: true`) with NO `golden-diff` gate in the ledger
  → the repo's readiness is capped at 49 and `cap_source` reads `requerimiento (perfil E)`
  (or `requerimiento (config)` when declared directly).
- [ ] With an approved (pass) `golden-diff` gate logged for the repo → the `golden_required`
  cap does NOT fire.
- [ ] A present-but-FAILED `golden-diff` is handled by the existing gate path, not double-capped
  by `golden_required`.
- [ ] Explicit `golden_required: false` under `risk_profile: "E"` → the cap does not fire, and
  the override is visible in provenance (explicit wins).
