---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
---
# ADR-015: The canonical package extracts into a typed graph (Uscha IR v0.1), Markdown stays canonical, and what cannot be typed is named UNTYPED

## Status: Accepted

## Context
Diamond M2. The forward canonical package — ACCEPTANCE (AC), the ADRs (DECISION + the
INVariants they govern), CONSTITUTION (INV), goldens, and the ledger's OBS/CURATION — lives
across several Markdown files and the JSON ledger. M1 proved the discovery loop closes on
typed items; M2 asks whether the WHOLE forward package can be deterministically extracted
into one typed graph with stable IDs, with zero information loss detectable by regenerating
the human views from the graph.

**Falsifiable thesis:** extraction is deterministic. **It fails if** typing a real statement
needs LLM interpretation — i.e. the Markdown conventions underdetermine the graph. That
failure is the finding: it names the authoring conventions the human layer is missing, and
those conventions (not a DSL) are the fix. So `UNTYPED` is not an error path, it is the
milestone's primary measurement.

Options considered for the ID scheme:
- **A) Content-address every node** (the OBS scheme, uniformly). Rejected: most canonical
  items ALREADY carry a stable human ID (`AC-07`, `ADR-013`, `INV-CURATION-01`). Hashing them
  would throw away the legibility the human layer exists to provide, and break the edges that
  reference those IDs by name.
- **B) Reuse the source's native ID where one exists; content-address only the ID-less.**
  **Chosen.** `AC-07`, `ADR-013`, `INV-CURATION-01`, `OBS-xxxxxxxxxxxx` stay themselves; a
  node with no native ID (a bare CONSTITUTION clause, an untyped line) gets
  `NODE-sha256(type + normalized_text + primary_source)[:12]`, the delta's scheme.

## Decision

**`qa_ledger.py ir-extract` emits `ir/IR.json`**: a typed graph `{schema_version: "0.1",
nodes: [...], edges: [...], untyped: [...], _integrity: <seal>}`, machine-canonical,
mechanically derived, never hand-edited (sealed with the delta's `_integrity_hash`).

- **Node types v0.1** (10, per the program): `REQ, INV, AC, CONTRACT, DECISION, NFR, GOLDEN,
  OBS, CURATION, EVIDENCE`. Each node: `{id, type, statement, source: {file, line}}`.
- **Edge types v0.1**, explicit and typed, each derived from an EXISTING reference — never
  inferred: `REQ->AC`, `AC->EVIDENCE` (a green tagged test in the ingested reports),
  `DECISION->INV` (an ADR's `governs:` / stated invariant), `OBS->CURATION`,
  `CURATION->canonical` (a promoted OBS's `derived_from`), `supersedes` (an ADR's explicit
  supersede text), `derived_from`. An edge whose endpoints do not both resolve is dropped and
  counted, never dangling.
- **Deterministic extraction only.** Sources and their typing rules: `ACCEPTANCE.md`
  checkbox + `AC-n` -> AC; `docs/adr/*.md` frontmatter `governs:` + `# ADR-NNN` title ->
  DECISION, its stated `INV-*` -> INV edges; `CONSTITUTION.md` `INV-*` headings -> INV;
  golden fixtures on disk -> GOLDEN; the ledger's `curation[]` -> CURATION and
  `candidate_delta`/`CANONICAL.json` -> OBS + EVIDENCE. A line that matches a structural slot
  but cannot be typed deterministically lands in `untyped[]` with its source — **visible,
  counted, never guessed.** REQ/NFR/CONTRACT have no deterministic source in this repo yet and
  are extracted only where a convention exists; their absence is reported, not faked.
- **Markdown stays canonical; the IR is an index.** `ir-render` regenerates a human view
  (a Markdown index of the graph) from `IR.json`; the structured parts round-trip
  content-stable (extract -> render -> extract yields the same graph).
- **`UNTYPED` rate is a first-class metric**, printed by `ir-extract` and carried in the
  graph. A rising rate on real input is the milestone reporting which conventions are missing.
- **Fidelity v1 recomputes over the graph.** `fidelity --ir` answers the same vector via
  graph reachability (path queries) instead of file heuristics; `unexplained_code` gains its
  denominator from graph reachability. It must reproduce v0's numbers on FIELD-RUN-001 within
  a documented tolerance — the graph is an index of the same facts, not a new opinion.
- **The schema is versioned and expected to change.** `schema_version` is mandatory; M4's
  findings will rewrite it, so a loader that meets an unknown version says so (exit 2) rather
  than mis-reading it. Migrations are a design concern from day one, not a retrofit.

## Reasons
- A typed graph is what M3's compiler contract consumes; prose and scattered files give it no
  addressable structure.
- Deterministic-or-UNTYPED keeps the whole milestone honest: the number of things the machine
  cannot type is the exact, measurable size of the gap between "what we wrote" and "what a
  machine can act on" — which is the Diamond thesis made countable.
- Reusing native IDs keeps the human layer legible and the edges nameable; content-addressing
  only the ID-less keeps stability where there is nothing human to anchor to.

## Consequences
+ The IR is the embryonic input to M3; M2 does not design M3's contract, only feeds it.
+ `UNTYPED` gives authoring feedback no linter can: it points at real statements the
  conventions underdetermine.
- v0.1 is deliberately minimal and WILL be rewritten by M4. Stated now, with the schema
  version and migration posture that makes the rewrite cheap.
- Fidelity v1 over the graph may diverge slightly from v0's heuristics; the tolerance is
  documented rather than the divergence hidden, and a divergence beyond tolerance is a finding
  about the graph, not a rounding excuse.

## Implementation Plan
- Engine: `ir-extract` (+ strict `_load_ir` with `exit 2` on unknown schema / malformed),
  `ir-render`, `fidelity --ir`; reuse `_obs_id`/`_delta_seal`/`_integrity_hash`, the
  `_parse_acceptance_items` and ADR `governs:` parsers that already exist.
- Tests: smoke T125+, criteria `AC-IR-01..06`, measured on a real fixture AND on the Uscha
  repo itself (the exit criterion is extraction from the real repo).
- Docs: this ADR, ACCEPTANCE `AC-IR-*`, CHANGELOG; the site/README stay VISION for everything
  past M1 until M4/M5 (T0 enforces the label).

## Verification
- [ ] `ir-extract` over a fixture emits a well-formed typed graph; every node carries
  id/type/source, every edge has resolvable endpoints (AC-IR-01)
- [ ] a statement that cannot be deterministically typed lands in `untyped[]` with its source
  and is counted in the printed UNTYPED rate; nothing is guessed (AC-IR-02)
- [ ] native IDs are reused (AC-07, ADR-013, INV-CURATION-01, OBS-*); only ID-less nodes are
  content-addressed, and re-extraction over unchanged sources is byte-identical (AC-IR-03)
- [ ] `ir-render` regenerates the human view; extract -> render -> extract is content-stable
  for the structured parts (AC-IR-04)
- [ ] an unknown `schema_version` or a malformed graph is `exit 2`, never mis-read (AC-IR-05)
- [ ] `fidelity --ir` reproduces v0's FIELD-RUN-001 vector within the documented tolerance
  (AC-IR-06)
