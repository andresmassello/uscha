---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/uscha_top.py
  - uscha-kit/skills/uscha-devloop/uscha_top.py
  - uscha-kit/install-uscha.py
---
# ADR-037: `o` rerun in `uscha top` — the TUI may TRIGGER the engine with a command the human supplied at launch; it never decides what to run and never writes the ledger itself (proposal for phase 2, M4)

## Status: Proposed

## Context
`uscha top` v0.1 (ADR-031..034, shipped 1.86.0–1.89.0) reads everything and writes exactly one
thing: the human's verdict, through `curate`, one process per keypress (ADR-033). The handoff's
key map reserved `o` — "rerun oracle" — for phase 2. Two invariants collide the moment `o` does
anything:

- **INV-TOP-03 / ADR-033.** A verdict never moves DONE; only a green rerun does. So `o` is the
  one key that could move DONE — and a rerun that lands in the ledger is a *second write* next to
  the verdict, which ADR-033 explicitly forbids for the TUI itself.
- **ADR-008 (clean-room): the engine never decides what to run.** `cleanroom --run <cmd>` and
  `golden-coverage --harness <script>` take the command explicitly from the human; reading a
  `test_command` from config and executing it "would make the engine an executor of
  config-supplied shell, which it is not". A TUI that guesses a project's test command would
  break the same rule one layer up.
- **Measured beats narrated.** Running tests and *showing* the result without ingesting a report
  would put a narrated green on the board next to measured facts — the exact dishonesty the kit
  exists to remove (kit 1.48.1).

Three shapes are possible. This ADR names them and recommends one; the maintainer decides.

## Options

**A — no `o` at all.** Remove the key. The human reruns tests from their own shell (or the devloop
does, at every pass close), the engine ingests as it always does (`snapshot`), and the board
catches the change on the next poll tick (M2). Zero new writes, zero new authority. Cost: the
"rerun" moment leaves the terminal the human is already in; the round trip *verdict → rerun →
DONE moves* is not visible as one motion.

**B — `o` triggers a command the human supplied at launch, then the engine ingests.**
`uscha top --rerun-cmd "<shell>"` (explicit, per session, ADR-008 style — never read from config,
never guessed). `o` is inert without the flag (`no rerun command given -- pass --rerun-cmd`).
With it: the TUI runs the command in the tracked repo's cwd, synchronously, with a status line
(`rerun running… (verdict keys locked)`), then invokes the engine's own `snapshot --repo <r>`
(the ingest the devloop already performs) and reloads. The TUI writes no file itself: the only
writes are the engine's (`curate` on `p/f/u`, `snapshot` on `o`), each attributable to the human
at the keyboard. Same drain + cooldown discipline as verdicts (ADR-033 review, 1.89.0): one `o`
= one run; a held key cannot queue reruns; `--state` refuses it. AST guard extended: exactly one
call site for each engine subcommand the TUI spawns, none inside a loop.

**C — `o` runs the command and shows the result without ingesting.** Rejected here: the board
would show a narrated outcome next to measured ones. Named only so it is not proposed again.

## Recommendation
**B.** It keeps every invariant that matters — the TUI never writes, the engine never guesses,
the ingest is the real one, the human supplied the command and pressed the key — and it closes
the loop the mockup promised (`fix → rerun → DONE moves`) inside the terminal. ADR-033's title
sentence would be restated as: *the TUI itself never writes; it invokes at most two engine
subcommands, `curate` (verdict) and `snapshot` (rerun), each once per keypress.*

Under-claim: B does not run tests in a clean room; it runs them in the working tree, exactly as
the human would from their shell — the clean-room gate stays `cleanroom --run`, unchanged. The
board's evidence-origin line already says `measured dirty` when that is the case (ADR-007).

## What would be measured (draft criteria, `AC-T-25..29`, phase 2)
- `o` without `--rerun-cmd` writes nothing and says why; `o` under `--state` refuses.
- with `--rerun-cmd`, one keypress → one command run (argv shape asserted at a mockable
  boundary) → one `snapshot --repo` (engine write, byte-identical to a manual call) → reload.
- verdict keys are locked while a rerun is in flight; a held `o` yields one run.
- after a green rerun of a fixture whose tests were red, `terminado.done` increases and the
  feed shows the snapshot event — the only path that moves DONE.
- AST guard: exactly one call site per engine subcommand, none inside a loop.

## Consequences / Risks
+ The complete loop lives in one screen; every write stays the engine's and human-attributed.
- A long test suite blocks the board while it runs (synchronous by design in phase 2; async with
  a lock is a later refinement, not a requirement).
- A misspelt `--rerun-cmd` runs whatever the shell makes of it, in the repo cwd — the same trust
  the human already extends to their own shell; documented, not mitigated further.

## What this ADR does NOT decide
`d` (spec↔code diff, read-only, ADR-032's contract) and spec-lens (a separate surface) — they are
phase-2 siblings, not this decision.
