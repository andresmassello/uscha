---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/skills/uscha-devloop/qa_ledger.py
---
# ADR-032: The engine computes the whole projection — one read-only subcommand `top --json` emits every state, cardinality, median and feed line already derived, and a field with no honest source is `null`, never invented

## Status: Accepted (M1 shipped in 1.86.0; nullable fields per ADR-035; curated 2026-08-17)

## Context
Decision #1 of this work: the engine computes everything and the TUI only renders
(`render(state, size) -> list[str]`, ADR-034). One derivation, one place — the 1.48.1/mirador
lesson. The engine already has the precedent for this read path: `uscha_progress.py._measured`
(L35-74) reads `ledger["measured"]` and labels its source (`"measured"|"narrated"`) rather than
re-deriving; `uscha top` follows exactly that discipline.

The audit (AUDIT-DELTA §A) established, field by field, what today's ledger can honestly supply and
what it cannot. This ADR takes the contract the handoff §2 drafted and rewrites it against that
reality. Where the handoff assumes a field the engine cannot honestly compute in v0.1, the field is
typed nullable and the rule is fixed: **no source → `null` → the TUI renders `—`** (truth-pass, the
mirador precedent). Two vocabulary corrections from the audit are folded in:

- **`gate`** — the handoff's `"oracle"|"curation"` borrows Diamond-bench terms (audit A/`gate`, E.4).
  For a general project the gate that closes an AC is JUnit-tag ingestion (`_ac_tags`, L762) or
  curation (`_delta_state`), never a withheld "oracle". The contract emits `"junit"|"curation"`.
- **`run`** — is the engine's global `step_counter` (L1943…), not a build number or a QA-loop-pass
  count. The contract names it `step` and the TUI labels it `step #N` (audit A/`run`).

## Decision
**New read-only subcommand `qa_ledger.py top --json`** (`cmd_top`). It reads the same files and
ledger dicts the dashboard reads, computes the full projection, and prints one JSON object. It never
writes, never runs tests, never calls a model. Shape:

```json
{
  "schema": "uscha-top/v0.1",
  "project": "backend-api/mobile-app",
  "spec_pin": { "sha": "a41f9c2", "clean_room_verified": false },
  "step": 147,
  "generated_at": "2026-08-16T22:40:00-03:00",

  "obligations": [
    {
      "id": "AC-07",
      "kind": "AC",
      "state": "MEASURED_PASS",
      "gate": "junit",
      "cases_pass": 3,
      "cases_total": 3,
      "trace": [],
      "quarantine_obs": null,
      "ac": null,
      "age_hours": null
    }
  ],

  "observations": [
    {
      "id": "OBS-0234",
      "ac": null,
      "title": null,
      "candidate": ["type: tolerance · site: cuotas()", "claim: fecha_venc=None → assumes today()"],
      "evidence":  ["conciliador.py:88 if c.fecha_venc is None: ...", "41 historical tickets"],
      "age_hours": null
    }
  ],

  "events_tail": [
    { "ts": "22:39:41", "level": "pass", "text": "oracle OC-118 → PASS" }
  ],

  "counts":   { "measured_pass": 14, "measured_fail": 2, "quarantine": 4, "unmeasured": 4, "traced": 0, "tagged": 0, "total": 24 },
  "terminado":{ "done": 14, "total": 24, "pct": 58, "unmeasured": 4 },
  "debtors":  { "machine": 2, "you": 4, "untagged": 4 },
  "honesty":  { "measured": 16, "total": 24, "pct": 67 },
  "eta_min":  null,
  "medians":  { "verdict_min": null, "loop_min": 38 },

  "checks":   { "pass": 418, "fail": 4, "total": 422 },
  "drift_pct": null,
  "burnup":   { "kind": "score", "weeks": [61, 61, 64, 66, 66, 70] }
}
```

**Percentages under-claim on rounding.** `terminado.pct` and `honesty.pct` come from one engine
helper and are capped at **99** whenever the numerator is below the denominator — 999 of 1000 rounds
to 100, and a board reading `100%` with an obligation outside `MEASURED_PASS` (or `100% measured`
with a criterion unmeasured) is precisely the lie INV-TOP-01 exists to forbid. `100` is emitted only
when it is literally true. The cap belongs to the engine, not the renderer: rounding is a derivation,
and derivations live in exactly one place.

**Nullability rules (v0.1 — each traces to an audit finding):**

