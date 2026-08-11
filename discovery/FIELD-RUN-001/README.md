# FIELD-RUN-001 — the Diamond M1 loop over `uscha-kit/install-uscha.py`

The first end-to-end run of the M1 curation loop on real code (ADR-013/014). Dogfooding:
the kit's own installer as the legacy target.

## What ran

```bash
qa_ledger.py discover --repo uscha --path uscha-kit/install-uscha.py   # 40 static OBS
# 40 human verdicts, one per OBS (Andrés: all "preserve"), no batch path
qa_ledger.py promote  --repo uscha    # 40 -> CANONICAL.json, all with derived_from lineage
qa_ledger.py fidelity --repo uscha    # the vector, bounded to the same target
```

## Measured

- **Curation burden: 40 OBS in 6.7s, ~0.17s/OBS** (the mechanical cost; the human's
  reading time is the real burden and is not counted here — the point of FR-002 will be a
  target with genuine `fix`/`undefined` decisions).
- **Fidelity vector (bounded to `uscha-kit/install-uscha.py`):**
  - `contracts` **1.00** — all 40 static signatures still derive from the code.
  - `curation_closure` **1.00** — all 40 carry a ledger verdict.
  - `unexplained_code` **0.00** — 0/1 bounded prod file without lineage.
  - `traceability` **0.00** — no `uscha-spec:` markers in the installer (never annotated;
    honest, not a defect — an existing file the migrator did not tag).
  - `behavior` UNMEASURED — no golden of the installer ingested.
  - `semantic` UNMEASURED [advisory] — never gates.

## Two findings the run produced (each shipped as its own release)

1. **`discover --path`** (1.70.0, AC-DD-07) — the ADR's own `--path` signature was missing;
   an unbounded discover emitted 197 static OBS (134 engine-twin) where the bounded target
   emits 40. "Real, bounded" was unimplementable without it.
2. **fidelity respects the bound** (1.71.0, AC-FV-06) — `unexplained_code` first reported
   0.93 by measuring the whole repo against a delta bounded to one file. Two scopes mixed
   into one number. Now every mechanical dimension is scoped to the delta's recorded bound,
   and the scope is named in each provenance.

The method found both by running on itself — the loop's first job was to critique the loop.
