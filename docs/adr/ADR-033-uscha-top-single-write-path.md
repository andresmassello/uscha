---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/uscha_top.py
  - uscha-kit/skills/uscha-devloop/uscha_top.py
---
# ADR-033: The verdict is the only thing `uscha top` writes, and it writes it by shelling out to the existing `curate` — one keypress, one `curate` call, no batch, no auto-promotion, no auto-rerun

## Status: Accepted (M3 shipped in 1.89.0; curated 2026-08-17; title sentence restated for phase 2 in 1.91.0 per ADR-037)

> **Restated 1.91.0 (ADR-037).** The title above is the M3 statement and stays true of the
> verdict. The general rule the feature now follows is one sentence wider: **the TUI itself
> never writes; it invokes engine subcommands, one per keypress, never in a loop** — `curate`
> for a verdict (this ADR) and `snapshot` for the ingest after a rerun (ADR-037), plus the
> human's own command, which is not an engine subcommand at all and writes only whatever the
> human's shell writes. Three spawns exist in `uscha_top.py` BEYOND THE READ BOUNDARY and no
> more; each has exactly one call site with no `for`/`while` above it, and the suite parses the
> module to prove it (AC-T-15, AC-T-29). The boundary itself — the single read-only `top --json`
> call in `load_state` (ADR-032/034) — is a fourth spawn in the file and always was; the earlier
> wording said "three spawns exist in `uscha_top.py`" full stop, which anyone grepping the module
> could falsify in one command (1.91.0 blind review). The suite now counts spawn call sites and
> pins the total at **four**, so a fifth inlined one goes red whichever side it lands on. Decision #4 below — **no auto-rerun** — is unchanged: nothing reruns by
> itself, and `o` is a keypress a human makes with a command that human supplied.

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
- **`--human` is passed explicitly** by the TUI, which resolves the operator's name. Stated
  precisely (1.89.0, correcting an over-claim in the first draft of this ADR): the TUI's own
  fallback is `$USERNAME`/`$USER` — **the same environment `curate` reads** — so on a plain local
  run the recorded name is identical either way, and the explicit pass buys nothing there. What it
  buys is the case it was written for: **only the explicit flag** attributes an SSH or multi-user
  verdict correctly, because only it can name someone the environment of whichever process runs
  `curate` does not. That is why the `uscha top` launcher forwards `--human` too. If nothing
  resolves, no flag is passed and the engine default stands.
- **One keypress means one keypress.** A held key repeats, and because the queue advances after each
  write, repeat two would judge an observation the human never read — the batch INV-CURATION-01
  forbids, arriving one legal call at a time. Two guards, both in the TUI: the input buffer is
  drained after every verdict attempt (`drain_keys`), and for 250 ms afterwards `p`/`f`/`u` produce
  no verdict at all and the status line says so. Navigation and the exits keep working — the
  cooldown blocks writes, not the reader.
- **A frozen snapshot is not a ledger.** With `--state` the frame comes from a file that may
  describe another project entirely, so a verdict is refused and named rather than written to
  whatever ledger happens to be in the working directory.
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
- [x] `p`/`f`/`u` shells out to `curate` once per keypress, never batched; empty queue returns to BOARD (AC-T-15)
- [x] the appended record is byte-identical to a manual `qa_ledger.py curate` call with the same arguments (AC-T-17)
- [x] after a verdict DONE does not change; no auto-rerun moves it (AC-T-16)

*Measured by T141 (1.89.0) over temp copies of `fixture-stale-quarantine`. What each assertion
really does, so the tick is readable: AC-T-15 replaces the subprocess boundary (`_curate_call`) and
counts the calls one keypress makes — one — and pins the argv; it also parses `uscha_top.py` and
fails if the module opens any file for writing, dumps JSON, or builds a second `curate` argv.
It also pins the three guards above: `apply_verdict` is called exactly ONCE in the whole module and
no `for`/`while` encloses that call (which is why the key loop reaches it through
`_apply_and_advance`); a verdict key during the cooldown yields no verdict while `j`/`t`/`q` still
work; and a `--state` run refuses with a named message and spawns nothing.
AC-T-17 compares the record the TUI path appended with the record a manual `curate` call appended on
a second copy: equal member for member, with `at` compared for shape (it is a wall clock, and the
suite injects no clock into a subprocess). AC-T-16 re-reads `top --json` before and after a real
verdict: `terminado.done` and `terminado.pct` unchanged, `debtors.you` down by one, the four buckets
still partitioning the board. Mutation-checked: a doubled call, a note the TUI authors itself, and a
verdict counted as DONE each turn the matching criterion red.*

## What this ADR does NOT decide
- The verdict record shape — owned by `curate`/ADR-013, consumed here unchanged.
- The JSON the verdict queue is rendered from — ADR-032.
- `promote` / canonical-package movement — out of scope for v0.1 (audit C).
- Whether the TUI should ever gain a `promote` action — a later decision; not this one.
