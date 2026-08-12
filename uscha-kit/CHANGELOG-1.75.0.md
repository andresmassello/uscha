# uscha-kit 1.75.0 — Diamond M5: the Diamond Bench, regeneration fidelity across archetypes (2026-08-12)

M5 of the Diamond program, the publishable result. M4 proved implementation replaceability for
**one** subsystem (`PARTIAL`, boundary drawn). M5 asks whether it **generalizes across
archetypes** — and, for three of four, it does.

## The bench

`qa_ledger.py bench` (subcommand 47) is the Diamond Bench: a deterministic orchestrator that,
over a set of bounded systems, aggregates the M3/M4 organs unchanged — `compile-validate`,
`bootstrap-oracle`, `bootstrap-variance` — and emits a **per-archetype verdict table** into
`DIAMOND-BENCH.md`. It measures **regeneration fidelity of canonical representations**, not
"which model codes better": model identities are **anonymized in the headline** (M1/M2/M3), the
mapping published beside it. Two lessons from M4 are baked in as gates, not conventions:
- **the oracle must discriminate** — a committed degenerate stub is run against every entry, and
  a `PASS`/`PARTIAL` over an oracle a stub can satisfy is downgraded to `FAIL`;
- **variance must show genuine difference** — a `PASS` requires ≥3 oracle-green compilations
  **and** no byte-identical pair; a near-identical convergence is `FAIL` (a disguised
  implementation, not a canonical package).

An entry not yet compiled is `PENDING`, counted, never silently dropped — the bench reports
honestly on a partial set.

## The result: 3 PASS, 1 PARTIAL

Four archetypes, each compiled **blind** by three independent models (Opus, Sonnet, Haiku)
through the M3 contract, each judged by a **withheld** oracle authored before any compilation:

| Archetype | Verdict | Compilers (oracle pass / total) |
|-----------|---------|---------------------------------|
| guard (validator) | PARTIAL | 19/23, 21/23, 21/23 |
| parser (pure function) | **PASS** | 17/17, 17/17, 17/17 |
| state-machine (stateful reducer) | **PASS** | 12/12, 12/12, 12/12 |
| transformer (data migration) | **PASS** | 11/11, 11/11, 11/11 |

For the parser, the state machine, and the transformer, **three substantially different
implementations behave identically on every oracle case** — that is *three substantially
different implementations, mechanically shown to be the same system*, the sentence M5 was built
to test, and it holds across three unlike archetypes. Every oracle discriminates (the degenerate
stubs score 1–11 of their cases, never green), so the identity is earned, not trivial. The guard
is the honest boundary M4 already drew (interpreter-inline-code handling), carried into the bench
as `PARTIAL`.

This is the program-level thesis answered with evidence, and answered **positively** for this
slice: implementation replaceability generalizes across the three non-validator archetypes
tested; the one boundary is drawn and named. The bench is v0.1 — four entries and the harness to
grow to the full 8–12 — but the four rows are real, measured, and reproducible
(`bash uscha-kit/tests/smoke-engine.sh`, T128).

## What the review caught

As in 1.74.0, the adversarial pass was an inline self-review (independent blind judges were held
back to conserve capacity after the eleven blind compilations this milestone ran) — stated
plainly, not the usual independent one. It reproduced: every number in `DIAMOND-BENCH.md` and the
table above matches a fresh `bench` run (guard 19/21/21 PARTIAL; parser/state-machine/transformer
17/12/11 all-green PASS; all entries `all_distinct`); the extended oracle runner did not regress
M4 — the guard's exit-only oracle is still 23/23; every entry's oracle discriminates not only
against a trivial stub (1–11 of cases) but against a *plausible-but-wrong* implementation — an
`eval`-based parser (floor division, over-permissive) scores 14/17 and is correctly **not**
green, so a `PASS` is earned behaviour, not an easy oracle; and `facts --check` is clean (no
truth-pass drift). No defect surfaced. An independent blind review of the bench remains worth
running when capacity is comfortable.

`AC-DB-01..06` measured green (T128). Suite: 414 checks; acceptance **104/104** where
`coverage.py` is installed.
