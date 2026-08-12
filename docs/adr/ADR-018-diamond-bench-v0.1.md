---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
---
# ADR-018: The Diamond Bench measures regeneration fidelity across archetypes; v0.1 seeds it with four bounded systems and the harness to grow it, model identities anonymized in the headline (Diamond M5 v0.1)

## Status: Accepted

## Context
Diamond M5, the program's publishable result. M4 proved, for **one** subsystem (the INV-GOLDEN
guard), that three substantially different implementations behave identically on the core —
`PARTIAL`, boundary drawn. M5 asks whether that **generalizes across archetypes**.

**Falsifiable thesis (program level):** implementation replaceability generalizes — across
system archetypes, the same canonical package compiled by independent models yields
substantially different implementations that a **withheld oracle** certifies as the same
system. **It fails if** the result does not generalize past certain archetypes — in which case
the bench produces the **map of where the thesis holds**, which is itself the honest,
defensible, publishable result. Both outcomes are program successes.

**Scope decision (human): a bounded v0.1.** The full handoff bench is 8–12 systems × ≥3 models.
v0.1 builds the **bench harness** and seeds it with **four** entries — enough for a real
per-archetype verdict table, small enough to run under realistic capacity — and defines exactly
how the bench grows to the full set. Under-claim, then wire.

Options considered for shape:
- **A) Full 8–12 archetypes now.** Rejected for v0.1: 24–36 blind compilations is a capacity and
  session risk that trades a real, shippable instrument for a half-finished one. The bench is a
  thing you grow, not a thing you land in one commit.
- **B) Harness + one ingested M4 entry only.** Rejected: a one-row table says nothing about
  *generalization*, which is the entire M5 question.
- **C) Harness + four diverse entries, growable.** **Chosen.** The guard (from M4, already
  measured) plus three new archetypes deliberately unlike each other and unlike a validator.

## Decision

**A bench entry is a bounded system compiled and judged by the M3/M4 machinery, unchanged.**
Each entry is a directory under `uscha-kit/tests/fixtures/diamond-bench/<entry>/` with:
- `canonical/` — SPEC + ACCEPTANCE (`AC-<NS>-nn`) + CONSTITUTION, the only compiler input;
- `IR.json` — the pinned IR (`ir-extract` over `canonical/`);
- `oracle/ORACLE.json` — the **withheld** behavioural suite, authored **before** any
  compilation, **never** shown to a compiler, and **discriminating** (it must reject degenerate
  implementations — the M4 lesson, now a bench invariant: an oracle that a trivial stub can
  satisfy proves nothing);
- `c-<model>/` — ≥3 blind compilations (`COMPILATION.json` + `source/`), each `compile-validate`
  against the pinned IR.

**v0.1 entries (4), each a distinct archetype:**
1. `guard` — the INV-GOLDEN PreToolUse guard (**ingested from M4**; already measured `PARTIAL`).
   Archetype: **validator / decision function.**
2. `parser` — a pure expression evaluator (a small arithmetic or config grammar; input string →
   value or a typed error). Archetype: **parser / pure function.**
3. `state-machine` — a small protocol/state machine (a sequence of events → resulting state and
   emitted outputs; illegal transitions rejected). Archetype: **stateful reducer.**
4. `transformer` — a data-shape transformer (records in one shape → records in another, with a
   declared mapping and validation). Archetype: **data migration / ETL-lite.**

**The new organ — `qa_ledger.py bench`** (subcommand 47). Deterministic, no LLM. Given the
bench directory, for **each entry** it runs the M3/M4 primitives already shipped —
`compile-validate` (every compilation against the entry's pinned IR), `bootstrap-oracle` (every
compilation against the entry's withheld oracle), `bootstrap-variance` (across the entry's
compilations) — and computes a **per-entry verdict**:
- **PASS** — every one of the ≥3 compilations is oracle-green **and** variance shows the
  implementations genuinely differ (no byte-identical pair). Three different implementations,
  mechanically the same system: the sentence that is the paper.
- **PARTIAL** — functional identity on the core (a documented majority of cases) with the
  divergence isolated and named; implementations genuinely differ.
- **FAIL** — no compilation is oracle-green, **or** they pass only by converging on
  near-identical code (variance below a floor — a disguised implementation, not a canonical
  package).

`bench` emits a **per-archetype verdict table** and writes `DIAMOND-BENCH.md`. **Model identities
are anonymized in the headline table** (`M1/M2/M3`, stable per run) so the bench reads as what it
is — *regeneration fidelity of canonical representations*, not "which LLM codes better"; the
identity mapping stays in the raw per-entry data, never hidden, just not the headline.

