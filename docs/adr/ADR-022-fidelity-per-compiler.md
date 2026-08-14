---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
---
# ADR-022: The per-compiler fidelity descriptor — the M1 reverse-discovery organ applied to each compiled artifact, advisory by construction, with the unmeasurable named UNMEASURED (fidelity-per-compiler v0.1)

## Status: Accepted

## Context
The last deferred arm of the M4/M5 protocol: reverse-discover each compiled implementation and
compute a per-compiler fidelity vector. M4 and M5 deferred it honestly — "it enriches the
descriptor without changing a verdict, and is wired only if a verdict actually turns on it" —
and no verdict ever did: the withheld oracle settles behavioural identity, variance settles
structural difference. So the honest scope for v0.1 is an **enrichment, stated as such**:
apply the M1 machinery mechanically to each compiled artifact and publish what it can measure,
naming what it cannot.

**What transfers from the M1 fidelity vector to a single-file blind compilation, and what does
not:**
- `traceability` transfers → here it is the trace-manifest **coverage share** (IR nodes the
  compilation claims, over all IR nodes) — already validated by `compile-validate`, now surfaced.
- `contracts` transfers → the M1 **static extractor** (`_extract_static_py`, AST-deterministic)
  run over the compiled source yields its **public surface** (functions/classes) — the
  reverse-discovered "what this artifact exposes", comparable across compilers of one entry.
- `behavior` transfers → the oracle pass-rate, already measured per compilation.
- `curation_closure` does **not** transfer: curation requires a human `preserve|fix|undefined`
  verdict per observation (INV-CURATION-01), and no human curates machine-generated fixture
  code. It is reported **UNMEASURED — absence named, never faked** (the house rule).
- `unexplained_code` is degenerate here by construction (single-unit manifests cover the unit);
  reported as the measured 0/1 share, not omitted.

## Decision
- **`bench --fidelity`**: an opt-in flag on the existing `bench` subcommand (no new subcommand;
  the descriptor is an enrichment of the bench, not a new instrument). For every compilation of
  every entry it computes a **per-compiler fidelity descriptor**:
  `{trace_coverage, static_surface: {functions, classes, names}, oracle_passrate,
  unexplained_share, curation_closure: "UNMEASURED"}` — `static_surface` produced by the M1
  static extractor over the compiled source (the reverse-discovery organ, reused unchanged in
  spirit: deterministic AST, public names only).
- The descriptor lands in the `--json` raw output and as a per-entry appendix section in
  `DIAMOND-BENCH.md`. **Advisory by construction: it never contributes to a verdict** — the
  verdict logic is untouched, and the flag defaults off so every existing caller is unchanged.
- **What the descriptor is for** (stated so the enrichment is not over-read): comparing the
  *reverse-discovered surface* of three compilers of one entry shows *how differently shaped*
  behaviourally-identical implementations are — the diamond loop (forward compile, reverse
  discover) closed over machine-generated code, mechanically, per compiler.

## Reasons
- This completes the deferred protocol arm at the fidelity it can honestly support, instead of
  inflating a vector whose heaviest dimension (human curation) cannot exist for fixture code.
- Reusing the M1 extractor keeps the claim true: it IS reverse discovery applied per compiler —
  not a new metric wearing its name.

## Consequences
+ The chain's last deferred item closes; the bench's raw data becomes a complete per-compiler
  record (behaviour, structure, surface, traceability).
- The descriptor invites over-reading; the UNMEASURED field and the advisory framing are the
  guard, and the changelog states the scope.

## Verification
- [ ] `bench --fidelity` emits the descriptor for every compilation of every entry; without the
  flag, output is byte-identical to before (AC-FC-01)
- [ ] `static_surface` comes from the M1 static extractor over the compiled source and is
  deterministic across runs; `trace_coverage` and `oracle_passrate` match the bench's own
  numbers (AC-FC-02)
- [ ] `curation_closure` is the literal string UNMEASURED — absence named, never a fabricated
  number; the descriptor never changes any verdict (AC-FC-03)
