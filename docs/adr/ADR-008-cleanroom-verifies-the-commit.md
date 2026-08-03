---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/.claude/skills/uscha-devloop/SKILL.md
  - uscha-kit/uscha.config.json
---
# ADR-008: The clean-room verifies the COMMIT, and the engine never decides what to run

## Status: Accepted

## Context
ADR-007 bound evidence to a commit and a tree state, and deferred the worktree clean-room the
originating handoff specified — explicitly noting that the SHA binding was its missing
prerequisite. That prerequisite now exists, so the gate is constructible.

The problem it closes: a suite can pass in the maker's working tree *because of uncommitted
state* and fail against the commit alone. Demonstrated, not assumed — the fixture in T119
drops a committed file, the maker's tree still passes (the file is still on disk), and the
clean-room run goes red.

The design question this ADR exists to answer is not *whether* to isolate, but **who decides
what to execute**.

Options considered:
- **A) The engine reads `test_command_<type>` from config and runs it.** What the handoff
  implies. Rejected: the engine's standing contract is that it **ingests reports it did not
  produce** — the skill executes, the engine measures. Making it an executor of
  config-supplied shell strings inverts that, and quietly turns a config file into a
  code-execution surface.
- **B) Split into `prepare` / `ingest` so the caller runs the suite between them.** Rejected:
  it hands the worktree lifecycle to the caller, and a caller that dies between the two steps
  leaves a zombie worktree — the one thing this feature must never do.
- **C) The caller passes the command explicitly (`--run`).** **Chosen.**

## Decision

`qa_ledger.py cleanroom --repo <r> --ref <sha> --run "<command>" [--setup "<command>"]`

- **The engine owns what it can guarantee**: creating a detached worktree of the exact commit,
  verifying it is clean by construction, running what it was given, recording the result with
  full provenance (`ref`, `worktree_sha`, `status`, `exit_code`, `wall_ms`), and cleaning up.
  **It never guesses what a project's suite is** — the same contract `golden-coverage` already
  uses for `--harness`.
- **Status is specific, never a bare boolean**: `GREEN`, `RED`, `SETUP_FAILED` (a bootstrap
  that failed is not a failing suite), `WORKTREE_FAILED`, `WORKTREE_DIRTY` (a fresh worktree
  that is *not* clean means something intervened — a smudge filter, a hook — and the isolation
  claim is already false; say so rather than measure inside it).
- **Wall-clock is recorded.** The cost of the gate must be visible, never a surprise.
- **Cleanup is verified, not assumed.** `worktree remove --force` + `prune` + `rmtree`, and
  then the path is CHECKED: `rmtree(ignore_errors=True)` and a discarded git return code can
  both fail in silence (typically on Windows, where a handle the caller's command left open
  blocks removal). A surviving worktree is recorded as `cleanup_failed` and shouted on stderr
  with the command to fix it. A zombie worktree is a defect; a zombie worktree the operator
  cannot see is a worse one.
- `keep_worktree_on_failure` retains the tree for **any** failing status, not only `RED` -- a
  `SETUP_FAILED` checkout is just as worth inspecting. The cost is the operator's to accept:
  a repeatedly failing run under this flag accumulates one full checkout per invocation, so it
  is an inspection aid, not a setting to leave on in CI.

**The gate is opt-in.** `defaults.clean_room` absent, or `mode: "off"` → the gate does not
exist and behavior is identical to 1.62.0. `mode: "final"` → `pr-ready` additionally requires
a **GREEN clean-room run pinned to the current HEAD**. A new commit makes the previous run
stale for the gate — the same staleness posture the rest of the engine takes: evidence
certifies the thing it was measured against, and nothing later.

The handoff proposed `mode: "final"` as the *default*. Rejected, per ADR-007: that changes the
PR gate for every upgrading user, and INV-RIGOR-02 reserves added rigor for a human
declaration. `absent = off` is the convention this kit has now set four times.

## Reasons
- Evidence that certifies a tree is being read as if it certified a commit; that gap is a
  false "done" the engine could not previously see.
- Maker ≠ checker becomes **physical** rather than procedural: the worktree cannot see the
  maker's uncommitted state, so the separation is a property of the mechanism, not a promise.
- Keeping the command out of the engine keeps the engine honest *and* keeps the feature
  polyglot: it works for any stack, because it never had to know the stack.

## Consequences
+ The dirty-tree false green becomes measurable and blockable, with the cost visible.
+ `--run` composes with anything (a suite, one test, a build) without new engine surface.
- **It does not replace CI, and must not be read as doing so.** A local worktree runs on the
  same machine, OS and shell; environment variance (this repo has paid for bash 3.2 on macOS
  and Windows 8.3 short paths) is invisible to it. Different failure class, different
  instrument.
- The gate costs one full run per candidate SHA, and re-costs it after every new commit.
  Opt-in exists precisely so a project decides whether that trade is worth it.
- `--run`/`--setup` execute through the shell. They come from the human or the skill, never
  from a discovered file — but they are executed, and that is stated rather than hidden.

## Implementation Plan
- Affected paths: `qa_ledger.py` (`cmd_cleanroom`, `_cr_cfg`, `_cr_latest`, the gate inside
  `_derive_phase`, the conditional `clean_room` in `cmd_dashboard`), the devloop SKILL, the
  example config, kit README.
- Patterns: `golden-coverage` for the explicit-command contract and `finally` cleanup; the
  conditional dashboard key used by `fast_path`, `spec_drift` and `evidence_origin`.
- Tests: smoke **T119**, feeding `AC-CR-01..07` through the sidecar pattern.

## Verification
- [ ] green in the maker's tree, red at the candidate SHA → clean-room RED, pr-ready blocked (AC-CR-01)
- [ ] green run → ledger entry carries ref, worktree_sha, status and wall-clock (AC-CR-02, AC-CR-04)
- [ ] a new commit → previous clean-room evidence stale for the gate (AC-CR-03)
- [ ] no leftover worktree after a run (AC-CR-05)
- [ ] block absent → pr-ready identical, and the gate's effect is ATTRIBUTABLE to it (AC-CR-06)
- [ ] a failing `--setup` → `SETUP_FAILED`, distinct from a red suite (AC-CR-07)
