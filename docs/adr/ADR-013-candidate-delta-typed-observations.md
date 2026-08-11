---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/.claude/skills/uscha-reverse-discovery/SKILL.md
---
# ADR-013: Discovery emits a typed CANDIDATE-DELTA; verdicts become ledger objects (supersedes ADR-010's storage, keeps its invariant)

## Status: Accepted

## Context
Diamond M1: the loop (code → observations → human curation → canonical) cannot close on
prose. 1.64.0's curation shipped markdown candidates (`discovery/*.md`) and a markdown
verdict table (`BEHAVIOR-LEDGER.md`) — human-readable, measured, append-only. What that
representation cannot do: carry stable per-observation IDs, be diffed against the canonical
package, or feed a fidelity measurement. Narrative curates by the page; the loop needs items.

Options considered:
- **A) Coexistence** — both representations live. Rejected outright: two representations of
  the same truth is the disease this program treats.
- **B) Dry replacement** — delete 1.64.0's machinery, build fresh. Rejected: the gate, the
  append-only discipline and the `pr-ready` integration are proven; only the *storage* is
  outgrown.
- **C) Evolution with explicit supersede.** **Chosen.**

## Decision

**The machine-canonical form of discovery output is `discovery/CANDIDATE-DELTA.json`**:
typed observations (`behavior | invariant | contract | config | dependency |
decision_trace`), each with `statement`, `evidence_class`, `provenance` (files, derivation,
tool) and `canonical_match`. Mechanically derived, never hand-edited; a rendered
`CANDIDATE-DELTA.md` twin is generated for human reading, banner-marked, and detectably
overwritten on regeneration (the program invariant: the human layer stays Markdown, every
machine representation is derived).

**Evidence classes are strict** — the heart of the phase: `measured` (demonstrated by an
executed characterization/golden run the ledger ingested — only source: real execution),
`static` (deterministically extracted: routes, schemas, declared config, signatures — if
regex/AST cannot establish it, it is not static), `narrated` (agent-inferred; legitimate,
useful, and labeled). This supersedes 1.64.0's `test|code|inference` taxonomy by 1:1 mapping
(`test→measured, code→static, inference→narrated`) — the new words are the house doctrine's
own vocabulary.

**OBS IDs are content-addressed**: `OBS-` + `sha256(type + "\n" + normalized_statement +
"\n" + primary_provenance)[:12]`, normalization = lowercase + whitespace collapse.
Re-running discovery over unchanged code yields byte-identical IDs.

**Verdicts become engine objects.** `curate --obs <id> --verdict preserve|fix|undefined`
records `{obs_id, verdict, human, timestamp, note}` in `QA-LEDGER.json`, append-only
(re-curation supersedes, never deletes). **No batch-accept path exists, and the CLI asserts
its absence.** `promote` moves only `preserve` observations into the canonical package with
`derived_from` lineage; `fix` generates a work item in `ISSUES-DEFERRED.md` (the observed
house convention — no new tracker, no unrequested remote issues); `undefined` stays open and
visible in the readouts. Promotion over any uncurated OBS is a hard refusal naming the IDs.

**What survives from ADR-009/010 untouched**: INV-CURATION-01 (nothing promotes without a
human verdict, engine-measured, fail-closed), the three-verdict set, the append-only
philosophy, and the `pr-ready` block. For delta-flow repos the human **rendered view** of
verdicts is the `CANDIDATE-DELTA.md` twin (verdict column, regenerated per OBS);
`BEHAVIOR-LEDGER.md` stays the `.md`-candidate flow's source unchanged — regenerating it
from ledger objects would read as tampering to the very append-only check that guards it
(amended at implementation: the original "BL becomes a rendered view" wording collided with
`_bl_append_only`). What is superseded is ADR-010's *storage* decision only.

**Extractor scope v0: Python** — the repo's own fixture/golden inventory is Python, the
engine is Python, and the proof chain is shortest there. Every other stack reports
`UNSUPPORTED`, explicit, per house style. Do not build 11 extractors.

**Criteria namespace: `AC-DD-nn`** (delta discovery) — the handoff's `AC-RD-nn` collides
with the thirteen criteria already shipped under that prefix with different meanings.

## Reasons
- Items with stable IDs are what curation, diffing and fidelity all need; prose gives none.
- Superseding days-old storage now is cheap; migrating adopted users later is not — and the
  invariant (the part users depend on) does not move.
- Content-addressed IDs make "the same observation" a mechanical fact instead of a fuzzy
  match.

## Consequences
+ The delta's node/ID model is the embryonic IR (M2 consumes it; M1 does not design it).
+ Curation burden becomes measurable per-item (FIELD-RUN-001 records it — burden is data).
- 1.64.0's candidate/ledger format dies young. Accepted and stated; the alternative was
  maturing a format the loop cannot use.
- The rendered twin can drift from the JSON between regenerations; the regeneration test and
  the generated-file banner are the mitigation, not a proof.

## Implementation Plan
- Engine: `discover` (orchestrates ingest of measured evidence + static extractors; the
  SKILL supplies narrated observations — the engine classifies and stores, it never calls an
  LLM), `curate`, `promote`; delta loader with strict shape (`exit 2` on malformed);
  renderer for the `.md` twin.
- Skill: `uscha-reverse-discovery` evolves again — candidates phase emits the delta,
  curation phase drives `curate` per-OBS.
- Tests: smoke T123+, criteria `AC-DD-01..06`, `AC-CU-01..06` per the M1 handoff (renamed).

## Verification
- [ ] discovery over a fixture emits well-formed delta; every OBS carries id/type/class/provenance (AC-DD-01)
- [ ] inference-only statement → `narrated`, never `static`/`measured` (AC-DD-02)
- [ ] ingested characterization run → `measured`, run timestamp in provenance (AC-DD-03)
- [ ] unchanged fixture → byte-identical OBS IDs (AC-DD-04)
- [ ] canonical_match populated when a match exists, null otherwise (AC-DD-05)
- [ ] rendered twin regenerates; hand edits detectably overwritten (AC-DD-06)
- [ ] promote over one uncurated OBS → refusal naming it; ledger unchanged (AC-CU-01)
- [ ] preserve → promoted with `derived_from`; fix → ISSUES-DEFERRED entry, never canonical;
  undefined → open in readouts; re-curation supersedes without deleting; no batch-accept
  path exists (AC-CU-02..06)
