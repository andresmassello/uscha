# uscha-kit 1.92.0 — TERMINADO is sealed to the exact code state: evidence content-hashed at ingest, and DONE is not DONE while the seal is broken (INV-T1, ADR-038) (2026-08-19)

An external package (`audits/uscha-cierre/`, three POSIX `sh` scripts + an 11-case suite, verified
11/11 under `sh` and `dash`) stated an invariant worth having: **TERMINADO requires evidence bound
to the exact current code state — the commit and the content hash of every evidence file; stale,
altered or absent evidence = no TERMINADO.** The maintainer chose to port the *invariant* into the
engine, not the scripts (option B): the kit is stdlib Python and Windows-first, the engine does not
execute shell it was not given (ADR-008/033), and an untracked `EVIDENCIA.md` cannot be verified by
CI while `QA-LEDGER.json` is the committed truth. Of the three holes the package names, two were
already closed here (the freshness rule of 1.31.0; `evidence_origin` + clean-room, ADR-007/008);
the third — **logs swapped or edited after the run** — was not. Now it is.

## What changed

- **Content hash at ingest.** `snapshot` records a `sha256` per ingested report beside the path
  and mtime it already recorded (the same files the parser reads; unreadable → `null`, an absence,
  never a match). Older snapshots without a hash read as *unmeasured* for that check — said out
  loud in the reasons, never a silent pass or a fake break.
- **The seal is derived, never written.** `top --json` gains `terminado.sealed = {ok, reasons,
  commit, repo}` recomputed at read time from the ledger and git: the working tree is clean
  (`git status --porcelain -uall`, exempting the ledger file and the reports the last snapshot
  names), `HEAD` equals the last snapshot's `evidence_origin.commit`, and every named report still
  exists and hashes to what was recorded. No git work tree, or no snapshot yet → `ok: null`
  (UNMEASURED — a snapshot is the ingest record; without one there is no anchor, which is an
  absence, not a break; the honest limit — a board can read 100% with nothing binding it — is
  stated in SPEC §4 and measured). No new file appears anywhere.
- **INV-TOP-06.** DONE never renders 100% while `sealed.ok` is `false`: the engine caps `pct` at
  99 (beside INV-TOP-01's cap — the TUI still computes no KPI), the header carries `· unsealed
  (<first reason>)`, and MEASURED_PASS rows show `seal: <what to do>` in ACTION. `ok: null`
  renders nothing (all 16 previous golden frames byte-identical); a new frozen state
  `state-unsealed` (a real run over a fixture whose report was edited after ingest) pins the
  suffix at 100×32 and 80×24.
- **`check-terminado`** (52 → 53 subcommands): the same derivation, on the command line — exit 0
  sealed, 1 measured break (reasons on stdout, mirroring the package's messages: *stale seal:
  snapshot at X, HEAD is Y* / *repo subtree dirty: changes no snapshot covers* / *evidence altered
  after ingest: <path>* / *evidence missing: <path>*), 2 UNMEASURED — including a ledger that is
  missing or corrupt, because 1 means "I checked and it is broken" and nobody read that file. A
  hook or a human can call it, and the loop's doc now says so IN the doc: `SKILL.md` Phase 6 (both
  mirrors) tells the loop to run `check-terminado` before declaring TERMINADO — exit 1,
  re-snapshot on the current state and record why; exit 2, say the seal is unmeasured rather than
  claim a TERMINADO nobody measured.
- **The claims audit.** `uscha-kit/templates/esceptico-prompt.md` — the package's ESCEPTICO
  prompt, vendor-neutral like the rubric grader's, labelled a hypothesis until used against real
  runs; it writes nothing and gates nothing.

`AC-CT-01..11` (T146) port the package's suite onto the engine over a real temp git repo: sealed on
a clean tree at the snapshot's commit; a modified tracked file, an untracked file no snapshot covers,
a commit after the snapshot → unsealed with the reason; a re-snapshot re-seals; a report edited or
deleted after ingest → unsealed; exit codes 0/1/2; `top --json` equals `check-terminado --json`;
DONE at 100% + unsealed renders the suffix with `pct` 99; a pre-1.92.0 snapshot reads the hash
check as unmeasured. Mutations proved each pin discriminates (skip the hash → CT-06 red; skip the
HEAD compare → CT-04; drop the suffix → CT-10; drop the engine cap → CT-03).

Two decisions the measurement forced, recorded in ADR-032/038: `checked_at` is NOT part of the seal
(a second wall clock broke `top --json`'s determinism pin, AC-T-24); "no snapshot yet" is `null`, not
`false` (every live fixture sits inside this repo's git tree — `false` would have capped a legitimate
100% to 99).

The blind review of this release found the CHANGELOG narrating a loop-doc line nobody had written (now
wired in SKILL.md), the paper still saying 52 subcommands outside the gate (the gate now covers it), an
unreadable ledger reading as a measured break (now UNMEASURED, exit 2), and the live board's poll not
seeing a seal break until reload (stated as a limit, not hidden). All applied and pinned.

Suite: 434 checks · 0 fail; acceptance 195/195; the kit's own ledger reads READINESS 100.0.
