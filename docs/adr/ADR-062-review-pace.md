---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/.claude/skills/uscha-devloop/SKILL.md
  - uscha-kit/skills/uscha-devloop/SKILL.md
model: not-needed -- SUPERSEDED by the interview (2026-11-15, answer 2a): decision 2 changes what convergence means, so a model IS required. The field flips to `required` in the commit that adds docs/review-pace/models/ (GatedDebt extended), before any engine code (origin: agent)
---
# ADR-062: Review effort follows the change's risk, and the QA loop converges on the diff -- a fix does not buy a full re-cycle of every tool

## Status: Proposed — drafted 2026-11-15 from field data; `adr-refine` interview in progress: batch 1 (decisions 1, 2, 3, 7) decided by the owner on 2026-11-15, batch 2 open.

## Context

**The owner's report:** development with the method feels slow; product quality stays first.

**Field data** (`tools/ledger-pace.py` over the ledger of a real Java + TypeScript project, five days,
66 commits):

- **106 QA rounds.** Rounds are logged per tool and per cycle; the tools that ran every cycle were
  checkstyle, findsecbugs, pmd and spotbugs (12 rounds each), code-review (11), judgment-day (7),
  eslint and tsc (5) and improve (4).
- **Yield is very uneven.** improve: 4 rounds, 0 findings. spotbugs: 204 findings, 203 deferred,
  1 gated. checkstyle, eslint, tsc: almost always zero. The productive ones: judgment-day (5 gated
  in 7 rounds), code-review (5 in 11), findsecbugs, pmd.
- **The same findings are counted again.** findsecbugs logged 53 gated findings over 12 rounds,
  with 13 fixed and 0 deferred: most are the same findings re-counted round after round.
- **What escaped:** 4 production findings reported by the user -- 2 CRITICAL concurrency races
  (operations without a lock; a draw run twice in parallel), 1 HIGH missing validation, 1 MEDIUM
  UI. None of the 106 rounds saw the races: a race is in the interleaving of two operations, not
  in a line a linter or a diff reviewer reads.
- No `test-run` records: test time could not be measured.

**The engine's rule that makes this so** (`_converged`, ADR-002 lineage): convergence needs the LAST
FULL CYCLE of every agent tool with zero gated findings AND zero files changed, plus every linter's
latest run clean. So every fix -- one line -- starts a full cycle of every tool again. And the tool
list comes from `risk_profile` for the WHOLE project (`RISK_PROFILES`: A runs code-review; C, D and E
run code-review, judgment-day and improve on every change), so a docs fix pays what a change to the
draw logic pays.

**Prior art** (credited in the references): the Claude Code team, "How the Claude Code team does code
review" (claude.dev, Oct 2026). Their target is the least human review time with NO rise in reverts
or incidents, which are the guardrail. Their measured levers: review effort set by the change's risk
(a classifier picks none / one / two humans; some paths always need a person); a round cap (after
three rounds the author reconsiders the approach), diff-only re-review after the first passes, no
repeated findings, flagging the bug CLASS; noise measured by what the author did with each finding;
every incident turned into an eval case. After the convergence work their mean reviews-to-pass went
from 2.08 to 1.32 and PRs needing five or more rounds from 8.9% to 1.5%; about 59% of what a
reviewer kept flagging was code older than its first pass.

## Decision (proposed)

1. **A review tier per change, set by the change.** `uscha.config.json` gains `review_tiers`:
   path globs mapped to `quick` / `standard` / `deep`, each tier naming its tools (default:
   `quick` = code-review; `standard` = code-review + judgment-day; `deep` = the profile's full list).
   The engine computes the tier from the files the change touches (the highest tier any touched path
   reaches; a path no glob matches gets `standard`). The agent may RAISE the tier; lowering it is a
   human act (ADR-058). `risk_profile` keeps owning the project's defaults and the deep list.
   **Decided (1a, 1b, 1c):** the tier comes from declared path globs only -- deterministic, no
   classifier; `quick` = one code-review pass plus the linters run once as a gate, never as rounds;
   `standard` adds judgment-day; `deep` = the profile's full list, improve included (the field data
   showed improve and spotbugs yielding nothing outside deep work); only a human lowers a tier.
