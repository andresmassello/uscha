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
- [x] AC-SD-05 — a spec declaring `governs: []` reports **`NO-CODE`**, distinct from both
  `UNMAPPED` and `CLEAN`: a negative decision governs no code, and saying so is a declaration,
  not an omission. Found by running `spec-drift` on this repo's own ADR-004.

## Golden coverage (Phase 1.5) — feature acceptance, closes on green `AC-GM-nn` tests

Unblocks the veto ADR-004 deferred, with the mapping DERIVED BY MEASUREMENT (ADR-006).
Opt-in via `defaults.fast_path.forbid_when_golden_touched`; fail-closed once declared.

- [x] AC-GM-01 - veto undeclared -> no `golden_touched` signal, and the verdict for a given
  diff is identical to the pre-feature behavior.
- [x] AC-GM-02 - veto declared + manifest absent (or a golden with no entry) -> `DENY`
  naming `golden_touched`.
- [x] AC-GM-03 - veto declared + diff touches a file the manifest maps to a golden -> `DENY`,
  breakdown naming the golden and the file.
- [x] AC-GM-04 - veto declared + diff touches only unmapped files -> the signal passes; the
  other signals decide the verdict.
- [x] AC-GM-05 - the signal's `source` carries the capture commit and the coverage tool
  version recorded in the manifest.
- [x] AC-GM-06 - malformed manifest -> exit 2 (config error), never a silent "no mapping".
- [x] AC-GM-07 - capture with `coverage.py` unavailable -> no map is written; an empty map
  that would read as "covers nothing" is never produced.
- [x] AC-GM-08 - `golden-coverage` under a real `coverage.py` records a MEASURED map that
  includes a file the harness reaches only through a **subprocess** (the boundary a
  parent-only instrumentation cannot see) and excludes one it never executes, with the
  capture commit and tool version recorded. Added after the first seven were written: they
  all measured the veto's CONSUMPTION and left its PRODUCTION -- the actual measurement --
  unmeasured.

## Evidence origin (ADR-007) - feature acceptance, closes on green `AC-EP-nn` tests

Provenance, not a gate: the snapshot records WHERE it was measured. Nothing scores, nothing
blocks. The worktree clean-room the handoff proposed is deferred, with reasons, in ADR-007.

- [x] AC-EP-01 - snapshot in a clean git repo -> `origin.commit` equals `git rev-parse HEAD`
  and `origin.dirty` is false.
- [x] AC-EP-02 - snapshot with an uncommitted change -> same commit, `origin.dirty` true
  (untracked files count as dirty).
- [x] AC-EP-03 - "could not measure" -> both null, NO CRASH, and `dirty` NOT false, in all
  three shapes: a directory that is not a git repo, a configured repo path that does not
  exist, and git absent from PATH. An unmeasurable tree state must never read as clean.
- [x] AC-EP-05 - the answer is scoped to the repo path: a repo entry pointing at a
  subdirectory of a larger working tree does not inherit the outer repo's dirtiness.
- [x] AC-EP-04 - the readiness score is numerically identical with and without the field.

## Clean-room (ADR-008) - feature acceptance, closes on green `AC-CR-nn` tests

Opt-in: `defaults.clean_room` absent or `mode: "off"` and the gate does not exist. Declared
`final`, `pr-ready` requires a GREEN clean-room run pinned to the current HEAD.

- [x] AC-CR-01 - suite green in the maker's tree but red at the candidate SHA -> clean-room
  RED and `pr-ready` blocked.
- [x] AC-CR-02 - a green run records `ok`, `status`, `ref` and a wall-clock.
- [x] AC-CR-03 - a new commit after a green run -> the previous evidence is stale for the
  gate; `pr-ready` blocked until it is re-run.
- [x] AC-CR-04 - `worktree_sha` recorded equals the candidate SHA.
- [x] AC-CR-05 - no leftover uscha worktree after a run.
- [x] AC-CR-06 - block absent -> `pr-ready` unchanged, AND the gate's effect is
  ATTRIBUTABLE: the same ledger returns pr-ready with the gate off, is blocked with it
  declared, and opens again once a green clean-room exists for HEAD.
