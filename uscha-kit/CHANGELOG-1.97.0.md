# uscha-kit 1.97.0 — the docs stop being hand-copied: one source for the skill block, a writer for the published claims, and a CI grid that measures what only it can (2026-09-02)

No engine behaviour changes for a consumer project. Everything here removes work that had no
judgement in it — the kind a maintainer performs between two fourteen-minute suite runs, once per
release, and gets wrong eventually. Three pieces of that work, named and measured:

- **15 claims per release** (measured on this 1.96.0 → 1.97.0 bump), rewritten by hand across
  13 published files, because `facts --check` could compare a claim but never fix one;
- **7-way manual synchronisation** of the orientation block across nine `SKILL.md` files in two
  skill trees (18 files), kept in step by copy-paste;
- **3 CI cells per push** that were re-measuring what the other three already said.

Plus one honest gap the paper review found: the paper's canonical `.tex` — the source the `.html`
and the `.pdf` are built from — was outside the factual-drift gate entirely.

## What changed

### `facts --write`: the claims gate learned to close itself

ADR-012 made published claims **comparable** against facts derived from the artifacts. It never
made them **writable**. So the shape of a release was: bump six surfaces, regenerate
`SYSTEM-FACTS.json`, run `facts --check`, read the list of drifted claims, and edit them by hand —
about twenty-five of them, spread over README twins, six site pages, the two `llms.txt`-class
files and the docs. `tools/release.py` shipped in 1.96.0 with a line in its own docstring saying
so: *it does not edit a published claim (`facts --write` is 1.97.0)*.

It is 1.97.0.

`facts --write <files>` rewrites every **recognised** claim to the derived fact and then runs the
same `--check` over the same files. Three properties are what make it safe to point at the repo's
own published surface:

1. **One recogniser, two consumers.** `_iter_claims` yields `(fact key, start, end, token)` for a
   line, and `--check` reports exactly what it yields while `--write` rewrites exactly what it
   yields. A writer that re-implemented the patterns could disagree with the checker, and the
   disagreement would surface as a release that refuses after fixing itself.
2. **The check still gates.** `--write` implies a final `--check` and exits non-zero if anything
   still disagrees. The writer only touches what it recognises: a missing row in a subcommand
   table, a count phrased in prose, a claim the patterns do not cover — those survive it and are
   still a refusal. A release that fixed what it could and shipped the rest would be exactly the
   self-graded evidence this repo refuses everywhere else. `release.py` step 2 now runs
   `facts --write` and *then* `facts --check`, and I3 is unchanged in what it demands.
3. **Byte-for-byte otherwise.** Line endings are preserved per file — the gated set mixes LF
   sources with CRLF-checked-out HTML — and a file with no recognised claim comes back
   byte-identical and unreported.
4. **A file it cannot read is a refusal, not a skip.** A gated file that is not valid UTF-8 is
   named, left untouched, and makes `--write` exit 2, which `release.py` turns into an I3
   refusal. `--check` reads that same file with `errors="replace"` and still reports its claims,
   so nothing is hidden — but the writer must not read it that way: writing a replaced byte back
   would destroy data to correct a version number. (`AC-FW-05`.)

`--check` and `--write` are also alternatives now rather than a pair: passing both used to
silently drop `--check`'s files, since `--write` set the check list to its own. It exits 2 and
says so, as does a `--write` with no files at all.

The recogniser also grew **spelled-out counts**, `one` through `ninety-nine`, and rewrites them in
the author's notation: "nine skills" becomes "ten skills", never "10 skills", and keeps its
leading capital. That is not a flourish. It is what let the gap below be closed at all.

### The paper's canonical `.tex` was outside the gate

`site/docs/paper/uscha-paper.html` was gated; `docs/paper/uscha-paper.tex` — the source it and the
PDF are built from — was not. And even had it been listed, the gate would have read it as green:
the paper's claim is *"A reference implementation (nine agent skills and a dependency-free Python
engine with 53 subcommands…)"*, and a digits-only recogniser sees the `53` and walks past the
`nine`. Half a sentence measured is not a measured sentence.

