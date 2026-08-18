# SPEC — `uscha top` v0.1 (governed by ADR-031..035)

`uscha top` is a stdlib-only terminal application that projects the QA ledger of a uscha project:
a board of obligations, a live feed of ledger events, and a verdicts mode that is its single write.
It derives nothing — the engine subcommand `qa_ledger.py top --json` (ADR-032) computes every state,
cardinality, median and feed line, and the TUI's `render(state, size)` (ADR-034) only draws it.

> Placement note: `docs/uscha-top/` is a new location (the repo convention is `docs/adr/*.md` +
> root `ACCEPTANCE.md`). It holds the curation-stage SPEC and FIXTURES for a multi-ADR feature;
> the ACs move into `ACCEPTANCE.md` (section in §7) once curated. **Curated 2026-08-17 (maintainer):**
> location accepted as the repo convention for multi-ADR features (`docs/<feature>/` holds the
> narrative SPEC + FIXTURES; ACs are promoted to `ACCEPTANCE.md` on acceptance). Also curated: v0.1
> renders `—` where the engine has no honest source (ETA, AGE, count burn-up — ADR-035); `AC-T-nn`
> close via smoke assertions + golden frames now, and the `_AC_TAG` widening ships as its own
> engine release (ADR-035 item 6), never coupled to M1.

This spec restates the handoff's KPI formulas (§3) over the **real derivable fields** and fixes the
UI honesty invariants. Where the handoff and the engine's reality conflict, reality wins and the
conflict is named. The definitive AC ids are assigned here, not by the handoff.

---

## 1. Scope

- **In v0.1 (M1-M3):** the read-only board (header + obligations table + state colors), the git
  `HEAD` spec-pin proxy, the live feed with `mtime` polling, and VERDICTS mode (the only write, via
  `curate`). Pure `render()`, golden-frame oracle, Windows first-class VT path, `--once` no-TTY mode.
- **Not in v0.1 (phase 2, M4):** `d` spec↔code diff, `o` oracle rerun, the spec-lens editor. Every
  deferred `—` field (ETA, ages, obligation-count burn-up, drift, TRACED/TAGGED rungs, designed
  spec-pin) is enumerated in ADR-035 and rendered honestly as `—`/gray until wired.

---

## 2. The two modes

### BOARD (default)
- Header: `DONE x/N (p%)` + debtor decomposition + honesty coverage + spec-pin + step.
- Obligations table, columns: `ID · GATE · STATE · CASES · AGE · ACTION`.
- Bottom pane: the ledger feed (last ≤N events, colored by level).
- Keys: `[v]` verdicts · `[d]` spec↔code diff *(phase 2, stub)* · `[o]` rerun oracle *(phase 2,
  stub)* · `[j/k` or `↑/↓]` move · `[q]` quit.

### VERDICTS (`v`)
- List of quarantined OBS (age, affected AC) with candidate and evidence side by side.
- Keys: `[1-9]` or `[j/k]` select · `[p]` preserve · `[f]` fix · `[u]` undefined · `[t]`/`[Esc]` back.
- Each verdict shells out to `curate` once (ADR-033) and advances to the next uncurated OBS; empty
  queue returns to BOARD.

All labels are English (repo convention since 1.55.0).

---

## 3. KPI formulas — over the real fields

Let `O` = the obligations in `top --json` `obligations[]` (the ACs of the pinned spec; denominator
fixed per commit). All values below are **computed by `cmd_top` and emitted in the JSON** — the TUI
renders them, it does not recompute them (single derivation, ADR-032).

- `DONE (terminado) = |MEASURED_PASS| / |O|` → JSON `terminado {done, total, pct, unmeasured}`.
- Debtor decomposition of the remainder → JSON `debtors`:
  - `machine owes = |MEASURED_FAIL|`
  - `you owe      = |QUARANTINE|`
  - `untagged     = |UNMEASURED ∪ TRACED|` (specification debt: not measurable yet)
- `ETA_min = you_owe × median_verdict + machine_owes × median_loop` → JSON `eta_min`.
  **v0.1 reality:** `median_verdict` is `null` (no per-OBS first-seen timestamp, ADR-032/035), so
  `eta_min` is `null` and the header renders `ETA —`. This overrides the mockup, which shows a live
  ETA; v0.1 cannot honestly compute it. `median_loop` **is** real (from `iterations[].at`).
