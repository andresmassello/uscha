# uscha-kit 1.51.3 — a leaner tarball and a public home (2026-07-24)

A publishing-surface release: what the npm package actually carries, and where every published
manifest points. No engine or installer behavior changes. Smoke suite: 389/389.

## The npm tarball drops 70 files of repo archive
`npm pack` was measured, not assumed: **127 files / 1218 KB unpacked**, of which **70 files
(55% of the package) were historical per-release changelogs** going back to 1.2.2. Nothing in
an install reads them — they are repo history, and the repo is where they belong. `files` now
excludes `uscha-kit/CHANGELOG-*.md`: **−70 files, −172 KB**, with the payload untouched.

What was already correct and stays that way: the repo's `docs/` (paper, decks, onepagers,
PNGs), `tests/`, and every `__pycache__`/`.pyc` were never in the tarball.

What is NOT trimmed, deliberately: `qa_ledger.py`, the mirador template and every `SKILL.md`
ship **twice** (~51% of the weight), because the Claude plugin manifest reads `./.claude/skills/`
and the Codex one reads `./skills/`. That duplication is a contract between two manifests that
both travel inside the package, not fat.

Regression: smoke **T67**, extended — no `CHANGELOG-` file may ship, plus **positive controls**
(`SKILL.md` for both skill trees, `templates/CONSTITUTION.md`, `uscha-kit/README.md` must still
be present) so a future trim cannot quietly gut the actual payload.

## The kit points at uscha.dev
The methodology now has a public home — **[uscha.dev](https://uscha.dev)** — with the paradigm,
the five rules, the skills and the library (essay, 2-day dev course, reference, paper). Until
now every published surface pointed only at the GitHub repo, which is the *source*, not the
*method*. Updated: `package.json` (this is the link npmjs.com renders), both plugin manifests,
the marketplace entry, both READMEs, and the post-install next-steps the installer prints.
GitHub remains `repository`/`bugs` — the conventional split.

Regression: smoke **T104** — the site link is asserted across all four published manifests and
both READMEs. The kit publishes on four surfaces that have drifted apart before (T57 mechanized
the same class of drift for skill counts), so this is measured rather than trusted.

## Note
The root README's changelog link is now an absolute GitHub URL: the per-release changelog no
longer travels in the tarball, so a relative link would dangle for anyone reading the unpacked
package.
