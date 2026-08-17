# FIXTURES — the `uscha top` oracle plan (governed by ADR-034)

The oracle for `uscha top` is golden frames: `render(state, size)` (pure, ADR-034) over a fixed
`top --json` object, snapshotted and asserted byte-identical in the smoke suite. This file names the
synthetic ledger fixtures, what each pins, the golden-frame matrix, the negative honesty cases, and
the before/after `curate` write-equivalence fixture. All names are generic (`backend-api`,
`mobile-app`) per repo rule 4.

Proposed home: `uscha-kit/tests/fixtures/uscha-top/` (ledger fixtures) and
`uscha-kit/tests/fixtures/uscha-top/golden/` (frame snapshots).

---

## 1. Synthetic ledger fixtures (3 + 1)

Each fixture is a minimal ledger (plus a `CANDIDATE-DELTA.json` where quarantine is involved) that
`qa_ledger.py top --json` reads to produce a deterministic JSON `state`.

- **F1 — healthy** (`fixture-healthy/`): all obligations `MEASURED_PASS`, no quarantine, no
  UNMEASURED. **Pins:** a legitimately full board — `DONE N/N (100%)` with **no** suffix (allowed by
  INV-TOP-01 precisely because nothing is outside PASS), `debtors {0,0,0}`, `eta_min:null` → `ETA —`,
  green-only board colors. This is the one frame where 100% is honest; it guards against a renderer
  that refuses to ever show 100%.

- **F2 — stale quarantine** (`fixture-stale-quarantine/`): a mix of `MEASURED_PASS` plus ≥2
  `QUARANTINE` OBS (uncurated, heuristically matched to ACs, some with `ac:null`). **Pins:** the
  `you owe Q` debtor cardinality, amber QUARANTINE rows, a populated VERDICTS queue in age-desc order,
  `AGE —` on every row (v0.1), and `ac:null` rendered honestly (no fabricated link).

- **F3 — re-pinned scope** (`fixture-repinned-scope/`): a `readiness_history` with a score step across
  a spec re-pin, and a changed obligation denominator. **Pins:** the score burn-up step rendered with
  block chars and labeled as a score trend (`burnup.kind:"score"`), the honesty coverage shown beside
  DONE (INV-TOP-04), and a denominator that differs from F1/F2 so the fixed-per-commit `|O|` is
  exercised.

- **F4 — real demo module** (`fixture-demo-module/`): the demo module's real ledger, end-to-end.
  **Pins:** that `top --json` runs over a real (not hand-built) ledger and the frame is stable and
  interpreter-independent; exercises the feed with real `ledger["steps"]` levels/text derivation.

---

## 2. Golden-frame matrix

`fixture × size × mode`. Sizes: 100×32 (reference), 80×24 (degradation floor). Modes: BOARD (all
fixtures), VERDICTS (only fixtures with a non-empty quarantine queue: F2, F4).

| Fixture | 100×32 BOARD | 80×24 BOARD | 100×32 VERDICTS | 80×24 VERDICTS |
|---|---|---|---|---|
| F1 healthy | ✓ | ✓ | — (empty queue) | — |
| F2 stale quarantine | ✓ | ✓ | ✓ | ✓ |
| F3 re-pinned scope | ✓ | ✓ | — | — |
| F4 demo module | ✓ | ✓ | ✓ | ✓ |
| N1 honesty negative | ✓ | ✓ | — | — |

The 80×24 frames assert the degradation rule (AC-T-21): the layout holds and the feed shortens first
— the header and board are never the first casualty.

---

## 3. Negative honesty cases

These exist to fail a cheating implementation, not to describe the happy path.

- **N1 — 23/24 + 1 UNMEASURED** (`fixture-honesty-negative/`): 23 `MEASURED_PASS`, 1 `UNMEASURED`.
  Golden frame MUST render `96%` with the `· 1 unmeasured` suffix and MUST NOT render `100%`
  (AC-T-23, INV-TOP-01/02). A renderer that rounds or drops the unmeasured obligation fails here.
- **Verdict does not move DONE** (paired render over F2): the BOARD `DONE` value is byte-identical
  before and after a verdict is applied via the write path; only the debtor cardinalities change
  (AC-T-16, INV-TOP-03). Asserts there is no auto-rerun.
- **Null medians → `ETA —`** (over F1/F2/F4, all v0.1): every fixture renders `ETA —` because
  `medians.verdict_min` is null; no fixture is allowed to render a numeric ETA in v0.1 (AC-T-03).
- **TRACED/TAGGED → gray, never PASS** (a fixture with `counts.traced`/`counts.tagged` forced): any
  such rung renders in the UNMEASURED-class gray, never green (AC-T-08).
- **spec_pin null → `—`** (a non-git fixture): the header renders `spec_pin —`, never a fabricated
  SHA (AC-T-06, INV-TOP-05).

---

## 4. Before/after `curate` write-equivalence fixture

Proves the TUI reimplements no append logic (ADR-033).

- **Setup:** a fixture ledger + `discovery/CANDIDATE-DELTA.json` with a known uncurated OBS.
- **Path A (manual):** run `qa_ledger.py curate --ledger <f> --repo <r> --obs OBS-XXXX --verdict
  preserve --human operator` and capture the appended `ledger["curation"]` entry.
- **Path B (TUI):** drive the VERDICTS dispatch with the same selection and the `p` key, which shells
  out to the same `curate` invocation.
- **Assertion:** the two appended records are **byte-identical** (`{obs_id, verdict, human, at, note,
  repo}`); the TUI never constructs a curation record itself. Timestamp determinism is handled by the
  same clock injection the rest of the suite uses (the `at` field is the one non-deterministic member;
  assert structural equality with `at` normalized, then assert the TUI path produced exactly one
  `curate` process spawn — never a batch, AC-T-15/17).

---

## 5. Input / dispatch fixtures

The terminal driver (`termios`/`msvcrt`) is not tested; the dispatch is (ADR-034).

- A scripted key sequence (`v`, `j`, `p`, `Esc`, `q`) is fed through the mockable input layer.
- **Assert:** the resulting state transitions (BOARD→VERDICTS→BOARD, selection index moves) and the
  exact `curate` argv the `p` keypress emits — without a real ledger write (that is §4's job).

---

## 6. Determinism notes

- Every fixture's `top --json` must be interpreter-stable (the repo's cross-platform discipline;
  `os.path.realpath` both sides of any path comparison — CLAUDE.md Windows 8.3 gotcha).
- The smoke assertions that check these frames must parse under bash 3.2: no `${`, no backticks, no
  quote inside a bracket expression in the heredocs (CLAUDE.md known gotcha). Golden frames are stored
  as files and compared, keeping the heredoc logic minimal.
