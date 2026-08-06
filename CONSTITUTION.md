# CONSTITUTION.md — project invariants (uscha)

The layer **above the ADRs**. It records what **no ADR or SPEC may violate**, whatever
trade-off wins. An ADR *chooses* between alternatives; the CONSTITUTION *forbids*.

> Truth hierarchy: **SPEC** = what must happen · **ADR** = why this shape ·
> **CONSTITUTION** = what is never acceptable.

A violation is a **BLOCKER** finding (non-negotiable): record it with
`qa_ledger.py flag-blocker --kind constitution`; once recorded it blocks convergence and caps
readiness until a human `--resolve`s it.

## Invariants

- **INV-CANON-01 — The canonical source of the kit is `uscha-kit/`.** Zips and doc snapshots in
  Downloads are builds; in any conflict, this repo wins.

- **INV-TRUTH-01 — No document may claim what the engine does not do.** Every claim in `docs/`
  must be backed by what `qa_ledger.py` actually does. Under-claim, then wire, then re-claim.

- **INV-TWIN-01 — The twins travel together.** The canonical skill tree
  (`uscha-kit/.claude/skills/`) and the distributable Codex mirror (`uscha-kit/skills/`) are
  byte-identical; every ES document under `docs/` has its `-EN` twin. An edit to one demands the
  equivalent edit to the other.

- **INV-ANON-01 — Zero references to clients or private projects.** What ships is generic
  (`backend-api`/`mobile-app`). No real client or project name in the kit or the docs.

- **INV-SMOKE-01 — Every engine change carries a green smoke.** `bash uscha-kit/tests/smoke-engine.sh`
  must exit 0 before any change to `qa_ledger.py` is committed; new behavior adds its check in the
  same change.

- **INV-VERSION-01 — The six version surfaces agree.** `VERSION`, `uscha.config.json`, both
  `plugin.json`, `marketplace.json` and `package.json` carry the same version, with a matching
  `CHANGELOG-<version>.md`, in the same commit.

- **INV-GOLDEN-01 — Never author or rename a `.approved`.** The approved golden is the one
  artifact the agent is mechanically forbidden from creating; the `PreToolUse` hook enforces it.

- **INV-MODEL-01 — The engine stays model-agnostic.** `qa_ledger.py` never reads tokens, model
  names or vendor telemetry. A model's judgment enters only through a JSON contract, in an
  adapter, never in the engine.

- **INV-RISK-01 — A declared risk level is never inert.** If `risk_profile` is set in config, the
  engine MUST read it and apply its expansion (required tools, caps, required golden), or fail
  loud on an unknown value. A declared risk level that changes nothing is a broken methodology —
  a convention masquerading as a method. *(This invariant is the lesson of the field
  retrospective that motivated ADR-001 and ADR-002.)*

- **INV-RIGOR-02 — Rigor is a one-way ratchet.** The human may always force MORE rigor (full
  path over fast-path); no human, agent or flag may ever force LESS (an `ALLOW` over a measured
  `DENY`, a skipped gate, a lowered cap at run time). Anything that weakens a control is a
  config change reviewed like code — never a runtime override. *(Introduced with ADR-003:
  without this asymmetry, a fast path is a backdoor with paperwork.)*

- **INV-CURATION-01 — No candidate behavior reaches the forward flow without a human verdict.**
  A spec candidate extracted from a legacy system — whatever its evidence or confidence — is
  quarantined until a human records `preserve`, `fix` or `undefined` in the behavior ledger,
  each verdict backed by its ADR. The gate is measured by the engine, fail-closed: no verdict,
  no promotion; a malformed ledger blocks, it never degrades to "no verdicts". *(Introduced
  with ADR-009: extraction without judgment fossilizes bugs as features — the agent may author
  candidates, only the human may promote them.)*
