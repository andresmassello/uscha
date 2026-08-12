---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
---
# ADR-017: Bootstrap v0.1 — a bounded subsystem's identity is carried by its canonical package + a withheld oracle, not by its implementation; independent compilers are certified the same system by evidence they never saw (M4)

## Status: Accepted

## Context
Diamond M4. M3 made "LLM as compiler" a validated contract (`compile/0.1`, ADR-016). M4 asks
the program's load-bearing question on real Uscha code: for a bounded subsystem with a mature
canonical package, **is the implementation the unique carrier of the system's identity, or can
independent compilers produce different code that the same external evidence certifies as the
same system?**

**Falsifiable thesis:** the implementation is *not* the carrier. Three independent compilers,
each seeing only the canonical package, produce three implementations that a **withheld oracle**
(authored before any compilation, never shown to the compilers) certifies as behaviourally the
same system — while implementation-variance evidence proves the three genuinely differ.
**It fails if** (a) no compiler reconstructs an oracle-passing implementation, or (b) all pass
only by converging on near-identical code (which would mean the canonical package is a disguised
implementation). **Both the pass and the honest failure are program successes:** a failure
yields the *S-gap* — exactly the information the canonical package lacked — which rewrites the IR
toward v0.2. Convergence-to-identical is the more dangerous outcome and is measured explicitly.

**The subsystem (human-picked): the INV-GOLDEN-01 PreToolUse hook** (`block-approved-writes.py`).
Chosen because it is the honest hard case in miniature: ~130 lines, a **pure decision function**
(`payload → block | allow`) with a fail-closed posture and a sharp, security-relevant invariant,
**standalone by nature** (a hook has no ledger coupling), and it already carries an adversarial
behavioural oracle (smoke T110). "Same behaviour = same system" is *meaningful* here — a hook
that allows one write the original blocks is a different system, measurably.

Three lines have to be drawn, and each is where the milestone could quietly cheat itself.

**Line 1 — maker ≠ checker, physically.** Options:
- **A) The oracle is derived from, or shown alongside, the canonical package.** Rejected: if the
  compilers can see the test cases, "passing the oracle" measures teaching-to-the-test, not
  reconstruction. The whole thesis dissolves.
- **B) The oracle is authored FIRST, hash-pinned, and physically withheld** — a separate
  `ORACLE.json` of `{payload, expected_exit}` cases that no compiler prompt ever contains, run by
  a separate engine against each compiled implementation. **Chosen.** The compilers see the
  canonical package (SPEC + ACs + INV-GOLDEN-01); they never see a single oracle case. This is
  the M3 engine-never-compiles wall extended to the whole experiment: the checker is a different
  physical artifact than anything the maker touched.

**Line 2 — the oracle is a measured fact, and facts decide.** The oracle's verdict (behavioural
pass rate per compiler) is deterministic execution — a `measured`-class fact, not an LLM
judgment — so it is *allowed to be decisive* about "same system" (facts decide; ADR-014's
quarantine is about advisory judgments, which this is not). Implementation variance is
**evidence, not a gate**: it proves the implementations differ, but it never certifies or denies
"same system" — only the oracle does that.

