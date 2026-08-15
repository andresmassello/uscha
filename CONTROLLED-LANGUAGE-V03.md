# CONTROLLED-LANGUAGE v0.3 — replication across archetypes (ADR-024)

The question v0.2 left open: the guard's deconfounded REDUCED (−61% inter-compiler variance)
is one positive on one subsystem. Does it generalize? v0.3 replicates the deconfounded
protocol — fresh same-generation blind compilations of BOTH arms, one shared withheld oracle
per pair, zero engine change — on two more bench archetypes.

## The aggregate: 5 deconfounded archetypes — REDUCED in 1, IMPROVED in 1, NO EFFECT in 2, WORSE in 1

| Archetype | Kind | Verdict | Variance delta | Pass-rate delta | Oracle-green | Source |
|-----------|------|---------|----------------|-----------------|--------------|--------|
| guard | logic-heavy validator | **REDUCED** | −0.2628 (−61%) | −0.015 (within margin) | 0/3 → 0/3 | CONTROLLED-LANGUAGE-DECONFOUNDED.md (v0.2) |
| parser | text-heavy, simple (control) | **NO EFFECT** | −0.0477 (within margin) | 0.000 | 3/3 → 3/3 | CONTROLLED-LANGUAGE-CONTROL.md (v0.2) |
| state-machine | state-heavy, simple | **NO EFFECT** | +0.0231 (within margin) | 0.000 | 3/3 → 3/3 | CONTROLLED-LANGUAGE-SM.md (v0.3) |
| transformer | data-heavy, simple | **WORSE** | −0.0321 (within margin) | −0.0238 | 3/3 → **2/3** | CONTROLLED-LANGUAGE-TF.md (v0.3) |
| scheduler | decision-dense (preemption, deadlines, tie-breaks) | **IMPROVED** | +0.1684 (rose) | **+0.0778** | 1/3 → **2/3** | CONTROLLED-LANGUAGE-SCHED.md (ADR-025, 1.83.0) |

Every row is a same-generation pair: both arms compiled fresh by the same three models in the
same session, judged by one byte-identical withheld oracle. The verdicts are computed by
`lang-compare` (ADR-019), never narrated.

## What the WORSE row is

The transformer's EARS+STE arm lost an oracle-green: the opus compilation fails the withheld
case `extra-field-tolerated` (a record carrying an extra unknown field must still transform).
Its own verbatim `unresolved_intent` records why: the EARS Definitions say a record has
"exactly the fields first/last/age", and the compiler chose strict key-set equality —
rejecting extras as malformed — while noting the conflict with the error list that never
names extra fields. The free-prose arm's three compilations all read the same "exactly" (the
word appears in BOTH arms) leniently. **The controlled rewrite made a latent ambiguity more
load-bearing, and one compiler resolved it into a behavioural commitment the oracle rejects.**
That is not noise; it is the cost side of the discipline, measured.

## What the IMPROVED row is (ADR-025 — the slack hypothesis, tested)

The scheduler is the second decision-dense archetype (≥10 discriminable rules: preemption,
resumption, two-level tie-breaks, deadline-at-exact-tick, zero-duration jobs, idle ticks).

**The mechanism, stated precisely (the 1.83.0 review corrected the first draft of this
paragraph):** the free-prose SPEC is *self-contradictory* on one rule. It says a job is
missed when `deadline <= tick` at step 2 (before execution), AND that "a job completing at
exactly its deadline tick has NOT missed" — but under the step order, step 2 always fires
before step 4, so a job whose completion would land ON its deadline tick is *always*
intercepted first. The "not missed" sentence describes a case the rule makes unreachable.
Two of three free-arm compilers (sonnet, haiku) saw that tension and resolved it toward the
prose — strict `<` — which their verbatim `unresolved_intent` records ("use `<` instead of
spec's `<=`", "strict `<` resolves the contradiction"). The withheld oracle resolves it the
other way (`<=`, matching `wrong/deadline-strict.py`, which the bench designer had built
precisely for this reading). **So the free arm's low variance (0.020) was two compilers
converging on the SAME defensible alternate reading of a contradictory spec — not on a bug.**

The EARS arm restates the same rule and the same parenthetical (sharper, but the contradiction
travels with it). What changed: haiku went 30/30 (landed on the oracle's resolution); sonnet
still failed the same two deadline cases via a *different, more elaborate* two-phase reading;
opus was right in both arms. Oracle-green 1/3 → 2/3, mean pass-rate 0.900 → 0.978. Variance
ROSE (0.188) because the rewrite separated the two that had agreed. **The rewrite did not
close the ambiguity — it moved one of two compilers off the shared reading.** That is the
measured effect, and it is smaller than "EARS fixed the bug".

The instrument initially called that WORSE — its ADR-019 rule was behaviour-first only
downward. ADR-026 (same release) adds the symmetric verdict: **higher variance toward a better
answer is not a loss**. IMPROVED is now a named outcome, and "convergence on a shared reading"
(right or wrong) a named phenomenon the report warns about.

## Honest reading

- **The slack hypothesis strengthened — with two corrections.** Two of two decision-dense
  archetypes show controlled authoring helping (guard: variance −61%; scheduler: behaviour +1
  green, +7.8 pts pass-rate). Correction one: on the scheduler the help was partial (one of two
  compilers moved) and the spec's own contradiction was NOT removed by the rewrite — the
  IMPROVED is real, its causal story is modest. Three of three simple, low-ambiguity archetypes
  show null or harm. The dense/simple split now holds at n=2 vs n=3.
- **Correction two: "pays" is not always "less variance".** On the guard it reduced variance; on the
  scheduler it fixed behaviour while raising variance. The common thread is *the free prose
  had slack a compiler could fall into*, and EARS narrowed it — partially, not fully; the
  scheduler's contradiction survived the rewrite. Variance alone was the wrong single number —
  the M4 lesson, now in both directions.
- **The cost side stands too:** the transformer's WORSE (a sharpened definition read as an
  over-commitment) is real and unchanged.
- **Stated limitation, unchanged:** the judgement of "same semantic content" between each
  pair of canonical packages is human (signed per pair by the operator).

## Protocol notes

- v0.3: 12 fresh blind compilations (2 archetypes × 2 arms × 3 models); ADR-025: 6 more (scheduler × 2 arms × 3 models, the free arm doubling as the bench entry) — all Write-first mandate,
  scaffold = the committed `PROMPT-TEMPLATE.md`, `unresolved_intent` stamped VERBATIM from
  each model's return.
- Oracles are byte-identical copies of the bench entries' withheld oracles; the compilers
  never saw a case.
- Verdicts are interpreter-stable: `lang-compare` reproduces NO EFFECT / WORSE / IMPROVED
  identically under Python 3.8 and 3.13 (checked before pinning — the 1.78.0 lesson).
