---
governs:
  - uscha-kit/tests/smoke-engine.sh
  - uscha-kit/tests/_jobs.sh
  - uscha-kit/tests/_harness.py
  - tools/release.py
---
# ADR-053: The smoke suite runs in parallel only when asked — USCHA_JOBS changes the wall time, never the measurement

## Status: Accepted (2.8.0)

## Context

The smoke suite is the instrument every release is measured with, and it runs several times per
release. Serial, it took ~18 minutes on a 16-core Windows machine. A profile of one instrumented
serial run put 55% of the wall time in one stretch: the three diamond-bench cache passes (~197 s)
and the nine blocks that consume them, T128–T136 (~413 s; T136 alone 127 s, T132 103 s). The
blocks from T137 to T162 added ~150 s and the post-teardown blocks T163–T170 ~74 s. The ~250 s
before the bench is ~125 small blocks that share one sandbox and one ledger.

Because the suite is the ruler, a bug in how it is run corrupts every later measurement. Speed is
worth having only if the measurement is provably unchanged.

## Decision

- **Opt-in.** `USCHA_JOBS=N` (N > 1) enables parallel units; unset, `1`, `0` or a non-number is the
  serial suite. `USCHA_COVERAGE=1` forces serial (one coverage data set, one writer). The job count
  is capped at the cores the machine reports (`nproc`, `getconf`, `NUMBER_OF_PROCESSORS`, then 1).
  `tools/release.py` pins `USCHA_JOBS=1` for the ritual's suite run, and CI does not set it.
- **One library, function units.** `uscha-kit/tests/_jobs.sh` (test-only, bash 3.2) provides
  `pj_unit NAME FN` and the barrier `pj_collect`. Each parallelized block is wrapped, body
  untouched, in a function. Serial, `pj_unit` calls it in the current shell — the same commands
  in the same order with the same output. Parallel, it runs in a background subshell with its
  counters zeroed, writes its `PASS FAIL` delta to its own result file and its stdout+stderr to its
  own log; the barrier waits, replays the logs in launch order and sums the deltas. A unit with no
  result file is one FAIL that names it, never a shorter sum.
- **What runs in parallel**, chosen by the profile: the three bench-cache passes start right after
  the sandbox init and overlap the serial prefix (each writes its own file; the barrier sits where
  the passes used to run, before the first consumer); T128–T162 run as units, collected before the
  serial tail (T112…T85) and the teardown; T163–T171 run as units, collected before the acceptance
  emitter. The prefix stays serial.
- **Shared state, resolved.** T142 and T143 are one unit (T143 reads what T142 wrote). The
  `.top-cases.json` merge shared by T137/T138/T141/T145 takes a directory lock in
  `_harness.sidecar`; their keys are disjoint, so the result does not depend on order. The
  coverage-mode `pyin` spools each call into its own `mktemp` directory instead of one fixed file.
  T168 stays after the teardown, where the bench cache is already gone, as it always was.
- **The criterion is equivalence.** T171 drives the shipped library through a mini-suite both
  ways, pins the bash-3.2 floor with a static scan, and carries a red probe and a shipped probe.
  The full-suite serial-vs-parallel diff is release evidence, recorded in the changelog.
- **The exit code reflects every counted failure.** The status was frozen at the teardown, so a
  FAIL counted after it (T163 onward, and every unit collected before the emitter) printed in
  `RESULTADO` but left exit 0. After the final `RESULTADO` a non-zero `FAIL` now raises a zero
  status; a non-zero status is never lowered. AC-PJ-07 pins it. This is the one change the serial
  default sees, and only on a red run.

## Why this is an ADR

It changes how the measuring instrument runs. Making the parallel path the default, or running
the ritual or CI with it, is a separate decision that needs CI evidence of equivalence on the
2–4-core runners first.

## Out of scope

- A block-level pool over the serial prefix (T1–T127): ~125 small blocks sharing one sandbox and
  one ledger, ~250 s that now bounds the parallel wall time. It needs a block-by-block dependency
  analysis that this release did not do.
- Flipping the default, or enabling `USCHA_JOBS` in `release.py` or CI.

## Acceptance

`AC-PJ-01..07` (smoke T171). AC-PJ-05 is the red probe (a barrier that deletes one unit's result
file turns the comparator red and counts that unit as one FAIL); AC-PJ-06 is the shipped probe
against the v2.7.0 suite. AC-PJ-02 and AC-PJ-05 read UNMEASURED on a machine that reports one core.