**Line 3 — the feedback loop must be real, and bounded.** Options for the compile→fail→improve
loop: unbounded (iterate until green) or fixed-N. **N = 2 (chosen):** the initial compile plus at
most one improvement round. On any oracle failure, the *S-gap* is computed (what the canonical
package underdetermined — the forward-direction sibling of M3's `unresolved_intent`), the
canonical package/IR is improved **once**, the failing compiler recompiles, and the oracle re-runs.
The convergence trajectory is reported either way. Unbounded iteration would let the canonical
package be over-fit to one model until it green-lights — a disguised implementation by the back
door. If round 1 passes clean for all three, the S-gap catalog is honestly *empty* and the loop is
reported as "not needed for this subsystem" — never a manufactured failure.

**Explicitly out of M4 v0.1 (deferred):** the **controlled-language arm** (compiling the same
subsystem from free prose vs an EARS/STE rewrite and measuring the variance delta). It roughly
doubles the work and is better run once the core loop has produced a variance baseline to compare
against. Named here so its absence is a decision, not an omission.

## Decision

**The M4 v0.1 protocol, on the INV-GOLDEN hook, with three blind compilers (Opus, Sonnet, Haiku
via independent subagents) and N = 2:**

1. **Freeze the canonical package `S`.** A purpose-authored `SPEC.md` + acceptance items + the
   governing `INV-GOLDEN-01`, describing the hook's REQUIRED behaviour (block writes/renames/
   deletes of a `.approved` golden across Bash and any write-capable tool; allow reads; case-
   insensitive; fail-closed on a malformed payload; exit 2 = block, 0 = allow) **without the
   implementation and without any oracle case.** `ir-extract`ed into a hash-pinned IR snapshot —
   the compile target.
2. **Author the withheld oracle `O`** BEFORE any compilation: `ORACLE.json`, a suite of
   `{name, payload, expected_exit}` behavioural cases covering the contract and its adversarial
   edges (fail-closed on non-JSON / non-dict; case-insensitivity; redirection `>`; write-flags;
   a pipeline whose reader still writes via `tee`; an unknown write-capable tool; a legitimate
   read allowed). Hash-pinned. **Never included in any compiler prompt.**
3. **Compile `S` with three models** through the `compile/0.1` contract (ADR-016). Each subagent
   sees only `S`; produces a `COMPILATION.json` (source = a reimplemented hook, tests = its own,
   `trace_manifest`, `unresolved_intent`, report) that **must pass `compile-validate`** against
   the pinned IR. → C₁, C₂, C₃.
4. **Run the withheld oracle against each Cᵢ** with the new **`bootstrap-oracle`** engine: pipe
   each case's payload into the compiled hook, compare its exit code to `expected_exit`, record
   pass/fail per case into the ledger. Deterministic; the oracle is a `measured` fact.
5. **Prove the implementations genuinely differ** with the new **`bootstrap-variance`** engine:
   per-impl `{loc, functions, classes, ast_nodes, imports}` and pairwise divergence — evidence,
   advisory, never a gate. And **reverse-discover each Cᵢ** (M1 `discover` + `fidelity`) → Sᵢ′ and
   its fidelity vector, reusing the shipped engines.
6. **S-gap loop (N = 2).** For every oracle failure, compute the S-gap (the canonical region the
   compiler underdetermined), improve `S`/IR **once**, recompile the failing model(s), re-run the
   oracle. Report the trajectory. Empty S-gap catalog (all pass round 1) is a reported outcome.
7. **Publish `BOOTSTRAP-REPORT.md`** — oracle results per compiler, fidelity vectors, variance
   evidence, the S-gap catalog, any IR schema change it forced (bump to `0.2` only if the S-gap
   demands it; the M2 versioned-schema + exit-2-on-unknown posture makes the migration cheap),
   and the **honest verdict**: pass / fail / partial, with the boundary drawn. The expected
   boundary — functional identity yes, NFR/operational identity underdetermined — is stated in
   Uscha's own docs *if observed*, before anyone else states it.

**The original hook is never removed from the repo.** "Remove the implementation" means the
compilers work from `S` alone in an isolated bootstrap sandbox
(`uscha-kit/tests/fixtures/bootstrap-golden-hook/`); the shipped `block-approved-writes.py` stays
in force. The experiment is hermetic.

## Reasons
- The INV-GOLDEN hook is the smallest subsystem where "same system" has teeth: a pure, fail-
  closed, security-relevant decision function whose adversarial oracle already exists. If the
  thesis cannot be shown here, a bigger subsystem would only hide the failure in noise.
