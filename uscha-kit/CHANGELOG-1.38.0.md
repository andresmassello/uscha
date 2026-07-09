# uscha-kit 1.38.0 ? contract closure loop

## Added

- `spec-change-request`: records a human contract-change bridge from evidence/doubt to SPEC/ADR amendment, surfaces it in `readiness --json`, and derives `phase=escalated` while open.
- `golden-diff --labels golden-labels.json --json`: reports approved fixture intent as `intended`, `observed-accidental`, or `unknown` without weakening byte comparison.
- `summary --json` now includes `post_merge_calibration` counts for production findings, SPEC doubts, and SPEC change requests so retros can calibrate the method from real reopen signals.

## Verification

- Smoke target: 216/216 green.
