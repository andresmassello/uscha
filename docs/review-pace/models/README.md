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
  or the tier the agent raised it to. With `TierHighWater` (the owner's decision, on in every
  fixed config) it is the highest tier the change EVER reached, so reverting `b` does not lower
  it; without it the touched set is derived from the tree now and a revert lowers the tier.
  quick runs tool 1; standard and deep run every tool.
- Diff scope: the agent picks the files of every review (the engine does not stop it; it only
  reads what was logged). In quick/standard, convergence is C1 (every tool of the tier has had one
  clean pass) and C2 (every file changed after a tool's clean pass has been reviewed clean again);
  the latest step must be clean and on the tree on disk (Anchor); with `WholeFirstPass`, every tool
  of the tier also had a review of the whole change; with `TierTools`, C2's re-review and the step
  Anchor reads count only tools of the tier. In deep it is today's rule, plus "each tool's last
  review covered the whole change".
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

### 3. The owner's three rules after the model (2026-11-15)

- **`WholeFirstPass`**: in quick/standard, every tool of the tier must have a witnessed review
  whose scope was the whole change, in addition to C1 and C2.
- **`TierTools`**: C2's re-review and the latest step Anchor reads count only tools of the tier.
- **`TierHighWater`**: the tier is the highest the change ever reached; reverting a deep-glob file
  does not lower it (only a human lowers a tier).

All three are on in `ci-shipped`, the lowering configs and the deep configs. **None of them is
needed for `NoFlaggedBugShips` at the bounds checked**, so none has a safety tooth. Their value is
coverage and policy, and each gets a property that shows the difference:

| rule | safety with it OFF | property | with it ON | with it OFF |
|---|---|---|---|---|
| `WholeFirstPass` | no error, 1,740,180 states (`ci-shipped` shape) | `EveryFileReviewed`: at `pr-ready` every tool of the tier reviewed every file | `ci-every-file`: no error, 1,740,180 states | `tooth-without-whole-pass`: violated, 4 states |
| `TierHighWater` | no error, 580,060 states (`ci-lowering` shape) | `LoweredNeverReady`: a change that touched the deep file converges only on the deep rule | `ci-lowering-policy`: no error, 600,556 states | `tooth-without-highwater`: violated, 7 states |
| `TierTools` | with `SameTool` on: no violation found, UNMEASURED (two tools, `MaxLog = 4`, stopped at 53 M states / 240 s) | `TierAnchored`: the latest step of a tool OF THE TIER saw the tree on disk | -- | no violation found, UNMEASURED (stopped at 16.6 M states / 300 s, one worker) |

- **without-whole-pass** (4 states): tool 1 reviews `a` alone (truly gated), a test-run, and the
  review is logged clean: `pr-ready` with `b` never reviewed by any tool. (No finding is known to
  the ledger, so `NoFlaggedBugShips` has nothing to say.)
- **without-highwater** (7 states): the agent edits `b` (deep), a test-run, reverts `b` (quick
  again), a whole-change review (truly gated) is logged clean, a test-run: `pr-ready` on the quick
  rule for a change that touched a deep file.
- **TierTools adds nothing measured beyond `SameTool`.** With `SameTool` off, it moves the
  shortest counterexample from the quick tier (9 states, tool 2 outside the tier clears the file)
  to the standard tier (10 states, tool 2 inside the tier clears it): `SameTool` stays necessary.
  With `SameTool` on, neither `NoFlaggedBugShips` nor `TierAnchored` broke without `TierTools` in
  the runs that could be afforded; those runs did not finish, so this is not a proof of
  redundancy.

### 4. Necessary vs checked sufficient -- at which bounds

Necessary for `NoFlaggedBugShips` (each one's absence is a counterexample; `-workers 1`):

| dropped | config | bound | shortest trace |
|---|---|---|---|
| `CoverFix` (with `Locate`) | `tooth-without-cover` | `MaxLog = 3`, 1 tool | 6 states, lying agent |
| `Locate` (with `CoverFix`) | `tooth-without-locate` | `MaxLog = 4`, 1 tool | 8 states, lying agent |
| C2 (with both) | `tooth-without-rereview` | `MaxLog = 4`, 1 tool | 9 states, no lie |
| `SameTool` (C2 as first worded) | `tooth-any-tool-rereview` | `MaxLog = 4`, 2 tools | 10 states, no lie |

The three owner rules stay on in these teeth; the as-written teeth turn everything new off.

Checked sufficient (no error), and only at these bounds:

- every rule on, **one tool**: `MaxLog = 3` with raises to deep (`ci-shipped`, `ci`), `MaxLog = 4`
  (`deep-shipped-maxlog4`, by hand), `MaxLog = 3` with deferrals (`deep-shipped-defers`, by hand),
  and with a deep-glob `b` (`ci-lowering` at `MaxLog = 3`, `deep-lowering-maxlog4` by hand).
- **With one tool `SameTool` and `TierTools` are inert** (there is no other tool). **With two tools
  nothing is checked sufficient**: the no-error run at `MaxLog = 4` (before the owner's rules) was
  stopped past 134 million distinct states / 16 min -- UNMEASURED.

**What CI checks today.** `ci-shipped` (`MaxLog = 3`) cannot see the `Locate`, C2 and `SameTool`
paths: with `Locate = FALSE` or `Rereview = FALSE` it still prints no error, 1,740,180 distinct
states, measured on the final module. A `MaxLog = 4` no-error config does not fit the 60 s limit:
54-64 s on this 16-core machine across runs, and a 2-4-core CI runner is slower. **Until the teeth
enter the manifest with their AC ids, CI checks only `CoverFix` and the as-written break** for the
safety rule, plus the two policy properties (`ci-every-file`, `ci-lowering-policy`); `Locate` and
C2 are checked sufficient only by hand (`deep-shipped-maxlog4`). The teeth stop in 1-17 s, so as
`ci` entries they will make CI see each rule's necessity.

The tooth stories (final module, `-workers 1`):

- **without-cover** (6): an unwitnessed gated step on `(a0, b0)` (an honest count) is located in
  `a`. The agent edits `b`, a whole-change review starts on `(a0, b1)`, a test-run, and that review
  (truly gated) is logged clean. Whole-tree debt and Memory see different trees.
- **without-locate** (8): a whole-change review starts on `(a0, b0)`. The agent edits `b`, a
  test-run, and an unwitnessed gated step is logged on `(a0, b1)`, covering its whole scope. The
  pending review (truly gated) is logged clean: it covered both files and `b` moved, so the debt
  closes. Tool 1 then reviews only `b` (clean). Memory does not fire: that review did not cover
  every file the gated step covered.
- **without-rereview** (9): the agent fixes `a`, a whole-change review starts on `(a1, b0)`. The
  agent reverts `a`, a test-run, and an unwitnessed gated step is logged on `(a0, b0)`, located in
  `a`. The stale review is logged clean: it covers `a`, and `a` moved, so the debt closes. Tool 1
  reviews only `b` (clean). Anchor holds and Memory does not fire. `a` changed after its clean pass
  and nothing re-reviewed it: C2 refuses exactly this.
- **any-tool-rereview** (10): the agent raises the tier to standard; the same run as above, then
  **tool 2** (in the tier) reviews the whole reverted change, honestly clean -- tool 2 never flags.
  That satisfies C2 "by at least one agent tool", and Memory (per tool) does not fire for tool 2.

### 5. Lowering the tier by a revert (`GlobB = 2`)

With `b` on a deep glob, touching `b` makes the change deep. Without `TierHighWater`, reverting `b`
made it quick again, and `NoFlaggedBugShips` still held (580,060 states, `MaxLog = 3`): the debt
and Memory are read for every tool that ever logged, so a lower tier removes reviews, not
knowledge. With `TierHighWater` the tier stays deep: `ci-lowering` (600,556 states) and
`deep-lowering-maxlog4` read no error, and `ci-lowering-policy` shows the change never converges on
the quick rule. The lowering vacuity control is now `NeverRevertedAndReady`, which MUST break and
does (`ci-lowering-vacuity`, 8 states): the agent edits `b` (deep), an unwitnessed gated step, the
agent fixes `a` and reverts `b`, tool 1 reviews the whole change clean, a test-run: `pr-ready`, on
the deep rule. In this model the bug is in `a`, a quick file, so a finding inside the deep file is
not checked.

## Configs and measurements

TLC v1.7.4, 16-core Windows box, 2026-11-15, final module, times are wall time including JVM
start. No-error configs ran with `-workers auto`; counterexample configs with `-workers 1`, so the
printed trace is the shortest one.

| config | tier | expect | distinct states | seconds | result |
|---|---|---|---|---|---|
| `ci-shipped.cfg` | ci | no-error | 1,740,180 | 9.9 | no error |
| `ci-baseline.cfg` (GatedDebt shape, `MaxLog = 4`, deferrals) | ci | no-error | 2,936,010 | 9.6 | no error (= GatedDebt `ci-shipped`) |
| `ci-vacuity.cfg` | ci | violated: NeverFixedAndReady | 14,193 | 1.7 | violated, 7 states |
| `ci-every-file.cfg` | ci | no-error (EveryFileReviewed) | 1,740,180 | 10.1 | no error |
| `ci-lowering.cfg` (`GlobB = 2`) | ci | no-error | 600,556 | 4.6 | no error |
| `ci-lowering-policy.cfg` | ci | no-error (LoweredNeverReady) | 600,556 | 4.6 | no error |
| `ci-lowering-vacuity.cfg` | ci | violated: NeverRevertedAndReady | 23,901 | 1.8 | violated, 8 states |
| `deep-shipped-maxlog4.cfg` (`MaxLog = 4`, no raise) | deep | no-error | 12,761,372 | 58.6 | no error |
| `deep-lowering-maxlog4.cfg` (`GlobB = 2`, `MaxLog = 4`) | deep | no-error | 12,986,842 | 57.6 | no error |
| `deep-shipped-defers.cfg` (`Defers = TRUE`) | deep | no-error | 52,299,000 | 253.9 | no error |
| `deep-two-tools-vacuity.cfg` | -- | violated: NeverFixedAndReadyStandard | 561,986 | 9.0 | violated, 9 states |
| `tooth-as-written-honest.cfg` | -- | violated | 10,796 | 1.4 | violated, 7 states |
| `tooth-as-written.cfg` | -- | violated | 14,346 | 1.4 | violated, 7 states |
| `tooth-without-cover.cfg` | -- | violated | 5,368 | 1.3 | violated, 6 states |
| `tooth-without-locate.cfg` (`MaxLog = 4`) | -- | violated | 48,723 | 2.2 | violated, 8 states |
| `tooth-without-rereview.cfg` (`MaxLog = 4`) | -- | violated | 76,029 | 2.6 | violated, 9 states |
| `tooth-any-tool-rereview.cfg` (two tools, `MaxLog = 4`) | -- | violated | 1,070,972 | 16.6 | violated, 10 states |
| `tooth-without-whole-pass.cfg` | -- | violated: EveryFileReviewed | 186 | 1.0 | violated, 4 states |
| `tooth-without-highwater.cfg` | -- | violated: LoweredNeverReady | 6,350 | 1.3 | violated, 7 states |
| `ci-shipped` with `Locate = FALSE` (not kept) | -- | -- | 1,740,180 | 9.8 | no error |
| `ci-shipped` with `Rereview = FALSE` (not kept) | -- | -- | 1,740,180 | 10.1 | no error |
| `ci-shipped` with `WholeFirstPass = FALSE` (not kept) | -- | -- | 1,740,180 | 10.1 | no error |
| `ci-lowering` with `TierHighWater = FALSE` (not kept) | -- | -- | 580,060 | 4.1 | no error |
| two tools, `SameTool` on, `TierTools = FALSE`, `MaxLog = 4` (not kept) | -- | -- | -- | -- | UNMEASURED: stopped at 53 M states / 240 s |
| the same, invariant `TierAnchored`, one worker (not kept) | -- | -- | -- | -- | UNMEASURED: stopped at 16.6 M states / 300 s |
| two tools, fix on, `MaxLog = 4`, before the owner's rules (not kept) | -- | -- | -- | -- | UNMEASURED: stopped past 134 M states / 16 min |

`ci-every-file` and `ci-lowering-policy` expect no error on a policy property
(`EveryFileReviewed`, `LoweredNeverReady`), not on the safety rule.

**Vacuity** (`ci-vacuity`, 7 states): tool 1 reviews `a` alone (gated), the agent fixes `a`, a
test-run, the gated step is logged, tool 1 reviews the whole change (clean): `pr-ready`, in the
quick tier. The old 6-state trace (no whole-change review) is no longer reachable, as expected with
`WholeFirstPass`; the new legitimate path includes the whole-change pass, and the diff-scoped
review is the gated one.

**Two-tool vacuity** (`deep-two-tools-vacuity`, 9 states): the agent raises the tier to standard,
an unwitnessed gated step, the agent fixes `a`, tool 1 and tool 2 each review the whole change,
clean, a test-run: `pr-ready`. At `MaxLog = 3` the two-tool shape cannot reach `pr-ready` after a
gated step, which is why no two-tool no-error config exists at that bound.

**Why these bounds.** The no-error checks of the richer shapes are past the 60 s `ci` limit on this
machine: deferrals on and `MaxLog = 4` (see the table); two tools did not finish at all. A CI
runner is slower. So the `ci` configs of the new design run `Defers = FALSE`, `MaxLog = 3` and one
tool, and the other shapes are `deep`, run by hand. Deferrals are 2.11.0's rules, already
model-checked in gate-integrity and unchanged here.

### Pending: the teeth enter the manifest with their RED cases

The six safety `tooth-*.cfg` files MUST break `NoFlaggedBugShips`, and the two policy teeth MUST
break their property; they do. They are not in `models.json` yet, because the validator refuses a
counterexample config that replays no AC id, and the AC-RP ids arrive in the next commit with the
RED cases:

- `tooth-as-written-honest` and `tooth-as-written` -> pending AC-RP-nn (a clean pass over other
  files closes a finding; a lie on a tree that differs in an unrelated file escapes Memory);
- `tooth-without-cover`, `tooth-without-locate`, `tooth-without-rereview`,
  `tooth-any-tool-rereview` -> pending AC-RP-nn;
- `tooth-without-whole-pass`, `tooth-without-highwater` -> pending AC-RP-nn.

`deep-two-tools-vacuity` should join them as the two-tool vacuity control.

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
