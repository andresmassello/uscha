---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/.claude/skills/uscha-devloop/SKILL.md
  - uscha-kit/skills/uscha-devloop/SKILL.md
  - uscha-kit/.claude/skills/uscha-discovery/SKILL.md
  - uscha-kit/skills/uscha-discovery/SKILL.md
  - uscha-kit/templates/CONSTITUTION.md
---
# ADR-046: Field truth for greenfield — a REAL-INPUT corpus is an evidence class, measured as a gate the project declares

## Status: Proposed

## Context

A field report, from a live greenfield build:

> The parser passed every test the agent wrote, and it was wrong. Running it over the REAL
> corpus is what exposed it: 96.96 % before the fix, 99.645 % after.

Every test payload in that project had been invented by the agent that wrote the code. That is
not a failure of discipline — it is the ordinary condition of greenfield work. There is no
production traffic to sample, no legacy system to characterize, and the same mind that decided
what the code should do also decided what the tests would feed it. A suite built that way can be
green over the whole input space the author imagined and silent about the one the world produces.

The kit already has an instrument for the OTHER half of this problem. `characterize` and
`golden-diff` implement one clear doctrine — *the old code is the truth* — and they are the right
tools whenever there is old code. In greenfield there is none, so that doctrine has nothing to
grip: `uscha-characterize` is explicitly a brownfield front, and `uscha-discovery` (the greenfield
front) has, until this ADR, no notion of field truth at all. The methodology can measure whether
the agent kept its own promises. It cannot measure whether those promises were about the real
world.

That gap is what the field report found, and the number is the point: 96.96 % is not a number any
invented suite would ever have produced. Only real inputs produce it.

## Decision

**A REAL-INPUT corpus becomes a first-class evidence class, run by the engine, scored as a
percentage, and persisted through the same FACT-gate machinery every other gate uses.**

### 1. `corpus-run` — the subcommand

```
qa_ledger.py corpus-run --repo R --corpus path.jsonl --command "<cmd>" \
             [--threshold P] [--ac AC-FIELD-01] [--timeout S] [--max-misses K] [--json]
```

The corpus is **JSONL**: one JSON object per line, `input` and `expected` required, `id`
optional (positional `case-NNN` when absent). Each case runs the command once with the input on
its **stdin** — verbatim when it is a string, JSON-encoded (`sort_keys`) otherwise — and the
trimmed **stdout** is compared to `expected`: string compare first, then JSON-equal when BOTH
sides parse as JSON, so a command that reorders an object's keys is not a false miss while a
command that prints prose is compared as prose. A non-zero exit is a miss named with its code.

**Determinism is part of the contract.** File order IS run order, so the same corpus reports the
same misses in the same places; a per-case `--timeout` (default 30 s) turns a hang into a miss
NAMED `timeout` instead of an unbounded wait.

**Refusal beats a guess.** A corpus that is missing, empty, or carries a malformed line is
**exit 2**, naming the file and the LINE NUMBER. The failure mode this closes is the obvious one:
an unreadable corpus scored as 0 % is an unmeasurable input reported as a measured catastrophe,
and 0 cases scored as 100 % is the same lie with the sign flipped.

### 2. The threshold is the project's, and with none the run is ADVISORY

`--threshold`, else `repos[R].corpus_threshold`, else `defaults.corpus_threshold`. With **none of
the three declared**, the run is ADVISORY: the percentage is measured and persisted, it gates
nothing, it caps nothing, and it never joins the `N ok` count in the gates line.

This is ADR-043's posture applied on the day the feature ships. A gate needs a budget the project
ADOPTED; a percentage the kit picked for you is an opinion wearing an exit code. Nobody but the
project knows whether 99.6 % is excellent or unacceptable for its domain.

With a threshold declared, `gate:corpus` is a FACT gate like any other: `fail` is a BLOCKER —
readiness capped ≤ 65, convergence blocked — and a later green run clears it (latest-per-tool
wins). No parallel mechanism was built; the record is the same static-gate shape `gate-check`
writes, so every reader downstream already understands it.

### 3. `log-gate --kind corpus` for parity, and it accepts `advisory`

A corpus measured somewhere else (a CI job, a nightly) can be recorded through the existing door:
`log-gate --kind corpus --verdict pass|fail|advisory|not-run`. `corpus` joins
`ADVISORY_CAPABLE_KINDS` — the third member, after `simplicity` and `waste` — for a reason
specific to it: **`corpus-run` itself runs advisory whenever no threshold is declared.** Refusing
the verdict on the parity door while the check emits it on the other would leave one fact with two
incompatible records, and the parity door could only spell an unbudgeted run as `pass` — the exact
false clean ADR-043 exists to refuse. The closed vocabulary is otherwise untouched: `ci`,
`gate-check` and every other FACT kind still refuse `advisory`.

