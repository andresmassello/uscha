# uscha-kit 1.99.0 — the bench meets a stranger: a second VENDOR compiles all 12 archetypes blind, and finds the ambiguity three relatives had agreed on (ADR-042) (2026-09-04)

No behaviour change a consumer project will notice. This release is a measurement the program
had been promising to make and had not made: **every blind compilation in the Diamond Bench came
from one vendor.** Haiku, Sonnet and Opus are three models of the Claude family — same trainer,
same lineage, same post-training — so three of them agreeing on how to read a spec is weaker
evidence than it looks. The repo said so on six pages: *"one vendor; cross-vendor not yet
measured."*

Now it is measured. The same 12 archetypes, the same canonical packages, the same withheld
oracles, compiled blind by **OpenAI Codex** (`gpt-5.5` via `codex-cli 0.142.5`).

**The claim survived, and the arm found something.**

## What changed

### A fourth compiler, from a second vendor

`tools/bench-compile-codex.py` dispatches through the Codex CLI and stages the result as a
`c-codex/` compilation. Every rule the Claude arms were held to holds here — blind by
construction (empty temp workspace outside the repo, canonical package inlined in the prompt,
oracle never rendered, mechanical leak audit on both sides), judged only by the engine's own
`compile-validate`, and **first result stands** (ADR-020): nothing was re-dispatched to get a
greener number.

One rule is new, and it is not cosmetic. `compile-ingest` content-addresses an unresolved-intent
record on `(ir_region + decision)`, so a compiler that invents its own region slugs would fork
that address space between arms forever. The prompt now lists the entry's IR node ids and
requires each `ir_region` to be one of them. Compliance: **48 of 48**.

**22 dispatches, 22 promoted, 0 refused, 0 shell commands executed, 801 s.**

### The result

| Archetype | codex | haiku | opus | sonnet | before | after |
|---|---|---|---|---|---|---|
| crud-store | 12/12 | 12/12 | 12/12 | 12/12 | PASS | PASS |
| guard | 20/23 | 19/23 | 21/23 | 21/23 | PARTIAL | PARTIAL |
| ledger-lite | 24/24 | 24/24 | 24/24 | 24/24 | PASS | PASS |
| parser | 21/21 | 21/21 | 21/21 | 21/21 | PASS | PASS |
| protocol-adapter | 15/15 | 15/15 | 15/15 | 15/15 | PASS | PASS |
| rate-limiter | 25/25 | 25/25 | 25/25 | 25/25 | PASS | PASS |
| rest-handler | **15/15** | 14/15 | 14/15 | 15/15 | PARTIAL | PARTIAL |
| scheduler | **30/30** | 25/30 | 30/30 | 26/30 | PARTIAL | PARTIAL |
| state-machine | 12/12 | 12/12 | 12/12 | 12/12 | PASS | PASS |
| transformer | **13/14** | 14/14 | 14/14 | 14/14 | PASS | **PARTIAL** |
| ui-render | 13/13 | 13/13 | 13/13 | 13/13 | PASS | PASS |
| worker | 12/12 | 12/12 | 12/12 | 12/12 | PASS | PASS |

**8 PASS · 4 PARTIAL** (was 9 · 3). The stranger validates on all twelve, beats the Claude arms
on two entries, and loses exactly one case.

### That one case is the whole point

`transformer`. The canonical SPEC says the input is *"a JSON array of records, each an object
with **exactly** the fields `first`, `last`, and `age`"* — then lists the error cases without
ever saying an **extra** field is one of them, while the out-of-scope section says *"No other
fields are read or preserved."* The package is genuinely ambiguous. The oracle resolved it one
way. Codex resolved it the other, and **said so before it was judged**:

> `AC-TR-05` — *"Reject records with extra fields in addition to first, last, and age. The
> contract says each input record is an object with exactly those fields, so additional keys are
> treated as malformed rather than ignored."*

Then it reproduced that reading in a **second, independent blind run**. Not a flake — a stable
reading of an under-specified sentence.

Three Claude models had converged on the other reading. That is what a single-vendor bench
cannot see: not a model defect, but a **hole in the canonical package** hidden by the fact that
every compiler looking at it was a relative of the others.

It is also the second time this repo has found that exact sentence. The controlled-language
experiment recorded in 1.83 that `transformer` read *WORSE* under EARS+STE because *"the rewrite
sharpened a latent ambiguity (`exactly the fields`) into a commitment the oracle rejects."* Two
unrelated instruments, sixteen releases apart, landed on the same clause.

### `--write-mode return`, stated rather than hidden

The release machine's administrator policy removes `never` from `allowed_approval_policies`, so
`codex exec` falls back to `on-request` and fails every file write. Defeating a security control
to make a benchmark run is not a method, so the arm runs in `return` mode: the model returns the
source inside its JSON and the harness writes the bytes. Every compilation records
`backend.write_mode` so nobody mistakes one arm's mechanics for the other's.

The obvious objection — *a return-mode arm is a weaker agent than one that writes its own files*
— is answered by the measurement: **`shell_commands_executed` is 0 across all 22 dispatches**,
and nothing was read outside the workspace. Codex never ran its own code either. Both arms are
one-shot generators judged by a withheld oracle, which is what the bench measures. The asymmetry
that **remains** is Codex's own ~15k-token system prompt, which the Claude arms never carried;
it is listed as UNMEASURED rather than argued away.

### Five entries got their run contract from the SPEC, not from Opus

