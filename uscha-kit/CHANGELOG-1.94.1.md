# uscha-kit 1.94.1 — five ways a red thing read green: the audit fixes (2026-09-02)

An audit of the harness and the engine found five places where a failure was measured and then
thrown away, or an absence was rendered as a number. They are not five bugs so much as one
mistake wearing five costumes, and it is the mistake this whole method exists to refuse: a green
that nobody measured. Two of them lived in the SUITE — the instrument that is supposed to catch
exactly this — and could not be caught by running it, so they are pinned by a static scan of the
suite's own source, the way T106 pins version literals.

## What changed

All line numbers below are **pre-change**, as they stood at 1.94.0.

- **A `chk` inside a subshell counted for nothing** (`tests/smoke-engine.sh:465-466`, T8). Both
  golden-diff checks ran as `( cd g && chk ... )`, so `FAIL=$((FAIL+1))` incremented a COPY of the
  counter that died with the subshell: the check printed `FAIL` and the suite still exited 0.
  `golden-diff` already takes `--dir`, so the two calls now pass `--dir g` and never leave the
  cwd. `AC-AU-01` scans the suite's own source for the single-line `( cd <dir> && ... chk` form
  and fails if it reappears — that is the shape that shipped, and the shape the scan measures.
- **T85 ran after its verdict could reach anyone** (`tests/smoke-engine.sh:12090`, pre-move). It
  sat below `RESULTADO BASE` — where `SMOKE_STATUS` freezes the process exit code — AND below the
  acceptance emitter, which is handed `$FAIL`. So a red T85 changed neither the exit code nor
  `AC-06 smoke_suite_green`. The block moved up, immediately before `RESULTADO BASE`, which
  precedes both readers; its `set -e` comment was corrected (at the new position `set -e` is not
  on) and the `|| ... _RC=$?` guards were kept. `AC-AU-02` pins the line order. (`$FAIL` itself
  keeps moving after that line — the P0-A/B/C roll-ups increment it and the emitter does read
  them; only `SMOKE_STATUS` is frozen there.)
- **A corrupt JaCoCo report was summed as a measured zero**
  (`.claude/skills/uscha-devloop/qa_ledger.py:208-217`, `_jacoco_line_counter`). On `ET.ParseError`
  it returned `(0, 0)`, and `maven_coverage` / `gradle_coverage` / `ant_coverage` set
  `report_found: bool(files)` — so a module whose XML was truncated mid-write contributed nothing
  to the sums while the reading still called itself measured, and the surviving modules'
  percentage was published as the project's. `_jacoco_line_counter` now returns `None` on
  `ET.ParseError`, `OSError`, `ReportTooLarge` and on a counter attribute that is not an integer,
  and the three callers share one `_jacoco_result` helper (three hand-copied sums is how one of
  them drifts) that returns **`covered 0, missed 0, pct 0.0, report_found False`** as soon as any
  report failed to parse — the report paths are still listed. The zero matters as much as the
  flag: `readiness` scores coverage as `pct/threshold` WITHOUT consulting `report_found`, so an
  earlier draft that kept the survivors' `pct` beside `report_found: false` scored the repo 16.7
  on a question nobody asked while printing "coverage scored UNMEASURED"; `snapshot` likewise
  prints and persists that `pct`. End to end the truncated case now reads `coverage=0.0%
  (found=False)` in `snapshot`, `0.0` in the readiness coverage dimension, and exit 1 from
  `check-coverage` — the same shape every other reader in the file has had since 1.57: absence is
  never invented as a number. `AC-AU-03`, `AC-AU-04`.
- **An explicit linter report nobody could find was ingested as silence**
  (`.claude/skills/uscha-devloop/qa_ledger.py:1277-1279`, `_find_all`). With `explicit` given and
  missing, it returned `[]`, `ingest-gate` logged nothing and exited 0 — a mistyped `--ruff` read
  as a clean gate. It now takes the same fail-closed path an unparseable report takes
  (`_invalid_static_report`, exit 2), with the path named in the message. A glob that finds
  nothing is unchanged: nobody claimed that file existed. `AC-AU-05`.
