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
   (note: `rg` needs `--hidden` to see `.claude/`). AC-03 automates this, reading the
   names to hunt for from **`.uscha-private-names`** at the repo root — UNTRACKED on
   purpose: hardcoding that list would publish, in a public repo and inside the npm
   tarball, exactly what the criterion exists to keep out. Without the file AC-03 is
   emitted as `<skipped/>` → **UNMEASURED**, never a silent pass. Keep the file on the
   machines that release; it is one name (or regex) per line.
5. **Changes to the engine carry a smoke test**: `bash uscha-kit/tests/smoke-engine.sh`
   must exit 0 BEFORE committing any change to `qa_ledger.py`. If the change
   adds behavior, its check is added to the suite in the same commit.
6. **Versioning**: bump `VERSION` + `uscha.config.json` + `CHANGELOG-X.Y.Z.md`
   + `uscha-kit/.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json`
   in the same commit. All five must match (smoke T44 verifies it).
7. **Conventional commits** (`feat:`, `fix:`, `docs:`…), small and atomic.
8. **INV-GOLDEN-01 governs here too**: never write/rename a `.approved`
   (the kit's hook applies to this repo like any other).

## Known gotchas

- The PNGs in `docs/` are regenerated from `docs/diagram-sources/*.html` with headless Edge
  (`--force-device-scale-factor=2`) + PIL autocrop (the render clips ~70px at the bottom if the
  window is too short).
- The HTML decks are paginated by JS (`querySelectorAll('.slide')`): inserting a
  `<section class="slide">` auto-integrates into the navigation; the `#NN` deep-links
  shift when slides are inserted.
- PowerShell 5.1 breaks with em-dashes/emoji in `.ps1` — the hook stays ASCII.

> The tool executes · the method governs · evidence decides · the human approves.