The contract handed to each entry is normally lifted verbatim from that entry's `c-opus`
constraints, so both arms compile against the same thing. For five entries those "constraints"
turned out to be post-hoc narration of Opus's implementation — *"`isinstance(v, bool)` is tested
BEFORE `isinstance(v, str)`"*, *"cycle detection is iterative (explicit stack, DFS coloring)"*.
Handing those to a second vendor hands it **one arm's design decisions**, which makes the second
arm a transcription rather than an independent compilation.

Those five now carry a two-line contract derived from their own `SPEC.md` (stack and file
layout, plus the I/O and exit contract the SPEC already fixes — nothing a compiler has to
decide). `tools/codex-arm/slots.json` records `source` **per entry**, so the asymmetry is
inspectable instead of buried.

### Numbers that moved because a fourth arm exists

- **The anonymised model map re-lettered**: `{codex: M1, haiku: M2, opus: M3, sonnet: M4}`. It is
  built over sorted model names, so every letter shifted. Pinned exactly, because a silent
  re-lettering would make every published `M<n>` claim wrong.
- **The noise floor softened**: SIGNAL/NOISY/NOISE went 1/5/4 → **1/7/2**, mean intra/inter
  0.98 → **0.82**, behaviour-stable reruns 26/30 → **36/40**. `parser` and `state-machine` left
  NOISE — a compiler from another vendor widened the inter-compiler spread more than it raised
  the intra-model floor. Both landed within ~0.3 of the threshold (parser 0.73, state-machine
  0.81), which ADR-027 says to read as
  borderline, so the **classes** are pinned and the ratios are not.
- **Round-trip recoverability**: 0.828 → **0.815**, six per-entry means moved. The published
  0.828 moved with it on **eight surfaces**: the six pages the vendor claim also touches
  (README, `site/llms.txt`, the diamond pair, the how pair) plus both language twins of the
  Claude Code deck, whose `bench-roundtrip` row states it too — and their two build copies
  under `site/docs/`, regenerated by `site/sync-docs.sh`. It is a hand-maintained number the
  facts writer does not recognise, so every one of them is a human edit and was one release
  away from being a narrated claim.
- **`ledger-lite`'s `edges_recovered_mean` went 1.00 → 0.75**, and the move is the useful kind:
  the field is the mean COUNT of edges recovered per compilation, not a ratio. Only `c-opus`
  anchors both endpoints of all three edges and the other arms anchor none, so the value is
  3/N — which printed as 1.00 at N = 3 and read like *"all edges, always"*. It never was. The
  fourth arm makes N = 4 and the same 3 prints 0.75. The instrument did not change; the arm made
  an ambiguity in the number visible, and `AC-RT-02` now pins it with that reading spelled out.
- The cross-vendor arm is the **most rerun-stable compiler in the bench**: behaviour-stable on
  all ten second runs, including the two entries where it does not score 100%.

### The claim on the site changed, in both languages

Six pages stop saying the arm is missing and say what it found — including the unflattering part,
that the fourth compiler moved an entry from PASS to PARTIAL. `tools/narrated-claims.txt` gains
**entry 7**: the first label in that file retired by being **answered** rather than rewritten,
which is the outcome the 1.98.0 doctrine exists to produce. `T154` asserts the old phrases stay
gone; the new `T157` asserts the replacements are present, in both twins.

The **paper is deliberately not touched**. Its numbers are dated at 1.96.0 and it is revised in
its own round; asserting a phrase into a document nobody has rewritten yet is the same narrated
claim pointed the other way.

## What stays UNMEASURED

Stated plainly, because an arm that overclaims is worse than no arm:

1. **One model of the second vendor** (`gpt-5.5`; `gpt-5.6-*` is refused by this CLI version).
   Nothing here measures a vendor.
2. **n = 2 runs**, on 10 of 12 entries. A floor, not a distribution.
3. **Two vendors of many.** A falsification test the claim survived, not a survey.
4. **The system-prompt asymmetry**, not removable from outside the vendor's CLI.
5. **`tool` mode not run** — the machine policy forbids it.
6. **`ledger-lite` and `rate-limiter` have no second round for any compiler.** They joined the
   bench after ADR-027's second round. A codex-only `r2/` there would print one model's rerun
   against four models' spread in the same column as the ten. Named absent, never half-measured.

## Verification

New criteria family **`AC-XV-01..07`**, measured by smoke **T157**: the arm validates like every
other (and every `ir_region` is a real IR node); no oracle reached it on either side, with the
committed prompt hashes **re-derived** rather than trusted; the bench reports it in all twelve
with the verdicts pinned as measured; a non-validating compilation is a **named refusal**,
measured on the real function with a corrupted fixture and no dispatch at all; it has its own
noise floor; the backend is on the record inside every compilation; and the published claim
matches the committed fixture in both languages.

Re-pinned from the measured run, each with its reason in a comment: `AC-DB-04`, `AC-BG-03`,
`AC-SH-02`, `AC-R2-01`, `AC-R2-02`, `AC-R2-03`, `AC-JS-01`, `AC-JS-02`, `AC-JS-03`, `AC-MU-01`,
`AC-MU-02`, `AC-RT-01`, `AC-RT-02`, `AC-RT-03`, and the three `WANT_VERDICT` maps in
T134/T135/T136.

`AC-XV-02` and `AC-XV-04` read `tools/bench-compile-codex.py`, which lives at the repo root and
is not shipped inside the kit — from an extracted kit they report **UNMEASURED**, never a silent
pass.

Suite: __SUITE__ checks · 0 fail; acceptance __ACC__.
