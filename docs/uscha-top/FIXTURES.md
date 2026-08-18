# FIXTURES — the `uscha top` oracle plan (governed by ADR-034)

The oracle for `uscha top` is golden frames: `render(state, size)` (pure, ADR-034) over a fixed
`top --json` object, snapshotted and asserted byte-identical in the smoke suite. This file names the
synthetic ledger fixtures, what each pins, the golden-frame matrix, the negative honesty cases, and
the before/after `curate` write-equivalence fixture. All names are generic (`backend-api`,
`mobile-app`) per repo rule 4.

Home (**shipped in M1**): `uscha-kit/tests/fixtures/uscha-top/` — one directory per ledger
fixture, `state/` for the frozen `top --json` objects the renderer is snapshotted against, and
`golden/` for the frame snapshots.

> **Status line (M1, 2026-08-17).** Sections 1 and 2 below describe what EXISTS. F3 and F4 were
> drafted here before M1 and are **not shipped** — they are marked `planned` and their rows carry
> no tick. This file states the fixture set as built, not as hoped; a matrix that ticks a fixture
> nobody wrote is the same over-claim the golden frames exist to prevent.

---

## 1. Synthetic ledger fixtures

Each fixture is a minimal ledger (plus a `CANDIDATE-DELTA.json` where quarantine is involved) that
`qa_ledger.py top --json` reads to produce a deterministic JSON `state`. Each fixture repo tree
carries **only** its ingested `reports/junit.xml` and no source file: with no source, the engine's
mtime freshness correlation is skipped entirely, so a checkout that rewrites mtimes cannot flip a
criterion between MEASURED and UNMEASURED.

**Shipped in M1 (3):**

- **F1 — healthy** (`fixture-healthy/`, 6 obligations): all `MEASURED_PASS`, no quarantine, no
  UNMEASURED. **Pins:** a legitimately full board — `DONE 6/6 (100%)` with **no** suffix (allowed by
  INV-TOP-01 precisely because nothing is outside PASS), `debtors {0,0,0}`, `eta_min:null` → `ETA —`,
  green-only board colors. This is the one frame where 100% is honest; it guards against a renderer
  that refuses to ever show 100%.

- **F2 — stale quarantine** (`fixture-stale-quarantine/`, 8 obligations): 2 `MEASURED_PASS`, 1
  `MEASURED_FAIL`, 2 `QUARANTINE` (uncurated observations heuristically matched to ACs), 3
  `UNMEASURED`, plus a third observation with `ac:null`. **Pins:** all four debtor buckets at once,
  the per-state colors, `AGE —` on every row (v0.1), `ac:null` rendered honestly (no fabricated
  link), and the only real median in the set (`medians.loop_min: 40`, from three iteration
  timestamps).

- **N1 — honesty negative** (`fixture-honesty-negative/`, 24 obligations): 23 `MEASURED_PASS` + 1
  `UNMEASURED`. See §3 — this is the discriminator, not a happy path.

**Planned — M2/M3, not shipped:**

- **F3 — re-pinned scope** (`fixture-repinned-scope/`) *(planned)*: a `readiness_history` with a
  score step across a spec re-pin, and a changed obligation denominator. Would pin a denominator
  differing from F1/F2/N1 so the fixed-per-commit `|O|` is exercised. M1 covers the score burn-up
  and the honesty-beside-DONE rule through F1/F2/N1, which already carry three different
  denominators (6, 8, 24).
- **F4 — real demo module** (`fixture-demo-module/`) *(planned, M2)*: the demo module's real ledger,
  end-to-end. It is the fixture that would exercise the event feed from real `ledger["steps"]`, and
  the feed itself is M2 — so it arrives with the feature it measures, not before it.

**Frozen states** (`state/`): `state-healthy.json`, `state-stale-quarantine.json`,
`state-honesty-negative.json` are verbatim `top --json` output with the two volatile members
(`generated_at`, the git sha inside `spec_pin`) normalized to fixed values. `state-traced-tagged.json`
is the one **deliberately forced** state: it carries a `TRACED` rung, a `TAGGED` rung and a null
`spec_pin` — three things the v0.1 engine can never emit — so the renderer's promise that those
rungs read gray and never PASS is measurable (§3, AC-T-08, AC-T-06).

---

## 2. Golden-frame matrix

`state × size × mode`. Sizes: 100×32 (reference), 80×24 (degradation floor). Modes: BOARD only in
M1; VERDICTS frames arrive with VERDICTS mode (M3).

| Frozen state | 100×32 BOARD | 80×24 BOARD | 100×32 VERDICTS | 80×24 VERDICTS |
|---|---|---|---|---|
| F1 healthy | ✓ shipped | ✓ shipped | — (empty queue) | — |
| F2 stale quarantine | ✓ shipped | ✓ shipped | planned (M3) | planned (M3) |
| N1 honesty negative | ✓ shipped | ✓ shipped | — | — |
| forced TRACED/TAGGED + null pin | ✓ shipped | ✓ shipped | — | — |
| F3 re-pinned scope | planned | planned | — | — |
| F4 demo module | planned (M2) | planned (M2) | planned (M3) | planned (M3) |

Eight frames ship in M1. The 80×24 frames assert the degradation rule (AC-T-21): the layout holds,
the frame is exactly 24 lines, no line exceeds 80 columns, and the feed is what shortens — the
header and board are never the first casualty.

---

## 3. Negative honesty cases

These exist to fail a cheating implementation, not to describe the happy path.

- **N1 — 23/24 + 1 UNMEASURED** (`fixture-honesty-negative/`): 23 `MEASURED_PASS`, 1 `UNMEASURED`.
  Golden frame MUST render `96%` with the `· 1 unmeasured` suffix and MUST NOT render `100%`
  (AC-T-23, INV-TOP-01/02). A renderer that rounds or drops the unmeasured obligation fails here.
- **Verdict does not move DONE** *(planned, M3 — the write path it measures is M3)*: paired render
  over F2; the BOARD `DONE` value is byte-identical before and after a verdict is applied through the
  write path, and only the debtor cardinalities change (AC-T-16, INV-TOP-03). Asserts there is no
  auto-rerun.
- **Null medians → `ETA —`** *(shipped: F1, F2, N1)*: every state renders `ETA —` because
  `medians.verdict_min` is null; no fixture is allowed to render a numeric ETA in v0.1 (AC-T-03).
- **TRACED/TAGGED → gray, never PASS** *(shipped: `state/state-traced-tagged.json`, both sizes)*:
  the two rungs are forced into the state by hand precisely because the engine cannot emit them;
  each renders in the UNMEASURED-class gray, never green (AC-T-08).
- **spec_pin null → `—`** *(shipped: the same forced state carries `spec_pin: null`)*: the header
  renders `spec_pin —`, never a fabricated SHA (AC-T-06, INV-TOP-05).

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
