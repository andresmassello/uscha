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
> engine release (ADR-035 item 6), never coupled to M1. **Shipped 1.87.0 as ADR-036:** the
> widening landed on its own; the `AC-T-nn` criteria still close by smoke assertion, and the
> engine can now also READ them.

This spec restates the handoff's KPI formulas (§3) over the **real derivable fields** and fixes the
UI honesty invariants. Where the handoff and the engine's reality conflict, reality wins and the
conflict is named. The definitive AC ids are assigned here, not by the handoff.

---

## 1. Scope

- **In v0.1 (M1-M3):** the read-only board (header + obligations table + state colors), the git
  `HEAD` spec-pin proxy, the live feed with `mtime` polling, and VERDICTS mode (the only write, via
  `curate`). Pure `render()`, golden-frame oracle, Windows first-class VT path, `--once` no-TTY mode.
- **Phase 2 (M4, shipped 1.91.0 — ADR-037):** `d` spec↔code diff (read-only, over the ledger's own
  advisory `spec-drift` record) and `o` rerun (the human's command, then the engine's `snapshot`).
  Still out: the spec-lens editor.
- **Not in v0.1 (deferred to phase 2, M4 — see the line above for what of it shipped):** `d`
  spec↔code diff, `o` oracle rerun, the spec-lens editor. Every
  deferred `—` field (ETA, ages, obligation-count burn-up, drift, TRACED/TAGGED rungs, designed
  spec-pin) is enumerated in ADR-035 and rendered honestly as `—`/gray until wired.

---

## 2. The two modes

### BOARD (default)
- Header: `DONE x/N (p%)` + debtor decomposition + honesty coverage + spec-pin + step.
- Obligations table, columns: `ID · GATE · STATE · CASES · AGE · ACTION`.
- Bottom pane: the ledger feed (last ≤N events, colored by level).
- Keys: `[v]` verdicts · `[d]` spec↔code diff · `[o]` rerun · `[j/k` or `↑/↓]` move · `[r]` reload ·
  `[q]` quit. *(`d` and `o` shipped in 1.91.0 — the hint line no longer marks them as future.)*

### VERDICTS (`v`)
- List of uncurated OBS (affected AC, and the age the engine cannot supply — so it is not shown)
  with candidate and evidence side by side, stacked below 100 columns.
- Keys: `[1-9]` or `[j/k]` select · `[p]` preserve · `[f]` fix · `[u]` undefined · `[r]` reload ·
  `[t]`/`[Esc]` back · `[q]` quit.
- Each verdict shells out to `curate` once (ADR-033) and advances to the next uncurated OBS; empty
  queue returns to BOARD.

### DIFF (`d`) — *shipped 1.91.0, read-only*
- One header line: `spec ↔ code drift · advisory · N of M doc(s) stale (lag > D d) · measured <at>`,
  or the honest `no spec-drift run recorded — run qa_ledger.py spec-drift --repo <r>` when the
  ledger carries no run. The count sits before the timestamp because this is the line the
  80-column floor cuts.
- A table, worst lag first: `DOC · LAG/d · A NEWER GOVERNED FILE (1 of N)`.
- Keys: `[t]`/`[Esc]`/`[d]` back · `[r]` reload · `[q]` quit. **No cursor in v1** — the pane names
  what does not fit (`— N more stale doc(s) do not fit at this size`) instead of scrolling, and no
  key in this mode writes anything.
- It reads `spec_diff` (ADR-032, amended) and **never runs `spec-drift`**: that command walks git
  and records its own verdicts; `d` is a projection of the last real run, with that run's timestamp
  on screen so an old measurement cannot pass for a fresh one.

### `o` — rerun *(shipped 1.91.0, ADR-037 option B)*
- Inert without `--rerun-cmd`, and it says so. With it: the human's shell string runs in the first
  configured repo's directory (named on screen), synchronously, verdict keys locked; then the
  engine's own `snapshot --repo <r>` ingests — **on a red run too** — and the board re-reads.