- `honesty = (|MEASURED_PASS| + |MEASURED_FAIL|) / |O|` → JSON `honesty {measured, total, pct}`.
- **Both percentages under-claim on rounding.** `terminado.pct` and `honesty.pct` are computed by the
  same engine helper and are capped at **99** whenever the numerator is below the denominator: 999 of
  1000 rounds to 100, and a board reading `100%` while one obligation is outside `MEASURED_PASS` — or
  `100% measured` while one criterion is unmeasured — is exactly the lie INV-TOP-01 forbids. 100 is
  emitted only when it is literally true. The cap lives in the engine so no renderer can be the place
  the rounding happens.
- Burn-**up**, not burndown → JSON `burnup`. **v0.1 reality:** `kind:"score"` (the real
  `readiness_history` series); obligation-count burn-up needs new persistence (ADR-035), so the TUI
  labels this as a score trend, never as a count of closed obligations.
- `spec_pin` → git `HEAD`, marked *not clean-room verified* unless a `clean_room` GREEN record exists
  at that SHA; `null` (non-git) renders `—`. This overrides the mockup's authoritative-looking pin.
  `spec_pin` is the HEAD of the git work tree that **versions the repo path** — a subdirectory of a
  repo (a monorepo subproject) pins that repo's HEAD, which is honest: those files are versioned
  there. Only a path outside any git work tree at all yields `null`.
- `AGE` column and per-OBS ages → `—` for every row in v0.1 (no first-seen timestamp).

---

## 4. UI honesty invariants (inherit INV-TRUTH-01)

- **INV-TOP-01** — the DONE bar **never** shows 100% while ≥1 obligation is outside `MEASURED_PASS`,
  and it carries the explicit suffix `· N unmeasured` whenever `terminado.unmeasured > 0`. (handoff I1)
- **INV-TOP-02** — `UNMEASURED` is a first-class visual state (its own gray), never a zero and never
  a blank cell; `TRACED` and `TAGGED`, which v0.1 cannot measure, render in this same gray class,
  never as `PASS`. (handoff I2, extended per ADR-032)
- **INV-TOP-03** — a verdict never increments DONE; only a real green oracle/test rerun does. There
  is no auto-rerun in v0.1. (handoff I3, ADR-033)
- **INV-TOP-04** — DONE measures distance to *satisfying the pinned spec*, not "product finished";
  the header shows JUnit/oracle coverage (`honesty`) beside it to expose a thin denominator. (I4)
