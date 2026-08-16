---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/tests/fixtures/diamond-bench/*/
---
# ADR-029: The bench leaves the single file — a multi-unit archetype with real IR edges, the compilation contract exercised over N source units, and the oracle run through the entry unit (bench-multi v0.1)

## Status: Accepted

## Context
Every one of the eleven bench archetypes is one source unit; every IR has zero edges (edges
appear only when a canonical package carries ADRs, and no bench canonical does). So two
things the program claims have never been measured: that `compile/0.1` (a `source[]` list, a
`trace_manifest[]` over units, per-unit sha256, unexplained-code by construction) actually
holds when there is more than one unit to trace — the bench reads `src[0]` at four sites and
would silently ignore units 2..N — and that a compiled system with internal structure
(module A depends on module B, decided by an ADR that lives in the canonical package) is
still identifiable by a withheld oracle run through its entry point.

## Decision
- **Archetype `ledger-lite`** — a two-module system with a decided seam: `source/model.py`
  (a typed, append-only journal: `post(entries) -> balance changes`, rejects unbalanced
  entries) and `source/cli.py` (the entry unit: reads a JSON batch of postings from stdin,
  imports `model`, prints `{balances, rejected}` or `ERROR`). The canonical package carries
  **`docs/adr/ADR-001-model-cli-seam.md`** (Accepted: the CLI never computes balances; the
  model never touches I/O; the seam is `model.post`) which the IR extractor turns into a
  DECISION node with edges to the INV it states and the ACs it references — the bench's first
  IR with edges > 0. The compiler must emit **two** source units and a manifest that maps
  nodes to units (the seam decision maps to both).
- **Engine, minimal and explicit** — the four `src[0]` sites become "the entry unit": the
  entry unit is the one named `cli.*` if present, else the first `source[]` unit (declared,
  logged in the bench record as `entry_unit`); the oracle runs the entry unit with the
  compilation directory on the module path (cwd = the compilation's `source/` parent, and
  `PYTHONPATH`/`NODE_PATH` = that dir) so `import model` resolves. Structural metrics
  (`_impl_metrics`) and the static surface run over **every** source unit and are summed /
  concatenated per compilation (fidelity `static_surface` lists names from all units;
  `unexplained_share` finally has something to count). `compile-validate` already checks
  every unit's sha; the bench now surfaces `units: N` per compilation.
- **Withheld oracle** (≥20 cases): balanced/unbalanced batches, multi-account, rejection
  isolation (a bad posting rejects only itself, others post), zero-amount, duplicate ids,
  malformed. Discrimination: stub + `wrong/` including one that puts balance logic in the CLI
  (breaks the seam but passes behaviour? — no: a wrong that computes balances wrongly in the
  CLI while the model is right shows up in the oracle) and one that ignores the second unit.
- **Blind protocol unchanged**, but the prompt scaffold's `<TARGET-PATH>` slot becomes a
  two-file instruction (write both files, return both units in `source[]` and both in the
  manifest). PROMPT-TEMPLATE.md gains that variant, committed.
- Python entries with one unit: byte-identical outputs (asserted).

## Reasons
- `compile/0.1` was designed for N units and has only ever seen N=1; a contract that has
  never been exercised beyond its trivial case is a narrated contract.
- An IR with zero edges cannot test the diamond's structural half; the seam ADR gives the
  extractor real edges to trace and the compiler a decision to honour.

## Consequences
+ The bench gains its first multi-unit, edge-carrying entry; the trace manifest and
  unexplained-code dimensions become measurable in earnest.
+ E2 (round-trip) becomes possible: it needs exactly this — an IR with edges to reverse into.
- Four engine sites change from `src[0]` to entry-unit selection; asserted byte-identical for
  every existing single-unit entry.

## Verification
- [ ] Every existing entry's `bench`, `bench --fidelity`, `bench-r2`, `lang-compare` outputs
  are byte-identical before/after (AC-MU-01)
- [ ] `ledger-lite`: IR has ≥ 1 DECISION node and ≥ 2 edges; each blind compilation carries 2
  source units, both sha-validated, both in the manifest; the oracle runs through `cli` and
  the verdict is computed and pinned; the fidelity descriptor lists names from both units
  and `entry_unit` is recorded (AC-MU-02)
- [ ] Discrimination: stub red, every `wrong/` red — including the one that ignores the second
  unit and the one that mis-computes in the CLI (AC-MU-03)