- Refused under `--state` (a frozen snapshot is not a live ledger) and with no configured repo.
  Same drain + 250 ms cooldown as a verdict: one keypress, one run.

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
- **INV-TOP-06** — the DONE bar never shows 100% while the seal is **measured broken**
  (`terminado.sealed.ok is false`): the header carries `· unsealed (<first reason>)` and the
  ACTION column of every `MEASURED_PASS` row says what that row is waiting on (`seal: …`).
  Green criteria measured against evidence that no longer belongs to this code state are the
  same lie INV-TOP-01 forbids one line earlier. (INV-T1, ADR-038)
  - **The cap is the engine's**, beside INV-TOP-01's: `cmd_top` lowers `terminado.pct` to 99
    when the seal is broken, so the TUI still computes no KPI of its own (AC-T-24).
  - **The seal is shown only when it is MEASURED.** `sealed.ok is null` — no git work tree, or
    a snapshot old enough to carry no `sha256` — adds no suffix, changes no row and caps
    nothing: absence of a measurement is not evidence of a break (INV-TOP-05), and every
    frozen fixture in `docs/uscha-top/FIXTURES.md` is in exactly that state.
  - **The seal tolerates commits that touch no source** (amended in 1.93.0, ADR-039). HEAD may
    differ from the snapshot's `origin.commit` by files outside the engine's source-extension set
    (`_SRC_EXT`) and outside the named report set — docs, changelogs, the ledger that carries the
    snapshot being read — and the seal holds, carrying a `note` that names what moved (capped at
    five paths, null when HEAD IS that commit). A source-relevant difference is still a break and
    names the first offending path; an unreachable commit keeps the strict verdict. Without this
    the repo that applies the method to itself can never read sealed: its ledger lives inside the
    commit it describes.
  - **What "source-relevant" means is one named set** (`_src_relevant`, shared with the freshness
    rule): `_SRC_EXT`, plus the adapter's own `SOURCE_EXT[repo_type]`, plus BUILD/HARNESS files —
    `.sh .bash .ps1 .yml .yaml .toml .sql .tf .gradle .cmake` and the basenames `Makefile`,
    `pom.xml`, `build.gradle`, `package.json`, `pyproject.toml`, `setup.py`, `Cargo.toml`,
    `go.mod` — because a commit that rewrites what the suite runs changes what a green report
    means. Outside it, on purpose: `.md`, `.json`, `.xml`, `.txt`, so docs, changelogs, the
    ledger and the reports it names are non-source by construction. The LIMIT is the set itself —
    a project whose source or fixtures live in an extension it does not list gets a seal that
    tolerates changes to them.
  - **The hash is over BYTES, so line-ending translation is a false alarm** — fail-closed, but an
    alarm. A consumer repo that lets git rewrite CRLF on checkout (`core.autocrlf=true`, the
    Windows default, with no `.gitattributes`) will hash a cloned report differently from the one
    that was ingested and read `evidence altered after ingest` on a file nobody touched. The fix
    is one line in `.gitattributes` — `* text=auto eol=lf` — and the kit states it rather than
    silently normalizing, because a seal that normalized what it hashes would be hashing an
    interpretation of the evidence instead of the evidence.
  - **The scope is the tracked repo's subtree**, not the whole work tree: the clean check is
    `git status --porcelain -uall -- .` inside the configured repo path, the same per-path
    scoping `evidence_origin` uses (ADR-007), so a monorepo sibling's edit is not this repo's
    dirt — and the reason says `repo subtree dirty`, never `working tree dirty`.
  - **The live board can hold a stale seal.** The seal is recomputed on reload (`r`), on a
    ledger change the poll sees, and after `o`. A source edit or a new commit ALONE does not
    trigger a redraw, so a board that was sealed can keep saying so until the next refresh.
    Under-claimed on purpose (widening the poll to the subtree is future work); the surface
    that recomputes on every call is `check-terminado`, which is what a hook gates on.
  - **The limit, stated out loud**: a board with **no snapshot recorded at all** has no anchor
    to compare the tree against, so its seal is UNMEASURED and the header says nothing. A
    project can therefore read 100% with nothing binding that evidence to a commit. What does
    not soften is the gate: `qa_ledger.py check-terminado` exits **2** there (0 sealed, 1
    measured break, 2 UNMEASURED), so a hook or a human gating on exit 0 still refuses.

---

## 5. Milestones and gates

- **M1 — top read-only.** Header + board + states + spec-pin proxy, `--once`, green golden frames.
  No feed, no verdicts. **Gate:** `top --json` shape asserted (AC-T-01..10, AC-T-24), golden frames
  green at 100×32 and 80×24 (AC-T-19, AC-T-21), honesty negative frame green (AC-T-23), Windows VT
  path and `--once` (AC-T-18, AC-T-20, AC-T-22).
- **M2 — live feed.** Event tail + `mtime` polling. **Gate:** AC-T-11, AC-T-12.
- **M3 — verdicts mode.** The single write. **Gate:** AC-T-13..16 + the before/after `curate`
  byte-equal fixture (AC-T-17). **Shipped 1.89.0**, measured by T141 plus two VERDICTS golden
  frames; the queue's order is the one §7/AC-T-13 records, not the age-descending one drafted in
  §2 (there is no age to sort by — ADR-032 amended for M3).
