---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/uscha_top.py
  - uscha-kit/skills/uscha-devloop/uscha_top.py
---
# ADR-033: The verdict is the only thing `uscha top` writes, and it writes it by shelling out to the existing `curate` — one keypress, one `curate` call, no batch, no auto-promotion, no auto-rerun

## Status: Proposed

## Context
Decision #2: the verdict write goes through the **existing** `curate` subcommand, never a
re-implemented append. The audit (AUDIT-DELTA §C) confirms the engine already enforces exactly the
discipline this feature needs:

- `cmd_curate` (L4425-4462) takes **one** OBS and **one** verdict:
  `curate --ledger <path> --repo <name> --obs <OBS-ID> --verdict preserve|fix|undefined [--human <name>] [--note <text>]`.
- It **hard-refuses any batch-looking input** (`re.search(r"[,\s*]", args.obs)` or `all`/`*`,
  L4429-4433) — one verdict, one call, enforced by the engine itself (ADR-013, INV-CURATION-01).
- It refuses if `discovery/CANDIDATE-DELTA.json` is missing/malformed or `--obs` is unknown
  (L4438-4450).
- The appended record is `{obs_id, verdict, human, at, note, repo}` (L4453-4456), append-only;
  re-curation supersedes without deleting (`_curation_verdicts`, L4290-4297).
- `promote` (L4465-4557) is the **separate** step that moves `preserve` observations into the
  canonical package; it is out of the TUI's scope in v0.1.

Decision #4: no auto-rerun after a fix verdict in M1-M3 — a fix leaves the obligation in its measured
state; only a real oracle/test rerun moves `DONE`. The mockup's 4.5s "resolved" animation is
demo-only.

## Decision
- **The only write `uscha top` performs is a verdict**, and it performs it by `subprocess`-invoking
  `qa_ledger.py curate` with the current curation record format. The TUI never opens the ledger for
  writing and never constructs a curation record itself. It is the *medium* of the human verdict, not
  a promoter (INV-CURATION-01).
- **One keypress → one `curate` invocation.** In VERDICTS mode, `p`/`f`/`u` each shell out once for
  the single selected OBS, then advance to the next uncurated OBS; an empty queue returns to BOARD.
  There is no loop that batches multiple OBS into one action — the engine would refuse it, and the
  TUI must not attempt it.
- **`--human` is passed explicitly** by the TUI (resolving the operator's name), rather than relying
  on `curate`'s `$USERNAME`/`$USER` default (L4452), so an SSH/multi-user verdict is attributed
  correctly. If no name resolves, the engine default stands.
- **No auto-promotion.** `promote` is never called by the TUI; it stays a human-run follow-up outside
  the single writable action.
- **No auto-rerun.** A verdict does not trigger tests, an oracle, or `readiness`. `DONE` (terminado)
  is unchanged by a verdict (INV-TOP-03); only a subsequent real green rerun moves it. The demo
  animation is not implemented as behavior.

## Consequences / Risks
+ The one write path is the one the engine already guards; the TUI inherits INV-CURATION-01,
  the batch refusal, and the append-only supersede for free.
+ A byte-for-byte fixture (ADR-034, FIXTURES.md) can prove the TUI-written record equals a manual
  `curate` call — the strongest possible statement that the TUI reimplements nothing.
- Shelling out per keypress costs one process spawn per verdict. In an interactive verdict session
  that is negligible and buys the guarantee that no append logic is duplicated.
- Because there is no auto-rerun, the board will show a just-fixed obligation still in its old measured
  state until a real rerun happens. That is intended and must be stated in the UI copy so it does not
  read as a bug (the fix is queued for the compiler, not applied to the score).

## Verification
- [ ] `p`/`f`/`u` shells out to `curate` once per keypress, never batched; empty queue returns to BOARD (AC-T-15)
- [ ] the appended record is byte-identical to a manual `qa_ledger.py curate` call with the same arguments (AC-T-17)
- [ ] after a verdict DONE does not change; no auto-rerun moves it (AC-T-16)

## What this ADR does NOT decide
- The verdict record shape — owned by `curate`/ADR-013, consumed here unchanged.
- The JSON the verdict queue is rendered from — ADR-032.
- `promote` / canonical-package movement — out of scope for v0.1 (audit C).
- Whether the TUI should ever gain a `promote` action — a later decision; not this one.
