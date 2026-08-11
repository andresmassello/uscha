# uscha-kit 1.69.0 — Diamond M1: the curation loop closes on items, not prose (2026-08-11)

M1 of the Diamond program, planned one session earlier as ADR-013/014 with all seventeen
criteria written before a line of code existed. The thesis in one sentence: the loop
(code → observations → human curation → canonical) cannot close on prose — narrative curates
by the page, the loop needs items. 1.64.0's markdown candidates and verdict table were the
right invariant on the wrong storage; this release supersedes the storage and keeps the
invariant.

## `discover` — subcommand 37

```bash
python qa_ledger.py discover --repo <r> --narrated discovery/narrated.json
```

Emits `discovery/CANDIDATE-DELTA.json`: typed observations
(`behavior | invariant | contract | config | dependency | decision_trace`), each with a
strict evidence class the ENGINE assigns — `measured` (only source: a golden/characterization
run the ledger actually ingested, run timestamp in provenance), `static` (deterministic
extraction: public signatures via `ast`, dependency manifests — Python-only in v0, every
other stack reported UNSUPPORTED rather than guessed), `narrated` (the skill's inference:
legitimate, useful, and labeled). A narrated input that tries to self-classify is refused,
not downgraded. OBS ids are **content-addressed**
(`OBS-sha256(type + statement + primary provenance)[:12]`), so re-running discovery over
unchanged code is byte-identical — and a hand-edited statement breaks its own id, which the
strict loader reports as tampering. A rendered `.md` twin regenerates on every run; hand
edits are overwritten and named as such.

## `curate` / `promote` — verdicts become ledger objects

```bash
python qa_ledger.py curate --repo <r> --obs OBS-xxxxxxxxxxxx --verdict preserve|fix|undefined
python qa_ledger.py promote --repo <r>
```

ONE observation, ONE human verdict, recorded append-only in `QA-LEDGER.json` — re-curation
supersedes, never deletes, and both records stay retrievable. **No batch path exists, and
the CLI asserts its absence**: a comma list is refused naming the rule. `promote` moves only
`preserve` observations into `discovery/CANONICAL.json` with `derived_from` lineage; `fix`
becomes an `ISSUES-DEFERRED.md` work item (never canonical); `undefined` stays open and
visible in the readouts (dashboard `candidate_delta` key, conditional). Promotion over ANY
uncurated OBS is a hard refusal naming the ids, and `phase --require pr-ready` blocks on the
same fact — INV-CURATION-01 survives the storage change untouched, and creating the delta is
still the opt-in.

## `fidelity` — a vector, never a blend (ADR-014)

Five independently measured dimensions, each with its own provenance: `traceability`
(canonical items reachable via the uscha-spec id machinery), `behavior` (the latest ingested
golden-diff verdict, clean-room noted where available), `contracts` (canonical static items
still derivable from the code right now), `curation_closure` (curated OBS / total),
`unexplained_code` (v0 deliberately crude — unit = source FILE, over-fires on monoliths BY
DESIGN; crude and honest beats fine-grained and narrated). Plus the quarantine: `semantic`
enters as `advisory` and **can never gate** — declaring it blocking in config is an engine
REFUSAL naming INV-ADVISORY-01, not a configuration; `log-gate --kind` is a closed
vocabulary so the side door does not exist either, and the smoke suite measures that it
stays closed. Deterministic end to end: same inputs, same numbers, no LLM anywhere in the
measured path.

## The skill evolves with the storage

`uscha-reverse-discovery` Phase 3 now writes narrated observations as `{type, statement,
files}` and runs `discover` (the engine derives measured/static itself); Phase 4 presents
one OBS at a time and records each human verdict via `curate`, then runs `promote`. Repos
on the 1.64 `.md`-candidate flow keep working unchanged — `curation-check` and
`BEHAVIOR-LEDGER.md` are untouched; new runs use the delta.

One ADR amendment made at implementation time, stated rather than slipped: ADR-013 said
`BEHAVIOR-LEDGER.md` "becomes a rendered view" of the ledger's curation objects —
regenerating that file would read as tampering to the very append-only check that guards it,
so the rendered view of delta verdicts is the `CANDIDATE-DELTA.md` twin instead, and the ADR
now says what the engine does.

## What the fresh review caught

Two HIGH and four MEDIUM, every one reproduced before being fixed:

- **HIGH — a structurally malformed delta (a provenance that is a list, a non-string
  statement) crashed `phase`, `dashboard`, `curate` and `fidelity` with a traceback** — the
  loader touched fields before checking their shape, so "malformation is exit 2, never a
  silent degrade" was true only for shapes it had imagined. Shape is now checked before use;
  the crash class is a named malformation everywhere, and the read-only readouts degrade
  instead of dying.
- **HIGH — a JSON syntax error in `--config` silently DISABLED the INV-ADVISORY-01
  refusal**: `fidelity` swallowed the parse error and proceeded as if no gate were declared.
  The release's headline invariant evaporated on a trailing comma. A config that cannot be
  parsed cannot declare gates — exit 2, named.
- The OBS id covers type + statement + primary provenance, so **a hand edit flipping
  `narrated` → `measured` survived the id recompute** and could launder inference into
  measured evidence through `promote`. The delta now carries an **integrity seal** over the
  full observation set (reusing the ledger's own `_integrity_hash`); any field edit is a
  named malformation.
- Malformed narrated input with a non-string ref was a TypeError traceback instead of the
  promised named refusal; the twin-overwrite notice printed to stdout and broke `--json`
  exactly on the path AC-DD-06 advertises; `fidelity` mislabeled a malformed delta as
  "no delta" and exited 0 while `curate`/`promote` exited 2 on the same file.

All six are regression-tested in T123/T124 (`review-h1/h2/m1/m3/m4` cases). Three LOW
findings went to `ISSUES-DEFERRED.md`, per the severity gate.

`AC-DD-01..06`, `AC-CU-01..06`, `AC-FV-01..05` measured green (T123/T124, sidecar pattern).
Suite: 410 checks. Acceptance: **77/77** where `coverage.py` is installed.
