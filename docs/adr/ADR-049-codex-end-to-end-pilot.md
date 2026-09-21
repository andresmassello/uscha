---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/.claude/skills/uscha-devloop/SKILL.md
  - uscha-kit/skills/uscha-devloop/SKILL.md
  - uscha-kit/install-uscha.py
  - tools/skill-blocks/orientation-block.md
  - tools/skill-blocks/orientation-block-short.md
---
# ADR-049: A full end-to-end pilot on Codex, and the five defects it found

## Status: Accepted (2.4.0)

## Context

On 2026-09-20 the full `/uscha-devloop` cycle was run end to end on OpenAI Codex (desktop app,
GPT-5.6, kit 2.3.0) against a small greenfield Python repo with one acceptance criterion — a
greenfield pilot repo, no client or project name involved. Every prior cross-vendor result
(ADR-042) measured a SLICE of the method: a compiler, a round-trip, an archetype. This was the
first time the WHOLE loop — plan, coverage gate, build, QA, PR gate — ran unattended on a vendor
other than the one it was built against.

It worked. Six green tests, 100% line coverage, a 33-step ledger (8 snapshots; code-review x2,
judgment-day x3, improve x3, contract-test x2; simplicity and waste recorded as advisory; gate-
check x4; one spec-doubt and one spec-change-request raised and resolved through the structured
bridge, not by silently editing the SPEC), CONVERGED, the sole criterion closed as MEASURED,
stopped cleanly at the merge gate with no commit or push. ~29 minutes, 22 Codex sub-agents. Its
own judgment-day pass found a real ambiguity in the SPEC (a threshold compared before or after
rounding) and the agent asked the human instead of quietly picking one — the method's own
discipline, reproduced on a vendor it was never tuned against.

The run also surfaced five defects — none of them fatal, all of them the kind that only shows up
when the assumptions built into Claude Code's surface (a statusline, a JaCoCo-first coverage
story, a git-aware human) are not there. Each is reproduced below before its fix, per repo rule 2
(the mandatory truth-pass): a doc claim without a reproduction is a claim that was never checked.

## Decision

