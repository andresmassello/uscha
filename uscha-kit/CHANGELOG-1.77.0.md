# uscha-kit 1.77.0 — Diamond Bench v0.2: nine archetypes, and the aliasing bug the oracle caught (2026-08-13)

ADR-020. The Diamond Bench grows from four entries to **nine** — no new engine mechanism (the
`bench` orchestrator was built to grow by adding entries), pure authoring + compilation volume:
five new canonical packages, five new withheld oracles, fifteen new blind compilations
(Opus/Sonnet/Haiku × 5), all through the M3 `compile/0.1` contract.

## The five new archetypes

Each specified as a bounded, sequence-driven system (`stdin → stdout/exit`, deterministic) that
keeps what is archetype-*essential* and sheds what is archetype-*incidental* (sockets, disks,
threads):

- **rest-handler** — request-driven service: a JSON request sequence over an in-memory item
  collection (routing, 200/201/204/400/404/405, state across the sequence, monotonic never-reused
  ids).
- **crud-store** — CRUD + storage semantics: strict create/read/update/delete/list (create is
  never upsert; update never inserts; list sorted).
- **worker** — concurrent-worker **coordination logic under specified deterministic scheduling**
  (priority desc, FIFO ties, dependencies first, failure isolates dependents transitively, cycle
  rejects). **Stated boundary, in the SPEC itself:** this tests coordination semantics, not real
  parallelism — oracling true parallel execution deterministically is out of the bench's scope,
  and saying so is the honest map ADR-018 promised.
- **ui-render** — a form view-model (input/toggle/reset/submit; reset restores the *initial*
  model; validation reports, never mutates).
- **protocol-adapter** — a wire↔JSON codec with an atomic batch and a byte-exact round-trip law.

**Process hardening (the 1.75.1 lesson made a pre-compilation gate):** every new oracle had to
reject its degenerate stub AND a hand-written plausible-wrong implementation (405-as-404 +
id-reuse; upsert semantics; priority-ignoring FIFO + running dependents of failed jobs;
reset-clears + submit-always-true; partial-output + field-sorting) **before** any compiler ran.
A correct reference implementation had to pass each oracle green first, too — which itself caught
an authoring bug: the first reference for rest-handler had the very aliasing bug described below.
All `unresolved_intent` stamped **verbatim** from each model's return (the 1.76.0 rule).

## The nine-row table

| Archetype | Verdict | Compilers |
|-----------|---------|-----------|
| crud-store | **PASS** | 12/12 ×3 |
| guard | PARTIAL | 19–21/23 |
| parser | **PASS** | 21/21 ×3 |
| protocol-adapter | **PASS** | 15/15 ×3 |
| rest-handler | PARTIAL | 14/15, 14/15, 15/15 |
| state-machine | **PASS** | 12/12 ×3 |
| transformer | **PASS** | 14/14 ×3 |
| ui-render | **PASS** | 12/12 ×3 |
| worker | **PASS** | 12/12 ×3 |

**7 PASS + 2 PARTIAL of 9**, every entry `all_distinct`, every oracle discriminating. The
implementation-replaceability claim now spans a service, a store, a scheduler, a UI view-model
and a codec — not just pure functions.

## The finding: a convergent implementation hazard, caught by the withheld oracle

rest-handler's PARTIAL is not an S-gap — it is a **bug two of three compilers wrote
identically**. Both Opus's and Haiku's handlers store the item dict and append *the same object*
to the response list; when a later `PUT` mutates the item, the **earlier 201 response mutates
retroactively** (the response to request 1 shows a name assigned by request 2 — time travel).
Sonnet snapshots its response bodies and is 15/15. The SPEC determines this behaviour by the
ordinary reading of "each request maps to one response" (a response that mutates after being
emitted is not *a* response) — though it never states snapshot semantics in so many words, so a
compiler could argue ambiguity; the SPEC gains from saying it explicitly, and that is recorded
as authoring feedback. The compilers erred — and so did the milestone author's own
hand-written reference implementation, which had the identical aliasing bug until the oracle
caught it during the pre-compilation gate. Three of four independent authors made the same
mistake: a genuine **convergent implementation hazard** of the stateful-service archetype
(shared mutable state + buffered responses), surfaced mechanically by an oracle none of them
saw. That is the bench doing exactly what it exists to do: "same system" certification catching
a subtle, realistic bug class — evidence the certification has teeth, not a weakness of the
method.

One SPEC ambiguity was also observed (not oracle-tested, named honestly): on an array element
that is not a request/operation object, Opus rejects the whole batch while Sonnet emits a
per-slot error — the "array of operation objects" phrasing underdetermines it. Recorded as
authoring feedback for the canonical layer.

## What the review caught

The independent blind review reproduced every number, verified the aliasing narrative at the
code level, wrote **twelve** of its own plausible-wrong implementations against the five new
oracles — and found the one that slipped: an implementation that sorts `errors`
**alphabetically** scored a false 12/12 green against the ui-render oracle, because the only
multi-error case used fields `a, b, c`... already in alphabetical order. The three real
compilations handle non-alphabetical order correctly (verified before fixing), so no shipped
verdict was false — but the oracle could not have caught a regression on AC-UI-03, ever. Fixed
before shipping: a non-alphabetical case (`z, a`) added (ui-render 12→13 cases; real impls
13/13, the alphabetical impl now 12/13 red). The review's deeper point was structural: the
plausible-wrong implementations were a prose note, not evidence — so they are now **committed
fixtures** under each new entry's `wrong/` (six impls, including the alphabetical one as a
regression guard), and AC-BG-05 runs them in the suite and asserts every one scores below
oracle-green. Also fixed from the same pass: stale "as of kit 1.75.1" stamps on the diamond
page (both languages) alongside the updated 7/9 citation; llms.txt citing ADR-017/018 without
/020; and the "SPEC fully determines" phrasing above softened to acknowledge snapshot semantics
is the ordinary reading, not an explicit sentence. Lesson, third time running: the blind review
keeps finding what the author's own gate missed — this time the gate itself (one wrong impl per
sharp edge is not enough; the review tried twelve).

`AC-BG-01..05` measured green (T128 extended to the nine-entry set). Suite: 415 checks;
acceptance **115/115** where `coverage.py` is installed. The site's REAL row citation updates
from 3/4 to the measured **7/9 PASS, 2 PARTIAL** (T0 keeps the number an artifact of a run).
