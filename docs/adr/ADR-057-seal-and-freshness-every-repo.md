---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/.claude/skills/uscha-devloop/uscha_top.py
  - uscha-kit/skills/uscha-devloop/uscha_top.py
  - uscha-kit/.claude/skills/uscha-devloop/SKILL.md
  - uscha-kit/skills/uscha-devloop/SKILL.md
---
# ADR-057: The seal covers EVERY configured repo, and `phase` re-derives freshness at read time (amends ADR-038)

## Status: Accepted (read-time freshness in `phase` and `_converged` in 2.10.0; the every-repo seal in 2.11.0)

## Context

Two gate surfaces read less than they claim, reproduced on v2.9.0:

- **A-F9.** `_sealed_state` (qa_ledger.py:10970-11119) evaluates `repos[0]` only (:11007) — its
  docstring says so (:10994, "The repo is the FIRST configured one"), ADR-038's Decision says
  "the tracked repo's subtree" with no multi-repo caveat, and SKILL Phase 6 presents
  `check-terminado` as the seal before TERMINADO. A crash committed into repo #2 after its
  evidence printed `SEALED (repo api)`, exit 0.
- **A-F3.** `_derive_phase` (:4034-4036) and `_converged` (:3973-3977) read
  `snapshots[-1].tests.freshness.status` as stored. A source edit after the snapshot stays
  `pr-ready`, while `readiness` on the same ledger re-derives (`_ac_tags`, :997-1007) and says
  "STALE ... discarded". `README.md:141-142` claims stale evidence is "discarded, not honored".
  Single repo: `check-terminado` catches it. Multi-repo: nothing did (with A-F9).

ADR-038's own principle is that the seal is "derived, never written" because "a stored verdict
is a claim about a tree that has moved on since". `phase` did not apply it.

## Decision

1. **`phase` and `_converged` re-derive at read time** through ADR-055's `_evidence_live(ledger,
   repo)` — the one function `_ac_tags` also uses — instead of the stored `freshness.status`.
   The stored value stays in the snapshot as the record of what was true at ingest.
2. **The seal evaluates every configured repo** (the synthetic `integration` scope excluded),
   each with today's three questions plus ADR-055's attestation check, and aggregates:
   `ok = false` if any repo is false, else `null` if any is null, else `true`.
3. **Contract.** `top --json` `terminado.sealed` keeps `{ok, reasons, commit, repo, note}` as the
   AGGREGATE: `repo`/`commit`/`note` of the first repo whose verdict is not `true` (else of
   `repos[0]`), `reasons` prefixed `[name]`. A `repos[]` detail key (one `{repo, ok, reasons,
   commit, note}` per repo) is added **only when more than one repo is configured**, so
   single-repo output — and the golden frames over it (AC-CT-10, AC-T-24) — is byte-identical.
4. **`check-terminado`** prints one verdict line per repo, then the aggregate; exit codes 0/1/2
   are unchanged and follow the aggregate.
5. **Nested repo paths.** The dirty-check exemption is the union of every repo's named reports
   plus the ledger; an outer repo's seal also breaks on an inner repo's source change, honestly,
   and both are named.

## Alternatives

- **Keep `repos[0]` and document it.** Honest, and leaves A-F9 open where it bites hardest.
  Rejected.
- **A `--repo` flag on `check-terminado`.** Lets a caller pick the repo that passes. Rejected as
  the default; a per-repo line in the output gives the same detail without the choice.
- **Always emit `repos[]`.** Simpler code, but moves every single-repo golden frame and the
  `top --json` byte-identity pins for no information. Rejected.
- **Re-snapshot inside `phase`.** `phase` would write; every gate read stays read-only. Rejected.

## Consequences

+ A-F3 and A-F9 fail closed; `phase`, `readiness`, `top` and `check-terminado` give one answer.
- A multi-repo project where only repo #1 was ever snapshotted used to read SEALED; it now reads
  UNMEASURED (exit 2) naming the other repo. Named in the CHANGELOG.
- `phase` now runs git (status + diff + hash) per call; bounded by the snapshot's report set,
  the same cost `_ac_tags` already pays.
- `uscha top`'s header still renders `reasons[0]`; in multi-repo it now carries the repo prefix.

## Out of scope

The `stop-signal` contradiction (A-F11); widening `uscha top`'s mtime poll to the tracked
subtrees (ADR-038's stated limit stays).

## Acceptance (draft, not in ACCEPTANCE.md — rule 8)

- AC-GI-30 — the A-F9 reproduction: `check-terminado` exit 1, naming the second repo.
- AC-GI-31 — the A-F3 reproduction: `phase` exit 1 without a new snapshot; `readiness` agrees.
- AC-GI-32 — two sealed repos: exit 0, one line per repo, `repos[]` of two in `top --json`.
- AC-GI-33 — a never-snapshotted second repo: exit 2, named.
- AC-GI-34 — single-repo `terminado.sealed` byte-identical to 2.9.0; golden frames unmoved.
- AC-GI-35 — nested repo paths: exemption union, per-repo breaks named.
- AC-GI-36 — a docs-only commit still seals with ADR-039's note, per repo.
