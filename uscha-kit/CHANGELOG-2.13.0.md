# uscha-kit 2.13.0 — a design with state and rules is model-checked before it is built, and the decision to model or not is written down (ADR-059)

## What changed

In 2.11.0 a TLA+ model of the gated-finding debt found three holes neither the code nor a fresh
reviewer had seen; in 2.12.0 the next feature with state was not modelled and nothing showed the
absence. This release makes the step impossible to forget in THIS repo. It is repo-level: the kit
package ships nothing new (a later ADR promotes the rule into the kit once a second real case
exists).

- **Repo rule 12 (`CLAUDE.md`).** Every ADR numbered 059 or higher declares `model: required`
  (with `model_manifest:`) or `model: not-needed -- <reason>`; written by the agent, the latter is
  an `(origin: agent)` item until the human confirms it. ADRs 001-058 are not retrofitted.
- **`tools/model-check.py check`** (no Java; smoke T176 on all six cells) refuses an ADR >= 059
  without the field, a `required` one without a well-formed manifest, a manifest without a `ci`
  config or without a vacuity config (an invariant that MUST break), and a replayed AC id that
  `ACCEPTANCE.md` or the smoke suite does not carry. A deep run recorded against an older `.tla`
  or `.cfg` is an advisory.
- **`tools/model-check.py run --tier ci|deep`** runs a manifest's configs with TLC v1.7.4, after
  checking the jar against its pinned sha256, and compares each verdict with `expect`; a mismatch
  prints the trace's first lines, and a `ci` config over 60 s (or past 120 s) is red, named.
- **The CI `models` job** (one ubuntu runner, Temurin 21, the jar cached by its sha256) runs the
  `ci` tier inside the smoke workflow, so a red model is a red run and `publish.yml` refuses the
  tag.
- **GatedDebt (2.11.0) is the first manifest** (`docs/gate-integrity/models/models.json`): six `ci`
  configs at MaxLog=4 (1-25 s each) -- the shipped design (no error), the vacuity control, and four
  teeth configs that MUST break, each naming the RED case that replays it (AC-GI-50/51, -52, -64,
  -65) -- and six `deep` configs at MaxLog=5 with their recorded results. The model gained
  `DeferFix` and `MemoryFix` so the fixes TLC forced are named in it.

## Closed before release (fresh review)

A fresh reviewer found six real ways around the first cut, each reproduced; all are fixed and
pinned in T176. A manifest named by `model_manifest:` outside `docs/<feature>/models/` passed the
check but was never run (AC-MC-03). ADR files named `ADR-061.md`, `ADR-1000-x.md` or `adr-0600-x.md`
skipped the rule, and a stray file in `docs/adr/` was ignored (AC-MC-01). A manifest could be valid
and say nothing: only the vacuity config in CI, a `no-error` config checking only `TypeOK`, a
counterexample that replays no AC id, or a vacuity "broken" in the initial state (AC-MC-03, -05). A
replayed id matched prose, a comment, or a longer id (AC-MC-04). `publish.yml`'s fallback path (no
smoke run for the tag) never ran TLC; it now does, with the same pin (AC-MC-08). And TLC's exit code
was ignored, a semantic error's cause was cut from the trace, `violated:X` never matched,
`not-neededforsure` passed as a reason, a duplicate `model:` won silently, and the deep-run hash
covered the `.tla` but not its `.cfg` (AC-MC-02, -05, -07).

## Found while building it

Reverting the deferral-closure fix ALONE is not a violation at MaxLog=4: the Memory fix already
refuses that path. The engine keeps both rules (defense in depth; AC-GI-64 pins the closure
message), and the teeth config for AC-GI-64 reverts both, saying why.

## Honest limits

- A green model proves that TLC found no violation OF THE MODEL at its declared bounds. It does not
  prove the engine matches the model; the RED cases each config replays are the only link.
- The `ci` tier is bounded (MaxLog=4); the deep tier is run by hand and only recorded.
- The suite measures `run`'s logic with a stub TLC; the real TLC verdicts are measured by the CI
  `models` job, not by the suite's acceptance count.

## How it is pinned

`AC-MC-01..08` (smoke T176), each red against a deliberately broken `model-check.py` before it
counted.

## Evidence

Suite: 467 checks · 0 fail; acceptance 448/449.
