# uscha-kit 1.79.0 — fidelity per compiler: reverse discovery applied to each compiled artifact (2026-08-13)

ADR-022 closes the last deferred arm of the M4/M5 protocol — the per-compiler fidelity
descriptor — at the fidelity it can honestly support. No verdict ever turned on it (the
withheld oracle settles behavioural identity; variance settles structural difference), so it
ships as what it is: an **enrichment, advisory by construction**.

## `bench --fidelity`

An opt-in flag (no new subcommand; 48 stays 48). For every compilation of every entry it emits
a per-compiler descriptor:

- `static_surface` — the **M1 static extractor** (`_extract_static_py`, deterministic AST, the
  reverse-discovery organ, reused) run over the compiled source: the artifact's public
  functions/classes, by name. The reverse-discovered "what this artifact exposes."
- `trace_coverage` — the share of IR nodes the compilation's manifest claims (already validated
  by `compile-validate`, now surfaced).
- `oracle_passrate` — behavioural identity, already measured, now in the descriptor.
- `unexplained_share` — units without a manifest entry (degenerate on single-unit fixtures,
  reported rather than omitted).
- `curation_closure` — the literal **UNMEASURED**: curation requires a human verdict per
  observation (INV-CURATION-01) and no human curates machine-generated fixture code. Absence
  named, never faked.

Without the flag, `bench` output is byte-identical to before; with it, the descriptor lands in
the raw JSON and as per-entry appendix lines in `DIAMOND-BENCH.md` (regenerated, enriched). It
never contributes to a verdict — regression-tested (`AC-FC-03`: verdicts identical with and
without the flag).

What it shows, on the committed bench: behaviourally near-identical compilers expose visibly
different reverse-discovered surfaces — the guard's three implementations score 19–21/23 on the
same oracle through 5, 4 and 8 public functions respectively. The diamond loop — forward
compile, reverse discover — closed over machine-generated code, per compiler, mechanically.

## What the review caught

The blind review found no CRITICAL or HIGH defect — it hand-verified the descriptor against
direct AST parses (exact name matches on all three guard implementations), confirmed byte-
identity of the no-flag output against the pre-change engine (stronger than the suite's own
check), and confirmed no verdict leak both by reading the logic and by the AC-FC-03 regression.
Three smaller findings, addressed: (1) MEDIUM — ADR-022 claimed AC-FC-02 asserts
`trace_coverage`, but the test only asserted `oracle_passrate`; fixed by **strengthening the
test** (the smoke now recomputes trace coverage independently from IR + manifest per
compilation) rather than weakening the ADR. (2) LOW-MEDIUM — the determinism re-run is
acknowledged as weak evidence (every descriptor field is a count, rounded float, or sorted
list; the re-run mainly proves stability over a fresh copy) — noted, not oversold. (3) LOW —
a redundant COMPILATION.json re-parse inside the fidelity block; cosmetic, left. The review
also noted the "diamond loop closed" phrasing does more rhetorical work than a 5-field
descriptor strictly earns — fair; read it with the ADR's own scoping (curation does not
transfer; UNMEASURED is named).

`AC-FC-01..03` measured green (T128 extended). Suite: 415 checks; acceptance **122/122** where
`coverage.py` is installed. With this, the "hacer 1, 2, 3" chain closes: bench growth (1.77.0),
controlled-language v0.2 (1.78.0), fidelity per compiler (1.79.0).
