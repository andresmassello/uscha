# uscha-kit 1.75.1 — the independent blind reviews earn their keep (2026-08-13)

A correctness-and-honesty patch. M4 (1.74.0) and M5 (1.75.0) each shipped with an *inline
self-review* because the independent blind judges had died on a session limit at M4's release.
This patch runs the independent blind reviews that were owed — one per milestone, on the shipped
commits `f10b9d1` (M4) and `8d6b966` (M5) — and folds in every real finding. Both reviews
confirmed the engine mechanics and the measured verdicts are sound; both caught defects the
inline self-reviews had missed. The lesson, stated plainly: an inline self-review is not a
substitute for an independent one.

## M5 — the bench oracles were thinner than claimed (CRITICAL, fixed)

The independent review wrote its own *plausible-but-wrong* implementations — exactly what
ADR-018's oracle-discrimination invariant exists to guard against — and found two withheld
oracles did **not** discriminate them:

- **parser:** the oracle had no exponentiation or bitwise case. An `eval`-based parser that
  accepts `2**3` (which the SPEC forbids) scored a false **17/17 green**.
- **transformer:** the oracle had no boolean-`age` case. A naive `isinstance(age, int)` check
  (bool is an int subclass in Python) that accepts `{"age": true}` scored a false **11/11
  green**.

The three *real* compiled implementations always rejected both — so the shipped PASS verdicts
were never computationally wrong — but the oracles were weaker than 1.75.0's "every entry
discriminates against a plausible-but-wrong implementation" claim. **Fixed** by adding the
missing cases (each verified to agree across all three real implementations first, so no PASS
was flipped by fitting the oracle to a result):

- parser oracle 17 → **21** cases: exponentiation-rejected, bitwise-and/or-rejected, and a
  second truncate-toward-zero case (`-7 / 2 → -3` was the only one; `-9 / 4 → -2` is the new
  one), closing the MEDIUM "only one negative-division case" finding too.
- transformer oracle 11 → **14** cases: boolean-`age` rejected, float-`age` rejected, and a
  positive extra-field-tolerated case.

Re-measured: the real implementations still all PASS (parser **21/21 ×3**, transformer **14/14
×3**); the two plausible-wrong implementations now correctly go red (18/21, 13/14). The
discrimination claim is now *true*, not merely asserted. DIAMOND-BENCH.md regenerated.

A LOW finding was also fixed: `_bench_entry` reported "implementations converged to a
byte-identical pair" when the real cause was fewer than two *resolvable* implementation files —
two different failure modes now get two different reasons.

## M4 — two report-honesty defects (HIGH + MEDIUM, corrected in the M4 docs)

- **HIGH:** BOOTSTRAP-REPORT.md and CHANGELOG-1.74.0.md described Opus-r2's residual two red
  cases as a *designed* `-c`/`-e` inline-expression boundary. It is not — it is a **tokenizer
  artifact**: Opus-r2's shell splitter treats a bare `(`/`)` as a stage separator, so `shlex`
  on the oracle's exact quoting isolates a pseudo-stage whose "verb" is not a known reader and
  default-deny blocks it. Re-quoting the identical command (`python -c "open('x.approved','w')…"`
  with outer double quotes) flips the verdict to allow; Sonnet-r2 is robust to the same
  re-quoting. So the semantic S-gap closed for *both* round-2 compilers — Opus's residual is a
  compiler implementation bug, not a canonical-package divergence. Corrected in place.
- **MEDIUM:** the round-2 winner (Sonnet-r2) is **305 LOC** — the measured cost of closing the
  S-gap — which the report never stated while quoting a "110–220 LOC" range drawn from round 1.
  Now stated.

Everything else both reviews checked held: oracle faithfulness, backward-compat (guard 23/23),
report-vs-data across every other number, path-traversal containment, anonymization,
withholding (no compiler input references any oracle), and the IR-hash-unchanged claim.

## Verification

`bash uscha-kit/tests/smoke-engine.sh` green (compile 7 · bootstrap 6 · bench 6); acceptance
**104/104** where `coverage.py` is installed. No new subcommands (47). The bench's four verdicts
are unchanged (guard PARTIAL, parser/state-machine/transformer PASS) — the oracles are stronger,
so the same PASS is now better earned.