**1. No coverage report is UNMEASURED, not 0%.** On a fresh repo, `check-coverage` used to print
"NO coverage report found ... -> treat as BELOW" and exit 1 — the same exit and the same word
("BELOW") a real report scoring under threshold produces. The devloop SKILL's Phase 1 read "coverage
< threshold (or no report): write characterization tests", collapsing two different facts (never
measured vs. measured and failing) into one instruction. On the pilot's fresh repo this read as
"coverage is 0%, write characterization tests" for code that had simply never been run. Fixed:
`check-coverage` now exits 2 (fail-closed, the kit's existing convention for a refused reading, per
`_jacoco_result`'s audit-1.94.1 precedent) and prints `coverage UNMEASURED -- no coverage report
found`, naming the path it looked for. The SKILL now separates the two branches explicitly:
BELOW (exit 1, a real report) still means characterization; UNMEASURED (exit 2, no report) means
"run the test command with coverage first", never characterization — that path is for code nobody
has tested yet, not code that has not been run at all.

**2. `uscha init` writes a `.gitignore` when the repo has none.** Codex's fresh repo, and every
greenfield pilot repo before it, was left without one — a gap the installer had simply never
closed. `install-uscha.py`'s `cmd_init` now writes a minimal, per-repo-type `.gitignore`
(`__pycache__/`, `*.pyc`, `.pytest_cache/`, `.coverage` for python; `node_modules/` for node; and
matching minimal sets for the other `detect_repo_type` outcomes) — generated the same way
`uscha.config.json` already is: only for a RECOGNISED type, never guessed. `reports/` is NEVER in
that list, in this repo type's set or any other's — it is the ledger's own evidence directory
(JUnit, coverage, smoke), and the devloop SKILL now says so explicitly wherever it describes
evidence, right next to the coverage-generation phase. An EXISTING `.gitignore` is left
byte-identical, even with `--force` — unlike the templates `init` already copies, this one is
filled only on a repo that has none, never overwritten, so a second `init` reports it unchanged.

**3. Progress is visible on surfaces without a statusline.** The statusline and its Stop hook are
wired into `.claude/settings.json` only; on Codex nothing renders it, and the "Orientation
markers" section of the generated block assumed a surface where the operator can always see a
collapsed tool-call log to find them. Fixed in the TEMPLATE (`tools/skill-blocks/`, never the 18
rendered files by hand, per repo rule 11): both the full and short orientation-block variants now
state that on a surface with no live statusline — Codex, pi, a plain terminal — the markers are
the operator's only signal and MUST appear in the visible reply text, and the final message of
every turn on such a surface opens with the compact `uscha-status` readout (derived phase, loop,
measured acceptance, next criterion) before the breadcrumb/close marker.

**4. Closing ticks the checkbox.** The pilot's readiness read "measured but unticked: AC-1" at the
end of a converged run — the engine had already closed the criterion with a green test, and
nothing in the SKILL told the agent to reconcile the box. The devloop SKILL now instructs: for
every ID `readiness` reports as `measured_unchecked`, flip that checkbox to `[x]` in
`ACCEPTANCE.md` (the engine measured it; ticking is bookkeeping, never the reverse — a tick with
no green test stays `narrated_only`, the engine's existing, separate classification), then
re-run `readiness` and confirm the list is empty before the close block.

**5. `pr-ready` is a phase value, never a subcommand.** While reading the pilot's ledger the OPERATOR
typed `qa_ledger.py pr-ready` and hit an argparse error -- the agent never did; the correct form has always been `phase --repo R
--require pr-ready`. An audit of every doc, skill, README, ADR and deck in the repo (AC-CX-06)
found the phrasing already correct everywhere it is documented — the confusion lived in the
agent's own recall of the command, not in a doc that taught it wrong. The devloop SKILL's PR
phase now states the rule explicitly and by name, immediately beside the command, so the negative
case is written down rather than merely never written wrong.

## Consequences

- Coverage semantics change for every caller of `check-coverage`: a repo with no report now exits
  2 where it used to exit 1. Anything scripted against the old "1 = not ready" contract needs to
  treat 2 as its own case (UNMEASURED) rather than folding it into "below".
- `uscha init` now writes one more file. Existing repos re-running `init` are unaffected (their
  `.gitignore`, if any, is left alone); a fresh repo gets a small, honest starting point instead
  of none.
- The orientation block grew by a few lines in all 18 rendered `SKILL.md` files; `doctor`'s
  version-marker mechanics (ADR-045) are untouched.
- This is measurement of ONE run, on ONE tiny repo, on ONE model, with hooks absent (the golden
  write guard, ADR-INV-GOLDEN-01, is not enforced on Codex — there is no hook surface there) and
  no live statusline (fix 3 is the mitigation, not a replacement). It does not establish that the
  method holds at scale on Codex, only that the five gaps this run found are now closed.

## What this ADR does NOT decide

- It does not claim hooks work on Codex, or plan to build a Codex-native hook surface. That
  remains an open gap, named rather than hidden.
- It does not change the coverage THRESHOLD or any risk-profile default — only what an ABSENT
  report reports.
- It does not make `.gitignore` generation cover every conceivable toolchain; only the repo types
  `detect_repo_type` already recognises.
- It does not claim the statusline visible-reply rule is enforced mechanically on every surface —
  it is an instruction in the rendered prose, measured by its presence, not by intercepting what a
  given agent actually sends back to its own operator.

## What is measured (`AC-CX-01..07`)

T167, through the `.cx-cases.json` sidecar:

- **AC-CX-01** — `check-coverage` on a repo with no report exits 2 and reads UNMEASURED, never
  BELOW; the control (a real, low-coverage report) still exits 1.
- **AC-CX-02** — `init` writes a scoped `.gitignore` for a python repo (`__pycache__/`, `*.pyc`,
  ...) and no PATTERN line in it ever names `reports`.
- **AC-CX-03** — an existing `.gitignore` is left byte-identical (even under `--force`), and a
  second `init` reports it `unchanged`.
- **AC-CX-04** — every rendered `SKILL.md` (both skill trees) carries the no-statusline rule, and
  `gen-skill-blocks.py --check` is green.
- **AC-CX-05** — the devloop `SKILL.md` (both mirrors) carries the tick-on-close rule and the
  reports-are-evidence rule, pinned by a stable phrase.
- **AC-CX-06** — no gated doc (every `SKILL.md`, both READMEs, `ACCEPTANCE.md`, the FIRST-USE
  twins, the deck twins) presents `pr-ready` as if it were its own subcommand, excluding lines that
  name the anti-pattern explicitly to warn against it.
- **AC-CX-07** — the RED PROBE: the v2.3.0 installer, run out of git via `git archive`, writes no
  `.gitignore` for the same fresh repo the current installer does. `None` (no git, a shallow
  clone, an extracted kit) is UNMEASURED, never a silent pass.

## Alternatives considered

**Treat "no report" and "below threshold" as the same signal, and fix only the SKILL prose.**
Rejected: the engine's own exit code and message were the thing an agent actually reads before the
SKILL's prose ever gets consulted; leaving them conflated would have left the fix advisory rather
than structural, exactly the gap ADR-012's "no derived fact behind a claim" lineage exists to
close.

**Ship a Codex-specific SKILL variant instead of one generated block covering both.** Rejected:
the orientation block is already the kit's one generated region (ADR/repo rule 11) precisely so a
divergent per-surface copy never has the chance to drift; a Codex branch would be exactly that
copy, one release early.

**Gate on the tick-on-close rule (refuse `pr-ready` while any box is measured-unchecked).**
Rejected: `readiness` already caps and blocks on the facts that matter (tests red, BLOCKER/CRITICAL
open, unresolved escalation); an unticked box that the ledger has already closed is bookkeeping,
not a risk, and gating on it would have punished exactly the honest case this fix documents.