### 4. A green corpus run closes an acceptance criterion MEASURED

`--ac AC-FIELD-01` stamps criterion ids on the persisted record. Readiness then closes a criterion
MEASURED when its only evidence is a corpus record **iff that record passed** — the same rule the
JUnit path has always obeyed, for the same reason:

- an **advisory** run measured a percentage against no adopted budget; it is not a green gate, and
  letting it read as one is the ADR-043 defect again;
- a **failing** run is evidence AGAINST, not absence of evidence;
- **red JUnit evidence still vetoes**, whatever the corpus says. Fail-closed did not move.

A ticked `AC-FIELD-01` with no green corpus record reports `narrated_only`, exactly as a ticked
criterion with no green testcase always has. The checkbox is narration; the run is the fact.

**Amended in the 2.2.0 fresh review — a failing run VETOES, it does not merely abstain.** "Evidence
AGAINST" was written above and only half implemented: the failing record stopped *closing* the
criterion, and a green `AC-n` testcase in the reports went on closing it anyway. The field had
refuted exactly what the suite was affirming, and the suite won by default. A failing corpus record
carrying `--ac AC-n` now vetoes `AC-n` outright, the same rule a red testcase and a failed tagged
smoke check obey, in that order: red JUnit → smoke veto → corpus veto → a green closes.
`readiness --json` gains `acceptance.corpus_vetoed` beside `corpus_closed`, because which ids a
veto is holding open is the half no reader can infer from the closed list. An **advisory** run is
still neither: it measured against no adopted budget and it moves nothing, in either direction.

### 5. Readiness gets a `field` line — and no weight

One conditional line per repo that declares a corpus (`repos[R].corpus`) or has ever run one:

```
--- field backend-api: corpus 66.7 % (2/3) < 90 % FAIL
--- field backend-api: corpus 99.6 % (996/1000) >= 90 % PASS
--- field backend-api: corpus 66.7 % (2/3) — no threshold declared, ADVISORY (measured, not gating)
--- field backend-api: corpus UNMEASURED — a corpus is declared and was never run (real/corpus.jsonl)
```

A record written through the `log-gate --kind corpus` PARITY door carries no run to read back,
so it produces no line and no `field` entry — it gates like any other record, and it is excluded
from this readout exactly as the smoke parity door is excluded from its own. Rendering it anyway
printed `corpus None % (None/None) >= None % PASS`: a sentence shaped like a measurement over
nothing measured.

plus a conditional `field` object in `--json`. **A repo that declares no corpus and ran none
prints nothing and emits nothing** — the same conditional-silence rule `lifecycle` (ADR-040) and
`agent_origin` (ADR-044) follow, so every existing project's readiness output is byte-identical to
what it was.

The `field` **dimension** and its weight are **deliberately not here** and are deferred to their
own ADR. Adding a weighted dimension moves every existing project's score on upgrade, and it must
be argued and measured on its own, not smuggled in beside the instrument that would feed it. The
line reports; a failing corpus already blocks through its `gate:corpus` record.

### 6. Discovery asks the question on day one

The discovery skill's domain round gains a MANDATORY question: *what input comes from the real
world, and where is the corpus?* No corpus on day 1 is not a blocker — it is a **HIGH** risk in
`RISKS.md` with an owner. The finding that produced this ADR was not "we ran the corpus late"; it
was "nobody asked whether one existed", and a question nobody asks is a gap nobody sees.

## Consequences

- **Greenfield gets an evidence class it did not have.** The one number that can contradict a
  green suite is now measurable, persistable and reviewable.
- **Nothing existing changes.** No new weight, no new cap, no new default threshold. A project
  that declares no corpus sees the same readiness text and the same JSON payload it saw before,
  plus one additive `acceptance.corpus_closed` key.
- **`ADVISORY_CAPABLE_KINDS` grows by one, and the reason is on the record.** It is the third
  member, admitted because the check's own default mode is advisory — not because corpora are
  important. Importance never earned anything a gate in this kit.
- **The `field` dimension is owed.** This ADR ships the instrument and explicitly defers the
  weight. That order is the house rule: measure first, re-claim after — under-claim, then wire,
  then re-claim.
- **AC closure through the corpus is FULL, not stamp-only.** The stamp and the readiness closure
  both ship, because the existing `_ac_closed` seam took one extra branch to widen. Had it taken
  more, the honest half (stamp plus `narrated_only`) would have shipped alone.

