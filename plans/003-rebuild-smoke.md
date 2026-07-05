# Plan 003: Add smoke coverage for `rebuild` (baseline + compare)

> **Executor instructions**: Follow step by step. Run every verification command and
> confirm the expected result before moving on. On any "STOP condition", stop and report.
> When done, update this plan's row in `plans/README.md`.
>
> **Drift check (run first)**:
> `git diff --stat b803c98..HEAD -- uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py uscha-kit/tests/smoke-engine.sh`
> If either changed, compare the "Current state" excerpts against the live code before
> proceeding; on a mismatch, STOP.

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: LOW
- **Depends on**: none (independent of 001/002; can land in any order)
- **Category**: tests
- **Planned at**: commit `b803c98`, 2026-07-05

## Why this matters

`rebuild` is the completeness test: it captures a baseline signature of the system, then
after the agent regenerates production code from the SPEC alone, scores whether the
regenerated system still matches (verdict `COVERS` / `PARTIAL` / `DIVERGE`). It has two
modes, a scored four-dimension comparison dominated by whether the preserved test suite
still passes, and it writes/reads a `REBUILD-BASELINE.json` artifact — all with **zero**
smoke coverage. A regression in the baseline-write or the compare-scoring would silently
mis-report how complete a specification is. This plan covers both modes and the dominant
"tests fail on regenerated code -> DIVERGE" path.

## Current state

Engine: `uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py`. Tests:
`uscha-kit/tests/smoke-engine.sh` (161 checks).

**What `rebuild` does** — `cmd_rebuild` at qa_ledger.py:2438 dispatches to
`_rebuild_baseline` (2444) or `_rebuild_compare` (2470). Both build a per-repo signature
via `_repo_signature` (2418): coverage %, test totals/pass/fail, prod/test LOC, the
test-file set, and acceptance done/total.

- **baseline** writes a JSON file (`--out`, default `REBUILD-BASELINE.json`) with
  `{"schema","created_at","config_repos","coverage_tolerance","acceptance_file","section","repos":{<name>:<signature>}}`.
  Returns normally (exit 0), prints where it wrote.
- **compare** (2470-2564) reads the baseline, re-signs the current tree, and scores four
  dimensions per repo:
  ```
  tests (dominant): no report -> 0.0 ; any failures+errors -> passed/total ;
                    else min(1, rebuilt.total / baseline.total)
  acceptance: done/total (of the current tree) when found & total>0
  coverage:   1.0 if within tolerance of baseline, else max(0, c1/c0)
  surface:    1 - |prod_loc1 - prod_loc0| / prod_loc0
  ```
  Weighted by `REBUILD_WEIGHTS = {"tests":60,"acceptance":20,"coverage":15,"surface":5}`
  (qa_ledger.py:2278), banded `COVERS>=90 · PARTIAL>=70 · DIVERGE<70`
  (`REBUILD_BANDS`, qa_ledger.py:2279). `--json` prints
  `{"score","verdict","weights","dimensions","coverage_tolerance","gaps",[...]}` and
  `sys.exit(0 if verdict == "COVERS" else 1)`.

CLI (argparse at qa_ledger.py:4521+): `rebuild --mode {baseline,compare}`
`--config PATH` (baseline) `--baseline PATH` (compare, default `REBUILD-BASELINE.json`)
`--out PATH` (baseline output) `--acceptance PATH` `--section TEXT`
`--coverage-tolerance FLOAT` `--json`.

**Fixture patterns to reuse** (from the existing suite):
- Cobertura coverage — `T13` (`covrepo/coverage.xml`): `<coverage lines-valid=".." lines-covered=".." line-rate="0.8" version="7.4"></coverage>`.
- JUnit — `T13` writes a wrapped junit under `reports/junit.xml`:
  `<testsuites><testsuite name="S" tests="5" failures="0" errors="0" skipped="0"/></testsuites>`.
- Fresh config + ledger — `T45` (`printf '{...}' > cfg.json` then `run init --config cfg.json --out L.json`).
  `rebuild` does NOT need a ledger — it reads the config directly — but it DOES need the
  repo directories to exist with the fixture files.

**Smoke conventions**: sandbox is `cd`-ed; `run()`/`chk()` helpers; value assertions via
`run ... --json | "$PY" -c "...; sys.exit(0/1)"`. See `plans/001-pit-check-smoke.md`
§"Current state" for the exact helper contracts.

## Commands you will need

| Purpose            | Command                                    | Expected on success |
|--------------------|--------------------------------------------|---------------------|
| Run the test suite | `bash uscha-kit/tests/smoke-engine.sh`  | `RESULTADO: <N> ok · 0 fail`, exit 0 |

Run from repo root `C:\Work\AI\SpecLoop`.

## Scope

**In scope**: `uscha-kit/tests/smoke-engine.sh` — add ONE block, `T50`.

**Out of scope**: the engine (`qa_ledger.py`), all version/changelog/manifest files, the
`== T44` block (your block goes before T44).

## Git workflow

- Branch: `advisor/003-rebuild-smoke`.
- One commit, conventional style, e.g. `test(smoke): cover rebuild baseline+compare (T50)`.
- Do NOT push/PR unless asked.

## Steps

### Step 1: Insert the T50 block before `== T44`

