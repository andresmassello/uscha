---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/.claude/skills/uscha-discovery/SKILL.md
  - uscha-kit/skills/uscha-discovery/SKILL.md
  - uscha-kit/.claude/skills/uscha-adr-refine/SKILL.md
  - uscha-kit/skills/uscha-adr-refine/SKILL.md
  - uscha-kit/templates/docs/adr/ADR-stack-template.md
---
# ADR-040: The stack is a decision with an EXPIRY DATE — a mandatory "Stack and lifecycle" round before the stack ADR, a machine-readable `lifecycle:` block, and a measured advisory that compares end-of-support against the declared go-live

## Status: Accepted (1.94.0; proposed by the maintainer from a field run, approved 2026-08-21)

## Context
A field run (2026-08-21) closed sixteen ADRs with real rigor: the domain was interrogated, the
invariants were written down, the failure modes had behavior. The stack ADR fixed a major line —
"language runtime version N + web framework major M" — and everyone read that as a complete
decision. It was not. Only in the test phase, ten days before a declared go-live, did it surface
that the chosen MINOR line had left OSS support months earlier, and that a development tool the
operator wanted from day one required the NEXT major. The result was a major upgrade days before
the milestone: the most expensive possible moment for the cheapest possible question.

The root cause is in the method, not in the run. The interview interrogates WHAT (behavior) and
WHY (decisions, alternatives), and it treats the stack as a GIVEN — "we use X" — rather than as a
risk decision that carries a date. A major version is a family; support is granted to a minor
line, for a window, by an upstream nobody in the room controls. Three questions in discovery would
have caught it, and they were not on the agenda because nobody had written them down.

Two adjacent facts made a mechanical check possible now. The ADR is already the place where the
stack is fixed (`spec-check` even flags stack terms that leak into the SPEC's acceptance
criteria), and the kit already has a precedent for a read-only dimension that reports without
gating: spec-drift (ADR-005), which never blocks a pipeline because a stale document is a prompt
for a human conversation, not a broken build.

## Alternatives
- **A) Prose guidance only** — add the questions to the skills and stop there. Cheapest, and the
  failure mode is exactly the one that produced this ADR: an agenda item with no artifact leaves
  no trace anyone can check later.
- **B) A gate** — block readiness when a component expires before go-live. Rejected: the engine
  can see that a date was CITED, never that the citation is true. A gate built on a number the
  operator types is a gate that gets typed around; and the anti-ceremony meta-invariant asks
  whether a new gate speaks only when it matters. This one would speak on every run of every
  project that has no lifecycle block at all.
- **C) Chosen: a mandatory interview round, a machine-readable block, and an ADVISORY dimension.**
  The human answers, the ADR records with a citation, and the engine compares two dates it can
  read. It reports; it never gates.

## Decision
- **A mandatory "Stack and lifecycle" round** in `uscha-discovery` and `uscha-adr-refine`, placed
  BEFORE the architecture/stack ADR, run in the method's own shape (one question per turn, each
  with the agent's recommended answer): the EXACT version of every runtime/framework/store and its
  OSS/LTS end-of-support date **verified against the official source at the moment of asking — the
  agent fetches it, never answers from memory — and cited (URL + date checked)**; the support
  window against the declared go-live and expected operating life; major dependencies and who
  approves an upgrade, aligned with the devloop's "zero new dependencies without approval";
  development and observability tools the operator wants from day one, because they constrain
  versions and asking late is what forces the upgrade; and the minimum version that reused legacy
  modules support. The answers distil into the stack ADR with the dates inside.
- **A machine-readable stack ADR.** A `lifecycle:` frontmatter block, a list of
  `{component, version, eol, source, checked}` with ISO dates. `eol: unknown` is allowed and is a
  NAMED absence, never a pass. The SPEC declares `go_live: YYYY-MM-DD` (frontmatter, or a
  `**Go-live:** YYYY-MM-DD` line). `uscha-kit/templates/docs/adr/ADR-stack-template.md` ships the
  shape, and one CONSTITUTION item makes the citation non-negotiable: *no stack ADR without a
  cited end-of-support date for every component it fixes*.
