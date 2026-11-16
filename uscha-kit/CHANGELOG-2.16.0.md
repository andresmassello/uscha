# uscha-kit 2.16.0 — review effort follows the change, and the QA loop converges on the diff (ADR-062)

A project that declares `review_tiers` in `uscha.config.json` stops paying a full re-cycle of every
QA tool for every one-line fix. The design was model-checked with TLA+/TLC first
(`docs/review-pace/models/`), and each counterexample the model found is replayed against the engine
as a RED case (AC-RP-18..25). One new subcommand, `review-tier`; no schema break: every new key and
line is conditional on the block, and without it the review loop reads and writes as in 2.15.1 --
the output differs only by `doctor`'s advisory, the new `--help` text and the opt-in flags
(AC-RP-16 measures `readiness`, `phase` and `converged` byte for byte).

## What changed

- **A review tier per change.** `review_tiers` maps path globs to `quick` / `standard` / `deep`. The
  engine computes the tier as the highest any file of the change reaches (committed since the
  merge-base with the base branch -- `origin/HEAD`, `origin/main`, `main`, `origin/master`,
  `master`, the first that resolves -- plus the working tree, prose included; a file no glob
  matches gets `default`), and keeps it: once a `test-run`, `review-start` or `log-step` has seen a deep file,
  reverting it leaves the change deep. `review-tier --repo R --tier T` raises it for anyone;
  lowering it is a human act (`--human`, `--note`; exit 2 in an agent's shell). `quick` runs
  code-review, `standard` code-review and judgment-day, `deep` the project's `qa_tools_order`;
  `review_tiers.tools` overrides each. Convergence waits for the tools of the tier, with the
  linters run once as a gate.
- **The block is read live and paths are repo-relative.** `review_tiers` in the live
  `uscha.config.json` wins over the ledger's frozen copy (the `qa_tools_external` precedent, ADR-051):
  a project adds it mid-run, keeps its ledger, and `doctor` no longer sends it to a re-init. Globs,
  scope paths and id paths are relative to the repo's configured `path`, not the git root, and
  prose files count in a review's tree. If no base branch resolves while the branch has commits,
  `review-start` exits 2 and `phase` / `converged` refuse (fail closed).
- **The scope of a review is assigned by the engine.** `review-start --json` gains `tier`, `scope`
  (the files, sorted) and `whole`. A tool with no clean pass reviews the whole change; afterwards
  only the files changed since its last clean pass; in `deep` always the whole change.
- **Convergence on the diff (`quick`, `standard`).** Every tool of the tier had a review of the
  whole change, its latest review is clean on the tree on disk, and every file changed after a
  tool's clean pass was reviewed clean again, after it, by that same tool. In `deep`: the 2.15.1
  rule over the tier's tools, plus each tool's last review covering the whole change. Every refusal
  names the tool, and the file whenever a file is the cause.
- **A finding carries its file (Locate, CoverFix).** Under `review_tiers` a gated step needs
  `--gated-ids <path>:<rule>`. Each id closes on its own: a later clean review that covered its file
  and in which that file changed, or its confirmed deferral (no coverage needed); fixing one id of a
  step never closes its siblings. A clean review that covered a file unchanged contradicts that id;
  a clean review of other files closes nothing. This is the amendment the model forced: decision 2 as first written let a
  known finding ship with an honest agent.
- **A finding is counted once; the author's verdict is recorded.** An id the tool already logged
  prints `repeat`. `log-step --rejected N` (optional) is stored. `readiness` prints an advisory
  `review yield` line per tool and `--json` carries `review_yield` (rounds, distinct gated ids,
  repeats, rejected); nothing gates on it.
- **A round cap.** After `review_round_cap` (default 3) gated rounds of one tool with no clean round
  of its own between, or gated review cycles (iteration numbers) across the tier's tools with no
  clean cycle between, `review-start` and `log-step` exit 2 and ask for an `escalate`; a human's
  `resolve-escalation` restarts the count.
- **An escape names its layer.** `production-finding --should-have-caught
  <test|static|review|model|human|none>` (optional) is stored; `readiness --json` counts
  `escapes_by_layer`.
- **Adoption.** `uscha init` writes `review_tiers` (`default: standard`, `quick: ["docs/**",
  "**/*.md"]`, an empty `deep`) for a new project and keeps an existing block; `doctor` proposes it
  to a project that declares none. The devloop SKILL documents the loop.
- **Model checking.** `docs/review-pace/models/models.json` now carries every `tooth-*.cfg` with the
  AC-RP case that replays it, the two-tool vacuity control, and the policy properties.

## Behavior changes on upgrade (read before upgrading)

- A project that never declares `review_tiers` reads exactly as before, with one visible change:
  `doctor` adds a WARN proposing the block (advisory; exit code unchanged).
- A project that adds `review_tiers` to its live config is on the review pace from its next command.
  The live block is read on every ledger load, so a malformed one makes every command that loads
  the ledger (`doctor` and `readiness` included) refuse, naming the file.
- A project created with `uscha init` from now on is on the review pace from its first run: a gated
  `log-step` without `--gated-ids <path>:<rule>` is refused. Delete the block to opt out.
- The id grammar of `ISSUES-DEFERRED.md` `defers:` lines and of `confirm-deferral --id` now also
  accepts `/`, `@` and `+` in the id, so a located finding such as `src/pay.py:R3` can be deferred.
- `.pace-cases.json` is a new suite sidecar (T180).

## Honest limits

- A green model proves no violation of the model at its bounds. Two tools were model-checked only
  where the bound allowed; with one tool, SameTool and TierTools are inert. The engine's rules are
  the model's, but the model takes a finding's file and a step's scope from the ground truth: the
  engine reads the file from the id (narrated, like every count) and assigns the scope itself.
- A fix that breaks a file it did not touch is seen only by the tests: the diff-scoped re-review
  trades that exposure for speed, which is why `deep` keeps the whole-change review.
- The ids' paths are matched literally against the repo-relative paths the engine derives; a path
  written another way is not covered, and its debt stays open (fail-closed).
- A flagged file put back to an earlier clean content is handed no scope, so only a confirmed
  deferral (or a review that covers it) closes its id; the engine never closes it by itself.
- The base is the first branch of a fixed list; a project whose base is named otherwise is refused
  (fail closed) until one of those names resolves.
- The round cap's cycle count reads the iteration numbers the agent logs: a round that reuses the
  latest iteration finishes that cycle and is not counted as a new one (the per-tool count has no
  such escape). A tool that alternates gated and clean rounds is never capped.
- The model carries one located finding, so it does not check two ids of one step; the engine closes
  each id on its own (AC-RP-30) and no model covers that.
- The review yield is narrated like the counts it adds up.

## Evidence

Suite: 471 checks · 0 fail; acceptance 518/519.
