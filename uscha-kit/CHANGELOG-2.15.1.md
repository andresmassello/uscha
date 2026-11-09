# uscha-kit 2.15.1 — `doctor` says why a target is WARN; the `origin: agent` scanner reads a code span that wraps a line

Two small instrument fixes, both found while dogfooding 2.15.0. No new subcommand, no schema change.

## What changed

- **`install-uscha.py doctor` (text output) names the reason a target is WARN.** Before, a failing
  target printed `WARN claude` and nothing else; the reason was only in `--json`. Now the line carries
  it, built only from what `target_status()` already collected:
  - no readable marker and no kit skill on disk: `WARN cursor -- not installed`;
  - a marker that is unreadable or names another target, or a current-version marker the checks reject:
    `WARN claude -- install marker unreadable or mismatched` (AC-IX-15), then any missing pieces;
  - a marker naming another version: `WARN claude -- installed 2.12.0 < kit 2.15.1`;
  - a current install with a piece missing: `WARN codex -- missing: hook_registered, marketplace_registered`
    (a missing skill reads `skill uscha-status`; the order is the order the checks run in).
  `OK` lines, the `--json` object (no new key) and every exit code are unchanged (AC-IX-11..15).
- **The `origin: agent` scanner no longer counts a marker inside an inline code span that wraps onto
  the next line.** The scan removed code spans one line at a time, so a span opened on one line and
  closed on the next left its second line to be read as a decision. ADR-058 documents a record shape
  that way, and `spec-check` reported it as "1 agent-origin item unconfirmed". A span may now cross a line break inside its paragraph, as CommonMark allows. It never
  crosses a blank line, a fence line (an unclosed bare fence opener included), a heading, a thematic break
  (`---`, `***`, `___`), a table row or a new list item. A real unbackticked marker is still counted, on
  its own line (AC-OA-08..12). ADR-058 is untouched; on this repo `spec-check` now reports 0
  unconfirmed.

## Behavior changes on upgrade (read before upgrading)

- `doctor` text lines for a WARN target are longer. Anything that parses the text (rather than
  `--json`) and matches `WARN <target>` as the whole line must now match the prefix.
- A project that had quoted a marker inside a multi-line code span and was told to confirm it no
  longer sees it listed.

## Honest limits

- The scanner follows CommonMark for backtick runs of length one only (the grammar the ADRs quote);
  a double-backtick span containing a single backtick is read as before.
- AC-OA-09 and AC-OA-10 guard the new reader against swallowing real claims; they also pass on the
  2.15.0 engine. AC-OA-11 and AC-OA-12 were first red against the first cut of the new reader (a review found it
  hid claims after an unclosed fence opener and after a heading or thematic break); only AC-OA-08, AC-IX-11, AC-IX-12, AC-IX-13 and AC-IX-15 were red against 2.15.0 behavior.

## Evidence

Suite: __SUITE__ checks · 0 fail; acceptance __ACC__.
