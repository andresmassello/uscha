---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
---
# ADR-020: The Diamond Bench grows from 4 to 9 archetypes; concurrency enters as specified deterministic semantics, and every new oracle must prove discrimination against a plausible-wrong implementation before any compilation runs (Diamond Bench v0.2)

## Status: Accepted

## Context
The Diamond Bench (ADR-018, v0.1) answered the generalization question with four entries:
guard `PARTIAL`, parser / state-machine / transformer `PASS`. The handoff's full design names
8–12 archetypes; the missing families are the ones whose absence most limits the claim — a
request-driven service, a stateful store, a concurrent worker, a UI, a protocol adapter. v0.2
adds five entries, taking the table to nine. No new engine mechanism is needed — `bench` was
built to grow by adding entries — so this milestone is **authoring + compilation volume**, plus
two hard problems the ADR must settle honestly.

**Problem 1 — deterministic oracling of "hard" archetypes.** The bench's oracle contract is
`stdin → stdout/exit`, deterministic, no LLM. A REST service, a CRUD+DB system and a concurrent
worker are not naturally that shape. Options:
- **A) Real infrastructure** (sockets, a real DB, real threads). Rejected: non-deterministic,
  environment-dependent, and the oracle stops being a measured fact.
- **B) Bounded, sequence-driven semantics.** **Chosen.** Each hard archetype is specified as a
  bounded system that consumes a JSON **sequence of events/requests/operations** on stdin and
  emits a deterministic result: the *logic* of the archetype, freed of its transport. A REST
  handler processes a request sequence against in-memory state; a CRUD store processes an
  operation sequence; a worker processes a job set under **specified scheduling semantics**.
- For **concurrency specifically**: the canonical package specifies a deterministic scheduler
  (priority order with explicit tie-breaking) — concurrency as *specified semantics*, not real
  parallelism. **Stated plainly: this tests the archetype's coordination logic (priorities,
  dependencies, failure isolation), not true parallel execution.** Oracling real parallelism
  deterministically is out of scope and named as a boundary of the bench, exactly the honest
  "map of where the thesis holds" ADR-018 promised.

**Problem 2 — oracle quality.** 1.75.1's lesson: a stub-only discrimination check is not
enough; two v0.1 oracles passed plausible-wrong implementations. For v0.2 the lesson becomes a
**pre-compilation gate**: every new oracle must, before any compiler runs, (a) reject the
degenerate stub AND (b) reject at least one hand-written **plausible-wrong** implementation
that violates a SPEC-named sharp edge. Only then is the entry opened for compilation.

## Decision

**Five new entries under `uscha-kit/tests/fixtures/diamond-bench/`, each a distinct archetype
absent from v0.1:**
1. `rest-handler` — an in-memory HTTP-style API: stdin is a JSON array of requests
   `{method, path, body}` over a small resource collection; stdout is the JSON array of
   responses `{status, body}`. Routing, status codes (200/201/404/400/405), state across the
   sequence. Archetype: **request-driven service (REST-shaped, transport-free).**
2. `crud-store` — a keyed record store: stdin is a JSON array of operations
   (`create/read/update/delete/list`), with uniqueness and missing-key errors specified;
   stdout is the array of per-operation results. Archetype: **CRUD + storage semantics.**
3. `worker` — a job scheduler: stdin is a JSON object `{jobs: [{id, priority, needs: [...]}]}`;
   the system emits the deterministic execution order (priority desc, FIFO on ties, dependencies
   first, cycle → error) and per-job status, failures isolating their dependents. Archetype:
   **concurrent worker as specified deterministic scheduling semantics** (the stated boundary).
4. `ui-render` — a form/view state machine: stdin is an initial model + a JSON array of UI
   events (input, toggle, submit, reset); stdout is the final rendered view as structured text
   (a deterministic, specified rendering). Archetype: **small UI (model-view logic,
   presentation-free).**
5. `protocol-adapter` — a bidirectional translator between a line-oriented wire format and a
   JSON message shape, with framing and malformed-frame errors. Archetype: **protocol adapter /
   codec.**

