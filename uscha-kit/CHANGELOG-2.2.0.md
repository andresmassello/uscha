# uscha-kit 2.2.0 — the agent asks for decisions, never for information (2026-09-07)

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

Suite: __SUITE__ checks · 0 fail; acceptance __ACC__.
