# uscha-kit 2.11.0 — nothing vanishes: a QA review is witnessed when it starts, convergence is anchored to the tree on disk, and the seal covers every repo (ADR-056 R2', ADR-057)

## What changed

The second slice of the gate-integrity work (`docs/gate-integrity/SPEC-2.11.0.md`). Its design was
model-checked before any code was written: a TLA+ model of the gated-finding debt as first
specified (`docs/gate-integrity/models/GatedDebt.tla`) let TLC find, with an HONEST agent, a 7-step
path to `pr-ready` on code a QA tool had flagged — flag v0, fix, log, review v1 clean, revert to v0,
re-test. Two causes: a QA step carried the tree it was LOGGED at, not the tree the tool REVIEWED,
and nothing anchored convergence to the tree on disk (2.10.0 re-derives the freshness of tests at
read time, never of reviews). The design below is the one TLC does not break at the same bounds.

- **`qa_ledger.py review-start --repo R --tool T --iteration N`** records `RV-n`: the tree a QA
  review starts on (ADR-055's tree stamp) and the content of `ISSUES-DEFERRED.md`. It runs nothing
  and reviews nothing. **`log-step --review RV-n`** links the pass to it: the step carries the
  REVIEWED state. A step logged without a valid open review of the same repo, tool and iteration is
  **unwitnessed** and, like an unverified step, never counts toward convergence and never hides an
  older one.
- **Anchor.** Convergence requires the latest review of each tool to have seen the source that is on
  disk now. Committing exactly the reviewed tree is not a change; a docs-only change is not a change;
  a late source edit or a revert means that tool runs again.
- **The debt, on reviewed trees.** A witnessed gated step opens a debt on its reviewed state; it
  closes only on a later clean review of the same tool on a different reviewed state — different
  source (a fix) or a changed `ISSUES-DEFERRED.md` (a deferral, which `readiness` now prints as
  "N gated finding(s) deferred, not fixed"). `--fixed` / `--deferred` never close it (narration).
  This closes the audit's A-F2 (a gated step re-logged clean with no source change).
- **Memory.** A clean verdict on exactly the content an earlier review of the same tool flagged
  contradicts the record and counts for nothing — the piece that holds even against a narrated
  clean pass.
- **The seal covers every configured repo** (ADR-057, the audit's A-F9). `check-terminado` prints
  one verdict line per repo and exits on the aggregate (False if any repo is broken, else UNMEASURED
  if any is unmeasured, else SEALED); `top --json` `terminado.sealed` is the aggregate, reasons are
  prefixed `[repo]`, and a `repos[]` detail appears only when more than one repo is configured. A
  single-repo payload is byte-identical to 2.10. Nested repo paths share their reports as footprint,
  and a change inside an inner repo breaks both seals, each named.
- **The devloop SKILL** (both twins): every QA pass starts with `review-start` and is logged with
  `--review`; the three rules are stated so the agent does not try to work around them.

## Behavior changes on upgrade (read before upgrading)

- **A `log-step` without `--review` no longer counts toward convergence.** Scripts and agents that log
  QA passes must call `review-start` first. Steps already in a ledger written by 2.10.x keep their
  2.10 semantics (they have no review); `readiness` names them ("N QA step(s) predate witnessed
  reviews").
- **A source edit after the last review of a tool un-converges the loop** until that tool runs again.
- **A clean re-review of flagged, unchanged code does not converge**: fix it, or defer it in
  `ISSUES-DEFERRED.md`. A tool's false positive is deferred, which is the method's existing path for
  a finding the human accepts.
- **A multi-repo project where only the first repo was ever snapshotted** used to read SEALED; it now
  reads UNMEASURED (exit 2), naming the other repo.
- `log-step`'s printed line is unchanged for an unwitnessed step (the human-approved devloop-entry
  golden pins it); the reason is named by `converged` and `phase`. A witnessed step prints
  `review=RV-n`.

## Pins that moved, on purpose

- The suite's QA steps that are meant to count are now witnessed: `rstep` (bash) and
  `_witness.rstep_argv` (Python) run the engine's own `review-start` and pass `--review`. The
  validation cases that compare ledger bytes around a rejected `log-step` keep the bare command.
- AC-QT-05's legacy emulation also strips the new step keys.
- The published subcommand count moves from 58 to 59 (`review-start`), with its row in both
  command-reference docs.

## Honest limits

- The engine witnesses the moment a tree is handed to a review; it does not run the reviewer, so it
  cannot prove the review ran, nor that a fix addresses a given finding. What it proves is that every
  verdict is about the tree it claims and that the verdicts do not contradict each other.
- **Without git** a reviewed tree cannot be compared, so a gated-finding debt degrades to 2.10
  semantics (a later clean step closes it) and `readiness` says so ("closed without a comparable
  tree (no git): movement was not measured"); Anchor and Memory need git for the same reason.
  `review-start` also refuses an iteration older than the newest step of the tool, as `log-step`
  does, before it writes anything.
- The model check is bounded (3 code versions, one tool, one repo, at most 5 ledger records). The
  design is written per tool and per repo so the bound maps onto it; that is an argument, not a
  check. Each TLC path is replayed against the real engine (T174).
- Still proposed, for 2.12.0 (ADR-058): `--human`/`--note` and the agent-marker refusal on the human
  acts, and the Claude Code hook that keeps a red PR a draft.

## How it is pinned

`AC-GI-30, -32..36, -50..58` (smoke T174): the three TLC paths (M1, M2, Lies) and the audit's A-F2 as
RED cases, a SHIPPED PROBE (AC-GI-50: the v2.10.1 engine reaches `pr-ready` on the M1 path), the
vacuity, deferral and docs-only GREEN cases, a v2.10.1 ledger, malformed `--review`; and the seal
over two repos (A-F9, both sealed, one never snapshotted, nested paths, a docs-only commit) plus
the single-repo payload shape.

## Evidence

Suite: __SUITE__ checks · 0 fail; acceptance __ACC__.
