# uscha-kit 1.44.1 — `uscha init` is per-file, not all-or-nothing (2026-07-21)

Found by dogfooding: running `uscha init` on the kit's own repository. Smoke suite: 367/367.

## Fix

### `init` was unusable on any repo that already had a `CLAUDE.md`
`cmd_init` copies four files (`uscha.config.json`, `CLAUDE.md`, `CONSTITUTION.md`,
`.gitattributes`). It was **all-or-nothing**: if any target already existed and differed from
the template, the whole init aborted and wrote **nothing**. But `CLAUDE.md` differs in every
repo that already uses Claude Code — i.e. exactly the repos adopting uscha — so init reliably
did nothing, and the only escape was `--force`, which would **overwrite the user's own
`CLAUDE.md`**. The first command of the self-application run hit this immediately.

Fix: `init` is now per-file. The non-conflicting files are written regardless; each conflict is
reported and left **untouched** (resolve by hand, or re-run with `--force` to replace it
deliberately). Status is `partial` when some files were written and conflicts remain, and the
exit code stays **1** while any conflict is pending, so the partial state is visible and
scriptable. A clean repo still initializes fully and exits 0 — backward compatible. The JSON
output gains a `wrote` list of the paths actually written. `install-uscha.py:cmd_init`.
Regression: smoke **T85**.

## Note
This is the first fix that came out of `uscha` measuring itself (the repo now carries its own
`uscha.config.json`, `ACCEPTANCE.md`, and versioned `QA-LEDGER.json`). More of the same retro's
findings — chiefly the inert `risk_profile` — are still queued.
