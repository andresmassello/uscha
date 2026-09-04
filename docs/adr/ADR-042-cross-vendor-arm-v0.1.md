---
governs:
  - tools/bench-compile-codex.py
  - tools/codex-arm/slots.json
  - uscha-kit/tests/fixtures/diamond-bench/*/c-codex/
  - uscha-kit/tests/fixtures/diamond-bench/*/r2/c-codex/
  - uscha-kit/tests/fixtures/diamond-bench/CODEX-ARM-RUN.json
---
# ADR-042: The cross-vendor arm — a SECOND vendor compiles the whole bench, blind, under the same withheld oracles (cross-vendor v0.1)

## Status: Accepted (1.99.0)

## Context

The Diamond program's central claim is **implementation replaceability**: independent blind
compilations of one canonical package regenerate the same system, and a withheld oracle
certifies it. ADR-017/018 built the instrument, ADR-020 grew it to twelve archetypes, ADR-028
took it out of Python and ADR-029 out of the single file.

Through all of that, every blind compilation came from **one vendor**. Haiku, Sonnet and Opus
are three models of the Claude family — same trainer, same tokenizer lineage, same
post-training. So a reader was entitled to ask a question the bench could not answer: is
regeneration fidelity a property of **the method**, or a property of **that family**? Three
models converging on the same reading of a spec is weaker evidence than it looks if they
converge because they are relatives.

The repo said so, out loud, on six pages: *"one vendor; cross-vendor not yet measured."*
`tools/narrated-claims.txt` even carried that label in its header as one of the two VISION
claims that were **correct today and must survive** — until an arm measured it.

This ADR is that arm.

## What this falsifies, and what it cannot

A cross-vendor arm is a **falsification test**, not a survey. If a second vendor's compilations
had failed broadly, the replaceability claim would have been shown to be family-shaped and the
program would have had to say so. They did not fail, so the claim survives one attempt to break
it — which is all a single arm can ever do.

It cannot become a claim about "LLMs in general". n=1 model of the second vendor, n=2 runs, 2
vendors out of many. The ADR is careful to state the arm as evidence *against a specific
alternative explanation*, never as evidence *for* generalization.

## Decision

### The protocol is ADR-017's, with the vendor swapped

`tools/bench-compile-codex.py` dispatches through the OpenAI Codex CLI (`codex-cli 0.142.5`,
model `gpt-5.5`, reasoning effort `high`) and stages the result as a `c-codex/` compilation.
Everything the Claude arms were held to, this arm is held to:

- **Blind by construction, not by asking.** The working directory is an EMPTY temp dir outside
  the repo; the canonical package is inlined in the prompt and never touches that disk; the
  oracle is never rendered; a mechanical leak audit re-checks prompt and output on the way out.
- **Isolated context.** `--ignore-user-config` stops `config.toml` from loading and *nothing
  else* — an `AGENTS.md`, a memory store or a skills directory in the real `CODEX_HOME` would
  still be in play. So the run gets a synthetic `CODEX_HOME` holding **only `auth.json`**, and
  the isolation is asserted at CREATION rather than assumed. The assertion is narrower than
  it sounds and is stated as such: the CLI populates that home during the first dispatch
  (`config.toml`, `skills/.system`, `plugins/cache`, a sqlite file), so it is not an
  invariant held across the run. What the CLI writes there was inspected by hand and holds
  no user `AGENTS.md`, memory or rules file — a MANUAL check today, not a measured one,
  and named here rather than left to read as mechanical.
- **The engine judges, the script never does.** Every staged compilation goes through
  `qa_ledger.py compile-validate`. A refused one is staged as `x-codex-REFUSED/`, which the
  bench's `c-*` discovery cannot see: a bad run cannot quietly become evidence.
- **First result stands** (ADR-020). No compilation was re-dispatched to obtain a greener one.

### `--write-mode return`, and why

The machine's administrator policy (`C:/ProgramData/OpenAI/Codex/requirements.toml`) removes
`never` from `allowed_approval_policies`. `codex exec` therefore falls back to `on-request` and
fails **every** file write with *"file change approval is not supported in exec mode"* — the
model cannot create a file at all.

Two options, and only one of them is honest. Bypassing an administrator's security policy to
make a benchmark run is not a research method. So the arm runs in `return` mode: the model
returns the complete source **inside its JSON** and the harness writes the bytes. The deviation
is recorded in `compilation_report.backend.write_mode` on every compilation, so no reader can
mistake one arm's mechanics for the other's.

**What this removes.** The obvious objection to a `return`-mode arm is that it is a weaker
agent than the Claude arms, which wrote their own files. The measurement answers it:
`shell_commands_executed` is **0** across all 22 dispatches, and `files_read_outside_workspace`
is empty. Codex never ran its own code either. The "one arm could execute, the other could not"
confound does not exist in practice — both arms are one-shot generators judged by a withheld
oracle, which is exactly what the bench measures.

