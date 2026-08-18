# uscha-kit 1.89.0 — `uscha top` M3: the human's verdict, from the terminal, through the one write path that already existed (2026-08-18)

M3 closes `uscha top` v0.1 (SPEC §5): VERDICTS mode. ADR-033 is Accepted; the terminal projection
now reads everything and writes exactly one thing.

## What changed

- **VERDICTS mode (`v`, back with `t`/`Esc`).** The list of uncurated observations (`OBS-id ·
  title · AC-x · pending`, ordered by the criterion they anchor, then id — not by age, because no
  age is recorded and sorting on a value nobody records would be a fabrication; named as an
  override of the draft SPEC). `1-9`/`j`/`k` select; the pane shows the machine's candidate
  (typed: `type · site`, `claim: <whole statement>`) and the evidence (one line per provenance
  entry, `file:line`, evidence class, tool) side by side, stacked under 100 columns; claims wrap
  and are never cut — a pane too short names the shortfall.
- **The single write.** `p` / `f` / `u` run `qa_ledger.py curate --repo R --obs OBS --verdict
  {preserve,fix,undefined} --human <you> --note "recorded via uscha top"` — ONE process per
  keypress, synchronously; success reloads the state and advances to the next pending OBS; an
  empty queue returns to BOARD; the engine's refusal (a batch, an unknown OBS) is surfaced, not
  swallowed, and nothing advances. The TUI never authors a name: `--human` is explicit (also
  forwarded by the `uscha top` launcher) or `curate`'s own default applies. There is no other
  write in `uscha_top.py` (asserted).
- **INV-TOP-03, measured.** After a real verdict on a fixture copy: `terminado.done` unchanged
  (2/8 → 2/8), `debtors.you` 2 → 1, `untagged` 3 → 4 — a verdict moves the debt, only a green
  rerun closes it. **Write-equivalence:** the record the TUI path appends is member-for-member
  identical to a manual `curate` call with the same arguments; `at` is a wall clock read inside a
  subprocess and is compared by shape, not byte (the suite injects no clock across a process
  boundary — said plainly, not implied).
- **Engine `top --json`.** `observations[]` (only uncurated ones, as before) now carry `repo`,
  a sanitized `title` (≤72), typed `candidate[]` and per-provenance `evidence[]`; malformed
  provenance degrades to no evidence line, never raises. Read-only unchanged.
- The BOARD key hint reads `[v] verdicts` (it said `(M3)` while M3 was future); the ten BOARD
  golden frames were regenerated for that one string; two VERDICTS frames were added.

Measured: `AC-T-13..17` (T141) — queue contents and order; side-by-side/stacked pane with
uncut claims; one `curate` per keypress with the documented argv, advance, empty-queue return,
refusal surfaced; INV-TOP-03 on a real verdict; write-equivalence. The interactive loop itself
is not driven by the suite (no TTY): every decision it makes lives in the pure functions that are.

With this, all 24 `AC-T` criteria are measured. `uscha top` v0.1 is complete: board, feed,
verdicts. Phase 2 (`d` diff, `o` rerun, spec-lens) stays out, as SPEC §6 says.

The blind review of this milestone found the one realistic path to what INV-CURATION-01 forbids: a
held key or buffered keystrokes would have fired one legal single-OBS verdict per repeat, each on the
NEXT observation the human never read. Fixed before this shipped: pending input is drained after every
verdict attempt, `p/f/u` are ignored for 250 ms afterwards (the status line says so), the write lives in
one function the AST guard proves is called once and never inside a loop, and a frozen `--state`
snapshot refuses verdicts. Also: `[r]` advertised in VERDICTS, the last verdict's confirmation survives
the return to BOARD, the order oracle in the suite reimplements the family rule instead of a bare-id
shortcut.

Suite: 429 checks · 0 fail; acceptance 178/178 — every criterion of this repo, `uscha top`'s 24 included,
measured green. Readiness of the kit's own ledger: 99.3 — READY.
