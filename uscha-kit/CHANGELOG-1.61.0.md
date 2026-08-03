# uscha-kit 1.61.0 — green, but green at *what*? (2026-08-03)

The engine could say **"tests green"** and not say **"green at what"**. Freshness is computed
from file mtimes, and nothing bound a snapshot to a commit. So evidence produced against a
dirty working tree was recorded as measured with full provenance — provenance true of the
**tree**, not of the **commit that will merge**. A dirty tree can make a suite pass while the
candidate commit alone would fail, and the ledger could not see the difference.

Every snapshot now records where it came from.

## `origin` on every snapshot

```json
"origin": { "commit": "5d17cf4…", "dirty": false }
```

Measured at `_snapshot` — the single ingestion choke point, so every caller inherits it —
with `git rev-parse HEAD` and `git status --porcelain` in the repo path.

- **Untracked files count as dirty.** An untracked file the suite depends on *is* the
  contamination worth recording, and treating untracked as invisible is a mistake this engine
  already paid for in 1.57.0.
- **Absence is named.** No git, no repo → both fields `null`. **`dirty: null` never reads as
  clean**: a tree state nobody could measure is not a clean one. `AC-EP-03` exists to forbid
  the tempting `dirty: false` default, and is mutation-proven against exactly that.
- **Advisory throughout.** `snapshot` prints `origin=<sha8>/<clean|dirty|unknown>`;
  `dashboard --json` carries `evidence_origin` **only when a snapshot has one** (a ledger
  predating this release keeps the exact prior schema, the same conditional-key rule
  `fast_path` and `spec_drift` follow); `/uscha-status` says one line when the latest evidence
  was dirty, and nothing when it was clean or unknown. `readiness`, `phase` and `converged` are
  untouched — `AC-EP-04` asserts the score is numerically identical.

Knowing a tree was dirty does **not** mean the evidence is wrong — only that it was not
produced from a commit alone. Escalating that to a verdict is a guess, and guesses advise here.

## The worktree clean-room is deferred, and ADR-007 says why

The originating handoff specified a git-worktree clean-room gate for this slot. It is
**deliberately not built**, recorded as a decision rather than left silently undone:

- **It could not be built as specified.** Its own `AC-CR-03` and `AC-CR-04` compare the
  evidence's SHA to the candidate SHA — and no such binding existed. *This release is that
  prerequisite*, not an alternative to it.
- **It solves a narrower slice than it appears.** A local worktree runs on the same machine,
  OS and shell. The two red CI cells this repo paid for — bash 3.2 on macOS, Windows 8.3 short
  paths — are *environment variance*, a different failure class, and would have been green in a
  local clean-room. For this repo the clean checkout already exists: CI, six cells, and nothing
  ships without it.
- **If it is ever built, it ships off by default** — `absent block = feature off`, the
  convention now set three times. The handoff's `mode: "final"` would change the PR gate for
  every upgrading user, which INV-RIGOR-02 reserves for a human declaration.

Honest limit, in the ADR: `origin` is a claim about the **repo path**, so a change outside
every configured repo path is invisible to it.

## Measured against its own acceptance

`AC-EP-01..05`, all green — smoke **T118** against real git fixtures.

The fresh review before commit paid for itself twice, and both findings were reproduced
before being fixed:

- **CRITICAL** — `_evidence_origin` CRASHED where this changelog and the ADR promised nulls.
  A repo path that does not exist (an unconfigured or not-yet-cloned repo — ordinary, not
  exotic) or git absent from PATH raised out of `_snapshot` and took the whole command down.
  Every sibling measurement in `_snapshot` already tolerates a missing path; provenance must
  not be the one field that can kill the command it merely annotates. Now guarded, the same
  posture `_spike_branch` already took.
- **HIGH** — `git status --porcelain` ran with no pathspec, so a repo entry pointing at a
  **subdirectory** of a larger working tree inherited the whole outer repo's state: an
  unrelated edit elsewhere marked this repo's evidence dirty. Scoped with `-- .`, which is
  what makes "a claim about the repo path" true rather than aspirational.

Both survived the first test pass for the same reason: `AC-EP-03` exercised only a plain
non-git directory, where both git calls return cleanly non-zero — never the two shapes that
actually raised. It now covers all three, and `AC-EP-05` measures the scoping. Each is
mutation-proven: removing the crash guard turns AC-EP-03 red, removing the pathspec turns
AC-EP-05 red.

Acceptance for the repo: **33/33 measured green** where `coverage.py` is installed;
**32/33 with AC-GM-08 UNMEASURED** without it — the ingested `uscha-acceptance.xml` says
which, per run, and is never averaged into a friendlier number. Suite: 403 checks.
