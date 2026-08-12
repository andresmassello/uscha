---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
---
# ADR-016: The LLM is a compiler with a validated output contract; the engine validates and ingests compilations but never compiles, and only mechanical violations gate (Compiler Contract v0.1)

## Status: Accepted

## Context
Diamond M3. M2 turned the forward canonical package into a typed, sealed graph (Uscha IR
v0.1, ADR-015). M3 asks the operational question the whole program rests on: can "LLM as
compiler" be made into a *contract* — an invocation fully specified by its inputs, whose
outputs make both directions of the intent ledger measurable **by construction** rather than
by after-the-fact heuristics?

**Falsifiable thesis:** a compliant invocation is fully specified by
`compile(canonical_ir, target_stack, implementation_constraints)`, and its outputs
(`trace_manifest`, `unresolved_intent`) close both ledger metrics by construction. **It fails
if** real compilations cannot honestly produce the manifests — the sharp failure being a
`trace_manifest` that degenerates into "everything traces to everything", or an
`unresolved_intent` that is empty (the compiler pretended it had no choices) or generic (it
listed non-answers). Those failures are **detectable** — fan-out statistics and specificity
are mechanical — and detection is part of the contract, not a hope.

The two metrics this milestone closes are the polished faces of the Diamond page:
- `unexplained_code` — code with no traceable intent (*the past lies to you*). Measured
  backward since M1 (ADR-014); made **by-construction** for new code here via `trace_manifest`.
- `unresolved_intent` — intent with insufficient determination (*the future diverges on you*).
  New in M3; every entry is a candidate canonical improvement, so the compiler's own output
  **generates the backlog** for the representation.

Two lines have to be drawn, and drawing them wrong would betray the doctrine:

**Line 1 — who compiles.** Options:
- **A) The engine drives the compilation** (calls a model, writes the source). Rejected: it
  violates ADR-011/013's spine — *the engine classifies and stores, it never calls an LLM*.
  An engine that compiles is a maker; the whole program needs the engine to be the
  **checker**, physically distinct from the maker (the maker≠checker rule M4 depends on).
- **B) The model (skill/raw/any backend) produces a compilation output; the engine validates
  and ingests it, and never compiles.** **Chosen.** The compilation output is a machine
  representation *derived by the compiler* — exactly like discovery's `narrated` OBS, which
  the skill supplies and the engine classifies and stores (ADR-013). "Models become
  interchangeable backends" is only true if the engine's side of the contract is model-blind:
  it reads a JSON and the real files on disk, and judges them by mechanism alone.

**Line 2 — what may gate.** The handoff is explicit: *degenerate-manifest detector (advisory
stats, blocking only on mechanical violations like unknown IR IDs)*. Options:
- **A) Degeneracy blocks.** Rejected: "everything traces to everything" is a *statistical
  smell*, and a threshold on a smell is a judgment. The standing rejection is absolute — no
  LLM-class judgment, and no statistic standing in for one, ever gates (INV-ADVISORY-01,
  ADR-014). A degeneracy threshold that blocks would be the first crack in that wall.
- **B) Only deterministic, mechanical violations gate; every statistic is advisory.**
  **Chosen.** Unknown IR node ID, malformed shape, an IR hash that names an IR this repo
  cannot reproduce, a manifest unit that does not exist on disk, a source/test hash that does
  not match the file — these are *facts*, and facts block. Fan-out degeneracy, an empty
  `unresolved_intent`, low specificity — these are *advice*, printed and carried, never
  fatal. Facts block; guesses advise, applied to compilation.

## Decision

**The compiler produces `compilations/<id>/COMPILATION.json`** conforming to
`compile/0.1` — machine-canonical, produced by the backend (any model), never authored by the
engine, sealed with the IR's `_integrity_hash` machinery:

```
compile(canonical_ir, target_stack, implementation_constraints)
→ {
    schema_version: "compile/0.1",
    canonical_ir:  { ir_hash, schema_version },   # WHICH IR was compiled (its M2 seal)
    target_stack, implementation_constraints,      # inputs, echoed
    source: [ { unit, sha256 } ],                  # real files on disk
    tests:  [ { unit, sha256 } ],
    trace_manifest:     [ { unit, implements: [ IR node id, ... ] } ],
    unresolved_intent:  [ { id, ir_region, decision, rationale } ],
    compilation_report: { stack, model, model_version, timestamps, constraint_handling },
    _integrity: <seal>
  }
```

