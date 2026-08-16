# uscha-kit 1.84.0 — the noise floor: same-model reruns differ about as much as different models, and the program's variance claims get their qualifier (ADR-027)

## The instrument (`bench-r2`)

Every variance number the program has published so far is **inter**-compiler: three different
models, one run each. That number is only interpretable against a floor nobody had measured —
how different are two runs of the SAME model on the SAME canonical package? A new subcommand,
`bench-r2` (49 → 50), answers it.

Each bench entry gains an optional `r2/` directory holding a second blind run (`c-opus`,
`c-sonnet`, `c-haiku` — the SAME models, the SAME canonical package, the SAME prompt scaffold,
a fresh blind dispatch in a later session). `r2/` carries no IR or oracle of its own: it is
measured against the entry's pinned IR and withheld oracle. `bench` treats every `c-*` directory
under an entry as a compilation, so `r2/` cannot live at that level without silently changing
every existing verdict (n 3→6, min-rate, PARTIAL floor) — it lives beside the entry instead, and
`bench` never scans into it, only top-level `c-*`. Existing verdicts are untouched by
construction, asserted by the suite (`AC-R2-01`).

`bench-r2` computes, per model with both a run 1 and a run 2, the **intra-model distance**
between the two runs with the SAME structural-distance function the bench uses BETWEEN
compilers (`_struct_distance` — LOC / AST-node / import-Jaccard mean, factored out of
`_lang_arm_metrics` unchanged in this release, then reused by both) — the ratio is only
meaningful because both sides are the same measurement. Per entry: `intra_mean` (mean of the
per-model distances) beside the entry's `inter` (the bench's own inter-compiler mean over run
1), the ratio `intra_over_inter`, and a computed class — `SIGNAL` below 0.5 (inter-compiler
variance is at least twice the noise floor), `NOISY` from 0.5 to 1.0, `NOISE` at or above 1.0
(same-model reruns differ as much as different models — that entry's inter-compiler number
carries no information). Each model run also reports `behaviour_stable`: whether the two runs
fail the exact same withheld-oracle cases. Entries without `r2/` report absent, never a false
zero. Writes `DIAMOND-BENCH-R2.md`; `--json` raw (`AC-R2-02`).

All 10 archetypes × 3 models = 30 fresh blind compilations, one second run each, dispatched
under the same blind protocol as every prior compilation in this program: subagents see only
the canonical package, Write-first, `unresolved_intent` stamped verbatim from each return,
artifacts never hand-edited. All 30 validate against their entry's IR; each
`unresolved_intent` has 2-6 entries and the three per entry are pairwise distinct (`AC-R2-03`).
Advisory throughout: no bench verdict changes anywhere in this release. The number is a
qualifier on the program's variance claims, published as such.

## The measurement

| Archetype | intra (mean) | inter | intra/inter | class |
|---|---|---|---|---|
| protocol-adapter | 0.0406 | 0.1401 | 0.290 | **SIGNAL** |
| guard | 0.2230 | 0.3472 | 0.642 | **NOISY** |
| transformer | 0.0639 | 0.0823 | 0.776 | **NOISY** |
| crud-store | 0.0866 | 0.1052 | 0.823 | **NOISY** |
| ui-render | 0.0617 | 0.0717 | 0.861 | **NOISY** |
| rest-handler | 0.1909 | 0.2058 | 0.928 | **NOISY** |
| state-machine | 0.0735 | 0.0657 | 1.119 | **NOISE** |
| parser | 0.0890 | 0.0787 | 1.131 | **NOISE** |
| worker | 0.0873 | 0.0588 | 1.485 | **NOISE** |
| scheduler | 0.0348 | 0.0195 | 1.785 | **NOISE** |

