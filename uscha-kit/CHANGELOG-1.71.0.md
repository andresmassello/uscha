# uscha-kit 1.71.0 — fidelity measures what the delta measured (2026-08-11)

FIELD-RUN-001's second finding, and the one the field run existed to produce: `fidelity`
computed `unexplained_code` over the **whole repo** even when the delta it measures was
bounded with `discover --path` to a single file. On the installer run that read **0.93**
(13 of 14 prod files "unexplained") — true of the repo, meaningless for a discovery scoped
to one file. Two scopes laundered into one number, the exact disease this program treats.

## The fix (AC-FV-06)

Every mechanical dimension now reads the bound the delta already records (1.70.0) and scopes
its measurement to it: `unexplained_code`, `contracts` and the marker scan behind
`traceability` all measure only files under `<path>`. The scope is **named in each
dimension's provenance** (`bounded to <path>`) and in the output header, so a bounded vector
can never be read as a whole-repo one. Same installer run, corrected:

```
FIDELITY uscha [bounded to uscha-kit/install-uscha.py]
  contracts         1.00   40/40 canonical static items still derive from the code
  curation_closure  1.00   40/40 OBS carry a ledger verdict
  unexplained_code  0.00   0/1 bounded prod file with no lineage
```

An unbounded `fidelity` (no `--path` in the delta) is unchanged — it measures the whole repo,
as before. The bound only narrows when the delta declares one.

Also in this release: **FIELD-RUN-001 lands in `discovery/FIELD-RUN-001/`** — the first
end-to-end M1 loop on real code (the kit's own installer), with its delta, canonical package,
ledger, bounded fidelity vector and a README recording the measured curation burden
(~0.17s/OBS) and both findings the run surfaced. The method critiqued itself by running on
itself.

## What the fresh review caught

One LOW, fixed before shipping rather than deferred because it contradicted this release's
own thesis: the first pass scoped the **numerator** of `traceability`/`contracts` (the marker
scan and static re-extraction) to the bound but left the **denominator** — `CANONICAL.json`,
which `promote` merges repo-wide — global. An earlier unbounded promote would then count
out-of-bound canonical items as "no longer derives", deflating `contracts` to a number that
mixed the two scopes the release exists to separate. The denominator is now scoped too (an
item is under the bound when its primary provenance file is), and `AC-FV-06` exercises it
with a canonical item deliberately left outside the bound.

`AC-FV-06` measured green (T124). Suite: 410 checks; acceptance **79/79** where `coverage.py`
is installed.
