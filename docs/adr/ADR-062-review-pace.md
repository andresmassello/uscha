---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/.claude/skills/uscha-devloop/SKILL.md
  - uscha-kit/skills/uscha-devloop/SKILL.md
model: required
model_manifest: docs/review-pace/models/models.json
---
# ADR-062: Review effort follows the change's risk, and the QA loop converges on the diff -- a fix does not buy a full re-cycle of every tool

## Status: Accepted (to ship as 2.16.0) — decided by the owner on 2026-11-15 (an `adr-refine` interview, two batches; decision 2 amended after the model the same day). The model (repo rule 12) is written before any engine code.

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

## Decision

1. **A review tier per change, set by the change.** `uscha.config.json` gains `review_tiers`:
   path globs mapped to `quick` / `standard` / `deep`, each tier naming its tools (default:
   `quick` = code-review; `standard` = code-review + judgment-day; `deep` = the profile's full list).
   The engine computes the tier as the HIGHEST tier the change has ever reached: the highest tier
   any path it touched reaches (a path no glob matches gets `standard`), kept when that file is
   reverted (decided after the model, 2026-11-15: `TierHighWater`). The agent may RAISE the tier;
   lowering it is a human act (ADR-058). `risk_profile` keeps owning the project's defaults and the deep list.
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
   **Refined by the owner with the RED cases (2026-11-15):** "only the tools that flagged" is not
   enough once a tier has two tools. The model's SameTool rule (below) also re-runs every tier tool
   whose clean pass the fix outdated -- still over the fix's diff only, never a full re-cycle. A tool
   with no clean pass yet reviews the whole change; its diff saving starts after its first clean
   pass. The scope of each review is assigned by the engine at `review-start`, not narrated by the
   agent.
   **Amended after the model (2026-11-15, decided by the owner):** as first written, decision 2 lets
   a known gated finding reach `pr-ready`, even with an honest agent (TLC, shortest trace 7 states,
   `tooth-as-written-honest`): tool 1 starts a review of `a` alone; the agent edits `b`; a test-run
   stamps the tree; the gated step is logged (it reviewed `a` with the old `b`); tool 1 reviews `b`
   alone on the new tree, honestly clean. The debt closes and Memory stays silent, because both
   compare whole trees and the two trees differ in `b`. Comparing whole trees was sound only while
   every review covered every file. Three rules are added (`docs/review-pace/models/`):
   - **Locate.** A gated finding records the file it is in: the gated id (decision 4) carries the
     path.
   - **CoverFix.** The debt of a gated step closes only on a clean step that **covered those files**
     and in which **those files** moved (or that saw a deferral, the 2.11.0 rule). Memory compares
     only those files: a clean step that covered them unmoved contradicts the record. (The debt and
     Memory are already read per tool in the engine; that part is not new.)
   - **SameTool.** A file changed after a tool's clean pass is re-reviewed clean **by that tool**,
     not by any agent tool -- a tool that cannot see a finding's class cannot clear a file of it.
   **What the model cannot see (found by a fresh review of 2.16.0).** It carries one located
   finding, so it says nothing about two ids of one gated step in different files: as first built,
   fixing one of them closed the step's debt. The engine now closes each `<path>:<rule>` id on its
   own (AC-RP-30); that rule is outside the model's bounds and no model checks it.
   **What the model shows, and at which bounds.** Necessary -- one counterexample each when it is
   dropped: CoverFix (one tool, `MaxLog = 3`), Locate and the re-review clause C2 (one tool,
   `MaxLog = 4`), SameTool (two tools, `MaxLog = 4`; with TierTools on, the trace is in the
   standard tier, where the second tool is in the tier and honestly clears the reverted file). Checked
   sufficient -- no error -- only with ONE tool: `MaxLog = 3` in CI, `MaxLog = 4` and deferrals
   by hand; with one tool SameTool is inert, and the two-tool no-error run did not finish
   (UNMEASURED). **When the model was written CI checked only CoverFix and the as-written break**: at its bound
   (`MaxLog = 3`) dropping Locate or C2 still reads no error; the teeth that catch them are `ci`
   entries of the manifest since 2.16.0, each with its AC-RP replay. The bug in the model is only ever in a quick file.
   **Decided by the owner after the model (2026-11-15):**
   - **WholeFirstPass.** Convergence verifies that every tool of the tier had a review whose scope
     was the whole change, in addition to C1 and C2.
   - **TierTools.** C2's re-review and the latest step Anchor reads count only tools of the tier.
   - **TierHighWater.** The tier is the highest the change ever reached; reverting a deep-glob file
     does not lower it (decision 1).
   What the model shows for each (one tool unless said; `-workers 1` for the counterexamples).
   None of the three is needed for `NoFlaggedBugShips` at the bounds checked: with each one off,
   the rule still reads no error (`MaxLog = 3`; WholeFirstPass on the shipped shape, TierHighWater
   on the lowering shape). Their value is coverage and policy, each shown by its own property:
   WholeFirstPass -- without it a change reaches `pr-ready` with a file no tool of the tier ever
   reviewed (`EveryFileReviewed` broken, 4 states); TierHighWater -- without it a change that
   touched a deep file converges on the quick rule after a revert (`LoweredNeverReady` broken, 7
   states); TierTools -- with SameTool off, it removes the quick-tier path in which a tool outside
   the tier clears the file (the shortest counterexample moves to the standard tier, 10 states), but
   with SameTool on, no violation was found without it (two tools, `MaxLog = 4`, runs stopped
   unfinished at 53 M and 17 M states: UNMEASURED); so SameTool stays necessary and TierTools adds
   nothing measured beyond it. With all three on, the shipped and lowering shapes read no error in
   CI (`MaxLog = 3`) and by hand (`MaxLog = 4`, deferrals). **A limit the
   engine adds:** the model takes a finding's file and a step's scope from the ground truth; in the
   engine the agent narrates the path -- and the scope, if `log-step` carries it -- like every count
   in `log-step` (until 2.16.0 review-start recorded only a whole-tree stamp; it now records the scope
   the engine assigns, so the scope is not narrated, while a finding's path still is).
3. **A round cap that stops the loop, not a ceiling it grinds to.** After `review_round_cap` cycles
   (default 3) without convergence, the engine refuses another cycle and asks for an escalation
   ("reconsider the approach", the existing `escalate`), instead of running to `max_iterations`.
   **Decided (2b):** cap 3, configurable as `review_round_cap`.
4. **A finding is counted once.** A gated finding already logged by id (`--gated-ids`, ADR-060) is a
   REPEAT in a later round: logged as such, never counted as new yield. `--gated-ids` becomes
   mandatory for gated steps of agent tools (it is already required to defer one).
   **Decided (4):** mandatory only in a project that declares `review_tiers`; elsewhere unchanged.
5. **What the author did with each finding is recorded.** `log-step` gains `--rejected N` (the tool
   was wrong) next to fixed / deferred / suppressed, so each tool's precision is measured. `readiness`
   prints a per-tool yield line (rounds, distinct gated findings, rejected) -- advisory, so a project
   can see which tool is pure cost before it removes one.
   **Decided (5):** `--rejected` is optional and the yield line is advisory only -- it never blocks.
6. **An escape says which layer should have caught it.** `production-finding` gains
   `--should-have-caught <layer>` (`test`, `static`, `review`, `model`, `human`, `none`). Readiness
   counts escapes per layer.
   **Decided (6):** optional.
7. **Option P, pre-existing findings** (not proposed yet, listed for the interview): a gated finding
   in lines the change did not touch (by `git blame` against the base) is tagged `pre-existing`, goes
   to the backlog and opens no debt. Fewer rounds, but it changes ADR-056's debt rule -> a model first.
   **Decided (3): not now.** Re-counted findings are handled by decision 4; the debt rule stays.
8. **Adoption.** **Decided (7):** everything is switched on by `review_tiers` in `uscha.config.json`;
   without it a project reads exactly as in 2.15 (the posture of ADR-061). `uscha init` writes a
   default block for a new project -- `default: standard`, `quick: ["docs/**", "**/*.md"]`, an empty
   `deep` list; `doctor` proposes it to an existing project; `adr-refine` asks which paths are `deep`.
   **Amended (2026-11-15, decided by the owner; ships as 2.16.1): `review_tiers.base`.** The fixed
   base list (origin/HEAD, origin/main, main, origin/master, master) left a project whose trunk is
   `develop`, `trunk` or a release branch unable to use the pace (2.16.0's "Honest limits"). The block
   gains an optional `base`: a git ref string such as `develop` or `origin/develop`. When set it is the
   ONLY base -- no fallback list -- and one that does not resolve fails closed exactly as an unresolved
   list does (`review-start` exits 2; `phase` and `converged` refuse), naming the ref and
   `review_tiers.base`. When absent, the list and the fail-closed rule are unchanged. A value that is
   not a nonempty string, or that starts with a dash (git would read it as an option), is refused
   naming the file, like any malformed live block; the ledger's frozen copy is validated the same way
   (naming the ledger). The ref is resolved to a commit before `merge-base` sees it. The key is read
   live like the rest of the block (ADR-051); `init` does not write it. Base resolution is outside
   ReviewPace.tla's abstraction (the model takes a change, not how its files are computed): no model
   change (AC-RP-37..41 replay the cases against the engine).
9. **Version.** **Decided (8):** 2.16.0 (new opt-in behavior). Order: the model, then the RED cases,
   then the code.

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
  references, `ACCEPTANCE.md`; the model is `docs/review-pace/models/` (GatedDebt extended), and
  decision 2's amendment adds Locate, CoverFix and SameTool to the engine's debt and convergence.
- Measured first: `tools/ledger-pace.py` on the project's ledger before and after, rounds-to-converge
  and escapes per layer as the guardrail.
- Tests: RED cases first, against 2.15.0.

## Verification (to be written as AC-RP-nn after the interview)

- A docs-only change runs the `quick` tier; a change touching a `deep` glob runs the full list; the
  agent cannot lower a tier.
- A one-line fix after a clean first cycle re-runs only the tools that flagged it.
- Each of the model's counterexamples (`tooth-*.cfg`) is replayed as a RED case against the engine:
  a clean step over other files, or by another tool, does not close a located finding's debt.
- A fourth cycle without convergence is refused, naming the escalation.
- A gated id logged again is a repeat, not new yield; the per-tool yield line counts distinct ids.
- `--rejected` and `--should-have-caught` are recorded and read by `readiness`.
