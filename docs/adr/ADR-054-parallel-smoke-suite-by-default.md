---
governs:
  - uscha-kit/tests/smoke-engine.sh
  - uscha-kit/tests/_jobs.sh
  - tools/release.py
  - .github/workflows/smoke.yml
---
# ADR-054: The smoke suite runs in parallel BY DEFAULT — unset USCHA_JOBS is min(cores, 8) jobs, and USCHA_JOBS=1 is the serial escape hatch

## Status: Accepted (2.9.0)

## Context

ADR-053 (2.8.0, amended 2.8.1) made the suite parallel only when asked and said what a flip would
need: evidence that the parallel path measures the same thing, on the small CI runners, before the
ritual or CI used it. The evidence now in hand:

- **Locally**, a full serial and a full parallel run of one tree produced byte-identical logs, the
  same acceptance and the same sidecars, twice (16-core Windows: 17.7 min serial, 7.5 min with 8
  jobs; the serial prefix, ~4 min, now bounds it).
- **On CI**, AC-PJ-01..09 pass on all six cells, macOS bash 3.2 included, driving mini-suites in
  parallel through the shipped library. What had NOT run on CI was the full suite in parallel:
  the first such run was this release's branch push, and it found a defect (below).
- The owner approved making the parallel suite the default.

A default is a claim about every run nobody configured: the ritual, a contributor's first
`bash uscha-kit/tests/smoke-engine.sh`, the `publish.yml` fallback. It is the instrument, so the
flip is an ADR, and the way back stays one environment variable.

## Decision

- **Default parallel.** With `USCHA_JOBS` unset or empty the job count is `min(cores, 8)`; 8 is the
  measured setting. Cores are resolved as before (`nproc`, `getconf _NPROCESSORS_ONLN`,
  `NUMBER_OF_PROCESSORS`, then 1): a machine that reports one core is serial.
- **An explicit value keeps its meaning.** `USCHA_JOBS=N` with N above 1 is parallel capped at the
  cores (an explicit 64 on 16 cores is 16, not 8); `1` and `0` are serial. **A non-number is
  serial** (fail safe: a typo never starts a parallel run) and the suite says so. `USCHA_COVERAGE=1`
  still forces serial.
- **The escape hatch is the 2.8.1 serial path.** `USCHA_JOBS=1` runs `pj_unit` as a plain function
  call in the current shell: no subshell, no buffering, no background process, no trap. AC-PD-07
  compares it byte for byte with the v2.8.1 library.
- **The ritual runs the default.** `tools/release.py` no longer sets `USCHA_JOBS`; the environment
  passes through, so a human who wants the serial suite exports `USCHA_JOBS=1` first.
- **CI runs the default in every cell but one.** In the six-cell grid (tag or manual dispatch) the
  `ubuntu-latest`/py3.8 entry carries `"jobs":"1"` (that cell is `ubuntu-22.04` since 2.10.1:
  `ubuntu-latest` became 26.04, which has no Python 3.8 build); the suite step exports `USCHA_JOBS` from it only
  when the cell sets one (`MATRIX_JOBS`), so the escape hatch is measured on every tag and the
  reduced grid keeps its shape. `publish.yml`, whose suite step runs only when no smoke run exists
  for the exact bytes, takes the default like any other run.
- **The suite states its mode.** `smoke-engine.sh` prints `suite mode: parallel, N jobs` or
  `suite mode: serial (reason)` once, right after `pj_init`, to **stderr**. A merged log (`2>&1`,
  how CI and the release evidence capture it) differs between modes by exactly that one line, and
  an evidence diff must say so. Separate stdout is not claimed identical: a unit's stderr goes into
  its log in parallel and straight to stderr in serial (AC-PJ-01 pins the serial side). The line is
  printed by the suite, never by the library, so the mini-suites AC-PJ-02 compares stay comparable.
- **The ritual echoes the mode and warns.** `tools/release.py` prints the suite's `suite mode:`
  line and, when `ACCEPTANCE` is not n/n, a WARNING naming the unmeasured criteria. It does not
  refuse: UNMEASURED is legitimate at X (AC-DF-01 when X touches the engine, AC-GM-08 without
  coverage.py).
- **A shared sidecar is merged by every writer.** See the defect below; AC-PD-09 scans for it.
- **One seam, no test branch.** Core detection moved into `pj__cores`. The table test redefines it
  after sourcing the library to simulate a machine; the production path is the same code either
  way, and a library without the function (v2.8.1) ignores the redefinition.

## The defect the first CI run found

The first full-suite parallel run on CI (windows-latest/py3.8, 4 jobs) printed
`ACCEPTANCE: 374/383` with AC-T-07, AC-T-08, AC-T-12 and AC-T-18..23 unmeasured, and the cell was
green. T137 wrote `.top-cases.json` with a plain overwrite while T138, T141 and T145 merge into it
under a lock. Serial, T137 always ran first; in parallel, a T138 merge that landed before T137's
final write was erased by it. The defect was latent since 2.8.0 for anyone using `USCHA_JOBS=N`;
the serial default never hit it, and the other cells and the writer's 8-job run got 383/383 by
schedule. Fixed by `merge=True` on T137, pinned by AC-PD-09 (a static scan of every `sidecar(`
call: a file with more than one writer needs `merge=True` on all of them, with a mutated copy as
teeth) and made visible by the ritual's warning (AC-PD-10). After the fix all six cells measured
385/385 with nothing unmeasured, the two Windows cells included. Lesson: a parallel run whose green
exit hides unmeasured criteria is the instrument failing silently; the acceptance line is read,
not trusted.

## Consequences

- `bash uscha-kit/tests/smoke-engine.sh` is ~2x faster on a workstation and gains less on a 2–4
  core runner. A failure is still read in a log replayed in launch order, as before.
- A red that appears only in parallel is a real finding about shared state between units, not a
  flake: `USCHA_JOBS=1` reproduces the serial result, and the ubuntu/py3.8 cell does so on tags.
- Rollback is one line each: `USCHA_JOBS=1` for a human, `PJ_DEFAULT_JOBS=1` in the library for
  everyone, a `jobs` field on more cells for CI.

## Out of scope

- A block-level pool over the serial prefix (T1–T127), as in ADR-053.
- Raising 8: it is the setting that was measured, not a limit of the design.

## Acceptance

`AC-PD-01..10` (smoke T172). AC-PD-01 is the resolve table over simulated core counts, with a copy
whose default is one job as its teeth; AC-PD-07 is the shipped probe against v2.8.1. AC-PD-02
reads UNMEASURED on a machine that reports one core; AC-PD-04 and AC-PD-05 read UNMEASURED from an
extracted kit (no repo-root script or workflow). AC-PJ-01 and AC-PJ-02 now name `USCHA_JOBS=1`
wherever they mean serial. AC-PD-09 is the shared-sidecar guard and AC-PD-10 the ritual's mode echo
and unmeasured-acceptance warning, each with a mutated copy as teeth.
