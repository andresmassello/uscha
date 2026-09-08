---
governs:
  - tools/skill-blocks/orientation-block.md
  - tools/skill-blocks/orientation-block-short.md
  - tools/gen-skill-blocks.py
  - tools/release.py
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/.claude/skills/uscha-status/SKILL.md
  - uscha-kit/skills/uscha-status/SKILL.md
---
# ADR-045: The generated orientation block carries the kit version, and the release script re-renders it — so an installed skill can be DATED

## Status: Proposed

## Context

A field report: skills sat under `~/.claude/skills/uscha-*` from kit **1.54.0** while the kit in
the repo was at **1.97.0**. A whole discovery ran on prose three months stale, and nothing said a
word — not the skill, not the engine, not the operator, who had no way to notice.

The reason is small and complete: **a `SKILL.md` carried no version.** The kit's version lived in
six surfaces (`VERSION`, two plugin manifests, the marketplace, `uscha.config.json`,
`package.json`), and none of them travels with an installed skill. `install-uscha.py` copies the
nine skill directories verbatim; whatever `SKILL.md` says is what the agent reads, forever, until
someone re-installs. There was no fact to compare, and therefore no comparison to make.

This is the same shape as the drift ADR-012 exists for, one layer out: a published claim (the
prose an agent is executing) with no derived fact behind it. The difference is that ADR-012's
claims live in this repo, where a gate can reach them, and these live on a user's machine.

Two things had to become true at once. The version has to BE in the file — and the file is a
generated region already (repo rule 11, 1.97.0: 18 runtime `SKILL.md` files rendered from one
source in `tools/skill-blocks/`), so there is a place to put it that is not 18 hand edits. And it
has to STAY correct across a bump — a marker that is re-rendered when someone remembers is a
marker that lies about which kit an install is running, which is worse than no marker at all.

## Decision

**1. The generated block opens with the kit version.** Both templates under `tools/skill-blocks/`
begin with

```
<!-- uscha kit: {{version}} -- generated region: ... -->
```

and `tools/gen-skill-blocks.py` renders `{{version}}` from `uscha-kit/VERSION` — the same file the
six surfaces move. An HTML comment on purpose: it is inside the region the generator owns, it is
text the agent reading the file can see, and it changes nothing about how the block reads.

A missing or empty `VERSION` is a `ConfigError` (exit 2), never a default. A block stamped with a
guessed version would be worse than one with no stamp: `doctor` would then compare an installed
skill against a number nobody wrote.

**2. `tools/release.py` re-renders the blocks in step 2**, immediately after the six surfaces move
and before the facts gate, and refuses (I3) if the generator is missing. The six surfaces are no
longer the only place the version lives; 18 runtime files follow them, and they follow them in the
same commit X. `gen-skill-blocks.py --check` (smoke T152) is red whenever `VERSION` has moved and
the regions have not, so the wiring is not a convention — the suite fails without it.

**3. `doctor` compares, and only reports.** It reads the marker out of every installed `SKILL.md`
under the roots `install-uscha.py` writes to (Claude `~/.claude/skills`, Codex
`~/plugins/uscha/skills`, pi `~/.agents/skills`, and the other Agent-Skills roots), or under the
roots the caller names with `--installed DIR` (repeatable). It emits one line per root and a
`skills_installed` array in `--json`, each row carrying **both** versions:

- `current` — the install matches the kit;
- `outdated` — the oldest installed marker is below the kit's version, or the blocks carry **no**
  marker at all (every install that predates 2.2.0), in which case `installed` is `null` and the
  skills are named in `unmarked` rather than given a version nobody wrote;
- `not installed` — the root holds no uscha skill. Not a fault: the kit installs one agent at a
  time, and six absent roots are the normal shape of a healthy machine.

**Advisory, always.** An outdated install is a `warn`, never an `error`; `doctor`'s exit code is
unchanged, and it exits 0 whether the install is current or three months old. Someone may be
pinning a version on purpose, and a diagnostic that fails a deliberate choice is a diagnostic
people turn off.

**4. The `uscha-status` skill prints the finding before its breadcrumb.** One line, above
everything else, when any root reads `outdated`:

```
SKILLS OUTDATED: installed 1.54.0 < kit 2.2.0 -- run `python install-uscha.py install --target claude`
```

Then it renders the readout exactly as it would have. The line never blocks, never changes a
number, and says nothing at all about roots that are simply not installed.

**No new subcommand.** `doctor` already answers "is this installation healthy?", the subcommand
count is a published fact gated by `facts --check`, and a `skills-check` command would have added
a surface to every doc that lists them in order to ask a question `doctor` was already the place
for.

