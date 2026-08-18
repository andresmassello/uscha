# ISSUES-DEFERRED

Findings the QA loop surfaced that are **below the severity gate**
(`BLOCKER | CRITICAL | HIGH`). They are recorded here rather than fixed, because the loop's
rule is *converge, don't chase zero*: a pass that keeps fixing MEDIUMs never ends, and every
extra changed line is risk the change did not need.

They are deferred, not forgiven. Each carries the evidence that found it.

---

## 2026-07-23 — QA loop over releases 1.46.1 → 1.48.1 (3 cycles, converged)

### D-01 (MEDIUM) — the mirador discards the phase it already derived — **RESOLVED in 1.49.0**
`uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py` · `cmd_dashboard`

> **Resolution (kit 1.49.0):** `loops[]` entries now carry `"phase": phase_d` — the full
> derived FSM value travels alongside the coarse 3-state badge, and the mirador renders it
> as a chip per repo. Regression: smoke T95. Entry kept for the record.

`loops[].state` collapses the 5-state FSM (`plan` / `build` / `qa` / `pr-ready` / `escalated`)
into 3 buckets (`active` / `converged` / `escalated`), so "never touched" and "measured but
pre-QA" both render as `active` with `iters: 0`. The full value is computed one line earlier
(`phase_d`) and thrown away.

- **Cost if ignored:** anyone wanting finer status in the mirador has to re-derive
  `_derive_phase` themselves — the exact duplication this release just removed.
- **Fix when scheduled:** add `"phase": phase_d` to the `loops` entry (free — already computed)
  and let the template opt into the detail while `state` stays the coarse badge.
- **Not gated because:** the coarse badge is not WRONG, only lossy; `iters` already
  distinguishes a virgin repo from one mid-loop. Found by the `improve` pass, cycle 3.

### D-02 (LOW) — `.claude/uscha-progress.json` has no schema marker — **RESOLVED in 1.82.0**
`uscha-kit/templates/scripts/uscha_progress.py` (producer) ·
`uscha_statusline.py` + the `uscha-status` skill (consumers)

> **Resolution (kit 1.82.0):** `uscha_progress.py::main()` now writes `"schema":
> "uscha/progress@1"` as the first key of the state dict, mirroring `QA-LEDGER.json`'s own
> `schema` marker. Verified both consumers tolerate the new key without change:
> `uscha_statusline.py` reads only named fields via `.get()`/`s["..."]`-on-known-keys, and the
> `uscha-status` skill's contract (`SKILL.md`) likewise names only specific fields — neither
> asserts the key set. No smoke assertion checks the exact key set of
> `.claude/uscha-progress.json` either, so none needed extending. Entry kept for the record.

The file grew from a handful of flat fields to ~17, including the nested `repos` map, with no
`schema` field — unlike `QA-LEDGER.json`, which carries `"schema": "dev-loop/qa-ledger@1"` for
exactly this reason.

- **Cost if ignored:** producer and consumers ship in lockstep today and every read is
  `.get()`-guarded, so it degrades safely. It bites only if a project ends up with a stale
  `uscha_statusline.py` beside a fresh `uscha-progress.json` — then there is no way to tell a
  shape mismatch from a legitimately-absent (unmeasured) field.
- **Fix when scheduled:** add `"schema": "uscha/progress@1"` now, while the shape is simple.
- **Not gated because:** no current failure mode; all reads already degrade. Found by the
  `improve` pass, cycle 3.

### D-03 (LOW) — coverage measures the engine, not the auxiliary scripts — **RESOLVED in 1.82.0**
`uscha-kit/tests/smoke-engine.sh` (the `USCHA_COVERAGE=1` seam)

> **Resolution (kit 1.82.0):** a second choke point, `runpy()`, mirrors `run()` but takes the
> script path as its own first argument and derives `--source` from that script's own
> directory (`dirname`) at call time — one absolute path per call, never a fixed multi-root
> constant. Two things ruled out a fixed `COV_SRC2`/`COV_SRC3` pair: `coverage.py`'s `--source`
> flag is NOT additive across repeated occurrences (measured empirically — the SECOND flag
> silently wins and the first is dropped, which the first attempt at this fix got wrong before
> the auxiliary scripts turned up absent from the report and the bug was caught), and a
> comma-joined multi-path list hits the same git-bash/MSYS hazard as `$COV_SRC` above.
> Routed through `runpy()`: the direct `uscha_progress.py`/`uscha_statusline.py` invocations in
> T88/T90/T91/T93, and the mirador renderer invocation in T80. Measured result: the auxiliary
> scripts are no longer absent from the report — `uscha_progress.py` 86%, `uscha_statusline.py`
> 88%, `mirador-render.py` 53% (see `ACCEPTANCE.md`, "Out of scope for measurement here", for
> the full breakdown and the `qa_ledger.py` re-measurement this also triggered). Entry kept for
> the record.