- **M4 — phase 2.** `d` diff and `o` rerun **shipped 1.91.0** (ADR-037; contract widened with
  `spec_diff` + `repos`, ADR-032 amended). **Gate:** AC-T-25..29, measured by T145 plus two DIFF
  golden frames. The spec-lens editor is still future and still consumes the same contract.

Each milestone closes with a full turn of the method (spec pinned → compile → oracle → curation).

---

## 6. Out of scope (explicit)

- Web server / SSE / browser UI.
- IR graph (concept 02, discarded).
- Modifying the existing HTML `mirador`.
- Any auto-promotion of observations (would violate INV-CURATION-01).
- **Auto-rerun after a verdict** (a fix leaves the obligation in its measured state — ADR-033).
  Still out in phase 2: `o` is a keypress a human makes, with a command that human supplied at
  launch; nothing reruns by itself and nothing is guessed from config (ADR-008/037).
- **A clean-room rerun.** `o` runs in the working tree, exactly as the human would from their
  shell; the clean-room gate stays `cleanroom --run`, unchanged (ADR-037).
- **An asynchronous rerun.** Phase 2 blocks the board while the command runs, by design.
- **The spec-lens editor** (still phase-2 future; it consumes the same `top --json` contract —
  nothing shipped may block it).

---

## 7. ACCEPTANCE section — ready to paste into `ACCEPTANCE.md` after curation

> These criteria close through **bespoke smoke-suite assertions and golden frames** (ADR-034), the
> same mechanism every family-prefixed criterion in this repo already uses — not through JUnit
> ingestion, because `_AC_TAG` matches only bare `AC-<n>` (audit B.1; widening it is ADR-035 future
> work, deliberately not taken for v0.1). Each criterion is measurable by an assertion over `top
> --json` output or a golden frame.
>
> **Superseded 1.87.0 (ADR-036)**: `_AC_TAG`/`_AC_ID` now read `AC-<FAMILY>-<n>` too, so these ids
> DO enter the measured pipeline. What closes them is unchanged — the smoke assertions and golden
> frames still produce the evidence; the engine can now read the testcases they emit.

