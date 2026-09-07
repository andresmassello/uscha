# Architecture Decision Records

Durable technical decisions of this repo. One per file:
`ADR-NNN-<slug>.md`. They are written by `/uscha-discovery` or `/uscha-adr-refine`, or proposed during the
build when a real decision appears (see the ADR rules in `CLAUDE.md`).

Format: Status (proposed/accepted/experiment/deprecated/superseded) · Context · Alternatives ·
Decision · Consequences · Implementation Plan (affected paths, patterns, tests) ·
Verification (checkboxes).

The ADR that fixes the stack has a template of its own, `ADR-stack-template.md`: it carries a
machine-readable `lifecycle:` frontmatter block (component / version / eol / source / checked)
that `spec-check` compares against the SPEC's declared `go_live` (ADR-040). Advisory: it reports,
it never gates.

A **decision item the AGENT introduced** — one that came from the agent's proposal rather
than from a human answer — carries a trailing marker on its own line:

```
- D-03 — the tree is renamed to English. (origin: agent)
- D-03 — the tree is renamed to English. (origin: agent, confirmed: 2026-09-07)
```

Items with no marker are human-origin by default (nothing already written is retro-tagged).
An unconfirmed item is NOT in scope: it is confirmed one item at a time, never by a
package-level "ok". `spec-check` lists the unconfirmed ones with file:line and `readiness`
counts them on a line of their own; both are advisory — no exit code, no score changes. A
marker inside a fenced block or an inline code span (like the two above) is documentation and
is skipped.

`Status: Experiment` is for a bounded, reversible hypothesis that needs real feedback.
It must include: Hypothesis, Feedback Signal, Review By or Review Trigger, Promote
Criteria, and Rollback / Supersede Criteria. Missing/expired metadata is advisory in
Mirador/dashboard; it is not a readiness score.

## Index

<!-- add one line per ADR -->
- _(no ADRs yet)_
