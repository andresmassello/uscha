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
- [x] AC-BG-03 - all 15 new compilations `compile-validate` against their entry's pinned IR; no
  compiler input references any oracle; `unresolved_intent` is each model's verbatim return.
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
- [x] AC-SH-02 - the three blind `scheduler` compilations `compile-validate` against the pinned
  IR; each `unresolved_intent` is non-empty, bounded (2-5 entries), and model-distinct
  (verbatim, not synthesized); the bench verdict for `scheduler` is `PARTIAL` with the pinned
  per-compiler oracle counts (opus 30/30, sonnet 26/30, haiku 25/30 of 30); the bench now
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
  `{guard, rest-handler, scheduler}`.
- [x] AC-R2-02 - `bench-r2 --dir BENCH --json` reports, for every entry, `has_r2` true, a `class`
  in `{SIGNAL, NOISY, NOISE}` equal to the expected function of the ratio (`< 0.5` SIGNAL,
  `< 1.0` NOISY, else NOISE), float `intra_mean`/`inter`/`intra_over_inter`, and exactly 3 models
  each with a float `intra_distance` and a boolean `behaviour_stable`; an entry with its `r2/`
  removed reports `has_r2` false, `class` null, and a non-empty `reason` (absent, never 0); an
  entry whose `r2/` is present but holds no parseable source reports `has_r2` true, `class` null
  and a non-empty `reason` (the review-found silent gap, now named);
  `protocol-adapter`'s reported `inter` matches an independent recomputation of the mean pairwise
  `_struct_distance` over its three run-1 implementations to 4 decimal places.
- [x] AC-R2-03 - all 30 `r2/` `COMPILATION.json` files `compile-validate` exit 0 against their
  entry's `IR.json`; each `unresolved_intent` has 2-6 entries and the three per entry are
  pairwise distinct; the aggregate is pinned (`verdict` NOISY, signal 1, noisy 5, noise 4, stable
  26, reruns 30) and every per-entry class is pinned exactly: SIGNAL `protocol-adapter`; NOISY
  `crud-store`, `guard`, `rest-handler`, `transformer`, `ui-render`; NOISE `parser`, `scheduler`,
  `state-machine`, `worker`.

## Non-Python archetype (ADR-028) - the method leaves Python

- [x] AC-JS-01 - Python untouched: `bench --json` entries equal 12 and the eleven Python entries'
  verdicts equal the pins `{crud-store PASS, guard PARTIAL, ledger-lite PASS, parser PASS,
  protocol-adapter PASS, rest-handler PARTIAL, scheduler PARTIAL, state-machine PASS,
  transformer PASS, ui-render PASS, worker PASS}`; `bench-r2 --json` aggregate stays `verdict`
  NOISY, signal 1, noisy 5, noise 4, with 10 measured and both `rate-limiter` and `ledger-lite`
  `has_r2` false; `lang-compare` on scheduler-free vs scheduler-controlled stays `IMPROVED` with
  variance scores in their interpreter-stable ranges (free 0.015–0.03, controlled 0.17–0.20; the exact decimals move between 3.8 and 3.13 per ADR-027) (the refactor left Python metrics identical); `_impl_metrics` on
  a Python impl returns an `int` `ast_nodes`.
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
  rest-handler PARTIAL, scheduler PARTIAL, state-machine PASS, transformer PASS, ui-render PASS,
  worker PASS}`; `lang-compare` on scheduler-free vs scheduler-controlled stays `IMPROVED` with
  variance scores in their interpreter-stable ranges (free 0.015–0.03, controlled 0.17–0.20; the exact decimals move between 3.8 and 3.13 per ADR-027); `bench-r2 --json` aggregate stays `verdict` NOISY, signal 1,
  noisy 5, noise 4, with 10 measured; a single-unit compilation (`guard`, `c-opus`) still reports
  `entry_unit` `source/guard.py` and `units` 1.
- [x] AC-MU-02 - `ledger-lite`'s `IR.json` carries at least one `DECISION` node and at least 2
  edges (the bench's first IR with edges, extracted from `docs/adr/ADR-001-model-cli-seam.md`);
  each of the three blind `COMPILATION.json` files ships exactly 2 source units, `compile-validate`
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
  state-machine PASS, transformer PASS, ui-render PASS, worker PASS}` - this instrument changes
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
  `edges_recovered_mean == 1.00` (it was 0.33 while static footing was the only one that
  anchored anything).
- [x] AC-RT-03 - the aggregate is pinned to today's measured state: 12 entries measured, mean
  `recoverability` in `[0.82, 0.83]`, 1 entry with edges, behaviour measured in 12 of 12
  entries, and `behaviour` an integer in every compilation of every entry; the per-entry
  `recoverability_mean` is pinned exactly: `crud-store 0.857, guard 0.875, ledger-lite 0.704,
  parser 0.714, protocol-adapter 0.714, rate-limiter 0.762, rest-handler 0.905, scheduler 0.875,
  state-machine 0.857, transformer 0.905, ui-render 0.905, worker 0.857`; the instrument is
  id-regex + file reads + oracle runs with no AST involved, so a second Python interpreter (3.8)
  reproduces the per-entry means EXACTLY - measured, not assumed. The aggregate is pinned as a
  RANGE and never as a float: the twelve means sum to 9.930 and `9.930 / 12` is 0.8275 exactly,
  a rounding boundary that lands on 0.828 under 3.13 and 0.827 under 3.8, so the cross-interpreter
  expectation is "within one thousandth", compared in integer thousandths.
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

- [x] AC-DF-01 - the root `QA-LEDGER.json` is re-recorded in or after the last engine change: the commit that last touched `qa_ledger.py` also carries the ledger, or `readiness_history[-1].at` is newer than that commit; no git = UNMEASURED, stale = RED.

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

Each ADR carries its own checkable Verification block; the executable form of those checks is
the smoke suite (`uscha-kit/tests/smoke-engine.sh`), not `AC-nn` criteria here — a kit change
is accepted by a green smoke, which is how uscha verifies its own engine.