**What this keeps.** Codex carries its own ~15k-token system prompt, which the Claude arms never
had (measured: ~17k input tokens per entry against a prompt of 3.6–8.6 KB). That asymmetry is
real, is not removable from outside the vendor's CLI, and is listed under UNMEASURED below.

A maintainer who relaxes the machine policy can re-run in `tool` mode; the fixture is designed
so a re-run **replaces `c-codex/` wholesale** rather than accumulating beside it.

### Slot provenance: five entries' worth of honesty

The run contract handed to each entry is lifted verbatim from that entry's `c-opus`
`implementation_constraints`, so both arms compile against the same constraints (ADR-021
scaffolding parity).

For **five** entries — `crud-store`, `protocol-adapter`, `rest-handler`, `ui-render`, `worker` —
those constraints turned out to be *post-hoc narration of that implementation* rather than a run
contract. They say things like *"`isinstance(v, bool)` is tested BEFORE `isinstance(v, str)`"*
and *"cycle detection is iterative (explicit stack, DFS coloring)"*. Handing those to a second
vendor would hand it **one arm's design decisions**, and an arm given another arm's design is
not an independent compilation of the canonical package — it is a transcription of it.

So those five carry `source: "canonical"` in `tools/codex-arm/slots.json`: a two-line contract
authored from the entry's own `SPEC.md` `## Contract` section — the stack and file layout (the
one fact the SPEC does not state, because the canonical package is stack-agnostic by
construction) plus the I/O and exit contract the SPEC already fixes. Nothing in it is a design
choice; it is the same information the oracle harness needs to run the unit at all. The
provenance is recorded **per entry**, so the asymmetry is inspectable rather than buried. The
other seven already carried genuine one-line run contracts and keep
`source: "c-opus constraints"`.

### `ir_region` is constrained to IR node ids

`compile-ingest` content-addresses a UINT on `(ir_region + decision)`. A compiler that invents
its own region slugs makes two arms' report of the **same** intent gap two different gaps,
forever. The prompt therefore lists the entry's IR node ids and requires each `ir_region` to be
one of them. Compliance was 100%: 48 `unresolved_intent` entries across 12 compilations, every
`ir_region` a real node.

## What is measured

Round 1 wrote `c-codex/` for all 12 entries. Round 2 wrote `r2/c-codex/` for the 10 entries that
already carried an `r2/`. **22 dispatches, 22 promoted, 0 refused, 0 shell commands, 801 s of
wall clock, 19–63 s per entry.**

### The bench

| Archetype | codex | haiku | opus | sonnet | verdict before | after |
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

**8 PASS · 4 PARTIAL** (was 9 · 3). All four compilations are pairwise distinct in every entry.

### The one finding, and why it is the point

`transformer` is the only verdict that moved, and it moved because of a single oracle case:
`extra-field-tolerated`. The canonical SPEC says the input is *"a JSON array of records, each an
object with **exactly** the fields `first`, `last`, and `age`"* — and then lists the error cases
without ever saying an **extra** field is one of them, while the out-of-scope section says *"No
other fields are read or preserved"*. The package is genuinely ambiguous. The oracle resolved it
one way. Codex resolved it the other, **declared that exact reading in its `unresolved_intent`
before the oracle judged it**:

> `AC-TR-05` — *"Reject records with extra fields in addition to first, last, and age. The
> contract says each input record is an object with exactly those fields, so additional keys are
> treated as malformed rather than ignored."*

and **reproduced it in a second, independent blind run** (13/14 in both, behaviour-stable).

This is the machinery working exactly as designed. The compiler named the freedom it took; the
withheld oracle disagreed; the bench recorded a PARTIAL. The failure is not a defect in the
compiler — it is an **under-specification in the canonical package** that three related models
happened to resolve identically, which is precisely the blind spot a single-vendor bench cannot
see.

It also **corroborates an earlier, independent finding from the other direction**: the
controlled-language experiment (1.83, ADR-019/024) recorded that `transformer` read *WORSE*
under EARS+STE because *"the rewrite sharpened a latent ambiguity (`exactly the fields`) into a
commitment the oracle rejects."* Two unrelated instruments, sixteen releases apart in
design, found the same sentence.

### The noise floor (`bench-r2`)

| | before | after |
|---|---|---|
| SIGNAL / NOISY / NOISE | 1 / 5 / 4 | 1 / **7** / **2** |
| mean intra/inter | 0.98 | **0.82** |
| behaviour-stable reruns | 26 / 30 | **36 / 40** |
| entries measured | 10 | 10 |

Two entries left NOISE: `parser` 1.13 → 0.73 and `state-machine` 1.12 → 0.81. Both moved
**toward signal**, and for the same mechanical reason: a fourth compiler from a different vendor
widened the *inter*-compiler spread more than it raised the intra-model floor. The ADR-027
reading softens accordingly — with a two-vendor compiler set, fewer archetypes are dominated by
sampling noise. Both moves land within ~0.3 of the threshold — parser 0.73, state-machine 0.81 — which ADR-027 says to read as
borderline; the **classes** are pinned, the ratios are not.