- **INV-TOP-05** — any field with no honest source renders `—` (or its state's gray), never a
  fabricated value. Truth-pass, the mirador precedent; this is what makes every `—` in §3 honest
  rather than a missing feature. (ADR-032)

---

## 5. Milestones and gates

- **M1 — top read-only.** Header + board + states + spec-pin proxy, `--once`, green golden frames.
  No feed, no verdicts. **Gate:** `top --json` shape asserted (AC-T-01..10, AC-T-24), golden frames
  green at 100×32 and 80×24 (AC-T-19, AC-T-21), honesty negative frame green (AC-T-23), Windows VT
  path and `--once` (AC-T-18, AC-T-20, AC-T-22).
- **M2 — live feed.** Event tail + `mtime` polling. **Gate:** AC-T-11, AC-T-12.
- **M3 — verdicts mode.** The single write. **Gate:** AC-T-13..16 + the before/after `curate`
  byte-equal fixture (AC-T-17).
- **M4 — phase 2 (not now).** `d` diff, `o` rerun, spec-lens over the same contract.

Each milestone closes with a full turn of the method (spec pinned → compile → oracle → curation).

---

## 6. Out of scope (explicit)

- Web server / SSE / browser UI.
- IR graph (concept 02, discarded).
- Modifying the existing HTML `mirador`.
- Any auto-promotion of observations (would violate INV-CURATION-01).
- **Auto-rerun after a verdict** (a fix leaves the obligation in its measured state — ADR-033).
- **The spec-lens editor** (phase 2; it consumes the same `top --json` contract — nothing in v0.1
  may block it).

---

## 7. ACCEPTANCE section — ready to paste into `ACCEPTANCE.md` after curation

> These criteria close through **bespoke smoke-suite assertions and golden frames** (ADR-034), the
> same mechanism every family-prefixed criterion in this repo already uses — not through JUnit
> ingestion, because `_AC_TAG` matches only bare `AC-<n>` (audit B.1; widening it is ADR-035 future
> work, deliberately not taken for v0.1). Each criterion is measurable by an assertion over `top
> --json` output or a golden frame.

```md
## uscha top v0.1 (ADR-031..035) - closes on green `AC-T-nn` smoke assertions and golden frames

- [ ] AC-T-01 — the header shows `DONE x/N (p%)` computed per SPEC §3, rendered from the
  engine-computed `terminado` block of `top --json`; the TUI derives no value itself.
- [ ] AC-T-02 — the header shows `machine owes M · you owe Q · untagged U` from the `debtors` block.
- [ ] AC-T-03 — ETA is rendered per §3; with `medians.verdict_min` null (v0.1 always) it renders `—`.
- [ ] AC-T-04 — with `terminado.unmeasured ≥ 1`, the percentage carries the suffix `· N unmeasured`
  (INV-TOP-01).
- [ ] AC-T-05 — the burn-up is rendered with block chars from `burnup`; v0.1 renders the `kind:"score"`
  series and labels it as a score trend, not a count of closed obligations.
- [ ] AC-T-06 — `spec_pin` renders the git `HEAD` sha with a *not clean-room verified* marker; a null
  pin (non-git) renders `—`; a fabricated pin never appears (INV-TOP-05).
- [ ] AC-T-07 — one row per obligation, state-colored (PASS green, FAIL red, QUARANTINE amber,
  UNMEASURED/TRACED/TAGGED gray), stable order by id.
- [ ] AC-T-08 — TRACED and TAGGED render in the UNMEASURED-class gray in v0.1, never as PASS and
  never fabricated, because the ledger carries no general-project source for them (INV-TOP-02,
  ADR-032).
- [ ] AC-T-09 — the `GATE` column shows `junit` or `curation` (never `oracle`) for a general project.
- [ ] AC-T-10 — the `AGE` column renders `—` for every obligation in v0.1 (no first-seen timestamp,
  ADR-035).
- [ ] AC-T-11 — the feed shows the last ≤N ledger events with timestamp and per-level color.
- [ ] AC-T-12 — `mtime` polling every `--refresh` s (default 2); a disk change re-renders within ≤1
  cycle.
- [ ] AC-T-13 — `v` enters VERDICTS listing only uncurated OBS, age-descending order.
- [ ] AC-T-14 — selecting an OBS shows candidate and evidence side by side, claims not truncated.
- [ ] AC-T-15 — `p`/`f`/`u` shells out to `curate` once per keypress (never batched) in the current
  curation record format and advances to the next uncurated OBS; empty queue returns to BOARD
  (ADR-033).
- [ ] AC-T-16 — after a verdict, DONE does not change (INV-TOP-03); the per-debtor cardinalities do;
  no auto-rerun moves DONE.
- [ ] AC-T-17 — the ledger record the TUI's verdict path appends is byte-identical to a manual
  `qa_ledger.py curate` call with the same arguments (before/after fixture).
- [ ] AC-T-18 — stdlib-only; runnable via `python -m`; py3.8-clean like the rest of the kit.
- [ ] AC-T-19 — `render(state, size)` is pure (no I/O); golden frames byte-identical over fixtures at
  100×32 and 80×24.
- [ ] AC-T-20 — no TTY (pipe/CI) → `--once` prints one plain frame and exits 0.
- [ ] AC-T-21 — degradation to 80×24: the layout does not break; the feed shortens first.
- [ ] AC-T-22 — Windows legacy conhost: VT processing is enabled via `SetConsoleMode` (ctypes,
  stdlib); on failure the app degrades to the `--once` plain frame rather than emitting raw escapes.
- [ ] AC-T-23 — honesty negative case: a 23/24-PASS + 1-UNMEASURED fixture renders 96% with the
  suffix, never 100% (discriminates a cheating renderer).
- [ ] AC-T-24 — single derivation: rendered from a frozen `top --json` fixture with no engine call,
  every number in the frame traces to a JSON field; the TUI computes no KPI itself.
```
