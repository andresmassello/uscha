# uscha-kit 2.2.0 — the agent asks for decisions, never for information (2026-09-07)

This release is a BATCH: eight items that arrived together from two field retrospectives
on live projects, carrying five ADRs (ADR-044 through ADR-048). They are one release because
they were measured as one -- a single suite run over a single tree -- and each keeps its own
section below, in the order the work landed: the origin markers (ADR-044), four field fixes
from a live monorepo, the homepage claim entering the facts gate with the installed-skill
version marker (ADR-045), field truth for greenfield (ADR-046), the smoke run as measured
evidence (ADR-047), operability as a measured dimension (ADR-048), and the first-use
walkthrough. Every section states its own scope and what it deliberately left out.

## The finding

Two field reports, arriving from opposite ends, that turned out to be one rule.

**A — a decision entered scope that nobody had made.** The agent read a global default —
*artifacts are written in English* — and turned it into a tree-wide rename. Not as a suggestion:
as a NEW acceptance criterion, a NEW `HANDOFF.md` rule, and two NEW ADR decision items, written
in the same voice as the items the human had actually decided. They were approved **by rebound**:
they sat inside a twenty-item summary the human said "ok" to. The work was cancelled after **112
files had already been renamed**.

The same shape, smaller and just as real, in a security fix: the agent moved a stack trace to
`DEBUG` because that is generally good practice, inside a change whose scope was something else.

Neither is a hallucination. Both are *reasonable* proposals — and that is precisely what makes
them dangerous. The artifact records WHAT was decided and never WHO decided it, so the moment the
conversation scrolls away, an item the agent invented and an item the human chose are the same
sentence in the same file.

**B — the agent asks for what it can read.** The devloop SKILL's rule 5 said that before
modifying any tracked `.md` the agent must *"ask the human for the current version first"*. The
current version of a tracked file is in the tree. The question produces a round trip whose answer
the agent could have obtained by opening the file — and it trains both sides that questions are
cheap ceremony, which is exactly the habit that makes a real question (finding A) easy to answer
with a distracted "ok".

## The rule

**The agent asks for DECISIONS, never for INFORMATION.**

*Information* is what the tree holds: the current version of a tracked file, what a config says,
whether a test exists. It is READ.

*A decision* is what only the human can supply. It is asked for — one at a time — and until it
arrives, whatever the agent decided in its place is marked as such.

This is the same line ADR-043 drew in 2.1.0 between a requirement the human declared and an
opinion the kit defaulted to, drawn this time through the conversation instead of through a
config file.

## Half one: read the file

Devloop rule 5 is rewritten. Read the tracked `.md` out of the tree, preserve its progress
(checkboxes, notes), edit in place, never regenerate from scratch. The *preservation* half of the
old rule was always right; the *question* was the defect, and it is removed rather than softened.
The discovery SKILL's "Explore instead of asking" is restated in the same vocabulary so the two
skills say one thing.

This half costs nothing and removes a question. It is not the interesting half.

## Half two: `origin: agent`

Every acceptance criterion, ADR decision item or `HANDOFF.md` rule that did **not** come from a
human answer carries one trailing marker on its own line:

    - [ ] AC-12 - when X then Y. (origin: agent)
    - [ ] AC-12 - when X then Y. (origin: agent, confirmed: 2026-09-07)

The grammar is deliberately dull: a trailing parenthesis, greppable with `rg "origin: agent"`,
identical in every file the method writes, and legible to someone who has never read the ADR.

- **No marker means human origin.** That is the default, and it is what makes this adoptable:
  not one existing line is retro-tagged, in this repo or in yours.
- **Confirmation is PER ITEM**, written as `confirmed: YYYY-MM-DD` on the same line. A
  package-level "ok" confirms none of them — that is the exact failure of finding A, and a rule
  that let a summary confirm twenty items would reproduce it with extra steps.
- **An unconfirmed item is not in scope.** It is not implemented, not gated on, not quoted back
  as agreed. It is written down so it is VISIBLE, not so it is settled.
- **A malformed `confirmed:` counts as unconfirmed, and is NAMED.** `confirmed: soon`,
  `confirmed: 2026-13-40`, `confirmed:` with nothing after it — none of those is a date, and a
  typo that read as a human's approval would be the one failure this marker exists to prevent.
- **A marker inside a fenced block or an inline code span is documentation** and is skipped. The
  ADR and the ACCEPTANCE section that DEFINE the grammar quote it; a scanner that read its own
  definition as a finding would be measuring its own prose.

## What the engine does with it — advisory, and nothing else

`spec-check` gains one conditional line, over the files it already reads plus the `ACCEPTANCE.md`
in play, `docs/adr/*.md` and `HANDOFF.md` when present:

    ~ origin: 2 agent-origin item(s) unconfirmed -- AC-07 (ACCEPTANCE.md:41), D-03 (docs/adr/ADR-002-x.md:57)

and `agent_origin: {unconfirmed: [...], confirmed: n}` in `--json`. `readiness` prints one line
of its OWN:

    --- origin: 2 agent-origin item(s) unconfirmed   (spec-check names them)

and carries the same object in `--json` when there is anything to report.

**It never changes an exit code, never caps the score, never blocks convergence, and never joins
the gates line.** The field author asked for an advisory and an advisory is what this is — and
after 2.1.0 the kit's posture is that a gate needs a budget the project adopted, which nobody has
declared for this dimension. The readiness line stays OUT of the gates rollup for the reason
ADR-043 gave in the other direction: folding something that is not a gate into `N ok` is a false
clean, and folding it into `N blocking` would be a gate nobody declared. It is neither, so it
gets a line of its own.

A tree with no marker anywhere prints exactly what it printed in 2.1.0 — byte for byte.

## What is measured

