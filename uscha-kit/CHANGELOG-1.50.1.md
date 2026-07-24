# uscha-kit 1.50.1 — the privacy fix reaches the package (2026-07-23)

A packaging and documentation release: 1.50.0 shipped a tarball that still carried what
1.50.0's own repo had already stopped carrying. Smoke suite: 381/381.

## What the published package was still doing
The AC-03 leak detector — the criterion that forbids naming client or private projects
anywhere in the kit — had those names **hardcoded as its own regex**. The guard published
the very list it exists to keep out, in a public repo and inside the npm tarball. That was
fixed in the repo, but a fix that never reaches the distributed artifact is not a fix.

- The names now live in **`.uscha-private-names`** at the repo root: untracked, one name or
  regex per line. Without it AC-03 emits `<skipped/>` → the criterion reads **UNMEASURED**,
  never a silent pass. Absence is not success, applied to the guard itself.
- **`uscha-kit/tests/`** is excluded from the npm package. The suite is the kit's own
  regression harness; a consumer never runs it, and it was more than half the download.
  Tarball: 449.6 kB → 388.9 kB (123 → 121 files).

## A README written for whoever lands on it
The published README was the repo's development map: it opened with the directory tree and
buried the install command eighty lines down. Rewritten user-first — what the method is,
the install line above the fold, the nine skills, the loop, and what makes it different —
with the repo-development detail moved to the end. The same file serves GitHub and npm; the
registry only captures it at publish time, which is why this release exists.

Every number in it was verified against the engine rather than recalled: nine skills, 29
subcommands, eleven language stacks, the readiness weights.

## Published docs: a truth-pass to 1.50.0
The decks were frozen around 1.27.0 and had drifted from stale into **false**:

- All four team-pitch decks instructed `cp uscha-kit/uscha-devloop.config.json` — a filename
  that has never existed. The same typo was corrected in the READMEs by 1.31.0 and never
  reached the decks. The whole obsolete block (manual skill copying, a superseded doctor
  script) is now the three-command npx flow.
- The one-pagers offered a `uscha-kit-1.21.0.zip`: wrong version, and a distribution
  mechanism replaced by npm/npx at 1.39.0–1.40.0. No published doc mentioned npx at all.
- The long deck stated three different skill counts in one file (seven in prose, eight in
  chips, eight in a table); none was nine. Counts corrected and `/uscha-status` added to the
  visible roster.
- The skills reference carried a `spec-loop · skills` wordmark — pre-1.29.0 branding, and
  also the name of an unrelated third-party project this repo explicitly cites as distinct.
- The paper (both the arXiv `.tex` and its parallel HTML source): seven → nine skills, with
  `mirador` and `status` added to the skills table; 24 → 29 subcommands; nine → eleven
  language stacks; nine → thirteen linter formats; 161 → 381 checks; five → six release
  artifacts; the self-application arc extended from 1.27 to 1.50.

## Known gap
`docs/paper/uscha-paper.pdf` is now older than the sources it was rendered from, and the
repository documents no command to regenerate it. The `.tex` is the canonical arXiv source
and the `.html` is a parallel hand-authored render source; nothing enforces that the three
agree. Recorded here rather than papered over.