**Authoring order is the maker≠checker order, per entry:** canonical package (SPEC + AC +
CONSTITUTION, the only compiler input) → pinned IR (`ir-extract`) → **withheld oracle authored
next, before any compilation** → the discrimination gate (stub + plausible-wrong both red) →
only then the 3 blind compilations (Opus, Sonnet, Haiku), stamped verbatim from each model's
real return — **never synthesized** (the 1.76.0 lesson, now a rule of the bench's process).

**Engine impact: none by design.** `bench` already handles N entries, `PENDING`, verdicts and
anonymization. The smoke's T128 pins `entries == 4`; it moves to asserting the count matches
the committed entry set (9) and its per-archetype assertions extend to one new entry as a
representative; the discrimination evidence for all five new oracles is captured in the T128
sidecar (each entry's committed stub must stay red).

**The claim discipline is unchanged.** Whatever the nine verdicts turn out to be, the table is
the claim: `PASS` rows extend the demonstrated set, `PARTIAL`/`FAIL` rows draw the boundary,
and the site's REAL row updates its citation (3/4 → the new fraction) only after the release
ships — T0 keeps every number an artifact of a run.

## Reasons
- The five additions attack the generalization claim where it is weakest — service, store,
  scheduler, UI, codec are the families practitioners will ask about first.
- Sequence-driven bounded semantics keep every oracle a measured fact while preserving what is
  archetype-*essential* (state across requests, storage invariants, scheduling order, view
  logic, framing) and shedding what is archetype-*incidental* (sockets, disks, threads).
- Making oracle-discrimination-with-plausible-wrong a pre-compilation gate turns the 1.75.1
  patch's lesson into process, cheap where it belongs (before 15 compilations, not after).

## Consequences
+ A nine-row table either strengthens the thesis substantially or maps its boundary with far
  more authority than four rows — both outcomes worth shipping.
+ The worker entry gives the bench its first *stated* semantic boundary (specified concurrency,
  not real parallelism) — honesty that pre-empts the obvious critique.
- 15 blind compilations is real volume; batched, with each model's return verified on disk
  (the haiku hallucinated-write lesson) before stamping.
- Five new canonical packages and oracles are five new chances to under-specify; the
  discrimination gate catches oracle thinness, but SPEC prose gaps will surface (as in M4) as
  compiler divergence — which is data, not failure.

## Implementation Plan
- Fixtures: the five entry directories, authored in the maker≠checker order above; a committed
  `stub/` per entry; **plausible-wrong implementations COMMITTED under each entry's `wrong/`**
  and asserted red by the suite (amended at review: the original plan kept them as a prose note
  in the oracle header, and the blind review showed exactly why that is not evidence — it found
  an alphabetical-errors implementation the ui-render oracle passed green. A committed fixture
  whose red run the suite reproduces is evidence; a note is trust).
- Compilations: 15 blind subagent runs (5 × Opus/Sonnet/Haiku), batched; verbatim
  `unresolved_intent`; `compile-validate` per compilation.
- Tests: T128 updated (entry count 9, one new representative entry asserted, discrimination
  sidecar extended). No new engine code expected; any incidental engine fix carries its check.
- Docs: this ADR, CHANGELOG-1.77.0, SYSTEM-FACTS (no subcommand change), DIAMOND-BENCH.md
  regenerated; the diamond page's REAL-row citation updates to the measured new fraction.

## Verification
- [ ] each of the five new entries has canonical/ + pinned IR + withheld oracle + committed
  stub, and `bench` reports all nine entries with a verdict (no PENDING left at ship) (AC-BG-01)
- [ ] every new oracle rejects both its degenerate stub AND a plausible-wrong implementation
  violating a SPEC-named sharp edge — recorded before compilation (AC-BG-02)
- [ ] all 15 new compilations `compile-validate` against their entry's pinned IR; no compiler
  input references any oracle; unresolved_intent is the model's verbatim return (AC-BG-03)
- [ ] the worker entry's SPEC states the deterministic-scheduling boundary explicitly, and the
  bench/changelog carry it as a named limitation, not a buried one (AC-BG-04)
- [ ] T128 asserts the committed entry count and the discrimination sidecar for the new entries;
  the suite is green across the matrix (AC-BG-05)
