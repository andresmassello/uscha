---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
---
# ADR-019: The controlled-language arm — the same canonical package in free prose vs EARS+STE, judged by the same withheld oracle; the language is demonstrated or discarded by the delta, never decreed (Diamond controlled-language v0.1)

## Status: Accepted

## Context
The deferred experimental variable from M4 (bootstrap) step 6. The Diamond Bench (M5) showed
that independent models regenerate the same bounded system from a canonical package — but the
one archetype with real divergence (the INV-GOLDEN guard, `PARTIAL`) diverged because its
**free-prose** canonical package left a requirement under-determined. The natural next question:
does the **way** a canonical package is authored change how faithfully it compiles? If a
controlled authoring discipline reduces the variance between independent compilers, that is a
concrete, measurable lever on regeneration fidelity — and the canonical human layer stays
Markdown, just written under rules.

**Falsifiable thesis:** rewriting a canonical package's requirements in **EARS** templates under
**STE** authoring rules — the *same semantic content*, controlled *form* — measurably reduces
inter-compiler variance and/or `unresolved_intent` versus free prose, when the same models
compile both arms and the same withheld oracle judges both. **It fails, and controlled language
is discarded for this case,** if the deltas are within noise. **Both outcomes are publishable
results** — "controlled authoring reduced compiler variance by X%" and "did not measurably help"
are equally reportable; the language is demonstrated or discarded by the data, never decreed.

**The controlled vocabulary, bounded so this is not hand-waving:**
- **EARS** (Easy Approach to Requirements Syntax) — every requirement is one of five templates:
  *ubiquitous* ("The `<system>` shall `<response>`"), *event-driven* ("When `<trigger>`, the
  `<system>` shall `<response>`"), *state-driven* ("While `<state>`, the `<system>` shall
  `<response>`"), *unwanted-behaviour* ("If `<condition>`, then the `<system>` shall
  `<response>`"), *optional-feature*. Each requirement names its trigger/condition/state
  explicitly — the templates surface the very conditionals free prose leaves implicit.
- **STE** (Simplified Technical English) — one instruction per sentence, active voice, a
  controlled vocabulary, no ambiguous pronouns, no synonyms for the same concept.

**The honesty tension (the crux this ADR must pin down).** EARS is powerful precisely because
its templates *force you to state conditions*. That creates a trap: an EARS rewrite could
quietly **add content** the free prose never decided (e.g. resolve the guard's interpreter
S-gap), and then a lower variance would be an artifact of a richer spec, not of the language.
Options:
- **A) Let arm-B resolve whatever EARS surfaces.** Rejected: it confounds *authoring discipline*
  with *added requirements*; the two arms would target different behaviour and the comparison
  would be apples-to-oranges.
- **B) arm-B re-EXPRESSES the same content; the withheld oracle is IDENTICAL across arms, and is
  the mechanical check that no behaviour was added.** **Chosen.** arm-B may make an
  *ambiguously-stated* requirement *unambiguous* (same decision, clearer form); it may **not**
  decide a requirement the free prose left genuinely silent. The shared oracle enforces this: if
  arm-B smuggled in a new decision, honouring it would require changing the oracle — which is
  forbidden. Where free prose is truly silent (the interpreter question), **both** arms stay
  silent, and that S-gap persists in both. The experiment then measures exactly what it claims:
  does clearer *expression of the same requirements* reduce compiler variance?

## Decision

**Subsystem: the INV-GOLDEN guard** — the only bench archetype with real inter-compiler
divergence. Controlled language can only be shown to reduce variance where variance exists; on
an already-converged archetype (parser/state-machine/transformer, 3/3 oracle-green) there is
nothing to reduce, so the guard is the honest choice for v0.1. arm-A (**free prose**) is the
guard's existing round-1 canonical package (`bootstrap-golden-hook/canonical/`, the one that
produced the unanimous interpreter S-gap). arm-B (**controlled**) is an EARS+STE rewrite of the
*same* requirements, authored under the constraint above.

**The two arms share one withheld oracle** — the guard's existing `ORACLE.json`, authored before
any of this, unchanged. Same behavioural target, only the authoring differs.

**Both arms are compiled blind by the same three models** (Opus, Sonnet, Haiku); each compiler
sees exactly one arm's canonical package and nothing else — six compilations, all
`compile-validate`d against each arm's pinned IR.

**The new organ — `qa_ledger.py lang-compare`** (subcommand 48). Deterministic, no LLM. Given
the two arms (each an archetype dir with its canonical package, pinned IR, the shared oracle, and
≥3 compilations), for **each arm** it runs `bootstrap-oracle` (green count across the compilers)
and `bootstrap-variance` (inter-implementation LOC/AST/import divergence), and reads
`unresolved_intent` from each compilation (count, and a specificity proxy: distinct `ir_region`s
cited and mean rationale length). It then emits the **delta** (controlled − free) on three
measured axes:
- **oracle green rate** — did controlled authoring make more compilers reconstruct the exact
  system?
- **inter-compiler variance** — mean pairwise structural distance; lower under controlled = the
  thesis's core signal.
