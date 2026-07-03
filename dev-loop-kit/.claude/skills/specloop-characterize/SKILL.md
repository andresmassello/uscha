---
name: specloop-characterize
description: >
  Capture a golden / approval suite of a module's CURRENT behavior — the one artifact the
  agent must NOT author. Run the ORIGINAL code with real inputs through a deterministic
  harness, emit .received, and STOP for human approval; never create or edit a .approved
  file. Used before any migration/modernization to freeze pre-change behavior as field
  truth. Invoke for "characterize", "golden-capture", "capturá el comportamiento viejo".
allowed-tools: Read, Write, Glob, Grep, Bash
disable-model-invocation: false
---

# characterize — freeze the current behavior as field truth (the agent does not author it)

The golden suite is the ONE piece of the loop the agent cannot author, and that is exactly
its reason to exist. If you write the golden by reasoning about what the code "should"
return, you encode the same partial understanding that loses logic silently. **You capture
what the code DOES, mechanically, by running it — never what it should do.** You may write
the capture harness; you may NOT create, rename, or edit any `.approved` file.

## Inputs

- **Target module** + a **corpus source**: a path to input fixtures, or a reference to
  (anonymized) production data. The golden is only worth as much as the corpus (see below).

## Phase 1 — Capture harness (you write this)

Generate a deterministic harness that runs the ORIGINAL module over the corpus and
serializes ALL observable output. Same input → same `.received`, byte for byte.

## Phase 2 — Non-determinism checklist (emit + normalize BEFORE serializing)

Control every one of these, or the diff lies. Output the checklist applied:
- [ ] **Timestamps / dates** — frozen clock or stable placeholder.
- [ ] **Random / seeds** — fixed seed or mocked generator.
- [ ] **Map/set iteration order** — sort keys before serializing.
- [ ] **GUIDs / DB auto-increment** — normalized or excluded from the snapshot.
- [ ] **Concurrency** — thread order must not leak into the output.
- [ ] **Target locale** — decimal separator, date format, culture. **Mandatory and
  explicit.** A golden built on one machine and run on another with a different locale
  breaks entirely (Windows/SQL Server: high risk).
- [ ] **Deterministic serialization** — JSON with sorted keys, fixed float precision,
  explicit encoding. Identical byte-for-byte when behavior is identical.

## Phase 3 — Run the capture

Execute the harness → generate `.received` files.

**Declare volatile fields BEFORE approval (kit 1.15.0).** If the ORIGINAL code emits
values that vary between correct runs and cannot be made deterministic at the source
(timestamps, request ids, GUIDs from a layer you cannot touch), declare scrub rules in
`golden.scrub.json` at the fixtures root:

```json
{ "rules": [
    {"pattern": "\\d{4}-\\d{2}-\\d{2}T[0-9:.+Z-]+", "replace": "<TIMESTAMP>"},
    {"pattern": "requestId=[0-9a-f-]{36}", "replace": "requestId=<UUID>"} ] }
```

`golden-diff` masks BOTH sides with these rules before comparing (text only; binary
stays byte-for-byte) and reports every scrub-match separately (`N via scrub`) — masking
is never invisible. Prefer fixing determinism at the source (Phase 2 checklist); scrub
is for what you genuinely cannot control. The rules file is part of what the human
approves in Phase 4 — gate-check flags any later edit to it (a broadened rule can mask
real divergence).

## Phase 4 — STOP for human approval

Return control to the human to review and approve the `.approved` — and, if present,
`golden.scrub.json` (the scrub rules are contract, same as the goldens). **The skill
ends here.** It does NOT auto-complete approval, and it does NOT create any `.approved`
file.

## Corpus — where the inputs come from (critical)

The golden only protects the paths you exercise; what gets lost is usually a rare path.
Sources, in order of value:
1. **Real production samples** (anonymized if needed) — the true distribution, including
   cases nobody knew existed.
2. **Hand-built edge cases** — known limits (zeros, boundaries, error states, rare
   combinations of inputs).
3. **Inputs of past bugs** — every historical bug is a golden input.
A module whose corpus does not exercise its known branches is marked **PARTIAL**, never
covered.

## Guardrails (non-negotiable)

- The skill STOPS at the approval point (Phase 4); it never creates/renames/edits `.approved`.
- A `PreToolUse` hook on `**/*.approved.*` should make agent writes mechanically impossible
  (see `hooks/block-approved-writes.ps1` + the settings snippet in the kit).
- `.gitattributes`: `*.approved.* binary` — line endings must not create false diffs
  (Windows/SQL Server).

## Acceptance criteria

- The skill ends at Phase 4 with no `.approved` created or renamed.
- The harness is deterministic (same input → same `.received` byte for byte).
- The output includes the non-determinism checklist that was applied.

## Harness stack

- **Java** → ApprovalTests.Java (`com.approvaltests:approvaltests`, JUnit 5 / JDK 21);
  `JsonApprovals.verifyAsJson()` for structured responses, `WithTimeZone`-style helpers
  to freeze time/locale. For read-only migrations, the "old query vs new query against prod"
  pattern applies.
- **C++ / other** → a fixtures dir + a deterministic serializer + a diff runner (no
  comfortable native ApprovalTests; go custom).
- For system I/O, a fixtures dir + custom runner that normalizes and diffs is often better
  than relying on the library alone.

## Relationship to the other skills

- **reverse-discovery** orchestrates this skill as its Phase 2 (golden capture at the
  boundaries).
- The captured `.approved` is the arbiter that `qa_ledger.py golden-diff` byte-compares
  against during `/specloop-devloop`.

## Tracked-markdown / tracked-golden protocol

Never overwrite an existing approved golden. If a `.received` already exists, regenerate it;
if a `.approved` exists, it is the human's — leave it untouched and surface the diff.
