# uscha-kit 1.62.0 — `NO-CODE`: declaring nothing is not declaring *nothing to declare* (2026-08-03)

Found by pointing `spec-drift` at this repo's own ADRs for the first time — the tool shipped
in 1.58.0 and had never been run on the decisions it exists to watch.

The first run answered **7 of 7 `UNMAPPED`**. That was the honest answer (nobody had ever
declared a `governs:` mapping here) and it exposed a real gap in the design underneath.

## The gap

`ADR-004` is a **negative decision** — it defers the golden-touched veto. It governs no source
and never will. Reporting it `UNMAPPED` was not a nudge to fix something; it was permanent
noise about a state that is already correct, and permanent noise is exactly how an advisory
stops being read.

The engine could not tell **"nobody declared a mapping"** from **"there is nothing to map"** —
the same conflation of absence with declaration this engine has now closed in four other
places (`UNMEASURED` vs green, `dirty: null` vs clean, a golden with no coverage entry, an
empty coverage map).

## The fix

A spec whose frontmatter declares an **explicit empty list** now reports its own verdict:

```markdown
---
governs: []
---
```

→ **`NO-CODE`** — *"declares governs: [] — a decision that governs no code"*. Distinct from
`UNMAPPED` (nobody said anything) and from `CLEAN` (mapped, and its code has not outrun it).
A `governs:` list that is non-empty but matches no tracked file still reports `UNMAPPED`: that
is a broken mapping, not a deliberate one.

`AC-SD-05` measures it, and is mutation-proven — collapsing `NO-CODE` back into `UNMAPPED`
turns the criterion red.

The fresh review caught that the first cut of this fix was only half true: `governs:` followed
by nothing usable (a placeholder, a lone `# TODO` comment) also collapsed to an empty list and
so read `NO-CODE` — asserting a deliberate decision nobody made, which is the exact conflation
this release claims to close. Only an **inline `[]`** counts as a declaration now; an
unfinished `governs:` key reports `UNMAPPED`, because that is what it is.

## Dogfooding, recorded

All seven ADRs in this repo now carry a `governs:` mapping (`ADR-004` declares `governs: []`),
so the repo's own spec-drift report is fully accounted for: six `CLEAN`, one `NO-CODE`, zero
unexplained. Verified honestly in both directions — at the default 30-day lag nothing is
stale, and at `--max-lag-days 5` the two oldest decisions (`ADR-001`, `ADR-002`, both from
2026-07-22 against an engine last changed 2026-08-03) correctly flip to `SPEC_STALE`, each
naming the exact governed files that outran them. "All green" that cannot be made to go red is
not a measurement.

Suite: 403 checks. Acceptance: **34/34 measured green** where `coverage.py` is installed.
