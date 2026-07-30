# ADR-003: Fast-path entry is granted by measured signals, never by opinion

## Status: Accepted

## Context
The ceremony floor is flat: a one-line fix and a schema migration pay the same entry cost
(discovery/ADR/full spec package). The landing claims "rigor where the stakes justify it", but
no mechanism implements the inverse — less rigor where stakes are measurably low. External
criticism of the SDD category ("overkill for small changes") lands on uscha precisely here.

Options considered:
- **A) Ask the operator/agent up front whether the change is small.** Rejected: an agent's
  answer is narrative opinion (the exact thing the method forbids as a gate), and a human's
  answer before the diff exists is a prediction — every change looks small before it starts.
- **B) Classify by measured signals from the actual diff, re-checked during the run.** Chosen.
- **C) No fast path; keep the flat floor.** Rejected: leaves the method's central promise
  ("rigor where the stakes justify it") without a mechanism, and the criticism unanswered.

## Decision
`/uscha-devloop` gains a fast-path mode, entered only when `qa_ledger.py fastpath-eval`
returns `ALLOW` from **measured** signals:

- `max_files_changed: 3` and `max_loc_delta: 80` — measured by the engine from
  `git diff --numstat`, never self-reported. Deliberately far below the simplicity gate's
  normal-change budgets (20 files / 400 lines): fast-path is for trivial changes, and a
  threshold that denies too much is cheap to loosen with data, while one that admits too much
  costs trust to tighten after an accident.
- `protected_paths` glob list (default includes `**/migrations/**`, `**/*.approved`, `db/**`):
  any touched file matching → `DENY` regardless of size.
- **Base ref**: default is the merge-base with `origin/main`, falling back to local `main`.
  **Any ambiguity — no git repo, unresolvable base, unreadable history — is `DENY`** with the
  reason named. Fail-closed: "could not measure, so the ceremony is skipped" is precisely the
  hole this design must not have. Consequence accepted: a freshly initialized repo has no
  fast-path until a base exists.
- **INTENT as request**: `fastpath-eval --intent "<one sentence>"` evaluates and records in a
  single ledger entry (request, signals, verdict — full provenance). Without `--intent` the
  call is a **dry-run**: verdict shown, nothing enters fast-path mode. Empty/whitespace intent
  counts as absent. The human *requests* the fast path; the engine verifies and decides.
- **Escalation invariant**: `fastpath-eval` re-runs inside the devloop (at minimum before the
  PR step). Thresholds exceeded mid-run → state `ESCALATED`, PR step blocked, and the run must
  produce **ADR + ACCEPTANCE** before continuing — not a full discovery: mid-build the shape
  already exists; what is missing is the recorded decision and a checkable done. Both ledger
  records are kept; nothing is overwritten.
- **Override asymmetry** (also `INV-RIGOR-02` in `CONSTITUTION.md`): the human can always
  force the full path; nothing and nobody can force `ALLOW` over a `DENY`. Humans may add
  rigor, never remove it.
- Absent `fast_path` block in config → feature off, behavior identical to the previous
  release.

Fast-path skips *ceremony* (discovery/ADR up front), never *approval* (rule 03) and never
*asserting tests* (rule 04): `require_asserting_test` demands ≥1 new/modified test visible in
ingested evidence, or the criterion stays open and readiness is capped.

## Reasons
- Classification from the measured diff is the only gate consistent with "facts block,
  guesses advise" — intent is honored as a request, verified twice against reality.
- Fail-closed on ambiguity mirrors the INV-GOLDEN hook lesson (1.55.2): a guard that yields
  when confused is not a guard.
- Escalation makes the classification *live*: it is re-derived from state, not frozen at entry.

## Consequences
+ A one-line fix enters the loop with one sentence of intent and one asserting test — the
  flat-floor criticism gets a mechanical answer, recorded and auditable in the ledger.
+ The fast-path verdict has the same evidentiary shape as every other gate (value, threshold,
  source, timestamp).
- Two more config knobs and one more subcommand to maintain.
- A legitimate small change in a young repo (no merge-base yet) is denied the shortcut.
- Threshold values are policy, not truth: they will need field calibration, and the ledger
  data (verdicts + escalations) is the input for that.

## Implementation Plan
- Affected paths: `uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py` (new subcommand
  `fastpath-eval`), `uscha-kit/uscha.config.json` (defaults block), `uscha-kit/.claude/skills/
  uscha-devloop/SKILL.md` (entry flow), `uscha-mirador`/`uscha-status` SKILL.md (surface the
  mode), twins in `uscha-kit/skills/`.
- Patterns: verdict/breakdown/exit-code conventions of existing gates (`simplicity-check`,
  `waste-check`); ledger writes via `_append_gate_record`-style provenance.
- Tests: smoke checks named `AC-FP-nn` per ACCEPTANCE.md; golden-anchor of current devloop
  entry behavior BEFORE implementing (feeds AC-FP-08).

## Verification
- [ ] `fastpath-eval` on a diff within all thresholds, no protected paths → `ALLOW` (AC-FP-01)
- [ ] one LOC over `max_loc_delta` → `DENY` naming `max_loc_delta` (AC-FP-02)
- [ ] protected path touched → `DENY` regardless of size (AC-FP-03)
- [ ] mid-run growth past a threshold → `ESCALATED`, PR blocked, both records present (AC-FP-05)
- [ ] no asserting test in evidence → criterion open, readiness capped (AC-FP-06)
- [ ] ledger entry carries mode, verdict, and every signal with value+threshold+source+timestamp (AC-FP-07)
- [ ] config block absent → behavior byte-identical to current release (AC-FP-08)
- [ ] full-path override works; no mechanism can force `ALLOW` (AC-FP-09)
- [ ] no git repo / unresolvable base → `DENY` with the reason named (AC-FP-10)
- [ ] `fastpath-eval` without `--intent` → verdict reported, no mode entry recorded (AC-FP-11)