Smoke **T160**, seven criteria (`AC-OA-01..07`), over real temp trees and the real engine:
an unconfirmed item is listed with id and `file:line` in both surfaces while the exit code stays
exactly what the same tree produced unmarked; a valid `confirmed:` date removes the item from the
list and adds it to the count; `soon`, `2026-13-40` and an empty value all list as unconfirmed
with the failing value named; `readiness` prints its line only above zero, and against a CONTROL
— the same ledger and tree with every marker stripped — the score, the status, the gates line and
every dimension are identical and the output differs by exactly that one line; a marker-free tree
is byte-identical to the `v2.1.0` engine on stdout, stderr and exit code; and `AC-OA-06`, the
**red probe** — the `v2.1.0` engine run on the marked fixture must print no `origin:` line and
carry no `agent_origin` key, and reports UNMEASURED rather than passing when git or the tagged
copy is absent; and `AC-OA-07`, from the fresh review — an unclosed fence no longer hides every
marker after it (a typo is not a decision to hide the rest of the file), a confirmation appended
after the original tag on the same line is read, and a marker inside an HTML comment is skipped.

A probe was run against this release's own engine before it shipped: making the scanner blind to
the `confirmed:` field — every marker read as confirmed — turns `AC-OA-01`, `-02`, `-03`, `-04`
and `-06` red. `AC-OA-05` stays green, correctly: it measures a marker-free tree, which that
probe cannot touch. A criterion that cannot go red measures nothing.

Acceptance goes 266 → 273 criteria; nothing was dropped.

## The claim moved where it was published

Repo rule 2, in the same change: the devloop SKILL and the discovery SKILL (both skill trees),
`uscha-kit/README.md`, `templates/CLAUDE.md` and `templates/docs/adr/README.md`. The published
decks and the paper are untouched: this release adds a convention and an advisory line, and
claims nothing on a surface that was not already silent about it.

## Not a breaking change

Nothing existing is retro-tagged, no marker is added to any file in this repo or in yours, and a
tree that carries none gets the 2.1.0 output verbatim. Devloop's principles renumber — the golden
rule moves from 6 to 7 and `origin: agent` takes 6 — and the text of the golden rule is untouched.

## Not in this release

The marker does not gate. No `--strict` mode fails on unconfirmed items, because that is a budget
and ADR-043's rule is that a budget is declared, not defaulted. It is not extended to code,
commits or PR titles: the three artifact kinds that hold decisions are where it belongs, and a
marker in a comment would be noise.

---

# Also in 2.2.0 — four field fixes from a live monorepo

Four reports from a team running the kit on a monorepo, all four reproduced against the 2.1.0
engine before a line was written. They share one shape, and it is the shape this release is
already about: the engine answered **confidently about a tree it was reading wrongly**, or
refused to answer at all about a fact the human could see.

## 1. A rename is a MOVE, and `--repo` scopes the diff (`gate-check`)

`git mv tests/a_test.py tests/b_test.py` blocked as a **deleted test** — a BLOCKER and exit 1 for
a change that deleted nothing. Two paths reached that verdict: `--from-git` did not pass `-M`, so
whether a rename was even visible depended on the caller's `diff.renames` config; and a saved
`--diff` whose producer detected no renames arrived as a delete/add pair, which is exactly what
the parser was built to catch.

Both are fixed. `--from-git` now forces `-M` — the option is opt-in inside the engine, because
the other readers of the same helper (simplicity, waste, regression) count LINES, and collapsing
a rename into a header would silently change numbers they have been measuring for releases. A
diff with no rename headers is paired by CONTENT: the same file body leaving one path and
arriving at another. Moves are reported under `moved`, informational and outside the hard/soft
tally.

What did NOT move: a real deletion still blocks, and **ambiguity is refused rather than
resolved** — two deleted test files sharing one body pair with nothing and stay two deletions,
because guessing which moved where would be inventing a fact to clear a gate.

The second half of the same report: `--repo R` did not scope anything. In a monorepo ONE
`git diff` carries every repo's hunks, so a sibling repo's suppressions and deletions were
reported under whichever repo was named — a fact about someone else's code, attributed to yours,
with your exit code behind it. `--repo R` now restricts the scanned hunks to `repos[R].path`,
comparing with `realpath` on BOTH sides (the Windows 8.3 short-path trap this repo has already
paid for once, in CI and never locally).

## 2. `spec-drift` reads the monorepo's SPEC

`spec-drift --repo R` looked for `SPEC.md` and `docs/adr/` only inside `repos[R].path`. A
monorepo keeps ONE spec at the root, next to `uscha.config.json` — so the answer was
`no spec documents found`, which is indistinguishable from "no drift" and went unnoticed for a
week. It now searches the repo path FIRST (a repo carrying its own SPEC is describing itself and
still wins), the config root second, and the report NAMES which of the two it read — `spec_source`
in `--json`, and a `CONFIG ROOT` line for a human. Still advisory, still exit 0 always.

## 3. `log-gate --kind ci` — the one fact every team already has

A green pipeline could not be recorded. `--kind` had no `ci`, so the fact the whole team looks at
every day was the one fact the ledger had no word for. `ci` joins the closed vocabulary as a FACT
gate: a `fail` caps readiness ≤65 and blocks convergence exactly like `gate-check`, a `pass`
clears it, a `not-run` records absence and leaves the last state standing. `--verdict advisory`
is REFUSED on it, as on every FACT gate — a mandatory gate cleared by goodwill is what this
ledger exists to refuse. `--ref <run URL or id>` is stored on the record and travels to the gates
rollup: a CI verdict typed by hand is a claim, and the run beside it is the receipt.

It is admitted because it is MEASURABLE, not because it is useful — an LLM judgment does not
become a gate by being important (ADR-014, INV-ADVISORY-01). Adding a FACT kind is declared in
the CONSTITUTION template, where that closed vocabulary is stated to the project rather than only
to the parser. `ci` gets no CONSTITUTION invariant of its own: the seven are unchanged.

## 4. `init --add-repo` — a service can join a live loop

Adding a second service meant re-running `init`, which builds a NEW ledger: the step counter,
every repo's iterations and every snapshot went back to zero. Hand-editing `QA-LEDGER.json`
instead trips the integrity checksum — correctly, and that refusal stays, because it is what
makes "measured beats narrated" worth anything. What was missing was a supported door.

`init --add-repo NAME --path P --type T [--test-command C]` appends one repo to the frozen config
and to `ledger["repos"]`, and `_save` re-seals the checksum. Nothing else moves: `defaults` are
not re-frozen, and every existing repo's steps, snapshots and iterations are byte-identical
across the add. `uscha.config.json` gains the same entry when it IS the source the ledger was
frozen from; when its repo list has drifted, it is left alone and the divergence is NAMED —
silently rewriting it would resolve a conflict the human has not seen. A duplicate name is
refused with both files untouched, and `--add-repo` without `--path`/`--type` is refused rather
than guessed.

