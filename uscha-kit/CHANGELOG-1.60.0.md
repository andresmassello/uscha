# uscha-kit 1.60.0 — the golden↔source mapping, derived by measurement (2026-08-02)

Phase 1.5, and the close of a debt ADR-004 opened deliberately. A golden freezes behavior, so
changing code a golden exercises is never a trivial change — but the engine had no way to know
WHICH source files a golden covers, so the `forbid_when_golden_touched` veto shipped as
*deferred* rather than as a gate that pretended to measure. This release builds the mapping and
unblocks the veto. Designed through the method's own front door (`/uscha-adr-refine` → ADR-006:
three decisions, each with its considered alternative, before a line of code).

## `golden-coverage` — subcommand 32

```bash
python qa_ledger.py golden-coverage --harness tests/golden/harness-x.py --golden tests/golden/x.approved.json
```

Runs the harness under `coverage.py` and records the source files that **actually executed**
into `golden.coverage.json` at the repo root — the same root-level, human-visible, PR-reviewed
convention `golden.scrub.json` already established (REUSE-FIRST: the engine does not enumerate
goldens and did not need to learn a tree walk for this).

**The mapping is derived, not declared.** A `governs:`-style glob list — the pattern spec-drift
uses — was the cheap option and was rejected as the primary source: a declared mapping is a
*claim about* what a golden exercises, and it rots the moment the code moves. Spec-drift can
live with that because it is advisory; a **veto that blocks work cannot**. Static import
analysis was rejected too: the harnesses drive their subject through a **subprocess**, where an
import graph sees nothing and would report near-empty coverage that reads as "safe".

That subprocess boundary is the whole engineering problem. Instrumentation is injected into
every python the harness spawns (a `sitecustomize` on `PYTHONPATH` plus
`COVERAGE_PROCESS_START` — the documented multiprocess technique, and the same PYTHONPATH
injection this repo's fault tests already use). Measuring only the parent would record an empty
map, which reads as "this golden covers nothing" — the one lie that would let the veto pass.

## The veto: opt-in, then fail-closed

```json
"fast_path": { "forbid_when_golden_touched": true }
```

Absent or `false` → **no `golden_touched` signal at all**, behavior identical to 1.57.0+ (the
same "absent block = feature off" rule `fast_path` and `spec_drift` already follow). Shipping
it always-on would silently strip the fast path from every project whose goldens predate this
release. Rigor stays a human declaration (INV-RIGOR-02: the ratchet only tightens, and only
when a human turns it).

Declared → every ambiguity denies, with the reason named: a touched mapped file (naming the
golden and the file), a missing manifest, a golden with no entry. A **malformed** manifest
exits 2 rather than degrading into a silent "no mapping" — under a declared veto that silence
would *grant* the shortcut the gate exists to deny. Same posture `golden.scrub.json` already
takes about its own rules.

**Provenance, not a freshness gate.** Every verdict carries the capture commit and coverage
tool version in the signal's `source`, so it always says which capture it trusted. There is
deliberately no staleness gate: an aged map's real risk is a *false negative*, which cannot be
detected without re-running the harness, and a gate on the map's age would be measuring age
while claiming to measure correctness.

## Two limits, named here rather than discovered in the field

- **`coverage.py` is Python-only.** A harness in another language cannot produce a map, so
  declaring the veto in such a project yields a permanent `DENY`. The remedy is not to declare
  it. It remains a **capture-time** dependency only — the engine is still stdlib-only at runtime.
- **File granularity over-fires on monolithic files.** Measured on this repo's own golden, the
  map contains exactly one file: the 7000-line engine. So here the veto would fire on nearly
  every engine change — close to useless locally, correct for a repo of small modules. When it
  errs, it errs toward more ceremony, never less.

## Measured against its own acceptance

`AC-GM-01..08`, all green. Smoke **T117** exercises each against a real git fixture whose
harness reaches its subject only through a subprocess. **AC-GM-08 was added after the first
seven were written**: those measured the veto's *consumption* and left its *production* — the
actual measurement, and the part that could silently return nothing — unmeasured. CI now
installs `coverage.py` so that criterion is measured rather than permanently skipped; the suite
still runs without it, reporting AC-GM-08 as UNMEASURED instead of passing it.

Acceptance for the repo as a whole: **28/28 measured green where `coverage.py` is installed** (CI, and the release machine); **27/28 with AC-GM-08 UNMEASURED** without it — the ingested `uscha-acceptance.xml` says which, per run, and is never averaged into a friendlier number. Suite: 402 checks.
