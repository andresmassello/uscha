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

## Inputs

1. **Metrics (authoritative):** run the ledger summary and use its numbers verbatim —
   never invent figures.

```bash
QL="./.claude/skills/uscha-devloop/qa_ledger.py"                      # instalacion por proyecto
[ -f "$QL" ] || QL="$HOME/.claude/skills/uscha-devloop/qa_ledger.py"  # instalacion global (kit 1.20.0)
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
