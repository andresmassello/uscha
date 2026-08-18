# uscha-kit 1.87.0 — the instrument reads family-prefixed criteria: 6/172 becomes 171/178 on the kit's own ledger (2026-08-18)

One engine change, its own release, because its blast radius deserved its own turn (ADR-035 item
6 → ADR-036, Accepted).

## What changed

- **Grammar.** An acceptance criterion id is `AC-<n>` (as before, normalised to `AC-<int>`) OR
  `AC-<FAMILY>-<n>` with `FAMILY = [A-Za-z][A-Za-z0-9]*`, normalised to `AC-<FAMILY>-<int>` —
  so `AC-T-01 == AC-T-1 == ac_t_1`, `AC-BC-07 == AC-BC-7`. Both sides of the measurement read it:
  `_AC_ID` (ACCEPTANCE.md checkboxes) and `_AC_TAG` (JUnit testcase names). The bare pattern is
  byte-identical to 1.86.1; the family pattern is a separate, disjoint regex, so a bare tag can
  never appear beside a family tag. camelCase family names (`testACBC07x`) are NOT recognised —
  the separators are what make the family unambiguous. The statusline (`uscha_progress.py`) uses
  the same grammar, so it can never disagree with the ledger it summarises.
- **What that changes on this repo.** ACCEPTANCE.md carries 178 criteria, 172 of them
  family-prefixed; the smoke suite proves them green in `reports/junit/uscha-acceptance.xml`.
  Until now the engine reported "6/172 measured, 166 criteria without an AC-ID" — TRUE for the
  instrument as it was, and the number `uscha top` printed on itself since 1.86.0. Now it reads
  **171/178 measured (96.1%), readiness 97.4 — READY** (the unmeasured ones are the M2/M3 `AC-T-11..17`, skipped on purpose).
  `uscha top` on this repo goes from `DONE 6/172` to `DONE 171/178 (96%) · 7 unmeasured` with the same code.
- **Named cost.** A test called `test_ac_helper_2` now tags a criterion `AC-HELPER-2` nobody
  declared. Harmless — a tag with no matching criterion closes nothing — but real, and the price
  of accepting the `ac_t_1` spelling that python/go test names force. Recorded in ADR-036.
- Everything downstream flows from the two helpers (`_ac_id_of`, `_ac_tag_ids`): readiness
  acceptance dimension, narrated-only / measured-but-unticked / without-an-AC-ID advisories,
  receipts, dashboard, `top --json` obligations (order: bare by number, then families
  alphabetically), simplicity-check duplicates, doctor hints. No second derivation.

Measured by `AC-FA-01..05` (T140): parse both forms in order; JUnit tags both forms with no
spurious keys; bare-id fixtures byte-identical old vs new engine (`readiness`, `dashboard`);
statusline count equals the ledger's; `top --json` ids/states/order over a mixed ACCEPTANCE.md.

Suite: 428 checks · 0 fail; acceptance 171/178 (7 UNMEASURED on purpose: `AC-T-11..17`, M2/M3).
The first 1.87.0 suite run went red on T125: `discover`'s canonical map still assumed a bare id and
crashed on `AC-DD-07` — a consumer the widening had missed. Fixed and pinned (`AC-FA-06`) before
this shipped; the instrument caught the instrument.