**And the decision the command records rather than hides.** A repo added with no evidence reads
as UNMEASURED: it enters `facts.static_unmeasured_repos`, and every aggregate that averages over
repos reads LOWER until its first snapshot or gate lands. That is absence, not a regression — the
command says so in as many words, and `AC-FF-09` asserts it entry by entry: no repo that was
already measured moves, no gate arrives with the new repo, no cap fires. Excluding an unmeasured
repo from the average instead would be the opposite mistake, and the readiness code refuses it on
purpose: an aggregate of 1.0 must never be producible by silence.

## Measured, with a red probe per fix

`T161` carries `AC-FF-01..10`. `AC-FF-10` is the RED PROBE that ships: the `v2.1.0` engine, read
out of git and run on the same fixtures, must still show all four failures — the rename blocking,
`--repo` reporting the sibling, `spec-drift` saying "no spec documents", and `--kind ci` and
`--add-repo` rejected by the parser. Without git or the tagged copy it reports `None` =
UNMEASURED, never a silent pass.

Each fix was also reverted one at a time against this engine before it shipped. Removing `-M` and
the move pairing turns `AC-FF-01` and `-02` red; making the scope helper return nothing turns
`-03` red; dropping the config-root fallback turns `-04` red; removing `ci` from the choices
turns `-05`, `-06` and `-07` red; dropping the `--ref` write turns `-07` red on its own; and
disabling the `--add-repo` branch turns `-08` and `-09` red. A criterion that cannot go red
measures nothing.

Acceptance goes 273 → 283 criteria; nothing was dropped.

## Not in this release

`ci` does not run anything: the engine is TOLD what the pipeline did, it never asks a CI
provider. The move pairing is deliberately EXACT and one-to-one — a rename WITH edits keeps its
hunks, so deleting a test out of a moved file still blocks, and a producer that both renames and
rewrites a file without emitting rename headers is beyond what a diff can prove. `init
--add-repo` adds ONE repo and never removes or renames one: removing a repo would orphan its
evidence, which is a decision, not a flag.

# Also in 2.2.0 — the homepage claim enters the facts gate

## The finding

The project's own homepage said the Diamond Bench passes **9/12** archetypes. The measured number
has been **8/12** since 1.99.0, when ADR-042's cross-vendor arm moved `transformer` to PARTIAL —
and `docs/`, `uscha-kit/README.md` and every other surface said 8. Nine releases went out green
with that page in the gated set.

Two things were wrong at once, and both are the same mistake in different clothes.

**There was no fact to compare it against.** `SYSTEM-FACTS.json` derived the version, the
subcommand count and the skill count. The bench headline — the project's single most-quoted
number — was not derived at all, so `facts --check` had nothing to hold the page to.

**The gate could not see the claim.** The stat tile reads
`<div class="v">9<small>/12</small></div><div class="k">archetypes regenerate</div>`: the number
lives in one element and the noun that gives it meaning in the next. Every recogniser pattern
demanded whitespace between a count and its noun, so the homepage's headline numbers read as
prose. That is not a near-miss — the same screen also said `52 engine subcommands` against a
derived **53**, and the release was green on both.

## The fix

**A derived fact.** `facts` now counts the verdict rows of `DIAMOND-BENCH.md` — the report
`qa_ledger.py bench` generates over the committed fixture, banner-marked *"do not hand-edit;
every number is a measured run"* — and publishes `diamond.pass`, `diamond.partial`,
`diamond.entries`, `diamond.fail`, `diamond.pending`. Counted per archetype, never read off the
summary sentence beside them.

Re-running the bench inside `facts` would be the more direct derivation, and it is not
affordable: a full pass is ~650 child processes, and `facts` runs on every suite, every deploy
and twice per release. The counted report is the honest second best, and it is stated as such in
`_derivation`. An installed kit ships no report, so `diamond` derives `null` there — and a claim
about a fact this tree cannot derive is reported **UNMEASURED** by `--check` and left alone by
`--write`, never quietly agreed with.

**A recogniser that crosses markup.** The gap between a claimed count and its noun may now be
whitespace *or* HTML tags, for the diamond patterns and for the subcommand and skill counts that
already existed. Two claim shapes were added, and both were narrowed **by measurement** — each
wider draft was run against the whole gated set first and rejected by what it caught:

- `<n>/12 archetypes`, `<n> of 12 archetypes`, `<n> de 12 arquetipos` — the count must be
  followed, across markup but never across prose, by the noun it counts, and the denominator must
  be the digits `12`. That is what keeps this repo's own historical sentence (*"It was 9 of 12
  until ADR-042 moved transformer"*) and the paper's *"ten of twelve archetypes"* out of a writer
  that would otherwise have silently rewritten both.
- `<n> PASS <sep> <n> PARTIAL` as ONE shape, verdicts matched case-sensitively. Reading the two
  numbers independently caught the paper's snapshot of the July–August arm — *"nine archetypes
  PASS … three PARTIAL"*, a sentence about a different experiment — and would have offered to
  rewrite it. The bench headline always writes the pair together.

`<n> archetypes` alone is deliberately **not** a claim: across the gated set it names subsets far
more often than the bench (*"five archetypes"*, *"two archetypes have no second run"*), so the
entries count stays a derived fact with no recognised published shape. A gate that fires on prose
is a gate people disable.

The first run of the new writer rewrote four claims: 9/12 → 8/12 and 52 → 53 on both the English
and the Spanish homepage. `site/index.html` and `site/es/index.html` were already in the
`# canonical` section of `tools/facts-gated-files.txt` — the list was never the hole; the
recogniser was.

## What is measured

`T153` grows `AC-FW-06..08`. `AC-FW-06` is differential: over a throwaway kit whose copy of
`DIAMOND-BENCH.md` has one row changed from `PASS` to `FAIL`, the derived fact MOVES with it, and
over the live report it equals the rows the suite counts independently. A number that stayed 8
there would be a constant with a comment, which is what this replaced. `AC-FW-07` plants the
homepage's exact markup shape and asserts `--check` names it and `--write` rewrites it — with the
historical sentence and the paper's snapshot, both on the same fixture, byte-identical afterwards.

