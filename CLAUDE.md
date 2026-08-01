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
8. **INV-GOLDEN-01 governs here too**: never write/rename a `.approved`
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
