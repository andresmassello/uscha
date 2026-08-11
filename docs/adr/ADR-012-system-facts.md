---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/tests/smoke-engine.sh
---
# ADR-012: Published claims are compiled artifacts of derived facts (SYSTEM-FACTS)

## Status: Accepted

## Context
T0 of the Diamond program: the project's public claims must be compiled from repo facts, not
hand-maintained prose. The founding fixture happened live: the site claimed kit **1.65.0**
with **32** engine subcommands while the repo was at **1.67.0** with **35** — factual drift,
in the project about factual drift, caught by a human reading two numbers side by side
instead of by a mechanism.

Options considered:
- **A) Keep fixing numbers by hand at release time.** The status quo; it just failed.
- **B) Derive facts from the artifacts and gate the claims in CI.** **Chosen.**
- **C) Generate the docs from templates.** Rejected for now: heavier, and the claims live in
  many hand-authored surfaces (site, README, manifests) that are not template-born.

## Decision
`qa_ledger.py facts` derives `SYSTEM-FACTS.json` **from the artifacts themselves, never from
prose**: the subcommand list by introspecting the real `build_parser()`, the skill list from
the real kit tree, the version from `uscha-kit/VERSION`. No timestamp — regeneration over an
unchanged repo is byte-identical. What has no mechanical source yet (stack matrix, the
REAL/VISION registry) is **omitted and named as omitted**, never guessed.

`facts --check <files>` fails (exit 1) when any recognizable claim disagrees with a derived
fact, naming `file:line`, the claim and the fact — and when the committed facts file itself
is stale against a fresh derivation. Claim recognition is deterministic regex over a small
declared pattern set (kit-version, N-subcommands/subcomandos, N-skills); a claim the
patterns do not recognize is simply not checked — the gate under-reaches rather than guesses.

**Scope is the LIVE claim surfaces** (README ×2, site index + llms.txt, both plugin
manifests, the command-reference doc ×4 twins), wired as a blocking check in the smoke suite
— which is what runs in CI, so factual drift is a red build. **Historical changelogs are
archives and deliberately out of scope**: rewriting an archive to match today falsifies the
record instead of correcting it.

## Reasons
- A claim nobody compares against a derived fact WILL drift; this release's own founding
  fixture is the proof.
- Deriving from the artifact (the parser, the tree) instead of grepping prose means the fact
  cannot itself rot.

## Consequences
+ Version and count drift on the published surfaces becomes a named red, not a reader's
  sharp eye.
- Every release now regenerates `SYSTEM-FACTS.json` (one command; the suite reminds by
  going red if forgotten — the coherence gate AC-02 already plays this role for changelogs).
- The pattern set is deliberately narrow; unrecognized claim phrasings pass unchecked.
  Widening it is cheap and incremental; guessing is neither.

## Implementation Plan
- `qa_ledger.py` (`_derive_facts`, `cmd_facts`, `FACTS_FILE`); smoke T122 + the live check;
  `SYSTEM-FACTS.json` committed at the repo root.

## Verification
- [ ] two runs over an unchanged repo emit byte-identical facts (AC-SF-01)
- [ ] an injected wrong claim fails the check naming file:line, claim and fact (AC-SF-02)
- [ ] a stale committed facts file is itself named drift (AC-SF-03)
- [ ] correct claims + fresh facts exit 0 (AC-SF-04)
