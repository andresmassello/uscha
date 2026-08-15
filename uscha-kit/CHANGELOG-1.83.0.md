# uscha-kit 1.83.0 — the slack hypothesis, tested: a decision-dense scheduler enters the bench, controlled authoring IMPROVES behaviour, and the instrument learns the symmetric lesson (2026-08-15)

ADR-025 + ADR-026, executed together: one same-generation experiment feeding two instruments
(the bench and the controlled-language arm), plus the one engine change the result demanded.

## The experiment (ADR-025)

`scheduler` — a priority job scheduler with deadlines and preemption — enters the Diamond
Bench as its tenth archetype, and deliberately its densest: ≥10 discriminable rules (preemption,
resumption, two-level tie-breaks, deadline at the exact tick vs after, zero-duration jobs,
arrival ties, idle ticks, a deadline landing on a preempted job). The discrimination gate ran
first, as every bench entry requires: the degenerate stub and all **9 `wrong/` implementations**
(each breaking exactly one rule) go red on the withheld oracle before any compilation was
dispatched — `AC-SH-01`, T132.

The three blind compilations (`c-opus`, `c-sonnet`, `c-haiku`) all validate against the pinned
IR with non-empty, bounded, model-distinct `unresolved_intent`. The bench verdict:
**PARTIAL** — opus 30/30 (GREEN), sonnet 26/30, haiku 25/30 — the entry's own discipline holding
under ten times the rule density of the smallest existing archetype (`AC-SH-02`, T132).

The same generation also fed the controlled-language arm: `scheduler-free` (the bench entry's
own free-prose canonical, byte-copied) against `scheduler-controlled` (an EARS+STE rewrite,
human-confirmed same semantics), one dispatch serving both instruments. In the free arm, two of
three compilers resolved the deadline rule as strict `<` where the oracle reads `<=` — their own
verbatim `unresolved_intent` says so. **The blind review of this release established the honest
reading of that fact:** the free-prose SPEC is *self-contradictory* on that rule (`<=` at step 2,
before execution, AND "a job completing at exactly its deadline tick has NOT missed" — a case
the step order makes unreachable), so the two compilers converged on a *defensible alternate
reading*, not on a bug. Their agreement read as low variance (0.0195). The EARS arm restates
the same rule and the same parenthetical — sharper, but the contradiction travels with it — and
what changed was partial: haiku went 30/30, sonnet still failed the same two deadline cases via
a different two-phase reading, opus stayed correct in both arms. Oracle-green rose 1/3 → 2/3,
mean pass-rate 0.900 → 0.978 — and variance **rose** to 0.1879, because the rewrite moved one of
the two compilers off the shared reading (`AC-SH-03`, T132). The rewrite narrowed the slack; it
did not remove it.

## The instrument (ADR-026)

`lang-compare`'s verdict rule was behaviour-first in one direction only: reduced variance with a
behavioural regression read `MIXED`, never masking the loss as a win (the M4 lesson). It had no
symmetric case for the scheduler's shape — behaviour improved, variance rose — and called it
`WORSE`, which was wrong: nothing regressed, an oracle-green was gained, mean pass-rate rose 7.8
points. The fix adds the mirror: **`IMPROVED`** — behaviour up (a gained all-green or a mean
pass-rate rise beyond the 0.02 margin) and not regressed, regardless of what variance did. Every
JSON report now also carries `improved`/`regressed` as explicit booleans, not just the folded
verdict string. The four pre-existing pinned verdicts are unchanged by the new branch: guard
`REDUCED`, parser `NO EFFECT`, state-machine `NO EFFECT`, transformer `WORSE` (`AC-LI-01`,
`AC-LI-02`, T132) — the new rule only opens a previously-unreachable branch, it does not move
any existing one.

## The aggregate

**5 deconfounded archetypes: REDUCED 1 / IMPROVED 1 / NO EFFECT 2 / WORSE 1** — the dense/simple
split now holds at 2 vs 3. Both decision-dense archetypes (guard, scheduler) show controlled
authoring helping — though not the same way: the guard cut variance −61%, the scheduler fixed
behaviour while raising variance. All three simple, low-ambiguity archetypes (parser,
state-machine, transformer) show null or harm. Variance alone was the wrong single number to
watch — the M4 lesson, now confirmed in both directions: it can hide a regression (MIXED) or
manufacture the appearance of one (IMPROVED). `CONTROLLED-LANGUAGE-V03.md` carries the updated
aggregate and rewritten hypothesis paragraph; `CONTROLLED-LANGUAGE-SCHED.md` is the scheduler's
own generated report; `DIAMOND-BENCH.md` regenerated at 10 entries, 7 PASS / 3 PARTIAL.

## What the review caught

Every number reproduced exactly (the five verdicts, the deltas, the discrimination gate, the
byte-identities, the suite counts, the six surfaces). The catches were about **honesty of the
narrative**, which is exactly where a measured program is most tempted to over-claim:
(1) HIGH — the first draft framed the free arm's strict-`<` reading as "two compilers making the
same bug"; the reviewer hand-traced the oracle's own cases and showed the SPEC is genuinely
self-contradictory on that rule and the "not missed at exactly the deadline tick" sentence
describes an unreachable case — so it was a defensible alternate reading of contradictory prose,
the EARS rewrite carried the same contradiction forward, and only one of the two compilers
moved. ADR-025, this changelog and CONTROLLED-LANGUAGE-V03.md were rewritten to say precisely
that; the IMPROVED verdict is unchanged (the numbers are the numbers), its causal story is now
modest. (2) MEDIUM — ADR-026 said WORSE is "reached only when behaviour did not improve";
false: `improved` and `regressed` are not mutually exclusive (an arm can gain an all-green AND
drop pass-rate beyond the margin → both true → WORSE); the ADR now states it and warns
consumers to read `regressed`, never `improved` alone. (3) LOW — the oracle case named
`deadline-exact-completion-ok` completes one tick BEFORE its deadline, so no case affirmatively
exercises the promised exception; noted, and it is the same contradiction seen from the test
side. The reviewer also observed the smoke suite is sensitive to concurrent `qa_ledger.py`
invocations against the same checkout (sidecar reads returned None during their parallel
verification; an isolated run was 418 · 135/135) — worth knowing for anyone sharing a working
tree.

`AC-SH-01..03` and `AC-LI-01..03` measured green (T132 added). Suite: 418 checks, 0 failures;
acceptance **135/135** criteria measured green.
