# uscha-kit 1.85.0 — the bench leaves its box: a JavaScript archetype passes the withheld oracle, a two-module archetype gives the IR its first edges, and the round trip gets its honest number (ADR-028, ADR-029, ADR-030)

## Why

Every claim this program has made about implementation replaceability — the bench verdicts, the
structural-distance metric, the static-surface extractor, the intra-model noise floor — was
narrated for exactly one language. Ten archetypes, ten Python compilations each, one AST module
(`ast`, stdlib) doing the structural work underneath `bench`, `bench-r2`, `lang-compare` and
reverse discovery alike. That is not "the method works" — it is "the method works in Python,"
and the difference had never been tested. This release adds the first non-Python archetype and
routes the four Python-only organs by file extension instead of widening the claim by assertion.

## The four Python-only points, routed by extension

- **The oracle runner.** `_run_oracle_case` fed every case to `python <impl>`. `_impl_interpreter`
  now resolves the interpreter by extension: `.py` unchanged (this same Python), `.js` resolves
  `node` from `PATH`. When the extension's runtime cannot be resolved, the function returns
  `None` and the caller reports the case `unmeasured` — never a fake red or green.
- **Structural metrics.** `_impl_metrics` routed everything through `ast.parse`. `.js` files now
  delegate to `_impl_metrics_js`, which measures LOC (non-blank, non-comment, a small `//`/`/*..*/`
  line state machine) and the lexical `require()`/`import` specifier set — both honestly narrower
  than the Python metrics; `ast_nodes`/`functions`/`classes` are `None`, not a narrated 0.
- **Structural distance.** `_struct_distance` averaged three dimensions (LOC delta, AST-node
  delta, import Jaccard distance) unconditionally. When either side's `ast_nodes` is `None`, it
  now drops to the two dimensions both sides actually have — stated in the docstring, not
  silently averaged against a phantom third number.
- **The static-surface extractor.** `_extract_static_py` walks Python's own `ast` for public
  signatures. `_extract_static_js` asks Node itself: a child-process one-liner requires the
  compiled module and reports `Object.keys(module.exports)` — the target runtime reporting its
  own public surface, not a regex parsing a language the engine cannot fully parse. Stub
  discovery in `bench` (`stubs = ... f.endswith((".py", ".js"))`) picks up JS stubs the same way.

## The honesty of the JS metric

No stdlib JS AST exists, and the engine does not invent one. That constraint is stated at every
layer that touches it: `_impl_metrics_js`'s docstring says the fingerprint is "honestly
NARROWER" than Python's; `_struct_distance`'s says a JS-involved pair "never mixes a Python
3-dimensional distance with a JS 2-dimensional one within a pair"; `_extract_static_js`'s says
the surface is "measured, not parsed by a heuristic." A JS entry never gets a fabricated third
dimension or a narrated function/class count — where the engine cannot see, it says so in the
data, not just the prose.

## The rate-limiter

The eleventh bench entry, and the first not in Python: a token-bucket rate limiter (allow/deny,
per-key buckets, tick-based refill, malformed-input rejection). The discrimination gate ran
first, as every entry requires: the degenerate stub and all **8 `wrong/` implementations** (each
breaking exactly one rule — bool-as-int, deny-consumes, float-accepted, negative-accepted,
no-clamp, starts-empty, tick-refills-one, unknown-event-ignored) go red on the withheld oracle
before any compilation was dispatched.

Three blind compilations (`c-opus`, `c-sonnet`, `c-haiku`) all validate against the pinned IR
with distinct, bounded `unresolved_intent`, and all three pass the withheld oracle **25/25**.
`bootstrap-variance` over the three confirms genuinely distinct implementations (no
byte-identical pair) — verdict **PASS**, the tenth Python-era verdict distribution (7 PASS, 3
PARTIAL) unaffected. `bench --fidelity` reports each compiler's own static surface as reported by
Node: opus 6 functions, sonnet 3, haiku 3 — visibly different surfaces behind the same passing
behaviour, the same lesson ADR-022 drew from Python compilers now reproduced in JavaScript.