Coverage wraps `run()`, the choke point the suite drives the engine through (~370 subprocess
calls) — that yields 84.2% on `qa_ledger.py`. The statusline scripts (`templates/scripts/*`)
and the mirador renderer are exercised by T88/T90/T91/T93 and the mirador tests, but through
direct `"$PY" "$SCRIPT"` invocations that bypass the seam, so they contribute nothing. Note
they are **absent** from the report, not scored 0: coverage.py does not surface files it never
imported, so no `--source` entry can conjure them — only routing their invocations through the
seam will.

- **Cost if ignored:** the number is honest about what it measures (declared in
  `uscha.config.json` as `defaults._coverage_scope`), but a reader could take "84%" for the
  whole kit. The scripts stay unmeasured while carrying real logic (provenance labeling,
  odometer reads).
- **Fix when scheduled:** route the ~6 direct script invocations through a wrapper honoring the
  same `USCHA_COVERAGE` switch.
- **Not gated because:** the scope is declared, not hidden, and the engine is where the risk
  concentrates (13.3k of the kit's statements).

### Also surfaced, deliberately NOT enabled: ruff security rules
`ruff.toml`

Enabling ruff's `S` (bandit) rules yields 61 findings, all mapped HIGH by the engine — but they
are dominated by this codebase's deliberate design: `S603`/`S606`/`S607` flag `subprocess`
called with a **list of args**, which IS the safe form; `S110` flags documented best-effort
`try/except/pass`; `S101` flags asserts in tests. Gating on those would train the reader to
ignore the gate.

Two are architecturally real and blocked by kit constraints, recorded here so they are not
silently lost:

- **`S324` — `sha1` (3 uses).** Used for FINGERPRINTING findings (oscillation detection), not
  for security. The canonical fix, `usedforsecurity=False`, needs Python **3.9+**; the kit's
  floor is **3.8**. Cannot be applied without raising the floor.
- **`S314` — `ET.parse` on report files (7 uses).** ruff prescribes `defusedxml`, a **new
  dependency**, and the engine is stdlib-only *by design*. The real risk is an XML bomb in a
  poisoned report → DoS of the measurement engine (not RCE, not exfiltration), already wrapped
  in `try/except ParseError`. The stdlib-compatible mitigation is a **size guard before
  parsing** — worth a small ADR, not a silent patch.

## 1.69.0 fresh review — LOW (deferred, below the severity gate)

- **Delta twin render: interior newlines in a narrated statement break the .md table row**
  (the JSON and the OBS id survive; only the rendered view corrupts). Sanitize newlines in
  `_render_delta_md`.
- **`promote` ISSUES-DEFERRED dedupe is a raw substring test**: an OBS id merely mentioned
  in prose in that file suppresses its work item. Match on the structured `- [ ] OBS-` line
  shape instead.
- **`fidelity --config` default resolves against cwd**: running from another directory
  silently means no gate declared (unnamed absence). Consider resolving relative to the
  ledger, or naming the miss.

## 1.82.0 hygiene block — measured debt (open, decided by the human)

- ~~**Engine coverage is 58% against a declared threshold of 60**~~ (`qa_ledger.py`, 6266
  statements, 2656 missed — re-measured through the D-03 seam). The previously committed
  `reports/coverage.xml` read 84.2% but dated from 2026-07-23 (3788 valid lines) and was never
  re-measured across 24 releases while the engine grew: bench, bench-curate, the whole
  controlled-language subsystem shipped with their smoke checks but without the coverage
  report being regenerated. **Decision (2026-08-15, human):** ship the honest number, do not
  paper it over with hurried tests; open "raise engine coverage to >= 60" as backlog work,
  targeting the newest subsystems first (bench/lang-compare/curation branches the suite drives
  only through their happy paths). The threshold stays at 60 — lowering it to match would be
  the narrated fix.
  **RESOLVED 2026-08-18 (1.90.0), and the honest half of the sentence is WHY it moved:** the
  gap was the INSTRUMENT far more than the suite. Two choke points were blind. `uscha_top.py`
  sat inside the `--source` root but was only ever driven in-process from `python -` heredocs,
  so it reported 0% while 24 acceptance criteria were being measured against it; and every
  block written since ~T117 drives the engine from INSIDE its own python program
  (`subprocess.run([sys.executable, ENG, ...])`), whose children were plain interpreters — so
  `cmd_fastpath_eval` read 1/132 covered lines while T117 measured nine criteria against it.
  Closed with coverage.py's own documented multiprocess technique (a `sitecustomize` on
  `PYTHONPATH` plus `COVERAGE_PROCESS_START`, the same mechanism `cmd_golden_coverage` already
  used) plus a third `pyin()` choke point that spools a heredoc to a file so `coverage run` can
  take it. Measured after the widening: **`qa_ledger.py` 6967 statements, 934 missed = 86.6%;
  the whole measured surface 7860 valid / 6752 covered = 85.9%** — against the same suite,
  with `uscha_top.py` at 73.2% and `telemetry-extract.py` at 95.3% where it read 0%. New behaviour
  checks were added in the same release (T142 telemetry-extract, T143 the mirador aggregate and
  its three friendly failures, T144 `uscha top`'s read boundary and refusals), and they are
  worth having on their own, but they are NOT what moved the number: the instrument is. Same
  lesson as ADR-036 and recorded the same way — when the number is ugly, fix the instrument or
  leave the number ugly; when it then jumps, say which of the two happened. The threshold
  stays at 60.
- ~~**`USCHA_COVERAGE=1` over the full suite makes `AC-GM-08` fail**~~: `coverage.py`'s
  `COVERAGE_FILE` environment variable unconditionally overrides `cmd_golden_coverage`'s own
  isolated `data_file`, so the golden-coverage capture collides with the suite's data file.
  Reproduced on the unmodified 1.81.0 baseline (pre-existing, surfaced by D-03, not caused by
  it). **RESOLVED 2026-08-18 (1.90.0)**: `cmd_golden_coverage` now writes
  `COVERAGE_FILE` explicitly into the child's environment, pinned to the isolated `data_file`
  (set, not popped: popping leaves the rc file to win, which is right only while nothing else
  in the chain sets it, whereas setting is correct under both plain and `USCHA_COVERAGE=1`).
  The parent's own `coverage.Coverage(data_file=...)` was already safe -- constructor
  arguments are applied after the environment in `coverage/config.py`. T117's AC-GM-08 now
  runs the capture a SECOND time with a `COVERAGE_FILE` planted in the environment and
  requires the map to come back measured with the planted file's directory still empty; the
  assertion goes red with the fix reverted (verified by mutation).
- ~~**The instrument changed what it measured: the withheld oracle handed its own coverage
  hooks to every program it judged**~~ (found and closed inside 1.90.0, three instrumented
  runs apart). Widening the coverage seam with coverage.py's multiprocess hook made
  `USCHA_COVERAGE=1` turn T136 red — and only T136, and only under coverage. The chain, once
  the criterion was made to say *which* of its sub-measurements moved: seven bench archetypes
  flipped to `FAIL` because an oracle child could not start, and a py3.8 `bench-roundtrip`
  came back `3221225794` = `0xC0000142` (`STATUS_DLL_INIT_FAILED`) with an empty stderr —
  Windows refusing to create processes. The cause is not the sitecustomize the suite writes:
  **coverage.py 7.x ships `a1_coverage.pth` in site-packages, and a `.pth` runs BEFORE
  `sitecustomize`**, so `COVERAGE_PROCESS_START` alone starts a full `Coverage` in *every*
  python descendant, at interpreter start-up, and nothing downstream can opt a process out.
  Most of those descendants are the diamond-bench compiled implementations the oracle judges —
  fixture programs outside every `--source` root, so their data is empty by construction:
  `coverage combine` over the first run said *"Combined 600 files, skipped 13702"*, 96%
  recording nothing while each still paid an `import coverage` and a data file.
  **RESOLVED**: `_judged_env()` in the engine drops `COVERAGE_PROCESS_START` /
  `COVERAGE_PROCESS_CONFIG` from the environment of a program `_run_oracle_case` runs — a
  measurement that alters what it measures is a broken measurement, and this is the boundary
  where the alteration enters. `COVERAGE_FILE` is deliberately left alone: it names a data
  file, it does not turn anything on. Measured after: `bench` over the whole fixture leaves 1
  data file instead of hundreds, the run leaves 1,280 instead of 14,424, and the instrumented
  suite read exactly what the plain suite read at the time of the fix (432 ok / 0 fail, 177/178 —
  measured mid-release, before AC-RT-04 and T142–T144 were added). Pinned by T127's
  `reg-oracle-child-gets-no-coverage-hook`, which plants the variable in the engine's
  environment and requires the judged program to report `clean`; red with the guard reverted
  (verified by mutation). Two lessons, both cheap only in hindsight: a criterion that folds
  five measurements into one boolean must say which one moved (T136 now does), and an
  instrument gets a blast radius before it gets a seam.

## 1.86.1 fresh review (`uscha top` M1) — LOW (deferred, below the severity gate)

- ~~**`uscha_top._fit`/`_spread` measure width in codepoints, not display columns.**~~ `len(text)`
  counts Python codepoints; a CJK project name or a wide-glyph string occupies 2 terminal
  columns per codepoint on most terminals, so a name near the column budget can overflow the
  frame's fixed width and break the "never wider than the terminal" invariant the golden
  frames pin. Deferred while no fixture exercised a wide-char project name.
  **RESOLVED 2026-08-18 (1.90.0)**: `_dw` (East Asian Wide/Fullwidth = 2, combining marks = 0,
  everything else including East Asian *Ambiguous* = 1) is now the measurement behind `_fit`,
  `_cut`, `_pad`, `_spread`, `_wrap`, `_row`, `_obs_row`, `_pane` and `_burnup_line`; a wide
  character is dropped whole rather than split. The fixture the deferral asked for exists:
  `tests/fixtures/uscha-top/state/state-wide.json` with golden frames at 100x32 and 80x24,
  and T138 sweeps every width from 20 to 120 asserting display width <= cols. Ambiguous
  counting 1 is what keeps every pre-existing golden byte-identical (`_dw == len` on ASCII).