- **`--repo integration` crashed two commands** (`qa_ledger.py:3110` `cmd_fastpath_eval`, `:3697`
  `cmd_cleanroom`): both read `_repo_cfg(...).get("path", ".")`, and the synthetic `integration`
  scope has no config entry, so they died with `no config entry for repo 'integration'`. Both now
  use `_scope_path`, the helper extracted for this exact crash class in 1.63. `cmd_phase:2968`
  keeps its own `args.repo != "integration"` guard plus `try/except SystemExit`: `_scope_path`
  would make the pair redundant, but the block is correct as it stands and this release does not
  touch it. `AC-AU-06`.

## Release infrastructure and docs

- **`publish.yml` no longer downgrades a running or red matrix into a one-cell fallback.** The
  single-sample lookup read "still running" and "completed, failed" identically — as "no run" —
  and fell through to running the suite here, which for a red SHA would have published over a
  measurement it could not change. It now POLLS for up to 40 minutes while the smoke run for that
  SHA is `queued`/`in_progress`, reuses it on `success`, and FAILS the job on any other
  conclusion. A `gh api` ERROR is retried rather than read as an answer, and "no run at all"
  needs two consecutive empty samples a minute apart — otherwise one API hiccup would downgrade a
  red matrix to the one-cell fallback, which is the same false green in a different place. A
  fully queued matrix can still outlast the 40-minute window; that is accepted and named in the
  file: the job fails closed and the tag can be re-pushed. The checkout gains `fetch-depth: 0` (the reason smoke.yml gives: AC-DF-01 cannot
  measure on a depth-1 clone) and a `coverage.py` install (so AC-GM-08 is measured on the fallback
  path too, not permanently skipped). `timeout-minutes` goes 20 → 80 so the poll plus a fallback
  suite fit. The fallback path now prints its own receipt saying what it actually measured — one
  cell, ubuntu-latest + py3.13, not the six-cell matrix. Not smoke-pinned: a T-block cannot run
  GitHub Actions, and claiming otherwise would be the over-claim this repo's rule 2 forbids.
- **CLAUDE.md rule 9** now says the release tag is pushed only once the `smoke` run for that exact
  SHA is green. `publish.yml` polls and fails closed, but the ritual must not lean on that.
- **`ACCEPTANCE.md` AC-FA-03 said "the committed HEAD engine"; the code pins tag `v1.86.1`**
  (`tests/smoke-engine.sh:8190`). The criterion now names the tag and states the policy the code
  already followed: the anchor is re-pointed at a later release only through a changelog line
  that says so. The same policy is now a comment beside the pin.
- **AC-T-19b deleted** (`tests/smoke-engine.sh:7846-7852` and its sidecar filter at `:8030`). It
  gated a py3.8 byte-identity frame on a uv-installed `cpython-3.8*` under one hard-coded Windows
  path; the glob matched on no CI cell and on no release machine, so `ok38` stayed `True` by
  absence — green without ever running — and it was excluded from the sidecar, so it closed no
  criterion and had no `ACCEPTANCE.md` row to remove. A check that cannot go red measures nothing.
  The real py3.8 evidence is the matrix's own py3.8 cells, which run the whole file.
  `CHANGELOG-1.88.0.md` still mentions the id: historical changelogs are the archive of what
  happened, and rewriting one to hide a retired check would be its own falsehood.

`AC-AU-01..06` (T149) measure all of it, through the `.au-cases.json` sidecar: the two static pins
over the suite's own source, and four behavioural pins over real temp fixtures — two maven modules
whose 50.0% collapses to `0.0% (found=False)` on `check-coverage`, `snapshot` AND the readiness
dimension once one of them is truncated, a `missed="N/A"` counter that reads UNMEASURED instead
of raising, a mistyped `--ruff` that exits 2 naming the path while a real report still exits 0, and
`fastpath-eval`/`cleanroom` on the `integration` scope no longer naming a config entry that never
existed. Acceptance goes 211 → 217 criteria; nothing was dropped.

Suite: __SUITE__ checks · 0 fail; acceptance __ACC__.
