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