- [x] AC-CR-07 - a failing `--setup` -> `SETUP_FAILED`, distinct from a red suite.
- [x] AC-CR-08 - with the gate declared, `phase --repo integration` returns a phase verdict,
  not a config-error crash. `integration` is a synthetic scope never present in
  `config["repos"]`; the gate resolved its path without the guard every other call site uses.
  Added after a fresh review reproduced the crash -- the criteria measured the feature and
  left the scope it runs in unmeasured.

## Reverse discovery, slice 1 (ADR-009/010/011) - feature acceptance, closes on green `AC-RD-nn` tests

Planned via `/uscha-adr-refine` against the sanitized reverse-discovery handoff; unticked
because the code does not exist yet - criteria before implementation, as always. Slice 2
(declared oracle divergences, spec-id, roundtrip) is out of scope here and gets its own
criteria when it starts.

- [x] AC-RD-01 - candidate spec with valid `evidence`/`confidence` frontmatter accepted;
  malformed frontmatter -> exit 2.
- [x] AC-RD-02 - an `evidence.refs` entry that does not resolve to a real `file:line(s)` ->
  candidate invalid, named.
- [x] AC-RD-03 - any candidate without a ledger verdict -> forward blocked, the reason names
  the candidate (the INV-CURATION-01 gate, measured).
- [x] AC-RD-04 - malformed `BEHAVIOR-LEDGER.md` (bad shape, unknown verdict, missing ADR
  ref) -> exit 2, never a silent "no verdicts".
- [x] AC-RD-05 - editing an existing ledger row -> append-only violation detected against
  git HEAD, named; without git the check reports UNMEASURED, never pass.
- [x] AC-RD-06 - `preserve` / `fix` / `undefined` produce three distinct, verifiable
  promotion effects.
- [x] AC-RD-07 - feature unused (no `discovery/`, no ledger) -> behavior identical to the
  prior release, and `cmd_spec_drift` untouched (ADR-011).

## Reverse discovery, slice 2 (oracle) - feature acceptance, closes on green `AC-RD-nn` tests

The `fix` verdict reaches the oracle: expected divergences are DECLARED
(`golden.divergences.json`, one ADR + reason each), never tolerated implicitly.
`roundtrip` is advisory coverage by embedded id - deliberately NOT semantic matching
(ADR-011: that stays out until it can be measured).

- [x] AC-RD-08 - an undeclared divergence still blocks; a DECLARED one reads
  `expected_divergence`, named with its ADR, and the verdict is CLEAN.
- [x] AC-RD-09 - declared divergent but byte-identical -> red, the reason names the ADR:
  the fix the declaration describes is not in the output.
- [x] AC-RD-10 - malformed `golden.divergences.json` -> exit 2, never a silent
  "no declarations".
- [x] AC-RD-11 - `roundtrip` reports promoted-candidate coverage by `uscha-spec:` id,
  lists the missing, and exits 0 - advisory end to end.
- [x] AC-RD-12 - `roundtrip` persists its latest state to the ledger and `dashboard --json`
  carries it ONLY when a run exists (virgin-ledger schema unchanged): an advisory that
  evaporates on exit is invisible to every read surface, which defeats the point.
- [x] AC-RD-13 - the three curation-family commands (`spec-drift`, `curation-check`,
  `roundtrip`) accept the SYNTHETIC `integration` scope and return a verdict, never a
  config-error crash. Second recurrence of the 1.63.0 class; the guard is now a helper
  (`_scope_path`) instead of a per-site pattern.

## SYSTEM-FACTS (T0, ADR-012) - feature acceptance, closes on green `AC-SF-nn` tests

Published claims become compiled artifacts of derived facts. Founding fixture: the site
claimed 1.65.0/32 subcommands while the repo was at 1.67.0/35 - live factual drift in the
project about factual drift.

- [x] AC-SF-01 - `facts` derivation is deterministic: two runs over an unchanged repo are
  byte-identical, and the facts come from the artifacts (parser introspection, tree
  inventory), never from prose.
