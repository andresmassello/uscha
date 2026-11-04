# uscha-kit 2.14.0 — a gated finding is deferred by its id, and only a human's recorded confirmation closes its debt (ADR-060)

## What changed

Since 2.11.0 a gated finding's debt closed "by deferral" whenever a later clean review saw
`ISSUES-DEFERRED.md` present and changed: removing one entry, adding a comma or deferring another
tool's finding closed it, and the agent did it alone. This release ties each deferral to the
finding it defers and its closing power to a human's decision. It is the first feature built under
repo rule 12 (ADR-059): the design was model-checked BEFORE the code.

- **`log-step --gated-ids id1,id2,...`** names the gated findings -- exactly `--gated-reported`
  distinct ids, scoped to the step's tool. A duplicate or a wrong count exits 2 and writes nothing.
  A gated step logged without ids is recorded, and its debt closes only by a fix.
- **`ISSUES-DEFERRED.md` carries one `- defers: <tool>/<id> -- <why>` line per deferred gated
  finding**; the rest of the file stays free prose. A line that starts like one but does not parse,
  or names a tool this repo never logged, defers nothing and `readiness` names it.
- **`qa_ledger.py confirm-deferral --repo R --id <tool>/<id> --human NAME --note TEXT`** -- a human
  act (ADR-058's mechanism): recorded in the ledger, refused under a known agent-shell marker, and
  refused for an id no gated step reported. A `confirmed:` typed in the markdown closes nothing.
- **The debt closes by deferral only when every id has a confirmation AND its `defers:` line is in
  the file the clean review saw AND in the file now.** Partially confirmed, it stays open naming the
  ids still missing; unconfirmed, `readiness` prints "N gated deferral(s) awaiting human
  confirmation"; a confirmed line removed later re-opens it. The whole-file hash no longer closes a
  debt for a step with ids (it stays as Anchor's input).
- **Legacy:** steps logged before 2.14.0 keep the whole-file rule, and `readiness` names each such
  closure ("closed by an untyped deferral (pre-2.14)").
- **`summary` prints a red-gate draft PR as an EXCEPTION** (`pr-opened-not-ready`), as ADR-058
  promised in 2.12.0 and 2.12.0 did not deliver; `summary --json` carries `exceptions` only when one
  exists.
- **The devloop SKILL** (both twins): log the gated ids, write the `defers:` line, then STOP and
  ask the human to run `confirm-deferral` in their own terminal.

## The model (repo rule 12)

`docs/deferral-by-id/models/DeferralById.tla`, written before the code (one tool, two findings,
witnessed reviews; the agent adds and removes `defers:` lines, may log a gated step without ids
and may narrate a clean verdict; confirmation is a human action the agent cannot take). Its
manifest runs in the CI `models` job: the design (no error, 13 s), two vacuity controls, and two
teeth configs that MUST break -- the 2.11-2.13 whole-file rule (replayed by AC-DI-07) and a
deferral with no human confirmation (AC-DI-04). Deep runs, recorded: with a partially fixed
version, no error at 14,676,480 states; with read-now off, no error at 29,611,512 states (Anchor and
Memory already hold; the engine keeps read-now as defense in depth).

## Behavior changes on upgrade (read before upgrading)

- **A new gated step without `--gated-ids` closes only by a fix.** To defer a gated finding, log its
  id, write its `defers:` line and have a human run `confirm-deferral`.
- **Editing `ISSUES-DEFERRED.md` no longer closes a debt** for steps logged from 2.14.0 on.
- The published subcommand count moves from 61 to 62 (`confirm-deferral`), with its row in both
  command-reference docs.

## Pins that moved, on purpose

- T174's deferral cases (AC-GI-55, -56, -61) now defer by id with a human confirmation; the
  whole-file rule they were first written against no longer closes a debt for a step with ids.
- AC-GI-46 also asserts the `summary` line.

## Honest limits

- The ids are narrated by the agent, like the counts. The design guarantees consistency -- the
  deferred id is the reported one, and a human confirmed it -- not that the finding is what the id
  says. Tying ids to `ingest-gate`'s measured finding ids is a later ADR.
- `--human` proves a name and a reason were typed outside a known agent shell, not identity
  (ADR-058).

## Correction to 2.13.0

CHANGELOG-2.13.0 said the GatedDebt `ci` configs take "1-25 s each". Measured: up to 42 s locally
with the suite running alongside; the whole tier took 23 s on the CI runner. The model's README
carries the measured figures.

## How it is pinned

`AC-DI-01..10` (smoke T177), each red against 2.13.0 before the code existed (AC-DI-02's refusal
arm also measured with a valid list, which 2.13.0 did not accept).

## Evidence

Suite: __SUITE__ checks · 0 fail; acceptance __ACC__.
