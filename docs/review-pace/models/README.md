# Model check of ADR-062 decisions 1-2 (review tiers, diff-scoped re-review) -- input for 2.16.0

A TLA+ model of `../../adr/ADR-062-review-pace.md` decisions 1 and 2, checked with TLC v1.7.4
BEFORE 2.16.0 writes the code (repo rule 12). It is a design artifact: nothing here ships, and
nothing here is a claim about the engine (repo rule 2). **A green config proves no violation OF
THE MODEL at its bounds -- not that the engine is correct.** Each counterexample below becomes a
RED case (AC-RP-nn) once the code exists, and is replayed against the real engine there; a path
the code does not reproduce means the model is wrong until shown otherwise.

`ReviewPace.tla` started as a copy of `../../gate-integrity/models/GatedDebt.tla` at commit
`a9ea294`. The 2.15.1 rules GatedDebt switches with `V211`, `DeferFix` and `MemoryFix` are fixed
ON. `Witness`, `Anchor`, `Lies` and `Memory` keep their meaning. Every new behaviour sits behind
a new constant (see the module header), and with all of them off the module **is** GatedDebt:
`ci-baseline.cfg` gives the same 2,936,010 distinct states as gate-integrity's `ci-shipped.cfg`
(no error). That number is the regression link between the two models.

## Rule

`NoFlaggedBugShips`: `pr-ready` never holds while the files a gated step covered carry exactly
the content that step flagged, unless the finding is deferred. For a whole-change review that is
GatedDebt's rule (the reviewed tree). For a review of a subset of the files, the ledger learns
only that THOSE files, at that content, hold a gated finding -- so that is what must not ship.

## The shape

- Two files: `a` holds the bug at content 0 and is touched by every fix; `b` is never buggy (the
  unrelated file). Each file has contents 0..1. `a` matches a `quick` glob. **The bug is only ever
  in `a`; a finding inside a deep-glob file is not modelled.**
- Tool 1 flags what it sees in its scope. Every no-error config has only tool 1; two `.cfg` files
  (a tooth and a vacuity probe) add tool 2, which never flags.
- Tiers: the tier is the highest glob tier of the files the change touches (`b` matches `GlobB`),
  or the tier the agent raised it to. No action lowers the raised tier, but the touched set is
  derived from the tree, so **reverting `b` lowers the computed tier** (`GlobB = 2`). quick runs
  tool 1; standard and deep run every tool.
