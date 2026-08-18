---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/templates/scripts/uscha_progress.py
---
# ADR-036: The instrument reads family-prefixed acceptance criteria — `AC-<FAMILY>-<n>` joins the bare `AC-<n>` in the measured pipeline, so a criterion the suite already proves stops reading as untagged

## Status: Accepted

## Context
`_AC_TAG` (JUnit testcase names) and `_AC_ID` (ACCEPTANCE checkbox ids) recognised exactly one
grammar: the bare `AC-<n>`, normalised by number (`AC-01 == AC_1 == ac1`, because python and go
test names cannot carry `-`). Everything else was invisible to the engine.

This repo's own `ACCEPTANCE.md` carries **172 criteria, 166 of them family-prefixed** across 28
prefixes (`AC-BC`, `AC-T`, `AC-DF`, `AC-FP`, `AC-SD`, …), and `uscha-kit/tests/smoke-engine.sh`
emits `reports/junit/uscha-acceptance.xml` with **172 testcases named `AC-XX-nn_<slug>`**. The
evidence existed, was captured by execution, and the instrument could not see it: `readiness`
reported *6/172 measured, 166 criteria without an AC-ID*. That number was TRUE about the engine
and false about the project — the exact gap the kit exists to close, sitting inside the kit.

ADR-035 item 6 recorded the widening as deferred, with a curated note that it must ship as its
**own engine release** because it retroactively re-counts every family prefix. This is that
release.

## Decision

**1. The canonical id grammar has two forms.**
- **Bare** — `AC-<n>`, normalised to `AC-<int>` (unchanged in every respect).
- **Family** — `AC-<FAMILY>-<n>` where `FAMILY = [A-Za-z][A-Za-z0-9]*`: at least one leading
  letter, digits allowed after it, **never purely digits**. Normalised to
  `AC-<FAMILY.upper()>-<int>`, so `AC-T-01 == AC-T-1 == ac_t_1` and `AC-BC-07 == AC-BC-7`.

A numeric "family" is not a family: `- [ ] AC-7-x` still reads as the bare `AC-7` followed by
the text `x` (the trailing-separator class eats the hyphen), exactly as it did before this change.

**2. ACCEPTANCE side (`_AC_ID` + the new `_AC_ID_FAM`, via `_ac_id_of`).**
Both forms match at the start of a checkbox body, tolerant of the same bold/backtick wrappers
and trailing separators as before. The family form is tried FIRST and the bare form is the
fallback, so every id the engine read before ADR-036 still reads the same. The item's `id`
becomes the normalised form; text stripping is unchanged.

**3. JUnit side (`_AC_TAG` + the new `_AC_TAG_FAM`, via `_ac_tag_ids`).**
`_AC_TAG` is left **byte-identical**; the family form is a separate pattern with the same
explicit boundaries (a non-alphanumeric before `AC`, or a camelCase jump into `AC`) plus a
**mandatory separator** (`-` or `_`) on BOTH sides of the family: `AC-BC-07`, `ac_bc_7`,
`AC_T_1`. The two patterns are **disjoint by construction** — a family must start with a letter,
so `AC-01` can never match the family pattern, and the digits of `AC-BC-07` do not follow `AC`,
so it can never match the bare one. `AC-01_twins` therefore yields exactly `AC-1`, and
`AC-BC-01_x` yields exactly `AC-BC-1` and never a spurious bare tag beside it.

**camelCase families are deliberately NOT supported**: `testACBC07x` stays unmatched, because
`ACBC` has no honest split into family + number and any split the engine picked would be a
guess. A camelCase-only language tags with a separator or stays untagged; silence is honest,
a guessed criterion is not.

**4. Everything downstream reads the normalised id.**
`_ac_tags` keys, `_sum_ac_tags`, the readiness `acceptance` dimension, `narrated-only`,
`measured but unticked`, `without an AC-ID`, the per-criterion receipts, the dashboard
`acceptance` block, `cmd_top`'s obligations, `simplicity-check`'s duplicate-id detection and
`doctor`'s hint. One parse, one normalisation, one id in the MEASURED pipeline (ACCEPTANCE ⇄ JUnit ⇄ statusline) —
no second derivation to disagree. Outside it, `_IR_AC_LINE` (the IR extractor, ADR-015) keeps its own
broader, non-normalising read of AC ids; nothing joins IR `AC` nodes to `_ac_tags` today, so it is not a
second derivation of a measured number — it would have to route through `_ac_canon` the day it is.

