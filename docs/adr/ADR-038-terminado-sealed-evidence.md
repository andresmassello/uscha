---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/.claude/skills/uscha-devloop/uscha_top.py
  - uscha-kit/skills/uscha-devloop/uscha_top.py
---
# ADR-038: TERMINADO is sealed to the exact code state — evidence files are content-hashed at ingest, and DONE is not DONE while the seal is broken (INV-T1, ported into the engine)

## Status: Accepted (1.92.0; option B chosen by the maintainer 2026-08-19)

## Context
An external package (`audits/uscha-cierre/`, kept as reference: three POSIX `sh` scripts + a
self-contained 11-case suite, verified 11/11 under `sh` and `dash`) states an invariant worth
having:

> **INV-T1**: TERMINADO requires evidence bound to the exact current code state — the commit,
> the diff since the base, and the content hash of every evidence file. Stale, altered or absent
> evidence = no TERMINADO.

It names three holes. Two are already closed by the kit as it is: (1) *"tests pass" from an old
run* — the freshness rule (1.31.0) discards a JUnit report older than the source it claims to
measure; (2) *code touched after the review* — every snapshot records `evidence_origin`
(commit + dirty, ADR-007) and the clean-room verifies the COMMIT (ADR-008). The third is NOT
closed: (3) *logs swapped or edited after the run* — the engine ingests reports by path and mtime,
never by content. That is the piece worth taking.

The package's SHAPE conflicts with the kit and is not taken (decision recorded 2026-08-19):
`sh` as product code adds a runtime the kit's Windows-first surfaces do not have (the `.ps1` was
removed in 1.50.2 for the same reason); making the engine call `check-terminado.sh` would have it
execute shell it was not given explicitly (ADR-008, ADR-033) and would create a second derivation
of TERMINADO next to `top --json` (the 1.48.1 sin); and an untracked, gitignored `EVIDENCIA.md`
cannot be verified by CI, while `QA-LEDGER.json` is the committed truth (repo rule 9).

## Decision
- **Content hash at ingest.** `snapshot` records, per ingested report, its `sha256` next to the
  path and mtime it already records. Nothing else changes in the snapshot.
- **The seal is derived, never written.** `top --json` gains `terminado.sealed = {ok, reasons[]}`
  recomputed at read time from what the ledger already carries: **the tracked repo's subtree**
  is clean (`git status --porcelain -uall -- .` inside the configured repo path, the same
  per-path scoping ADR-007 uses — a monorepo sibling's edit is not this repo's dirt), ignoring
  `QA-LEDGER.json` and the report files the last snapshot names; `HEAD` equals the last
  snapshot's `origin.commit`; every report file
  the last snapshot names still exists and hashes to what was recorded. No git → `ok: null`
  (UNMEASURED, INV-TOP-05), never a silent pass. No new file appears anywhere.
- **INV-TOP-06.** DONE never renders 100% while `sealed.ok` is not `true`; the header carries the
  suffix `· unsealed (<first reason>)` and the board's ACTION column says `seal: <what to do>`.
  A verdict does not seal; a rerun's snapshot does — the same asymmetry as INV-TOP-03.
- **`check-terminado`.** One read-only subcommand: prints the seal verdict and its reasons, exit 0
  when sealed, 1 when not, 2 UNMEASURED (no git work tree, no snapshot, unreadable ledger) —
  the enforcement a hook or a human can call. It is the engine's own recomputation, one
  derivation shared with `top --json`.
- **The claims audit.** `ESCEPTICO.md` ships as `uscha-kit/templates/esceptico-prompt.md`, a
  vendor-neutral prompt like the rubric grader's, labelled a hypothesis until it has been used
  against real runs; it writes nothing and gates nothing.

## What is measured (`AC-CT-01..11`, mirroring the package's suite T1..T10 — shipped)
seal valid on a clean tree at the snapshot's commit; a tracked file modified → unsealed with
reason; an untracked file no snapshot covers → unsealed; a new commit after the snapshot → stale;
a re-snapshot re-seals; a report edited after ingest → unsealed (hash); a report deleted →
unsealed; `check-terminado` exit codes 0/1/2; `top --json` `terminado.sealed` equals the
subcommand's verdict; DONE at 100% renders the `unsealed` suffix when the seal is broken (frozen
state + golden); no git → `ok: null` and no suffix.

The eleven criteria are in `ACCEPTANCE.md` and are measured by smoke **T146** over a real temp git
repo the ENGINE drives (`init` → a real JUnit report → `snapshot`), plus two golden frames over
`state/state-unsealed.json`.

**Two things shipped differently from the draft above, both recorded rather than quietly changed:**

1. **`ok: null` renders NOTHING on the board.** The draft said the header would say
   `seal unmeasured`. It does not: an unmeasured seal is the state of every frozen fixture and of
   every non-git tree, and decorating the header with the absence of a measurement would turn
   INV-TOP-05's `—` into permanent noise — and would have moved all sixteen existing golden
   frames for a line that says nothing. The seal is shown only when it is measured (SPEC §4).
2. **"No snapshot recorded yet" is UNMEASURED, not a break.** The reference `sh` package calls a
   missing `EVIDENCIA.md` a rejection, and that is right for a file whose only job is to be the
   seal. A snapshot is the INGEST record: with none, there is no anchor to compare the tree
   against — not stale, not altered, simply nothing measured. The honest cost is stated in SPEC
   §4: a board can read 100% with nothing binding that evidence to a commit. What does not
   soften is the gate — `check-terminado` exits **2** there, so a hook gating on exit 0 refuses.

## Consequences / Risks
+ The invariant lands where the evidence already lives; CI can verify it; one derivation.
- A `snapshot` taken on a dirty tree still records `dirty: true` (ADR-007) — the seal is honest
  about it (`unsealed: measured dirty`), it does not forbid the snapshot.
- Hashing large reports at every `top --json` read: bounded by the report set the last snapshot
  names (a handful of files); measured, not assumed, in the smoke.
- **The live board can hold a stale seal.** `uscha top` polls the LEDGER's mtime, so the seal is
  recomputed on reload (`r`), on a ledger change and after `o`; a source edit or a new commit
  alone does not trigger a redraw until then, and a board that was sealed can keep saying so for
  as long as nobody refreshes it. Under-claimed here rather than papered over: widening the poll
  to the tracked subtree is future work, and `check-terminado` — which recomputes on every call —
  is what a hook or a human gates on meanwhile.

## What this ADR does NOT decide
The full "tribunal" the package's design mentions (four judges, severities, ratchet) stays in
its incubator; a size-based bypass is not introduced (the package forbids it too).

## Verification (1.92.0)
- `AC-CT-01..11` green in smoke T146 (sidecar `.ct-cases.json`, the same contract as the other
  bespoke families); the eleven ids are emitted into `reports/junit/uscha-acceptance.xml`, so a
  missing case reads UNMEASURED and never a silent pass.
- Mutation-checked, each mutation caught by exactly one criterion: dropping the hash comparison
  → AC-CT-06 red; dropping the `HEAD` comparison → AC-CT-04 red; dropping the header suffix or
  the `seal:` ACTION cell → AC-CT-10 red; dropping the engine-side 99 cap → AC-CT-03 red.
- All sixteen pre-existing golden frames byte-identical; two new frames added.
- `terminado.sealed` and `check-terminado --json` asserted equal member for member (AC-CT-09):
  one derivation, two surfaces.
