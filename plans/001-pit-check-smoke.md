# Plan 001: Add smoke coverage for `pit-check` (mutation gate)

> **Executor instructions**: Follow this plan step by step. Run every verification
> command and confirm the expected result before moving on. If anything in "STOP
> conditions" occurs, stop and report — do not improvise. When done, update the status
> row for this plan in `plans/README.md`.
>
> **Drift check (run first)**: from the repo root
> `git diff --stat b803c98..HEAD -- uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py uscha-kit/tests/smoke-engine.sh`
> If either file changed since this plan was written, compare the "Current state"
> excerpts below against the live code before proceeding; on a mismatch, treat it as a
> STOP condition.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: LOW
- **Depends on**: none
- **Category**: tests
- **Planned at**: commit `b803c98`, 2026-07-05

## Why this matters

`pit-check` is a **blocking** QA gate (`exit 1` when the mutation score is below the
declared minimum). It enforces the project's CONSTITUTION invariant "Tests efectivos —
coverage miente": it parses a PIT `mutations.xml` and decides whether the tests actually
ASSERT behavior. It has a non-trivial classifier (which mutation statuses count as
killed, which are excluded from the denominator) — and it is the **only** subcommand of
its kind with **zero** tests in the smoke suite. A parsing or classification bug here
silently lets weak tests through (false PASS) or blocks good code (false FAIL), and
nothing would catch it. This plan gives it a deterministic smoke test, closing that gap.

## Current state

The engine is one file: `uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py`.
The tests are one bash suite: `uscha-kit/tests/smoke-engine.sh` (161 checks today,
blocks labelled `T1`..`T47`; it prints `RESULTADO: <PASS> ok · <FAIL> fail` and exits
non-zero if any check failed).

**What `pit-check` does** — `cmd_pit_check` at qa_ledger.py:3171 and `_pit_metrics` at
qa_ledger.py:2896. The classifier constants at qa_ledger.py:2878-2882:

```python
_PIT_KILLED = {"KILLED", "TIMED_OUT", "MEMORY_ERROR"}
_PIT_EXCLUDED = {"NON_VIABLE", "RUN_ERROR"}   # dropped from the denominator entirely
```

The metric loop (qa_ledger.py:2900-2927), abbreviated:

```python
for mut in root.iter("mutation"):
    status = (mut.get("status") or "").upper()
    if status in _PIT_EXCLUDED:      # NON_VIABLE / RUN_ERROR -> excluded++, skip
        excluded += 1; continue
    total += 1
    detected = (mut.get("detected") or "").lower() == "true"
    if detected or status in _PIT_KILLED:   # detected=true OVERRIDES status
        killed += 1; continue
    # else: NO_COVERAGE -> no_cov++, SURVIVED -> survived++
# mutation_score = round(100*killed/total, 1)   (100.0 if total==0)
# test_strength  = round(100*killed/(killed+survived), 1)
```

CLI surface (argparse at qa_ledger.py:4582-4587): `pit-check --report PATH`
`--min-score FLOAT` (default 60.0) `--top INT` `--json`. Exit codes: `0` PASS
(`mutation_score >= min_score`), `1` BELOW-GATE, `2` when no report is found / XML is
unparseable. The `--json` output shape:
`{"verdict": "PASS"|"BELOW-GATE", "report": ..., "min_score": ..., "metrics": {"total","killed","survived","no_coverage","excluded","mutation_score","test_strength"}, "hotspots": [...]}`.

**The smoke suite's conventions you must match** — read the top of
`uscha-kit/tests/smoke-engine.sh` (lines 1-90). Key facts:
- It runs inside a temp sandbox; `cd "$SB"` is already done. Create fixture files/dirs
  with relative paths (they land in the sandbox).
- Helper `run() { PYTHONIOENCODING=utf-8 "$PY" "$QL" "$@"; }` invokes the engine.
- Helper `chk "<desc>" <expected_exit> run <subcommand> <args...>` asserts an exit code
  and bumps `PASS`/`FAIL`.