- **A lifecycle dimension in `spec-check`** — read-only and advisory, the spec-drift contract
  (ADR-005): it never gates, never caps readiness and never changes an exit code. It parses the
  `lifecycle:` blocks of `docs/adr/*.md` with a YAML SUBSET parser (stdlib only — the kit ships no
  PyYAML), reads `go_live` from the SPEC, and per component emits `ok` (eol ≥ go-live AND a source
  cited) / `expires before go-live (<eol> < <go_live>)` / `no EOL cited` / `no source cited`. When
  a date already expires the expiry wins the label even if the source is missing — the sharper
  fact first; the missing source stays visible in the record. The WHOLE dimension is `UNMEASURED`,
  with the reason spelled out, when no ADR carries a `lifecycle:` block, when the block is present
  but unparseable, or when no go-live is declared. Never silence.
- **Where it shows.** `spec-check` text and `--json` (key `lifecycle`), one advisory line in
  `readiness`, and the block in `dashboard --json`. `readiness` and `dashboard` carry it
  CONDITIONALLY — only when some ADR declares a `lifecycle:` block — the same conditional-key rule
  `fast_path` and `spec_drift` already follow: a project that declares nothing keeps the exact
  prior payload and the exact prior text, byte for byte. `spec-check`, the command whose whole job
  is to lint the spec surface, always says the dimension's state, UNMEASURED included.
- **No readiness cap.** Deliberately: see alternative B.

## Consequences
+ The question that cost a field run its last ten days is now on the agenda, with an artifact
  behind it and a mechanical reading of that artifact.
+ The dimension is honest about what it does not know: it measures that a date and a source were
  CITED and compares two dates. It CANNOT verify that the cited source tells the truth, that the
  URL still resolves, or that `checked` was really the day someone looked. A wrong date, cited,
  reads `ok`. This is stated here, in the doc row, and in the ADR template.
+ Existing projects are unaffected: no lifecycle block, no new output, no schema change.
- One more round in an already long interview. It is placed where it is cheapest (before the stack
  ADR) and it is skipped, like every other round, when the references already answer it.

## Dogfooding note
Applied to the kit itself, the rule immediately forces a distinction it is worth writing down: the
declared **py3.8-clean** floor is a COMPATIBILITY FLOOR FOR USERS, not the runtime the kit runs on.
"The runtime you run" and "the minimum you support" are different components with different dates,
and a lifecycle block that conflates them would report a date about nothing. The kit's own SPEC
declares no go-live — it is a library on a rolling release, not a system with a milestone — so the
dimension reads UNMEASURED here, and that is the honest answer rather than a decorative green.

## Implementation Plan
- Affected paths: `uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py` (+ mirror),
  `uscha-kit/.claude/skills/uscha-discovery/SKILL.md` (+ mirror),
  `uscha-kit/.claude/skills/uscha-adr-refine/SKILL.md` (+ mirror),
  `uscha-kit/templates/docs/adr/ADR-stack-template.md`, `uscha-kit/templates/CONSTITUTION.md`,
  `uscha-kit/tests/smoke-engine.sh` (T148), `ACCEPTANCE.md`, the four doc decks.
- Patterns: `_lifecycle_report` is the single derivation; `_lifecycle_summary` renders the one line
  both `spec-check` and `readiness` print, so the surfaces cannot disagree.
- Tests: T148, sidecar `.lc-cases.json`, criteria `AC-LC-01..05`.

## Verification
- [x] A component whose `eol` falls before the go-live reads `expires before go-live` in
      `spec-check` text and `--json`, and in the `readiness` advisory line (AC-LC-01).
- [x] `eol` ≥ go-live with a source cited reads `ok` (AC-LC-02).
- [x] A missing `eol` reads `no EOL cited`; a missing `source` reads `no source cited` (AC-LC-03).
- [x] No go-live in the SPEC, and no `lifecycle:` block anywhere, both read UNMEASURED with the
      reason named (AC-LC-04).
- [x] Advisory only: the readiness score is byte-identical with and without an expiring
      component, and `dashboard --json` carries the block (AC-LC-05).
