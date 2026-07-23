# uscha-kit 1.48.0 — uscha-status: the statusline on demand, in chat (2026-07-23)

Ninth skill. The statusline (1.46.0) is passive and terminal-bound — some surfaces
(Claude Desktop, Codex, plain terminals, CI logs) may never show it. `uscha-status` is the
same truth, printed in chat when the human asks. Smoke suite: 377/377.

## Three zoom levels, each datum shown once
- **Push** — one readiness verdict line at every pass close (the devloop already does this;
  1.25.0 single-verdict + 1.47.0 `--record`).
- **Pull** — `/uscha-status`: one compact block on demand (this release).
- **Bird's-eye** — the mirador, when the human wants everything.

Explicitly rejected: having every command print status blocks as it goes. The push line
already exists; repeating the same truth several times per pass is ceremony.

## What the skill does
Renders ONE fenced block (max ~8 lines): label · derived phase `×loops` · measured
acceptance bar · tests · coverage · `next →` criterion · per-repo loop odometer (multi-repo
only, with `plateau ⚠`) · roadmap · `recorded` timestamp + score/band. Sources, in order:
run `uscha_progress.py` if installed (fast, never runs tests) and read
`.claude/uscha-progress.json`; else read `QA-LEDGER.json` `measured` directly; no config →
not a uscha project, say so.

Read-only by contract: it never runs `readiness`, tests or gates. No `measured` recorded →
it says so and points at the feed (`readiness --record`, automatic at pass close since
1.47.0); a checkbox-only count is shown labeled **narrated**, never passed off as measured.

## Registration
Installer `SKILLS` roster, doctor `USCHA_SKILLS` (T57 no-drift guard forced it), both
plugin manifests, marketplace, READMEs (eight → nine), and the project template
`CLAUDE.md` command list.

Regression: smoke **T92** — `install-uscha.py` SKILLS must match the skill dirs on disk
(same no-drift spirit as T57, for the installer), and `uscha-status/SKILL.md` carries a
valid frontmatter and its read-only contract.