Both `.tex` files and the rendered `.html` are now in the list `site/sync-docs.sh` gates — the one
`tools/release.py` **parses** rather than copies — and the smoke suite's own T0-live list gained
the canonical `.tex` too.

### One gated list, because two lists were a hole and not just untidiness

There were **two** hand-maintained lists of gated files with different contents: the suite's
T0-live and the one in `site/sync-docs.sh`. The obvious complaint is duplication. The real one is
worse, and a fresh review found it: six of the paths only `sync-docs.sh` carried live under
`site/docs/`, which is **build output** — `sync-docs.sh` opens with `rm -rf site/docs` and
regenerates it from `docs/`. So a release would have rewritten a claim in
`site/docs/uscha-claude-code-doc.html` while its canonical twin `docs/uscha-claude-code-doc.html`
was only ever *checked*. The next deploy deletes the fix. A writer pointed at build output writes
into the sea.

`tools/facts-gated-files.txt` is now the one list, read by all three consumers — the deploy gate,
the suite's T0-live and the release — with two sections. `# canonical` is authored here and a
rewrite lands and stays; `# deployed` is regenerated from a canonical twin. **Both** are written,
so the tree is consistent between a release and the next deploy, and the twin is what makes it
stick. The sections are not decoration: `AC-FW-04` asserts that every `# deployed` path has its
canonical twin in the section above, that the written set is the checked set, and that every path
exists — all of it by importing `release.py`'s own parser rather than typing the list a fourth
time. The gate widened from 20/21 files to **27**, and it is now impossible to add a page to the
deploy's gate without adding it to the release's.

**Explicitly not done:** the paper's *other* numbers — its Diamond content — are untouched. Those
are the author's, not a derived fact, and a writer that reached them would be guessing.

### The orientation block has one source now

Seven of the nine skills carry a byte-identical "First contact" + "Orientation markers" block;
`mirador` and `status` carry a shorter two-marker variant. Two skill trees ship (`.claude/skills/`
for Claude Code, `skills/` for Codex), so that is **18 files** that had to move together, by hand,
whenever a line of the method's own vocabulary changed.

They must stay whole: an agent loads one `SKILL.md` and nothing else, so there is no include
mechanism to lean on. The duplication therefore stays on disk and its **source** moves upstream —
the same shape `SYSTEM-FACTS` gave published claims. `tools/skill-blocks/` holds the two template
variants and a `skills.json` of per-skill parameters; `tools/gen-skill-blocks.py` renders them
into the region between `<!-- uscha:orientation-block:begin -->` and its `end` twin, in both trees.

A generator nobody runs is a suggestion, so `--check` is measured (T152): green over this repo,
exit **1** naming the file when one word inside a region drifts, exit **2** naming the file when a
marker is gone — a configuration fault is not a drift, and collapsing the two would let a deleted
marker read as "nothing to update". The test drives a throwaway copy of the trees through a new
`--root` flag; a test that mutated the repo it is testing would not be one.

Repo rule **11** states the discipline: edit the template, run the generator, never the block by
hand. Everything outside the two markers is still per-skill prose.

### `docs/adr/INDEX.md`: forty-one ADRs get a reading order

Forty-one ADRs in one flat directory is a list, not a document. `docs/adr/INDEX.md` groups them by
who needs them and opens with a five-ADR entry path for someone arriving cold. The folder stays
flat and the numbering chronological — prose across the repo cites ADRs by number, so nothing is
moved or renumbered; the index is the map over the flat folder. Repo rule 8 now names it: a new
ADR is added to the index in the same change that writes it, and ADR-041 (which shipped in 1.96.0
without a row) got one.

The index is **measured**, not trusted (`AC-DC-04`): every `ADR-*.md` has exactly one row, every
row's link resolves, every row's status is that ADR's own `## Status:` line verbatim, and no row
names a file that does not exist. That check earned itself twice on the day it was written — it
found ADR-041 with no row at all, and then caught the first draft of this release putting the
ADR-041 amendment in the INDEX row while the ADR's own status line still read `Accepted (1.96.0)`.
An index that says something its source does not is the drift this repo exists to refuse.

`README.md` also moves "The diamond" below "What makes it different" — the reader meets the claim
before the research programme behind it.