`AC-FW-08` is the RED PROBE that ships: the `v2.1.0` engine, given the same untouched bench report
and the same stale page, derives no `diamond` fact at all and exits **0** on the 9/12 tile. It
reads the claim as prose — which is precisely the nine releases of green this criterion exists to
make impossible. Without git or the tagged copy it reports `None` = UNMEASURED, never a silent
pass.

## Not in this release

The site is **not deployed**: `site/sync-docs.sh` is a gate, not a publish, and the live site is
nine releases behind on purpose. This change fixes the canonical sources and the gate that holds
them; the deploy is the maintainer's, at release time.

The homepage's `11 language stacks` and `100% Python stdlib` stay narrated — no mechanical source
exists for either yet, and inventing one to make a page look measured is the failure mode this
gate exists to catch (ADR-012's `omitted`, not `guessed`).

# Also in 2.2.0 — an installed skill says which kit it came from (ADR-045)

## The finding

Skills sat under `~/.claude/skills/uscha-*` from kit **1.54.0** while the kit in the repo was at
**1.97.0**. A whole discovery ran on prose three months stale, and nothing said a word — not the
skill, not the engine, not the operator, who had no way to notice.

The reason is small and complete: **a `SKILL.md` carried no version.** The kit's version lived in
six surfaces, and none of them travels with an installed skill — `install-uscha.py` copies the
nine skill directories verbatim, and whatever `SKILL.md` says is what the agent reads until
someone re-installs. There was no fact to compare, and so no comparison to make. The same shape as
the drift above, one layer out: prose being executed, with no derived fact behind it.

## The fix

**The generated block carries the version.** Since 1.97.0 the orientation block of every
`SKILL.md` is a generated region rendered from `tools/skill-blocks/` into 18 runtime files. Both
templates now open with `<!-- uscha kit: {{version}} -->`, rendered by `tools/gen-skill-blocks.py`
from `uscha-kit/VERSION` — the same file the six surfaces move. A missing or empty `VERSION` is a
configuration error (exit 2), never a default: a block stamped with a guessed version would be
worse than one with no stamp, because `doctor` would then compare an installed skill against a
number nobody wrote.

**The release script re-renders them.** `tools/release.py` runs the generator in step 2,
immediately after the six surfaces move and before the facts gate, and refuses (I3) if the
generator is missing. The six surfaces are no longer the only place the version lives; 18 runtime
files follow them, in the same commit X. `gen-skill-blocks.py --check` (smoke T152) is red
whenever `VERSION` has moved and the regions have not, so this is not a convention anyone has to
remember.

**`doctor` compares, and only reports.** It reads the marker out of every installed `SKILL.md`
under the roots the installer writes to (Claude `~/.claude/skills`, Codex `~/plugins/uscha/skills`,
pi `~/.agents/skills`, and the other Agent-Skills roots) — or the roots named with `--installed
DIR`, repeatable — and reports per root:

```
[ !] SKILLS OUTDATED at ~/.claude/skills: installed 1.54.0 < kit 2.2.0
     re-install: python install-uscha.py install --target claude
```

`--json` carries `kit_version` and a `skills_installed` array with both versions per root:
`current`, `outdated` (`installed: null` where the blocks predate 2.2.0 and carry no marker at
all, with the skills named in `unmarked` rather than given a version nobody wrote) or `not
installed` — which is not a fault, since the kit installs one agent at a time and six absent roots
are the normal shape of a healthy machine.

**Advisory, always.** An outdated install is a `warn`, never an `error`; `doctor` exits 0 whether
the install is current or three months old. Someone may be pinning a version on purpose, and a
diagnostic that fails a deliberate choice is a diagnostic people stop running. The `uscha-status`
skill prints the same finding as ONE line above its breadcrumb and then renders the readout
exactly as it would have.

**No new subcommand**, on purpose: the subcommand count is a published fact appearing in the
README, the site, the docs and the paper, and a `skills-check` command would have moved every one
of those surfaces to ask a question `doctor` already exists to answer.

## What is measured

New family `AC-SK-01..06` in `T162`. All 18 rendered regions carry the kit's own version and the
stamp comes from the template, not from 18 hand edits (`-01`); bumping only `VERSION` in a
throwaway copy makes `--check` exit 1 naming the drifted regions and writing nothing, and the
plain run re-stamps all 18 (`-02`); `doctor` reports `outdated` with both versions for a planted
1.54.0 root and `current` for a fresh one, **exit 0 in both** (`-03`); an absent or empty root is
`not installed` with `installed: null`, exit 0, no traceback (`-04`); a block with no marker at
all is `outdated` with the skills NAMED, never `current` and never a made-up version (`-05`).

`AC-SK-06` is the RED PROBE: the `v2.1.0` engine cannot answer the question at all — it rejects
`--installed` at the parser and its `doctor --json` has no `skills_installed` key. `None` =
UNMEASURED without git.

The release wiring is measured where a real release runs: `AC-RL-03` (T151) now asserts that
commit X carries the re-rendered `SKILL.md` pair alongside the six surfaces, stamped with the new
version — its fixture ships the real generator and a two-line template.

## Not in this release

No auto-update and no install prompt: the installer stays a command a human runs. An outdated
install gates nothing, anywhere. And a skill installed **before** 2.2.0 carries neither the marker
nor these instructions, so on that surface the warning cannot come from the skill itself — the
`doctor` seam is the instrument that still works there, because it runs from outside and reads the
installs. A stated limit, not a gap that closes itself.

Acceptance goes 283 → 292 criteria; nothing was dropped.

# Also in 2.2.0 — field truth for greenfield: a REAL-INPUT corpus is an evidence class (ADR-046)

## The finding

From a live greenfield build, in the field author's own words:

> The parser passed every test the agent wrote, and it was wrong. Running it over the REAL corpus
> is what exposed it: **96.96 %** before the fix, **99.645 %** after.

That number is the finding. No invented suite ever produces a 96.96 % — it produces green, or it
produces a bug the author already suspected. Only real inputs produce a percentage.

And the condition that made it possible is not a lapse of discipline; it is the ordinary state of
greenfield work. There is no production traffic to sample, no legacy system to characterize, and
the same mind that decided what the code should do also decided what the tests would feed it. A
suite built that way can be green across the whole input space its author imagined, and silent
about the one the world produces.

The kit had an instrument for the other half of this problem and only the other half.
`characterize` and `golden-diff` implement one clear doctrine — *the old code is the truth* — and
they are exactly right whenever there is old code. `uscha-characterize` says so in its own
description: it is the brownfield front. `uscha-discovery`, the greenfield front, had no notion of
field truth at all. The method could measure whether the agent kept its own promises. It could not
measure whether those promises were about the real world.

## `corpus-run` — the subcommand

```bash
python3 $QL corpus-run --repo <REPO> --corpus corpus/real.jsonl --command "python -m myparser" \
  --threshold 99 --ac AC-FIELD-01
#   [qa_ledger] backend-api/gate:corpus: FAIL 96.96 % (3195/3295) — threshold 99 % from --threshold
#     miss inv-2019-03 (mismatch): expected '{"total": 1042}', got '{"total": 104200}'
#     caps readiness <=65 and blocks convergence until a green run
```

The corpus is **JSONL**: one JSON object per line, `input` and `expected` required, `id` optional
(a positional `case-NNN` is derived when absent). Each case runs the command once with its input
on **stdin** — verbatim when it is a string, JSON-encoded (`sort_keys`) otherwise — and the
trimmed **stdout** is compared to `expected`: string compare first, then JSON-equal when BOTH
sides parse as JSON. So a command that reorders an object's keys is not a false miss, while a
command that prints prose is compared as prose. A non-zero exit is a miss named with its code.

**Determinism is part of the contract.** File order IS run order, so the same corpus reports the
same misses in the same places; `--timeout` (default 30 s) turns a hang into a miss named
`timeout` rather than an unbounded wait.

**Refusal beats a guess.** A corpus that is missing, empty, or carries a malformed line is
**exit 2**, naming the file and the LINE NUMBER, and it persists nothing. The failure this closes
is the obvious one: an unreadable corpus scored as 0 % is an unmeasurable input reported as a
measured catastrophe — and 0 cases scored as 100 % is the same lie with the sign flipped.

## The threshold is the project's — and with none, the run is ADVISORY

`--threshold`, else `repos[R].corpus_threshold`, else `defaults.corpus_threshold`. With **none of
the three declared**, the run is ADVISORY: the percentage is measured and persisted, it gates
nothing, it caps nothing, and it never joins the `N ok` count in the gates line.

This is ADR-043's posture applied on the day the instrument ships. A gate needs a budget the
project ADOPTED; a percentage the kit picked for you is an opinion wearing an exit code, and
nobody outside the project knows whether 99.6 % is excellent or unacceptable for its domain.

With a threshold declared, `gate:corpus` is a FACT gate like every other: `fail` is a BLOCKER —
readiness capped ≤ 65, convergence blocked — and a later green run clears it (latest-per-tool
wins). Nothing parallel was built: the record is the same static-gate shape `gate-check` writes,
so every reader downstream already understood it before this release existed.

`log-gate --kind corpus --verdict pass|fail|advisory|not-run` is the parity door for a corpus
measured elsewhere. `corpus` becomes the **third** member of `ADVISORY_CAPABLE_KINDS`, after
`simplicity` and `waste`, and the reason is specific to it: `corpus-run` itself runs advisory
whenever no threshold is declared. Refusing the verdict on the parity door while the check emits
it on the other would leave one fact with two incompatible records, and the parity door could only
spell an unbudgeted run as `pass` — the exact false clean ADR-043 exists to refuse. The closed
vocabulary is otherwise untouched: `ci`, `gate-check` and every other FACT kind still refuse
`advisory`, which `AC-CO-08` measures.

## A green corpus run closes a criterion MEASURED

`--ac AC-FIELD-01` stamps criterion ids on the persisted record, and `readiness` closes a
criterion whose only evidence is a corpus record **iff that record passed**:

- an **advisory** run measured a percentage against no adopted budget — not a green gate, and
  letting it read as one is the ADR-043 defect again;
- a **failing** run is evidence AGAINST, not absence of evidence;
- **red JUnit evidence still vetoes**, whatever the corpus says. Fail-closed did not move.

A ticked `AC-FIELD-01` with no green corpus record reports `narrated_only`, exactly as a ticked
criterion with no green testcase always has. The checkbox is narration; the run is the fact.

The closure is FULL, not stamp-only: `_ac_closed` — the seam the JUnit path already went through —
took one extra branch. Had it taken more, the honest half (the stamp plus the `narrated_only`
report) would have shipped alone with the closure deferred, which is what the plan called for.

## Readiness gets a `field` line — and no weight

```
--- field backend-api: corpus 66.7 % (2/3) < 90 % FAIL
--- field backend-api: corpus 99.6 % (996/1000) >= 90 % PASS
--- field backend-api: corpus 66.7 % (2/3) — no threshold declared, ADVISORY (measured, not gating)
--- field backend-api: corpus UNMEASURED — a corpus is declared and was never run (real/corpus.jsonl)
```

One line per repo that declares a corpus (`repos[R].corpus`) or has ever run one, plus a
conditional `field` object in `--json`. **A repo that declares no corpus and ran none prints
nothing and emits nothing** — the same conditional-silence rule `lifecycle` (ADR-040) and
`agent_origin` (ADR-044) follow, so every existing project's readiness output is what it was.

The `field` **dimension** and its weight are **deliberately not in this release** and are deferred
to their own ADR. A weighted dimension moves every existing project's score the moment they
upgrade, and it has to be argued and measured on its own rather than smuggled in beside the
instrument that would feed it. The line reports; a failing corpus already blocks through its
`gate:corpus` record.

## Discovery asks the question on day one

The discovery skill's domain round gains a MANDATORY question: **what input comes from the real
world, and where is the corpus?** Name the real-input surfaces, ask where a sample with its
expected outputs can be obtained, record the path as `repos[R].corpus`. No corpus on day 1 is not
a blocker — it is a **HIGH** risk in `RISKS.md` with an owner and a date.

The finding that produced this ADR was not "we ran the corpus late". It was "nobody asked whether
one existed", and a question nobody asks is a gap nobody sees. The skill also says the thing that
has to be said out loud: **never author the corpus yourself** — a corpus the agent invented is the
invented input this whole instrument exists to expose.

## What is measured

Smoke **T163**, nine criteria (`AC-CO-01..09`), over real temp projects and the real engine:
the 66.7 % gate persisted and rendered (`-01`); `narrated_only` → measured → reopened as the tag's
evidence changes (`-02`); UNMEASURED for a declared-and-never-run corpus and total silence for a
repo that declares none (`-03`); ADVISORY with no budget, held out of the `ok` count, plus the
full precedence ladder — flag beats repo beats defaults (`-04`); four refusals at exit 2 naming
the line, persisting nothing (`-05`); `timeout` and non-zero-exit misses named (`-06`); the
**control pair** — a passing corpus caps nothing at score 99.0, a failing one on a second repo
caps the same ledger at exactly 65 with `BLOCKER` as the reason (`-07`); the `log-gate` parity
door and the still-closed vocabulary (`-08`); and the **red probe** — the `v2.1.0` engine has
neither the subcommand, nor the `--kind`, nor the `field` block (`-09`).

A second probe was run during development and not shipped: breaking the comparison so every case
hits turns `AC-CO-01`, `-02`, `-04` and `-07` red. The block measures the comparison, not its own
scaffolding.

## Not a breaking change

No new weight, no new cap, no new default threshold, no change to any existing subcommand's
behaviour. A project that declares no corpus sees the same readiness text and the same JSON
payload it saw before, plus one additive `acceptance.corpus_closed` key.

## Not in this release

- **The `field` readiness dimension and its 10 points.** Deferred to its own ADR, on purpose.
- **A default threshold.** A budget is declared, never defaulted.
- **Corpus generation or sampling.** The engine RUNS real inputs; where they come from is the
  project's problem, and a synthesized corpus would recreate the exact failure this catches.
- **Partial or fuzzy matching.** A similarity score is a judgment, and judgments do not gate
  (INV-ADVISORY-01). A case hits or it misses.
- **Running the corpus automatically in the inner loop.** A real corpus can be large; when to run
  it is the project's scheduling decision, like `pit-check`.

Acceptance goes 292 → 301 criteria; nothing was dropped.

# Also in 2.2.0 — the smoke run as measured evidence: executed, never narrated (ADR-047)

## The finding

The ledger ingests everything a machine produces on its own: JUnit, coverage, linters, the static
gate's XML, and since this release a CI verdict. One phase of the loop was still prose. Phase 7 —
the smoke list — asked the agent to *produce a concrete manual smoke-test checklist*, and what
came back was a paragraph:

> the jar served /admin · the simulator answered 200 in 6 ms · the catalogue endpoint worked

None of that is evidence. It is a sub-agent narrating, and it is believed because it is written
confidently. From the field, the cost:

> **Every simulator run returned an empty list, because the database had no rows. The smoke was
> reported as verified.**

An empty list is a 200. A narrated smoke cannot tell "the endpoint answered correctly" from "the
endpoint answered", and the difference was the release. Worse, the ledger held no record of the
run at all — so readiness, convergence and the PR gate had nothing to disagree with the sentence.

The gap was never that smoke runs are hard to measure. It is that nobody asked the project's own
tool for a machine-readable answer, and prose was accepted in its place.

## `smoke-ingest` — the subcommand

```bash
python3 $QL smoke-ingest --repo <REPO> --report reports/smoke.json
#   [qa_ledger] backend-api/gate:smoke: FAIL — 7/8 checks ok
#     ok   AC-28 the jar serves /admin (status 200, 6 ms)
#     FAIL healthz (status 503)
#     caps readiness <=65 and blocks convergence until a clean smoke
python3 $QL readiness
#   --- smoke backend-api: 7/8 checks ok, 1 failed (healthz) FAIL
```

The contract is the smallest thing a shell script can emit:

```json
{"checks": [{"name": "AC-28 the jar serves /admin", "ok": true, "status": 200,
             "latency_ms": 6, "evidence": "curl -sS localhost:8080/admin | head -1"}]}
```

`name` (a non-empty string) and `ok` (a **boolean**) are the whole mandatory surface. `status`
(integer or string), `latency_ms` (a number) and `evidence` (a string) are optional, validated
when present, and never invented when absent — a check with no `latency_ms` measured no latency,
which is a different fact from a latency of 0. `ok: "true"` and `ok: 1` are refused: a contract
that coerces is a contract that cannot say what it measured.

The record carries the MEASUREMENT, not only the verdict — the report path, the ok/failed counts,
the per-check receipts (name, ok, status, latency) and the failed names, capped at 20 because a
receipt cites evidence and is not a dump. The counts and the AC verdicts are computed over EVERY
check, so a criterion's fate never depends on where the display list was cut.

## Refusal beats a guess

Exit 2, naming the first offending check or field: a report that is missing, unreadable, not valid
JSON, not an object, has no `checks` key, has a `checks` that is not a list, holds an **empty**
list, or carries a check that is not an object, has no `name`, has no boolean `ok`, or has a
wrong-typed `status` / `latency_ms` / `evidence`.

```
[qa_ledger] smoke-ingest: reports/smoke.json: check 2 (the admin page) has no boolean `ok`
            (got 'true') -- a smoke check is a binary fact, and a string, a number or a
            missing key is not a verdict
```

The empty list is the one worth naming twice. `{"checks": []}` is a run that verified nothing, and
scoring it `0 failed → PASS` would manufacture a clean gate out of an absence — the false clean
this kit refuses everywhere else.

## A FACT kind — and it may NOT run advisory

`log-gate --kind smoke --verdict pass|fail|not-run` is the parity door for a smoke measured
elsewhere (a CI job, a nightly, a human running the paths by hand). `smoke` joins the closed
`--kind` vocabulary as the second FACT addition after `ci`, and it is **not** admitted to
`ADVISORY_CAPABLE_KINDS`.

The asymmetry with `corpus` (ADR-046, in this same release) is deliberate and is the interesting
half. `corpus` may run advisory because a percentage is only a verdict once a budget is ADOPTED,
and with no threshold declared there genuinely is no gate. A smoke check has no budget: `ok` is
binary. It answered or it did not. An advisory smoke would be a mandatory gate cleared by
goodwill, so `--verdict advisory --kind smoke` is exit 2.

## A green check closes a criterion — and a failed one VETOES it

A check whose `name` carries an AC tag — `AC-28 the jar serves /admin`, in the **same tag grammar
JUnit testcase names use** — closes that criterion MEASURED **iff** the check is `ok` **and** the
ingested report's gate is `pass`. Both halves matter: a green check inside a failing report is a
green light on a run that did not hold.

And a **failed tagged check vetoes**, exactly like a red JUnit testcase. The veto is evaluated
before any green, because the cheapest way to fake a closed criterion is to put a green beside a
red. `readiness --json` reports both halves — `acceptance.smoke_closed` and
`acceptance.smoke_vetoed` — and the `narrated-only` line gains its smoke clause: a ticked
criterion with no green testcase, no green corpus run and no green smoke check is narration.

## Phase 7 produces the report

The devloop skill's phase 7 no longer asks for a prose list. It RUNS the smoke paths with the
project's own tool, has that tool write `reports/smoke.json`, ingests it, and cites the resulting
verdict line in the PR body instead of a claim that the smoke passed.
`uscha-kit/templates/scripts/smoke-report-example.json` is the reference report — three checks,
one tagged `AC-01`. If a human runs the paths by hand, they still write the report: a checklist a
human ticked is evidence, a checklist an agent narrated is not.

## What is measured — `AC-SI-01..09`, smoke **T164**

Nine criteria over real temp projects and the real engine: the gated fail and its clearing by a
later clean report (`-01`); `narrated_only` → MEASURED through a tagged check, attributed in
`acceptance.smoke_closed` (`-02`); the **veto** — a failed tagged check holds the criterion open
even beside a green one elsewhere, and a green check inside a failing report closes nothing
(`-03`); the empty list refused at exit 2, persisting nothing (`-04`); six refusals naming the
offending check or field (`-05`); the record's receipts, the named failure on the readiness line
and total silence for a repo that ingested nothing (`-06`); the **control pair** — a passing
smoke caps nothing at score 99.0, a failing one on a second repo caps the same ledger at exactly
65 with `BLOCKER` as the reason (`-07`); the `log-gate` parity door and the advisory refusal
(`-08`); and the **red probe** — the `v2.1.0` engine has neither the subcommand, nor the `--kind`,
nor the `smoke` block, nor `acceptance.smoke_closed` (`-09`).

A second probe was run during development and not shipped: forcing every check to read `ok` turns
`AC-SI-01`, `-03`, `-06` and `-07` red. The block measures the verdict, not its own scaffolding.

## Not a breaking change

No new weight, no new cap, no config key, no change to any existing subcommand's behaviour. A
project that never ingests a smoke report sees the same readiness text and the same JSON payload
it saw before, plus two additive `acceptance` keys. Subcommands 54 → 55.

## Not in this release

- **A `smoke` readiness dimension.** A failing smoke caps through its gate record; a weighted
  dimension would move every existing project's score and is owed its own argument.
- **Running the smoke.** The engine ingests a report; how the paths are exercised is the project's
  problem, and an engine that invented HTTP calls would be inventing the evidence.
- **A check taxonomy** (endpoint / flow / device). A `name` and an `ok` are the contract.
- **Flake handling, retries or averaging.** A flaky check reported as `ok` is a lie the ledger
  cannot detect, and averaging it would be the kit manufacturing one.
- **`evidence` as proof.** The string travels for a human reader; the engine gates on `ok` alone,
  because a free-text field is narration again.

Acceptance goes 301 → 310 criteria; nothing was dropped.

# Also in 2.2.0 — operability is a MEASURED dimension, not phase-8 prose (ADR-048)

## The finding

Release by CI, the reset/seed script and the RUNBOOK arrived in the **last week** of two
consecutive projects. Not because anybody decided to defer them — because nothing ever asked.
The devloop NAMES all four, in phase 8, in prose, and prose is the one thing this kit has spent
its whole life replacing.

A narrated dimension is not a weak gate. It is an **absent** one: it produces exactly the same
output whether the work was done or forgotten, and by the time anybody looks, the answer is "next
week". Coverage, gate integrity, the golden suite, the stack's expiry date, the simplicity budget
— every one of them stopped being a checklist line the day the engine started READING
something. Operability never did, in projects running risk profile E.

## The fix

**A new subcommand `operability --repo R [--json]`** that verifies FACTS IN THE TREE. Four
checks, each `ok` / `missing` / `unknown`, each with a detail that SAYS what it matched so a human
can disagree with the match instead of with a boolean:

- **`ci`** — a workflow under `.github/workflows/*.yml` whose steps run the repo's
  **configured** test command (`repos[R].test_command`, else `defaults.test_command_<type>`),
  matched verbatim or by its first token beside a test-ish subcommand on the same line:
  `ci: ok (ci.yml runs "pytest -q")`.
- **`release`** — a workflow that publishes or attaches an asset, by a short DOCUMENTED
  recogniser list: `softprops/action-gh-release`, `actions/upload-release-asset`,
  `gh release create`, `gh release upload`, `gh release`, `npm publish`, `twine upload`. A regex
  over the word "release" would match a branch name, a job title and a comment — a gate that
  matches prose is a gate that certifies prose.
- **`runbook`** — `docs/RUNBOOK.md` (or `RUNBOOK.md`, or `defaults.operability.runbook`)
  exists AND names the four headings an operator needs at 3am: start/boot, config, rollback,
  smoke, matched case-insensitively in EN and ES (`arranque|start|boot`, `config`,
  `rollback|reversi`, `smoke|humo`), NAMING the ones that are absent:
  `runbook: missing sections (rollback, smoke)`.
- **`seed`** — a seed/reset command declared in `repos[R].operability.seed_command` or
  `defaults.operability.seed_command`, whose script exists on disk when the command names a path:
  `seed: missing (script not found: scripts/seed.py)`. The declaration is not the artifact.

Both trees are searched — repo path first, **config root** second, `realpath` on both sides
— and the answer NAMES which it read: the monorepo lesson `spec-drift` paid for earlier in
this release, plus the Windows 8.3 lesson of 2026-08-02, in one helper. The command **never
executes anything** (ADR-008: it reads the test command, it does not run it) and **its own exit
code is always 0**.

**GitHub Actions is the only pipeline read.** A `.gitlab-ci.yml`, `Jenkinsfile` or
`azure-pipelines.yml` is NAMED `unknown ci system`, never failed. Failing it would be a red nobody
measured; passing it would be a green nobody measured, and under a declared gate that second one
is the false clean ADR-043 exists to refuse.

## The posture is the profile's, not the kit's

`gate:operability` is persisted through the existing FACT-gate plumbing — no parallel
mechanism — and a new knob `defaults.operability.gate` decides what the record means. It is
`false` by the engine's own default and `true` on presets **C, D and E**, which makes it a
profile-OWNED knob: `init` must not write it (AC-RP-06 asserts that from the engine's own table),
and `doctor` reports it with its origin on the three-rung ladder like every other owned knob. It
is the first owned knob that lives one level DOWN in `defaults`, so `_apply_risk_profile` and the
origin ladder now read DOTTED knob names.

- **`gate: false`** (A, B, or no profile) → the record is **advisory**: never in the `N ok`
  count, caps nothing, blocks nothing. `operability` therefore joins `ADVISORY_CAPABLE_KINDS` —
  which widens WHEN it gates, never WHAT counts as evidence, the line INV-ADVISORY-01 draws.
- **`gate: true`**, a check `missing` → **fail**: readiness capped ≤ 65, convergence
  blocked, and `phase --require pr-ready` refuses **naming the missing check**. `static-gate
  gated=1 (gate:operability:1)` tells a human the gate is red without telling them whether to
  write a workflow or a RUNBOOK.
- **`gate: true`**, nothing missing, something `unknown` → **advisory**, not `pass`.

`readiness` prints one conditional line — `--- operability: ci ok · release missing ·
runbook ok · seed missing (advisory)` — and prints nothing at all when no record exists.
`log-gate --kind operability` joins the closed vocabulary for parity, for a project whose CI
computes the four facts elsewhere.

Because `init` freezes the expanded profile into the ledger's config, `_resolved_defaults` now
reads `_risk_profile_keys` — written by `_apply_risk_profile` for exactly this purpose, and
already read this way by the golden cap — so a profile-supplied knob is reported as
`profile <X>` on the frozen copy instead of masquerading as a human `override`.

**The skills say so.** The devloop's phase 8 RUNS `operability` before `readiness` and the PR body
cites the line; discovery's grilling agenda gains a day-1 item — *who owns the RUNBOOK and the
seed?* — because the cheapest moment to decide that is before anything is built, and the most
expensive is the week before go-live.

## What is measured

T165, `AC-OP-01..08`, over real temp projects: `ci: missing` with no workflow, exit 0, advisory
under B (`-01`); an absent RUNBOOK under E persists `fail`, the rollup row blocks, and
`phase --require pr-ready` exits 1 naming `runbook missing` (`-02`); the CONTROL PAIR — the
same complete tree reads `pass` under E and `advisory` under B with a byte-identical note, and
readiness prints the line, and prints nothing with no record (`-03`); a RUNBOOK missing headings
names them (`-04`); an orphan seed script is named (`-05`); the generated config declares no
`operability` knob while `doctor` reports `effective operability.gate = True` with origin
`profile E`, exit code unchanged (`-06`); a foreign CI is `unknown` and keeps the record advisory
even under a declared gate (`-07`).

`AC-OP-08` is the RED PROBE: the `v2.1.0` engine has no `operability` subcommand, rejects
`log-gate --kind operability` at the parser, and knows no `operability.gate`. `None` = UNMEASURED
without git.

One twin gap fell out of the subcommand count moving: the EN doc carried a **Exact current parser
surface: N subcommands** line and the ES doc did not, so the facts writer rewrote one page and
not the other and `AC-VC-02` went red — repo rule 3, caught mechanically. The ES page now carries
the same claim (**Superficie exacta del parser actual: 54 subcomandos**), so it is inside the
facts gate too and the twins moved together again.

## Not in this release

Nothing is GRADED. The engine can see that a `## Rollback` heading exists; whether the procedure
under it is correct is the human's, and pretending otherwise would be the invented judgment
ADR-014 refuses. Nothing is EXECUTED — not the tests, not the seed, not the pipeline. No CI
system other than GitHub Actions is read, because a reader that guesses is worse than an honest
`unknown`. And profiles A and B gate exactly as much as they did before: zero.

Acceptance goes 310 → 318 criteria; nothing was dropped.

# Also in 2.2.0 — one executable first-use path

## The finding

The entry experience asked a newcomer to learn the model before it showed them one complete
result. The README opens on doctrine, the field manual opens on doctrine, and the reader who
wanted to know what the kit DOES on their own repo had to assemble that answer from five pages.
A method that measures evidence was asking to be believed first.

## The fix

`docs/FIRST-USE-EN.md` and its Spanish twin `docs/FIRST-USE.md` are the short path: ONE verified
runtime, the install and the first skill invocation together, ONE bounded change carrying ONE
acceptance criterion, the executed evidence that closes it, and the merge left to the human. The
guide is reachable from the README and from both homepages, one link each.

Every transcript on the page is real output from the run that wrote it. The two agent-driven
steps are labelled *not exercised here* rather than dressed up as a transcript — the same rule
ADR-047 applies to a smoke list, applied to a walkthrough.

## What is measured — `AC-FU-01..05`, smoke **T166**

These are DOC criteria: the block measures the PAGE, not the engine. `T166` extracts every fenced
`bash` command in the guide that invokes the engine or the installer and RUNS them in order in a
clean temp project, so a command that rots is a red suite rather than a reader's dead end; the
lines it cannot run (`npx`, `cd`, `pytest`, the `/uscha-*` agent invocations) are excluded BY NAME
in the sidecar, never silently dropped. It also asserts the three entry links resolve, that every
route names a skill that exists on disk, that the twins carry the same fences with byte-identical
command lines and no fenced line wider than 120 columns, and that neither twin promises a
completion time.

## Not in this release

No new engine behaviour and no new subcommand — the guide navigates capabilities that already
ship. The runtime the page claims is the one that was exercised, and no second one is implied.

Acceptance goes 318 → 323 criteria; nothing was dropped.

Suite: __SUITE__ checks · 0 fail; acceptance __ACC__.
