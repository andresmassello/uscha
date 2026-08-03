# uscha-kit 1.63.0 — the clean-room: verify the commit, not your tree (2026-08-03)

The last piece of the originating handoff, and the one ADR-007 deliberately deferred four
releases ago until its prerequisite existed. It does now (evidence has carried a commit and a
tree state since 1.61.0), so the gate is built.

## The failure it closes, demonstrated

A suite can pass in the maker's working tree **because of uncommitted state**, and fail
against the commit alone. The ledger records that as measured, with full provenance — true of
the *tree*, not of the *commit that will merge*.

T119 does not assume this, it reproduces it: a committed file is dropped from the index, the
maker's tree still passes (the file is still on disk), and the clean-room run goes **RED**.

```bash
python qa_ledger.py cleanroom --repo <name> --run "<your test command>" [--setup "npm ci"]
```

Detached `git worktree` of the commit → verified clean by construction → your command → the
result recorded with `ref`, `worktree_sha`, `status`, `exit_code` and **wall-clock** (the cost
of a gate must be visible, never a surprise) → worktree removed unconditionally, because a
zombie worktree is a defect.

Status is specific, never a bare boolean: `GREEN`, `RED`, `SETUP_FAILED` (a bootstrap failure
is not a failing suite), `WORKTREE_FAILED`, and `WORKTREE_DIRTY` — a *fresh* worktree that is
not clean means something intervened (a smudge filter, a hook), so the isolation claim is
already false and the engine says so rather than measuring inside it.

## The engine never decides what to run

The command arrives explicitly via `--run`. The handoff implied reading `test_command_<type>`
from config and executing it; that is rejected, and the rejection is the point of ADR-008.

The engine's standing contract is that it **ingests reports it did not produce** — the skill
executes, the engine measures. Making it an executor of config-supplied shell inverts that and
quietly turns a config file into a code-execution surface. So the engine owns only what it can
guarantee (isolation, the SHA binding, cleanup) and never guesses what a project's suite is —
the same contract `golden-coverage` already uses for `--harness`. A side benefit: it works for
any stack, because it never had to know the stack.

## Opt-in, and the gate is *attributable*

`defaults.clean_room` absent or `mode: "off"` → the gate does not exist, behavior identical to
1.62.0. The example config ships `"off"`. `mode: "final"` → `pr-ready` additionally requires a
GREEN run pinned to the **current HEAD**; a new commit makes the previous run stale for the
gate, the same staleness posture the rest of the engine takes.

The handoff wanted `"final"` as the default. Rejected per ADR-007: it would change the PR gate
for every upgrading user, and INV-RIGOR-02 reserves added rigor for a human declaration.
`absent = off` is now the convention four times over.

`AC-CR-06` is built so the gate's effect is **attributable**, not merely present: the *same
ledger* returns `pr-ready` with the gate off, is blocked with it declared, and opens again once
a green clean-room exists for HEAD. A test that only ever sees exit 1 measures "something
blocks", not "this blocks".

## What it is not

**Not a substitute for CI.** A local worktree runs on the same machine, OS and shell.
Environment variance — this repo has paid for bash 3.2 on macOS and Windows 8.3 short paths —
is invisible to it. Different failure class, different instrument. Anyone reading the
evidence-grade ladder as "clean-room ⇒ CI unnecessary" would be reading it wrong.

Also honest: `--run` and `--setup` execute through the shell. They come from the human or the
skill, never from a discovered file — but they *are* executed, and ADR-008 states it rather
than burying it.

## What the fresh review caught

- **CRITICAL** — `integration` is a SYNTHETIC scope, never present in `config["repos"]`, and
  `_repo_cfg` exits on an unknown name. Every other call site guards it; the new gate did not,
  so declaring the clean-room turned `phase --repo integration --require pr-ready` — the merge
  gate for the integration layer — into a config-error crash instead of a phase verdict.
  Reproduced, guarded, and now measured by `AC-CR-08`: the criteria measured the feature and
  left **the scope it runs in** unmeasured, which is why it survived.
- **HIGH** — cleanup was *attempted*, not verified. `rmtree(ignore_errors=True)` and a
  discarded git return code can both fail in silence, typically on Windows where a handle the
  caller's command left open blocks removal — leaving a real zombie on disk AND in git's admin
  state, while the record reported only the test outcome. The path is now CHECKED after
  removal; a survivor is recorded as `cleanup_failed` and shouted on stderr with the command
  to fix it. A defect the operator cannot see is worse than one that shouts.
- `keep_worktree_on_failure` retains ANY failing status, not only `RED` — the ADR said
  otherwise, so the ADR was what was wrong. Stated now, with its cost: one full checkout per
  failing invocation, an inspection aid rather than a CI setting.

`AC-CR-01..08`, all green. Suite: 404 checks. Acceptance: **42/42 measured green** where
`coverage.py` is installed.
