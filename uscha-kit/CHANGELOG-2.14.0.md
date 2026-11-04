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
  A confirmation confirms the gated steps logged BEFORE it: a later finding that reuses the id
  (review tools restart their numbering) needs its own, which the human can give.
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
manifest runs in the CI `models` job: the design in two bounded worlds (no error, 21 s and 16 s),
two vacuity controls, and three teeth configs that MUST break, each in about 2 s -- the 2.11-2.13
whole-file rule (replayed by AC-DI-07), a deferral with no human confirmation (AC-DI-04) and a
confirmation not scoped to its step (AC-DI-11). The deep tier (source edits, gated steps without
ids, a partially fixed version) is recorded in the manifest: no error at 4.5 M, 14.1 M and
111.0 M states.

## Closed before release (fresh review)

A fresh reviewer found five problems, all reproduced, now fixed and pinned. **A confirmation never
expired**: it was keyed only by `tool/id`, so after an edit a NEW finding that reused `F-1` was
closed by the OLD confirmation, and the human could not confirm the new one ("already confirmed").
Confirmations now record the step counter and confirm only earlier steps (AC-DI-11). **The model
had missed it** because it treated an id as one finding for good; it now records when a
confirmation was given, and the unscoped version is a teeth config. A confirmation row typed into
the ledger without a declared human closed a debt, and removing `gated_ids` from a 2.14 step brought
the whole-file rule back (AC-DI-12). A `defers:` line inside a code fence or an HTML comment counted
(AC-DI-13). And the refusal message spoke of "lifting an escalation", an empty id list printed as a
blank, and long lists were cut without "+N more".

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
  (ADR-058). The ledger is a file the agent can write: a confirmation forged by hand WITH a declared
  human, after removing the ledger's `integrity` field, is indistinguishable from a real one -- a
  deliberate, visible act, not one the engine can prove did not happen.
- Without git a fix cannot be measured, so (as since 2.11.0) a later clean review closes a gated
  debt and `readiness` names it; the id rules apply in full where the tree can be compared.

## Correction to 2.13.0

CHANGELOG-2.13.0 said the GatedDebt `ci` configs take "1-25 s each". Measured: up to 42 s locally
with the suite running alongside; the whole tier took 23 s on the CI runner. The model's README
carries the measured figures.

## How it is pinned

`AC-DI-01..13` (smoke T177), each red against 2.13.0 before the code existed (AC-DI-02's refusal
arm also measured with a valid list, which 2.13.0 did not accept).

## Evidence

Suite: 468 checks · 0 fail; acceptance 461/462.