| Field | v0.1 value | Why (audit ref) |
|---|---|---|
| `spec_pin` | `{sha, clean_room_verified:false}` or `null` | No pinned-spec concept exists. v0.1 shells to git for `HEAD`, labels it *not clean-room verified*; `clean_room_verified:true` only if a `clean_room` GREEN record exists at that SHA (`_cr_latest`, L3451). `spec_pin` is the HEAD of the git work tree that VERSIONS the repo path — a subdirectory of a repo (monorepo subproject) pins that repo's HEAD, which is honest: those files ARE versioned there. Only a path outside any git work tree at all yields `null`. A designed pin is ADR-035. (A/`spec_pin`, E.1) |
| `obligations[].trace` | `[]` | No general AC→implementation map exists; `_rt_ids_in`/`_RT_ID_RE` is bench-wired only. Deferred to ADR-035; until then the array is empty, never fabricated. (A/`trace`, E.3) |
| `obligations[].ac`, `.quarantine_obs` | OBS id or `null` | The AC↔OBS link is a heuristic text match (`canonical_match`, L4374), not a designed field. `null` when no match — carried honestly. (A/`quarantine_obs`, C) |
| `obligations[].age_hours`, `observations[].age_hours` | `null` | No per-observation/first-seen timestamp; CANDIDATE-DELTA.json is rewritten wholesale each `discover` run, so `mtime` is not a valid "first seen" proxy. (A/`age_hours`, E.5) |
| `observations[].title` | `null` | No separate short label exists; `statement` is the only prose field. TUI may head-truncate `candidate[0]` for display but the engine emits `null`. (A/`observations`) |
| `eta_min` | `null` | `ETA = you × median_verdict + machine × median_loop`; `median_verdict` is null (below), so ETA is null → `—`. (§3, E.5) |
| `medians.verdict_min` | `null` | No timestamp for "entered quarantine"; only `curation[].at` exists. Throughput between curations is a *different* metric, not per-item wait — not substituted silently. (A/`medians.verdict_min`, C) |
| `medians.loop_min` | integer or `null` | Honestly computable from `ledger["repos"][r]["iterations"][*].at` (median gap between consecutive iterations); `null` if fewer than two iterations. (A/`medians.loop_min`) |
| `checks` | `{pass,fail,total}` or `null` | Mapped from the LATEST snapshot's `tests` block per repo (`pass = passed`, `fail = failures+errors`, `total = executed`), summed across repos. `null` — not a zeroed object — when no repo carries an ingested report: "0 of 0 tests ran" and "nobody measured" are different statements, and only one of them is true. Never conflated with `cases_pass/cases_total`, which is the AC-tagged subset. (A/`checks`) |
| `drift_pct` | `null` | `spec_drift` stores per-file verdicts, not an aggregate. A percentage would be a *new metric definition*, deferred to ADR-035. (A/`drift_pct`, E.7) |
| `burnup` | `{kind:"score", weeks:[…]}` | Only the **score** series is real (`readiness_history`, L8238). Obligation-count burn-up needs new persistence (ADR-035); v0.1 ships the score burn-up and labels `kind` so the TUI never implies it is a count of closed obligations. (A/`burnup_weeks`, E.6) |

**Per-obligation state ladder — what each state requires as evidence (v0.1):**

Handoff ladder: `UNMEASURED → TRACED → TAGGED → MEASURED_PASS ↘ MEASURED_FAIL`, lateral `QUARANTINE`.

| State | Evidence the engine requires | Derivable in v0.1? |
|---|---|---|
| `MEASURED_PASS` | an ingested JUnit report has a green testcase named `AC-n` and **zero** red (`_ac_closed`, L8046) | **Yes** |
| `MEASURED_FAIL` | an ingested JUnit report has ≥1 red testcase named `AC-n` (`ac_tags[cid].red >= 1`) | **Yes** (the FAIL bucket is a one-line split the engine now exposes as a discrete list) |
| `QUARANTINE` | `discover` has run **and** an uncurated observation's `statement` literally contains `AC-n` (`_delta_state` + `canonical_match`) | **Partial / heuristic** — honest `ac:null` when no match |
| `UNMEASURED` | none of the above — `ac_tags.get(cid) is None` | **Yes**, by elimination |
| `TRACED` | source text references `AC-n` and nothing measures it yet | **No general-project source** — needs `_rt_ids_in` rewired outside the bench (ADR-035). Until then the engine emits `counts.traced: 0` and the TUI renders any such rung in the UNMEASURED-class gray. |
| `TAGGED` | an oracle case exists for the AC, no verdict yet | **No JUnit equivalent** — bench-only concept (`_rt_compilation.behaviour_measured`). Not reachable via JUnit ingestion; `counts.tagged: 0` in v0.1, rendered UNMEASURED-class gray. |

The rule: `TRACED`/`TAGGED` are never faked into existence and never rendered as `MEASURED_PASS`. They
render in their own gray (INV-TOP-02) exactly because the ledger does not carry their facts yet.

**Events feed derivation.** `events_tail[]` is built from `ledger["steps"]` (fields `n, at, kind,
repo` exist, L1943…). `level` and `text` do **not** exist and are derived per `kind` by a fixed map
in `cmd_top` (e.g. an oracle-pass step → `level:"pass"`), so the derivation lives once in the engine,
not in the TUI.

## Consequences / Risks
+ One JSON, one derivation. The TUI is a pure function of this object (ADR-034); a change to a KPI is
  a change in `cmd_top`, provable by re-emitting the JSON, not by re-reading the TUI.
+ Every honesty rule (I1-I5) is enforceable on the JSON alone, independent of the renderer.
- The contract is deliberately poorer than the handoff mockup: ETA, ages, obligation-count burn-up,
  drift and trace all read `—`/empty in v0.1. That is the true state of the ledger, published as
  such (under-claim, then wire, then re-claim — repo rule 2).
- `cmd_top` must be covered by a smoke assertion over its JSON before it can be claimed (repo rule 5);
  the JSON shape is the contract the golden frames and the ACs both measure against.

## Verification
- [ ] `qa_ledger.py top --json` emits the contract shape; every KPI/cardinality/median/feed line is computed by the engine and asserted by the smoke suite (AC-T-01..06, AC-T-09, AC-T-10)
- [ ] the TUI computes no KPI: a frame rendered from a frozen `top --json` fixture traces every number to a JSON field (AC-T-24)
- [ ] TRACED/TAGGED render in the UNMEASURED gray class, never as PASS (AC-T-08)

## What this ADR does NOT decide
- The renderer, the layout, or the keymap — ADR-031/ADR-034.
- The write path — ADR-033.
- The new persistence any nullable field would need to become non-null — ADR-035.
- Widening `_AC_TAG` so `AC-T`-family ids enter the measured pipeline — ADR-035 (position (b));
  v0.1 does not depend on it. *(Taken up in 1.87.0 by ADR-036; v0.1's contract is unchanged by
  it — the same obligations, now with the family ids readable.)*