- Diff scope: the agent picks the files of every review (the engine does not stop it; it only
  reads what was logged). In quick/standard, convergence is C1 (every tool of the tier has had one
  clean pass) and C2 (every file changed after a tool's clean pass has been reviewed clean again);
  the latest step must be clean and on the tree on disk (Anchor). In deep it is today's rule, plus
  "each tool's last review covered the whole change".
- The agent may lie (`Lies = TRUE`): it can log 0 gated findings for a review that found some.
- Bounds: see "Why these bounds". The `ci` configs of the new design run `MaxLog = 3` (records,
  runs and steps together), one tool, no deferral moves; `ci-baseline` keeps GatedDebt's own
  `MaxLog = 4` with deferrals.

## Findings

### 1. Decision 2 as written lets a flagged finding ship -- with an HONEST agent

`tooth-as-written-honest.cfg` (decision 2 literally, no lying): **violated in 7 states**
(`-workers 1`, the shortest trace TLC finds):

1. tool 1 starts a review of `a` alone, on `(a0, b0)`;
2. the agent edits `b` (`b1`);
3. a test-run stamps `(a0, b1)`;
4. the gated step is logged: it reviewed `(a0, b0)`, scope `{a}`;
5. tool 1 reviews `b` alone on `(a0, b1)`, honestly clean, and it is logged.

The clean step's tree differs from the gated one (in `b`), so the tree-level debt (ADR-056)
closes, and Memory sees new content. C1 holds: tool 1 has a clean pass. C2 has nothing to check:
no clean pass came before. `pr-ready`, and `a` still has the content tool 1 flagged.

The cause: **a clean pass over files that do not include the flagged file closes the finding.**
The debt and Memory compare whole trees, which was sound only while every review covered every
file. `tooth-as-written.cfg` (the same, lying agent) breaks in 7 states by a second route: the
same first four steps, then tool 1's next review of `a` (truly gated, on `(a0, b1)`) is logged
clean. Memory compares whole trees, and the two trees differ in `b`.

### 2. What closes it: findings carry their file, debt and Memory read that file

- **`Locate`**: a gated step records the files its findings are in (the gated id carries the path;
  decision 4 already makes ids mandatory under `review_tiers`).
- **`CoverFix`**: the debt of a gated step closes only on a clean step that **covered those files**
  and in which **they** moved, or that saw a deferral (2.11.0's rule). A clean step contradicts the
  gated one (Memory) when it covered those files and they did not move. "By the same tool" is not
  new: the engine already reads the debt and Memory per tool (`_review_verdicts`), and so does the
  model in every config.
- **`SameTool`**: C2's re-review must come from the tool whose clean pass the change outdated.

### 3. Necessary vs checked sufficient -- at which bounds

Necessary (each one's absence is a counterexample; the teeth, `-workers 1`):

| dropped | config | bound | shortest trace |
|---|---|---|---|
| `CoverFix` (with `Locate`) | `tooth-without-cover` | `MaxLog = 3`, 1 tool | 6 states, lying agent |
| `Locate` (with `CoverFix`) | `tooth-without-locate` | `MaxLog = 4`, 1 tool | 8 states, lying agent |
| C2 (with both) | `tooth-without-rereview` | `MaxLog = 4`, 1 tool | 9 states, no lie |
| `SameTool` (C2 as worded) | `tooth-any-tool-rereview` | `MaxLog = 4`, 2 tools | 9 states, no lie |

Checked sufficient (no error), and only at these bounds:

- `CoverFix` + `Locate` + C2 + `SameTool`, **one tool**: `MaxLog = 3` with raises to deep
  (`ci-shipped`, `ci`), `MaxLog = 4` (`deep-shipped-maxlog4`, by hand), `MaxLog = 3` with
  deferrals (`deep-shipped-defers`, by hand), and with the tier lowered by a revert (`ci-lowering`
  at `MaxLog = 3`, `deep-lowering-maxlog4` by hand).
- **With one tool `SameTool` is inert** (there is no other tool to re-review). **With two tools
  nothing is checked sufficient**: the no-error run at `MaxLog = 4` was stopped past 134 million
  distinct states / 16 min -- UNMEASURED.

**What CI checks today.** `ci-shipped` (`MaxLog = 3`) cannot see the `Locate`, C2 and `SameTool`
paths: with `Locate = FALSE` or `Rereview = FALSE` it still prints no error, 1,740,180 distinct
states, measured. A `MaxLog = 4` no-error config does not fit the 60 s limit: 54-64 s on this
16-core machine across runs, and a 2-4-core CI runner is slower. **Until the teeth enter the manifest with their AC ids, CI checks
only `CoverFix` and the as-written break**; `Locate` and C2 are checked sufficient only by hand
(`deep-shipped-maxlog4`). The teeth themselves stop in 2-5 s, so as `ci` entries they will make CI
see each rule's necessity.

The tooth stories:

- **without-cover** (6): an unwitnessed gated step on `(a0, b0)` (an honest count) is located in
  `a`. The agent edits `b`, a review of `a` starts on `(a0, b1)`, a test-run, and that review
  (truly gated) is logged clean. Whole-tree debt and Memory see different trees.
- **without-locate** (8): a whole-change review starts on `(a0, b0)`. The agent edits `b`, a
  test-run, and an unwitnessed gated step is logged on `(a0, b1)`, covering its whole scope. The
  pending review (truly gated) is logged clean: it covered both files and `b` moved, so the debt
  closes. Tool 1 then reviews only `b` (clean). Memory does not fire: that review did not cover
  every file the gated step covered.
- **without-rereview** (9): the agent fixes `a`, a review of `a` starts on `(a1, b0)`. The agent
  reverts `a`, a test-run, and an unwitnessed gated step is logged on `(a0, b0)`, located in `a`.
  The stale review is logged clean: it covers `a`, and `a` moved, so the debt closes. Tool 1
  reviews only `b` (clean). Anchor holds and Memory does not fire. `a` changed after its clean pass
  and nothing re-reviewed it: C2 refuses exactly this.
- **any-tool-rereview** (9): the same first seven steps, then **tool 2** reviews the reverted `a`,
  honestly clean (tool 2 never flags). That satisfies C2 "by at least one agent tool", and Memory
  (per tool) does not fire for tool 2. **The trace is in the QUICK tier: tool 2 is outside the tier**,
  yet it satisfies C2 and it is the latest step, the one Anchor reads. A possible extra rule: C2's
  re-review and the latest-step check count only tools of the tier. Not modelled.

### 4. Lowering the tier by a revert (measured, `GlobB = 2`)

With `b` on a deep glob, touching `b` makes the change deep; reverting `b` makes it quick again --
no human act involved. `ci-lowering-vacuity` breaks `NeverLoweredAndReady` in **8 states**
(`-workers 1`): the agent edits `b` (deep), an unwitnessed gated step is logged on `(a0, b1)`, the
agent fixes `a` and reverts `b` (quick), tool 1 reviews `a` alone clean, a test-run: `pr-ready` in
quick, with a known finding fixed. So the path is reachable. `NoFlaggedBugShips` holds on it:
`ci-lowering` (`MaxLog = 3`, 580,060 distinct states) and `deep-lowering-maxlog4` (`MaxLog = 4`)
give no error. The debt and Memory are read for every tool that ever logged, so a lower tier
removes reviews, not knowledge. What it loses is coverage of bugs NO tool has reported -- and in
this model the bug is in `a`, a quick file, so a finding inside the deep file is not checked.
Whether a revert should be allowed to lower the tier is a question for decision 1, not settled
here.

## Configs and measurements

TLC v1.7.4, 16-core Windows box, 2026-11-15, times are wall time including JVM start. No-error
configs ran with `-workers auto`; counterexample configs with `-workers 1`, so the printed trace
is the shortest one.

| config | tier | expect | distinct states | seconds | result |
|---|---|---|---|---|---|
| `ci-shipped.cfg` | ci | no-error | 1,740,180 | 9.7 | no error |
| `ci-baseline.cfg` (GatedDebt shape, `MaxLog = 4`, deferrals) | ci | no-error | 2,936,010 | 14.7 | no error (= GatedDebt `ci-shipped`) |
| `ci-vacuity.cfg` | ci | violated: NeverFixedAndReady | 5,285 | 1.5 | violated, 6 states |
| `ci-lowering.cfg` (`GlobB = 2`) | ci | no-error | 580,060 | 5.9 | no error |
| `ci-lowering-vacuity.cfg` | ci | violated: NeverLoweredAndReady | 22,430 | 2.2 | violated, 8 states |
| `deep-shipped-maxlog4.cfg` (`MaxLog = 4`, no raise) | deep | no-error | 12,761,372 | 53.7 | no error |
| `deep-lowering-maxlog4.cfg` (`GlobB = 2`, `MaxLog = 4`) | deep | no-error | 12,761,372 | 55.7 | no error |
| `deep-shipped-defers.cfg` (`Defers = TRUE`) | deep | no-error | 52,299,000 | 213.8 | no error |
| two tools, fix on, `MaxLog = 4` (no `.cfg` kept) | -- | no-error | -- | -- | **UNMEASURED**: stopped past 134 M states / 16 min |
| `deep-two-tools-vacuity.cfg` | -- | violated: NeverFixedAndReadyStandard | 561,514 | 8.8 | violated, 9 states |
| `tooth-as-written-honest.cfg` | -- | violated | 10,796 | 1.7 | violated, 7 states |
| `tooth-as-written.cfg` | -- | violated | 14,346 | 1.8 | violated, 7 states |
| `tooth-without-cover.cfg` | -- | violated | 5,326 | 1.4 | violated, 6 states |
| `tooth-without-locate.cfg` (`MaxLog = 4`) | -- | violated | 48,723 | 2.5 | violated, 8 states |
| `tooth-without-rereview.cfg` (`MaxLog = 4`) | -- | violated | 69,467 | 2.6 | violated, 9 states |
| `tooth-any-tool-rereview.cfg` (two tools, `MaxLog = 4`) | -- | violated | 266,312 | 5.3 | violated, 9 states |
| `ci-shipped` with `Locate = FALSE` (not kept) | -- | -- | 1,740,180 | 10.3 | no error |
| `ci-shipped` with `Rereview = FALSE` (not kept) | -- | -- | 1,740,180 | 10.7 | no error |

**Vacuity** (`ci-vacuity`, 6 states): an unwitnessed gated step (an honest count, located in `a`),
the agent fixes `a`, tool 1 reviews only `a` (clean), a test-run: `pr-ready`, in the quick tier,
through a diff-scoped review. The green is not green because nothing can happen.

**Two-tool vacuity** (`deep-two-tools-vacuity`, 9 states): in the standard tier, an unwitnessed
gated step, the agent fixes `a`, tool 1 and tool 2 each review only `a`, clean, a test-run:
`pr-ready`. At `MaxLog = 3` the two-tool shape cannot reach `pr-ready` after a gated step (a
clean step per tool, a run and the gated step are four records), which is why no two-tool
no-error config exists at that bound.

**Why these bounds.** The no-error checks of the richer shapes are past the 60 s `ci` limit on this
machine: deferrals on and `MaxLog = 4` (see the table); two tools did not finish at all. A CI
runner is slower. So the `ci` configs of the new design run `Defers = FALSE`, `MaxLog = 3` and one
tool, and the other shapes are `deep`, run by hand. Deferrals are 2.11.0's rules, already
model-checked in gate-integrity and unchanged here.

### Pending: the teeth enter the manifest with their RED cases

The six `tooth-*.cfg` files MUST break `NoFlaggedBugShips`, and they do. They are not in
`models.json` yet, because the validator refuses a counterexample config that replays no AC id,
and the AC-RP ids arrive in the next commit with the RED cases:

- `tooth-as-written-honest` and `tooth-as-written` -> pending AC-RP-nn (a clean pass over other
  files closes a finding; a lie on a tree that differs in an unrelated file escapes Memory);
- `tooth-without-cover` -> pending AC-RP-nn;
- `tooth-without-locate` -> pending AC-RP-nn;
- `tooth-without-rereview` -> pending AC-RP-nn;
- `tooth-any-tool-rereview` -> pending AC-RP-nn.

`deep-two-tools-vacuity` should join them as the two-tool vacuity control.

## Open questions for the ADR

- **Should convergence verify the whole-change first pass, per tool?** Decision 2 says the first
  cycle runs every tool of the tier over the whole change. As modelled, convergence never checks
  that it happened: C1 accepts any clean pass, and `ci-vacuity` converges with no whole-change
  review at all (`b` is never reviewed). The stricter rule was not checked.
- **Should C2 and the latest-step check count only tools of the tier?** (finding 3,
  any-tool-rereview.)
- **Should a revert be allowed to lower the tier?** (finding 4.)

## Limits of the abstraction

- **A fix that breaks a file it did not touch is seen only by the tests** (the risk the ADR
  states itself). In this model `b` is never buggy, and the rule covers only what a tool reported.
  The model says nothing about a bug no tool flagged, so nothing about coverage.
- **The model takes two things from the ground truth that the agent would narrate in the engine:**
  a finding's file (`Locate`) and a step's scope (which `CoverFix` and C2 read). The lying agent
  can lie about a count, but never put a finding in the wrong file or claim a scope it did not
  review. In the engine the path and, if `log-step` carries it, the scope are narrated like every
  count -- and today's review-start records only a whole-tree stamp, not a scope. A wrong path or
  scope is a hole this model does not have.
- **Without `Locate`, a whole-change gated step is "known" only for that exact tree.** An unrelated
  edit makes the finding unknown to the rule, in the baseline (GatedDebt) too: versions are opaque
  there.
- **The scope is the agent's choice.** The ADR says the engine runs the tools "over the files
  changed since". The model lets the agent pick any files instead, a superset of those behaviours.
- **The latest step stands for the latest cycle** in quick/standard (2.15.1's Anchor reads "the
  tools of the cycle"). **The model allows ONE pending review in total** (a single `pending`),
  across all tools; the engine allows several concurrent reviews.
- **Small domains.** Two files with binary contents, one buggy content, only in a quick file. A
  finding located in a file is a single fact; in the engine a file holds several findings, and
  `Locate` would key on id + path.
- **Deferral is the 2.11.0 bit, not ADR-060's per-id deferral**, the same as GatedDebt.
- **Not modelled:** the round cap (decision 3; it adds a counter and no safety property), repeats
  and yield (decisions 4-5), escapes per layer (decision 6), and linters run once as a gate.

## Reproduce

```sh
python tools/model-check.py check                                   # no Java
python tools/model-check.py run --tier ci --jar tla2tools.jar       # TLC, pinned sha256
python tools/model-check.py run --tier deep --jar tla2tools.jar --timeout 600   # by hand
# the teeth, outside the manifest until their AC ids exist (-workers 1: shortest trace):
cd docs/review-pace/models
java -cp tla2tools.jar tlc2.TLC -workers 1 -config tooth-as-written-honest.cfg -metadir <tmp> ReviewPace.tla
```
