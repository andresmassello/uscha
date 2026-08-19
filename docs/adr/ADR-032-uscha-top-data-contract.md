---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/skills/uscha-devloop/qa_ledger.py
---
# ADR-032: The engine computes the whole projection — one read-only subcommand `top --json` emits every state, cardinality, median and feed line already derived, and a field with no honest source is `null`, never invented

## Status: Accepted (M1 shipped in 1.86.0; feed derivation amended and shipped in 1.88.0 for M2; `observations[]` amended and shipped in 1.89.0 for M3; `spec_diff` + `repos` amended and shipped in 1.91.0 for phase 2 / ADR-037; `terminado.sealed` amended and shipped in 1.92.0 / ADR-038; nullable fields per ADR-035; curated 2026-08-17)

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
      "repo": "backend-api",
      "title": "the settlement window rolls to the next business day",
      "candidate": ["type: behavior · site: svc/settle.py", "claim: <the whole statement>"],
      "evidence":  ["svc/settle.py:88", "evidence_class: static · tool: qa_ledger-static-py"],
      "age_hours": null
    }
  ],

  "events_tail": [
    { "ts": "22:39:41", "level": "pass", "text": "oracle OC-118 → PASS" }
  ],

  "counts":   { "measured_pass": 14, "measured_fail": 2, "quarantine": 4, "unmeasured": 4, "traced": 0, "tagged": 0, "total": 24 },
  "terminado":{ "done": 14, "total": 24, "pct": 58, "unmeasured": 4,
                "sealed": { "ok": false,
                            "reasons": ["stale seal: snapshot at 1a2b3c4d, HEAD is 9f8e7d6c"],
                            "commit": "9f8e7d6c...", "repo": "backend-api" } },
  "debtors":  { "machine": 2, "you": 4, "untagged": 4 },
  "honesty":  { "measured": 16, "total": 24, "pct": 67 },
  "eta_min":  null,
  "medians":  { "verdict_min": null, "loop_min": 38 },

  "checks":   { "pass": 418, "fail": 4, "total": 422 },
  "drift_pct": null,
  "burnup":   { "kind": "score", "weeks": [61, 61, 64, 66, 66, 70] },

  "repos": [ { "name": "backend-api", "path": "services/api" } ],
  "spec_diff": {
    "measured_at": "2026-08-18T12:00:00+00:00",
    "repo": "backend-api",
    "max_lag_days": 30,
    "docs_total": 4,
    "stale": [
      { "doc": "SPEC.md", "lag_days": 74, "code_ref": "src/app.py", "newer_files_total": 3,
        "spec_committed_at": "2026-01-05T10:00:00Z", "newest_governed_at": "2026-03-20T10:00:00Z" }
    ],
    "advisory": true,
    "source": "spec-drift"
  }
}
```

**`repos` and `spec_diff`** *(amended 1.91.0, phase 2 — ADR-037).* Both are reads of what the
ledger already holds; `top` still runs nothing.

- **`repos[]`** — the configured repos, name and **configured** path, in configuration order.
  It exists because phase 2 gave the TUI two questions it must not answer for itself: which
  repo `o` runs in and ingests for (the head of this list, the same repo `spec_pin` labels the
  board with) and which repo `d` names when it tells the reader how to produce a missing
  spec-drift run. The path is the one in the config — relative to the ledger, never resolved to
  an absolute machine path here, because a frozen state carrying one is a golden frame nobody
  else can render.
- **`spec_diff`** — `null` when no `spec-drift` run is recorded, and that null is the point: the
  pane then says *no run recorded* rather than showing a clean board, because "nobody measured"
  and "nothing is stale" are different statements (INV-TOP-05). When a run exists, this
  projects `ledger["spec_drift"]` (ADR-005) and **only its `SPEC_STALE` rows** — CLEAN, UNMAPPED,
  UNTRACKED and NO-CODE are the four ways a doc is not drifting, with `docs_total` keeping the
  denominator visible. `advisory` is always `true`: ADR-005 drift never gates, here or anywhere.
  `code_ref` is **one** of the governed files that outran the doc — the record stores a capped,
  alphabetically sorted list and no per-file dates, so it is "a newer file", never "the newest
  one", and `newer_files_total` carries the real cardinality. `drift_pct` stays `null`: an
  aggregate percentage is still a new metric definition nobody has agreed (ADR-035/3).

**`terminado.sealed`** *(amended 1.92.0 — ADR-038, INV-T1).* Derived at read time from the
ledger plus the tree, **never stored**: a recorded verdict is a claim about a tree that has moved
on since, which is the failure mode the field exists to catch. It answers one question — is the
recorded evidence still bound to the code on disk right now — from three checks over what the
ledger already carries: the working tree is clean (`git status --porcelain -uall`, ignoring the
ledger file itself and the report files the last snapshot names), `HEAD` equals that snapshot's
`origin.commit` (ADR-007), and every report it names still exists and still hashes to the
`sha256` recorded at ingest (new in 1.92.0, beside the path and mtime already recorded).

- **Three verdicts, never two.** `true` sealed · `false` a MEASURED break, with `reasons[]`
  naming which · `null` UNMEASURED — no git work tree, no configured repo, no snapshot recorded
  yet, or a snapshot old enough to carry no hash. A measured break outranks an unmeasured check
  (fail-closed); an unmeasured check never reads as a pass (INV-TOP-05).
- **`repo`** names the repo every reason is read against: the FIRST configured one, the same
  choice `spec_pin` and `repos[]` make. `commit` is the tree's `HEAD` at check time, `null`
  without git. The block carries **no timestamp of its own**: it is recomputed on every read, so a
  "checked at" would be a second wall clock beside `generated_at` and two consecutive `top --json`
  runs would differ in it — which AC-T-24 measures, and which is how the field was caught before
  it shipped. Everything in the block is deterministic given the ledger and the tree.
- **What it costs to read.** The hash is taken over the report set the LAST snapshot names — a
  handful of files the engine already opens — so `top --json` stays a read of bounded size.
- The same derivation backs the `check-terminado` subcommand (exit 0/1/2). One derivation, two
  surfaces: a second place that decides TERMINADO is a second place that can disagree.

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
| `observations[].title` | the statement's capped head *(amended 1.89.0, M3)* | Still no separate short label: `statement` is the only prose field. Until M3 the engine emitted `null` and left the truncation to the TUI. M3 needs the label and the full claim at once, and a renderer that cuts prose is a renderer that decides what the human judges — so the ENGINE now emits both: `title` is the statement cleaned and capped at 72 (marked `…` when cut), `candidate[]` carries the whole claim, uncapped. `null` only when the observation has no statement at all. (A/`observations`) |
| `eta_min` | `null` | `ETA = you × median_verdict + machine × median_loop`; `median_verdict` is null (below), so ETA is null → `—`. (§3, E.5) |
| `medians.verdict_min` | `null` | No timestamp for "entered quarantine"; only `curation[].at` exists. Throughput between curations is a *different* metric, not per-item wait — not substituted silently. (A/`medians.verdict_min`, C) |
| `medians.loop_min` | integer or `null` | Honestly computable from `ledger["repos"][r]["iterations"][*].at` (median gap between consecutive iterations); `null` if fewer than two iterations. (A/`medians.loop_min`) |
| `checks` | `{pass,fail,total}` or `null` | Mapped from the LATEST snapshot's `tests` block per repo (`pass = passed`, `fail = failures+errors`, `total = executed`), summed across repos. `null` — not a zeroed object — when no repo carries an ingested report: "0 of 0 tests ran" and "nobody measured" are different statements, and only one of them is true. Never conflated with `cases_pass/cases_total`, which is the AC-tagged subset. (A/`checks`) |
| `drift_pct` | `null` | `spec_drift` stores per-file verdicts, not an aggregate. A percentage would be a *new metric definition*, deferred to ADR-035. (A/`drift_pct`, E.7) |
| `spec_diff` | the block above or `null` *(added 1.91.0)* | Projects `ledger["spec_drift"]`, the advisory latest-state record ADR-005's command leaves behind. No recorded run → `null` → the pane says so. Nothing is re-measured here: `top` never walks git. |
| `repos` | `[{name, path}]` (possibly empty) *(added 1.91.0)* | The configured repos in configuration order, so the TUI picks neither the rerun target nor the repo it names. Empty list when the ledger configures none — `o` then refuses by name. |
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

**Verdict-queue derivation** *(amended 1.89.0, M3 — the shape below is the shipped one).*
`observations[]` was already the UNCURATED set (`_delta_state().uncurated`); M3 fixes what each
entry carries, because the pane that shows it is the one a human records a verdict from.

- **Only uncurated observations.** A verdict removes its observation from the queue on the next
  read — the same filter the gates use, not a second definition of "pending".
- **`repo`** is the delta's own repo. It is in the contract because `curate` takes `--repo`
  (ADR-033): a queue without it would make the TUI pick one, which is the derivation the TUI is
  never allowed to make.
- **`candidate[]`** is typed, from the delta's own fields: `type: <type> · site: <first
  provenance entry>`, then `claim: <statement>` **uncapped**. The claim is the thing being judged;
  capping it in the engine would hide evidence, and capping it in the renderer would move a
  derivation into the TUI.
- **`evidence[]`** is one line per provenance entry (already `file:line` where the extractor knows
  the line), then `evidence_class: <class> · tool: <tool>` — the class is what separates a measured
  observation from a narrated one, and it belongs beside the files, not in a legend.
- **Order:** the criterion the observation anchors first (by the same key the obligations use),
  the unanchored ones after, the content-addressed id as the tie-break. **Age-descending, which the
  SPEC drafted, is not derivable**: every `age_hours` is null, and sorting by a value that does not
  exist is the fabrication INV-TOP-05 forbids.
- Every string is sanitized here (C0 + DEL, `_top_clean`) exactly as the feed's text is, and the
  renderer sanitizes again on the way out.

**Events feed derivation** *(amended 1.88.0, M2 — the map below is the shipped one).*
`events_tail[]` is built from `ledger["steps"]` (fields `n, at, kind, repo` exist, L1943…). `level`
and `text` do **not** exist and are derived per `kind` by a fixed map in `cmd_top` (`_top_events`),
so the derivation lives once in the engine, not in the TUI.

- **Order and size:** the last **8** steps, **newest first** (the board reads top-down, so the most
  recent line is the one at the top of the pane). The TUI renders as many as fit and says `5/7` when
  it shows fewer — a feed that silently drops lines is a feed that can hide the red one.
- **`ts`:** the step's `at` as `HH:MM:SS` in **UTC**. A stamp carrying an offset is normalized to
  UTC; it is never converted to the LOCAL zone, which would make one ledger read differently on two
  boxes and break the golden frames. An unparseable stamp yields `null` → the TUI renders `—`.
- **`level`** ∈ `{pass, fail, human, unmeasured, info}`:

  | `kind` | `level` | refined from |
  |---|---|---|
  | `snapshot` | `info` → `fail` if the snapshot recorded red tests | the snapshot record with the same `(repo, at)` |
  | `qa-step` | `info` → `pass` if 0 reported, or all reported were fixed | the iteration record with the same `n` |
  | `static-gate` | `pass`/`fail` by `gated_reported` (≥1 → `fail`) | the iteration record with the same `n` |
  | `gate-not-run` | `unmeasured` | — (a gate nobody ran is not a pass) |
  | `cleanroom` | `pass`/`fail` by the record's `ok`, and only when it carries both a `status` and an `ok` | the k-th `clean_room` record of that repo |
  | `escalation` | `human` | the escalation with the same `n` (its `reason` is the line's tail) |
  | `escalation-resolved` | `human` | — (it takes a FRESH counter, so there is no record to look up: the line says what happened and nothing more) |
  | `production-finding`, `spec-doubt`, `spec-change-request` (+ their `:resolve` twins) | `human` | — |
  | `fastpath-eval` | `info` | the `fast_path` entry with the same `n` (its `verdict`) |
  | anything else | `info` | — (an unclassified step is never a green one) |

  The correlations are the ones the ledger really supports — by `n` where the writer copies the
  counter into both records, in order where step and record are appended in the same call, by
  `(repo, at)` for snapshots. **A miss degrades that one line to its neutral level, never to a
  verdict**: the failure mode of the feed is under-claiming, by construction. The same rule covers
  a malformed ledger: the file is JSON on disk, so any field can arrive as a list or a dict from a
  hand edit, and one unreadable step becomes one `info` line naming its `kind` — the read-only
  readout never raises and never drops the JSON the board depends on.
- **`text`** is a short English line built only from step fields (`kind`, `repo`, the one or two
  salient fields of the correlated record), capped at 72 characters. It is the **only free-text
  field of the contract that reaches a terminal**, and it carries ledger prose (an escalation
  reason, a tool name) that came from a human or a CLI, so the control characters are stripped
  here, in the engine — and again in the renderer on the way out. Two cheap guards over one
  surface. **What is filtered since 1.90.0 is the C0 range (`\x00`-`\x1f`), DEL (`\x7f`), the
  8-bit C1 range (`\x80`-`\x9f`) and every Unicode format character (category `Cf`)** — bidi
  overrides, zero-width joiners and friends. C1 and `Cf` were explicitly **not** filtered in
  v0.1 and that was recorded as a named gap, not implied completeness; it is closed now
  because both are the same attack in a cheaper disguise: a terminal decoding the stream as
  latin-1 reads `\x9b` as a CSI introducer, `U+200B` spends a codepoint and no column, and
  `U+202E` reverses everything drawn after it. A character that cannot be seen must not be
  able to move what is. Both guards do the same filtering, on purpose: `_top_clean` in the
  engine, `_safe` in the renderer.

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
- [ ] `qa_ledger.py top --json` emits the contract shape; every KPI/cardinality/median/feed line is computed by the engine and asserted by the smoke suite (AC-T-01..06, AC-T-09, AC-T-10, AC-T-11)
- [ ] the TUI computes no KPI: a frame rendered from a frozen `top --json` fixture traces every number to a JSON field (AC-T-24)
- [ ] TRACED/TAGGED render in the UNMEASURED gray class, never as PASS (AC-T-08)

## What this ADR does NOT decide
- The renderer, the layout, or the keymap — ADR-031/ADR-034.
- The write path — ADR-033.
- The new persistence any nullable field would need to become non-null — ADR-035.
- Widening `_AC_TAG` so `AC-T`-family ids enter the measured pipeline — ADR-035 (position (b));
  v0.1 does not depend on it. *(Taken up in 1.87.0 by ADR-036; v0.1's contract is unchanged by
  it — the same obligations, now with the family ids readable.)*
