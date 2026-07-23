# uscha-kit 1.50.0 — receipts: every number cites its evidence (2026-07-23)

The mirador's footer has said *"click a milestone to see its receipt"* since 1.32.0 — and the
engine fed that drawer a hardcoded `{}`. The machinery waited eighteen releases for data that
never came. This release wires it, and extends the same principle to every number on the page:
**a figure you cannot trace to a file and a timestamp is narration wearing a suit.**
Smoke suite: 381/381.

## The provenance was always in scope — and being thrown away
Three separate places computed a fact while holding its receipt, then discarded it:

- `_ac_tags` read the testcase NAME and the report PATH to tally green/red per criterion —
  and kept only the integers. Now each tag carries `cases: [{test, report, ok}]` (capped at 8:
  a receipt cites evidence, it is not a dump), aggregated across repos and carried through
  `readiness --json` into the dashboard's per-criterion items.
- Every coverage backend (maven, lcov, cobertura, go, gradle, ant) matched its report file
  and returned only the numbers. Now the returned dict carries `reports: [paths]`.
- `_mirador_adrs` derived id/title/status from the file it was reading and dropped the
  filename. Now each ADR row carries `file`.

## The drawer, fed
`cmd_dashboard` now builds `evidence` from recorded facts only:

- **spec** — the ACCEPTANCE file, criteria counts, measured tally, untagged warning.
- **adr** — every ADR with its status and source file.
- **build** — per repo, the last snapshot: when it was taken, prod/test LOC, tests verdict
  with report paths + mtimes + freshness, coverage pct with its report path.
- **qa** — cycles per repo with the burn-down tail, plus which gates are persisted.
- **verify** — the last `readiness --record` entry, the current score/band, any active cap,
  and how many history records back the time-lapse.
- **prod** — a receipt for the ABSENCE of evidence: the method stops at the PR; merging and
  deploying are human acts the ledger does not record, by design.
- **ac:AC-nn** — one receipt per criterion, **cases-driven, never status-driven**: a measured
  one cites the green testcases that carry its name and the reports they live in; a criterion
  with green AND red testcases shows BOTH and names the veto (*"veto rojo"* — fail-closed, a
  hidden vetoed green would be the receipt lying about the evidence it exists to cite); a
  narrated one with no cases says *"tildado a mano — ningún testcase lo respalda"*; an open
  one says nothing backs it yet. User-authored strings (testcase names, paths, titles) are
  escaped before entering the drawer, so a crafted name cannot paint fake verdict tokens.

A phase with no recorded facts gets NO key — and clicking it now opens an honest "sin recibo"
drawer instead of the old silent no-op (a click that does nothing reads as broken; a missing
receipt is itself a fact worth stating).

## Acceptance rows are clickable
Each row in the Acceptance panel opens its criterion's receipt (keyboard-accessible,
`role=button`). The drawer is the same one the trail uses — one mechanism, more keys.

Regression: smoke **T96** — the AC receipt cites testcase + report; the mixed green+red
criterion does not close AND its receipt shows both cases naming the veto; narrated says so;
build cites the coverage path; ADRs carry their file; a facts-less phase has no evidence key.
The 1.10.0 edge-case check updated: tags now assert counts by key (the dict grew `cases`).
