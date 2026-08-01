# ACCEPTANCE — uscha applied to itself

The kit exists to make a project's quality **measured** rather than narrated. This file turns
that same discipline on the kit's own repository: each criterion below closes only when a
green test case named `AC-nn` exists in an ingested JUnit report — a checkbox ticked by hand
is recorded as `narrated-only` and does not close.

The evidence is emitted by `uscha-kit/tests/smoke-engine.sh` (the acceptance block at the end
of the suite) into `uscha-kit/reports/junit/`. It is captured **by execution**: the report is
written by the run itself, never by hand.

## Criteria

- [x] AC-01 — The distributable skill tree (`uscha-kit/skills/`) is byte-identical to the
  canonical one (`uscha-kit/.claude/skills/`). A Codex user and a Claude Code user run the
  same engine, or the twin promise is false.

- [x] AC-02 — The six version surfaces (`VERSION`, `uscha.config.json`, both `plugin.json`,
  `marketplace.json`, `package.json`) all agree, and a `CHANGELOG-<version>.md` exists for the
  declared version. A release that disagrees with itself cannot be trusted about anything else.

- [x] AC-03 — The kit and its docs contain zero references to client or private project names.
      <!-- Re-ticked 2026-07-26, and this time it is MEASURED, not declared. It was a
           hand-ticked green over a FALSE criterion (4 tracked files carried names) while the
           gate itself read UNMEASURED. Two holes, both closed: the list is now committed as
           SHA-256 hashes (.uscha-private-names.sha256), so CI runs the criterion instead of
           emitting <skipped/>; and the scan covers every TRACKED file in the repo, not just
           uscha-kit/ + README.md -- which is why it never saw audits/ or formats/. Proven by
           mutation: planting a listed name in a tracked file turns AC-03 red. -->
  What ships is generic, or it leaks.

- [x] AC-04 — The engine stays model-agnostic: `qa_ledger.py` never reads tokens, model names,
  or vendor telemetry. Any model-reported number enters through an adapter, never the engine.

- [x] AC-05 — Every published ES document under `docs/` has its `-EN` twin. The twins travel
  together, or one of them silently rots.

- [x] AC-06 — The smoke suite finishes with zero failures. It is the gate every engine change
  must pass before a commit exists.

## Fast-path (Phase 1) — feature acceptance, closes on green `AC-FP-nn` tests in ingested evidence

Numbering follows the originating handoff for traceability; **AC-FP-04 is deliberately absent**
(the golden-touched veto is deferred — ADR-004 records why; the direct fixture case is covered
by `**/*.approved` in `protected_paths`, exercised by AC-FP-03).

- [x] AC-FP-01 — diff within all thresholds, no protected paths → `fastpath-eval` verdict `ALLOW`.
- [x] AC-FP-02 — diff exceeding `max_loc_delta` by 1 → `DENY`, breakdown names `max_loc_delta`.
- [x] AC-FP-03 — diff touching one file matching `protected_paths` → `DENY` regardless of size.
- [x] AC-FP-05 — fast-path run whose diff later grows past a threshold → state `ESCALATED`,
  PR step blocked, both ledger records present.
- [x] AC-FP-06 — fast-path run with no asserting test in evidence → criterion open, readiness
  capped (via the existing cap mechanics).
- [x] AC-FP-07 — the ledger entry for a fast-path verdict carries: mode, verdict, and every
  signal with value + threshold + source + timestamp.
- [x] AC-FP-08 — `fast_path` block absent from config → behavior identical to the previous
  release (golden-anchored BEFORE implementation, via `/uscha-characterize`).
- [x] AC-FP-09 — human override to full path works; no mechanism can force `ALLOW` over `DENY`.
- [x] AC-FP-10 — no git repo, or unresolvable merge-base → `DENY` with the reason named
  (fail-closed: "could not measure" never grants the shortcut).
- [x] AC-FP-11 — `fastpath-eval` without `--intent` is a dry-run: verdict reported, no
  fast-path mode entry recorded in the ledger.

