# CONTROLLED-LANGUAGE v0.3 — replication across archetypes (ADR-024)

The question v0.2 left open: the guard's deconfounded REDUCED (−61% inter-compiler variance)
is one positive on one subsystem. Does it generalize? v0.3 replicates the deconfounded
protocol — fresh same-generation blind compilations of BOTH arms, one shared withheld oracle
per pair, zero engine change — on two more bench archetypes.

## The aggregate: REDUCED in 1 of 4 deconfounded archetypes

| Archetype | Kind | Verdict | Variance delta | Pass-rate delta | Oracle-green | Source |
|-----------|------|---------|----------------|-----------------|--------------|--------|
| guard | logic-heavy validator | **REDUCED** | −0.2628 (−61%) | −0.015 (within margin) | 0/3 → 0/3 | CONTROLLED-LANGUAGE-DECONFOUNDED.md (v0.2) |
| parser | text-heavy, simple (control) | **NO EFFECT** | −0.0477 (within margin) | 0.000 | 3/3 → 3/3 | CONTROLLED-LANGUAGE-CONTROL.md (v0.2) |
| state-machine | state-heavy, simple | **NO EFFECT** | +0.0231 (within margin) | 0.000 | 3/3 → 3/3 | CONTROLLED-LANGUAGE-SM.md (v0.3) |
| transformer | data-heavy, simple | **WORSE** | −0.0321 (within margin) | −0.0238 | 3/3 → **2/3** | CONTROLLED-LANGUAGE-TF.md (v0.3) |

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

## Honest reading

- **The guard's REDUCED did not replicate on the simple archetypes.** One deconfounded
  positive (guard, −61%), two nulls (parser control, state-machine), one negative
  (transformer). The program claim is now "REDUCED in 1 of 4" — not "controlled language
  reduces variance".
- **The pattern the data suggests (hypothesis, not conclusion):** the guard is the one
  archetype with real decision density (a security guard with dozens of edge rules); the
  three where controlled authoring showed nothing or hurt are bounded, low-ambiguity systems
  whose free prose was already unambiguous. Controlled language may only pay where the prose
  had slack — and may sharpen definitions into over-commitments where it had none.
- **Stated limitation, unchanged:** the judgement of "same semantic content" between each
  pair of canonical packages is human.

## Protocol notes

- 12 fresh blind compilations (2 archetypes × 2 arms × 3 models), Write-first mandate,
  scaffold = the committed `PROMPT-TEMPLATE.md`, `unresolved_intent` stamped VERBATIM from
  each model's return.
- Oracles are byte-identical copies of the bench entries' withheld oracles; the compilers
  never saw a case.
- Verdicts are interpreter-stable: `lang-compare` reproduces NO EFFECT / WORSE identically
  under Python 3.8 and 3.13 (checked before pinning — the 1.78.0 lesson).