## What this ADR does NOT decide

- It does not add a `field` readiness dimension or move any weight. Separate ADR.
- It does not pick a default threshold. A budget is declared, never defaulted.
- It does not sample, generate or synthesize a corpus. The engine RUNS real inputs; where they
  come from is the project's problem, and an invented corpus would recreate the exact failure
  this ADR exists to catch.
- It does not diff or score partial matches. A case hits or it misses; a similarity score is a
  judgment, and judgments do not gate (INV-ADVISORY-01).
- It does not touch `characterize` or `golden-diff`. Brownfield keeps its doctrine; this is the
  greenfield counterpart, not a replacement.
- It does not run the corpus automatically in the loop. A corpus can be large and slow; when to
  run it is the project's scheduling decision, like `pit-check`.

## What is measured (`AC-CO-01..11`)

Smoke **T163**, nine criteria, over real temp projects and the real engine:

1. `AC-CO-01` — a 3-case corpus with 2 hits and `--threshold 90` exits 1 and persists a
   `gate:corpus` record reading 66.7 % (2/3), gated, not advisory, with the miss named — and
   readiness shows it as `FAIL` in the text line and in `--json`.
2. `AC-CO-02` — a ticked `AC-FIELD-01` with no run reports `narrated_only`; a GREEN tagged run
   closes it measured and attributes it in `acceptance.corpus_closed`; a later FAILING tagged run
   REOPENS it.
3. `AC-CO-03` — a declared-but-never-run corpus reads `UNMEASURED`, a repo that declares none
   produces no field entry and no field line, and a project with no corpus anywhere is silent.
4. `AC-CO-04` — with no threshold anywhere the run is ADVISORY, exits 0, and the gates line reads
   `0 ok · 1 advisory` — never inside the ok count; plus the precedence ladder measured end to
   end (flag beats repo beats defaults).
5. `AC-CO-05` — a missing, empty, malformed or key-less corpus REFUSES at exit 2 naming the line,
   and persists NO record.
6. `AC-CO-06` — a case past `--timeout` is a miss named `timeout`; a non-zero exit is a miss named
   with its code.
7. `AC-CO-07` — the CONTROL PAIR: a passing corpus caps nothing (score 99.0), and a failing one on
   another repo caps the same ledger at exactly 65 with `BLOCKER` named as the reason.
8. `AC-CO-08` — `log-gate --kind corpus` accepts pass/fail/advisory/not-run and a fail blocks;
   `--kind ci` still refuses `advisory` (the closed vocabulary did not open).
9. `AC-CO-09` — the **red probe**: the `v2.1.0` engine has neither the subcommand, nor the
   `--kind`, nor the `field` block. Without git or the tagged copy it reports `None` = UNMEASURED,
   never a silent pass.

A second, unshipped probe was run during development: breaking the comparison so every case hits
turns `AC-CO-01`, `-02`, `-04` and `-07` red. The block measures the comparison, not its own
scaffolding.

## Alternatives considered

- **Add the `field` dimension now, weighted 10.** Rejected for this release. It changes every
  existing project's score the moment they upgrade, for a dimension none of them has data for —
  the same "the kit decided your budget" defect ADR-043 removed from `simplicity-check`.
- **Default the threshold to something sensible (95 %, 99 %).** Rejected. Sensible for whom? A
  parser and a recommender do not share a bar, and a default that gates is an opinion with an exit
  code.
- **Extend `golden-diff` instead of adding a subcommand.** Rejected: golden-diff is `.received`
  vs `.approved` under INV-GOLDEN-01, where the human APPROVES the artifact. A corpus is not
  approved by a human — it is collected from the world, and its expected outputs come with it.
  Overloading one with the other would have blurred the invariant that makes goldens trustworthy.
- **Score partial/fuzzy matches so a near-miss counts.** Rejected: a similarity threshold is a
  judgment, and INV-ADVISORY-01 keeps judgments out of gates. Hit or miss is mechanical.
- **A corpus of one row per file (a directory of cases) instead of JSONL.** Rejected: thousands of
  small files is a worse ergonomic than one appendable file, and JSONL is what field pipelines
  already emit.
- **Score an empty or unreadable corpus as 0 %.** Rejected outright — this is the whole
  UNMEASURED-is-not-zero discipline of AC-03 and of the coverage dimension, and a corpus is the
  place where a silent 0 % would be most convincing and most wrong.
- **Make the discovery question advisory rather than mandatory.** Rejected: the field finding was
  precisely that nobody asked. A question the round may skip is a question that gets skipped.
