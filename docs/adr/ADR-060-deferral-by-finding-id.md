---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/.claude/skills/uscha-devloop/SKILL.md
  - uscha-kit/skills/uscha-devloop/SKILL.md
model: required
model_manifest: docs/deferral-by-id/models/models.json
---
# ADR-060: A gated finding is deferred BY ITS ID, and only a human's recorded confirmation lets that deferral close its debt

## Status: Accepted (2.14.0) — decided by the owner on 2026-11-02 (an `adr-refine` interview). Amends ADR-056 R2' (the debt's deferral rule).

## Context

Since 2.11.0 (ADR-056 R2') a gated finding's debt closes "by deferral" when a later clean review
sees `ISSUES-DEFERRED.md` PRESENT and with content different from what the gated review saw. That
rule has two holes, and a third problem under them:

1. **Removal reads as deferral** -- documented as an honest limit in 2.11.0: drop one entry and keep
   others, the file still changed and is present, so the debt closes.
2. **The deferral is not tied to the finding.** ANY change to the file -- a comma, a deferral for
   another tool -- closes a debt it has nothing to do with.
3. **Authority.** A gated finding is at or above the severity gate; the method says it is FIXED and
   only the rest goes to the backlog. Deferring a gated finding is an exception a human accepts --
   yet today the agent edits the file and the debt closes, and nobody decided anything.

Considered: **(A) identity** -- a deferral names the finding it defers, and a debt closes only when
ITS findings are deferred, read at the clean review and now; **(B) authority** -- deferring a gated
finding is a human act; **(C) both**. A alone lets the agent invent an id, write it and close its
own debt (narration closing a measured fact); B alone confirms "a deferral" without saying which
finding it closes. Chosen: C.

For the confirmation itself: (i) a `confirmed:` marker in the markdown (ADR-044) is text anyone can
type, the hole ADR-058 closed for escalations; (ii) a text hook blocking the agent from writing it is
weak (a script gets through); (iii) an ENGINE human act, recorded in the ledger and refused in a
known agent shell. Chosen: iii.

## Decision

1. **A gated step names its ids.** `log-step` gains `--gated-ids id1,id2,...`: exactly
   `--gated-reported` distinct ids, scoped to the step's tool. Duplicates, or a count that differs
   from G, are refused (exit 2, nothing written). A gated step logged WITHOUT ids is recorded, and its
   debt can close only by a fix -- never by deferral; `readiness` names it.
2. **A deferral line per id** in `ISSUES-DEFERRED.md`, the only lines the engine reads there:

       - defers: <tool>/<id> -- <why the risk is accepted>

   The rest of the file stays free prose. A malformed `defers:` line (unknown tool, no reason) counts
   for nothing and `readiness` names it.
3. **Confirmation is a human act** (ADR-058's mechanism): `qa_ledger.py confirm-deferral --id
   <tool>/<id> --human NAME --note TEXT` records `{id, by, note, at, human_declared}` in the ledger,
   refuses under a known agent-shell marker, and refuses an id no gated step reported. A `confirmed:`
   typed in the markdown does not count for a gated deferral. **A confirmation confirms the gated
   steps logged BEFORE it** (it records the step counter, `after_step`): review tools restart their
   numbering, so a later finding that reuses `F-1` is a different finding and needs its own
   confirmation -- which the human can give (2.14.0 fresh review). Only rows with a declared human
   (`human_declared: true` and a name) count.
4. **The debt closes by deferral** when EVERY gated id of the step has a confirmed confirmation AND a
   `defers:` line present in the file the clean review saw AND in the file now (read at read time,
   like Anchor). Partially confirmed: the debt stays open for the ids still missing, named.
   Unconfirmed: `readiness` prints "N gated deferral(s) awaiting human confirmation". A confirmed
   line removed later re-opens the debt.
5. **The hash of the whole file no longer closes a debt** for steps that carry ids. It stays as
   Anchor's input (a changed file means the last review is not current).
6. **Legacy:** steps logged before 2.14.0 keep the 2.11 rule, and `readiness` names them ("closed by
   an untyped deferral (pre-2.14)"). Nothing green turns red on upgrade. A step is 2.14 when it
   carries `gated_ids` OR its logged state carries the `defers` it saw, so removing `gated_ids` from
   a 2.14 step does not bring the whole-file rule back.
7. **Only live lines count:** a `defers:` line inside a code fence or an HTML comment is
   documentation and defers nothing.

## Model (repo rule 12)

`docs/deferral-by-id/models/DeferralById.tla`, written before the code: one QA tool, two findings,
witnessed reviews and Anchor as shipped; the agent adds and removes `defers:` lines, may log a gated
step without ids and may narrate a clean verdict; confirmation is a separate human action the agent
cannot take. The rule: `pr-ready` never holds on a version with a finding the ledger knows was
flagged, unless a human confirmed that finding's deferral AFTER the step that flagged it, and the
line is still on file.

**The model was wrong once, and the fresh review found it.** Its first version treated an id as one
finding for good, so it could not express a later finding reusing `F-1`; an old confirmation then
closed the new finding in the engine. The model now records WHEN a confirmation was given and which
step flagged each finding, and the unscoped confirmation is a teeth config that breaks in 2 s. The
lesson is the method's own: a green model says nothing outside what the model can express.

Measured 2026-11-04, TLC v1.7.4, 2 workers (`ci` = run by the CI `models` job, blocking):

| config | tier | verdict |
|---|---|---|
| the design, no source edits (MaxLog=3; the agent narrates, logs without ids, deletes lines) | ci | no error, 1,953,200 states, 21 s |
| the design in a narrower world (no edits, no deletions; MaxLog=4) | ci | no error, 1,091,255 states, 12-16 s |
| the 2.11-2.13 whole-file rule (`ById = FALSE`) | ci | **violated** in 2 s -- replayed by AC-DI-07 |
| a `defers:` line without human confirmation (`Confirm = FALSE`) | ci | **violated** in 2 s -- AC-DI-04 |
| a confirmation not scoped to its step (`Scoped = FALSE`) | ci | **violated** in 2 s -- AC-DI-11 |
| vacuity: a confirmed, present deferral still ships; a real fix still ships | ci | violated (as they must) |
| the design with source edits (MaxLog=3) | deep | no error, 4,530,168 states, 48 s |
| ... and gated steps logged without ids | deep | no error, 14,104,440 states, 146 s |
| ... and the partially fixed version | deep | no error, 111,004,608 states, 30 min |

Read-now (decision 4's "and in the file now") was not needed for the rule at the first model's
bounds (MaxLog=4, read-now off: no error, 29,611,512 states): Anchor and Memory already refuse a
removed deferral. The engine keeps it as defense in depth.

## Reasons

- Both holes close by construction, and a deferral stops being something the agent grants itself.
- It reuses ADR-044's grammar for what the file SAYS and ADR-058's human act for who DECIDED.
- Legacy keeps its semantics, named, as every earlier gate change did.

## Consequences

+ A gated deferral is now a visible, attributable decision, finding by finding.
- One more call per gated deferral, typed by the human; and `log-step` asks for ids on gated steps.
- **What an id proves:** nothing about the finding. Ids are narrated by the agent (`--gated-ids`),
  like the counts. What the design guarantees is consistency -- the deferred id is the reported one,
  and a human confirmed it -- not that the finding is what the id says.
- **The ledger is a file the agent can write.** A confirmation row forged by hand without a declared
  human counts for nothing, but one forged WITH `human_declared: true` and a name after removing the
  ledger's `integrity` field is indistinguishable from a real one. The defense is ADR-058's: the
  command refuses in the agent's shell, and a hand edit of the ledger is a deliberate act visible in
  the agent's command text and in git. It is not a cryptographic proof.
- **Without git** a fix cannot be measured, so -- as since 2.11.0 (ADR-039's posture) -- a later
  clean review closes a gated debt and `readiness` names it ("closed without a comparable tree").
  The id rules apply in full only where the tree can be compared.

## Out of scope

- Tying ids to the MEASURED findings of `ingest-gate` (which do have real ids) -> a later ADR.
- Deferring non-gated findings: they keep going to `ISSUES-DEFERRED.md` with no debt, unchanged.
- A hook against writing `confirmed:` in the markdown: unnecessary, it no longer closes anything.
- Retroactivity: steps before 2.14.0 keep the hash rule (decision 6).

## Implementation Plan

- Affected paths: `qa_ledger.py` (both twins: `log-step --gated-ids`, `confirm-deferral`, the
  `defers:` parser, `_review_verdicts`, `readiness`), the devloop SKILL twins, the command
  references, `ACCEPTANCE.md`, the model and its manifest.
- Patterns: ADR-058's `_human_act` for the confirmation; ADR-044's marker grammar for the line
  shape; ADR-056 R2's read-time Anchor.
- Tests: the RED cases below, each red against 2.13.0 first; each TLC counterexample replayed as one.

## Verification (promoted into ACCEPTANCE.md in 2.14.0)

- [ ] AC-DI-01 -- a gated step without `--gated-ids` is recorded, its debt closes by no deferral, and
  `readiness` names it.
- [ ] AC-DI-02 -- `--gated-ids` with a duplicate, or with a count other than G: exit 2, nothing written.
- [ ] AC-DI-03 -- an unconfirmed `defers:` line does not close the debt; `readiness` says "awaiting
  human confirmation".
- [ ] AC-DI-04 -- `confirm-deferral` (human) closes it; under `CLAUDECODE=1` it is refused; a
  `confirmed:` typed in the markdown closes nothing.
- [ ] AC-DI-05 -- partial: two of three ids confirmed, the debt stays open for the third, named.
- [ ] AC-DI-06 -- removing a confirmed line after the close re-opens the debt (the 2.11 hole).
- [ ] AC-DI-07 -- any other change to the file (a comma, another tool's deferral) closes nothing.
- [ ] AC-DI-08 -- a 2.13.0 ledger (steps without ids, closed by the hash) loads, and `readiness`
  names the untyped deferral.
- [ ] AC-DI-09 -- `confirm-deferral` for an id no gated step reported is refused.
- [ ] AC-DI-10 -- the model: `model-check.py check` and the `models` job are green over the
  manifest, whose teeth configs (the hash rule, no confirmation) replay AC-DI-07 and AC-DI-04.
