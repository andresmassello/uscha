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

- [x] AC-02 — The six version surfaces (`uscha-kit/VERSION`, `uscha-kit/uscha.config.json`, both `plugin.json`,
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

Planned via `/uscha-adr-refine` against the sanitized reverse-discovery handoff - criteria
before implementation, as always, and unticked while that was still the whole story. It is not:
the code shipped in 1.64.0 and every criterion below has closed on its own green `AC-RD-nn`
case since (measured by T120, sidecar `.curation-cases.json`). Slice 2 (declared oracle
divergences, spec-id, roundtrip) has its own section below and shipped in 1.65.0.

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
- [x] AC-FV-06 - fidelity respects the delta's `--path` bound: mechanical dimensions
  measure only files under the bound, and the scope is named in each provenance.

## Diamond M2 (ADR-015) - the canonical package extracts into a typed graph

- [x] AC-IR-01 - `ir-extract` over a fixture emits a well-formed typed graph; every node
  carries id/type/source, every edge has resolvable endpoints.
- [x] AC-IR-02 - a line that cannot be deterministically typed lands in `untyped`, is
  counted in the UNTYPED rate, and is never given a guessed id.
- [x] AC-IR-03 - native ids are reused (AC-nn, ADR-nnn, INV-*); edges derive from real
  references; re-extraction over unchanged sources is byte-identical.
- [x] AC-IR-04 - `ir-render` regenerates the human view; extract -> render -> extract is
  content-stable for the structured parts.
- [x] AC-IR-05 - an unknown `schema_version` or a hand-edited graph is `exit 2`, never
  mis-read.
- [x] AC-IR-06 - `fidelity --ir` answers `curation_closure` as a graph path query and
  reproduces v0's FIELD-RUN-001 number.

## Diamond M3 (ADR-016) - the LLM is a compiler with a validated output contract

- [x] AC-CC-01 - a well-formed compilation over the reference IR passes `compile-validate`;
  every trace_manifest id resolves to an IR node and every unit hash matches disk.
- [x] AC-CC-02 - the manifest cannot lie: a trace_manifest id that is not an IR node, a unit
  whose file/hash does not match disk, and a hand-edited seal each `exit 2` naming the fault.
- [x] AC-CC-03 - a `canonical_ir.ir_hash` this repo cannot reproduce is refused (`exit 2`); a
  compilation never validates against an absent or stale IR.
- [x] AC-CC-04 - a degenerate manifest (everything traces to everything) and an empty
  `unresolved_intent` are flagged `advisory` and printed, and `compile-validate` still exits
  0 — statistics never gate (INV-ADVISORY-01).
- [x] AC-CC-05 - `compile-ingest` records each `unresolved_intent` as an append-only,
  content-addressed `UINT-` object with an `ISSUES-DEFERRED.md` mirror; re-ingest supersedes,
  never duplicates.
- [x] AC-CC-06 - by-construction `unexplained_code`: a source unit absent from the
  trace_manifest is named and counted in the compilation's ingest record.
- [x] AC-CC-07 - two reference compilations produced by two different models both pass
  `compile-validate`; the contract is backend-blind.

## Diamond M4 (ADR-017) - a bounded subsystem's identity is its canonical package + a withheld oracle

- [x] AC-BS-01 - `bootstrap-oracle` runs the withheld oracle against a compiled implementation
  and exits 0 iff every case matches its expected exit; the canonical system passes all-green.
- [x] AC-BS-02 - the oracle is decisive and names divergences case-by-case: an implementation
  that allows a case the contract blocks fails, `exit 1`; the runner consults no model.
- [x] AC-BS-03 - the maker≠checker wall is asserted mechanically: no compiled source references
  the withheld oracle or its cases.
- [x] AC-BS-04 - the three round-1 compilations pass `compile-validate` against the pinned
  canonical IR (the compile interface is M3's contract).
- [x] AC-BS-05 - `bootstrap-variance` reports per-impl metrics and pairwise divergence proving
  the implementations genuinely differ; advisory, never a gate.
- [x] AC-BS-06 - the S-gap loop is measured and bounded (N=2): a round-1 divergence records its
  failing cases to the ledger, and the improvement round makes at least one independent
  recompilation oracle-green; partial convergence is reported, not chased.

## Diamond M5 (ADR-018) - the Diamond Bench: regeneration fidelity across archetypes

- [x] AC-DB-01 - `bench` over the bench directory emits a per-archetype verdict table and writes
  `DIAMOND-BENCH.md`; every number traces to a compile-validate/bootstrap-oracle run.
- [x] AC-DB-02 - each entry's withheld oracle is discriminating: a degenerate stub scores below
  the real compilers and never all-green; an entry whose oracle a stub satisfies is `FAIL`.
- [x] AC-DB-03 - a `PASS` entry has >=3 oracle-green compilations that genuinely differ; a
  near-identical (byte-identical) convergence is `FAIL`, not `PASS`.
- [x] AC-DB-04 - model identities are anonymized in the headline table; the raw identity mapping
  is present in the per-entry data.
- [x] AC-DB-05 - an entry with no compilations yet is `PENDING`, counted, never silently
  dropped; the bench reports honestly on a partial set.
- [x] AC-DB-06 - no compiler input references any oracle; the maker≠checker wall holds across
  every bench entry.

## Diamond controlled-language (ADR-019) - free prose vs EARS+STE, same withheld oracle

- [x] AC-CL-01 - `lang-compare` over the two arms emits `CONTROLLED-LANGUAGE-REPORT.md` with
  per-arm oracle/variance/unresolved_intent and the three deltas; every number traces to a run.
- [x] AC-CL-02 - the oracle-identity invariant holds: two arms with differing oracle files are
  refused (`exit 2`), naming the mismatch — the comparison is apples-to-apples by construction.
- [x] AC-CL-03 - both arms' three compilations `compile-validate` against their pinned IR; no
  compiler input references the oracle (the maker≠checker wall holds across both arms).
- [x] AC-CL-04 - the verdict is behaviour-first: reduced variance WITH a behavioural regression
  (a lost all-green or a mean pass-rate drop) is `MIXED`, never `REDUCED`; a zero delta is
  `NO EFFECT` — the regression cannot be masked as a win.
- [x] AC-CL-05 - the `unresolved_intent` specificity proxy is deterministic and per-arm
  (distinct `ir_region`s + mean rationale length), reproducible across runs.
- [x] AC-CL-06 - the reference guard passes the shared oracle unchanged, and arm-B's IR differs
  from arm-A's while the oracle is byte-identical (authoring changed, behaviour held fixed).

## Diamond Bench v0.2 (ADR-020) - nine archetypes

- [x] AC-BG-01 - each of the five new entries (rest-handler, crud-store, worker, ui-render,
  protocol-adapter) has canonical/ + pinned IR + withheld oracle + committed stub, and `bench`
  reports all nine entries with a verdict (no PENDING at ship).
- [x] AC-BG-02 - every new oracle rejects both its degenerate stub AND a plausible-wrong
  implementation violating a SPEC-named sharp edge, checked before any compilation ran.
- [x] AC-BG-03 - all 20 new compilations (five entries x four compilers since ADR-042)
  `compile-validate` against their entry's pinned IR; no compiler input references any oracle -
  the cross-vendor arm's source is held to the same maker!=checker wall as the three Claude
  arms; `unresolved_intent` is each model's verbatim return.
- [x] AC-BG-04 - the worker entry's SPEC states the deterministic-scheduling boundary
  explicitly; the bench/changelog carry it as a named limitation.
- [x] AC-BG-05 - the discrimination evidence is committed and reproducible: every
  plausible-wrong implementation under each new entry's wrong/ scores below oracle-green, run
  by the suite itself — a red run of a committed fixture, not a prose note.

## Controlled-language v0.2 (ADR-021) - the control arm and the confound kill

- [x] AC-CL2-01 - parser-controlled is an EARS+STE re-expression with its own IR (differs from
  parser-free's) while the oracle is byte-identical; all six new compilations compile-validate;
  no compiler input references any oracle.
- [x] AC-CL2-02 - the control comparison (parser-free vs parser-controlled) measures NO EFFECT
  with both arms 3/3 oracle-green — the instrument can show nothing where nothing is expected.
- [x] AC-CL2-03 - the de-confounded comparison (guard-free-r2, byte-matched scaffolding, vs
  controlled) measures REDUCED with the variance delta beyond the margin — v0.1's signal
  survived its confound.
- [x] AC-CL2-04 - the three generated reports exist (v0.1, control, de-confounded); every
  number traces to a run.

## Fidelity per compiler (ADR-022) - reverse discovery applied to each compiled artifact

- [x] AC-FC-01 - `bench --fidelity` emits the descriptor for every compilation; without the
  flag, no descriptor appears and output is unchanged.
- [x] AC-FC-02 - `static_surface` comes from the M1 static extractor over the compiled source
  and is deterministic across runs; `oracle_passrate` and `trace_coverage` match independent
  recomputation from the bench's own artifacts.
- [x] AC-FC-03 - `curation_closure` is the literal UNMEASURED where no human verdict exists,
  and exactly judged/total where one does (never any other shape, never a fabricated 0.0);
  the descriptor never changes any verdict.

## Controlled language v0.3 (ADR-024) - replication across archetypes

- [x] AC-CL3-01 - both new archetype pairs: arms compiled blind, same generation, oracle
  byte-identical across arms; every compilation validates against its arm's IR and carries a
  non-empty `unresolved_intent`, distinct across the three models.
- [x] AC-CL3-02 - `lang-compare` verdicts pinned over the committed fixtures: state-machine
  NO EFFECT (deltas inside the margins), transformer WORSE (an oracle-green lost; the
  divergence is the withheld `extra-field-tolerated` case on the controlled opus
  compilation); interpreter-stable across 3.8 and 3.13.
- [x] AC-CL3-03 - the v0.3 summary states the aggregate as "1 of 4" with per-archetype rows;
  the WORSE row publishes with the same prominence as the REDUCED.

## Bench curation (ADR-023) - the human verdict extended to machine-generated code

- [x] AC-BC-01 - `bench-curate` records one verdict per call and appends (a superseding
  verdict keeps the earlier record); batch input, an unknown observation and a malformed
  store are refused with exit 2 (fail-closed, never degrade).
- [x] AC-BC-02 - `bench --fidelity` reports measured `curation_closure` (judged/total) for
  compilations with at least one verdict and the literal UNMEASURED for the rest; verdicts
  never change.
- [x] AC-BC-03 - a fixture edit after curation invalidates the stale observation id:
  `bench-curate` refuses the verdict and `--list` shows the divergence as STALE.
- [x] AC-BC-04 - `bench-curate --compilation` is a backward-compatible alias of `--dir`
  (both resolve to the same `dest`): `--compilation c-opus --list` produces byte-identical
  stdout and exit code to `--dir c-opus --list`.

## Slack hypothesis (ADR-025) + lang-compare IMPROVED verdict (ADR-026)

- [x] AC-SH-01 - the `scheduler` bench oracle discriminates: the degenerate stub is red, EVERY
  `wrong/` implementation (each breaking exactly one rule) is red, and the bench's own
  discrimination gate over the entry agrees; the reference passing 100% is evidenced by the
  `c-opus` compilation, 30/30 (no separate reference implementation is committed).
- [x] AC-SH-02 - the four blind `scheduler` compilations `compile-validate` against the pinned
  IR; each `unresolved_intent` is non-empty, bounded (2-5 entries), and model-distinct
  (verbatim, not synthesized); the bench verdict for `scheduler` is `PARTIAL` with the pinned
  per-compiler oracle counts (codex 30/30, opus 30/30, sonnet 26/30, haiku 25/30 of 30 - the
  cross-vendor arm matches opus and the entry stays PARTIAL, because PARTIAL is the min-rate
  verdict, not the max); the bench now
  reports 10 entries.
- [x] AC-LI-01 - the `lang-compare` verdict rule (REDUCED / IMPROVED / MIXED / NO EFFECT /
  WORSE, ADR-026) is reachable and correct across the five committed same-generation pairs;
  every JSON report carries the `improved`/`regressed` booleans.
- [x] AC-LI-02 - the four pre-existing pinned verdicts are unchanged by the ADR-026 rule
  addition: guard `REDUCED` (`MIXED` on Python 3.8, the same interpreter-pinned expectation
  AC-CL2-03 carries), parser `NO EFFECT`, state-machine `NO EFFECT`, transformer `WORSE`.
- [x] AC-SH-03 - `lang-compare` over `scheduler-free` vs `scheduler-controlled` (oracle
  byte-identical across both arms and to the bench entry's own oracle) yields the pinned
  `IMPROVED` verdict (`improved` true, `regressed` false, oracle-green delta +1, mean pass-rate
  delta > 0.02, variance delta > 0.05); `CONTROLLED-LANGUAGE-V03.md` states "5 deconfounded
  archetypes" with the `scheduler` `IMPROVED`, `transformer` `WORSE` and `REDUCED` rows present.
- [x] AC-LI-03 - the rendered `CONTROLLED-LANGUAGE-SCHED.md` states `## Verdict: IMPROVED` and
  names the "convergence on a shared error" reading, both in the committed file and in a fresh
  regeneration.

## Intra-model variance (ADR-027) - the noise floor under the bench

- [x] AC-R2-01 - `bench --dir BENCH --json` output is byte-identical whether the `r2/` second-run
  directories are present or removed; the real bench reports 12 entries with `PARTIAL` exactly
  `{guard, rest-handler, scheduler, transformer}` - `transformer` joined at 1.99.0, and it is
  the cross-vendor arm's one loss (ADR-042).
- [x] AC-R2-02 - `bench-r2 --dir BENCH --json` reports, for every entry, `has_r2` true, a `class`
  in `{SIGNAL, NOISY, NOISE}` equal to the expected function of the ratio (`< 0.5` SIGNAL,
  `< 1.0` NOISY, else NOISE), float `intra_mean`/`inter`/`intra_over_inter`, and exactly 4 models
  each with a float `intra_distance` and a boolean `behaviour_stable`; an entry with its `r2/`
  removed reports `has_r2` false, `class` null, and a non-empty `reason` (absent, never 0); an
  entry whose `r2/` is present but holds no parseable source reports `has_r2` true, `class` null
  and a non-empty `reason` (the review-found silent gap, now named);
  `protocol-adapter`'s reported `inter` matches an independent recomputation of the mean pairwise
  `_struct_distance` over its four run-1 implementations to 4 decimal places.
- [x] AC-R2-03 - all 40 `r2/` `COMPILATION.json` files `compile-validate` exit 0 against their
  entry's `IR.json`; each `unresolved_intent` has 2-6 entries and the four per entry are
  pairwise distinct; the aggregate is pinned (`verdict` NOISY, signal 1, noisy 7, noise 2, stable
  36, reruns 40) and every per-entry class is pinned exactly: SIGNAL `protocol-adapter`; NOISY
  `crud-store`, `guard`, `parser`, `rest-handler`, `state-machine`, `transformer`, `ui-render`;
  NOISE `scheduler`, `worker`. `parser` and `state-machine` left NOISE when the cross-vendor arm
  joined (ADR-042): a fourth compiler from another vendor widened the inter-compiler spread more
  than it raised the intra-model floor. Both landed within ~0.3 of the threshold (parser 0.73,
  state-machine 0.81), which ADR-027
  says to read as borderline - so the classes are pinned and the ratios are not.

## Non-Python archetype (ADR-028) - the method leaves Python

- [x] AC-JS-01 - Python untouched: `bench --json` entries equal 12 and the eleven Python entries'
  verdicts equal the pins `{crud-store PASS, guard PARTIAL, ledger-lite PASS, parser PASS,
  protocol-adapter PASS, rest-handler PARTIAL, scheduler PARTIAL, state-machine PASS,
  transformer PARTIAL, ui-render PASS, worker PASS}`; `bench-r2 --json` aggregate stays `verdict`
  NOISY, signal 1, noisy 7, noise 2, with 10 measured and both `rate-limiter` and `ledger-lite`
  `has_r2` false; `lang-compare` on scheduler-free vs scheduler-controlled stays `IMPROVED` with
  variance scores in their interpreter-stable ranges (free 0.015–0.03, controlled 0.17–0.20; the exact decimals move between 3.8 and 3.13 per ADR-027) (the refactor left Python metrics identical); `_impl_metrics` on
  a Python impl returns an `int` `ast_nodes`. The pins above were re-measured at 1.99.0 when a
  fourth compiler joined (ADR-042): `transformer` moved to PARTIAL and the r2 class counts to
  7/2. Neither move is the ADR-028 refactor - this criterion asserts that JS support did not
  disturb the Python path, and the values it compares against are whatever the current bench
  measures, never a frozen copy of the 1.85.0 run.
- [x] AC-JS-02 - the JS entry plus discrimination and the node-absent path: `rate-limiter`
  verdict `PASS`, each compilation oracle passed 25/25 with `compile_valid` true;
  `bootstrap-oracle` on `stub/stub.js` is not green; every file in `rate-limiter/wrong/*.js` is
  not green; with no `node` on `PATH` the entry reads verdict `PENDING` with a reason containing
  "node not on PATH" instead of a fake red or green — measured directly on a machine without
  node, and simulated on a machine with node by stripping `PATH` down to the Python
  interpreter's own directory, which also verifies the raw compilation oracle records carry
  `unmeasured`.
- [x] AC-JS-03 - metrics/distance/static-surface honesty for JS: `_impl_metrics` on a JS impl
  returns `lang`-agnostic `ast_nodes: None`, an `int` `loc`, and its lexical imports (e.g. `fs`);
  `_struct_distance` between two JS impls equals the two-dimensional mean (LOC delta + import
  Jaccard distance, no AST dimension) recomputed independently from their metrics dicts;
  `_extract_static_js` on a compiled JS unit returns observations naming exactly the module's
  own `module.exports` functions, reported by Node itself; `bench --fidelity --json` on the JS
  entry carries a `static_surface.functions` count and a sorted `names` list per compilation.

## Multi-unit archetype (ADR-029) - the bench leaves the single file

- [x] AC-MU-01 - single-unit Python entries unchanged: `bench --json` verdicts equal the pins
  `{crud-store PASS, guard PARTIAL, parser PASS, protocol-adapter PASS, rate-limiter PASS,
  rest-handler PARTIAL, scheduler PARTIAL, state-machine PASS, transformer PARTIAL, ui-render PASS,
  worker PASS}`; `lang-compare` on scheduler-free vs scheduler-controlled stays `IMPROVED` with
  variance scores in their interpreter-stable ranges (free 0.015–0.03, controlled 0.17–0.20; the exact decimals move between 3.8 and 3.13 per ADR-027); `bench-r2 --json` aggregate stays `verdict` NOISY, signal 1,
  noisy 7, noise 2, with 10 measured; a single-unit compilation (`guard`, `c-opus`) still reports
  `entry_unit` `source/guard.py` and `units` 1.
- [x] AC-MU-02 - `ledger-lite`'s `IR.json` carries at least one `DECISION` node and at least 2
  edges (the bench's first IR with edges, extracted from `docs/adr/ADR-001-model-cli-seam.md`);
  each of the four blind `COMPILATION.json` files ships exactly 2 source units, `compile-validate`
  exits 0 against the IR, and `trace_manifest` names exactly `{source/model.py, source/cli.py}`;
  the bench record's verdict is `PASS`, each compilation's oracle is 24/24, and every compilation
  carries `entry_unit` `source/cli.py` and `units` 2; `bench --fidelity --json` reports
  `static_surface.names == ["main", "post"]` for each compilation.
- [x] AC-MU-03 - discrimination holds for the multi-unit entry: `bootstrap-oracle` on
  `stub/source/cli.py` is not green; every `wrong/<name>/source/cli.py` is not green, including
  `wrong/balance-in-cli` (breaks the model/CLI seam by computing balances in the CLI) and
  `wrong/ignores-model` (ignores the model unit entirely); `bench --json` reports `ledger-lite`
  `discrimination.stub_green` false.

## Round-trip recoverability (ADR-030) - the reverse organs anchor facts, never a spec

- [x] AC-RT-01 - `bench-roundtrip --json` reports all 12 bench entries measured; the rendered
  report (both a fresh `--out` render and the committed `DIAMOND-ROUNDTRIP.md`) states, in
  words, that the instrument "does not regenerate an IR" from code, that `recoverability`
  "counts ONLY static + behaviour" footing, and that the manifest footing is "never counted as
  recovered"; running it regenerates no `IR*.json` or `*IR'*` file anywhere under the bench
  directory (a before/after file-tree snapshot is equal); `lang-compare` on the scheduler pair
  still reads `IMPROVED` with variance scores in their interpreter-stable ranges (free 0.015–0.03, controlled 0.17–0.20; the exact decimals move between 3.8 and 3.13 per ADR-027), and `bench --json` still reports 12
  entries with the same verdict pins `{crud-store PASS, guard PARTIAL, ledger-lite PASS, parser
  PASS, protocol-adapter PASS, rate-limiter PASS, rest-handler PARTIAL, scheduler PARTIAL,
  state-machine PASS, transformer PARTIAL, ui-render PASS, worker PASS}` - this instrument changes
  no bench verdict.
- [x] AC-RT-02 - for every compilation of every entry: `recoverability` is between 0 and 1;
  `anchored` never exceeds `static_anchored + behaviour` (when behaviour is measured) and never
  falls below the larger of the two, allowing overlap; `claimed` (the manifest footing) is
  always `>= anchored`; `behaviour` is an integer count between 0 and `ir_nodes` for every
  compilation - it read the literal string `UNMEASURED` until the diamond-bench oracles were
  curated with per-case `ac` tags (ADR-030 amended, 1.90.0); `edges_recovered <= edges`;
  `unanchored` is a list whose length equals `ir_nodes - anchored`; per-node detail carries the
  keys `id`/`static`/`manifest`/`behaviour`/`anchored`/`claimed`; `ledger-lite` - the bench's
  only entry with edges - reports `edges == 3` for every compilation and
  `edges_recovered_mean == 0.75`. That field is the mean COUNT of edges recovered per
  compilation, not a ratio: only `c-opus` anchors both endpoints of all three edges and the
  other arms anchor none, so the number is 3/N. It read 1.00 while N was 3, which looked like
  "all edges, always" and never was; ADR-042's fourth compiler recovers 0 and makes N 4, so the
  same 3 now reads 0.75.
- [x] AC-RT-03 - the aggregate is pinned to today's measured state: 12 entries measured, mean
  `recoverability` in `[0.81, 0.82]`, 1 entry with edges, behaviour measured in 12 of 12
  entries, and `behaviour` an integer in every compilation of every entry; the per-entry
  `recoverability_mean` is pinned exactly: `crud-store 0.857, guard 0.844, ledger-lite 0.667,
  parser 0.714, protocol-adapter 0.714, rate-limiter 0.75, rest-handler 0.893, scheduler 0.875,
  state-machine 0.857, transformer 0.857, ui-render 0.893, worker 0.857`; the instrument is
  id-regex + file reads + oracle runs with no AST involved, so a second Python interpreter (3.8)
  reproduces the per-entry means EXACTLY - measured, not assumed. Six of the twelve moved when
  ADR-042's fourth compiler joined (`guard`, `ledger-lite`, `rate-limiter`, `rest-handler`,
  `transformer`, `ui-render`), all downward: an entry's recoverability is the mean over its
  compilations, and the cross-vendor arm anchors a slightly different subset of each IR than the
  three Claude arms converge on. The aggregate is pinned as a RANGE and never as a float: before
  ADR-042 the twelve means summed to 9.930 and `9.930 / 12` was 0.8275 exactly, a rounding
  boundary that landed on 0.828 under 3.13 and 0.827 under 3.8. The 1.99.0 means sum to 9.778,
  `/12` = 0.81483, which is not on a boundary - the range stays anyway, because whether a given
  release's sum happens to be safe is not a property worth re-deciding every release. The
  cross-interpreter expectation is "within one thousandth", compared in integer thousandths.
- [x] AC-RT-04 - the curated `ac` tag is what is READ, and a tag asks a question rather than
  answering it. Over a TEMP COPY of one entry (the committed fixture is never written):
  stripping every `ac` field returns `behaviour` to the literal `UNMEASURED` in every
  compilation and the entry's mean to its static-only `0.000`; in one oracle carrying both, a
  tag on a case that PASSES anchors its node and a tag on a case that FAILS does not - the only
  difference between the two ids being the verdict of the case; and a tag written `ac_cs_1`
  matches the IR node `AC-CS-01`, because the comparison is made on ADR-036's normal form on
  both sides and the zero padding is not part of the identity.

## Out of scope for measurement here

- **Conventional commits** and **INV-GOLDEN-01** (never author a `.approved`) are enforced
  outside this file: the first by review, the second by a best-effort `PreToolUse` hook on the
  Claude target (text-matching, so an indirect write is NOT caught) plus `golden-diff`, which
  is the measured control because it compares bytes.
  They are invariants, not acceptance criteria — nothing here should pretend to measure them.
- **Coverage** of the engine is **instrumented** (the fork this file used to leave open was
  resolved by measuring, not by declaring an exemption). `USCHA_COVERAGE=1` wraps the one
  choke point the suite drives the engine through — ~370 subprocess calls — and the combined
  Cobertura report lands in `reports/coverage.xml`. Opt-in, so the default suite stays fast
  and needs no `coverage.py`.
  **Re-measured for 1.82.0** (D-03 widened the seam): `qa_ledger.py` read **58%** (6266
  statements, 2656 missed) against a declared threshold of 60 — down from the **84.2%**
  recorded on 2026-07-23, and genuinely so: the committed `reports/coverage.xml` from that date
  showed only 3788 valid lines total, against 6266 statements in `qa_ledger.py` alone. Not a
  regression that change caused, and not silently patched over.
  **Re-measured again for 1.90.0, and the honest half is WHY it moved: the instrument, not the
  suite.** Two seams were blind. `uscha_top.py` sat inside the `--source` root but was only
  ever driven in-process from `python -` heredocs, so it reported 0% while 24 acceptance
  criteria were measured against it; and the engine children that test blocks spawn from
  *inside* their own python were plain interpreters, so `cmd_fastpath_eval` read 1/132 covered
  lines while T117 measured nine criteria against it. Both are closed (a `pyin()` choke point,
  and coverage.py's documented multiprocess hook). Measured over the same suite:
  `qa_ledger.py` **86.6%** (6967 statements, 934 missed), `uscha_top.py` **73.2%** (537, 144),
  `.claude/skills/uscha-mirador/mirador-render.py` **95.6%** (91, 4),
  `telemetry-extract.py` **95.3%** (85, 4) — it read 0% before, present in the seam's `--source`
  root but never invoked — `templates/scripts/uscha_progress.py` **87.8%** (115, 14) and
  `uscha_statusline.py` **87.7%** (65, 8). Whole measured surface: **85.9%**, 7860 valid lines,
  6752 covered. New behaviour checks shipped in the same release (T142 `telemetry-extract`,
  T143 the mirador aggregate and its three friendly failures, T144 `uscha top`'s read boundary
  and refusals) and are worth having, but they are not what moved the number. Same shape as
  ADR-036, recorded the same way.
  Measuring this surfaced one unrelated pre-existing issue, flagged separately (not part of
  this change): `USCHA_COVERAGE=1` for the full suite made `AC-GM-08` fail, because
  `coverage.py`'s `COVERAGE_FILE` environment variable unconditionally overrides the isolated
  `data_file` the golden-coverage capture (`cmd_golden_coverage`) sets for itself — confirmed
  in `coverage/config.py`, reproduced on the unmodified 1.81.0 baseline. Under that
  combination the acceptance number read 128/129 and the plain suite was the gate.
  **Resolved in 1.90.0**: `cmd_golden_coverage` now sets `COVERAGE_FILE` explicitly on the
  child's environment, pinning the capture to its own data file whether or not the caller has
  one of its own. T117 asserts it directly — the same capture is run a second time with a
  `COVERAGE_FILE` planted in the environment, and the map must still come back MEASURED with
  the caller's file untouched.

## uscha top v0.1, M1+M2+M3 (ADR-031/032/033/034) - closes on green `AC-T-nn` smoke assertions and golden frames

Shipped in 1.86.0 (M1 = read-only board), extended in 1.88.0 (M2 = the live feed and its mtime poll)
and completed in 1.89.0 (M3 = VERDICTS mode, the application's single write, made by shelling out to
the engine's own `curate`). Criteria authored in `docs/uscha-top/SPEC.md` s7 and curated before code;
measured by T137 (engine `top --json` contract, including the derived feed and the verdict queue),
T138 (pure `render`, twelve golden frames, the poll primitive) and T141 (the write path, on temp
copies of the quarantine fixture) through the acceptance sidecar. Every v0.1 id is now measured; the
phase-2 keys (`d` diff, `o` rerun) shipped in 1.91.0 and carry their own criteria in the section
below (AC-T-25..29, ADR-037), not here. They close by the
suite, like every other family prefix — and since
1.87.0 (ADR-036) the engine also READS those family ids, so the green ones enter the measured
pipeline instead of counting as untagged (the gap ADR-035 item 6 recorded is closed).

- [x] AC-T-01 - the header shows `DONE x/N (p%)` from the engine-computed `terminado` block; the TUI derives nothing.
- [x] AC-T-02 - the header shows `machine owes M · you owe Q · untagged U` from `debtors`.
- [x] AC-T-03 - ETA renders per SPEC s3; with `medians.verdict_min` null (v0.1) it renders `-`.
- [x] AC-T-04 - with `terminado.unmeasured >= 1` the percentage carries the suffix `· N unmeasured` (INV-TOP-01).
- [x] AC-T-05 - the burn-up renders the `kind:"score"` series labelled as a score trend, never as closed obligations.
- [x] AC-T-06 - `spec_pin` renders git HEAD with a not-clean-room-verified marker; null renders `-`; never fabricated (INV-TOP-05).
- [x] AC-T-07 - one row per obligation, state-coloured, stable order by id.
- [x] AC-T-08 - TRACED and TAGGED render in the UNMEASURED-class gray, never as PASS (INV-TOP-02).
- [x] AC-T-09 - the GATE column shows `junit` or `curation` for a general project.
- [x] AC-T-10 - the AGE column renders `-` for every obligation in v0.1 (ADR-035).
- [x] AC-T-11 - (M2) the engine derives `events_tail`: the last <=8 steps, newest first, each `{ts, level, text}` with `level` from the fixed per-kind map, `ts` the step's `at` as UTC HH:MM:SS, `text` stripped of C0 controls, DEL, the 8-bit C1 range and every Unicode format char (category `Cf`) -- widened in 1.90.0; no steps -> `[]`.
- [x] AC-T-12 - (M2) the mtime poll: `_changed()` flips on a real disk change and only then, `--refresh` defaults to 2 s with a 0.5 s floor, and a `--once` frame renders the derived feed with timestamp and level letter. Measures the polling PRIMITIVE plus the rendered frame, not a driven TTY session.
- [x] AC-T-13 - (M3) `v` enters VERDICTS and the queue is exactly the uncurated observations the engine emitted, in its documented order: the criterion each anchors first, the unanchored after, the content-addressed id as the tie-break. NOT age-descending as first drafted - every `age_hours` is null, so there is no age to sort by (ADR-032 amended). `t`/`Esc` returns to BOARD; a curated OBS leaves the queue and only that one.
- [x] AC-T-14 - (M3) candidate and evidence side by side at 100 columns, stacked at the 80-column floor, and a claim longer than either column comes back whole across the pane's lines. A pane too short to hold it NAMES the shortfall instead of cutting in silence; the one-line queue label above may carry the engine's `…` cap, the claim in the pane may not.
- [x] AC-T-15 - (M3) `p`/`f`/`u` shells out to `curate` exactly once per keypress with the documented argv and advances; an empty queue returns to BOARD; the engine's refusal is surfaced and nothing retried. Also measured structurally: `uscha_top.py` opens no file for writing, dumps no JSON, builds exactly one `curate` argv, calls `apply_verdict` exactly once with no loop above that call, and drains the input buffer on every verdict path. Two refusals besides: a verdict key inside the 250 ms cooldown records nothing (a held key would otherwise judge the observation that just took the cursor's place) while navigation keeps working, and a `--state` run - a frozen snapshot, not a live ledger - refuses by name and spawns nothing.
- [x] AC-T-16 - (M3) after a real verdict, `terminado.done`/`pct` are unchanged (INV-TOP-03) and `debtors.you` drops by one, the four buckets still partitioning the board; no auto-rerun moves DONE.
- [x] AC-T-17 - (M3) the record the TUI path appends and the record a manual `curate` call appends, over two copies of the same fixture with the same arguments, are identical member for member - `at` (a wall clock in a subprocess) compared for shape.
- [x] AC-T-18 - stdlib-only; runnable via `python -m`; py3.8-clean.
- [x] AC-T-19 - `render(state, size)` is pure; golden frames byte-identical at 100x32 and 80x24.
- [x] AC-T-20 - no TTY -> `--once` prints one plain frame and exits 0.
- [x] AC-T-21 - 80x24 degradation keeps the layout; the feed shortens first.
- [x] AC-T-22 - Windows legacy conhost: VT via `SetConsoleMode` (ctypes); on failure degrade to the plain frame.
- [x] AC-T-23 - honesty negative case: 23/24 PASS + 1 UNMEASURED renders 96% with the suffix, never 100%.
- [x] AC-T-24 - single derivation: a frame rendered from a frozen `top --json` fixture traces every number to a JSON field.

## uscha top phase 2 (ADR-037) - closes on green `AC-T-nn` smoke assertions

Shipped in 1.91.0: `d` (spec<->code drift, read-only) and `o` (rerun). Criteria drafted in ADR-037
before the code and measured by T145 through the same acceptance sidecar, plus two DIFF golden
frames over `state/state-drift.json` - a frozen state whose drift block comes from a REAL
`qa_ledger.py spec-drift` run on a temp git repo, not from a hand edit. The contract grew two
members for this (`spec_diff`, nullable, and `repos`); ADR-032 is amended for both. What did NOT
change: the TUI still writes nothing itself, and DONE still moves only on ingested evidence.

- [x] AC-T-25 - `o` is inert without `--rerun-cmd` and says why; it refuses under `--state` (a frozen snapshot is not a live ledger) and with no configured repo. Each refusal spawns nothing - not the command, not the ingest - and leaves the ledger byte-identical. `o` answers on the BOARD only.
- [x] AC-T-26 - with `--rerun-cmd`, one keypress runs the human's shell string ONCE in the first configured repo's directory (`shell=True`, ADR-008 style: the string is the human's, never guessed) and then the engine's `snapshot --ledger ... --repo ...` ONCE, in that order, followed by a re-read. Both boundaries are replaced and their argv asserted, so nothing runs. A held `o` (a repeat inside the 250 ms cooldown) yields one run; a red run is ingested anyway and the status line names the exit code; a failing ingest says `snapshot FAILED ... nothing was ingested` instead of implying the board moved.
- [x] AC-T-27 - verdict keys record nothing while a rerun is in flight and `o` cannot stack on itself, while `j`/`t`/`q` keep working; the banner names the lock and the repo it picked. Measured PURELY (the flag is a caller-supplied boolean): the phase-2 rerun is synchronous, so while the command runs no key is read at all and what is typed meanwhile the drain throws away.
- [x] AC-T-28 - the loop closes on measured evidence: with the fixture's red case replaced by a green report, the REAL `_snapshot_call` leaves a ledger record equal member for member to a manual `qa_ledger.py snapshot` call's (the record's `at` and the report mtime - two wall clocks read inside a subprocess - compared for shape, not value), the feed's newest event is that snapshot, and `terminado.done` is up by one while `debtors.machine` is down by one. Stated narrowly: the AC recount reads the ingested REPORT, so the number moves as soon as the report does - what the snapshot adds, and what the TUI could not fabricate, is the recorded measurement and the event that names it. A verdict moves neither (AC-T-16).
- [x] AC-T-29 - structural, plus the read-only pane. Exactly one call site each for `_curate_call`, `_snapshot_call` and `_rerun_call`, none under a `for`/`while`, and exactly one place builds a snapshot call: three engine spawns exist in `uscha_top.py` BEYOND THE READ BOUNDARY and no more (ADR-033 as restated by ADR-037). The boundary is counted too rather than hand-waved: the module's spawn call sites (`subprocess.run`/`Popen`/`call`) total exactly FOUR - the three above plus the single read-only `top --json` read in `load_state` - so a fifth inlined spawn goes red whichever side of the boundary it lands on. The `d` pane renders byte-identical against its two golden frames at 100x32 and 80x24 with zero escapes on the plain path, shows only the SPEC_STALE docs worst-lag-first with the cardinality beside the one file it names, and - the case that matters most - a state with no `spec_drift` record renders "no spec-drift run recorded" plus the command that would produce one, never a clean board (INV-TOP-05). The engine half is asserted beside it on BOTH cases: no record -> `spec_diff: null`, and a hostile record spliced into a copied ledger (mixed verdicts, tied and missing lags, a junk non-dict row, a `newer_files` that is a string) comes back through the real `top --json` as SPEC_STALE rows only, worst-lag-first with the doc name as tie-break, `advisory: true`, `docs_total` over the dict rows only, and no code_ref invented out of a string's characters. The board's key hint no longer labels either key as `phase 2`.

## Sealed TERMINADO, INV-T1 (ADR-038) - closes on green `AC-CT-nn` smoke assertions

Shipped in 1.92.0. The invariant comes from an external `sh` package kept as reference under
`audits/uscha-cierre/`; what was taken is the piece the kit did not already have -- evidence ingested
by PATH and MTIME cannot answer "is this still the file that was measured", so `snapshot` now records
each report's `sha256` beside them, and `top --json` derives `terminado.sealed` at read time from the
ledger plus the tree. Nothing new is written anywhere, and the derivation is shared with the
`check-terminado` subcommand rather than duplicated. Measured by T146 over a REAL temp git repo the
engine drives end to end (`init` -> a real JUnit report -> `snapshot`), plus two golden frames.
Two limits stated rather than papered over: an UNMEASURED seal (no git, or a snapshot predating the
hash) decorates nothing on the board, and a project with NO snapshot at all can read 100% with the
seal silent -- `check-terminado` still exits 2 there, which is where the enforcement lives.

- [x] AC-CT-01 - on a clean subtree at the snapshot's commit the seal holds: `check-terminado` exits 0 and prints `SEALED`, `top --json` carries `terminado.sealed.ok: true` with no reasons, and the board's `pct` is a real 100 (the cap does not fire when the seal is intact). The ledger file and the report files the snapshot names are exempt from the tree check, which is what makes an untracked report and an untracked ledger a sealed state rather than a permanent refusal. Measured with a NON-ASCII report name too (`reports/junit/junit-acion.xml`, with the accent): git C-quotes such a path unless `core.quotepath=false` is set on the command, and a quoted path matches no exemption - so the seal would read dirty forever over the very file it exempts, and an altered-report reason would print octal escapes instead of the name.
- [x] AC-CT-02 - a TRACKED file modified after the snapshot: exit 1, `ok: false`, reason `repo subtree dirty: changes no snapshot covers (<path>)` (the scope is the configured repo's subtree, ADR-007's per-path scoping, not the whole work tree). And a `snapshot` taken ON that dirty subtree does NOT launder it: the record carries `origin.dirty: true` and the seal keeps refusing with the same reason - a snapshot is evidence of when the measurement happened, never a pardon for the state it happened in.
- [x] AC-CT-03 - an UNTRACKED file no snapshot covers: exit 1 with the file named (`-uall`, the collapse the reference suite caught), the board still 2/2 but its percentage capped at **99** by the engine, and removing the file re-seals it without any new snapshot.
- [x] AC-CT-04 - a new commit after the snapshot that touches SOURCE: exit 1, reason `stale seal: source changed since snapshot <sha>: <path>` (amended in 1.93.0 by ADR-039 — before it, any new commit read `stale seal: snapshot at <sha>, HEAD is <sha>`, which is still the verdict when the snapshot's commit is unreachable and the diff cannot be seen).
- [x] AC-CT-05 - a re-snapshot on the current state re-seals: exit 0 again. A verdict does not seal; a rerun's snapshot does (the same asymmetry as INV-TOP-03).
- [x] AC-CT-06 - a report EDITED after ingest, same path and same directory: exit 1 with `evidence altered after ingest: <path>` as the ONLY reason - the tree is clean and the mtime says nothing, which is precisely the hole path+mtime could not see and the reason the content hash was taken.
- [x] AC-CT-07 - a report DELETED after ingest: exit 1 with `evidence missing: <path>` as the only reason.
- [x] AC-CT-08 - the three exit codes are all reachable and each means one thing: 0 sealed, 1 a measured break, 2 UNMEASURED. Every unmeasured source is asserted: a directory that is no git work tree (`ok: null`, `commit: null`, stdout says `UNMEASURED`), a ledger with no snapshot recorded at all (`reasons == ["no snapshot recorded yet"]`, exit 2), a git repo with no commit yet (`git repo without commits - seal UNMEASURED`), and a ledger that is missing or is corrupt JSON - the last one because `_load` exits 1 by design and 1 here means "I checked and the seal is broken": a verdict on evidence nobody managed to read is the exact claim this command exists to refuse - the limit named above, measured so it cannot drift into a silent pass.
- [x] AC-CT-09 - one derivation, two surfaces: `top --json`'s `terminado.sealed` equals `check-terminado --json` member for member over the same tree, with no wall clock inside the block to excuse a difference (its members are exactly `ok`, `reasons`, `commit`, `repo` and — since 1.93.0, ADR-039 — `note`, which is null here because HEAD IS the snapshot's commit; the member list is pinned, so a key added to the seal has to be a decision).
- [x] AC-CT-10 - INV-TOP-06 on the board: the frozen `state-unsealed.json` (a real run over a copied fixture whose report was edited after ingest) renders byte-identical against two golden frames at 100x32 and 80x24, showing `DONE 6/6 (99%) · unsealed (evidence altered after ingest: reports/junit.xml)` - never 100% - with every `MEASURED_PASS` row's ACTION reading `seal: ...`, no escape on the plain path, and `render()` still pure. Its twin: a state with NO `sealed` member renders exactly as before, no suffix and no `seal:` cell, which is why the sixteen older golden frames did not move.
- [x] AC-CT-11 - backward compatible and honest about it: a snapshot recorded before 1.92.0 carries no `sha256`, so the hash check reads UNMEASURED (exit 2, reason `evidence hash unmeasured: <path> - no hash recorded at ingest (older snapshot, or the file was unreadable)`) and NOT `altered` or `missing`. An old ledger does not become a lie in either direction.

## Freshness by content and commit (ADR-039) - closes on green `AC-FR-nn` smoke assertions

Shipped in 1.93.0. The 1.31.0 freshness rule compares MTIMES, and three ordinary operations rewrite
every file's mtime without changing a byte of source: a fresh clone or CI checkout, a `git worktree
add`, and a merge or rebase that re-checks files out. The day INV-T1 shipped the maintainer's own
board read `DONE 0/195 - 195 unmeasured` on the release machine for exactly that reason. So the clock
rule keeps its job and gains a second, independent one: a report is also fresh when its `sha256`
still matches what the last `snapshot` recorded for it, that snapshot recorded a commit (ADR-007),
and git shows no source-relevant change since - `git diff --name-only <commit> HEAD -- <subtree>`
and `git status --porcelain -uall -- <subtree>`, both filtered by the engine's own `_SRC_EXT`, the
SAME set the clock rule already trusts. Either rule suffices; no git, no recorded commit or no
recorded hash leaves the clock rule alone. One derivation (`_report_fresh`) serves both the snapshot
record and the tag ingest, so the two surfaces cannot disagree. Measured by T147 over a REAL temp git
repo the engine drives end to end (`init` -> a real JUnit report -> `snapshot`).
Two limits stated rather than papered over: neither rule reads test SEMANTICS - a green report whose
fixtures live in an extension outside `_SRC_EXT` can be misjudged fresh, and the set is the limit -
and the kit's own repo does not flip to sealed on the strength of this change alone, because its
committed report is re-run after the snapshot it is compared against.

- [x] AC-FR-01 - a report the CLOCK rejects because a source file was re-dated after it (content byte-for-byte unchanged: what a clone, a worktree or a merge does) is FRESH by content: the criterion closes measured, `stale_reports` is empty, and the snapshot record SAYS WHY - `freshness.reason` names the commit (`content unchanged since <sha>`) and the report carries `fresh_by: content` rather than an unexplained pass.
- [x] AC-FR-02 - one changed byte in that same source file and it is stale again: rule (b) reads content, not dates, so what re-dating could not break, a real edit does - in the working tree, before any commit.
- [x] AC-FR-03 - a commit that touches only docs (`.md`) leaves the evidence current.
- [x] AC-FR-04 - a commit that touches a `.py` does not. The extension set is the whole difference between the two cases, and it is the same `_SRC_EXT` rule (a) already used - widening it widens both rules at once, never one.
- [x] AC-FR-05 - the hash guards rule (b): with the clock already rejecting it, a report whose bytes no longer match the ones the snapshot ingested is NOT rescued by content. A log edited after the run keeps its path and can keep its date; that hole was closed in 1.92.0 and stays closed.
- [x] AC-FR-06 - no git means rule (a) ALONE, and "alone" is MEASURED rather than asserted: `readiness` text and `top --json` (minus the wall clock) are byte-identical to the 1.92.0 engine read from tag `v1.92.0`, both on a committed `uscha-top` fixture and on a temp repo whose work tree was removed - where the report stays stale and the criterion stays unmeasured. The ONE payload difference allowed is the new optional `sealed.note`, and it is asserted null rather than skipped. Tag not fetched / no git -> UNMEASURED, never a silent pass.
- [x] AC-FR-07 - the seal, amended (ADR-039 amending ADR-038): with HEAD one commit ahead of the snapshot by docs and the ledger only - the self-applied repo's release commit - `check-terminado` exits 0, `sealed.ok` is true with no reasons, and a `note` names what moved (`HEAD <sha> differs from snapshot <sha> by non-source files only: ...`, capped at five). Put one source file in that diff and it is a break again: exit 1, `note` null, reason `stale seal: source changed since snapshot <sha>: src/main.py`, and the text output says UNSEALED.
- [x] AC-FR-08 - the baseline cannot launder ITSELF: on a repo whose code changed and was committed while the tests were never re-run, `snapshot` honestly records `freshness: stale` with the report marked `fresh_by: stale` - and the READ-TIME rule refuses that record as an anchor (its commit is HEAD and its hash was taken over that very file, so trusting it would answer its own question). The criterion stays UNMEASURED and the report stays listed as stale on both surfaces. Found in blind review before 1.93.0 shipped, and it is the difference between a freshness rule and a laundering machine.
- [x] AC-FR-09 - the RITUAL, end to end, which is the case this ADR exists for: commit the code (X), run the suite, `snapshot` at X, commit the ledger AND the JUnit it names (X+1) - so the report is necessarily inside the X..X+1 diff - then CLONE at X+1, the very operation that re-dates every file. The board reads the truth: fresh by content with the criterion closed, `check-terminado` exit 0, `sealed.ok: true` with no reasons, and a note naming the ledger and the report as the non-source files that moved. The seal does NOT re-add the named reports to its diff filter: the hash check already proves the file on disk is byte-for-byte the one ingested, which is strictly stronger than "this path did not appear in a diff".
- [x] AC-FR-10 - BUILD and HARNESS files are source-relevant for rule (b) AND for the seal: a commit that adds `run-tests.sh` (by extension) or `pom.xml` (by basename) after the snapshot makes the evidence stale and breaks the seal with the offending path named. A commit that rewrites what the suite runs changes what a green report means; `.md`/`.json`/`.xml`/`.txt` stay non-source, which is what keeps the ledger and the reports themselves tolerable.
- [x] AC-FR-11 - line endings are not content (1.93.1): a report ingested with CRLF and checked out as LF - and the mirror case - reads FRESH by content and SEALED, because the evidence hash is taken EOL-normalized (`_sha256_evidence`); the record carries `sha256_eol: "lf"` so a reader never guesses how it was taken, and a record from before the marker is compared against all three renderings of its text so an old ledger neither breaks nor gains a pass. What is NOT given away: one changed byte with the line endings untouched still reads `evidence altered after ingest`. 1.93.0 shipped with this named as a limit in SPEC 4 and the kit's own release board hit it the same day - `altered` about a file nobody had touched, and a board at 0/205.

## Stack and lifecycle (ADR-040) - closes on green `AC-LC-nn` smoke assertions

Shipped in 1.94.0. A field run closed sixteen ADRs with rigor and still fixed the stack as a MAJOR
line, as if a family were a decision; ten days before a declared go-live the test phase surfaced
that the chosen MINOR line had left OSS support months earlier and that a tool the operator wanted
from day one required the next major - a major upgrade at the most expensive possible moment, which
three questions in discovery would have avoided. So the front-half skills gain a MANDATORY "Stack
and lifecycle" round before the stack ADR (one question per turn, dates FETCHED from the official
source as they are asked, never from memory), the stack ADR gains a machine-readable `lifecycle:`
frontmatter block and the SPEC declares `go_live:`, and `spec-check` gains a lifecycle dimension
that compares the two. ADVISORY by construction, the spec-drift contract (ADR-005): it never gates,
never caps readiness and never changes an exit code. The limit is stated rather than papered over:
the engine measures that a date and a source were CITED and compares two dates - it cannot verify
that the cited source tells the truth. Measured by T148 through the `.lc-cases.json` sidecar.

- [x] AC-LC-01 - a stack ADR whose component's `eol` falls before the SPEC's `go_live` reads `expires before go-live (<eol> < <go_live>)` in `spec-check` text AND in `--json` (key `lifecycle`), and the same fact reaches the `readiness` advisory line - one derivation (`_lifecycle_report`) behind both surfaces, so they cannot disagree.
- [x] AC-LC-02 - `eol` at or after the go-live WITH a source cited reads `ok`, and nothing is flagged: the dimension speaks only when it matters.
- [x] AC-LC-03 - a missing/`unknown`/unparseable `eol` reads `no EOL cited` and a missing `source` reads `no source cited`. A named absence, never a silent pass; and a date that already expires keeps the sharper label even when its source is missing.
- [x] AC-LC-04 - the whole dimension is UNMEASURED, with the reason spelled out, when the SPEC declares no go-live and when no ADR carries a `lifecycle:` block at all - and the SAME fixture WITH a go-live reads `measured`, so the parse is proved to be doing work rather than failing quietly.
- [x] AC-LC-05 - advisory only: the `readiness` score is BYTE-IDENTICAL with and without an expiring component, and `dashboard --json` carries the `lifecycle` block. The key is CONDITIONAL, the `fast_path`/`spec_drift` rule: a project that declares nothing keeps the exact prior payload and the exact prior readiness text.
- [x] AC-LC-06 - a SPEC whose go-live is declared ONLY in the frontmatter reads the same on both surfaces: the `lifecycle` line `readiness` prints is byte-identical to the one `spec-check` prints for the same SPEC, and neither says UNMEASURED. The two are compared against EACH OTHER, so a reworded line cannot make the criterion pass for the wrong reason (1.98.1).
- [x] AC-LC-07 - the inline `**Go-live:** YYYY-MM-DD` form is read where a human writes it: EVERY prefix the pattern claims is measured rather than narrated - `-`, `*`, `1.`, `>`, `> -` and up to three leading spaces - and prose after the date is allowed. The date stays a WHOLE token - `2026-12-011` is not a go-live with a stray digit, it is not a go-live at all (1.98.1).
- [x] AC-LC-08 - and where the pattern must NOT fire, because a permissive prefix is how an EXAMPLE gets read as a declaration: a `**Go-live:**` line inside a fenced block (either fence marker) is skipped and the real line below it wins; a four-space- or tab-indented line is an indented code block, not a declaration; and `-**Go-live:**` glued to the marker is not a list item (1.98.1).

## Family-prefixed criteria (ADR-036) - closes on green `AC-FA-nn` smoke assertions

Shipped in 1.87.0. The instrument now reads `AC-<FAMILY>-<n>` beside the bare `AC-<n>`, so the 166
family-prefixed criteria above stop reading as untagged: measured acceptance for this repo goes from
6/172 to 165/172 without a single new test — the evidence already existed, the engine could not see
it. The bare form is pinned byte-identical against the previous engine (AC-FA-03) before any new
form is claimed. Measured by T140 through the acceptance sidecar.

- [x] AC-FA-01 - `_parse_acceptance_items` over a file mixing `AC-01`, `**AC-BC-07**`, `AC-T-24`, `ac_dd_3` and `AC-7-x` yields `AC-1, AC-BC-7, AC-T-24, AC-DD-3, AC-7` in that order (a numeric "family" is not one).
- [x] AC-FA-02 - `_ac_tags` over testcase names `AC-BC-01_x`, `test_ac_bc_1_y`, `AC-01_z`, `testAC01Q`, `testACBC07x` and a skipped `AC-T-11_w` yields exactly `AC-BC-1` (2 green) and `AC-1` (2 green): no spurious bare tag beside a family one, no camelCase family, no key for a skipped case.
- [x] AC-FA-03 - the bare form is unchanged: `readiness` and `dashboard --json` (minus the wall clock) from the engine read at tag `v1.86.1` - the last engine BEFORE the widening, never HEAD, which after the release commit would compare the new engine with itself - and from this one, over a bare-id fixture, are byte-identical. The anchor tag is re-pointed at a later release only by a changelog line that says so.
- [x] AC-FA-04 - the statusline agrees with the ledger it summarizes: `uscha_progress.py` counts the same done/total `_parse_acceptance_items` counts (3 done / 5 total) over the AC-FA-01 file.
- [x] AC-FA-05 - `top --json` over a ledger mixing both grammars emits the normalized obligation ids, `MEASURED_PASS` where a green testcase tags them, in the documented order (bare by number, then families alphabetically).
- [x] AC-FA-06 - `discover` reads family ids too: its canonical map no longer assumes a bare id (it crashed on `AC-DD-07` on the first 1.87.0 run, caught by T125), and an observation whose statement names a family id anchors that criterion (`canonical_match`) exactly as a bare mention does.

## Dogfooding (repo rule 9) - closes on green `AC-DF-nn` smoke assertions

Since 1.96.0 (ADR-041) the criterion is decided by git ANCESTRY, never by a clock. It used to
have a second arm comparing `readiness_history[-1].at` -- a wall clock written into a JSON file --
against the engine commit's committer time, and closing that unit mismatch cost a throwaway
`readiness --record` BEFORE every suite run: a record taken on a tree whose tests had not been
re-run, whose only job was to be newer than a commit. It manufactured the green it reported, it
created the amend trap, and ~46% of `readiness_history` since 2026-08-18 is that step rather than
the product. The question was always about ORDER, and git records order. AC-DF-02..04 are measured
by T150 through the `.df-cases.json` sidecar, driving the outcomes over real temp git repos
(including a real `git clone --depth 1`) through the SAME `dogfood_verdict` the acceptance
emitter calls.

- [x] AC-DF-01 - the root `QA-LEDGER.json` was recorded after the last engine change, decided by ancestry: the commit that last touched `qa_ledger.py` is the ledger's commit or an ancestor of it = GREEN; the ledger's commit is an ancestor of the engine's (HEAD is the code commit X, the evidence lands in X+1) = UNMEASURED; diverged histories = RED; shallow clone or no git = UNMEASURED. No clock is consulted.
- [x] AC-DF-02 - the two green shapes both read `pass`: one commit carrying engine and ledger together, and the X -> X+1 ritual where the engine commit is an ancestor of the ledger commit.
- [x] AC-DF-03 - HEAD is the code commit X (the ledger's commit is an ancestor of the engine's) reads `skip` = UNMEASURED - not green, not red: the honest report of a measurement that has not happened yet.
- [x] AC-DF-04 - a ledger recorded on a history that does not contain the engine change (both branches merged, neither commit containing the other) reads `fail`; a tree with no git at all reads `None` = UNMEASURED, never a silent pass.
- [x] AC-DF-05 - the shallow guard is MEASURED, not asserted: the SAME history reads `pass` in full and `skip` at `--depth 1`, because `git log -1 -- <path>` returns HEAD for every path in a shallow clone and the criterion would otherwise pass without measuring anything. Delete the guard and the shallow clone joins the greens.

## Audit fixes (1.94.1) - closes on green `AC-AU-nn` smoke assertions

Shipped in 1.94.1. An audit of the harness and the engine found five ways a red thing could read
green, and every one of them was the same mistake in a different costume: absence rendered as a
number, or a measurement discarded before anyone read it. Two live in the SUITE -- a `chk` whose
`FAIL=$((FAIL+1))` incremented a copy inside a `( cd ... )` subshell, and a T-block that ran after
`SMOKE_STATUS` was frozen and after `$FAIL` was handed to the acceptance emitter -- so neither can
be caught by running the suite: they are pinned by a STATIC scan of the suite file itself. Three live in the ENGINE: a corrupt JaCoCo module report summed as `(0, 0)`
while `report_found` stayed true, an explicit `--<linter>` path that did not exist ingested as
silence and exited 0, and the synthetic `integration` scope crashing `fastpath-eval` and
`cleanroom` because they read `_repo_cfg` instead of `_scope_path`. Measured by T149 through the
`.au-cases.json` sidecar.

- [x] AC-AU-01 - no `chk` call sits inside a `( cd ... && ... )` subshell: the counter it raises dies with the subshell, so the check is reported and then discarded. Pinned statically over the suite's own source, because running the suite is exactly what cannot detect it.
- [x] AC-AU-02 - the `== T85` header sits BEFORE the `RESULTADO BASE` line, so its verdict reaches both readers: `SMOKE_STATUS` (the process exit code) freezes there, and the acceptance emitter comes later still. Below that line T85 reached neither - it sat past the emitter too. Pinned as a line-order assertion over the suite's own source.
- [x] AC-AU-03 - one unreadable module report makes the WHOLE JaCoCo reading UNMEASURED, and unmeasured means **0.0**, never the surviving modules' percentage: two valid maven modules sum to 50.0% and `check-coverage` says BELOW; truncate one and `check-coverage` refuses with no traceback, `snapshot` prints and persists `coverage=0.0% (found=False)`, and `readiness` scores the coverage dimension 0.0 - the reader that computes `pct/threshold` without consulting `report_found` is the one this invariant protects.
- [x] AC-AU-04 - a well-formed report whose `LINE` counter is not a number (`missed="N/A"`) is the same named absence: `report_found` false, no traceback, never an invented percentage.
- [x] AC-AU-05 - an EXPLICIT linter report path that does not exist fails closed (exit 2) naming the path, the same treatment an unparseable report already gets; a mistyped `--ruff` is a typo, never a gate with no findings. A report that IS there still ingests and exits 0.
- [x] AC-AU-06 - `fastpath-eval --repo integration` and `cleanroom --repo integration` no longer die with `no config entry for repo 'integration'`: the synthetic scope goes through `_scope_path`, the helper extracted for exactly this crash class.

## Release ritual (ADR-041) - closes on green `AC-RL-nn` smoke assertions

Shipped in 1.96.0. The ritual was ~20 manual steps and eight ordering invariants written as prose
in `CLAUDE.md` rule 9, with the most dangerous one -- never amend X after the record -- in capitals
because it had been hit. Prose a human re-reads is not an instrument. `tools/release.py` performs
the six steps and REFUSES loudly, naming the invariant (I1..I8) each refusal protects. It is
repo-level and never shipped: `package.json` `files` does not carry `tools/`, so a bug in it can
cost a release but can never reach an installed kit. It imports `_src_relevant` from the engine by
path rather than re-typing the extension tables -- one definition of "a change that invalidates a
test run" (ADR-039), not two. Measured by T151 through the `.rl-cases.json` sidecar, driving
`--dry-run` for the refusals it can measure without committing (AC-RL-01, AC-RL-02) and REAL
local runs against throwaway fixture repos for the ones that need commits to exist (AC-RL-03,
AC-RL-04, AC-RL-05). `--dry-run` itself writes nothing and touches no network, so it can be run
against the repo it is about to release.

- [x] AC-RL-01 - I1 is about whether X can be a fast-forward, NOT about a clean tree: a branch diverged from `origin/main` is refused naming I1, a half-done merge (MERGE_HEAD plus an unmerged path) is refused naming I1, and the same branch ahead of `origin/main` only passes preflight **with the tree dirty** - the working tree is X's payload, not a reason to refuse.
- [x] AC-RL-02 - a missing `uscha-kit/CHANGELOG-<X.Y.Z>.md`, or one whose `Suite: __SUITE__ checks · 0 fail; acceptance __ACC__.` placeholder line is absent, is refused naming I2; an already-existing `v<X.Y.Z>` tag is refused naming I2 too.
- [x] AC-RL-03 - the commits have the right shapes: X is the CODE commit - the six version surfaces (one hit per file), the regenerated `SYSTEM-FACTS.json` **and whatever the human left uncommitted** - while X+1 carries the ledger and the changelog counts line and nothing else.
- [x] AC-RL-04 - X amended between the code commit and the record is refused naming I5: the recorded identity of X no longer matches HEAD, which is the trap the pre-record created and rule 9 wrote in capitals. The fixture ASSERTS its own precondition - X's sha must actually have moved - so an amend that produced a byte-identical commit reports itself instead of blaming the engine (1.98.1).
- [x] AC-RL-05 - an X+1 whose staged set carries a source-relevant path (by the engine's own `_src_relevant`) is refused naming I6: the ledger commit carries evidence, never code.
- [x] AC-RL-06 - the whole ritual runs from a `git worktree add` of a wip branch while main is checked out in the primary tree (repo rule 9's own shape): the six steps complete, `check-terminado` prints SEALED at X+1 (I7), the push lands on `origin/main`, and the busy local `main` ref is left untouched with `git -C <path> merge --ff-only <sha>` printed for the human. Nothing is ever checked out - `git checkout main` inside a worktree fails with "already checked out at ...", which would have refused every real release.

## Docs as generated artifacts (1.97.0) - closes on green `AC-DC-nn` smoke assertions

Seven of the nine `SKILL.md` files carried a byte-identical "First contact" + "Orientation
markers" block and the two short ones a second copy: 18 runtime files, across two skill trees,
kept in step by hand. The files must stay WHOLE -- an agent loads one `SKILL.md` and nothing
else, so there is no include mechanism to lean on -- so the duplication stays on disk and its
SOURCE moves: the canonical text lives once under `tools/skill-blocks/` and
`tools/gen-skill-blocks.py` renders it into the region between two markers. This is the same move
`SYSTEM-FACTS` made for published claims (ADR-012): the artifact stays where its reader needs it,
the truth moves upstream of it. Measured by T152 through the `.dc-cases.json` sidecar, driving
the generator over the REAL repo and over throwaway copies of the two trees -- never mutating the
repo it is testing, which is what the `--root` flag exists for.

- [x] AC-DC-01 - `python tools/gen-skill-blocks.py --check` exits 0 over this repo: every one of the 18 marked regions equals what the template renders. A hand edit inside a region is therefore a red the suite reports, not a divergence someone notices six releases later.
- [x] AC-DC-02 - one word changed inside one region of a throwaway copy makes `--check` exit **1** and NAME the file, and the check writes nothing while saying so - a checker that repaired what it reported would be a checker whose green means nothing.
- [x] AC-DC-03 - a deleted begin marker makes `--check` exit **2** and name the file: a configuration fault is not a drift, and collapsing the two would let a deleted marker read as "nothing to update".
- [x] AC-DC-04 - `docs/adr/INDEX.md` is measured, not trusted: every `docs/adr/ADR-*.md` has **exactly one** row, every row's link resolves to the file it names, every row's status text equals that ADR's own `## Status:` line **verbatim**, and no row names an ADR that does not exist. The index claims to be the map over a flat folder; nothing but a check keeps that true. ADR-041 shipped in 1.96.0 with no row at all, and the first draft of 1.97.0 put its amendment in the INDEX row only - an index saying something its source did not.

## The claims writer (1.97.0) - closes on green `AC-FW-nn` smoke assertions

ADR-012 made published claims comparable against derived facts; it never made them WRITABLE. So
every version bump was ~25 hand edits across ~13 files, and `tools/release.py` could only print
the drift and hand it back (I3). `facts --write` rewrites the claims the SAME recogniser finds --
one `_iter_claims`, two consumers, because a writer that re-implemented the patterns could
disagree with the checker -- and then re-runs `--check`: a writer that reported its own success
would be exactly the self-graded evidence this engine exists to refuse. The recogniser also grew
spelled-out counts, which is how the paper's canonical `.tex` had sat outside every gate while
claiming "nine agent skills and ... 53 subcommands" in one sentence. Measured by T153 through the
`.fw-cases.json` sidecar, over throwaway fixtures -- never over the repo's own pages.

- [x] AC-FW-01 - `--write` rewrites a stale claim to the derived fact and the `--check` it implies then passes; the rewrite is in the AUTHOR's notation (a spelled-out claim stays spelled out, keeping its leading capital) and the file's CRLF line endings survive byte for byte, because normalising them would turn a one-token fix into an unreviewable whole-file diff.
- [x] AC-FW-02 - `--write` over a file with no recognised claim leaves it **byte-identical** and does not report it: the writer only touches lines it recognises, and "no claims" is not a reason to rewrite a file.
- [x] AC-FW-03 - a spelled-out count is a claim: a fixture reading "seven skills" is RED against a derived nine, naming `skills.count` and the word it read; the same fixture with the right word is green. The pattern is anchored on the kit's own noun phrases (`<n> skills`, `<n> agent skills`, `<n> subcommands`) and nothing wider, because a WRITER that guessed at "two other skills" would corrupt the sentence it fixed.
- [x] AC-FW-04 - there is **one** gated file list (`tools/facts-gated-files.txt`, read by the deploy, the suite and the release), the written set IS the checked set, every path it names exists, the three paper paths are in it, and every `# deployed` path has its canonical twin in the `# canonical` section. That last clause is the load-bearing one: `site/docs/*` is build output that `site/sync-docs.sh` deletes with `rm -rf site/docs` and regenerates from `docs/`, so a rewrite that lands only in the copy is undone by the next deploy. Asserted by importing `tools/release.py`'s own `facts_gated_sections` - a second copy of the list here would be the very thing this change removed.
- [x] AC-FW-05 - a gated file that is not valid UTF-8 is a **named skip**, never a traceback: `--write` names it, leaves its bytes untouched, still writes the rest of the list, and exits **2** so the release refuses (I3) instead of proceeding on a claim set it could not fully write. `--check` reads that same file with `errors="replace"` and still reports its claims, so nothing is hidden - but the writer must not read it that way, because writing a replaced byte back would destroy data to correct a version number.

## Narrated backlog, round 1 (1.98.0) - closes on green `AC-VC-nn` smoke assertions

A `VISION` / `planned` / `not yet` label is a promise the reader cannot check, and six of them
had outlived their truth: this file said the reverse-discovery criteria were unticked for want
of code that had in fact shipped, directly above ten ticked ids (the sentence is not reproduced
here - `tools/narrated-claims.txt` holds it, and AC-VC-01 asserts it is gone from this file);
the diamond table's drift row wore a VISION chip over a caption that already said ADR-011
REJECTED it as architecture;
the CONSTITUTION promised risk profiles were "NOT yet" mechanized when the paragraph above says
they are design discipline BY DESIGN; `CROSS-PLATFORM.md` titled itself a roadmap six lines
above declaring the roadmap closed; the outer-loop slides carried a `proposal` badge after the
human deferred them on 2026-09-02; and `uscha top` fixture F3 read *planned* in a paragraph that
argued its own redundancy. Each was WIRED or REWRITTEN as the honest state, and the rewrite is
what is measured. Measured by T154 through the `.vc-cases.json` sidecar.

- [x] AC-VC-01 - every claim `tools/narrated-claims.txt` records as retired is **absent** from the file it was retired from, and every path the list names still exists (a row pointing at a deleted file would pass by accident, which is the failure mode the list exists to refuse). It is an ALLOWLIST, deliberately, not a ban on the word VISION: **ONE label is correct today** and survives untouched - the diamond table's "arbitrary systems" row, still VISION because the bounded half is measured and generalization is not. There were two until 1.99.0; the other was "cross-vendor is not yet measured", and ADR-042 retired it by MEASURING it rather than by rewriting it - entry 7 of the list records what happened to it, which is the outcome this whole doctrine is meant to produce. And the historical record - the per-release changelogs, `audits/`, `ISSUES-DEFERRED.md` as a mechanism name, the paper's Future Work, every code and CSS token - is out of scope by construction, because nothing outside the list is read. A gate that flags what is right teaches the reader to ignore it.
- [x] AC-VC-02 - repo rule 3, measured: for each ES/EN twin pair the list names, the two files are diffed against the base ref and the changed-line counts are **equal**. An edit that landed in one language and not the other is invisible until a reader who only speaks the other one finds it. No git, no base ref, or a shallow clone -> UNMEASURED, never a silent pass.

## The three 1.69.0 deferred LOWs, closed (1.98.0) - closes on green `AC-DE-nn` smoke assertions

`ISSUES-DEFERRED.md` records findings below the severity gate so the loop can converge without
chasing zero - it is not a graveyard. The three the 1.69.0 fresh review filed there share one
shape: the JSON stayed right and a HUMAN-facing surface lied. Each carries its assertion, and
each was verified RED against the 1.97.0 engine before the fix. A fresh review of the fix then
found the same bug in two NEIGHBOURS the report had not named, which is `AC-DE-04`: a one-off fix
at the site that was reported is how the second and third copies survive. Measured by T155
through the `.de-cases.json` sidecar.

- [x] AC-DE-01 - an observation whose statement carries an interior newline renders as **ONE** table row in the delta twin. A markdown row ends at a newline, so the old renderer split the observation across two physical lines and every column after the break landed in the wrong one. Counted as whole rows (six cells, seven pipes, closing with one) against the observation count, plus the statement present flattened. The JSON and the OBS id always survived; the twin is the artifact the HUMAN curates from, which is exactly why the rendered view is not cosmetic.
- [x] AC-DE-02 - `promote`'s `ISSUES-DEFERRED.md` dedupe matches the **work item**, not the text. An OBS id merely mentioned in prose in that file used to suppress its work item forever - a `fix` verdict that quietly produced nothing - and the anchored `- [ ] OBS-<id>` line form is what answers the actual question. Both halves measured: end to end, a prose mention no longer suppresses the item and a second `promote` still writes it only once; at the function level, `OBS-1` is not `OBS-10`, the boundary a raw substring over hash-prefix ids cannot express.
- [x] AC-DE-04 - the SAME cell writer is used everywhere a value reaches a one-line surface, not only at the site the review reported. Two neighbours carried the identical bug: `_render_ir_md` escaped a pipe and never touched a newline (both the node rows and the UNTYPED rows), and `promote` wrote the raw statement into a markdown **checklist item** - which ends at a newline exactly as a table row does, so a multi-line statement split the work item in two and left the half `_deferred_carries` recognises without its text. Measured on both: a synthetic IR graph with newlines in a node statement, an UNTYPED text and its reason renders one row each (the UNTYPED text is truncated AFTER flattening, so the cut cannot land mid-break), and a real `fix` verdict over a multi-line statement appends exactly one line with no stray remainder, still deduped on the second `promote`.
- [x] AC-DE-03 - `fidelity --config` resolves a relative default against the cwd **first, then beside the `--ledger`**, and the output NAMES the path it read - or names the absence and where it looked. Run from any directory but the project root, the old resolution silently found no config, so `defaults.fidelity.gate` was never declared and the INV-ADVISORY-01 refusal that reads it never fired: an unnamed absence indistinguishable from having no gate at all. Measured from a foreign cwd on all three arms - absence named, path named and reported in `--json`, and the advisory-as-blocking refusal firing with exit 2.

## Cross-vendor arm (ADR-042) - closes on green `AC-XV-nn` smoke assertions

Every blind compilation in the Diamond Bench came from ONE vendor until 1.99.0. Three models of
the Claude family converging on the same reading of a spec is weaker evidence than it looks if
they converge because they are relatives, and the repo said so on six pages: *cross-vendor not
yet measured*. This arm is the falsification test. It ran the same 12 archetypes through the
OpenAI Codex CLI (`gpt-5.5`) under ADR-017's protocol with the vendor swapped - 22 dispatches,
22 promoted, 0 refused, **0 shell commands executed** - and the claim survived: 8 PASS, 4 PARTIAL,
one verdict moved.

The one that moved is the finding. `transformer` went PASS -> PARTIAL on a single oracle case,
because the cross-vendor arm read *"an object with exactly the fields first/last/age"* as
forbidding an extra field, **declared that reading in its `unresolved_intent` before the oracle
judged it**, and reproduced it in a second independent run. The canonical package is genuinely
ambiguous there; three related models had resolved it identically, so the ambiguity was
invisible while every compiler came from one vendor. The controlled-language arm had found the
same sentence from the other direction in 1.83.

- [x] AC-XV-01 - all 12 `c-codex` compilations `compile-validate` exit 0 against their entry's
  pinned `IR.json`; each `unresolved_intent` is verbatim, non-empty and bounded (2-6 entries);
  the twelve are pairwise distinct; and **every `ir_region` names a real IR node**. That last
  clause is not cosmetic: `compile-ingest` content-addresses a UINT on `(ir_region + decision)`,
  so a compiler inventing its own region slugs would fork the UINT address space between arms
  permanently. Compliance was 48/48.
- [x] AC-XV-02 - no oracle reached the arm on either side of the dispatch. The INPUT half is
  proven by RE-DERIVATION rather than trust: `CODEX-ARM-RUN.json` carries a sha256 per prompt
  and no prompt bytes, and the block re-renders all twelve from the same slot table and the same
  canonical package and compares - a prompt that had ever carried an oracle value would have to
  carry it again to match. The OUTPUT half re-runs the dispatcher's own leak audit over all 22
  compiled sources. Storing the prompt bytes was rejected: a prompt is the canonical package
  plus the run contract, both already committed, and a second copy is how two copies start to
  differ.
- [x] AC-XV-03 - `bench` reports a `codex` compilation in all 12 entries; the anonymised model
  map is the pinned four-key `{codex: M1, haiku: M2, opus: M3, sonnet: M4}` (the letters MOVED -
  the map is built over sorted model names, so a silent re-lettering would make every published
  `M<n>` claim wrong); every entry's four compilations are all-distinct; and the per-entry codex
  counts and the twelve verdicts are pinned exactly as measured, including the two the arm WINS
  (`rest-handler` 15/15, `scheduler` 30/30) and the one it loses (`transformer` 13/14).
- [x] AC-XV-04 - a compilation that does not validate is a NAMED refusal. Measured on the real
  `validate_and_place` function against a temp target root with a real corrupted fixture (one
  source `sha256` rewritten), never by dispatching anything: the corrupted copy lands in
  `x-codex-REFUSED/`, names the exit code, writes `VALIDATE-STDERR.txt`, and leaves NO `c-codex/`
  for the bench's `c-*` discovery to find; the intact copy promotes cleanly. The committed run
  record agrees that nothing was refused for real (12 + 10 promoted, 0 refused).
- [x] AC-XV-05 - the arm has its own noise floor: `bench-r2` reports a float `intra_distance`
  for `c-codex` in each of the 10 entries that carry an `r2/`, every codex rerun is
  `behaviour_stable` and `run2_compile_valid`, and the per-entry classes are pinned with the two
  that moved recorded before and after (`parser` NOISE -> NOISY, `state-machine` NOISE -> NOISY).
  `ledger-lite` and `rate-limiter` still report `has_r2` false: they carry no second round for
  ANY compiler, and a codex-only one there would report one model's rerun against four models'
  spread under the same column as the ten - a different quantity printed as the same one.
- [x] AC-XV-06 - the backend is on the record inside every one of the 22 compilations:
  `vendor`, `cli`, `model_slug`, `reasoning_effort`, `sandbox`, `approval` and `write_mode`, with
  `shell_commands_executed == 0` and nothing read outside the workspace. The zero is the
  load-bearing one: it is what makes the `--write-mode return` deviation harmless to the
  comparison, because an arm that ran no command is not exercising a capability the Claude arms
  never had.
- [x] AC-XV-07 - the published claim says what the committed fixture backs and no more, in BOTH
  languages: six pages carry the measured statement (README, `site/llms.txt`, the diamond pair,
  the how pair), and the six retired phrases are registered in `tools/narrated-claims.txt` where
  `AC-VC-01` asserts their absence. Both halves are needed - a claim deleted from one page and
  rewritten on the other is exactly the drift repo rule 3 exists to catch. The paper is
  deliberately NOT in this list: its numbers are dated at 1.96.0 and it is revised in its own
  round, and asserting a phrase into a document nobody has rewritten yet is the same narrated
  claim pointed the other way.

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
- ADR-031 — `uscha top` is a raw-ANSI terminal projection of the ledger, wired like `mirador`.
- ADR-032 — One engine subcommand (`top --json`) computes the whole projection; the TUI renders.
- ADR-033 — The verdict is the only thing `uscha top` writes, and it writes it through the existing `curate`.
- ADR-034 — `render(state, size)` is pure; golden frames are its oracle, with a negative-honesty fixture.
- ADR-036 — The instrument reads family-prefixed criteria (`AC-<FAMILY>-<n>`); the bare form is unchanged.
- ADR-037 — `o` triggers the command the HUMAN supplied at launch, then the engine's own `snapshot` ingests; the TUI never decides what to run and never writes.
- ADR-038 — TERMINADO is sealed to the exact code state: reports are content-hashed at ingest, the seal is DERIVED at read time (never stored), and DONE does not render 100% while it is measured broken (INV-T1, INV-TOP-06).
- ADR-039 — Evidence freshness is decided by CONTENT and COMMIT, not by the clock alone: a report is current when no source changed since the run that produced it, whatever the mtimes say; and the seal tolerates commits that touch no source (amends ADR-038).
- ADR-041 — The dogfooding criterion is decided by git ANCESTRY, not by a wall clock — and the release ritual is a script that refuses (I1..I8), not prose a human re-reads.
- ADR-042 — The cross-vendor arm: a SECOND vendor compiles the whole bench, blind, under the same withheld oracles; `--write-mode return` because the machine's approval policy forbids exec writes, and 0 executed commands means the confound that mode would have introduced does not exist.

Each ADR carries its own checkable Verification block; the executable form of those checks is
the smoke suite (`uscha-kit/tests/smoke-engine.sh`), not `AC-nn` criteria here — a kit change
is accepted by a green smoke, which is how uscha verifies its own engine.
