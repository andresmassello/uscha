# CLAUDE.md — SpecLoop (development of the method and the kit)

This repo is the **home of the Uscha project**: the source of the `uscha-kit` and its
documentation artifacts. THE METHOD is developed here — and the method applies to
itself.

## Repo rules

1. **The canonical source of the kit is `uscha-kit/`.** The zips in Downloads are builds;
   the docs in Downloads are snapshots. In case of conflict, this repo wins.
2. **Mandatory truth-pass**: no doc in `docs/` may claim anything that
   `uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py` does not do. If you change the engine,
   you update the docs in the SAME change (or you mark the claim as `proposal`).
   *Under-claim, then wire, then re-claim.*
3. **The twins travel together**: every ES doc has its -EN. An edit in one requires the
   equivalent edit in the other.
4. **Zero references to projects/clients**: the kit and the docs are generic
   (example repos: `backend-api`/`mobile-app`). Verify with grep before committing
   (note: `rg` needs `--hidden` to see `.claude/`). AC-03 automates this. The list ships as
   **SHA-256 hashes** in `.uscha-private-names.sha256` (COMMITTED — regenerate with
   `python uscha-kit/tests/private-names-hash.py`), so CI measures the criterion without
   publishing the names it exists to keep out. The plaintext **`.uscha-private-names`** stays
   UNTRACKED as the release machine's stricter superset: it can carry prefixes/regexes, which a
   hash cannot express. With neither list AC-03 emits `<skipped/>` → **UNMEASURED**, never a
   silent pass. Two lessons paid for in production (2026-07-26): the scan must cover **every
   tracked file**, not just `uscha-kit/` + README — that blind spot let names sit in `audits/`
   and `formats/` for weeks — and a gate whose list nobody can see is a gate nobody can verify
   is complete.
5. **Changes to the engine carry a smoke test**: `bash uscha-kit/tests/smoke-engine.sh`
   must exit 0 BEFORE committing any change to `qa_ledger.py`. If the change
   adds behavior, its check is added to the suite in the same commit.