```md
## uscha top v0.1 (ADR-031..035) - closes on green `AC-T-nn` smoke assertions and golden frames

- [x] AC-T-01 — the header shows `DONE x/N (p%)` computed per SPEC §3, rendered from the
  engine-computed `terminado` block of `top --json`; the TUI derives no value itself.
- [x] AC-T-02 — the header shows `machine owes M · you owe Q · untagged U` from the `debtors` block.
- [x] AC-T-03 — ETA is rendered per §3; with `medians.verdict_min` null (v0.1 always) it renders `—`.
- [x] AC-T-04 — with `terminado.unmeasured ≥ 1`, the percentage carries the suffix `· N unmeasured`
  (INV-TOP-01).
- [x] AC-T-05 — the burn-up is rendered with block chars from `burnup`; v0.1 renders the `kind:"score"`
  series and labels it as a score trend, not a count of closed obligations.
- [x] AC-T-06 — `spec_pin` renders the git `HEAD` sha with a *not clean-room verified* marker; a null
  pin (non-git) renders `—`; a fabricated pin never appears (INV-TOP-05).
- [x] AC-T-07 — one row per obligation, state-colored (PASS green, FAIL red, QUARANTINE amber,
  UNMEASURED/TRACED/TAGGED gray), stable order by id.
- [x] AC-T-08 — TRACED and TAGGED render in the UNMEASURED-class gray in v0.1, never as PASS and
  never fabricated, because the ledger carries no general-project source for them (INV-TOP-02,
  ADR-032).
- [x] AC-T-09 — the `GATE` column shows `junit` or `curation` (never `oracle`) for a general project.
- [x] AC-T-10 — the `AGE` column renders `—` for every obligation in v0.1 (no first-seen timestamp,
  ADR-035).
- [x] AC-T-11 — the engine derives `events_tail`: the last ≤8 `ledger["steps"]`, newest first, each
  `{ts, level, text}` with `level` from the fixed per-kind map (ADR-032, amended for M2), `ts` the
  step's `at` as UTC `HH:MM:SS`, and `text` stripped of C0 controls, DEL, the 8-bit C1 range and
  every Unicode format character (category `Cf`) — ADR-032, widened in 1.90.0; a ledger with no
  steps yields `[]`. Measured by T137 over a synthetic ledger carrying one step per kind, an unknown
  kind, an offset timestamp and an injected ESC sequence.
- [x] AC-T-12 — the `mtime` poll: `_changed(paths, seen)` flips on a real disk change (write, touch,
  delete) and only then; `--refresh` defaults to 2 s with a 0.5 s floor; a `--once` frame renders the
  derived feed with its timestamp and level letter (colour decorates the letter, so the plain and
  coloured frames keep identical geometry). **What is measured is the polling primitive plus the
  rendered frame, not a driven TTY session** — the interactive loop needs a terminal the suite does
  not have, and a test that claimed one would be the over-claim the golden frames exist to prevent.
- [x] AC-T-13 — `v` enters VERDICTS and the queue is exactly the UNCURATED observations the engine
  emitted, in the documented order: the criterion each one anchors first, the unanchored ones after,
  the content-addressed id as the tie-break. **Age-descending, drafted above, is not what shipped**:
  every `age_hours` is null (no first-seen timestamp, ADR-035), so ordering by age would sort on a
  value nobody records. `t`/`Esc` returns to BOARD. Measured over a temp copy: a curated OBS leaves
  the queue and only that one, and each queue entry carries the `repo` the write needs.
- [x] AC-T-14 — the selected OBS shows candidate and evidence side by side at 100 columns and
  stacked at the 80-column floor, and a claim longer than either column comes back **whole**, word
  for word, across the pane's lines. When even the wrapped form does not fit, the pane names the
  shortfall (`— N more line(s) …`) instead of cutting in silence. The one-line queue label above it
  MAY carry the engine's `…` cap — the label is a label; the claim is in the pane.
- [x] AC-T-15 — `p`/`f`/`u` shells out to `curate` exactly once per keypress (never batched) with
  the documented argv and advances to the next uncurated OBS; an empty queue returns to BOARD; the
  engine's refusal (unknown OBS, batch-looking id) is surfaced and nothing is retried. Also measured
  structurally: `uscha_top.py` opens no file for writing, dumps no JSON, builds exactly one
  `curate` argv, calls `apply_verdict` exactly once with no `for`/`while` above that call, and
  drains the input buffer on every verdict path — `curate` is not merely the write path used, it is
  the only one that exists, and one keypress cannot become a pass over the queue (ADR-033).
  Two further refusals are measured here: a verdict key inside the 250 ms cooldown records nothing
  (a held key would otherwise judge the observation that just took the cursor's place) while
  `j`/`t`/`q` keep working, and a `--state` run — a frozen snapshot, not a live ledger — refuses by
  name and spawns nothing.
- [x] AC-T-16 — after a real verdict on a temp copy, `terminado.done` and `terminado.pct` are
  unchanged (INV-TOP-03) and `debtors.you` drops by one while the four buckets still partition the
  board; no auto-rerun moves DONE.
- [x] AC-T-17 — the ledger record the TUI's verdict path appends and the record a manual
  `qa_ledger.py curate` call appends, over two copies of the same fixture with the same arguments,
  are identical member for member — `at` (a wall clock in a subprocess) compared for shape.
- [x] AC-T-18 — stdlib-only; runnable via `python -m`; py3.8-clean like the rest of the kit.
- [x] AC-T-19 — `render(state, size)` is pure (no I/O); golden frames byte-identical over fixtures at
  100×32 and 80×24.
- [x] AC-T-20 — no TTY (pipe/CI) → `--once` prints one plain frame and exits 0.
- [x] AC-T-21 — degradation to 80×24: the layout does not break; the feed shortens first.
- [x] AC-T-22 — Windows legacy conhost: VT processing is enabled via `SetConsoleMode` (ctypes,
  stdlib); on failure the app degrades to the `--once` plain frame rather than emitting raw escapes.
- [x] AC-T-23 — honesty negative case: a 23/24-PASS + 1-UNMEASURED fixture renders 96% with the
  suffix, never 100% (discriminates a cheating renderer).
- [x] AC-T-24 — single derivation: rendered from a frozen `top --json` fixture with no engine call,
  every number in the frame traces to a JSON field; the TUI computes no KPI itself.
```

> **Amended 1.92.0 (ADR-038).** The contract grew `terminado.sealed`
> (`{ok, reasons[], commit, repo}`, derived at read time, never stored, no clock of its own) and the
> board grew INV-TOP-06 above. The criteria for it are their own family, `AC-CT-01..11` in
> `ACCEPTANCE.md`, measured by smoke T146 over a real temp git repo plus two golden frames
> over `state/state-unsealed.json` — the same mechanism, a separate family, because they are
> about the seal and not about the view.
