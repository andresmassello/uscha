---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/.claude/skills/uscha-devloop/SKILL.md
  - uscha-kit/skills/uscha-devloop/SKILL.md
  - uscha-kit/.claude/skills/uscha-discovery/SKILL.md
  - uscha-kit/skills/uscha-discovery/SKILL.md
  - uscha-kit/templates/CLAUDE.md
  - uscha-kit/templates/docs/adr/README.md
---
# ADR-044: The agent asks for DECISIONS, never for INFORMATION — and a decision the human never made carries `origin: agent` until they confirm it, item by item

## Status: Proposed

## Context

Two field findings arrived from opposite directions and turned out to be the same rule seen
from either end.

**Finding A — a decision entered scope without ever being made.** The agent read a global
default ("artifacts are written in English"), and turned it into a tree-wide rename: a NEW
acceptance criterion, a NEW `HANDOFF.md` rule, and two NEW ADR decision items, none of which any
human had answered. They were approved *by rebound* — they sat inside a twenty-item summary that
the human said "ok" to — and the work was cancelled after **112 files had already been renamed**.
The same pattern, smaller and just as real, in a security fix: the agent moved a stack trace to
`DEBUG` because that is generally good practice, inside a change whose scope was something else.

Neither is a hallucination. Both are *reasonable* proposals. That is exactly what makes them
dangerous: a defensible item, written in the same voice as the items the human did decide,
becomes indistinguishable from them the moment the conversation scrolls away. The artifact
records WHAT was decided and never WHO decided it, so the provenance is lost in the writing.

**Finding B — the agent asks for what it can read.** The devloop SKILL's rule 5 told the agent
that before modifying any tracked `.md` it must *"ask the human for the current version first"*.
The current version of a tracked file is in the tree. Asking for it produces a round trip whose
answer the agent could have obtained by opening the file — and, worse, it trains both sides that
questions are cheap ceremony, which is precisely the habit that makes a real question (finding A)
easy to answer with a distracted "ok".

The kit already has the doctrine both findings need, in a different domain. ADR-043 (2.1.0) drew
the line between a **requirement** the human declared and an **opinion** the kit defaulted to,
and refused to let the second wear the first's exit code. Findings A and B are that same line
drawn through the *conversation*: what the human decided, and what the agent decided for them.

## Decision

**One rule: the agent asks for DECISIONS, never for INFORMATION.**

### 1. Information is READ, never asked

Anything the tree holds — the current version of a tracked file, what a config says, whether a
test exists, which ADRs are accepted — is read. Devloop rule 5 is rewritten to say so: read the
tracked `.md` out of the tree, preserve its progress (checkboxes, notes), edit in place, never
regenerate from scratch. The *preservation* half of the old rule was always right; the *question*
was the defect, and it is removed rather than softened. The discovery SKILL's "Explore instead of
asking" is restated in the same vocabulary so the two skills say one thing.

This half costs nothing and removes a question. It is not the interesting half.

### 2. A decision the agent made carries `origin: agent` until a human confirms THAT item

Every acceptance criterion, ADR decision item or `HANDOFF.md` rule that did **not** come from a
human answer carries one trailing marker on its own line:

```
- [ ] AC-12 — when X then Y. (origin: agent)
- [ ] AC-12 — when X then Y. (origin: agent, confirmed: 2026-09-07)
```

The grammar is deliberately dull: a trailing parenthesis on the item's own line, greppable with
`rg "origin: agent"`, stable across every file the method writes, and legible to a human who has
never read this ADR.

- **No marker = human origin.** That is the default, and it is what makes this adoptable: not one
  existing file is retro-tagged, so nobody has to re-audit history to start using the marker.
- **Confirmation is PER ITEM**, written as `confirmed: YYYY-MM-DD` on the same line. A
  package-level "ok" confirms nothing — that is the exact failure mode of finding A, and a rule
  that let a summary confirm twenty items would reproduce it with extra steps.
- **An unconfirmed item is not in scope.** The agent does not implement it, does not gate on it,
  and does not quote it back as agreed. It is written down so it is VISIBLE, not so it is settled.
- **A malformed `confirmed:` counts as unconfirmed and is NAMED.** `confirmed: soon`,
  `confirmed: 2026-13-40`, `confirmed:` with nothing after it — none of them is a date, and a
  typo that read as a human's approval would be the one failure this marker exists to prevent.
  This is the `<skipped/>` = UNMEASURED discipline applied to a signature.

### 3. The engine reports it, ADVISORY, and changes nothing else

`spec-check` gains one conditional line over the files it already reads plus the `ACCEPTANCE.md`
in play, `docs/adr/*.md` and `HANDOFF.md` when present:

```
  ~ origin: 2 agent-origin item(s) unconfirmed -- AC-07 (ACCEPTANCE.md:41), D-03 (docs/adr/ADR-002-x.md:57)
```

and `agent_origin: {unconfirmed: [...], confirmed: n}` in `--json`. `readiness` prints one line
of its OWN, outside the gates rollup:

```
--- origin: 2 agent-origin item(s) unconfirmed   (spec-check names them)
```

and carries the same object in `--json` when there is anything to report.

**It never changes an exit code, never caps the score, never blocks convergence, and never joins
the gates line.** That is not timidity, it is the 2.1.0 posture applied on the day the feature
ships: a gate needs a budget the project adopted, and nobody has declared one. The field author
asked for an advisory (P7) and an advisory is what this is. If projects later want it to gate,
that is a declaration they make, in a later ADR, with a criterion measuring it.