```bash
echo "== T50 rebuild: baseline escribe la firma; compare puntua COVERS / DIVERGE =="
mkdir -p rbrepo/src rbrepo/reports
cat > rbrepo/src/mod.py <<'EOF'
def add(a, b):
    return a + b
def mul(a, b):
    return a * b
EOF
cat > rbrepo/coverage.xml <<'EOF'
<?xml version="1.0"?>
<coverage lines-valid="10" lines-covered="8" line-rate="0.8" version="7.4"></coverage>
EOF
cat > rbrepo/reports/junit.xml <<'EOF'
<testsuites><testsuite name="S" tests="5" failures="0" errors="0" skipped="0"/></testsuites>
EOF
printf -- "# ACCEPTANCE\n\n- [x] uno\n- [x] dos\n" > ACCEPTANCE-rb.md
printf '{ "defaults": { "acceptance_file": "ACCEPTANCE-rb.md" },\n  "repos": [ {"name":"rb","path":"rbrepo","type":"python"} ], "integration": {"enabled": false} }\n' > rb-cfg.json
# baseline: escribe la firma
chk "baseline escribe REBUILD-BASELINE -> exit 0" 0 run rebuild --mode baseline --config rb-cfg.json --out RB.json
"$PY" -c "import json,sys; d=json.load(open('RB.json',encoding='utf-8')); sys.exit(0 if 'rb' in d['repos'] and d['repos']['rb']['tests']['total']==5 else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   la firma baseline capturo el repo (tests total=5)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL baseline no capturo la firma esperada"; }
# compare sobre el MISMO arbol -> todas las dimensiones 1.0 -> COVERS
chk "compare mismo arbol -> COVERS exit 0" 0 run rebuild --mode compare --baseline RB.json --json
run rebuild --mode compare --baseline RB.json --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
sys.exit(0 if d['verdict'] == 'COVERS' and d['dimensions']['tests'] == 1.0 else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   arbol sin cambios -> COVERS (tests dim 1.0)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL compare del mismo arbol no da COVERS"; }
# el arbol 'regenerado' rompe tests -> la dimension dominante cae -> NO COVERS + gap
cat > rbrepo/reports/junit.xml <<'EOF'
<testsuites><testsuite name="S" tests="5" failures="4" errors="0" skipped="0"/></testsuites>
EOF
chk "compare con tests que fallan -> exit 1 (no COVERS)" 1 run rebuild --mode compare --baseline RB.json --json
run rebuild --mode compare --baseline RB.json --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
ok = (d['verdict'] != 'COVERS' and d['dimensions']['tests'] < 0.5
      and any('fail' in g for g in d['gaps']))
sys.exit(0 if ok else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   tests rotos al regenerar -> DIVERGE/PARTIAL + gap reportado"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL compare no detecto la divergencia de tests"; }
```

**Verify**: `bash uscha-kit/tests/smoke-engine.sh` → `· 0 fail`, exit 0, and six new
`ok` lines under `== T50`.

### Step 2: Confirm scope

**Verify**: `git status --short` shows only `uscha-kit/tests/smoke-engine.sh` modified.

## Test plan

- New `T50` block covering: baseline writes a valid signature file; compare on an
  unchanged tree → COVERS/exit 0 with tests-dim 1.0; compare after the preserved suite
  starts failing → not-COVERS/exit 1 with a `tests fail` gap.
- Patterns to follow: `T13` (coverage + junit fixtures) and `T45` (fresh config).
- Verification: `bash uscha-kit/tests/smoke-engine.sh` → `0 fail`, six new `ok` lines.

## Done criteria

ALL must hold:

- [ ] `bash uscha-kit/tests/smoke-engine.sh` exits 0, prints `· 0 fail`.
- [ ] Total ok count = previous baseline + 6.
- [ ] `grep -c "== T50" uscha-kit/tests/smoke-engine.sh` returns `1`.
- [ ] `git status --short` shows ONLY the smoke file modified.
- [ ] `plans/README.md` row for 003 updated to DONE.

## STOP conditions

- Drift check shows `qa_ledger.py` changed and the `_rebuild_compare` scoring, the
  `REBUILD_WEIGHTS`/`REBUILD_BANDS`, or the CLI flags no longer match the excerpts.
- The COVERS check does not give exit 0 / verdict COVERS **even though** the tree is
  unchanged between baseline and the first compare. Likely causes to report (do NOT edit
  the engine): (a) `coverage()` reads coverage from a different path for python repos, so
  the coverage dim dropped — try moving `coverage.xml` to `rbrepo/reports/coverage.xml`
  once; if still failing, STOP; (b) the acceptance file did not parse as 2/2 done, so the
  acceptance dim dropped — verify `ACCEPTANCE-rb.md` has two `- [x]` lines and no
  unchecked boxes. If neither explains it, STOP and report the `--json` `dimensions`
  object.
- The DIVERGE check yields COVERS after you set `failures="4"` — report the `--json`
  output; do not weaken the assertion.
- Any pre-existing check (T1–T47) that passed before now fails.

## Maintenance notes

- If `REBUILD_WEIGHTS` or the band thresholds change, the COVERS/DIVERGE expectations
  here may shift — update the fixture numbers so the two verdicts still land on opposite
  sides of a band boundary (the point of the test is the boundary behavior, not exact
  scores).
- Reviewer: confirm the DIVERGE case mutates only `rbrepo/reports/junit.xml` between the
  two compares (nothing else), so the tests dimension is unambiguously the cause.
- Deferred out of this plan (fine to skip): the `PARTIAL` middle band and the
  `--coverage-tolerance` boundary — cover them later if rebuild's scoring gets more
  load-bearing.