- **`unresolved_intent`** — count and specificity; fewer/less-diffuse under controlled = the
  compilers had less to guess.

`lang-compare` writes `CONTROLLED-LANGUAGE-REPORT.md` with the per-arm numbers and the deltas,
and prints the **honest verdict read from the deltas**. The verdict is **behaviour-first** (the
M4 convergence lesson: lower variance toward a *worse* answer is not a win). A **behavioural
regression** is a lost all-green OR a drop in mean oracle **pass-rate** beyond a pass-rate margin
— so `lang-compare` measures and reports the per-arm mean pass-rate, not just the binary
all-green count, and gates on it:
- `REDUCED` — variance measurably lower AND no behavioural regression;
- `MIXED` — variance measurably lower BUT behaviour regressed (agreed more, on a worse answer);
- `WORSE` — variance higher, or behaviour regressed without a variance gain;
- `NO EFFECT` — within the margins.
The verdict is *computed*, never asserted; a null result and a MIXED result are both first-class
outputs, not failures.

**The oracle-identity invariant is enforced, not trusted.** `lang-compare` refuses to compare
two arms whose oracle files differ (by content hash): the whole experiment rests on the two arms
targeting the *same* behaviour, so a differing oracle is a mechanical error, not a configuration.

## Reasons
- A measurable authoring lever on regeneration fidelity is exactly the kind of result the
  program exists to produce — and controlled language is a claim the requirements-engineering
  world makes constantly *without* a fidelity number attached. Attaching one is the contribution.
- Sharing one withheld oracle across both arms is what makes the comparison honest: it turns
  "controlled language feels clearer" into "controlled language changed the compiler variance by
  a measured amount, with behaviour held fixed."
- Choosing the guard (where variance exists) over a converged archetype avoids a rigged null:
  the experiment is given a real chance to show an effect, and a null there is informative.

## Consequences
+ Either result publishes: a reduction is a concrete lever; a null retires a popular intuition
  with evidence. The program's "report the boundary" ethos applies to its own methods.
+ `lang-compare` generalises: any future archetype can be run through both arms to add a data
  point — the controlled-language claim grows the same way the bench does.
- One archetype, three models, is a single data point on a small subsystem; the ADR says so, and
  the verdict is scoped to "for this subsystem, at this sample size." A control archetype
  (already-converged, expected `NO EFFECT`) is named as the first growth step, not built in v0.1.
- Authoring both arms is the canonical author's job (here, me acting as author); the honesty
  constraint (re-express, don't re-content) is enforced by the shared oracle, but the *judgement*
  of "same content" is human — stated as a limitation, not hidden.

## Implementation Plan
- Engine: `lang-compare` subcommand — per-arm oracle + variance + unresolved_intent metrics, the
  delta, the oracle-identity refusal, the behaviour-first `REDUCED/MIXED/NO EFFECT/WORSE`
  verdict, `CONTROLLED-LANGUAGE-REPORT.md` writer. Reuse `_bench_oracle_all`, `_impl_metrics`,
  `_load_ir_at`, `_validate_compilation` unchanged; the engine calls no model.
- Fixtures: `uscha-kit/tests/fixtures/controlled-language/` with `free/` (the guard's round-1
  canonical, its pinned IR, the shared oracle, three blind compilations) and `controlled/` (the
  EARS+STE rewrite, its pinned IR, the *same* oracle by content, three blind compilations).
- Tests: smoke T129, criteria `AC-CL-01..06`; the oracle-identity refusal and the verdict logic
  are regression-tested on committed fixtures plus crafted margin cases.
- Docs: this ADR, ACCEPTANCE `AC-CL-*`, CHANGELOG, SYSTEM-FACTS (subcommand count 47→48). The
  site's controlled-language claim stays absent until the report earns it — a null result is
  reported as a null, never quietly dropped.

## Verification
- [ ] `lang-compare` over the two committed arms emits `CONTROLLED-LANGUAGE-REPORT.md` with
  per-arm oracle/variance/unresolved_intent and the three deltas; every number traces to a run
  (AC-CL-01)
- [ ] the oracle-identity invariant holds: two arms with differing oracle files are refused
  (`exit 2`), naming the mismatch — the comparison is apples-to-apples by construction (AC-CL-02)
- [ ] both arms' three compilations `compile-validate` against their pinned IR; no compiler input
  references the oracle (the maker≠checker wall holds across both arms) (AC-CL-03)
- [ ] the verdict is behaviour-first and computed from the deltas: reduced variance WITH a
  behavioural regression (a lost all-green or a mean pass-rate drop) is `MIXED`, never `REDUCED`;
  a zero delta is `NO EFFECT` — the regression cannot be masked as a win (AC-CL-04)
- [ ] the `unresolved_intent` specificity proxy is deterministic and per-arm (distinct
  `ir_region`s + mean rationale length), reproducible across runs (AC-CL-05)
- [ ] the reference guard passes the shared oracle unchanged, and arm-B's IR differs from arm-A's
  (the authoring changed) while the oracle is byte-identical (behaviour held fixed) (AC-CL-06)
