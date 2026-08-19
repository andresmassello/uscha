# uscha-kit 1.93.1 — evidence hashes are line-ending-insensitive: a clean checkout no longer reads its own green report as "altered" (2026-08-19)

1.93.0's first day on the release machine: the board read `unsealed (evidence altered after ingest:
reports/junit/uscha-acceptance.xml)` and `DONE 0/205`. The reviewer had named the limit (ADR-039,
NIT "CRLF"): the suite writes the JUnit with `\r\n` on Windows, the snapshot hashed those bytes, git
stores the file normalized to LF (`.gitattributes`), and a clean checkout hands back LF — a different
hash, a false "altered", rule (b) inert, the mtime rule stale. Fail-closed, and wrong about the world.

## What changed
- **`_sha256_evidence`**: evidence reports are hashed over their bytes with `\r\n` normalized to
  `\n`; new records carry `sha256_eol: "lf"`. Any byte change other than line endings still reads
  `evidence altered after ingest`. Compile-validate's manifest hashes (`_sha256_file`) are exact and
  untouched — a compiled unit is not a text report.
- **Backward compatible, honestly**: a 1.93.0 record (no marker) holds the exact hash of whichever
  rendering the run produced, so it is compared against the three renderings of the current file's
  text (normalized, exact, CRLF); a marker-bearing record is compared normalized only.
- The suite's acceptance writer now emits LF (`newline="\n"`) — the working copy equals git's normal
  form; belt to the engine's braces.
- Release ritual corrected once more (CLAUDE.md rule 9): the CHANGELOG's suite counts are committed
  in X+1 with the ledger; X is never amended after the record (an amend re-dates X and orphans the
  snapshot's commit — which is why a fresh clone of 1.93.0 still reads `stale seal`).

`AC-FR-11` measures it: CRLF-recorded → LF on disk and the mirror both read fresh and sealed; one
changed byte with line endings untouched reads altered. On the release machine's checkout 1.93.1
reads `SEALED … differs from snapshot by non-source files only` and `DONE 205/205` where 1.93.0 read
`UNSEALED … 0/205`.

Suite: 435 checks · 0 fail; acceptance 206/206.
