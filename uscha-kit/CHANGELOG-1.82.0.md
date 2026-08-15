# uscha-kit 1.82.0 — hygiene block: schema marker, a dead re-parse, a copy-paste hazard closed, coverage widened (2026-08-15)

Four small, independent fixes accumulated as `ISSUES-DEFERRED.md` LOWs and one review note across
the 1.80.0/1.81.0 cycles. No new subcommand, no ADR, no engine behavior change beyond the one
explicitly measured below — the point of this release is closing the deferred, not adding.

## `uscha-progress.json` gets a schema marker (D-02)

`uscha_progress.py::main()` now writes `"schema": "uscha/progress@1"` as the first key of the
state dict, matching `QA-LEDGER.json`'s own `schema` field. Both consumers were checked, not
assumed: `uscha_statusline.py` reads named fields only (`.get()` / direct key access on keys it
already knows), and the `uscha-status` skill's contract names specific fields the same way —
neither asserts the key set, so the new key changes nothing for either. No smoke assertion
checks the exact key set of the file either.

## A redundant re-parse, removed (cosmetic)

`qa_ledger.py::_bench_entry`'s fidelity block re-opened and re-parsed the same
`COMPILATION.json` a second time (`c2`) a few lines after the function already parsed it once
(`c`). The second parse only ever runs when the first one succeeded — reaching the fidelity
block requires `unit` to be set, which only happens after that earlier parse — so `c` is always
defined there. The block now reuses `c` directly. Verified zero behavior change: `bench
--fidelity --json` over `uscha-kit/tests/fixtures/diamond-bench` is byte-identical before and
after the edit.

## `bench-curate --dir` gets a disambiguating alias

`bench --dir` means the bench root; `bench-curate --dir` means the compilation subdir (e.g.
`c-opus`) — a copy-paste hazard the 1.80.0 review flagged and recorded rather than fixed. Now
`bench-curate --compilation` is a backward-compatible alias for the same `--dir` destination:
`--compilation c-opus --list` behaves identically to `--dir c-opus --list` (`AC-BC-04`, T130).
`--dir` keeps working unchanged. Both the ES and EN doc tables note the alias.

## Coverage seam widened to the auxiliary scripts (D-03)

`USCHA_COVERAGE=1` wrapped exactly one choke point — `run()`, the ~370 subprocess calls the
suite drives `qa_ledger.py` through — so the statusline scripts and the mirador renderer,
invoked directly as `"$PY" "$SCRIPT" ...` outside that seam, were absent from the coverage
report, not scored 0. A second seam function, `runpy()`, mirrors `run()` for these calls: it
takes the script path as its own first argument and derives `--source` from that script's own
directory at call time — one absolute path per invocation, never a fixed multi-root constant.
That design was not the first attempt: a fixed pair of `--source` flags was tried first and
looked plausible, but `coverage.py`'s `--source` option is not additive across repeated
occurrences — the second flag silently wins and the first is dropped, confirmed by direct
measurement, not documentation. The auxiliary scripts turning up absent from the report a
second time is what caught it. Routed through `runpy()`: the direct `uscha_progress.py` /
`uscha_statusline.py` invocations in T88/T90/T91/T93, and the mirador renderer invocation in
T80.

Re-measuring surfaced a real number, not a formality. `qa_ledger.py` alone is now **58%**
(6266 statements, 2656 missed) — down from the 84.2% recorded on 2026-07-23, and genuinely so:
that date's committed `reports/coverage.xml` covered only 3788 valid lines total, against 6266
statements in `qa_ledger.py` alone today. The engine has grown faster than its smoke coverage
since (bench, bench-curate, the controlled-language subsystem) — a fact this release surfaces,
not one it caused or hides. The newly-measured auxiliary scripts: `uscha_progress.py` 86%,
`uscha_statusline.py` 88%, `mirador-render.py` 53%. `telemetry-extract.py` (same skill
directory as the mirador renderer) reports 0% — present in the seam's `--source` root but never
invoked by the suite; D-03 named only the renderer, so this was already true, only now visible.

Measuring this also surfaced one unrelated pre-existing issue, flagged separately rather than
folded into this change: running the full suite with `USCHA_COVERAGE=1` makes `AC-GM-08` fail,
because `coverage.py`'s `COVERAGE_FILE` environment variable unconditionally overrides the
isolated `data_file` `cmd_golden_coverage` sets for its own harness capture (confirmed by
reading `coverage/config.py`; reproduced on the unmodified 1.81.0 baseline before this change
touched anything). It costs a handful of harmless test-fixture lines in the combined total and
two red criteria under that specific combination (`AC-GM-08` itself and `AC-06`, which cascades from any red check); it does not affect the `qa_ledger.py`
or auxiliary-script figures above, which live in separate data files the collision never
touches. Left for a dedicated fix.

## What the review caught

The blind review re-measured the highest-stakes claim from scratch — `USCHA_COVERAGE=1` over
the full suite, `coverage combine`, `coverage xml` — and every number in the committed
`reports/coverage.xml` matched **exactly** (6266/3610/57.6% on the engine, the four auxiliary
figures, the 0.5762 roll-up); it also confirmed the AC-GM-08 collision reproduces on the
untouched 1.81.0 baseline via a detached worktree, so it is surfaced by D-03, not caused by it.
Three documentation findings, all fixed: (1) MEDIUM — the regeneration recipe in
`uscha.config.json` was unfollowable: `coverage xml` without `--ignore-errors` exits 1 and
writes nothing (a golden-coverage capture leaves a `sitecustomize.py` from an already-deleted
temp dir in the shared data file); the flag is now in the recipe with the reason. (2) MEDIUM —
the `_coverage_scope` narrative still described the auxiliary scripts as "absent from the
number", the exact limitation D-03 removed; rewritten. (3) LOW — "one always-red criterion"
undercounted: `AC-06` (zero suite failures) cascades from any red check, so it is two;
corrected in ACCEPTANCE.md and here. The review also confirmed change 2 byte-identical via a
pre-change engine extracted from HEAD, and change 3's argparse alias on both interpreters.

`AC-BC-04` measured green (T130 extended). Suite: 417 checks, 0 failures; acceptance
**129/129** criteria measured green.