6. **Versioning**: bump all **six** version surfaces + a `CHANGELOG-X.Y.Z.md` in the same
   commit: `VERSION`, `uscha.config.json`, `uscha-kit/.claude-plugin/plugin.json`,
   `uscha-kit/.codex-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `package.json`.
   All six must match (smoke T44 verifies it).
7. **Conventional commits** (`feat:`, `fix:`, `docs:`…), small and atomic.
8. **Multi-ADR features get a `docs/<feature>/`** (curated 2026-08-17 with `uscha top`): the
   narrative SPEC + FIXTURES live there while the ADRs are `Proposed`; the ACs are promoted into
   `ACCEPTANCE.md` on acceptance. Single-ADR changes keep the plain `docs/adr/` + `ACCEPTANCE.md` path.
9. **Dogfooding is measured, not narrated** (curated 2026-08-17): the root `QA-LEDGER.json` is this
   repo's own truth. Every kit release runs the ritual on itself -- smoke (writes
   `reports/junit/uscha-acceptance.xml`) -> `qa_ledger.py snapshot --repo uscha` -> `readiness --record`
   -> ledger committed in its OWN commit right after the code commit (since 1.93.0 / ADR-039: the
   snapshot's commit must exist and the difference must be non-source only; order = code commit X ->
   `readiness --record` (dates the ledger after X, so AC-DF-01 is green while the suite runs) -> suite ->
   `snapshot` + `readiness --record` -> ledger + JUnit + the CHANGELOG's suite counts committed as X+1;
   NEVER amend X after the record: an amend re-dates X and orphans the snapshot's commit).
   The release **tag** is pushed only once the `smoke` run for that exact SHA is green: `publish.yml`
   polls for it and refuses to publish over a red or unfinished run, but the ritual must not lean on
   that -- a tag on an unmeasured SHA turns a release into a wait. And the smoke suite checks that
   `readiness_history[-1].at` is not older than the last commit that touched the engine (a stale
   ledger is a FAIL, not a note). At session start the `uscha-status` skill is shown first, from the
   ledger. The honest gap that made measured acceptance read 6/172 in 1.86.0 was the INSTRUMENT, not
   the evidence: `_AC_TAG`/`_AC_ID` could not see the family-prefixed criteria. **Widened in 1.87.0
   (ADR-036)** -- measured acceptance now reads `171/178` (the 7 unmeasured are the M2/M3 `uscha top` ids,
   skipped on purpose) -- and it shipped as its own release,
   never as a hand-edit of the ledger. That stays the rule: when the number is ugly, fix the
   instrument or leave the number ugly.
10. **INV-GOLDEN-01 governs here too**: never write/rename a `.approved`
   (the kit's hook applies to this repo like any other).

## Known gotchas

- **The smoke suite must parse under bash 3.2** — the one macOS still ships (2007, GPLv3).
  Inside a `VAR=$(... <<'PY' ... PY )` block, a **literal `'` or `"` in a Python character
  class** (e.g. `['"]`) makes bash 3.2 hunt for a matching quote to the end of the file and die
  with `unexpected EOF while looking for matching`. Bash 4/5 (Linux, git-bash) parse it fine, so
  it is invisible locally — only the macOS CI cell catches it. Write the quotes as `\x27` /
  `\x22`. Same family: **no backticks in comments inside those heredocs** — the shell runs them
  as command substitution and silently truncates the code. Also same family, paid for on
  2026-08-01: **a literal `${` inside those heredocs** (e.g. matching the GitHub Actions
  `${{ secrets.` syntax) makes bash 3.2 open a parameter expansion while hunting for the closing
  paren, lose track of where the heredoc ends, and parse the following Python line as a shell
  command — `syntax error near unexpected token '('`, reported on a line that is not the cause.
  Build it as `chr(36) + "{..."`. Note what is NOT the trap: a bare `$"` is fine (a `$` regex
  anchor before a closing quote has shipped green for many releases) — the opener `${` is.
  General rule for these heredocs: the shell must never see `${` or a backtick, and a bracket
  expression must never contain a quote. A text scanner for this is NOT worth writing — the
  obvious one flags every `d["key"]` subscript in the suite (211 false positives when tried);
  the macOS cell is the measurement.

- **Windows 8.3 short paths break path comparison in CI, not locally** (paid for on
  2026-08-02). A temp dir under a username longer than 8 chars is reported in short form
  (`RUNNER~1`) by one API and long form by another; `os.path.relpath` between the two yields
  `..\..` and a file INSIDE the tree is judged outside it. The GitHub runner user is
  `runneradmin` (mangles); a typical local user like `Usuario` does not — so the Windows CI
  cells went red while local Windows stayed green, the mirror image of the bash 3.2 trap.
  **Always `os.path.realpath` BOTH sides before comparing paths.** Same lesson, different
  platform: the matrix cell is the instrument, not the dev box.

- The PNGs in `docs/` are regenerated from `docs/diagram-sources/*.html` with headless Edge
  (`--force-device-scale-factor=2`) + PIL autocrop (the render clips ~70px at the bottom if the
  window is too short).
- The HTML decks are paginated by JS (`querySelectorAll('.slide')`): inserting a
  `<section class="slide">` auto-integrates into the navigation; the `#NN` deep-links
  shift when slides are inserted.
- PowerShell 5.1 breaks with em-dashes/emoji in `.ps1` — the shipped `.ps1` (`mirador-watch`)
  stays ASCII. The INV-GOLDEN hook is now the portable `.py`; the `.ps1` was removed in 1.50.2
  (PowerShell is absent on macOS/Linux), and the plugin `hooks.json` invokes the `.py` directly.

> The tool executes · the method governs · evidence decides · the human approves.
