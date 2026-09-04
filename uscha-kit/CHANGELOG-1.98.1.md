# uscha-kit 1.98.1 — a fixture that measured the clock instead of the amend, and a go-live the field declared but `readiness` could not see (2026-09-03)

## Why 1.98.1 exists

`v1.98.0` was tagged and its GitHub release was created, and then `publish.yml` REFUSED to
publish it: the 6-cell smoke run the tag triggers went red on `macos-latest` / py3.8, on the one
case described below. The 3-cell run of the same commit on the branch push had been green. The
gate did exactly what it is built to do — it fails closed on a red measurement rather than
publishing over it — so 1.98.0 never reached npm, and the published version stays 1.97.0 until
1.98.1. Nothing about 1.98.0's content was in doubt; 1.98.1 carries it unchanged plus the two
fixes below.

## The fixture measured the clock, not the amend (`AC-RL-04`)

This is the case that turned the tag red. `AC-RL-04` drives `tools/release.py` over a temp
fixture repo, amends the code commit X after the evidence was recorded, and asserts that the
script refuses naming **I5**. `release.py` compares the pair `head_identity()` records — X's sha
and its committer date — against HEAD, so an amend is caught by either half moving.

The fixture amended with a bare `git commit --amend --no-edit`. That reuses the tree, the
message, the author and the AUTHOR date, and takes the committer date from now — so run inside
the same second that created X, it produces a **byte-identical commit object**. Git is
content-addressed: an identical object has an identical sha. X's identity had not moved, there
was nothing for I5 to detect, `release.py` correctly proceeded, and the assertion that it would
refuse failed. Reproduced here by pinning the amend's committer date to X's own:

    [probe] X before=05836ee4 after=05836ee4 same=True
    BAD AC-RL-04 | AC-RL-04: amend 05836ee4->05836ee4 rc=0 out='...done. State in
    .uscha-release-state.json -- delete it once the release is out.'

which is the CI line verbatim. So the case was never measuring the engine; it was measuring
whether the runner happened to cross a second boundary between two git commands. ubuntu and
windows crossed it; the faster macos/py3.8 cell did not. A fixture with a race in it is worse
than no fixture: it reads as evidence about the engine and is evidence about the machine.

The amend is now a real amend whatever the clock says — the author date is pinned to a fixed
instant, so the amended object differs every time — and the sha move is **asserted** before the
script is invoked. A fixture that failed to amend now reports ITSELF (`why` names the pair,
`amend <before>-><after>`) instead of blaming the engine. `tests/smoke-engine.sh`, T151; the
criterion in `ACCEPTANCE.md` gained the precondition clause.

`release.py`'s I5 check is unchanged, and deliberately. A sha covers every field of a commit
object, so the only thing it cannot distinguish is a byte-identical re-commit — which is not an
amend, it is the same commit. And in real use the ritual runs the whole suite between X and the
record, which takes minutes: a same-second amend cannot happen there. The blind spot was the
fixture's, not the invariant's.

## `readiness` could not see a go-live that `spec-check` could (`AC-LC-06`..`AC-LC-08`)

Reported by a field run, and confirmed. A SPEC declared its go-live in the frontmatter,
`spec-check --spec SPEC.md` measured the lifecycle dimension, and `readiness` over the same SPEC
printed `lifecycle: UNMEASURED - no go-live declared`. Two surfaces, one derivation
(`_lifecycle_report`), and they disagreed — which `AC-LC-01` exists to make impossible.

The cause was one line. `spec-check` is handed the SPEC text; `readiness` reads `SPEC.md`
itself, through `_lifecycle_for`, which appended it as `(spec_text or "") + "\n" + fh.read()`.
With no text supplied that prepends a newline, so the file's opening `---` was no longer line 0,
and `_lc_frontmatter` — which requires the fence at the top — returned `None`. The frontmatter
was invisible to the surface that read the file, and only to that surface. The join was the
cause, and the fix is that it now happens only when there is something to join to;
`_lc_frontmatter` additionally skips leading blank lines and a BOM before looking for the fence,
which closes the separate case of a SPEC saved with a byte-order mark.

The same report said the inline form was not accepted either. Measured, the trailing text was
never the problem — `**Go-live:** 2026-09-06 (entrega 1). ...` at the start of a line already
parsed, and the regex's closing `\b` already allows prose after the date while keeping the date a
whole token. What did not parse was the line written as a LIST ITEM, `- **Go-live:** ...`, or
behind a blockquote marker, because the pattern anchored the bold label to the start of the line.
The body pattern now tolerates a list marker or a `>` in front. The whole-token rule is
unchanged and now pinned: `2026-12-011` is not a go-live with a stray digit, it is not a go-live.

Tolerating a prefix is where a permissive pattern starts reading examples as declarations, so
the prefix is markdown-CORRECT rather than merely loose: at most three leading spaces and never
a tab, a list marker only when whitespace follows it, and the body scan skips fenced blocks the
way `_spec_check_text` already did. A SPEC that quotes the template — inside a fence, or in a
four-space-indented block — is showing the form, not declaring a date, and the quoted line comes
FIRST, so a scan that read it would let an example beat the real declaration below it.

`AC-LC-06` compares the `lifecycle` line `readiness` prints against the one `spec-check` prints
for the SAME SPEC — the two surfaces against each other, not against a literal, so a reworded
line cannot make it pass for the wrong reason. `AC-LC-07` pins every prefix the pattern claims —
`-`, `*`, `1.`, `>`, `> -`, three spaces — plus the trailing-prose and whole-token rules, so the
accepted set is measured rather than narrated in a comment. `AC-LC-08` pins where the pattern
must NOT fire: a fenced example — under either fence marker — followed by the real line, where
the real date wins; a four-space- or tab-indented line, which is a code block; and the glued
`-**Go-live:**`, which is not a list item. All three are in T148, through the `.lc-cases.json`
sidecar, and all three are red against the 1.98.0 engine (`BAD AC-LC-06,AC-LC-07,AC-LC-08`) and
green against this one. The engine is mirrored byte-identical into
`uscha-kit/skills/uscha-devloop/qa_ledger.py`. The templates that document the two forms needed
no edit: they already claimed both work, and now both do.

The same field run proposed five further changes (P2–P6). They are not in this patch; each
follows as its own ADR, judged on its own evidence.

## Ritual: one full suite, one CI wait

A patch cost about two and a half hours of wall clock: the suite ran three times (the writer,
the writer again after review fixes, and `release.py` at X) and CI was waited for twice in
series (the branch push's three cells before the tag, then the tag's six cells before publish).
Two rules from 1.98.1 on. Writers run only the blocks they touch; the one full run is
`release.py` step 4, on the exact bytes that ship. And the tag is created right after the push:
`publish.yml` already waits for the tag's own six-cell run and refuses on red, which 1.98.0
proved, so waiting for the branch run first measured nothing twice. `--wait-ci` keeps the old
poll as an opt-in; `--no-wait-ci` is accepted and is now the default. CLAUDE.md rule 9 (I8),
ADR-041 and CROSS-PLATFORM.md say the same thing.

Acceptance goes 242 → 245 criteria; nothing was dropped.

Suite: 444 checks · 0 fail; acceptance 244/245.