2. **Re-review on the diff after the first full cycle.** The first cycle runs every tool of the tier
   over the whole change. A later cycle runs only the tools that found something gated in the previous
   one, over the files changed since. Convergence = every tool of the tier has had one clean pass, and
   every file changed after a tool's clean pass has been reviewed clean by at least one agent tool.
   **Decided (2a):** in `quick` and `standard`, only the tools that flagged something re-run, over
   the fix's diff; in `deep`, a fix still re-runs every tool over the whole change (as today), so
   expensive code loses nothing. This changes what convergence means -> a model first (repo rule 12),
   extending GatedDebt with tiers and diff-scoped re-review; the model must show that no gated
   finding the ledger knows ships, under both rules.
3. **A round cap that stops the loop, not a ceiling it grinds to.** After `review_round_cap` cycles
   (default 3) without convergence, the engine refuses another cycle and asks for an escalation
   ("reconsider the approach", the existing `escalate`), instead of running to `max_iterations`.
   **Decided (2b):** cap 3, configurable as `review_round_cap`.
4. **A finding is counted once.** A gated finding already logged by id (`--gated-ids`, ADR-060) is a
   REPEAT in a later round: logged as such, never counted as new yield. `--gated-ids` becomes
   mandatory for gated steps of agent tools (it is already required to defer one).
5. **What the author did with each finding is recorded.** `log-step` gains `--rejected N` (the tool
   was wrong) next to fixed / deferred / suppressed, so each tool's precision is measured. `readiness`
   prints a per-tool yield line (rounds, distinct gated findings, rejected) -- advisory, so a project
   can see which tool is pure cost before it removes one.
6. **An escape says which layer should have caught it.** `production-finding` gains
   `--should-have-caught <layer>` (`test`, `static`, `review`, `model`, `human`, `none`). Readiness
   counts escapes per layer.
7. **Option P, pre-existing findings** (not proposed yet, listed for the interview): a gated finding
   in lines the change did not touch (by `git blame` against the base) is tagged `pre-existing`, goes
   to the backlog and opens no debt. Fewer rounds, but it changes ADR-056's debt rule -> a model first.
   **Decided (3): not now.** Re-counted findings are handled by decision 4; the debt rule stays.

## Reasons

- The data shows where the time goes: tools that never find anything gated, findings re-counted, and
  a full re-cycle for every fix. None of those buys quality.
- The escapes show where quality is actually lost: concurrency. No number of review rounds finds a
  race; a test that fires two requests at once, or a model (ADR-061), does. Moving effort there is
  the quality half of this ADR -- it belongs to each project, so it is out of scope here.
- Quality stays the guardrail: every lever is advisory or opt-in until the per-tool yield and the
  escapes per layer say it is safe.

## Consequences

+ A low-risk change stops paying a deep review; a fix stops restarting every tool.
+ Each tool's yield and precision become measured facts, so removing one is a decision with evidence.
- Decision 2 trusts a diff-scoped review to see what a fix broke elsewhere: a fix that breaks a file
  it did not touch is seen only by the tests. That is why it needs a model and an interview.
- More fields to log (`--rejected`, `--should-have-caught`); counts stay narrated by the agent, as
  every count in `log-step` already is.

## Out of scope

- Concurrency tests and models for a specific project -> that project's own ADRs.
- A merge queue, feature flags and rollback (the article's last layers) -> the project's CI and
  release, not the engine.
- An LLM risk classifier -> the tier comes from declared path globs; a classifier is a later ADR if
  the globs prove too coarse.

## Implementation Plan

- Affected paths: `qa_ledger.py` (both twins: `review_tiers`, `_converged`, the round cap, repeats,
  `--rejected`, `--should-have-caught`, the readiness lines), the devloop SKILL twins, the command
  references, `ACCEPTANCE.md`; a GatedDebt model extension if decision 2 or option P is adopted.
- Measured first: `tools/ledger-pace.py` on the project's ledger before and after, rounds-to-converge
  and escapes per layer as the guardrail.
- Tests: RED cases first, against 2.15.0.

## Verification (to be written as AC-RP-nn after the interview)

- A docs-only change runs the `quick` tier; a change touching a `deep` glob runs the full list; the
  agent cannot lower a tier.
- A one-line fix after a clean first cycle re-runs only the tools that flagged it (if decision 2).
- A fourth cycle without convergence is refused, naming the escalation.
- A gated id logged again is a repeat, not new yield; the per-tool yield line counts distinct ids.
- `--rejected` and `--should-have-caught` are recorded and read by `readiness`.