### CI: three cells on a push, six on a tag

The matrix was `ubuntu` / `macos` / `windows` × Python 3.8 / 3.13 on **every** push and PR: six
cells of a ~35-minute suite, buying the same answer several times.

The grid exists for the failures that are *invisible outside it*, and each has exactly one home:

| cell | the trap only it can see |
|---|---|
| `macos` / 3.13 | bash 3.2 quoting — macOS ships that bash whatever Python is installed |
| `windows` / 3.8 | 8.3 short paths under `runneradmin`, **and** the declared interpreter floor |
| `ubuntu` / 3.13 | the reference cell |

Those three run on a branch push or PR. A **tag** — and a manual dispatch — runs all six. What the
reduced grid does not measure is said out loud rather than implied: `ubuntu`/3.8, `macos`/3.8,
`windows`/3.13. Pinning the floor to `windows` also costs almost nothing in wall time: it was
already the slowest cell.

**Nothing is published on three cells.** `smoke.yml` now also triggers on `v*` tags;
`tools/release.py` waits for the branch push's 3-cell run before creating the tag (I8), the tag
triggers the 6-cell run on that same SHA, and `publish.yml` reuses **that** run — selected by
`head_branch` (the tag name), never by "the newest run for this SHA". Both runs exist on that
commit, and "newest" is a race whose losing side would publish on three cells. If the grace
expires with no tag run, the runs that *do* exist for the SHA are listed by branch before the
fallback: "three cells stood in for six" has to be a line in the log, never something a reader
infers from its absence. The receipt line no
longer asserts "6/6 cells" as a constant either; it prints the run's URL, its ref and its event,
so the log says what was actually leaned on. The empty-sample grace grew from two minutes to
**five**, matching what `release.py` already gives a run to register: the tag's matrix is now
triggered by the same push that starts the publish job, so asking too early is the normal case.

Implementation note worth recording, because the obvious approach does not work: GitHub does not
expose the `matrix` context to a job-level `if:`, so a per-cell condition is not expressible. A
small `grid` job computes the matrix JSON and `smoke` consumes it with `fromJSON` — which is the
better shape anyway, since a reduced run has three jobs rather than six with three skipped.

### The paper: honesty and numbers pass (round 1)

`docs/paper/uscha-paper.{tex,html,pdf}` (and the byte-identical copies under `site/docs/paper/`) had
last been touched at 1.92.0. A read-only review against the ADRs and the bench fixtures found six
claims that were false or stale and a Diamond paragraph that did not carry the qualifiers the
program itself requires. Changed, each sentence traceable to its source: the three compilers are
named (Claude Haiku, Sonnet and Opus, one vendor; cross-vendor compilation is not yet measured);
"each release passed an independent blind review" now names the two exceptions (1.74.0 and 1.75.0,
reviewed inline, and the later independent review of 1.74.0 caught two defects the self-review had
missed); the suite count is dated (440 checks at kit 1.96.0, 227 of 227 acceptance criteria measured);
the self-application arc runs through 1.96; the implementation is released, not "will be"; Figure 2's
caption says its toolbar band predates two of the nine skills; the HTML twin's section reference
(section 7 for section 6) is fixed; the Diamond paragraph carries the noise-floor coverage (ten of
twelve archetypes at n=2), the SIGNAL/NOISY/NOISE tally, the NOISY 0.642 and MIXED-under-3.8
qualifiers on the controlled-language result, the round-trip range and tag coverage, and the
single-curator fact; Limitations gains one vendor, noise-floor coverage and the two-dimensional
JavaScript distance. Nothing was restructured or rewritten for style; that is round 2. The PDF was
regenerated from the HTML.

## Migration

None. No shipped file changed behaviour for a consumer project; the engine gained one flag
(`facts --write`) that nothing calls unless asked. For maintainers of this repo: the ritual is
unchanged in shape — `python tools/release.py X.Y.Z --message-file <msg> --tag` — but step 2 now
fixes the published claims it can derive instead of printing them, and the tag waits on a 3-cell
run while the publish waits on the tag's 6-cell one.

Suite: 442 checks · 0 fail; acceptance 235/236.