The arm's own reruns were behaviour-stable on **all ten** entries — including its
`transformer` 13/14 and its `guard` 20/23. It is the most rerun-stable compiler in the bench.

### Round-trip recoverability

Mean **0.828 → 0.815**. Six per-entry means moved (guard, ledger-lite, rate-limiter,
rest-handler, transformer, ui-render), all slightly down; six did not. An entry's recoverability
is the mean over its compilations, and the cross-vendor arm anchors a slightly different subset
of each IR than the three Claude arms converge on — which is the same effect the variance
instruments report, seen through the reverse organs.

`ledger-lite`'s `edges_recovered_mean` moved 1.00 → 0.75, and the move is worth naming because
the old number read better than it was. The field is the mean COUNT of edges recovered per
compilation, not a ratio: only `c-opus` anchors both endpoints of all three edges and the other
arms anchor none, so the value is 3/N. At N = 3 that printed as 1.00, which looked like "all
edges, always" and never was. The fourth compiler recovers 0 and makes N = 4, so the same 3 now
prints 0.75. Nothing about the instrument changed; the arm made an existing ambiguity in the
number visible. AC-RT-02 now pins 0.75 with that reading spelled out.

### `lang-compare` is untouched

It runs over `tests/fixtures/controlled-language/`, a separate tree. Verified unchanged:
`IMPROVED`, free 0.0195, controlled 0.1879.

## What stays UNMEASURED

Stated plainly, because an arm that overclaims is worse than no arm:

1. **One model of the second vendor.** `gpt-5.5` only. `gpt-5.6-*` is refused by this CLI
   version ("requires a newer version of Codex", HTTP 400). Nothing here measures a vendor.
2. **n = 2 runs**, on 10 of 12 entries. A floor, not a distribution — ADR-027's own caveat.
3. **Two vendors of many.** This is a falsification test that the claim survived, not a survey.
4. **The system-prompt asymmetry.** Codex carries its own ~15k-token system prompt the Claude
   arms never had. Not removable from outside the vendor's CLI.
5. **`tool` mode not run.** The machine policy forbids it; `return` is what was measured.
6. **`ledger-lite` and `rate-limiter` have no second round for any compiler.** They joined the
   bench after ADR-027's second round. A codex-only `r2/` there would report *one model's rerun
   against four models' spread* under the same column as the ten — a different quantity, printed
   as if it were the same one. Named absent (asserted by AC-JS-01), never half-measured.
7. **The paper is not revised here.** Its numbers are dated at 1.96.0 and it is revised in its
   own round; asserting a phrase into a document nobody has rewritten yet is the same narrated
   claim pointed the other way.

## Consequences

- **The anonymised model map re-lettered.** It is built over the sorted model names, so `codex`
  takes `M1` and haiku/opus/sonnet each shift one letter: `{codex: M1, haiku: M2, opus: M3,
  sonnet: M4}`. Every published `M<n>` claim had to be re-read; AC-DB-04 pins the map exactly so
  a future silent re-lettering is a red, not a surprise.
- **One bench verdict moved** (`transformer` PASS → PARTIAL) and the headline count moved
  9 · 3 → 8 · 4. The published claim on six pages says so, in both languages.
- **Two r2 classes moved** out of NOISE; the r2 aggregate and mean moved with them.
- **The round-trip mean moved** 0.828 → 0.815.
- **The suite grew by ~33% in child processes.** Every full-fixture pass now runs a fourth
  compilation through every oracle case of every entry.
- **`tools/narrated-claims.txt` gained entry 7** — the first row retired by being **answered**
  rather than rewritten, which is the outcome the 1.98.0 doctrine exists to produce.
- **A new criteria family, `AC-XV-01..07`**, measured by smoke **T157**. AC-XV-02 and AC-XV-04
  read `tools/bench-compile-codex.py`, which lives at the repo root and is not shipped inside
  the kit: from an extracted kit they report `None` = UNMEASURED, never a silent pass.
- **The prompt hashes are re-derivable.** `CODEX-ARM-RUN.json` carries a sha256 per prompt and
  no prompt bytes — a prompt is the canonical package (committed beside it) plus the run
  contract in `slots.json`, so storing the bytes would put a second copy of the canonical
  package in the repo, which is how two copies start to differ. T157 re-renders all twelve and
  compares.

## Alternatives considered

- **Bypass the machine's approval policy to get `tool` mode.** Rejected: defeating an
  administrator's security control to make a benchmark run is not a method, and the measurement
  shows the confound it would have removed does not exist (0 commands executed).
- **Hand the five residual entries their `c-opus` constraints anyway.** Rejected: it would make
  the second arm a transcription of the first on exactly the entries where the first arm's
  constraints encode its own design.
- **Drop those five from the arm.** Rejected: a 7-entry arm chosen by which entries were
  convenient is a selected result. All 12 ran.
- **Give `ledger-lite` and `rate-limiter` a codex-only `r2/`.** Rejected, see UNMEASURED 6.
- **Let `ir_region` stay free text.** Rejected: it would permanently fork the UINT address space
  between arms.
