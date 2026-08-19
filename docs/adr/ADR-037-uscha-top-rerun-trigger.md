---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/uscha_top.py
  - uscha-kit/skills/uscha-devloop/uscha_top.py
  - uscha-kit/install-uscha.py
---
# ADR-037: `o` rerun in `uscha top` — the TUI may TRIGGER the engine with a command the human supplied at launch; it never decides what to run and never writes the ledger itself (proposal for phase 2, M4)

## Status: Accepted (phase 2 shipped in 1.91.0; option B chosen by the maintainer 2026-08-18)

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
**B** — chosen by the maintainer on 2026-08-18 (curated interactively). It keeps every invariant that matters — the TUI never writes, the engine never guesses,
the ingest is the real one, the human supplied the command and pressed the key — and it closes
the loop the mockup promised (`fix → rerun → DONE moves`) inside the terminal. ADR-033's title
sentence would be restated as: *the TUI itself never writes; it invokes at most two engine
subcommands, `curate` (verdict) and `snapshot` (rerun), each once per keypress.*

Under-claim: B does not run tests in a clean room; it runs them in the working tree, exactly as
the human would from their shell — the clean-room gate stays `cleanroom --run`, unchanged. The
board's evidence-origin line already says `measured dirty` when that is the case (ADR-007).

## What shipped (1.91.0) — two decisions the draft left open

- **The snapshot runs whether or not the command exited 0.** A red suite is evidence; refusing
  to ingest it would leave the board showing the previous, greener measurement — narrated green
  beside measured facts, the exact inversion this kit exists to remove. What a non-zero exit
  changes is the status line, which names it (`rerun exit 7 (red) · ingested: …`), and nothing
  else. A failing *ingest* is a different statement and gets its own line
  (`snapshot FAILED (…) — nothing was ingested`).
- **Which repo.** The **first configured repo**, exactly as `spec_pin` already picks the sha it
  labels the board with (ADR-032). The choice is the engine's: `top --json` now emits
  `repos[]` in configuration order and the TUI takes its head — a TUI that scanned the ledger
  for a repo would be deriving. Every line that depends on the choice names the repo it picked
  (`running in backend-api (first configured repo)`), so a multi-repo project cannot read the
  status as "all of them". Under-claim: `o` reruns and ingests **one** repo per keypress.
- A third refusal joined the two the draft named: a ledger with **no configured repo** (no cwd
  to run in, no repo to ingest for) is refused by name, like the other two, spawning nothing.

## What is measured (`AC-T-25..29`, T145, promoted into `ACCEPTANCE.md`)
- **AC-T-25** — `o` is inert without `--rerun-cmd`, refuses under `--state`, and refuses with no
  configured repo: each says why, spawns nothing, and leaves the ledger byte-identical.
- **AC-T-26** — with the flag: one keypress → one command in the first configured repo's
  directory (as a shell string, `shell=True`) → one `snapshot --ledger … --repo …` → one
  re-read, in that order, both boundaries asserted by argv; a held `o` yields one run; a red
  run is still ingested and a failed ingest says so.
- **AC-T-27** — verdict keys record nothing while a rerun is in flight and `o` cannot stack on
  itself, while navigation and the exits keep working. Measured purely (a caller-supplied
  boolean), because the phase-2 rerun is synchronous: while the suite runs no key is read at
  all, and what is typed meanwhile the drain throws away.
- **AC-T-28** — the loop closes on measured evidence: with the fixture's red case replaced by a
  green report, the real `_snapshot_call` leaves a ledger record equal member for member to a
  manual `qa_ledger.py snapshot` call's (minus the two wall clocks), the feed's newest event is
  that snapshot, and `terminado.done` is up by one. **Stated narrowly:** the AC recount reads
  the ingested *report* (`_ac_tags` reads the file), so the number moves as soon as the report
  does — what the snapshot adds, and what the TUI could not fabricate, is the recorded
  measurement and the event that names it.
- **AC-T-29** — AST guard: exactly one call site each for `_curate_call`, `_snapshot_call` and
  `_rerun_call`, none under a `for`/`while`; plus the `d` pane byte-identical against its two
  golden frames with zero escapes on the plain path, and the empty case rendering "no
  spec-drift run recorded" rather than a clean board.

*Mutation-checked: a doubled rerun call, a skipped snapshot, a verdict allowed during a rerun,
a stale `[d]/[o] phase 2` hint and a tampered golden each turn a criterion red.*

## Consequences / Risks
+ The complete loop lives in one screen; every write stays the engine's and human-attributed.
- A long test suite blocks the board while it runs (synchronous by design in phase 2; async with
  a lock is a later refinement, not a requirement).
- A misspelt `--rerun-cmd` runs whatever the shell makes of it, in the repo cwd — the same trust
  the human already extends to their own shell; documented, not mitigated further.

## What this ADR does NOT decide
spec-lens (a separate surface) — a phase-2 sibling, not this decision. `d` (spec↔code diff,
read-only) shipped in the same release under ADR-032's contract, widened there with the nullable
`spec_diff` block: it is a projection of the advisory record `spec-drift` already writes, it runs
nothing, and with no recorded run it says so instead of showing a clean board.
