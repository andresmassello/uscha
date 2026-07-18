# uscha-kit 1.42.0 — the mirador answers "how's it going / what's blocking / what's next" (2026-07-18)

Until now the mirador showed the project's SKELETON — the phase trail, the counters, the
invariant names — but a real early-stage project rendered as a wall of empty-looking cards
that left you with "sabor a nada": you could not tell, at a glance, how it was going, what was
blocking it, or what to do next. This release makes the mirador lead with exactly those three
answers — and every one of them is **measured**, not narrated. Smoke suite: 359/359.

## The status story (hero block)

A three-line block sits under the verdict, each line derived purely from fields the engine
already emits in `dashboard --json` (no new engine logic, still model-agnostic):

- **Cómo viene** — the measured sub-scores, verbatim: e.g. `coverage 0% · simplicity FAIL`.
- **Qué lo traba** — the hard blockers, each traceable to a measured field: failing gates
  (sub-scores reading FAIL/MISS), the readiness cap (`readiness.sub`), open discovery intake
  (production findings / spec doubts / spec change requests), and expired/malformed ADR
  experiments. A failing gate is NOT double-reported as its flipped CONSTITUTION invariant.
  When nothing blocks, it says so and names the dimensions still lacking measured evidence.
- **Qué sigue** — the active phase in the derived FSM plus its method and execution hint
  (`tier` / `model` / `effort`), so the operator sees the next concrete move.

`mirador.template.html:renderStatus`. Regression: smoke **T80**.

## Empty cards earn their place

Cards no longer render as dead space when a real project has nothing for them yet:

- **The 6 layers of truth** (`capas`) — the engine never feeds this for a real project (it was
  demo-only), so the whole card now HIDES when empty instead of showing an empty grid.
- **Specifications / ADRs / QA loops** — when empty, show a one-line hint of what fills them
  and in which phase, instead of a blank list or a bare `0/0`.

## Safety
All status/hint DOM is built with `textContent` / `createTextNode` (no `innerHTML`), so the
1.41.0 Mirador XSS hardening still holds — smoke P0-A (script-context escaping, no HTML sinks)
stays green.

## Note on the test suite
The installer/npm smoke checks still hardcode the version string, so this bump updated those
literals. A follow-up could have them read `VERSION` dynamically.