- For value assertions, the idiom is to pipe `run ... --json` into
  `"$PY" -c "..."` that `sys.exit(0/1)`, then `&& { PASS=$((PASS+1)); echo "  ok ..."; }
  || { FAIL=$((FAIL+1)); echo "  FAIL ..."; }`.
- **Exemplar to copy**: block `T46` (search for `== T46`) shows the exact fixture +
  `chk` + `--json`/`$PY` assertion pattern. Model your new block on it.

## Commands you will need

| Purpose            | Command                                        | Expected on success |
|--------------------|------------------------------------------------|---------------------|
| Run the test suite | `bash uscha-kit/tests/smoke-engine.sh`      | last line `RESULTADO: <N> ok · 0 fail`, exit 0 |
| Parse-check engine (only if you had to touch it — you should NOT) | `python -c "import ast; ast.parse(open('uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py',encoding='utf-8').read())"` | exit 0 |

Run from the repo root `C:\Work\AI\SpecLoop`. `bash` is available (Git Bash). If `python`
is not on PATH, try `py` or `python3` — the suite auto-detects, but your standalone
parse-check may need the working one.

## Scope

**In scope** (the only file you modify):
- `uscha-kit/tests/smoke-engine.sh` — add ONE new block, `T48`.

**Out of scope** (do NOT touch):
- `uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py` — the engine. This plan
  only ADDS a test for existing behavior. If the test reveals a real bug, that is a STOP
  condition (see below), not a licence to edit the engine.
- Any `VERSION` / `uscha.config.json` / `CHANGELOG` / `plugin.json` /
  `marketplace.json` — no version bump: adding a smoke test is not a release.
- The `== T44 sync quintuple ==` block and everything after it — your block goes
  **before** T44 so the version-sync check stays last.

## Git workflow

- Branch: `advisor/001-pit-check-smoke`.
- One commit; conventional-commit style (match `git log --oneline -5`), e.g.
  `test(smoke): cover pit-check mutation gate (T48)`.
- Do NOT push or open a PR unless the operator asked for it.

## Steps

### Step 1: Locate the insertion point

Open `uscha-kit/tests/smoke-engine.sh` and find the line:

```
echo "== T44 sync quintuple de version: VERSION = config = plugin.json = marketplace.json =="
```

Your new `T48` block goes **immediately before** that line (T45/T46/T47 already sit
before T44; you are adding after T47 and before T44).

### Step 2: Insert the T48 block

Insert exactly this block (a single PIT fixture that exercises KILLED, the
`detected=true` override, SURVIVED, NO_COVERAGE, and NON_VIABLE+RUN_ERROR exclusion):

```bash
echo "== T48 pit-check: mutation gate desde un mutations.xml (efectividad, no coverage) =="
cat > mutations.xml <<'EOF'
<mutations>
<mutation detected="true"  status="KILLED"><sourceFile>a.py</sourceFile></mutation>
<mutation detected="true"  status="KILLED"><sourceFile>a.py</sourceFile></mutation>
<mutation detected="true"  status="KILLED"><sourceFile>a.py</sourceFile></mutation>
<mutation detected="true"  status="SURVIVED"><sourceFile>a.py</sourceFile></mutation>
<mutation detected="false" status="SURVIVED"><sourceFile>b.py</sourceFile></mutation>
<mutation detected="false" status="NO_COVERAGE"><sourceFile>b.py</sourceFile></mutation>
<mutation detected="false" status="NON_VIABLE"><sourceFile>c.py</sourceFile></mutation>
<mutation detected="false" status="RUN_ERROR"><sourceFile>c.py</sourceFile></mutation>
</mutations>
EOF
# total = killed(4: 3 KILLED + 1 detected-override) + survived(1) + no_cov(1) = 6
# NON_VIABLE + RUN_ERROR excluidos del denominador -> excluded=2
# mutation_score = 100*4/6 = 66.7 ; test_strength = 100*4/(4+1) = 80.0
chk "score 66.7 >= min-score 60 -> PASS exit 0" 0 run pit-check --report mutations.xml --min-score 60
chk "score 66.7 < min-score 70 -> BELOW-GATE exit 1" 1 run pit-check --report mutations.xml --min-score 70
run pit-check --report mutations.xml --min-score 60 --json 2>/dev/null | "$PY" -c "
import json, sys
m = json.load(sys.stdin)['metrics']
ok = (m['total'] == 6 and m['killed'] == 4 and m['survived'] == 1
      and m['no_coverage'] == 1 and m['excluded'] == 2
      and abs(m['mutation_score'] - 66.7) < 0.05
      and abs(m['test_strength'] - 80.0) < 0.05)
sys.exit(0 if ok else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   NON_VIABLE/RUN_ERROR fuera del denominador; detected=true cuenta como killed"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL metricas del mutation report mal computadas"; }
chk "report inexistente -> exit 2 (no evidencia)" 2 run pit-check --report no-such.xml --min-score 60
```

