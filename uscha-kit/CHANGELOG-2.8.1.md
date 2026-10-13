# uscha-kit 2.8.1 — the parallel suite can no longer hang on a killed unit or leave a mess behind (ADR-053, amended) (2026-10-12)

## What was wrong

Two defects on the opt-in parallel path (`USCHA_JOBS=N`), both left by the 2.8.0 review:

- **A hang.** The throttle counted a unit as running until its `.done` marker existed. A unit whose
  wrapper was killed from outside (SIGKILL, OOM) never wrote it, so the next `pj_unit` spun forever
  and a CI job would sit until its timeout instead of failing.
- **A mess.** Ctrl-C or SIGTERM of the main suite while units ran orphaned the units and left the
  scratch directory behind.

## The fix

- A unit whose `.done` is missing but whose wrapper pid no longer answers `kill -0` counts as
  finished. Collection is unchanged and fail-closed: no result file is one FAIL naming the unit.
- In parallel mode only, `pj_init` installs INT and TERM traps that kill the pending units, remove
  the scratch directory and exit 130 or 143. There is no EXIT trap, so the suite's own stays intact.
  Not covered: a unit's own children (a running python), and a trap fires only when the foreground
  command ends.

## How it is pinned

`AC-PJ-08` and `AC-PJ-09` (smoke T171), each bounded and each with teeth: a copy of `_jobs.sh`
without the liveness check hangs and is killed by the bound; a copy without the traps leaves the
scratch directory and live units behind. The serial default runs the same commands as 2.8.0 and
installs no trap (AC-PJ-09 reads `trap -p`).

Suite: 462 checks · 0 fail; acceptance 375/375.
