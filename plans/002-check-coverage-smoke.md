# Plan 002: Add smoke coverage for `check-coverage`

> **Executor instructions**: Follow step by step. Run every verification command and
> confirm the expected result before moving on. On any "STOP condition", stop and report.
> When done, update this plan's row in `plans/README.md`.
>
> **Drift check (run first)**:
> `git diff --stat b803c98..HEAD -- dev-loop-kit/.claude/skills/specloop-devloop/qa_ledger.py dev-loop-kit/tests/smoke-engine.sh`
> If either changed, compare the "Current state" excerpts against the live code before
> proceeding; on a mismatch, STOP.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: tests
- **Planned at**: commit `b803c98`, 2026-07-05

## Why this matters

`check-coverage` is a gate: `exit 0` if a repo's coverage is at/above a threshold, `exit
1` if below or if no coverage report exists. It reads a real coverage report and decides
an exit code, and it has **zero** smoke coverage. It is small and low-risk, which makes
this a cheap win that closes a real gap: a regression in the threshold comparison or the
"no report = below" fail-closed behavior would otherwise go unnoticed.

## Current state

Engine: `dev-loop-kit/.claude/skills/specloop-devloop/qa_ledger.py`. Tests:
`dev-loop-kit/tests/smoke-engine.sh` (161 checks, `T1`..`T47`).

**What `check-coverage` does** — `cmd_check_coverage` at qa_ledger.py:1170-1188:

```python
def cmd_check_coverage(args):
    ledger = _load(args.ledger)
    cfg = _repo_cfg(ledger, args.repo)
    threshold = args.threshold
    if threshold is None:
        threshold = ledger["config"].get("defaults", {}).get("coverage_threshold", 60)
    cov = coverage(cfg["path"], cfg["type"])
    pct = cov["pct"]
    below = pct < threshold
    if not cov["report_found"]:
        print(... "NO coverage report found ... -> treat as BELOW.")
        sys.exit(1)                         # no report == fail-closed
    print(f"... coverage {pct}% vs threshold {threshold}% -> {'BELOW' if below else 'OK'}")
    sys.exit(1 if below else 0)
```

CLI (argparse at qa_ledger.py:4349-4353): `check-coverage --ledger PATH --repo NAME
--threshold FLOAT`. `--threshold` defaults to the config's `coverage_threshold` (60).
Requires a ledger whose config lists the repo.

**How a Cobertura coverage fixture is written** — see the existing `T13` block (search
`== T13`), which creates `repo-c/coverage.xml`:

```
<coverage lines-valid="10" lines-covered="8" line-rate="0.8" version="7.4"></coverage>
```

`coverage()` for a `python`-type repo reads that Cobertura file and yields `pct` (80% for
the line above). Use the same shape.

**Smoke conventions** — same as noted in `plans/001-pit-check-smoke.md` §"Current state":
sandbox is `cd`-ed; `run()`/`chk()` helpers; init a fresh ledger with
`run init --config <cfg>.json --out <L>.json` (note: `init` uses `--out`, NOT `--ledger`).
Exemplar for a fresh-ledger block: `T45` (search `== T45`) creates its own config + ledger.

## Commands you will need

| Purpose            | Command                                    | Expected on success |
|--------------------|--------------------------------------------|---------------------|
| Run the test suite | `bash dev-loop-kit/tests/smoke-engine.sh`  | `RESULTADO: <N> ok · 0 fail`, exit 0 |

Run from repo root `C:\Work\AI\SpecLoop`.

## Scope

**In scope**: `dev-loop-kit/tests/smoke-engine.sh` — add ONE block, `T49`.

**Out of scope**: the engine (`qa_ledger.py`), all version/changelog/manifest files, and
the `== T44 sync quintuple ==` block (your block goes before T44).

## Git workflow

- Branch: `advisor/002-check-coverage-smoke`.
- One commit, conventional style, e.g. `test(smoke): cover check-coverage gate (T49)`.
- Do NOT push/PR unless asked.

## Steps

### Step 1: Insert the T49 block before `== T44`

Find `echo "== T44 sync quintuple` and insert this immediately before it (after the T48
block if plan 001 landed; order among T48/T49/T50 does not matter, but all go before T44):

```bash
echo "== T49 check-coverage: gate de umbral (OK / BELOW / sin report = fail-closed) =="
printf '{ "defaults": { "acceptance_file": "ACCEPTANCE.md" },\n  "repos": [ {"name":"cov","path":"covrepo","type":"python"}, {"name":"nocov","path":"nocovrepo","type":"python"} ], "integration": {"enabled": false} }\n' > cc-cfg.json
mkdir -p covrepo nocovrepo
# Cobertura: line-rate 0.85 -> 85% (lines-valid/lines-covered coherentes con line-rate)
cat > covrepo/coverage.xml <<'EOF'
<?xml version="1.0"?>
<coverage lines-valid="20" lines-covered="17" line-rate="0.85" version="7.4"></coverage>
EOF
run init --config cc-cfg.json --out L-cc.json >/dev/null
chk "coverage 85% >= threshold 60 -> OK exit 0" 0 run check-coverage --repo cov --threshold 60 --ledger L-cc.json
chk "coverage 85% < threshold 90 -> BELOW exit 1" 1 run check-coverage --repo cov --threshold 90 --ledger L-cc.json
chk "sin report de coverage -> fail-closed exit 1" 1 run check-coverage --repo nocov --threshold 60 --ledger L-cc.json
```

**Verify**: `bash dev-loop-kit/tests/smoke-engine.sh` → `· 0 fail`, exit 0, and three new
`ok` lines under `== T49`.

### Step 2 (only if the OK check fails with "NO coverage report found")

If the first `check-coverage` printed `NO coverage report found` (i.e. the OK check got
exit 1 instead of 0), `coverage()` is looking under `reports/` for this repo type. Move
the fixture: replace the `cat > covrepo/coverage.xml` line so it writes to
`covrepo/reports/coverage.xml` instead (add `mkdir -p covrepo/reports`). Re-run. If it
**still** reports no report found, STOP and report — the coverage path resolution differs
from what T13 implies and needs a human.

### Step 3: Confirm scope

**Verify**: `git status --short` shows only `dev-loop-kit/tests/smoke-engine.sh` modified.

## Test plan

- New `T49` block covering: coverage above threshold (OK/exit 0), below threshold
  (BELOW/exit 1), and no report at all (fail-closed/exit 1).
- Pattern to follow: `T45` (fresh config + `--out` ledger + `run` assertions).
- Verification: `bash dev-loop-kit/tests/smoke-engine.sh` → `0 fail`, three new `ok` lines.

## Done criteria

ALL must hold:

- [ ] `bash dev-loop-kit/tests/smoke-engine.sh` exits 0, prints `· 0 fail`.
- [ ] Total ok count = previous baseline + 3.
- [ ] `grep -c "== T49" dev-loop-kit/tests/smoke-engine.sh` returns `1`.
- [ ] `git status --short` shows ONLY the smoke file modified.
- [ ] `plans/README.md` row for 002 updated to DONE.

## STOP conditions

- Drift check shows `qa_ledger.py` changed and the `cmd_check_coverage` excerpt or the
  CLI flags no longer match.
- After Step 2's fallback, `coverage()` still finds no report — do not fake the pct or
  weaken the assertion; report the path issue.
- A pre-existing check (T1–T47) that passed before now fails.

## Maintenance notes

- If the coverage-report search path for `python` repos changes, this fixture's location
  may need to move with it (that is what Step 2 guards).
- Reviewer: confirm the fixture is a static Cobertura file, no test run involved.