**5. Obligation order on the board.** `_top_ac_key` (was `_top_ac_num`) sorts **bare criteria
first by number, then each letter family alphabetically and by number inside it**. An id in
neither shape sorts last instead of raising: the board must still render when the acceptance
file carries something unexpected.

**6. The statusline moves with the engine.** `uscha_progress.py`'s `_AC` and its `next` regex
widen to the same grammar. The statusline summarises the ledger; a statusline blind to a family
the engine can see would contradict the truth it claims to show.

## Consequences / Risks
- **A consumer the first cut missed:** `discover`'s canonical map (`_canonical_ids`) did
  `int(id.split("-")[1])` and crashed on the first family id — the suite's own T125 caught it on
  the first 1.87.0 run. `_match_canonical` now reads statements with the same grammar as the
  tags (`AC-FA-06`). Lesson kept: widening an id grammar means auditing every `split`/`int` on
  that id, not only the regexes.
- **A new blocker class on upgrade.** `spec-check`'s traceability gate blocks on duplicate normalised
  ids. Family ids used to normalise to *nothing* and could not collide; now a project that reuses
  `AC-BC-01` in two sections, or spells one criterion `AC-T-01` and `ac_t_1`, gets a BLOCKER, not an
  advisory. That is the gate doing its job on ids it can finally read — but it is new, and it is
  named here.
+ Measured acceptance for this repo goes from **6/172 to 165/172** (7 stay UNMEASURED: the M2/M3
  `uscha top` ids, emitted as `<skipped/>` on purpose). No evidence was added — the instrument
  was widened to read evidence that already existed.
+ Every kit project that already numbered its criteria by family gets them measured on the next
  `readiness` run, with no edit to its `ACCEPTANCE.md`.
- **The re-count is retroactive and kit-wide.** A family criterion whose checkbox is ticked but
  whose testcase is red or absent now surfaces as `narrated-only` where it was previously
  invisible. That is the point, and it is why this shipped as its own release with the bare form
  pinned byte-identical (AC-FA-03) before any new form was claimed.
- **A new false-positive class exists**: a test named `test_ac_helper_2` now tags a criterion
  `AC-HELPER-2` that nobody declared. It is harmless (a tag with no matching criterion closes
  nothing and appears in no readout) but it is real, and it is the cost of accepting the
  lowercase/underscore spelling that python and go test names force.
- Scores move. A project's readiness number is not comparable across this engine boundary; the
  ledger's `readiness_history` records both sides honestly rather than being rewritten.

## Verification
- [ ] AC-FA-01 — `_parse_acceptance_items` over a file mixing `AC-01`, `**AC-BC-07**`, `AC-T-24`,
      `ac_dd_3`, `AC-7-x` yields `AC-1, AC-BC-7, AC-T-24, AC-DD-3, AC-7` in that order
- [ ] AC-FA-02 — `_ac_tags` over testcase names `AC-BC-01_x`, `test_ac_bc_1_y`, `AC-01_z`,
      `testAC01Q`, `testACBC07x`, skipped `AC-T-11_w` yields exactly `AC-BC-1: 2 green` and
      `AC-1: 2 green`, with no spurious key
- [ ] AC-FA-03 — the bare form is byte-identical to the previous engine: `readiness` and
      `dashboard --json` (minus the wall clock) over a bare-id fixture do not move a byte
- [ ] AC-FA-04 — `uscha_progress.py` counts the same done/total the engine counts (3/5)
- [ ] AC-FA-05 — `top --json` emits normalised obligation ids, `MEASURED_PASS` where a green
      testcase tags them, in the documented order (bare by number, then families)

## What this ADR does NOT decide
- camelCase family tags — deliberately out (see Decision 3); adding them would need its own ADR
  and a rule for splitting `ACBC07` that is not a guess.
- A family REGISTRY (which prefixes a project may use) — the grammar is open on purpose; the
  engine measures ids, it does not govern taxonomy.
- Any of the other five ADR-035 deferrals: `age_hours`, the count burn-up, `drift_pct`, the
  designed `spec_pin`, general-project `TRACED`. Each is still its own future change.
