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

`Status: Experiment` is for a bounded, reversible hypothesis that needs real feedback.
It must include: Hypothesis, Feedback Signal, Review By or Review Trigger, Promote
Criteria, and Rollback / Supersede Criteria. Missing/expired metadata is advisory in
Mirador/dashboard; it is not a readiness score.

## Index

<!-- add one line per ADR -->
- _(no ADRs yet)_
