# uscha-kit 2.8.0 — the smoke suite runs in parallel only when asked: USCHA_JOBS changes the wall time, never the measurement (ADR-053) (2026-10-09)

## The gap

The smoke suite is the instrument every release is measured with, and it runs several times per
release: the writer's run, the ritual's run, CI. Serial it took ~18 minutes on a 16-core Windows
workstation, and that was the main reason a change took hours. Because the suite is the ruler, the
only acceptable speed-up is one that provably measures the same thing.

## The profile chose the design

One instrumented serial run (each block header timestamped) of v2.7.0, 1107 s in total:

| block | seconds | share |
|---|---:|---:|
| diamond-bench cache (three full passes) | 196.7 | 17.8% |
| T136 round trip | 126.9 | 11.5% |
| T132 slack hypothesis | 103.3 | 9.3% |
| T134 JS archetype | 44.7 | 4.0% |
| T129 controlled-language arm | 38.4 | 3.5% |
| T135 multi-unit archetype | 34.2 | 3.1% |
| T73b ledger integrity | 26.4 | 2.4% |
| T161 field fixes | 25.8 | 2.3% |
| T133 noise floor | 21.8 | 2.0% |
| T163 corpus field truth | 20.0 | 1.8% |
| T130 bench-curate | 19.2 | 1.7% |
| teardown + P0-B/C/A | 18.5 | 1.7% |
| T170 installer extras | 17.3 | 1.6% |
| T147 freshness | 17.3 | 1.6% |
| T146 TERMINADO seal | 13.1 | 1.2% |

The bench cache plus its nine consumers (T128–T136) were 55% of the run; T137–T162 ~150 s; the
post-teardown blocks T163–T170 ~74 s; the serial prefix T1–T127 ~250 s spread over ~125 small
blocks that share one sandbox and one ledger.

## What changed

- **`USCHA_JOBS=N` (N > 1) is opt-in.** Unset, `1`, `0` or a non-number is the serial suite; every
  `pj_unit` call is then a plain function call in the same shell, so the suite runs the same
  commands in the same order with the same output. `USCHA_COVERAGE=1` forces serial. The job count
  is capped at the cores the machine reports (`nproc`, `getconf`, `NUMBER_OF_PROCESSORS`, then 1).
- **`uscha-kit/tests/_jobs.sh`** (test-only, bash 3.2): `pj_unit NAME FN` runs a unit in a
  background subshell with its counters zeroed, its `PASS FAIL` delta in its own result file and
  its stdout+stderr in its own log; `pj_collect` — the barrier — waits, replays the logs in launch
  order and sums the deltas. A unit that leaves no result file is one FAIL that names it.
- **What runs in parallel:** the three bench-cache passes start right after the sandbox init and
  overlap the serial prefix (the barrier sits where they used to run, before the first consumer);
  T128–T162 run as units, collected before the serial tail and the teardown; T163–T171 run as
  units, collected before the acceptance emitter. The prefix stays serial.
- **Shared state, resolved, not assumed away:** T142+T143 are one unit; the `.top-cases.json`
  merge shared by T137/T138/T141/T145 takes a directory lock in `_harness.sidecar` (their keys are
  disjoint, so the order does not matter); the coverage-mode `pyin` spools each call into its own
  `mktemp` directory instead of one fixed `pyin.py`.
- **The ritual stays serial:** `tools/release.py` runs step 4 with `USCHA_JOBS=1`, and CI does not
  set it. Flipping the default is a later release, after CI shows equivalence.

## Measured on this machine (16 cores)

Measured on this machine (16 cores, Windows, empty HOME): **17.7 min serial -> 7.5 min with
`USCHA_JOBS=8`** (1060 s -> 451 s, ~2.35x), the same commit, both runs fully green.

CI runners (2–4 cores) will show much less: the serial prefix, ~4 minutes, now bounds the run.

## Equivalence, full suite

Both full runs of the same tree, diffed: the two logs are **byte-identical** (657 lines, same
order -- every unit's output is replayed in launch order); `RESULTADO BASE`, `RESULTADO` and
`ACCEPTANCE` carry the same values; the 49 sidecar files under `uscha-kit/reports/junit/`
parse to the same content; and `reports/junit/uscha-acceptance.xml` is identical once its
timestamps are normalized. Against the v2.7.0 serial log the 2.8.0 serial log differs only by
the two T171 lines and the counts they add. A second parallel run (447 s) was byte-identical
again. Two parallel runs on one machine are evidence, not a flake study: flipping the default
waits for CI.

## Acceptance

`AC-PJ-01..07` (smoke T171): the serial path is today's path (unset, `1`, `0`, a non-number and
coverage mode are byte-identical; the ritual pin; CI unset); a parallel run of the same units is
equivalent (log, tallies, merged sidecar); the bash-3.2 floor is a static scan with teeth; the
coverage spool is unique under concurrency and the sidecar merge is locked; AC-PJ-05 is the red
probe (a barrier that drops one unit's result file turns the comparator red and counts it as one
FAIL); AC-PJ-06 is the shipped probe against v2.7.0; AC-PJ-07 pins the wiring (no unit running at
the bench consumer, the serial tail, the teardown or the emitter).

## Not in this release

A block-level pool over the serial prefix (T1–T127): it now bounds the parallel run, and it needs
a block-by-block dependency analysis of ~125 blocks that share one sandbox and one ledger.

## Also fixed

**The suite's exit code now reflects every counted failure.** The status was frozen at the
teardown, so a check counted as failed after it (T163 onward, and the parallel units collected
before the acceptance emitter) printed in `RESULTADO` but left the process exit 0. The release
ritual was never exposed -- it refuses on any `fail` count in `RESULTADO` -- but a CI job judges by
the exit code alone, so a red check there could have passed a cell. Pre-existing; closed here
because this release is the one about the instrument, and pinned by AC-PJ-07. Green runs are
unaffected.

Suite: __SUITE__ checks · 0 fail; acceptance __ACC__.
