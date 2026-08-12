# uscha-kit 1.72.0 — Diamond M2: the canonical package becomes a typed graph (2026-08-11)

M2 of the Diamond program. M1 proved the discovery loop closes on typed items; M2 asks
whether the WHOLE forward canonical package — ACCEPTANCE, the ADRs, CONSTITUTION's
invariants, goldens, and the ledger's curated observations — extracts deterministically into
one typed graph with stable IDs. The falsifiable thesis: extraction needs no LLM
interpretation. **It fails if typing a real statement requires guessing** — and that failure
would name exactly which authoring conventions the human layer is missing.

Run on this repo itself, the thesis **passes**: 107 nodes (79 AC, 15 DECISION, 12 INV, 1
GOLDEN), 71 edges, **UNTYPED rate 0.00**. Every acceptance criterion, every ADR, every
invariant typed without a guess. The zero is the result: the kit's own conventions fully
type its own package.

## `ir-extract` — subcommand 41

```bash
python qa_ledger.py ir-extract --repo <r>    # -> ir/IR.json + ir/IR.md
```

Emits a typed graph `{schema_version, nodes, edges, untyped, stats, _integrity}`, machine-
canonical, sealed, never hand-edited. Ten node types (`REQ INV AC CONTRACT DECISION NFR
GOLDEN OBS CURATION EVIDENCE`); edges derived only from references that already exist —
`DECISION->INV` (an ADR governing an invariant), `supersedes`, `REQ->AC`,
`OBS->CURATION`. **Native IDs are reused** (`AC-07`, `ADR-013`, `INV-CURATION-01`,
`OBS-xxxxxxxxxxxx`); only a node with nothing human to anchor to is content-addressed. A line
that fills a structural slot but cannot be typed deterministically lands in `untyped` with
its source — **visible, counted, never guessed**. The `UNTYPED` rate is a first-class metric,
printed every run: a rising rate on real input is the milestone reporting which conventions
are missing. `REQ`/`NFR`/`CONTRACT` have no deterministic source in this repo yet; their
absence is reported, never faked.

## `ir-render` — subcommand 42

Regenerates the human-readable `ir/IR.md` from the graph. `extract -> render -> extract` is
byte-stable for the structured parts: the Markdown stays canonical, the IR is a derived index
of it, and the round-trip proves no information the graph indexes was lost.

## `fidelity --ir` — the vector answered from the index

`fidelity --ir` computes `curation_closure` as a genuine **graph path query** — OBS nodes
that reach a CURATION node via an `OBS->CURATION` edge, over all OBS nodes — instead of the
v0 heuristic. On FIELD-RUN-001 it reproduces v0's number exactly (40/40 = 1.00), from the
graph rather than from re-reading the ledger. The schema is versioned (`0.1`) and expected to
be rewritten by M4; a loader that meets an unknown version refuses (`exit 2`) rather than
mis-reading it, and migrations are a design concern from day one.

## What the fresh review caught

One MEDIUM, fixed before shipping — the recurring "derived-but-unsealed" pattern, a third
time (evidence_class at 1.69, path at 1.70): the integrity seal covered `nodes/edges/untyped`
but left `stats` outside it, so a hand-edited summary (`stats.nodes = 999`) rendered a lie
above a truthful table while the strict loader passed the file clean. The seal now covers
`stats` too — a doctored summary is `exit 2`, regression-tested in AC-IR-05. Two LOWs also
closed: duplicate `REQ->AC` edges when an ADR cites the same AC twice (now set-deduped), and
an over-strong "reproduces v0" comment tightened to state the graph's honest denominator.

`AC-IR-01..06` measured green (T125). Suite: 411 checks; acceptance **85/85** where
`coverage.py` is installed.