## Node-absent, named

A JS entry with no `node` on `PATH` is not scored FAIL or PASS: `_run_oracle_case` returns
`unmeasured` with the reason `"node not on PATH"`; `_bench_oracle_all` propagates it when every
case in a compilation came back that way; `_bench_entry` reads it ahead of every other verdict
check and reports the entry **PENDING**, reason `"node not on PATH -- JS entry unmeasured"`.
Absence is measured and named, the same discipline `curation_closure` and the `r2/`-absent path
already carry — never a silent gap, never a fabricated verdict standing in for a runtime the
machine does not have.

## The bench gets its first structural edges (ADR-029)

Every one of the eleven archetypes above is one source unit, and every IR the bench has ever
produced has zero edges — edges appear only when a canonical package carries ADRs, and no bench
canonical did. So two things the program claims had never been measured: that `compile/0.1` (a
`source[]` list, a `trace_manifest[]` over units, per-unit sha256) actually holds when there is
more than one unit to trace — the bench read `src[0]` at four sites and would have silently
ignored units 2..N — and that a compiled system with internal structure, decided by an ADR that
lives in the canonical package, is still identifiable by a withheld oracle run through its entry
point.

`ledger-lite` is the answer: two source modules — `model.py` (a typed, append-only journal:
`post(entries) -> balance changes`, rejects unbalanced entries) and `cli.py` (the entry unit:
reads a JSON batch from stdin, imports `model`, prints `{balances, rejected}` or `ERROR`) —
joined by a committed seam decision, `docs/adr/ADR-001-model-cli-seam.md` (Accepted: the CLI
never computes balances, the model never touches I/O, the seam is `model.post`), that the IR
extractor turns into a DECISION node with edges to the INV it states and the ACs it references —
the bench's first IR with edges > 0 (1 DECISION node, 3 edges).

The four `src[0]` sites become "the entry unit": the unit named `cli.*` if present, else the
first `source[]` unit — declared and logged in the bench record as `entry_unit`. The oracle now
runs the entry unit with the compilation directory as `cwd` (and on the module path) so `import
model` resolves. Structural metrics and the static-surface extractor now run over **every**
source unit, not just the first, and are summed/concatenated per compilation. `compile-validate`
already checked every unit's sha; the bench now surfaces `units: N` per compilation.

All three blind compilations validate against the pinned IR, ship two sha-validated source units
each with both traced in the manifest, and pass the withheld oracle **24/24** — verdict **PASS**.
`bench --fidelity` reports the same `static_surface` (`main`, `post`) for every compiler, built
from both units together. Discrimination holds: the degenerate stub scores 1/24, and all seven
`wrong/` implementations read red — including `wrong/balance-in-cli` (moves balance arithmetic
into the CLI, breaking the model/CLI seam while leaving surface behaviour close) and
`wrong/ignores-model` (ignores the model unit entirely and reimplements the logic in the CLI).

## The round trip gets its honest number (ADR-030)

The diamond's promise is `discovery(forward(specs)) ≈ specs`. The forward half is measured (the
bench above). The reverse half is where the doctrine draws its hardest line: reverse discovery
produces FACTS, never a spec — `discover` emits typed, content-addressed observations, quarantined
until a human curates them (INV-CURATION-01); the IR (`ir-extract`) is derived only from the
canonical package's own documents, never from code. An "automatic round trip" that regenerated an
IR′ from a compilation and diffed it against the pinned IR would be exactly the narrated inference
the method forbids — the agent authoring a spec of a system it just wrote. So `bench-roundtrip`
(subcommand 51) does not do that. It measures something narrower and honest: for every bench
compilation, how much of the human-pinned IR the mechanical reverse organs the engine already has
can *anchor* — (a) static: an id literally referenced in a source unit's text or in a static
observation; (b) manifest: the compiler's validated `trace_manifest` maps the node to a unit that
exists; (c) behaviour: a withheld-oracle case whose name carries the AC id passes.

