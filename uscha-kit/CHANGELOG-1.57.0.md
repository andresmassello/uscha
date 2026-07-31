# uscha-kit 1.57.0 — fast-path: the ceremony floor is no longer flat (2026-07-30)

The strongest category-level criticism of spec-driven development landed squarely on uscha: a
one-line fix and a schema migration paid the same entry cost, while the landing promised
"rigor where the stakes justify it" with no mechanism for the inverse. This release ships that
mechanism — designed through the method itself (`/uscha-adr-refine` interview → ADR-003/004 →
golden anchor → implementation against AC-FP criteria). Smoke suite: 398/398.

## `fastpath-eval` — the shortcut is granted by measurement, never by opinion

```bash
qa_ledger.py fastpath-eval --repo <name> --json            # dry-run: verdict only
qa_ledger.py fastpath-eval --repo <name> --intent "fix: x" # records it in the ledger
```

- **Signals, not narrative:** `max_files_changed` (3) and `max_loc_delta` (80) measured from
  `git diff --numstat` against the merge-base with `origin/main` (fallback `main`) — **plus
  untracked files**, because a small change is very often a new file, and `git diff` is blind
  to those. That blind spot was caught by this release's own tests: four cases failed until
  untracked files counted. `protected_paths` globs (migrations, goldens, `db/**`) deny
  regardless of size.
- **Fail-closed:** no config, no git, no resolvable base → `DENY` with the reason named.
  "Could not measure" never grants a shortcut — the same posture the INV-GOLDEN hook learned
  in 1.55.2, applied at design time here.
- **Intent as request:** the human *requests* the fast path (`--intent`, one sentence); the
  engine verifies and decides, and the single ledger entry carries request, every signal with
  value/threshold/source/timestamp, and verdict. Without `--intent` the call is a dry-run and
  writes nothing.
- **Escalation through the existing machinery:** a prior `ALLOW` followed by a `DENY` re-eval
  (the devloop re-runs before the PR step) appends a standard escalation — so the derived
  phase flips to `escalated`, `pr-ready` is blocked and readiness capped until a human
  `resolve-escalation`, after producing the ADR + ACCEPTANCE the change turned out to deserve.
  No new FSM state, no parallel bookkeeping.
- **Asymmetric override (INV-RIGOR-02, new in CONSTITUTION.md):** the full path can always be
  forced; nothing can force `ALLOW` over a measured `DENY`. Without that asymmetry a fast
  path is a backdoor with paperwork.
- `require_asserting_test`: while a fast-path run has no measured test execution after its
  entry, readiness is capped through the existing cap mechanics.
- `dashboard --json` carries `fast_path` (latest verdict per repo); `/uscha-status` shows one
  line when entries exist and nothing when none do.

## Measured against its own acceptance
`ACCEPTANCE.md` gained `AC-FP-01..11` (numbering preserved from the originating handoff;
AC-FP-04 deliberately absent — ADR-004 records that the golden-touched veto is deferred until
a golden↔source mapping exists, since a gate that cannot be measured must not ship as if it
did). Smoke **T113** exercises every criterion against real git fixtures and feeds a sidecar
so each closes on its **own** named testcase in the acceptance emission: 15/16 measured green,
with AC-FP-08 (behavior-identical-when-unconfigured) anchored to a pre-implementation golden
that emits UNMEASURED until a human approves the capture — the box stays unticked exactly
until then.

## What the fresh review caught before this shipped
Five real defects, one of them CRITICAL and reproduced in ordinary documented usage:

- **Escalation gated on “an ALLOW ever existed”**, not on the latest entry — so after one
  fast-path run, every later unrelated DENY-with-intent would have been misclassified as
  ESCALATED, forever. Now it gates on the LATEST entry being ALLOW.
- **A git rename walked past `protected_paths`**: numstat reports renames as one descriptor
  (`old => new`), and the raw string was matched against the globs. Renaming a file INTO `db/`
  produced ALLOW. Both sides of a rename are now expanded and matched — renaming a file OUT of
  a protected area is as gate-worthy as renaming one in.
- **Binary diffs counted as 0 LOC** (numstat emits `-`), letting a swapped artifact sail under
  `max_loc_delta`. Unmeasurable LOC now DENIES with its own named signal (`binary_files`) —
  fail-closed applies to what cannot be measured, not just to what fails.
- **A stale sidecar could feed the acceptance emission** if T113 crashed mid-run after a green
  previous run. The sidecar is deleted before T113 starts: a crash now yields UNMEASURED.
- **`dashboard --json` grew a `fast_path` key unconditionally**, a schema change contradicting
  the “absent block = behavior identical” claim. The key now exists only when entries exist.

## Also
- The example `uscha.config.json` documents the `fast_path` block; absent block = feature off.
- Engine subcommand count corrected everywhere it was published: **30**, not 29.
- `/uscha-devloop` gained Phase 0a (run the classifier first; echo the engine's breakdown
  verbatim on DENY — the skill wires, it never argues with the verdict).