**Fidelity, honestly scoped (unchanged from M4).** The withheld oracle is the behavioural-identity
measure; `bootstrap-variance` is the structural-difference measure. Together they answer the M5
question. The heavier **reverse-discovery→fidelity-vector-per-compiler** arm remains named and
deferred — it enriches the descriptor without changing a verdict, and is wired only if a v0.1
entry's verdict actually turns on it.

**The oracle-discrimination invariant is enforced, not trusted.** For every entry, `bench`
records that the oracle rejects a degenerate implementation (a stub that ignores its input),
and a `PASS`/`PARTIAL` verdict over an oracle that a stub satisfies is downgraded to `FAIL` with
the reason named. M4 shipped this check by hand; M5 makes it a gate of the bench itself.

**Build order (capacity-aware, stated so the sequencing is not mistaken for scope).** The
harness, the four canonical packages, and the four withheld oracles are authored first (no
model needed). The ≥3 blind compilations per new entry are produced by independent-model
subagents; they run as capacity allows. The bench is designed to report honestly on a
**partial** set — an entry with no compilations yet is `PENDING`, counted, never silently
dropped — so the milestone lands its instrument even if the last compilations trail the commit.

**The schema-gap watch.** If a new archetype surfaces an S-gap that the IR schema — not the SPEC
prose — underdetermines (unlike M4's authoring-level gap), that is the trigger to rewrite the IR
to `v0.2` with the migration posture M2 built. v0.1 does not presume it; it watches for it and
reports it.

## Reasons
- A bench of diverse archetypes is the only way to answer *generalization*; one subsystem
  (M4) answers only itself.
- Reusing the M3 contract and the M4 oracle/variance organs unchanged keeps M5 an
  **orchestration** milestone, not a new-mechanism one — the mechanisms were earned in M3/M4;
  M5 aggregates them into a result.
- Anonymized headlines keep the framing defensible: the bench measures the representation, not
  the model. The raw mapping is published, so nothing is hidden — it is just not the story.
- Making oracle-discrimination a gate of the bench encodes the sharpest M4 lesson (a
  non-discriminating oracle makes "same system" meaningless) as a mechanism, not a convention.

## Consequences
+ The bench is the artifact M5's write-up reads from; growing it to 8–12 is adding entries, not
  new engine.
+ A per-archetype verdict table with boundaries is publishable whether the thesis generalizes or
  maps to a subset.
- v0.1's four entries cannot settle the full-generalization claim; the ADR says so, and the
  bench's own `PENDING`/coverage accounting keeps the partiality visible.
- The blind compilations depend on subagent capacity; the `PENDING` state and the authored-first
  order make that a scheduling fact, not a correctness one.

## Implementation Plan
- Engine: `bench` subcommand — per-entry `compile-validate` + `bootstrap-oracle` +
  `bootstrap-variance` + a degenerate-stub discrimination check; verdict per entry; anonymized
  per-archetype table; `DIAMOND-BENCH.md` writer. Reuse `_run_oracle_case`, `_impl_metrics`,
  `_validate_compilation`, `_load_ir_at` unchanged.
- Fixtures: `uscha-kit/tests/fixtures/diamond-bench/` with `guard` (ingested from M4),
  `parser`, `state-machine`, `transformer` — each canonical package + pinned IR + withheld
  oracle (authored first), then ≥3 blind compilations (as capacity allows) + a committed
  degenerate stub per entry for the discrimination gate.
- Tests: smoke T128, criteria `AC-DB-01..06`; the discrimination gate and the anonymization are
  regression-tested, and the verdict logic is measured on the committed entries.
- Docs: this ADR, ACCEPTANCE `AC-DB-*`, CHANGELOG, SYSTEM-FACTS (subcommand count). Site/README
  stay VISION for the generalization claim until the bench's verdict table earns REAL (T0
  enforces the label); the per-archetype table is where VISION→REAL is decided, per result.

## Verification
- [ ] `bench` over the committed entries emits a per-archetype verdict table and writes
  `DIAMOND-BENCH.md`; every number traces to a `compile-validate`/`bootstrap-oracle`/
  `bootstrap-variance` run (AC-DB-01)
- [ ] each entry's withheld oracle is **discriminating**: a committed degenerate stub scores
  below the real compilers and far below all-green; an entry whose oracle a stub satisfies is
  `FAIL`, reason named (AC-DB-02)
- [ ] a `PASS` entry has ≥3 oracle-green compilations AND genuine variance (no byte-identical
  pair); a near-identical-convergence entry is `FAIL`, not `PASS` (AC-DB-03)
- [ ] model identities are anonymized in the headline table; the raw identity mapping is present
  in the per-entry data (AC-DB-04)
- [ ] an entry with no compilations yet is `PENDING`, counted in coverage, never silently
  dropped; the bench reports honestly on a partial set (AC-DB-05)
- [ ] no compiler input references any oracle; the maker≠checker wall holds across every bench
  entry (AC-DB-06)
