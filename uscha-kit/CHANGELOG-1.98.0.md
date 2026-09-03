# uscha-kit 1.98.0 — the narrated backlog, round 1: six labels that outlived their truth, and three deferred LOWs that outlived their deferral (2026-09-03)

No behaviour change a consumer project will notice unless it uses reverse discovery, and then
only in its favour. This release is the method turned on the repo's own prose: a `VISION` /
`planned` / `not yet` label is a promise the reader cannot check, and the rule from here on is
that such a label either gets **wired** — built and measured — or gets **rewritten as the honest
state**: rejected, deferred by a dated decision, or by design. Six were rewritten. Three deferred
findings were wired. Both halves are asserted by the suite, because a doctrine nobody measures is
another narrated claim.

## What changed

### Six labels, rewritten to what is actually true

Each of these was correct when it was written. That is the point: a label is a claim with a
shelf life, and nothing in the repo was watching the expiry date.

- **`ACCEPTANCE.md`** said the reverse-discovery slice-1 criteria were unticked *"because the
  code does not exist yet"* — in a paragraph sitting directly above ten **ticked** `AC-RD` ids.
  The code shipped in **1.64.0** and slice 2 in 1.65.0. The paragraph now says so and names the
  block that measures them (T120).
- **The drift row** in the diamond table — *"Drift = incremental reverse discovery, same
  engine"* — wore a `VISION` chip over a caption that already read *"valid idea, rejected as
  architecture · ADR-011"*. Those two things cannot both be the label. VISION means *not built
  yet*; ADR-011 is a **negative decision** with reasons on file: the handoff's mandate rested on
  a factual error (it imagined a spec-drift that performs semantic extraction; the one that
  shipped compares commit dates), so there is no extraction engine to share. The chip is now
  `REJECTED` on both language pages, with its own style, and `site/llms.txt` and the README
  pointer say *rejected by ADR-011* instead of *deferred until it can be measured*. The
  **arbitrary-systems row stays VISION** — that one is honest, and this release does not touch
  it.
- **`templates/CONSTITUTION.md`** promised risk profiles A–E were *"NOT yet mechanized in the
  engine"*, two lines below a paragraph explaining that everything but rule 3 is *design
  discipline and review judgment*. Not yet implies a queue. It now reads **by design**, which is
  what the surrounding paragraph has said all along.
- **`docs/CROSS-PLATFORM.md`** was titled *"audit and roadmap"* six lines above *"kept as the
  record of what was found and fixed, not an open roadmap."* Retitled **audit (measured)** — and
  then the body had to earn the title: its status line still read *"393/393 … on every push"*,
  a suite count from before ~50 releases and a grid 1.97.0 had already reduced. The present-tense
  claims now say **444 checks at kit 1.98.0**, three cells on a branch push or PR and all six on a
  tag or dispatch; the sentence justifying the reduction moved to the past tense. The audit-trail
  narrative below it keeps its historical numbers — they are the record of what was measured
  then, and rewriting them would be the opposite of an audit trail.
- **The outer-loop slides** (design + security tax, both languages) carried a `proposal` badge —
  *design agreed, not yet in code*. The human **evaluated and deferred** them on 2026-09-02. The
  slides stay: a documented design that was considered and declined is worth more published than
  deleted. The badge now reads *evaluated — deferred (2026-09-02), not on the roadmap*, with its
  own muted style and a new entry in the doc's own status-convention legend, so they no longer
  present as pending kit work. A fresh review then found the label in **five more places**: the
  atlas SVG caption inside both decks says `(proposal)` in a diagram sitting beside the slide that
  now says `deferred`, and so did the diagram SOURCE (`docs/diagram-sources/atlas-map.html`, what
  the inline SVG is copied from, so a fix that skipped it would come back on the next redraw) and
  the standalone `formats/uscha-F-atlas.html`, the fifth copy nobody had counted. All are
  relabelled — as is a sixth, the field manual's §11 status chip — and all seven paths are in the
  list. Six copies of one label is the argument for a list rather than a memory. No PNG is derived
  from that diagram — the only tracked PNGs are the paper's three figures — so there was nothing
  to re-render.
- **The deferral itself had no checkable record.** A date in a badge is a claim like any other.
  `ISSUES-DEFERRED.md` gains a *Scope, decided by the human — dated deferrals* block, and the
  2026-09-02 outer-loop decision is its first line, naming what was set aside and what survives;
  both status legends point at it.
- **`uscha top` fixture F3** was marked *planned* in a paragraph whose own second half argued its
  redundancy: F1/F2/N1 already carry three different denominators (6, 8, 24), which is the exact
  variation F3 existed to supply. It is now **DECLINED**, like F4, with the reason and the matrix
  cell to match.