- **`compile-validate` is a deterministic, read-only checker (exit 2 on any mechanical
  violation, like `_load_ir`).** It BLOCKS on, and only on, facts:
  1. unknown `schema_version` → refused, never mis-read;
  2. missing/mistyped required section;
  3. `canonical_ir.ir_hash` does not equal the seal of an IR this repo reproduces via
     `ir-extract` — a compilation against an unknown or stale IR is refused (it cannot be
     measured against a graph that is not there);
  4. a `trace_manifest[].implements` ID that is not a node in that IR — **the named mechanical
     violation**;
  5. a `trace_manifest[].unit`, `source[].unit` or `tests[].unit` whose file is absent, or
     whose `sha256` does not match the bytes on disk — the manifest cannot lie about what was
     compiled. **A unit path must be relative and contained within the compilation directory**
     (`realpath`-checked both sides — the repo's Windows 8.3 trap); an absolute path or a `..`
     escape is refused, so a manifest cannot name an out-of-tree file and pass on its hash;
  6. an `unresolved_intent[]` entry missing `ir_region` or `decision` (shape only);
  7. a malformed *element* — a `source`/`tests`/`trace_manifest`/`unresolved_intent` entry that
     is not an object, or an `implements` that is not a list. Adversarial or buggy compiler
     output is a named mechanical refusal (exit 2), **never an uncaught traceback** — the trust
     boundary the contract exists to defend.
- **The degenerate-manifest detector is ADVISORY.** `compile-validate` computes and prints
  fan-out statistics — nodes-per-unit and units-per-node (mean/max), the share of nodes
  covered, and `unresolved_intent` count/specificity — and flags `degenerate: advisory` when
  the manifest approaches everything→everything or `unresolved_intent` is empty. **These never
  change the exit code.** A degenerate but mechanically valid compilation validates, loudly.
- **`compile-ingest` records a validated compilation into the ledger, append-only.** It
  re-runs the full validation (ingesting an unvalidated compilation is refused), then:
  - folds `trace_manifest` into a **by-construction `unexplained_code`** for the compilation —
    every `source`/`tests` unit with no manifest entry is unexplained, named, counted; this is
    the *forward* face ADR-014 measured only backward;
  - writes each `unresolved_intent` entry as an append-only ledger object with a
    content-addressed id (`UINT-` + `sha256(ir_region + "\n" + decision)[:12]`, the OBS
    scheme), and mirrors it as a work item in `ISSUES-DEFERRED.md` — **the same house
    convention `fix` verdicts use (ADR-013): no new tracker, no unrequested remote issues.**
    The backlog for the representation is a real, reviewable file. Two entries that resolve to
    the same id are the same intent gap and dedupe within one ingest, not just across ingests.
  - Idempotency is **per repo**: the seal is the identity within a repo, so the supersede
    check is scoped by repo. The `compilations` ledger is flat and cross-repo; two repos that
    legitimately produce the same compilation (a shared, small canonical package) are each
    recorded — a byte-identical re-ingest into the *same* repo supersedes nothing.
- **Promotion closes the loop.** An `unresolved_intent` entry is *promoted* when the human
  turns it into a canonical improvement (a new AC, an ADR note, an authoring convention that
  would have removed the compiler's freedom). Promotion is a human canonical edit with
  recorded lineage back to the `UINT-` id — the engine measures that the backlog exists and
  shrinks; it never authors the canonical fix.
- **Two reference compilations, two models, one small canonical package.** A tiny committed
  canonical package (Markdown ACs + INV, purpose-built and public) is `ir-extract`ed
  deterministically into the reference IR. Two independent models compile it through the
  contract; **both COMPILATION.json fixtures are committed and both must pass `compile-validate`
  in the smoke suite.** That two different backends produce conformant, independently-validating
  output *is* the "interchangeable backends" claim, proven mechanically. The real
  Uscha-on-Uscha bootstrap is M4's job, deliberately not pulled forward.
- **The schema is versioned and expected to change.** `compile/0.1` is mandatory; M4's S-gap
  findings will rewrite it. A validator that meets an unknown version says so (exit 2), never
  guesses.

## Reasons
- Putting the compilation behind a *validated output contract* is what makes "LLM as compiler"
  an engineering claim instead of a slogan: the invocation is specified by its inputs and the
  output is judged by mechanism, so swapping the model is swapping a backend.
- The maker≠checker split (engine never compiles, only validates) is not a nicety — M4's
  bootstrap requires an oracle physically distinct from the compilers. Building the wall now,
  in M3, is what makes M4 honest later.
- By-construction `unexplained_code` and `unresolved_intent` convert both ledger faces from
  after-the-fact heuristics into properties the compiler *must* declare — and a declaration is
  checkable in a way an inference is not.
- Blocking only on facts keeps the doctrine intact under the exact pressure M3 invites: it is
  tempting to gate on degeneracy because degeneracy is bad, but a threshold on a statistic is
  the camel's nose. Advisory-forever for every non-fact is the same wall ADR-014 built.

## Consequences
+ The compiler output is M4's compilation format; M3 specifies the contract, M4 stresses it
  with ≥3 models on real Uscha code.
+ `unresolved_intent` makes the representation *self-improving*: the compiler's own admissions
  of freedom become the prioritized backlog of what to author next.
- A mechanically-valid compilation can still be semantically poor (degenerate manifest,
  hand-wavy `unresolved_intent`). Stated plainly: `compile-validate` green means *conformant*,
  not *good*; the advisory stats are where "good" is argued, and they never gate.
- v0.1 is deliberately minimal and WILL be rewritten by M4. Said now, with the schema version
  and the exit-2-on-unknown posture that makes the rewrite cheap.
- Two reference models cost two real compilations. Accepted: a contract nobody has run twice,
  with two backends, is an unfalsified contract.

## Implementation Plan
- Engine: `compile-validate` (read-only, exit 2 on mechanical violation; advisory degeneracy
  stats in output/`--json`) and `compile-ingest` (validate → by-construction unexplained_code
  → append-only `UINT-` ledger objects + `ISSUES-DEFERRED.md` mirror). Reuse `_integrity_hash`,
  the `_load_ir`/`_ir_seal` seal machinery, `_obs_id`-style content addressing, the
  `ISSUES-DEFERRED` writer from `cmd_promote`, and `ir-extract` to reproduce the target IR's
  hash. The engine calls no model, ever.
- Fixtures: a small committed canonical package under
  `uscha-kit/tests/fixtures/compile-ref/` (Markdown ACCEPTANCE + CONSTITUTION), plus two
  committed `COMPILATION.json` produced by two different models (proposed: Opus 4.8 and Sonnet
  via an independent subagent — an honest maker≠maker split; final pairing is a human call).
- Tests: smoke T126, criteria `AC-CC-01..07`; both reference compilations validated in the
  suite, one degenerate fixture proving the detector fires **advisory** without changing the
  exit code, one unknown-IR-ID fixture proving the mechanical block.
- Docs: this ADR, ACCEPTANCE `AC-CC-*`, CHANGELOG, SYSTEM-FACTS (subcommand count 42→44).
  Site/README stay VISION for everything past M1 until M4/M5 (T0 enforces the label).

## Verification
- [ ] a well-formed compilation over the reference IR passes `compile-validate`; every manifest
  ID resolves, every unit hash matches disk (AC-CC-01)
- [ ] the manifest cannot lie: a `trace_manifest` ID that is not an IR node → exit 2 naming the
  unknown ID; a unit whose file/hash does not match disk → exit 2 naming the unit; a
  hand-edited seal → exit 2 (AC-CC-02)
- [ ] a `canonical_ir.ir_hash` that this repo cannot reproduce via `ir-extract` → exit 2; a
  compilation never validates against an absent or stale IR (AC-CC-03)
- [ ] a degenerate manifest (everything→everything) and an empty `unresolved_intent` are flagged
  `advisory` and printed, and `compile-validate` still exits 0 — statistics never gate (AC-CC-04)
- [ ] `compile-ingest` records each `unresolved_intent` as an append-only `UINT-` object with a
  content-addressed id and an `ISSUES-DEFERRED.md` mirror; re-ingest supersedes, never
  duplicates (AC-CC-05)
- [ ] by-construction `unexplained_code`: a `source` unit absent from `trace_manifest` is named
  and counted in the compilation's ingest record (AC-CC-06)
- [ ] two reference compilations from two different models both pass `compile-validate`; the
  contract is backend-blind (AC-CC-07)
