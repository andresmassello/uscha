# uscha-kit 1.70.0 — the field run's first finding: a discovery you cannot bound (2026-08-11)

FIELD-RUN-001 (the full M1 loop over `uscha-kit/install-uscha.py`, per ADR-014) found its
first gap before its first command ran: the originating handoff's signature was
`discover --path <target>`, and 1.69.0 shipped without the bound. Measured, not argued: an
unbounded `discover` over this repo emits **197** static observations — 134 of them the
engine twins — where the "real, bounded" target the ADR names emits **40**. A curation
session over 197 engine internals is not a bounded field run; it is a denial-of-service on
the human the gate exists to serve.

## `discover --path` (AC-DD-07)

```bash
python qa_ledger.py discover --repo <r> --path uscha-kit/install-uscha.py --narrated ...
```

The bound restricts the **mechanical** scans — static extraction and the measured golden
inventory — to one subtree or file; narrated input stays the skill's to scope. Three
postures, all in the house style:

- A bound that **matches no tracked file is a named refusal** (exit 2) — a typo'd path
  silently emitting an empty delta is exactly the silent-degrade trap the loader class
  exists to close.
- A bound that escapes the repo tree is refused (reusing `_gc_rel`, the confinement the
  evidence refs already pass through).
- The bound is **recorded in the delta** (`"path"` key, conditional), **surfaced in the
  rendered twin** the human curates from (a bounded discovery announces itself as PARTIAL,
  so its shrunk INV-CURATION-01 promotion surface is never undisclosed), and **covered by
  the integrity seal** (which now spans observations + repo + path, not observations alone).

## What the fresh review caught

A focused review of the bound itself found no correctness break and three gaps worth
closing before tagging, all reproduced:

- **HIGH — the bound was recorded in the JSON but invisible in the `.md` twin the human
  reads.** A bounded, partial discovery rendered identically to a complete one; the
  promotion gate's surface shrank silently. The twin now carries a `BOUNDED discovery`
  banner naming the path.
- **MEDIUM — the recorded `path` sat OUTSIDE the integrity seal**, the first unsealed field
  whose value changes what the delta means. The seal (`_delta_seal`) now covers
  observations, repo and path; a hand edit of any is a named malformation.
- **MEDIUM — `--path ""` silently degraded to a full-repo scan** (a wrapper passing an
  unset variable). An empty bound is now a named refusal, and the bound is normalized
  (`./src`, `src/`, `/src` → `src`; `.`/`..` refused) so a shell-completed path is not
  misattributed to a nonexistent one.

ADR-013 amended in the same change, stating the field origin of the addition. Suite: 410
checks (AC-DD-07 is a sidecar case inside T123, not a new check); acceptance **78/78** where
`coverage.py` is installed.
