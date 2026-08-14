# uscha-kit 1.80.0 — bench-curation: the human verdict extended to machine-generated code (2026-08-14)

ADR-023 removes the "had" from ADR-022's honest UNMEASURED: `curation_closure` was
UNMEASURED because no human **had** curated machine-generated fixture code — not because no
human could. This release gives the human the instrument, under the EXACT discipline the M1
gate already enforces (INV-CURATION-01), and lets the descriptor report a measured closure
where verdicts exist.

## `bench-curate` (48 → 49 subcommands)

ONE human verdict (`preserve|fix|undefined`) for ONE observation of ONE bench compilation,
appended to `BENCH-CURATION.json` at the bench root:

- **The curable set is the published set.** The observations are the SAME M1 static-extractor
  observations `static_surface` publishes — re-extracted at verdict time, so a fixture edited
  after `--list` invalidates the old content-addressed id instead of silently carrying a stale
  judgment (`--list` reports it as STALE).
- **The M1 refusals, verbatim.** No batch path exists and will not; an unknown observation is
  refused; a malformed store fails closed with exit 2 in BOTH callers (`bench-curate` and
  `bench --fidelity`) — a broken verdict store must never silently degrade to UNMEASURED,
  which would hide tampering behind the honest word.
- **Append-only.** A superseding verdict appends; the earlier record stays as history, the
  last one wins.

## Measured closure in `bench --fidelity`

For a compilation with at least one human verdict, `curation_closure` becomes
`round(judged/total, 3)` with the raw `{judged, total}` alongside; with zero verdicts it stays
the literal UNMEASURED — **zero verdicts is an absence, not a 0.0**. The verdict logic is
untouched: the descriptor remains advisory by construction (AC-FC-03 re-pinned to the new
shape: UNMEASURED without a verdict, exactly judged/total with one, never anything else).

The agent never writes a verdict. The instrument ships with the store empty; measured closure
appears in `DIAMOND-BENCH.md` only after a human runs `bench-curate`, and the appendix line
then reads `curation 0.750 (judged 3/4)` instead of `curation UNMEASURED`.

## What the review caught

Two MEDIUMs, both reproduced and fixed with their regressions pinned in T130: (1) `cmd_bench`
loaded the verdict store **unconditionally**, so a plain `bench` run — which never reads
curation — was blocked by a stray corrupt `BENCH-CURATION.json`, exceeding what ADR-023
promises ("`bench --fidelity` reads the store"); the load now happens only under the flag,
and a plain run with a malformed store is pinned green. (2) A **directory** occupying the
store's path read as "no curation exists" (the exact silent-degrade the loader forbids) and
crashed with a raw traceback on write; a path that exists but is not a regular file is now
malformed — exit 2 in every caller. Two LOWs: the `--dir` flag meaning "bench root" on
`bench` but "compilation subdir" on `bench-curate` (kept — each `--help` disambiguates; noted
here as the known copy-paste hazard), and a whitespace-wrapped `--obs` being refused with the
batch-path message (now its own clear refusal). The review also confirmed a real subtlety
worth recording: content-addressed obs ids DO collide across entries (the id hashes
type+statement+path+line, not the entry), and the curation map is keyed on the full
`(entry, dir, obs_id)` triple precisely so a verdict never leaks across the collision.

`AC-BC-01..03` measured green (T130 added). Suite: 416 checks; acceptance **125/125** where
`coverage.py` is installed.
