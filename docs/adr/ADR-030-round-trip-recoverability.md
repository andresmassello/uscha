---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
---
# ADR-030: The round trip, honestly bounded — reverse discovery over each compiled artifact yields FACTS, and the instrument measures how much of the pinned IR those facts can anchor; it never regenerates an IR from code (round-trip v0.1)

## Status: Accepted

## Context
The diamond's promise is `discovery(forward(specs)) ≈ specs`. The forward half is measured
(bench: 12 archetypes, withheld oracles). The reverse half is where the doctrine draws its
hardest line: **reverse discovery produces facts, never a spec** — `discover` emits typed,
content-addressed observations (static / measured / narrated), quarantined until a human
curates them (INV-CURATION-01); the IR (`ir-extract`) is derived ONLY from the canonical
package's documents, never from code. An "automatic round trip" that regenerated IR′ from a
compilation and diffed it against IR would be exactly the narrated inference the method
forbids: the agent authoring a spec of a system it just wrote.

What CAN be measured without crossing that line: for a compiled artifact, run the same
mechanical reverse organs the program already has (static extraction; the withheld oracle as
measured behaviour), and ask, per IR node, whether the facts recovered from the code **anchor**
it — the same `canonical_match` `discover` already computes between an observation's statement
and canonical ids. That is a coverage number over the pinned IR, computed from facts, with the
human's judgment left where it belongs.

## Decision
- **New subcommand `bench-roundtrip`** (50 → 51): for every bench entry and every compilation,
  builds the reverse fact set the M1/M4 organs already produce — (a) static observations from
  every source unit (`_static_surface_for`, py or js), (b) the trace-manifest claims the
  compiler made per unit (already validated), (c) the withheld-oracle case results as measured
  behaviour — and computes, per IR node: `anchored_static` (a static observation's statement or
  provenance names the node id or the node's statement's key terms — reuse `_match_canonical`
  verbatim), `anchored_manifest` (the compilation's manifest maps the node to a unit that
  exists), `anchored_behaviour` (for AC nodes: ≥1 oracle case whose name or payload tag
  references the AC id passes; entries whose oracles do not tag cases report UNMEASURED for
  this dimension — absence named). Per compilation: `recoverability = anchored_nodes /
  ir_nodes` with the three dimensions reported separately; per entry the mean over
  compilations; edges: `edges_recovered = edges whose BOTH endpoints are anchored`. Advisory:
  no bench verdict changes.
- **What it is NOT** (stated in the report header, the ADR and the docs): it does not produce
  an IR′, it does not diff specs, it does not infer requirements from code. It measures how
  much of the human-authored IR the mechanical reverse organs can find footing for in the
  compiled artifact. Where a node is unanchored, the report names it — that is the diamond's
  honest gap list, per compiler, not a regenerated spec.
- **Written report `DIAMOND-ROUNDTRIP.md`** with the per-entry table (ir_nodes, edges,
  recoverability mean, edges_recovered, unanchored nodes listed) and the aggregate.
- Zero change to any existing verdict or output; asserted byte-identical.

## Reasons
- Closing the diamond loop mechanically is the program's headline; doing it by inference would
  poison the one layer no other tool has (the human curation gate). Bounding it to fact
  anchoring keeps the claim true and the doctrine intact.
- The reverse organs exist and are measured; the only new thing is the join against the IR —
  small, deterministic, and it names its own UNMEASURED.

## Consequences
+ The program gains a per-compiler recoverability number and a per-node gap list — the
  round trip becomes a measurement with a stated ceiling instead of a promise.
+ Multi-unit entries (E1) finally exercise edge recovery.
- The number will be modest (static facts anchor names, not semantics; behaviour anchoring
  needs tagged oracle cases, which the 1.85.0 oracles lacked → UNMEASURED there; closed in
  1.90.0, see the amendment below). That was the honest state of reverse discovery, published
  as such.

## Verification
- [ ] `bench-roundtrip` runs over the whole bench; every existing instrument's output is
  byte-identical before/after; the report header states what the instrument does NOT do
  (AC-RT-01)