## Consequences

- An installed skill is now **dateable**, on any surface, by anyone with a kit checkout.
- The version lives in 24 files rather than 6, but 18 of them are generated from one template and
  measured by `--check`; the hand-maintained count is unchanged.
- A skill installed **before** 2.2.0 carries no marker and does not carry these instructions
  either, so on that surface the warning cannot come from the skill itself. `doctor` is the
  instrument that still works there — it runs from outside and reads the installs. This is a
  stated limit, not a gap that closes itself.
- `doctor` now reads paths under the user's home. Read-only, wrapped, and an unreadable file is
  treated as unmarked rather than raising.

## What this ADR does NOT decide

- It does not make an outdated install **gate** anything, in `doctor` or anywhere else.
- It does not auto-update, auto-install, or prompt to install. The installer stays a command a
  human runs.
- It does not version the skill prose independently of the kit: the marker says which KIT the file
  came from, not that this particular skill changed in that release.
- It does not compare anything but the nine `uscha-*` skills, and it makes no claim about skills
  installed by other means.

## What is measured (`AC-SK-01..07`)

T162, through the `.sk-cases.json` sidecar:

- **AC-SK-01** — all 18 rendered regions carry `uscha kit: X.Y.Z` equal to `uscha-kit/VERSION`, and
  both templates carry the `{{version}}` placeholder (the stamp is rendered, not typed 18 times).
- **AC-SK-02** — bumping only `VERSION` in a throwaway copy makes `--check` exit 1 naming the
  drifted regions and writing nothing; the plain run re-stamps all 18 and `--check` is green again.
- **AC-SK-03** — `doctor` reports `outdated` with both versions for a planted 1.54.0 root and
  `current` for a fresh one, **exit 0 in both**, with the fix command in the detail.
- **AC-SK-04** — an absent or empty install root is `not installed`, `installed: null`, exit 0, no
  traceback, and the verdict is not ERROR.
- **AC-SK-05** — a block with no marker at all reads `outdated` with `installed: null` and the
  skills named in `unmarked`.
- **AC-SK-06** — the RED PROBE: the `v2.1.0` engine rejects `--installed` at the parser and its
  `doctor --json` has no `skills_installed` key. `None` = UNMEASURED without git.
- **AC-SK-07** — a REAL install: `install-uscha.py install --target claude --home <tmp>` and then
  the INSTALLED engine's `doctor --json`, which must report `kit_version` and `current`. Removing
  every source inside the install tree — the copied version file and `uscha-install.json` — must
  put the same engine back to `null` / `unknown` with the directories it read named in the fix
  line. Amended in the same release: the planted fixtures above all passed while a real install
  reported UNMEASURED, because nothing put `uscha-kit/VERSION` where an installed engine could
  reach it (found by running the first-use guide end to end).
- **AC-SK-08** — the copy is written as **`.uscha-kit-VERSION`**, not as the bare `VERSION`: a
  pre-existing foreign `~/.claude/skills/VERSION` survives install AND uninstall byte-identically.
  The installer owns the files it creates and nothing else, and the only way to guarantee that in
  a directory the kit does not own is to claim a name nobody else would pick.
- **AC-SK-09** — a `--mode link` install resolves the kit it points INTO: with the copy and the
  install marker removed, the installed engine still answers with the kit checkout's version,
  because the walk-up starts at the engine's REALPATH. An abspath walk climbs the agent's tree and
  can only ever find what the installer put there.

The release wiring is measured where a real release runs: **AC-RL-03** (T151) asserts that commit X
carries the re-rendered `SKILL.md` pair alongside the six surfaces, stamped with the new version.

## Alternatives considered

**A version file beside the skills (`~/.claude/skills/.uscha-version`).** Rejected: the installer
already writes an install marker, and an install marker answers "when did I install?", not "which
kit is this FILE from?". A file copied out of one install into another — which is how skills
actually travel — carries its own block and none of the sidecars.

**A `skills-check` subcommand.** Rejected: the subcommand count is a published fact appearing in
the README, the site, the docs and the paper, and every one of those surfaces would have had to
move for a question `doctor` already exists to answer.

**Frontmatter (`kit: X.Y.Z` in the YAML header).** Rejected for now: the frontmatter is the agent
harness's contract (`name`, `description`, `allowed-tools`), and adding a key to it risks a
harness rejecting the file. The generated region is ours.

**Making an outdated install a gate.** Rejected on the kit's own doctrine: a diagnostic that fails
a deliberate pin is a diagnostic people stop running, and this measurement is worth more running
than winning.
