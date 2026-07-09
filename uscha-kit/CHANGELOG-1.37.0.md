# CHANGELOG 1.37.0 ? ADR experiments: visible hypotheses

Decision #10 from the deferred analysis is implemented narrowly: an ADR can now say
`Status: Experiment` when the decision is a bounded hypothesis that needs real feedback.

## What changed

- `dashboard --json` now preserves both ADR layers:
  - legacy `status` remains the coarse Mirador bucket (`done` / `prog` / `todo`);
  - `adr_status` preserves the authored ADR status (`accepted`, `proposed`, `experiment`, etc.).
- Experimental ADRs carry advisory metadata:
  - `experiment_valid`
  - `experiment_missing`
  - `review_by`
  - `review_trigger`
  - `feedback_signal`
  - `expired`
- Top-level `adr_experiments` summarizes `open`, `malformed`, `expired`, and `ids`.
- Mirador renders experiment ADRs as `experiment`, `experiment invalid`, or `experiment overdue`.
- `Status: Experiment` is intentionally **not** readiness scoring and **not** a hard PR gate.

## Required sections for `Status: Experiment`

An experiment ADR must include:

- `Hypothesis`
- `Feedback Signal`
- `Review By` or `Review Trigger`
- `Promote Criteria`
- `Rollback / Supersede Criteria`

Missing/expired metadata is visible/advisory so the operator does not confuse a hypothesis with
an accepted decision.

## Smoke

- Full smoke: `209 ok ? 0 fail`.
- New T62 covers:
  - valid experiment ADR exposed in `dashboard --json`;
  - malformed/expired experiment counted as advisory;
  - Mirador renders `experiment` without changing readiness.