- [ ] Per compilation: `recoverability` ∈ [0,1] with the three anchoring dimensions reported
  separately, behaviour dimension UNMEASURED where oracle cases carry no AC tag; per entry the
  unanchored node ids are listed; edges_recovered ≤ edges; ledger-lite reports edges > 0 and
  edges_recovered computed (AC-RT-02)
- [ ] The aggregate and per-entry numbers are pinned over the committed fixtures,
  interpreter-stable; no IR′ file is ever written (AC-RT-03)

## Amended 1.90.0 — the behaviour dimension is measured, because the oracles were tagged

The consequence above said the number would be modest "because today's oracles mostly lack
tagged cases → UNMEASURED there". That was a **named absence with a stated next step**, and
this amendment is that step taken — not a change of definition to make a number look better.

**What changed.** A case's tags are now read from two places, unioned: the ids literally
referenced in the case **`name`** (unchanged, the original source) and a curated **`ac`** list
on the case — `{"name": "create-read", "ac": ["AC-CS-01", "AC-CS-02"], ...}`. The mapping is
**human-curated**, with its provenance and per-case rationale committed beside the fixtures in
`uscha-kit/tests/fixtures/diamond-bench/ORACLE-TAGS-CURATED.json` (201 of 216 cases tagged; the
untagged ones are the cases no single criterion owns). Nothing else about a case moved:
**`payload`, `raw_stdin` and every `expected_*` are untouched**, so tagging cannot change what a
case measures — only what the id map says it measures. A case still anchors a node only by
**passing**; a tagged case that fails anchors nothing (AC-RT-04 measures exactly that).

**One spelling for one id.** The three footings read ids from three places that punctuate them
differently — an IR node keeps the human's padding (`AC-DD-07`), a source comment or a curated
tag may write `AC-DD-7` or `AC_DD_07`. The behaviour comparison is therefore made on **ADR-036's
own normal form** (`_ac_tag_ids`: family + integer, separator and zero padding dropped), applied
to **both sides** and **only** to that comparison — `per_node["id"]`, the static footing and the
manifest footing keep the IR's spelling, so no report changes shape. Reusing ADR-036's grammar
rather than writing a second one is deliberate: two grammars for one id is the drift the
normalisation exists to prevent.

**What it moved.** Mean recoverability over the 12 bench entries goes from **0.062** (static
footing alone) to **0.828**, with the behaviour dimension **measured in 12/12** entries and
`ledger-lite`'s `edges_recovered_mean` from 0.33 to 1.00. `DIAMOND-ROUNDTRIP.md` is regenerated
from the measured run, and its closing sentence about the behaviour dimension is now **derived
from the aggregate** instead of asserted — it used to end "which today is every entry", a
hardcoded claim inside a generated document, which is precisely where such a claim rots unseen.
Still advisory: **no bench verdict changes** (AC-RT-01 re-pins all twelve).

**Judging must not modify what is judged.** Running cases in this instrument made a latent
hazard reachable: a multi-unit compilation imports its sibling module, so executing it wrote
`__pycache__/*.pyc` into the bench tree — and AC-RT-01's own promise is that a run regenerates
nothing there. Measured on a clean tree, three `.pyc` files appeared; in the suite an earlier
`bench` block had already warmed the cache, so the red would have waited for a fresh CI clone.
The judged program's environment now carries `PYTHONDONTWRITEBYTECODE=1` (alongside the
coverage start-up hooks it already drops), and a clean-tree run leaves nothing behind.

**How the aggregate is pinned.** As a **range**, never a float. The twelve per-entry means are
interpreter-stable and pinned exactly, but they sum to 9.930 and `9.930 / 12` is 0.8275 — a
rounding boundary that lands on 0.828 under python 3.13 and 0.827 under 3.8. A float pin there
would be a red about IEEE754, not about the round trip.

**The honest reading.** What changed is what the instrument can **attribute**, not what the
compiled artifacts **do**. The compilations are byte-identical to the ones that scored 0.062;
the reverse organs are the same. An absence that was named is allowed to be closed, and the
release says which of the two numbers moved and why — the alternative, quietly publishing 0.828
as though the reverse half had improved, is the narrated fix this ADR exists to refuse.