**Verify**: `bash uscha-kit/tests/smoke-engine.sh` → last line `RESULTADO: 165 ok · 0
fail`, exit 0. (161 existing + 4 new checks in T48 = 165. If your local baseline was not
161, the total is baseline+4 — confirm `0 fail` and that the four `T48` lines all print
`ok`.)

### Step 3: Confirm only the intended block was added

**Verify**: `git diff --stat uscha-kit/tests/smoke-engine.sh` shows only that file
changed, additions ≈ 30 lines, 0 deletions. `git status --short` shows no other modified
tracked file.

## Test plan

- New block `T48` in `uscha-kit/tests/smoke-engine.sh`, covering: (a) PASS at/above
  the gate, (b) BELOW-GATE below it, (c) the metric math incl. the NON_VIABLE/RUN_ERROR
  exclusion and the `detected=true` override, (d) the missing-report exit-2 path.
- Structural pattern to follow: the existing `T46` block (fixtures + `chk` + `--json`/`$PY`
  assertion).
- Verification: `bash uscha-kit/tests/smoke-engine.sh` → `0 fail`, four new `ok` lines
  under the `== T48` header.

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `bash uscha-kit/tests/smoke-engine.sh` exits 0 and prints `· 0 fail`.
- [ ] The run's total ok count is exactly the previous baseline + 4.
- [ ] `grep -c "== T48" uscha-kit/tests/smoke-engine.sh` returns `1`.
- [ ] `git status --short` shows ONLY `uscha-kit/tests/smoke-engine.sh` modified (no
      engine file, no version files).
- [ ] `plans/README.md` status row for 001 updated to DONE.

## STOP conditions

Stop and report back (do not improvise) if:

- The drift check shows `qa_ledger.py` changed and the "Current state" excerpts
  (`_PIT_KILLED`/`_PIT_EXCLUDED`, the metric loop, the CLI flags, the `--json` shape) no
  longer match the live code.
- The suite fails on a **T48** assertion after you have confirmed the fixture is
  byte-for-byte as written above. This most likely means a real behavior difference in
  `pit-check` (e.g. `detected` no longer overrides `status`, or the exclusion set
  changed) — report the actual vs expected numbers; do NOT edit the engine to make the
  test pass, and do NOT weaken the assertion to force green.
- Any pre-existing check (T1–T47) that passed before now fails — you have broken the
  sandbox state; revert and report.

## Maintenance notes

- If `pit-check`'s classification ever changes (e.g. a new PIT status, or `test_strength`
  formula), this fixture's expected numbers must be updated in lockstep — that is the
  point of the test.
- Reviewer should confirm the fixture stays a **static** file with **no** external tool
  invocation (no `pitest`, no Maven) — determinism is the contract.
- The fixture deliberately mixes `detected=true status=SURVIVED` to lock the
  detected-overrides-status branch; keep that row if you regenerate the fixture.
