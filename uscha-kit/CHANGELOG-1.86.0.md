# uscha-kit 1.86.0 — `uscha top` M1: the ledger gets a terminal, and the repo starts eating its own dog food (2026-08-17)

Two things ship, both curated before code (ADR-031..035 proposed, three decisions taken by the
maintainer, then M1 built against `docs/uscha-top/SPEC.md`).

## 1. `uscha top` — M1, the read-only board (ADR-031/032/034 accepted; 033/035 stay proposed)

A stdlib-only terminal application that projects the QA ledger where the programmer already lives.
No curses, no server, no state of its own: `uscha top` is a projection of files, and if it dies and
comes back it shows the same thing.

- **Engine (`qa_ledger.py top --json`, 51 → 52 subcommands).** ONE read-only subcommand computes the
  whole projection and emits one JSON: per-obligation state (`UNMEASURED | MEASURED_PASS |
  MEASURED_FAIL | QUARANTINE`; `TRACED`/`TAGGED` are never emitted in v0.1 because the ledger has
  no general-project source for them), `terminado {done, total, pct, unmeasured}`, the debtor
  decomposition `debtors {machine, you, untagged}`, `honesty`, `medians.loop_min` (real, from
  `iterations[].at`), a `burnup` of `kind:"score"` from `readiness_history`, `spec_pin` (git HEAD,
  marked not clean-room verified unless a GREEN record exists at that sha). Fields the engine
  cannot compute honestly today are **null**, by contract: `eta_min`, `age_hours`,
  `medians.verdict_min`, `drift_pct`, obligation-count burn-up (ADR-035 names each one and what
  persistence it needs). A percentage is capped at 99 whenever `done < total`, so 999/1000 can
  never round to 100 (INV-TOP-01 lives in the engine, not in the renderer). The TUI derives
  nothing — single derivation, the mirador precedent.
- **TUI (`uscha_top.py`).** `render(state, size) -> list[str]` is a pure function; the plain path
  emits zero escape bytes. BOARD mode: `DONE x/N (p%) · N unmeasured`, `machine owes · you owe ·
  untagged`, `ETA —`, honesty, spec-pin, burn-up labelled *score trend* (never "closed
  obligations"), the obligations table `ID · GATE · STATE · CASES · AGE · ACTION` with `AGE —`.
  `--once` prints one plain frame and exits 0; a non-TTY stdout behaves as `--once`. Windows is
  first-class: VT enabled through `SetConsoleMode` (ctypes); on failure the app degrades to the
  plain frame instead of emitting raw escapes. 80×24 degrades honestly (feed first, then the table
  with an explicit "N more not shown" line). Wired as `uscha top` in `install-uscha.py` exactly the
  way `mirador` is.
- **Oracle.** Golden frames at 100×32 and 80×24 over three synthetic ledgers, plus the negative
  honesty fixture: 23/24 PASS + 1 UNMEASURED renders `96% · 1 unmeasured`, never 100%. Mutation
  checks confirmed the fixtures discriminate (drop the suffix → red; break the debtor partition →
  red; drop the rounding cap → red). Frames are byte-identical under 3.8 and 3.13.
- **Not in M1, on purpose:** the live feed (`events_tail` ships as `[]`, M2), mtime polling (M2),
  VERDICTS mode and the `curate` write path (M3), `d`/`o` (phase 2). `AC-T-11..17` are recorded
  as skipped testcases — UNMEASURED, never a silent pass — until their milestone.

## 2. Dogfooding is measured, not narrated (repo rule 9, `AC-DF-01`)

The repo that teaches "measured beats narrated" had its own root ledger last recorded on
2026-07-23. From this release the ritual runs on the kit itself — smoke → `snapshot --repo uscha`
→ `readiness --record` → ledger committed in the same release commit — and the suite measures it:
the commit that last touched the engine must also carry the ledger, or the ledger's last readiness
entry must be newer than it (no git = UNMEASURED; stale = RED). What the ledger says today is the
honest ugly number: measured acceptance reads **6/172** (readiness 66.5, no cap), because `_AC_ID`/`_AC_TAG` only recognise
bare `AC-<n>` and cannot see the family-prefixed criteria the suite proves green. That number is
TRUE for the engine as it is; widening the instrument (ADR-035 item 6) is the next engine release,
never a hand-edit of the ledger.

Suite: 425 checks · 0 fail; acceptance 165/172 (7 UNMEASURED on purpose: `AC-T-11..17`, M2/M3) where `coverage.py` is installed. Every
existing instrument's output over the existing fixtures is unchanged; `cmd_dashboard` shares
`_project_name` with `top` (one derivation, two readouts) with byte-identical output.