The first run of this instrument read `claimed_share` 1.000 on every entry, and that number meant
nothing: the manifest is what the compiler *claimed*, and the blind prompt handed it the node ids
to claim in the first place, so counting manifest footing as recovered is tautological by
construction. `recoverability` now counts ONLY static + behaviour footing; the manifest dimension
is reported apart as `claimed`, always `>= anchored`, and never counted as recovered — the split
this release makes explicit, in the code, the report header, and the docs.

The measured number: mean recoverability **0.062** across the bench's 12 entries. `ledger-lite` —
the multi-unit archetype above — is the bench's only entry with IR edges (3), and `bench-roundtrip`
reports `edges_recovered_mean` **0.33** for it. The behaviour dimension reads the literal string
`UNMEASURED` in 12 of 12 entries: no oracle case in the bench fixtures is tagged with an AC id
today, so the instrument names that absence instead of faking a zero or a pass — the honest next
step is tagging oracle cases per-AC, not this release. `DIAMOND-ROUNDTRIP.md` is the committed
report; it regenerates no IR file, ever — that constraint is asserted by the smoke suite (T136)
under a before/after file-tree snapshot of the bench directory.

## What changed, what didn't

`bench` now reports 12 entries; the eleven Python verdicts (the original ten plus `ledger-lite`,
itself PASS), `bench-r2`'s aggregate (10 measured, NOISY, signal 1 / noisy 5 / noise 4 — neither
`rate-limiter` nor `ledger-lite` has an `r2/` and neither ever enters "measured"), and
`lang-compare`'s scheduler-pair result (IMPROVED, variance 0.0195 → 0.1879) are byte-for-byte
what they were before this release — the refactor routes JS and multi-unit entries through new
organs, it does not touch the Python single-unit metrics path. `bench-roundtrip` is purely
additive: read-only over the bench fixtures, advisory, and no existing bench verdict changes.
`ACCEPTANCE.md` gains three new sections (`AC-JS-01`/`02`/`03`, T134; `AC-MU-01`/`02`/`03`, T135;
`AC-RT-01`/`02`/`03`, T136). Subcommand count is now 51.

## What the review caught

Every engine and fixture claim reproduced by execution: `bench-roundtrip` byte-identical to the
committed report (0.062, no IR file written), the static anchoring hand-traced to the exact
docstrings that mention ids, `_struct_distance` 2-dim verified by hand, node-absent → PENDING
reproduced, all 8 JS and 7 multi-unit wrong/ red, six lang-compare pairs and the bench
byte-identical, the seam edges present, blind protocol intact, py3.8 syntax clean, 422 · 147/147
reproduced. The catches were all **truth-pass on prose** — the place a measured program is
most tempted to over-state: (1) MEDIUM — the paper said the 83 curation verdicts / 8 fixes
came from "the first round"; the repo's own history says round one was the guard alone (17
observations, 1 fix) and 83/8 is the cumulative of two rounds; corrected to "across the first
two rounds". (2) MEDIUM — `site/llms.txt`, the crawler-facing truth-pass digest, still said
semantic round-trip "remains VISION" while the diamond page in the same commit moved it to
REAL (measured, bounded); llms.txt now states the bounded reality (0.062, behaviour UNMEASURED,
anchors names not semantics). (3) LOW — `DIAMOND-BENCH-R2.md` was stale against the 12-entry
bench (the two new entries appear as "(no r2)"); regenerated. (4) Unreproduced by the reviewer:
the paper's "nine of ten releases" review-catch count had no committed ledger behind the exact
number; softened to "in most releases — each catch is recorded in that release's changelog",
which is what the repo can actually show. Paper `.tex`/`.html`/`.pdf` regenerated and mirrored.

---

`AC-JS-01..03`, `AC-MU-01..03`, `AC-RT-01..03` measured green (T134, T135, T136 added). Suite: **422 checks · 0 fail**; acceptance **147/147** where `coverage.py` is installed. The engine gained one subcommand (`bench-roundtrip`, 51 total); every existing instrument's output over the eleven single-unit Python entries is byte-identical to 1.84.0.
