---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
---
# ADR-026: `lang-compare` learns the symmetric lesson — higher variance toward a BETTER answer is not a loss; the IMPROVED verdict (lang-compare v0.2)

## Status: Accepted

## Context
ADR-019 made the controlled-language verdict *behaviour-first*, with the M4 lesson written into
the code: "lower variance toward a WORSE answer is not a win" — variance down + behaviour
regressed reads MIXED, never REDUCED. The rule was one-sided. The scheduler experiment
(ADR-025) produced the mirror case the rule could not name: the EARS arm improved behaviour
(oracle-green 1/3 → 2/3, mean pass-rate 0.900 → 0.978) AND raised inter-compiler variance
(0.020 → 0.188) — because in the free arm two compilers **converged on the same reading**
(both resolved a self-contradictory deadline rule as strict `<` — a defensible alternate
reading the withheld oracle happens to reject), and convergence on a shared reading reads as
low variance whether the reading is right or wrong. The controlled rewrite separated them: one fixed the bug, one made a different
mistake, one was already right. The engine called that WORSE, on the variance branch, while
every behavioural number said the discipline had helped.

Low variance is only a virtue when it converges on the right answer. The instrument must say
so in both directions.

*Qualified by ADR-027 (1.84.0):* the scheduler example above is retracted AS A VARIANCE
CLAIM — its free-arm inter-compiler distance (0.0195) is below that entry's intra-model
noise floor (0.0348, `bench-r2`), so the low variance was not evidence of convergence. The
IMPROVED verdict stands on the oracle delta (1/3 → 2/3 green), which is not a variance
number, and the rendered IMPROVED text now points readers at the noise floor.

## Decision
- **New verdict `IMPROVED`**: behaviour improved (an oracle-green gained, or mean pass-rate up
  by ≥ `_LANG_PR_MARGIN`) while variance is NOT reduced (rose or unchanged). Behaviour won;
  variance did not — reported as what it is, never as WORSE.
- **Verdict order, behaviour-first in both directions**:
  1. variance reduced AND regressed → `MIXED` (unchanged, ADR-019)
  2. variance reduced (behaviour held or improved) → `REDUCED` (unchanged)
  3. **improved (behaviour up) AND variance not reduced → `IMPROVED` (new)**
  4. variance worse OR regressed → `WORSE` (unchanged). Note `improved` and `regressed` are
     NOT mutually exclusive: an arm can gain an all-green AND drop mean pass-rate beyond the
     margin; that reads WORSE (rule 3 requires `not regressed`) and the report carries both
     booleans true — a consumer must read `regressed`, never `improved` alone.
  5. else → `NO EFFECT`
- The report renders IMPROVED with its own explanatory line naming the mechanism: "behaviour
  improved while variance rose — check whether the free arm's low variance was convergence on
  a shared reading — right or wrong". The raw JSON carries `improved: true|false` alongside `regressed`.
- Existing pinned verdicts must not move: guard REDUCED, parser NO EFFECT, state-machine NO
  EFFECT, transformer WORSE (behaviour regressed there — rule 4 still fires) — the suite
  asserts all four unchanged.

## Reasons
- A verdict that contradicts every behavioural number in the report is a narrated verdict; the
  method forbids it in the engine as much as in the docs.
- The symmetric case is not hypothetical — the program produced it. Naming it costs one
  branch and one word.

## Consequences
+ The controlled-language instrument becomes honest in both directions; the scheduler row
  reads IMPROVED and the aggregate can count it.
+ "Convergence on a shared reading" becomes a named phenomenon the report warns about.
- One more verdict to explain; the doc tables and the report legend grow by a line.

## Verification
- [ ] Variance up + oracle-green up (or pass-rate up ≥ margin) → `IMPROVED`; variance up +
  behaviour flat → `WORSE`; variance down + behaviour up → `REDUCED` (AC-LI-01)
- [ ] The four previously pinned verdicts (guard, parser, state-machine, transformer) are
  unchanged by the new rule (AC-LI-02)
- [ ] The scheduler pair reads `IMPROVED` with `improved: true`, and the rendered report
  carries the shared-error warning line (AC-LI-03)
