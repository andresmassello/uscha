---
name: uscha-sysdoc
description: >
  Generate a single self-contained, navigable HTML deck (PowerPoint-style, keyboard +
  click navigation) documenting a system in two parallel tracks: a commercial/CEO view
  and a technical view. Pulls real metrics from QA-LEDGER.json, includes inline SVG
  diagrams, dark control-room aesthetic. Invoke for "document this system",
  "make the system deck", "commercial + tech doc". Pairs with the dev-loop skill.
allowed-tools: Read, Write, Glob, Grep, Bash
disable-model-invocation: false
---

# sys-doc — two-view system deck generator

Produce ONE self-contained `.html` file (no external assets, no CDN, no localStorage)
that reads like a slide deck and documents the system on two tracks the reader can
switch between at any time:

- **Commercial / CEO track** — what the system does, the value, the risk posture, the
  status. No code. Plain business language. Money/time/reliability framing.
- **Technical track** — architecture, modules, data flow, contracts, QA results,
  coverage, known deferred issues.

## Orientation markers (non-negotiable)

The operator must never have to ask "where am I?" or "what happens now?". Two markers, always.
They are navigation, not ceremony: one line per turn, one block at the end.

**Open every turn with a breadcrumb**, then the content:

`[uscha · sysdoc · <step> → <target>]`

- `<step>` — `Q<n>` for a question, `pass <n>` for a loop iteration, `step <n>` otherwise.
  Count what has actually happened. **Never write a denominator** (`Q4/12`): this phase
  converges, its length is not known in advance, and an invented total is exactly the kind of
  narrated number the method forbids. **When the ledger already measures the count** (the QA
  loop's `loop_count`), use the measured number — never keep a parallel tally of your own.
- `<target>` — the artifact this turn feeds (`SPEC`, `ADR-003`, `ACCEPTANCE`, `LEDGER`,
  `RECEIVED`, ...). Drop `→ <target>` only when the turn genuinely feeds none.

**Close with the close block ONCE, when the skill finishes** — not on every turn. Ending
without it is a defect, even when the phase converged cleanly:

```
[uscha · sysdoc · CLOSED]
Produced: <files actually written, or "nothing">
Blocks:   <what stands between here and the next phase, or "nothing">
Next:     <the next action, and why it is that one>
Run:      <the exact command or skill to invoke>
```

This is **not** the implementation handoff some skills also emit: that one is a prompt for
whoever implements next, this one is navigation for the human operator, and both can appear.

`Blocks` and `Next` are **derived from the state you just produced** — never copied from a
fixed route, **including any `Flow:` line in this file**. Those lines are the nominal path;
open ADR experiments, an unclosed spike, an unapproved golden or a red gate all change what
genuinely comes next, and the derived answer wins. If the next phase cannot start yet, name it
and say exactly what unblocks it.

Keep the CONTENT in the conversation's language, but keep the labels (`CLOSED`, `Produced`,
`Blocks`, `Next`, `Run`) verbatim — they are the method's vocabulary and the smoke checks them.

## Inputs

1. **Metrics (authoritative):** run the ledger summary and use its numbers verbatim —
   never invent figures.

```bash
QL="./.claude/skills/uscha-devloop/qa_ledger.py"                      # instalacion por proyecto
[ -f "$QL" ] || QL="$HOME/.codex/skills/uscha-devloop/qa_ledger.py"   # Codex raw-skills install
[ -f "$QL" ] || QL="$HOME/plugins/uscha/skills/uscha-devloop/qa_ledger.py"  # Codex plugin install
[ -f "$QL" ] || QL="$HOME/.claude/skills/uscha-devloop/qa_ledger.py"  # Claude global install
python3 $QL summary --json > /tmp/qa-summary.json
python3 $QL readiness --json > /tmp/qa-readiness.json
```

   From the summary use: `total_steps`, `by_tool`, `by_repo`, `aggregate`, `escalations`.
   From readiness use: `score`, `status`, `cap_reason`, `dimensions`, `acceptance`,
   `by_repo`. Render readiness as a **semaphore widget** at the top of slide 5 and as a
   per-repo readiness column on the technical QA slide: green ≥80, amber 50–79, red <50,
   and always print the `cap_reason` when a hard cap is active.

2. **System understanding:** read the ADR/PLAN, CLAUDE.md, module layout, and key
   contracts to describe architecture and value. If no ledger exists, ask whether to
   proceed without QA metrics (the deck still works, just without the QA section).

3. **Tracked-markdown protocol:** the HTML output itself is not tracked markdown, so
   generate freely. But if asked to also update a tracked `.md`, ask for its current
   version first.

## Structure (each is one navigable slide)

1. **Title** — system name, one-line purpose, date, run id.
2. **Track switcher** — persistent toggle: Commercial ⇄ Technical (affects which
   slides/sections show; default Commercial).
3. Commercial: **What it does** (plain language, the job it removes).
4. Commercial: **Value & status** (what's done, what's in flight, risk posture).
5. Commercial: **Quality at a glance** — coverage %, tests count, a simple
   "issues found and resolved" readout from `by_tool`. No jargon.
6. Technical: **Architecture** — inline SVG: modules/repos as boxes, data flow as
   arrows, external systems (DB, external APIs, devices) distinct.
7. Technical: **Key contracts / interfaces** — the seams between repos/modules.
8. Technical: **QA results** — per-tool table (reported / fixed / %fixed / deferred /
   suppressed), coverage per repo, tests/kLOC, escalations list.
9. Technical: **Deferred issues** — summarize `ISSUES-DEFERRED.md` honestly.
10. **Smoke checklist** — the manual verification steps.

## Build constraints

- Single `.html`, all CSS/JS inline. Works opened directly from disk and deployable to
  Cloudflare Pages / S3 as-is.
- **No localStorage / sessionStorage** (won't run in some sandboxes). Hold nav state in
  JS variables only.
- Navigation: arrow keys (← →), on-screen prev/next, a slide index/dots, and Esc for an
  overview grid. Slide counter visible.
- Diagrams are hand-authored inline `<svg>` using `currentColor`/CSS variables so they
  theme with the deck. No raster images, no external diagram libs.
- Aesthetic: dark control-room (deep neutral background, one accent, high-contrast
  mono for technical figures), but keep the Commercial track clean and uncluttered.
- Accessible: semantic headings, `aria-label`s on nav controls, visible focus, contrast
  AA. Readable when printed (print stylesheet flattens slides to a linear document).

## Output

Write to `docs/system-deck.html` (or the path the human gives). Then state the file
path and the two or three things the reader should look at first. Do not paste the HTML
into chat — present the file.
