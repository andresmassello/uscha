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
  needs tagged oracle cases, which today's oracles mostly lack → UNMEASURED there). That is the
  honest state of reverse discovery, published as such.

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