**Aggregate: 10 entries measured — SIGNAL 1, NOISY 5, NOISE 4, mean intra/inter 0.984.
Verdict: NOISY.** Behaviour is far more stable than structure: 26 of 30 reruns fail the exact
same withheld-oracle cases as their first run. The 4 that DIFFER (guard c-haiku 0.826→0.957,
guard c-opus 0.913→1.0, scheduler c-haiku 0.833→0.933, scheduler c-sonnet 0.867→0.9) all
*improved* on rerun — none regressed.

Read plainly: same-model reruns differ structurally about as much as different models do,
across this bench. A number this close to the noise floor is not evidence of nothing — but it
is not evidence of much on its own, either, and every entry now carries its own reading instead
of one aggregate standing in for all ten.

## What it does to prior claims

- **The scheduler's "convergence on a shared reading" narrative is retracted as a variance
  claim.** The free arm's inter-compiler distance (0.0195) sits BELOW that entry's own
  intra-model floor (0.0348) — two blind runs of the SAME model differ from each other more
  than the two free-arm compilers differed from one another. Low inter-compiler variance there
  was never evidence of a shared reading; it was inside the noise. What survives is the
  behavioural fact, which is not a variance claim: two compilers made the same `<` choice,
  visible verbatim in their own `unresolved_intent`, and the EARS rewrite moved one of them
  onto the oracle's resolution (oracle-green 1/3 → 2/3).
- **The guard's REDUCED (−61% inter-compiler variance) keeps signal, but the margin is thinner
  than the headline suggested.** Its r2 class is NOISY, not SIGNAL: inter 0.347 against an
  intra-model floor of 0.223, ratio 0.642 — real, but closer to the noise floor than a clean
  −61% implies standing alone.
- **The transformer's WORSE and the scheduler's IMPROVED both stand.** Neither rests on a
  variance number — both are read directly off the withheld oracle (an oracle-green lost, an
  oracle-green gained), and oracle deltas are exactly what `bench-r2` does not qualify.

No bench verdict, no engine verdict of any kind, changes in this release. `ACCEPTANCE.md` gains
a new section (`AC-R2-01`/`02`/`03`); `CONTROLLED-LANGUAGE-V03.md` gains an "r2 class" column
on its five-archetype table and a new section stating the three consequences above, plus a
rewritten opening to "Honest reading": structural variance alone no longer carries a claim in
this program — every variance-based statement now carries its r2 qualifier, and the
controlled-language conclusion is behaviour-first.

## What the review caught

Every number reproduced (the ten classes, the aggregate, 26/30, the byte-identity of `bench`
with and without `r2/`, the refactor's identity on all five lang-compare pairs, the six
surfaces, 419 · 138/138). Five findings, all fixed before release: (1) HIGH, interpretive —
the ratio was printed to 3 decimals as if point-precise, but `ast.walk` counts nodes
differently on 3.8 vs 3.13, so a ratio moves by up to ~0.26 across interpreters with no code
or model changing (scheduler 1.52 vs 1.79) — the classes were stable, the decimals were not;
the ratio now prints to 2 dp, the report footer and ADR-027 state the sensitivity and name
entries within ~0.25 of a threshold as borderline. (2) MEDIUM — the retraction lived in this
changelog and V03 but ADR-025, ADR-026 and the generated `CONTROLLED-LANGUAGE-SCHED.md`
still told the pre-retraction story with no pointer; ADR-025/026 now carry the supersession
note and the IMPROVED render text points readers at the noise floor. (3) MEDIUM — a silent
gap: an entry with `r2/` present but no parseable source ended with `class None, reason None`
(the exact "unnamed absence" the instrument exists to forbid); reproduced, fixed, pinned in
T133. (4) LOW — the aggregate tie rule (NOISE > NOISY > SIGNAL) was in the code, not the ADR;
now in ADR-027. (5) LOW — three untracked debug files at the repo root; removed. The reviewer
also confirmed the prose never over-reads NOISY as "models are interchangeable" — the
interpretation was calibrated; the presentation was not.

---

Suite: MEASURED — see the RESULTADO/ACCEPTANCE lines recorded at release.
