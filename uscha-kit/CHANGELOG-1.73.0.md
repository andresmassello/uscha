# uscha-kit 1.73.0 — Diamond M3: the LLM is a compiler with a validated output contract (2026-08-12)

M3 of the Diamond program. M2 turned the forward canonical package into a typed, sealed graph
(the IR). M3 asks the operational question the whole program rests on: can "LLM as compiler"
be made into a **contract** — an invocation fully specified by its inputs, whose outputs make
both directions of the intent ledger measurable *by construction*? The falsifiable thesis:
`compile(canonical_ir, target_stack, constraints)` is fully specified, and its
`trace_manifest` + `unresolved_intent` close `unexplained_code` and `unresolved_intent` by
construction. **It fails if** real compilations cannot honestly produce the manifests — the
sharp failure being a manifest that degenerates into "everything traces to everything".

Two lines are drawn, and drawing either wrong would betray the doctrine:

- **The engine never compiles.** The model (any backend) produces a `COMPILATION.json`; the
  engine validates and ingests it and never calls an LLM — exactly as discovery's `narrated`
  observations are produced by the skill and only classified by the engine. "Models become
  interchangeable backends" is only true because the engine's side of the contract is
  model-blind: it reads a JSON and the real files on disk, and judges them by mechanism alone.
  This also builds the maker≠checker wall that M4's bootstrap requires.
- **Only mechanical violations gate.** Unknown IR node id, malformed shape, an `ir_hash` this
  repo cannot reproduce, a manifest unit absent from disk, a source/test hash that does not
  match the bytes, a hand-edited seal — these are facts, and facts block. Fan-out degeneracy,
  an empty `unresolved_intent`, low coverage — these are advice, printed and carried, never
  fatal. A threshold on a smell would be a judgment, and no judgment gates (INV-ADVISORY-01).

## `compile-validate` — subcommand 43

```bash
python qa_ledger.py compile-validate --ir <IR.json> --compilation <COMPILATION.json>
```

Deterministic, read-only (`exit 2` on any mechanical violation, like the IR loader). Prints
advisory fan-out statistics — nodes-per-unit, coverage, `unresolved_intent` count, and a
`degenerate` flag when ≥2 source units each claim ≥80% of all nodes — and **these never change
the exit code.** A degenerate but mechanically valid compilation validates, loudly.

## `compile-ingest` — subcommand 44

Records a validated compilation into the ledger, append-only. It folds `trace_manifest` into a
**by-construction `unexplained_code`** (every source/test unit with no manifest entry is
unexplained, named, counted — the forward face measured only backward until now), and writes
each `unresolved_intent` entry as a content-addressed `UINT-` object mirrored into
`ISSUES-DEFERRED.md`, the house convention `fix` verdicts already use. The compiler's own
admissions of freedom become the prioritized backlog of what to author next. Re-ingest is
idempotent: the seal is the identity, a byte-identical compilation supersedes nothing, a
changed one reseals into a new record — never a duplicate.

## Two reference compilations, two models, one contract

A tiny public canonical package (a temperature converter: 4 ACs + 1 invariant) is
`ir-extract`ed into the reference IR (5 nodes, UNTYPED 0.00). Two independent models —
Opus 4.8 and Sonnet — compiled it through the contract; both `COMPILATION.json` fixtures are
committed and both pass `compile-validate`. That two different backends produce conformant,
independently-validating output *is* the "interchangeable backends" claim, proven
mechanically. Each model's `unresolved_intent` list is non-empty and specific (bool handling,
return-type precision, symmetric validation, module naming) — the underdetermination is real
and now first-class. The real Uscha-on-Uscha bootstrap is M4's job, deliberately not pulled
forward. The schema is versioned (`compile/0.1`) and expected to be rewritten by M4; an unknown
version refuses (`exit 2`) rather than mis-reading it.

## What the fresh review caught

Two blind adversarial judges, each reproducing against the live CLI. Seven real findings, all
fixed before shipping (reproduced first, then patched, each with a regression in T126):

- **CRITICAL — cross-repo seal collision.** `compile-ingest`'s idempotency check compared the
  compilation seal across a *flat, cross-repo* ledger list without scoping by repo. Two repos
  producing the same compilation (a shared small canonical package — this milestone's own
  fixtures) collided: the second repo's *first* ingest was dropped as a false "superseded" and
  reported success. Now scoped per repo.
- **CRITICAL — malformed element crashed instead of refusing.** `_validate_compilation`
  type-checked that `source`/`tests`/`trace_manifest`/`unresolved_intent` were lists but not
  that their *elements* were objects; a compiler emitting `source: ["x.py"]` raised an
  `AttributeError` traceback (exit 1) instead of a clean mechanical refusal (exit 2) — a break
  in the exact trust boundary the contract defends. Element shapes are now validated.
- **HIGH — unit path traversal.** A `unit` could be absolute or `../`-escape the compilation
  directory and validate on the hash of an out-of-tree file, defeating "the manifest cannot lie
  about what was compiled." Units are now required relative and contained (`realpath` both
  sides — the same Windows 8.3 trap this repo already paid for).
- **MEDIUM — duplicate `unresolved_intent` within one ingest** wrote the same `UINT-` line
  twice; dedup only checked prior file content, not the current batch. Now deduped within the
  ingest too.
- **MEDIUM — the (advisory) degeneracy detector was gameable** by listing a source unit under
  `tests` as well; source classification is now sticky, so the detector stays honest. Advisory
  either way — it never gated.
- **CRITICAL hygiene — the two engine mirrors diverged mid-review**; re-synced, and the suite's
  existing byte-identity gate (AC-01) guards it.
- **LOW — nothing regenerated the reference `IR.json` from `canonical/`;** T126 now `ir-extract`s
  it and asserts a byte-identical graph, so fixture drift cannot go silent.

One finding was consciously *not* changed: an empty compilation (`source: []`) validates with
`node_coverage: 0.0` reported advisory-only — consistent with "coverage never gates"; forcing
non-empty would be a policy gate on a statistic, which the doctrine forbids.

`AC-CC-01..07` measured green (T126). Suite: 412 checks; acceptance **92/92** where
`coverage.py` is installed.
