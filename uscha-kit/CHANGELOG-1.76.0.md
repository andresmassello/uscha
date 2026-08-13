# uscha-kit 1.76.0 — the controlled-language arm: does EARS+STE authoring compile more faithfully? (2026-08-13)

The deferred experimental variable from M4. The Diamond Bench (M5) measured *whether* a
canonical package regenerates the same system; this asks whether the **way it is authored**
changes how *consistently* independent models compile it. The claim that controlled language
helps is made constantly in requirements engineering — usually without a fidelity number
attached. This attaches one.

## `lang-compare` — subcommand 48

`qa_ledger.py lang-compare --free <arm-A> --controlled <arm-B>` compares two arms of the **same**
canonical package — arm A in free prose, arm B rewritten in **EARS** requirement templates under
**STE** authoring rules — each compiled blind by the same three models, both judged by **one
shared withheld oracle**. It measures, per arm, the oracle-green count, the mean oracle
pass-rate, the inter-compiler structural variance, and the `unresolved_intent` (count + a
specificity proxy), and emits the delta with a **computed, behaviour-first** verdict:
`REDUCED` / `MIXED` / `NO EFFECT` / `WORSE` — reduced variance with a behavioural regression
reads `MIXED`, never `REDUCED`. Deterministic, no LLM.

**The honesty guard is mechanical.** The two arms must share a byte-identical oracle —
`lang-compare` refuses (`exit 2`) if they differ. That holds *behaviour* fixed while only the
*authoring* changes: an EARS rewrite cannot quietly resolve a gap the free prose left silent,
because honouring a new decision would require changing the oracle. Where the free prose is
genuinely silent, both arms stay silent. The one judgement that remains human — that the two
canonical packages carry the *same semantic content* — is stated as a limitation, not hidden.

## The result: MIXED (and the independent review is why it isn't a false "REDUCED")

> The release candidate first reported this as a clean **REDUCED** (variance −51%, unresolved_intent
> −57%). The independent blind review caught two defects that inflated it, both fixed before this
> shipped: (a) the `unresolved_intent` −57% was an artifact of the fixture generator hard-coding
> two entries per controlled compilation instead of using the models' real returns (the true delta
> is ~0); (b) the verdict logic could label a run `REDUCED` while it *lost* behavioural fidelity —
> and this run did. `lang-compare` now reports mean oracle pass-rate and gates the verdict on it
> (behaviour-first), so a convergence-toward-worse reads as **MIXED**, never REDUCED. The honest
> result below is what survived that pass.

The subsystem is the INV-GOLDEN guard — the one Diamond Bench archetype with real inter-compiler
divergence (controlled language can only be shown to reduce variance where variance exists).
arm A is the guard's round-1 free-prose canonical (the one that produced the unanimous
interpreter S-gap); arm B is an EARS+STE rewrite of the *same* requirements, the interpreter
question left silent in both. Six blind compilations (Opus, Sonnet, Haiku × two arms), all
`compile-validate`d.

| Arm | Oracle-green | Mean pass-rate | Inter-compiler variance | unresolved_intent (count) |
|-----|--------------|----------------|-------------------------|---------------------------|
| free prose | 0/3 | 0.884 (61/69) | 0.347 | 4.67 |
| EARS + STE | 0/3 | **0.855 (59/69)** | **0.170** | 4.67 |

**Delta:** inter-compiler variance **−51%**, mean oracle pass-rate **−2.9%**, `unresolved_intent`
**±0**, oracle-green **+0**.

Read honestly, this is a **two-part, MIXED** result — and the honest version is the opposite of
tidy:

1. **Controlled authoring did reduce structural divergence.** The three EARS+STE guards converged
   on similar size and imports (variance 0.347 → 0.170, −51%) where the free-prose guards
   scattered. The compilers wrote **more alike**.
2. **But it did not reduce under-determination, and it cost a little fidelity.** The
   `unresolved_intent` count was **unchanged** (4.67 in both arms — the EARS compilers had exactly
   as many open questions, and actually cited *more* distinct requirement regions). And mean
   oracle pass-rate **regressed** 88.4% → 85.5%: the weakest compiler (Haiku), reading the EARS
   spec, wrote a guard that **over-blocks** — it blocks ordinary `rm scratch.txt` and
   `Write(notes.md)` calls that name no golden at all. The three compilers agreed *more*, on a
   *marginally worse* behaviour.

So the verdict is **MIXED**, not REDUCED: lower structural variance is **not** a win when it
converges toward a worse answer. EARS+STE made these compilers *agree more* without *guessing
less* or *behaving better* — for this subsystem, at this sample size. That is a more useful
finding than a clean "controlled language helps," and it is the finding the data actually
supports.

`CONTROLLED-LANGUAGE-REPORT.md` (generated, in-repo) carries the measured numbers and the verdict,
now including the per-arm mean pass-rate the behaviour-first verdict gates on.

## Scope and limitations (stated, not hidden)

- One subsystem, three models — a single data point; the verdict is scoped to "for this
  subsystem, at this sample size." A converged control archetype (`NO EFFECT` expected) is the
  first growth step, not built here.
- arm A reuses M4's round-1 compilations (verified byte-identical to the `bootstrap-golden-hook`
  fixtures). Their prompt scaffolding is close but not captured as an artifact, so a prompt-level
  confound cannot be fully ruled out from the repo — named, not waved away.
- `unresolved_intent` count is a weaker proxy than variance, and its rationale-length component
  is confounded by STE's terse register (a model mirrors terse authoring in its own text
  regardless of remaining ambiguity); the count is reported but not over-read.
- The free-prose baseline is reused verbatim from M4 and carries a garbled clause ("...only
  never"); part of arm A's disadvantage may be that authoring slip rather than "free prose" as a
  category.
- The two margins are asymmetric by design and are reporting choices, not derived constants:
  variance (a 3-component structural composite) uses 0.05, mean pass-rate (a direct behavioural
  fraction) uses the tighter 0.02 — behaviour is held to a stricter bar than structure, on the
  same facts-block-guesses-advise instinct. Neither value is anchored by a precedent elsewhere
  in the engine; both are printed with every verdict so a reader can re-judge the delta under
  their own margin.
- "Same semantic content" between the two canonical packages is a human judgement; the shared
  oracle enforces "same behaviour," not "same content."

`AC-CL-01..06` measured green (T129). Suite: 415 checks; acceptance **110/110** where
`coverage.py` is installed. In uscha mode: this milestone was built through the kit's own
`uscha-devloop` (ADR-first → build → smoke gate → adversarial review → human merge gate).
