# uscha-kit 1.47.0 — the trail feeds itself: loop odometer + measured phase (2026-07-23)

Field feedback on the coordinator's real pain: with all the method's loops and passes, the
human steering the work loses track of *where the method is* and *how it is going*. The data
to answer that already existed in the ledger — derived phase (FSM 1.18.0), loop passes
(`iterations`), plateau (1.14.0), history (`readiness --record`) — but nothing surfaced it,
and the history starved because `--record` was opt-in and nobody ran it. Smoke suite: 376/376.

## Doctrine first: what "how much is left" may honestly mean
"Where am I" and "how many passes happened" are FACTS the engine already derives. "How much
is left" is a forecast — the QA loop converges, it does not count down — so the kit never
prints an ETA. The honest answers it CAN give: the derived phase, the pass count, and the
convergence signal (findings going down vs. plateau). That is what this release surfaces.

## The feed (the fix that unblocks everything)
`uscha-devloop` now closes **every** pass with `readiness … --record`. One flag, two feeds:
`readiness_history` (the mirador time-lapse stops saying "no history yet") and
`ledger["measured"]`, which now also carries the **loop odometer** per repo:

```jsonc
"measured": { …, "repos": { "backend-api": { "phase": "qa", "loops": 3, "stalled": false } } }
```

All facts the readiness run ALREADY computed — `--record` only persists them (append-only,
never a gate). `qa_ledger.py:cmd_readiness`.

## The odometer in the mirador trail
The trail's "QA loop" node now shows a measured badge via the `count` field the template
always supported (it was emitted `null` since 1.32.0): `"3 loops"`, plus `"1 escalado"` when
escalations are open, and the convergence verdict — `"plateau"` when the stall detector fires,
`"convergido"` when every repo converged. `cmd_dashboard` fills it from the same `loops` +
`advice` facts it already emitted; no new derivation.

## The phase token in the statusline (A-lite)
One compact token after the label: `qa×3` (derived phase × pass count), with a yellow
`plateau` warning when iterating stopped helping. Read from `ledger["measured"]` — the Stop
hook still never runs the engine. The phase shows even for projects with no AC-IDs (the
phase is its own fact, independent of acceptance).

Deferred (needs a phase-transition history the ledger does not keep, by design so far):
counting Build↔Verify re-entries, and the odometer over time in the time-lapse.

Regression: smoke **T91** — after two `log-step` passes and one `readiness --record`, the
measured summary carries `{phase: qa, loops: 2, stalled: false}`, the mirador `qa` node badge
reads `"2 loops"`, and the statusline renders `qa×2`.
