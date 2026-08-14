# uscha-kit 1.78.0 — controlled-language v0.2: the control shows nothing, the confound kill shows the signal was real (2026-08-13)

ADR-021. The two follow-ups v0.1 (kit 1.76.0) owed, run as pre-registered experiments — both
expectations were stated in the ADR before any compilation, so the data could embarrass them.
No engine changes; six new blind compilations; every number a `lang-compare` run.

## Experiment 1 — the control arm: NO EFFECT, as predicted

The parser is a converged archetype (3/3 oracle-green from free prose in the bench). It was
re-authored in EARS+STE (same content, byte-identical oracle — the mechanical guard) and
recompiled blind by the same three models. Measured: **NO EFFECT** — a clean null on every
axis: both arms 3/3 green, pass-rate 1.000 both, variance delta −0.048 (inside the 0.05
margin), `unresolved_intent` **4.00 vs 4.00, delta 0.00**. An instrument that has only ever
shown effects where effects were hoped for had never demonstrated it can show **nothing**; now
it has, on real data. (The release candidate briefly reported a "+2.0 unresolved_intent under
EARS" wrinkle here; the blind review exposed it as an artifact of a contaminated baseline —
see below — and with real data the wrinkle vanishes into an exact null.)

## Experiment 2 — the confound kill: REDUCED, the v0.1 signal survived

v0.1's arm A reused M4's compilations, whose prompt scaffolding was close-but-not-identical to
the EARS arm's — the review called the confound "asserted, not bounded." The guard's free-prose
canonical was therefore **recompiled blind with scaffolding byte-matched to the EARS arm's**
(same template; only the canonical text differs). Measured against the same controlled arm:

| Arm | Oracle-green | Mean pass-rate | Variance | unresolved_intent |
|-----|--------------|----------------|----------|-------------------|
| guard free-prose, fresh (matched scaffolding) | 0/3 | 0.870 | **0.432** | 5.00 |
| guard EARS+STE (v0.1's controlled arm) | 0/3 | 0.855 | **0.170** | 4.67 |

**Verdict: REDUCED** — variance delta **−0.263 (−61%)**, pass-rate delta −1.45% (inside the 2%
margin), green +0. Two things this settles honestly:

- **The v0.1 effect was not scaffolding.** With the scaffold held fixed (the committed
  template), the free-prose arm scattered at least as much as the M4-reused one had (0.432 vs
  0.347 — though that 0.432 is dominated by one 450-LOC Opus outlier, so its exact size is
  n=3-noisy). The de-confounded reduction is comfortably beyond the margin either way.
- **v0.1's MIXED softens to REDUCED against the fresh baseline** — computed, not decreed: the
  fresh free arm's own mean pass-rate is 0.870, so the controlled arm's 0.855 sits inside the
  pass-rate margin (−1.45%) that the stale baseline had put outside it (−2.9%). The v0.1
  report stands as measured-then; this run is the cleaner comparison and both are published
  (`CONTROLLED-LANGUAGE-REPORT.md` = the confounded first run, `CONTROLLED-LANGUAGE-CONTROL.md`,
  `CONTROLLED-LANGUAGE-DECONFOUNDED.md` — three generated files, every number a run artifact).

Scoped as ever: one subsystem + one control archetype, three models — two data points, not a
law. `unresolved_intent` remains the weaker proxy (an exact null in the control, a slight fall here).

## What the review caught (fifth consecutive catch)

- **HIGH — the pre-1.76.0 synthesized-metadata defect was still live in the original bench
  fixtures, and this milestone imported it.** `parser-free` is a byte-copy of the bench parser
  (stamped at 1.75.0, *before* the verbatim rule), and its `unresolved_intent` was
  **word-for-word identical across all three "independent" compilers** — the exact fingerprint
  1.75.1 caught once already, systemic in the bench's original parser/state-machine/transformer
  entries. The experiment's briefly-reported "+2.0 under EARS" compared genuine model diversity
  against that synthetic floor. **Fixed at the root:** all nine pre-1.76.0 bench compilations
  re-stamped with each model's REAL M5 return (preserved in the build record), `parser-free`
  re-synced, the control re-measured — the verdict stays NO EFFECT and becomes a cleaner null
  (UI delta 0.00). Bench verdicts unchanged (source files were always genuine; only the
  metadata was synthesized). Lesson: an audit rule adopted mid-program must be applied
  *backwards* to surviving artifacts, not just forwards.
- **MEDIUM — the "signal grew" framing leaned on an n=3 outlier.** guard-free-r2's higher
  variance (0.432) is dominated by one fresh Opus compilation of 450 non-blank LOC (its prior
  runs: 182, 220). The REDUCED verdict does not depend on it (controlled variance 0.170 is far
  below either baseline), but "grew" overstated what one outlier-sensitive sample supports —
  now stated as: the signal **survived** de-confounding; its exact size is n=3-noisy.
- **MEDIUM — "byte-matched scaffolding" was asserted with the mechanism outside the repo**,
  a step backward from v0.1's own hedge. The scaffold template is now a committed artifact
  (`controlled-language/PROMPT-TEMPLATE.md`) with its honest residual stated: historical prompts
  are not replayable; the template plus output fingerprints are what the repo can evidence.
- LOW — the generated reports' banner cites ADR-019 (the command's origin) for ADR-021
  experiments; noted, left as-is (the engine was deliberately untouched this milestone).
- **And one more, caught by the CI matrix itself (the py3.8 cells went red where local py3.13
  was green):** `controlled/c-haiku`'s EARS guard — shipped at 1.76.0 — declares "Python 3.8+"
  in its own constraints but uses a `tuple[bool, str]` function annotation, which is evaluated
  at definition time on 3.8 and crashes the guard on every input (0/23 there; 21/23 on ≥3.9).
  A **portability defect of that blind compilation, lying about its own compatibility claim**
  — latent since 1.76.0, exposed only when this release pinned the de-confounded verdict. The
  compiled artifact stays untouched (editing a blind compilation would fabricate the
  experiment); instead the pin now states the measured, version-dependent truth: the variance
  signal (−0.263) is identical on 3.8 and 3.13 and is the pin, while the verdict is REDUCED on
  ≥3.9 (the experiment's stated runtime) and MIXED on 3.8, where that one artifact is broken.
  The matrix cell is the instrument — this repo's oldest lesson, now measured against a
  compiled artifact's own claims.

`AC-CL2-01..04` measured green (T129 extended). Suite: 415 checks; acceptance **119/119** where
`coverage.py` is installed.