- Withholding the oracle physically is the only honest way to measure *reconstruction* rather
  than *teaching-to-the-test* — the same maker≠checker discipline M3 built into the engine, now
  built into the experiment's file layout.
- Bounding the loop at N = 2 keeps the canonical package from being over-fit into a disguised
  implementation, which is the failure mode that would make a "pass" meaningless.
- Reusing M3's `compile-validate` as the compile interface and M1's `discover`/`fidelity` as the
  reverse arm means M4 adds only the two genuinely new organs — the oracle runner and the
  variance meter — and otherwise composes shipped, tested engines.

## Consequences
+ M4 v0.1 is the first end-to-end run of the whole Diamond loop on real Uscha code: canonical
  package → three compilations → withheld oracle → variance + fidelity → S-gap → (maybe) IR v0.2.
+ Whatever the verdict, it is publishable: "three different implementations, one oracle, same
  system" *or* "the canonical package underdetermined X, here is the S-gap and the IR change it
  forced." The program's own standing rule (failure is a computed, reported result) holds.
- A genuine risk: all three compilers converge on near-identical code (thesis-endangering). This
  is measured head-on by `bootstrap-variance`; low variance with a green oracle is reported as a
  *weak* result, not dressed up as a strong one.
- The controlled-language arm is deferred; the variance baseline this milestone produces is
  exactly what makes that follow-up interpretable.
- v0.1 is deliberately one subsystem. M5 generalizes across archetypes; M4 earns the right to.

## Implementation Plan
- Engine: `bootstrap-oracle` (run a withheld `ORACLE.json` against a compiled hook; per-case
  pass/fail into the ledger; exit 0 iff all pass) and `bootstrap-variance` (per-impl AST/LOC/
  import metrics + pairwise divergence; advisory). Reuse `compile-validate` (compile interface),
  `discover`/`fidelity` (reverse arm), `_load`/`_save`/`_integrity_hash` (ledger + pinning).
- Fixtures: `uscha-kit/tests/fixtures/bootstrap-golden-hook/` — `canonical/` (SPEC + ACCEPTANCE +
  CONSTITUTION for the hook) + its pinned `IR.json`; `oracle/ORACLE.json` (withheld); `c-opus/`,
  `c-sonnet/`, `c-haiku/` (the three `COMPILATION.json` + sources, produced by blind subagents,
  each `compile-validate`-green).
- Tests: smoke T127, criteria `AC-BS-01..06`; the withheld-oracle discipline is itself asserted
  (the oracle file is not referenced by any compiler input).
- Docs: this ADR, `BOOTSTRAP-REPORT.md`, ACCEPTANCE `AC-BS-*`, CHANGELOG, SYSTEM-FACTS
  (subcommand count 44→46). Site/README stay VISION for everything past M1 until M4/M5 close and
  T0 lets the label change — and M4's verdict is precisely what may begin to move it.

## Verification
- [ ] `bootstrap-oracle` runs the withheld `ORACLE.json` against a compiled hook, records per-case
  pass/fail, and exits 0 iff every case matches its `expected_exit` (AC-BS-01)
- [ ] the oracle is a measured fact and is decisive: an implementation that allows a case the
  contract blocks fails the oracle, named case-by-case; the runner never consults an LLM (AC-BS-02)
- [ ] no compiler input (any `c-*/` prompt/source) references the oracle file or its cases — the
  maker≠checker wall is asserted mechanically, not trusted (AC-BS-03)
- [ ] all three `c-*` compilations pass `compile-validate` against the pinned canonical IR
  (AC-BS-04)
- [ ] `bootstrap-variance` reports per-impl metrics and pairwise divergence proving the three
  implementations genuinely differ; it is advisory and never changes an exit code (AC-BS-05)
- [ ] the S-gap loop is bounded at N = 2: on an oracle failure an S-gap entry is recorded and one
  improvement round runs; an all-pass round 1 yields an empty, reported S-gap catalog — never a
  manufactured failure (AC-BS-06)
