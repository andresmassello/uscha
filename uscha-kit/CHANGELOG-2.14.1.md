# uscha-kit 2.14.1 — seven ADR statuses tell the truth about what shipped

## What changed

A truth-pass over `docs/adr/` (repo rule 2): seven ADRs still read `Proposed` although their
releases shipped. Each decision item was checked against the engine, the skills and the tools.

- **ADR-043** (simplicity advisory by default) -> `Accepted (2.1.0)`.
- **ADR-044** (origin: agent), **ADR-045** (skill blocks carry the kit version), **ADR-046**
  (`corpus-run`), **ADR-047** (`smoke-ingest`) and **ADR-048** (operability measured) ->
  `Accepted (2.2.0)`; every decision item is built and pinned (T159-T165).
- **ADR-035** (`uscha top` deferred persistence) stays `Proposed`, now saying what it is: a
  deferral record whose item 6 shipped as ADR-036 (1.87.0) and whose items 1-5 are not built.
- ADR-048's acceptance list named `AC-OP-01..09` but listed eight; AC-OP-09 (a knob turned off by
  hand is an `override`), which `ACCEPTANCE.md` and the suite already carried, is now in it.

`docs/adr/INDEX.md` copies each new status verbatim (AC-DC-04). The kit itself does not change.

## Evidence

Suite: __SUITE__ checks · 0 fail; acceptance __ACC__.
