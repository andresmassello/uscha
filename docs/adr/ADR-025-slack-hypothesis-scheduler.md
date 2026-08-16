---
governs:
  - uscha-kit/tests/fixtures/diamond-bench/scheduler/
  - uscha-kit/tests/fixtures/controlled-language/scheduler-free/
  - uscha-kit/tests/fixtures/controlled-language/scheduler-controlled/
  - uscha-kit/tests/smoke-engine.sh
---
# ADR-025: The slack hypothesis, tested — a decision-dense scheduler archetype enters the bench AND the controlled-language arm in one same-generation experiment (slack-hypothesis v0.1)

## Status: Accepted

## Context
Controlled-language v0.3 (ADR-024) closed at "REDUCED in 1 of 4 deconfounded archetypes" and
left one hypothesis on the table, stated as hypothesis: *EARS+STE pays where the prose had
slack — the decision-dense guard, −61% variance — and does nothing or harms where the prose was
already unambiguous (parser, state-machine, transformer: bounded, low-ambiguity systems).* One
positive on the only decision-dense archetype is a pattern with n=1. The cheapest test is a
SECOND decision-dense archetype run through the same protocol: if REDUCED reappears, the
hypothesis strengthens; if null or WORSE, it dies. Either result ships.

The bench itself also benefits: its 9 entries are all small (7–8 IR nodes, 12–23 oracle cases,
one unit); a denser entry tests whether the verdict machinery (discriminating oracle, wrong/
fixtures, PARTIAL floor) holds when there is more to get wrong.

## Decision
- **New bench archetype `scheduler`** — a priority job scheduler with deadlines and preemption:
  jobs `{id, priority, arrival, duration, deadline?}` arrive over discrete ticks; at every tick
  the highest-priority ready job runs; a higher-priority arrival preempts a running job (which
  resumes later, remaining duration preserved); ties break by earlier arrival then lower id; a
  job past its deadline is dropped with a `missed` event; output is the ordered event log
  `[tick, event, job]` and a final `{completed, missed}` summary; malformed input → `ERROR`.
  This is deliberately decision-dense: ≥10 discriminable rules (preemption, resumption, tie
  breaks at two levels, deadline at exact tick vs after, zero-duration jobs, arrival ties,
  idle ticks, deadline on a preempted job) — every one of them a place a compiler can diverge.
- **The entry ships with the full bench discipline**: canonical (SPEC/ACCEPTANCE/CONSTITUTION),
  pinned IR, withheld oracle (≥25 cases, one per rule plus malformed shapes), a degenerate
  `stub/`, and `wrong/` implementations that each break exactly one rule — the oracle must
  turn every wrong/ red and the reference green BEFORE any compilation is dispatched (the
  1.77.0 discrimination gate, run by the suite).
- **Both arms, same generation**: `scheduler-free` (the free-prose canonical, byte-copied) and
  `scheduler-controlled` (an EARS+STE rewrite, human-confirmed same semantics) each compiled
  blind ×3 models in one session; shared byte-identical oracle; `lang-compare` computes the
  verdict. The bench entry's `c-*` compilations ARE the free arm's compilations (one dispatch
  serves both instruments — no duplicate free run).
- **The claim update is mechanical**: `CONTROLLED-LANGUAGE-V03.md` gains a fifth row and the
  aggregate becomes "REDUCED in k of 5"; the hypothesis paragraph is rewritten to state what
  the fifth datapoint did to it — strengthened, weakened, or killed — in those words.
  *Post-review note (1.83.0):* the datapoint landed as IMPROVED (ADR-026) and the mechanism
  was smaller than first written — the free-prose SPEC was self-contradictory on the deadline
  rule, two compilers converged on a defensible alternate reading, and the EARS rewrite moved
  one of them without removing the contradiction. The row is honest about that.
  *Superseded on the variance point by ADR-027 (1.84.0):* the free arm's low inter-compiler
  variance (0.0195) sits BELOW the scheduler entry's own intra-model noise floor (0.0348),
  so "convergence on a shared reading" is RETRACTED as a variance claim; the behavioural
  fact (two compilers made the same `<` choice, verbatim in their `unresolved_intent`; EARS
  moved one, oracle 1/3 → 2/3) is what stands.
- **Zero engine change.** Fixtures + smoke pins only.

## Reasons
- A hypothesis the program itself produced deserves the program's own instrument pointed at it
  before anyone repeats it. n=2 on the dense side is the minimum that separates "pattern" from
  "the guard was special".
- One dispatch feeding two instruments keeps the experiment cheap and the free arm honestly
  same-generation with the controlled arm.

## Consequences
+ The bench gains its first decision-dense entry; the controlled-language aggregate reaches
  n=5 with two dense archetypes.
+ Whichever way it lands, the hypothesis stops being a paragraph and becomes a measured row.
- A dense oracle is more work to make discriminating; the wrong/ set must be complete or the
  entry proves less than it claims. The discrimination gate is the guard.

## Verification
- [ ] `scheduler` oracle is discriminating: the reference passes 100%, the degenerate stub and
  EVERY `wrong/` implementation each go red on at least one case, run by the suite (AC-SH-01)
- [ ] The three blind compilations validate against the pinned IR; the bench verdict for
  `scheduler` is computed and pinned (whatever it is); `unresolved_intent` verbatim and
  model-distinct (AC-SH-02)
- [ ] `lang-compare` over `scheduler-free` vs `scheduler-controlled` (oracle byte-identical,
  same generation) yields a pinned verdict; `CONTROLLED-LANGUAGE-V03.md` states the aggregate
  as "k of 5" and rewrites the hypothesis paragraph in the direction the data went (AC-SH-03)