## Spec-drift (Phase 2) — feature acceptance, closes on green `AC-SD-nn` tests in ingested evidence

Advisory by design (ADR-005): drift detection is a heuristic, and a guess advises, never gates.

- [x] AC-SD-01 — governed file newer than its spec beyond `max_lag_days` → `SPEC_STALE`
  advisory listing the newer files.
- [x] AC-SD-02 — spec newer than all governed files → no advisory.
- [x] AC-SD-03 — spec without `governs:` frontmatter → `UNMAPPED`, distinct from clean.
- [x] AC-SD-04 — advisory present → readiness score numerically unchanged.

## Golden coverage (Phase 1.5) — feature acceptance, closes on green `AC-GM-nn` tests

Unblocks the veto ADR-004 deferred, with the mapping DERIVED BY MEASUREMENT (ADR-006).
Opt-in via `defaults.fast_path.forbid_when_golden_touched`; fail-closed once declared.

- [ ] AC-GM-01 - veto undeclared -> no `golden_touched` signal, and the verdict for a given
  diff is identical to the pre-feature behavior.
- [ ] AC-GM-02 - veto declared + manifest absent (or a golden with no entry) -> `DENY`
  naming `golden_touched`.
- [ ] AC-GM-03 - veto declared + diff touches a file the manifest maps to a golden -> `DENY`,
  breakdown naming the golden and the file.
- [ ] AC-GM-04 - veto declared + diff touches only unmapped files -> the signal passes; the
  other signals decide the verdict.
- [ ] AC-GM-05 - the signal's `source` carries the capture commit and the coverage tool
  version recorded in the manifest.
- [ ] AC-GM-06 - malformed manifest -> exit 2 (config error), never a silent "no mapping".
- [ ] AC-GM-07 - capture with `coverage.py` unavailable -> no map is written; an empty map
  that would read as "covers nothing" is never produced.

## Out of scope for measurement here

- **Conventional commits** and **INV-GOLDEN-01** (never author a `.approved`) are enforced
  outside this file: the first by review, the second by a best-effort `PreToolUse` hook on the
  Claude target (text-matching, so an indirect write is NOT caught) plus `golden-diff`, which
  is the measured control because it compares bytes.
  They are invariants, not acceptance criteria — nothing here should pretend to measure them.
- **Coverage** of the engine is **instrumented** (the fork this file used to leave open was
  resolved by measuring, not by declaring an exemption). `USCHA_COVERAGE=1` wraps the one
  choke point the suite drives the engine through — ~370 subprocess calls — and the combined
  Cobertura report lands in `reports/coverage.xml`: **84.2%** against a declared threshold of
  60. Opt-in, so the default suite stays fast and needs no `coverage.py`.
  Honest limit, recorded in `uscha.config.json` as `defaults._coverage_scope`: the number
  covers the **engine** (`qa_ledger.py`) — what the seam actually executes. The auxiliary
  scripts (`templates/scripts`, the mirador renderer) are exercised by the suite but invoked
  outside it, and coverage.py does not report never-imported files, so they are **absent from
  the number, not counted as 0**. Widening the seam is deferred work (`ISSUES-DEFERRED.md`
  D-03), not a silent omission.

## Recorded decisions
- ADR-001 — The risk profile modulates the flow (kit-shipped, overridable presets).
- ADR-002 — `golden_required`: a declarable cap for "an approved golden must exist".
- ADR-003 — Fast-path entry is granted by measured signals, never by opinion.
- ADR-004 — The golden-touched veto is deferred until a golden↔source mapping exists.
- ADR-005 — Spec drift is detected mechanically and reported as advisory — never gated.
- ADR-006 — The golden↔source mapping is derived by measurement; the veto it unblocks is opt-in.

Each ADR carries its own checkable Verification block; the executable form of those checks is
the smoke suite (`uscha-kit/tests/smoke-engine.sh`), not `AC-nn` criteria here — a kit change
is accepted by a green smoke, which is how uscha verifies its own engine.