The readiness line stays OUT of the gates rollup for the reason ADR-043 gave in the other
direction: folding a thing that is not a gate into `N ok` is a false clean, and folding it into
`N blocking` would be a gate nobody declared. It is neither, so it gets its own line.

### 4. A marker inside code is documentation

A marker inside a fenced block or an inline code span is skipped. The ADR and the ACCEPTANCE
section that DEFINE this grammar quote it, and a scanner that read its own definition as a
finding would be measuring its own prose — the same reason `_lc_go_live` skips fenced blocks
(1.94.0). It also gives a writer a way to show the form without asserting it.

## Consequences

- **The provenance of every new decision is on the record**, in the artifact, where the
  conversation is not. That is the whole finding: a reader six weeks later can tell which
  criteria a human chose.
- **Confirmation costs one line per item, and it has to.** The friction IS the mechanism. An
  agent that wants fewer markers writes fewer decisions of its own, which is the behaviour
  change this ADR is buying.
- **Nothing existing changes.** No marker is added to any file in this repo or any project's, the
  engine prints nothing new on a tree that carries none, and `spec-check`'s human output on a
  marker-free tree is byte-identical to the 2.1.0 engine's (`AC-OA-05`).
- **The kit's own ACCEPTANCE for this release carries no markers**, and correctly: every
  `AC-OA-nn` below came from the field author's written request, not from the agent.
- **Devloop's principles renumber**: the golden rule moves from 6 to 7 and the new `origin: agent`
  rule takes 6. The text of the golden rule is untouched.
- **`readiness --json` gains a conditional `agent_origin` key.** Conditional, like `lifecycle`
  before it, so a project that tags nothing keeps a byte-identical payload.

## What this ADR does NOT decide

- It does not gate. No exit code, no cap, no convergence effect, no gates-line entry.
- It does not retro-tag anything. Unmarked is human-origin, permanently, by definition.
- It does not extend the marker to code, commits or PR titles. The three artifact kinds named
  above are where decisions live; a marker in a comment would be noise.
- It does not add a `--strict` mode that fails on unconfirmed items. That is a budget, and
  ADR-043's rule is that a budget is declared, not defaulted.
- It does not change `--strict`, `--acceptance`, `--rubric`, `--adr-dir` or any existing
  spec-check finding.

## What is measured (`AC-OA-01..07`)

Smoke **T160**, seven criteria, over real temp trees and the real engine:

1. `AC-OA-01` — an unconfirmed item is listed with its id and `file:line`, in the human output
   and in `--json`, and the exit code is exactly the one the same tree produced without markers.
2. `AC-OA-02` — an item with a valid `confirmed: YYYY-MM-DD` is NOT listed and IS counted in
   `agent_origin.confirmed`.
3. `AC-OA-03` — `confirmed: soon`, an impossible date and an empty value all count as
   **unconfirmed**, each named with the value that failed.
4. `AC-OA-04` — `readiness` prints its line only when N > 0, outside the gates rollup, and the
   score, the gates line and every dimension are identical to the SAME ledger with N = 0 (the
   control). Without the control the "caps nothing" half would be an assertion, not a measurement.
5. `AC-OA-05` — a marker-free tree: this engine's `spec-check` human output is **byte-identical**
   to the `v2.1.0` engine's on the same bytes. Nothing new is printed where nothing was tagged.
6. `AC-OA-06` — the **red probe**: the `v2.1.0` engine, run on the MARKED fixture out of git,
   MUST print no `origin:` section — the behaviour this release adds — while this engine prints
   it. Without git or the tagged copy it reports `None` = UNMEASURED, never a silent pass.
7. `AC-OA-07` — a markdown typo cannot hide a decision: a fence that never closes leaves the
   lines after it scanned as prose; a confirmation appended after the original tag on the same
   line is read (every marker on a line, not the first); a marker inside an HTML comment is
   documentation and skipped, like a fenced block.

## Alternatives considered

- **Make it a gate (`--strict` fails on unconfirmed items).** Rejected for this release. It is
  exactly the ADR-043 defect in a new dimension: a threshold the kit chose, stopping a project
  that never adopted it. The field author asked for an advisory, and an advisory is what a
  measurement earns before anyone has run it.
- **Structured provenance in a sidecar JSON instead of a marker in the line.** Rejected: the
  artifact and its provenance would drift apart on the first hand edit, and a human reading
  `ACCEPTANCE.md` would see no marker at all. The value here is that the tag travels WITH the
  sentence, in the file the human is already reading.
- **A whole `## Agent-origin` section per file instead of a per-line marker.** Rejected: it
  separates the item from its provenance, and confirming an item would mean moving it between
  sections — an edit that loses checkbox state, which is the failure rule 5 already forbids.
- **Retro-tag existing items as human-origin.** Rejected: 100% churn for zero new information.
  Absence of a marker is a perfectly good default, and choosing it costs one sentence.
- **Keep asking for the current version of a tracked file "to be safe".** Rejected: it is
  information, the tree answers it, and cheap questions are what made the expensive one easy to
  wave through.
- **Treat a malformed `confirmed:` as a hard error (exit 2), like `gate: true` with no budget.**
  Rejected: this whole dimension is advisory, and an advisory that can exit 2 is a gate with
  extra steps. Counting it as unconfirmed and NAMING the bad value is the honest report and the
  safe default in the same move.
- **Let the marker also mean "the agent wrote this prose".** Rejected: then everything the agent
  writes carries it and the marker means nothing. It marks a DECISION the human has not made,
  which is a much smaller and much more useful set.
