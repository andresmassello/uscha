---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/.claude/skills/uscha-characterize/SKILL.md
  - uscha-kit/uscha.config.json
---
# ADR-006: The golden↔source mapping is DERIVED BY MEASUREMENT, and the veto it unblocks is opt-in

## Status: Accepted

## Context
ADR-004 deferred `forbid_when_golden_touched` — the fast-path veto for "this change touches
code a golden froze" — for one honest reason: no golden↔source mapping existed in the engine,
and a gate that cannot measure must not ship as if it did. This ADR builds the mapping and
unblocks the veto.

Options considered:
- **A) Declare the mapping by hand** (a `governs:`-style glob list, as spec-drift uses for
  specs). Cheap and already patterned in the kit. Rejected as the primary source: a declared
  mapping is a *claim about* what a golden exercises, and it rots the moment the code moves
  without anyone noticing — the exact failure mode the method exists to remove. Spec-drift can
  live with declaration because it is advisory; a *veto* that blocks work cannot.
- **B) Derive it by measurement** — run the golden harness under coverage instrumentation at
  capture time and record the source files it actually executed. **Chosen.**
- **C) Static import analysis.** Rejected: the harnesses drive the subject through
  `subprocess` (see `tests/golden/harness-devloop-entry.py`), and a static import graph sees
  nothing across that boundary. It would report near-empty coverage and read as "safe".

## Decision

**Production.** `/uscha-characterize` runs the harness under `coverage.py` while producing the
`.received`, and records the measured file list in **`golden.coverage.json` at the repo root** —
the same location and shape convention as the existing `golden.scrub.json` (REUSE-FIRST: the
engine already reads one root-level, human-visible, PR-reviewed golden sidecar; it does not
need a second mechanism, nor a tree walk it has never done).

**Granularity: FILE level.** Line-level coverage is more precise on day one and starts lying on
day two — line numbers move with every edit, so consuming it would require re-anchoring old
lines to new ones through git hunks. File-level attribution stays true across edits.

**The veto is opt-in, then fail-closed.** `defaults.fast_path.forbid_when_golden_touched`
absent → the veto does not exist and behavior is identical to 1.57.0+ (the same "absent block =
feature off" rule `fast_path` and `spec_drift` already follow). Declared → every ambiguity
denies, with the reason named.

**Provenance, not a freshness gate.** The manifest records the capture commit and the coverage
tool version, and `fastpath-eval` carries them in the signal's `source` field, like every other
signal. There is deliberately **no staleness gate**: an aged map's real risk is a *false
negative* (the golden now exercises a file captured before it existed), and that cannot be
detected without re-running the harness. A gate on the map's age would be measuring age while
claiming to measure correctness — and the anti-ceremony meta-invariant forbids the weight.

**The map is not a human-approved artifact.** INV-GOLDEN-01 governs the `.approved` bytes,
which encode judgment. The coverage manifest is derived measurement; the agent may write it.

### Behavior, with the veto DECLARED
| Situation | Behavior |
|---|---|
| Diff touches a file the manifest maps to a golden | `DENY`, naming the golden and the file |
| Diff touches only unmapped files | signal passes; other signals decide |
| A golden in the tree has no entry (manifest absent, or incomplete) | `DENY` naming it — "could not measure" never grants the shortcut |
| No golden exists in the tree | the signal passes: nothing can be covered. This is a measurement, not an absence of one |
| Manifest malformed | exit 2, a config error — same posture as `golden.scrub.json`, which refuses to degrade into "no rules" in silence |
| `coverage.py` unavailable at CAPTURE time | characterize refuses to write a map; an empty map would read as "covers nothing" |

With the veto **not** declared, the signal is absent from the output entirely.

<!-- Refined during implementation: the first table said only "manifest absent". A fresh
     review reproduced the gap that wording left open -- a manifest knowing SOME goldens made
     the signal assert "nothing is covered" about one it had never measured, and ALLOW. The
     rule is per-golden, and a repo with no goldens is measured, not denied. -->

## Reasons
- A measured mapping cannot rot into a comfortable lie; a declared one can, and a veto that
  blocks work on a stale claim is worse than no veto.
- Opt-in keeps rigor a human declaration (INV-RIGOR-02: the ratchet only tightens, and only
  when a human turns it). Shipping the veto always-on would silently strip the fast path from
  every project whose goldens predate this release.
- File granularity errs toward MORE ceremony when it errs — never less.

## Consequences
+ The veto ADR-004 deferred becomes measurable, and ADR-004 can be superseded rather than left
  open indefinitely.
+ Coverage instrumentation already exists in this repo's own suite (`USCHA_COVERAGE=1`), so the
  capture-time technique is proven here before it ships to anyone.
- **`coverage.py` is Python-only.** A harness written in another language cannot produce a map,
  so declaring the veto in such a project yields a permanent `DENY`. The remedy is to not
  declare it. Named here rather than discovered in the field.
- **File granularity over-fires on monolithic files.** In THIS repo — one 7000-line engine —
  the veto would fire on nearly every engine change, making it close to useless locally while
  being correct for a repo of small modules. Accepted, and recorded so nobody reads the
  over-firing as a defect.
- `coverage.py` becomes a **capture-time** dependency for anyone who wants the veto. The engine
  itself stays stdlib-only at runtime; nothing about this changes that contract.

## Implementation Plan
- Affected paths: `uscha-kit/.claude/skills/uscha-characterize/SKILL.md` (capture under
  instrumentation), `qa_ledger.py` (a `golden-coverage` subcommand that records a MEASURED map,
  plus a `golden_touched` signal inside `cmd_fastpath_eval`), `uscha-kit/uscha.config.json`
  (document the flag), kit `README.md`.
- Patterns: `_load_scrub_rules` for the manifest loader — strict shape, `exit 2` on malformed,
  never a silent degrade; the existing `sig(name, value, threshold, source, ok)` helper for the
  new signal; exact path comparison (no glob dialect needed — the map holds real paths).
- Tests: smoke **T117**, feeding `AC-GM-01..07` per-criterion through the sidecar pattern
  already used by T113/T114 (and deleted before the run, so a crash yields UNMEASURED).

## Verification
- [ ] veto undeclared → no `golden_touched` signal; verdict identical to the same diff pre-feature (AC-GM-01)
- [ ] veto declared + manifest absent → `DENY` naming `golden_touched` (AC-GM-02)
- [ ] veto declared + diff touches a mapped file → `DENY` naming the golden and the file (AC-GM-03)
- [ ] veto declared + diff touches only unmapped files → the signal passes (AC-GM-04)
- [ ] the signal's `source` carries the capture commit and the coverage tool version (AC-GM-05)
- [ ] malformed manifest → exit 2, never a silent "no mapping" (AC-GM-06)
- [ ] capture without `coverage.py` → no map written, never an empty one (AC-GM-07)
