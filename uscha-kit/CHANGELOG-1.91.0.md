# uscha-kit 1.91.0 — `uscha top` phase 2: `d` shows the drift the ledger already measured, and `o` reruns what the human supplied (ADR-037) (2026-08-18)

M4 closes the key map the handoff drew: `d` and `o` stop being stubs. ADR-037 (option B, chosen by
the maintainer) is Accepted; ADR-033's sentence is restated: *the TUI itself never writes; beyond
the one read-only `top --json` read boundary it spawns at most three things — `curate` (a verdict),
`snapshot` (an ingest), and the human's own rerun command — each once per keypress.*

## `d` — spec ↔ code drift, read-only
`top --json` gains `spec_diff`, projected ONLY from the `spec-drift` record the ledger already
carries (ADR-005, advisory): the stale documents, worst lag first, with the code reference that
outran them; `null` when no run was recorded (INV-TOP-05 — no source, no invention). The DIFF pane
says so in words when there is nothing: `no spec-drift run recorded — run qa_ledger.py spec-drift`.
It runs nothing. The `spec-check` advisory (criteria without ids) is deliberately NOT included: it
records nothing in the ledger, so showing it would mean linting files inside a read-only command.

## `o` — rerun (ADR-037 B)
`uscha top --rerun-cmd "<shell>"` (also through the launcher). Without the flag `o` is inert and
says why; under a frozen `--state` it refuses. With it, one keypress = one run of the human's
command in the tracked repo's cwd (the FIRST configured repo — the engine now names it in
`repos[]`, so the TUI derives nothing and every status line says which), then ONE `snapshot --repo`
by the engine, then a reload. **The snapshot is recorded whatever the exit code**: a red suite is
evidence, and not ingesting it would leave the previous, greener measurement on the board.
Verdict keys are locked while a rerun is in flight; input is drained and a 250 ms cooldown follows,
exactly as verdicts do; the AST guard now proves one call site each for `_curate_call`,
`_snapshot_call` and `_rerun_call`, none inside a loop. Measured end to end: on a fixture whose
JUnit had a red case, `o` moved `done 2 → 3`, `machine 1 → 0`, with the snapshot at the head of the
feed — the only path that moves DONE (INV-TOP-03 completes its loop).

`AC-T-25..29` (T145) measure it: inert without the flag / refused under `--state`; one command +
one snapshot per keypress, in that order, a held key yields one; verdicts refused mid-rerun; the
real ingest moves DONE and the record equals a manual `snapshot`; the guard, and the DIFF pane
byte-identical to its goldens with zero escapes. Frozen state `state-drift.json` was produced by a
real `spec-drift` run on a temp git repo (not hand-written). The board hint now reads
`[v] verdicts · [d]iff · [o] rerun`; the twelve board goldens moved by that one line.

Also: ADR-038 proposed (INV-T1 — TERMINADO sealed to the exact code state — ported into the engine as the
next release; the external `sh` package that stated it is kept under `audits/uscha-cierre/` as reference).
The blind review's six should-fix items were applied and each is now measured (spawn-site count, engine-side
`spec_diff` assertions, display columns in the DIFF pane, historical version sentences restored).

Suite: 433 checks · 0 fail; acceptance 184/184; the kit's own ledger reads READINESS 100.0.