- [x] AC-SF-02 - an injected wrong claim -> `facts --check` exits 1 naming file:line, the
  claim and the derived fact.
- [x] AC-SF-03 - a stale committed `SYSTEM-FACTS.json` is itself drift, named.
- [x] AC-SF-04 - correct claims + fresh facts -> exit 0.
- [x] AC-SF-05 - the Codex twin engine derives byte-identical facts: the twins are identical
  FILES, but a fixed-depth root walk made runtime behavior diverge by install location
  (version null, 0 skills, silently). Root is now found by marker, and facts that cannot
  locate their own VERSION exit 2 instead of emitting nulls.

## Diamond M1 (ADR-013/014) - closes on green `AC-DD/AC-CU/AC-FV` tests

Shipped in 1.69.0 (criteria preceded the code by one session). Namespace
note: the originating handoff numbered these `AC-RD-nn`, which collides with the thirteen
criteria already shipped under that prefix; renamed at planning time (ADR-013).

- [x] AC-DD-01 - discovery over a fixture emits a well-formed CANDIDATE-DELTA; every OBS
  carries id, type, evidence_class, provenance.
- [x] AC-DD-02 - an inference-only statement is `narrated`, never `static`/`measured`.
- [x] AC-DD-03 - a statement backed by an ingested characterization run is `measured`, run
  timestamp in provenance.
- [x] AC-DD-04 - re-running discovery on an unchanged fixture yields byte-identical OBS IDs.
- [x] AC-DD-05 - an OBS matching an existing canonical item carries `canonical_match`;
  unmatched carries null.
- [x] AC-DD-06 - the rendered `.md` twin regenerates from the JSON; hand edits are
  detectably overwritten.
- [x] AC-DD-07 - `discover --path` bounds the mechanical scans to the subtree; a bound
  matching no tracked file is a named refusal; the bound is recorded in the delta (and
  surfaced in the human-facing twin; sealed).
- [x] AC-CU-01 - promote over a delta with one uncurated OBS -> refusal naming it; ledger
  unchanged.
- [x] AC-CU-02 - `preserve` promotes into the canonical package with `derived_from` lineage.
- [x] AC-CU-03 - `fix` never enters the canonical package; an ISSUES-DEFERRED entry exists.
- [x] AC-CU-04 - `undefined` appears as open in the status readouts.
- [x] AC-CU-05 - re-curation supersedes without deleting; both records retrievable.
- [x] AC-CU-06 - no CLI/skill path performs curation without an explicit human verdict per
  OBS (absence of batch-accept asserted).
- [x] AC-FV-01 - fidelity emits all v0 dimensions with per-dimension provenance.
- [x] AC-FV-02 - a file with no canonical/OBS lineage -> `unexplained_code` > 0, file named.
- [x] AC-FV-03 - configuring any advisory-class dimension as blocking -> engine refusal
  (INV-ADVISORY-01).
- [x] AC-FV-04 - `curation_closure` < 1.0 whenever uncurated OBS exist; 1.0 only when none.
- [x] AC-FV-05 - the measured dimensions are deterministic: same inputs, same numbers.

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
- ADR-007 — Evidence records the commit and tree state it was measured at.
- ADR-008 — The clean-room verifies the COMMIT; the engine never decides what to run.
- ADR-009 — Candidate specs in quarantine: the agent authors, only the human promotes.
- ADR-010 — The behavior ledger: human-readable table, machine-enforced rules.
- ADR-011 — No shared extraction engine; spec-drift and reverse discovery stay separate.
- ADR-012 — Published claims are compiled artifacts of derived facts (SYSTEM-FACTS).
- ADR-013 — Discovery emits a typed CANDIDATE-DELTA; verdicts become ledger objects.
- ADR-014 — Fidelity is a vector; an advisory-class dimension can never gate.

Each ADR carries its own checkable Verification block; the executable form of those checks is
the smoke suite (`uscha-kit/tests/smoke-engine.sh`), not `AC-nn` criteria here — a kit change
is accepted by a green smoke, which is how uscha verifies its own engine.
