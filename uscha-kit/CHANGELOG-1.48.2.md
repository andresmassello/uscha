# uscha-kit 1.48.2 — the engine measures its own coverage (2026-07-23)

`ACCEPTANCE.md` had left an open fork since 1.44.0: instrument the engine's coverage, or
declare the exemption in config with provenance. **Resolved by measuring.** A measurement kit
that cannot measure its own coverage is a weak calling card. Smoke suite: 379/379.

## The problem was the shape of the suite, not the will
The engine is exercised almost entirely through **subprocess** — the smoke is bash, and it
drives `qa_ledger.py` ~370 times. Instrumenting that normally means the `COVERAGE_PROCESS_START`
+ `.pth` dance in site-packages. It was unnecessary here: the suite already funnels every one
of those calls through a single `run()` choke point. Wrapping that one function measures
everything.

```bash
USCHA_COVERAGE=1 bash uscha-kit/tests/smoke-engine.sh
coverage combine && coverage xml -o reports/coverage.xml
```

**Opt-in by design.** Off by default, so the normal suite stays fast and `coverage.py` is NOT
a dependency of running the tests. `--source` is ONE absolute path (the suite runs from a temp
sandbox): git-bash rewrites only the first POSIX path embedded in an argument, so a
comma-joined list would reach Windows Python half-translated — and coverage.py does not report
never-imported files anyway, so extra roots buy nothing. The distributable twin
`uscha-kit/skills` is absent from the report because the suite never executes it (`$QL` points
at `.claude/skills`), not because a flag excluded it.

## The number, and what it does NOT cover
**84.2%** on the engine, against a threshold of 60 now DECLARED in `uscha.config.json`
(provenance: a human requirement, not the kit's default opinion — kit 1.17.0). The report is
Cobertura at `reports/coverage.xml`, exactly the path and shape `cobertura_coverage()` already
ingests; nothing new had to be taught to the engine.

Honest limit, recorded in config as `defaults._coverage_scope` and in `ISSUES-DEFERRED.md`
(D-03): the number covers **`qa_ledger.py`**. The auxiliary scripts (`templates/scripts`, the
mirador renderer) are exercised by the suite but invoked outside the `run()` seam, so they
contribute nothing to it. Calling 84.2% "the kit's coverage" would be exactly the inflated
claim this project exists to remove.

## Self-application: 35 → 100
With coverage measured, every readiness dimension is now MEASURED for this repo and the
score reads **100.0 — READY**: acceptance 6/6 (green tests, not checkboxes), ADR complete,
coverage 84.2%, static gate clean (ruff + mypy), convergence closed by a real 3-cycle QA loop.
The path was: stale snapshot cleared (35 → 50) → static gate wired (→ 72.2) → QA loop
converged (→ 83.3) → coverage instrumented (→ 100).

Regression: smoke **T94** — instrumentation stays opt-in (the suite runs with no `coverage.py`
present), and a Cobertura report at `reports/coverage.xml` is ingested as MEASURED.
