# uscha-kit 1.81.0 — controlled-language v0.3: the REDUCED does not generalize, and that ships (2026-08-14)

ADR-024, executed exactly as accepted (with one pre-implementation amendment recorded in the
ADR: the draft named `parser` as a replication target, overlooking that parser already IS a
deconfounded datapoint — the v0.2 control; `transformer` took its place and the control enters
the aggregate as the existing row it is). **Zero engine change** — the same instrument, pointed
at more data.

## The measurement

Twelve fresh blind compilations (2 archetypes × 2 arms × 3 models; Write-first mandate;
committed `PROMPT-TEMPLATE.md` scaffold; `unresolved_intent` verbatim), each pair judged by
one byte-identical withheld oracle:

| Archetype | Verdict | The number |
|-----------|---------|-----------|
| guard (v0.2) | REDUCED | variance −61% |
| parser (v0.2 control) | NO EFFECT | perfect null |
| state-machine (new) | NO EFFECT | +0.023 variance, within margin |
| transformer (new) | **WORSE** | an oracle-green lost (3/3 → 2/3) |

**The aggregate the program can now sign: REDUCED in 1 of 4 deconfounded archetypes.** The
guard's positive did not replicate on the simple systems. `CONTROLLED-LANGUAGE-V03.md` carries
the full table; the WORSE row publishes with the same prominence as the REDUCED — a negative
result is a result.

## What the WORSE row teaches

The transformer's EARS arm lost its green on the withheld `extra-field-tolerated` case: the
controlled Definitions say a record has "exactly the fields first/last/age", and the opus
compilation chose strict key-set equality — its own verbatim `unresolved_intent` records the
choice AND the conflict it saw. The free arm's three compilations read the same word
leniently. Controlled language made a latent ambiguity more load-bearing and one compiler
resolved it into a behavioural commitment the oracle rejects: **the discipline has a measured
cost side, not just a benefit side.** The emerging hypothesis (stated as hypothesis): EARS+STE
pays where the prose had slack (the guard's decision-dense rules) and does nothing — or harms
— where the prose was already unambiguous.

`AC-CL3-01..03` measured green (T131 added; verdicts verified interpreter-stable on 3.8 and
3.13 before pinning). Suite: 417 checks; acceptance **128/128** where `coverage.py` is
installed.
