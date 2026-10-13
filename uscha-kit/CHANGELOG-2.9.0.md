# uscha-kit 2.9.0 — the smoke suite runs in parallel by default: unset USCHA_JOBS is min(cores, 8) jobs, USCHA_JOBS=1 is the serial escape hatch (ADR-054) (2026-10-12)

## What changed

ADR-053 shipped the parallel suite as opt-in and left the ritual and CI serial until there was
evidence it measures the same thing. The owner approved the flip on the evidence then in hand
(full serial and parallel logs of one tree byte-identical, twice; AC-PJ-01..09 green on all six CI
cells including macOS bash 3.2). The first full-suite parallel run on CI then found a real defect
(below), so the flip ships with its fix and its guard. What changed:

- **The default is parallel.** `USCHA_JOBS` unset or empty runs `min(cores, 8)` jobs; a machine that
  reports one core is serial. An explicit `USCHA_JOBS=N` keeps its meaning (capped at the cores);
  `1`, `0`, a non-number (fail safe: a typo never starts a parallel run) and `USCHA_COVERAGE=1` are
  the serial suite, the same commands as 2.8.1 and no trap.
- **The ritual runs the default.** `tools/release.py` no longer sets `USCHA_JOBS`; it passes the
  environment through, so `USCHA_JOBS=1 python tools/release.py ...` is a serial ritual. It now
  echoes the suite's `suite mode:` line and prints a WARNING when the acceptance line is not n/n
  (UNMEASURED is legitimate at X, so it warns and never refuses).
- **CI runs the default in every cell but one.** In the six-cell grid (tag or manual dispatch)
  ubuntu/py3.8 carries a `jobs` field and the suite step exports `USCHA_JOBS=1` from it, so the
  serial escape hatch is measured on every tag and manual dispatch (the three-cell branch grid has
  no such cell). `publish.yml` takes the default in its fallback suite step.
- **The suite says which mode it ran.** One line, `suite mode: parallel, N jobs` or
  `suite mode: serial (reason)`, on stderr. In a merged `2>&1` log (how CI and the release
  evidence capture it) the two modes differ by exactly that line. Separate stdout is not claimed to
  be identical: a unit's stderr goes to its log in parallel and straight to stderr in serial.

## Fixed: a sidecar race the serial suite could never show

The first full-suite parallel run on CI (windows-latest/py3.8, 4 jobs) ended
`ACCEPTANCE: 374/383` with AC-T-07, AC-T-08, AC-T-12 and AC-T-18..23 unmeasured, and the cell was
green. Cause: T137 wrote `.top-cases.json` with a plain overwrite while T138, T141 and T145 merge
into the same file. Serial, T137 always ran first; in parallel, when T138 merged before T137's final
write, T137 replaced the file and T138's criteria vanished. It was latent since 2.8.0 for anyone
using `USCHA_JOBS=N`; the serial default never hit it, and the other three CI cells and the local
8-job run got 383/383 by schedule. T137 now merges (`merge=True`), and `AC-PD-09` scans every
`sidecar(` call of the suite and refuses a file written by more than one block unless every writer
merges. Because a green exit hid it, the ritual now warns on an unmeasured acceptance (`AC-PD-10`).

## How it is pinned

`AC-PD-01..10` (smoke T172): the resolve table over simulated core counts (a function seam,
`pj__cores`, redefined after sourcing; no test branch in production), the default path as a real
parallel mini-suite equal to the serial one, the escape hatch, the ritual (AST walk, no
`USCHA_JOBS`), the workflow (exactly one serial cell, from its embedded JSON), the mode line, a
shipped probe against v2.8.1, a truth-pass over the docs, the shared-sidecar guard and the
ritual's mode echo and warning. Each has teeth. AC-PJ-01 and AC-PJ-02 now say `USCHA_JOBS=1`
wherever they mean serial, and the ritual and workflow claims AC-PJ-01 carried moved to AC-PD-04
and AC-PD-05.

## Evidence

One full run of the tree as first built (before the sidecar fix above), in the new default mode (8
jobs on a 16-core Windows machine, empty HOME): 521 s, exit 0, `RESULTADO: 463 ok · 0 fail`,
`ACCEPTANCE: 383/383`. Against the 2.8.1 parallel log its merged (`2>&1`) log differed only by the
`suite mode: parallel, 8 jobs` line, the reworded T171 header and ok line, the new T172 header and
ok line, the check count (+1), the acceptance count (+8) and the version lines. That run was
schedule luck for T137/T138, as the CI run showed; the final tree adds AC-PD-09 and AC-PD-10 and
was validated by standalone extraction of the touched blocks, not by a second full run.

Measured after the fix: the fixed tree's full suite on all six CI cells (manual dispatch, run
38338054335) -- five parallel (3 jobs on macOS, 4 on Ubuntu and Windows) and the serial
ubuntu/py3.8 cell -- each `RESULTADO: 463 ok · 0 fail` and `ACCEPTANCE: 385/385`, no criterion
unmeasured. The two Windows cells, which lost nine criteria to the race before the fix, are among
them. If a later run is red, `USCHA_JOBS=1` is the way back and the finding is about state shared
between units.

Suite: 463 checks · 0 fail; acceptance 385/385.
