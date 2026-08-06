# uscha-kit 1.64.0 — curation: candidates in quarantine, verdicts on the record (2026-08-06)

Reverse discovery, slice 1 — the layer the interview identified as the differentiator, and
the one that required renegotiating standing doctrine instead of silently violating it.

## The renegotiation (ADR-009)

The `uscha-reverse-discovery` skill said: *never author an inferred SPEC of the old system*.
The rule guarded against a real failure — an LLM's reading of legacy code is plausible on the
surface and divergent from reality — but at real-legacy scale it made the human a typist: 200
behaviors, 200 hand-written specs. The resolution is **quarantine**: the agent may author
CANDIDATES (`discovery/*.md`, mandatory `evidence.type` / `evidence.refs` / `confidence`
frontmatter; `inference` is always `low`), and **nothing is promoted without a human
verdict**. The protection moved from "never author" to "never promote without judgment" —
and it moved from prose to measurement: **INV-CURATION-01** in the CONSTITUTION, enforced by
the engine, fail-closed.

## `curation-check` — subcommand 34

```bash
python qa_ledger.py curation-check --repo <name> [--json]
```

- Validates every candidate: frontmatter shape, evidence types, and **refs resolved against
  real files** (`path`, `path:N-M`, `path#fragment` — a ref that does not resolve makes the
  candidate invalid, *named*, never silently skipped: a skipped candidate would walk past the
  gate unjudged).
- Parses `BEHAVIOR-LEDGER.md` strictly (ADR-010): six columns, verdict ∈
  `preserve`/`fix`/`undefined` — anything else is malformation, not a fourth state — and
  every verdict names its ADR. Malformed → `exit 2`, because under this gate a silent "no
  verdicts" would *unblock* exactly what the gate guards.
- **Append-only, verified against git**: HEAD's rows must be a byte-prefix of the working
  file (line endings normalized — with `core.autocrlf`, git stores LF and checks out CRLF,
  and the first probe on Windows read that translation as tampering). Revert = new row + new
  ADR; the latest row per candidate wins. No git → `unmeasured`, reported as such — the
  suite caught the first build conflating "no git" with "file not in HEAD yet".
- The three verdicts have three distinct, verifiable effects: `preserve` →
  `promote_as_is`, `fix` → `promote_with_declared_divergence` (consumed by slice 2's
  oracle), `undefined` → `excluded`.
- Exit codes: `2` malformation/tampering · `1` valid candidates awaiting verdict · `0` all
  judged, or feature unused.

## The gate is in the phase machine, and it is attributable

While any candidate lacks a verdict, `pr-ready` is blocked **naming the candidate** — same
derivation as every other gate, guarded for the `integration` synthetic scope (the 1.63.0
lesson, applied this time instead of re-learned). T120 proves attribution the AC-CR-06 way:
the same ledger reaches `pr-ready` with no `discovery/`, is blocked by one unjudged
candidate, and opens again the moment the verdict lands. No `discovery/` directory → the
feature does not exist, behavior identical to 1.63.0 (AC-RD-07).

## Skill evolved, not replaced

`uscha-reverse-discovery` keeps its facts-first spine (map → golden → summary) and gains two
phases: **Candidates** (emit quarantined claims, run `curation-check`, echo it verbatim — the
skill wires, the engine measures) and **Curation** (present one candidate at a time with its
evidence; the verdict is the human's; the skill appends the row and the `ADR-RD-NNN`
skeleton). The doctrine section now states the quarantine rule and cites ADR-009. A
`BEHAVIOR-LEDGER.md` template ships in `templates/`.

## What the fresh review caught

Six findings, two HIGH, both reproduced before fixing:

- **A stray top-level `type:`/`confidence:` after the evidence block silently overrode the
  nested values** — last-value-wins with no duplicate detection — walking a candidate
  straight past the `inference ⇒ low` invariant. Scope and duplicates are now
  malformation: keys outside the evidence block and re-declarations are named errors.
- **Evidence refs escaped the repo tree**: an absolute path makes `os.path.join` discard
  `repo_path` entirely, and `../` walks out — either way the "evidence" pointed outside the
  legacy tree it claimed to evidence. Confinement is now part of resolution, reusing
  `_gc_rel` (which already realpaths both sides — the Windows 8.3 lesson, applied not
  re-learned).
- An all-empty ledger row was vacuously a "separator" and vanished silently — now
  malformation, per ADR-010's no-silent-degrade rule.
- The phase gate blocked on malformation with a generic message and was only tested via
  `curation-check`; it now NAMES the malformed candidates/ledger, and T120 asserts the
  block through `phase` itself.
- The no-git fixture gained `GIT_CEILING_DIRECTORIES` so an ancestor `.git` on some machine
  cannot flake it; BOM-saving editors no longer produce a false "no frontmatter"
  (`utf-8-sig`).

Slice 2 — declared oracle divergences in `golden-diff`, embedded spec-id, `roundtrip`
coverage — is next, as its own release.

`AC-RD-01..07` measured green. Suite: 405 checks. Acceptance: **49/49** where `coverage.py`
is installed.
