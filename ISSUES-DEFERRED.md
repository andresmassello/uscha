# ISSUES-DEFERRED

Findings the QA loop surfaced that are **below the severity gate**
(`BLOCKER | CRITICAL | HIGH`). They are recorded here rather than fixed, because the loop's
rule is *converge, don't chase zero*: a pass that keeps fixing MEDIUMs never ends, and every
extra changed line is risk the change did not need.

They are deferred, not forgiven. Each carries the evidence that found it.

---

## 2026-07-23 — QA loop over releases 1.46.1 → 1.48.1 (3 cycles, converged)

### D-01 (MEDIUM) — the mirador discards the phase it already derived
`uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py` · `cmd_dashboard`

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

### D-02 (LOW) — `.claude/uscha-progress.json` has no schema marker
`uscha-kit/templates/scripts/uscha_progress.py` (producer) ·
`uscha_statusline.py` + the `uscha-status` skill (consumers)

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