The instrument is `tools/narrated-claims.txt`: one `path :: phrase` per retired claim, asserted
absent by **`AC-VC-01`**. An **allowlist** on purpose, not a ban on the word VISION — the
arbitrary-systems row and *"cross-vendor is not yet measured"* are correct labels today and must
survive, and a gate that flags what is right teaches the reader to ignore it. It also means the
historical record (the per-release changelogs, `audits/`, `ISSUES-DEFERRED.md` as a mechanism
name, the paper's Future Work, every code and CSS token) is out of scope **by construction**:
nothing outside the list is read. A listed path that no longer exists is a red, not a pass.

**`AC-VC-02`** makes repo rule 3 mechanical for the pages this release touched: each ES/EN twin
pair is diffed against the base ref and the changed-line counts must be **equal**. An edit that
lands in one language and not the other is invisible until a reader who only speaks the other one
finds it. No git or no base ref → UNMEASURED, never a silent pass.

### The three 1.69.0 deferred LOWs, closed

`ISSUES-DEFERRED.md` exists so the QA loop can converge instead of chasing zero. It is not a
graveyard. Three findings had been sitting in it for **33 releases**, each individually small —
and they turn out to share one shape that is not small at all: **the JSON stayed right and a
human-facing surface lied.** A rendered row split in two, a work item silently suppressed, a gate
silently not declared. Nothing wrong in the ledger; all three wrong on the screen the human
decides from. Each was verified **RED against the 1.97.0 engine** before its fix.

- **The delta twin broke on interior newlines** (`AC-DE-01`). A markdown row ends at a newline,
  so a narrated statement carrying one split its observation across two physical lines and every
  column after the break landed in the wrong one. `_md_cell` now renders every cell of that
  table — CR/LF collapse to a space, `|` is escaped — so one observation is one row whatever its
  statement carries. A space rather than `<br>`: every other cell is plain text, and a lone HTML
  tag in one column would be the only markup in the table. The JSON and the OBS id always
  survived, which is exactly why this looked cosmetic; the twin is the artifact the **human
  curates from**.
- **`promote`'s ISSUES-DEFERRED dedupe was a raw substring test** (`AC-DE-02`). An OBS id merely
  *mentioned in prose* in that file suppressed its work item forever — a `fix` verdict that
  quietly produced nothing. `_deferred_carries` anchors on the `- [ ] OBS-<id>` line form
  instead. The question was never *does this text occur* but *does this file already carry the
  work item for this observation*, and only the line shape answers it. The trailing word boundary
  buys the case a substring test cannot express at all: `OBS-1` is not `OBS-10`.
- **`fidelity --config` resolved against the cwd alone** (`AC-DE-03`). Run from anywhere but the
  project root, the config beside the ledger was never opened — so `defaults.fidelity.gate` was
  never declared and the INV-ADVISORY-01 refusal that reads it never fired. An **unnamed
  absence**: full vector, exit 0, indistinguishable from having no gate at all. Both halves of
  the original suggestion are implemented, because either alone leaves a hole. The relative
  default now resolves against the cwd **first** (an explicit config next to you is what you
  meant, and no existing invocation changes behaviour) and then **beside the `--ledger`**; and
  the output **names the path it read**, or names the absence and the two places it looked.
  `--json` carries it as `config`.

A fresh review of those three fixes then found the fourth criterion (`AC-DE-04`): the delta twin
was the site that got **reported**, not the only site with the bug. `_render_ir_md` escaped a pipe
and never touched a newline, in both its node rows and its UNTYPED rows; and `promote` wrote the
raw statement into a markdown **checklist item**, which ends at a newline exactly as a table row
does — so a multi-line statement split the work item in two and left the half
`_deferred_carries` recognises without its text. Both now go through `_md_cell` (the UNTYPED text
is truncated *after* flattening, so the 80-character cut cannot land mid-break). A one-off fix at
the reported site is how the second and third copies survive.

`_DEFERRED_ITEM_LINE` also grew a `.*` between the checkbox and the id, so a human who reworks the
item — prefixing a date, a severity, an owner — does not get a second copy appended on the next
`promote`. `OBS-1` is still not `OBS-10`: the word boundaries do that, not the prefix.

The same pass rewrote the two entries below them that are **not** going to be fixed. `S324`
(`sha1` for fingerprinting) needs `usedforsecurity=False`, which needs Python 3.9, which means
raising a declared floor the Windows CI cell exists to hold. `S314` (`ET.parse`) prescribes
`defusedxml`, a new dependency, against a stdlib-only contract. Both now say **blocked by a
decision** rather than reading as someday-work: "someday" invites a future reader to just do it,
and doing it would break something declared.

## Migration

None. The engine gains no flag and drops none. Three surfaces move for anyone using reverse
discovery, all in the same direction — a delta twin that no longer corrupts on a multi-line
statement, a `fix` verdict that reliably produces its work item, and a `fidelity` that says which
config it read. `fidelity --json` gains one key (`config`, null when none was found).

Suite: __SUITE__ checks · 0 fail; acceptance __ACC__.
