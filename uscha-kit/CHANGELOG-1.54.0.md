# uscha-kit 1.54.0 — first contact: the newcomer is oriented once (2026-07-26)

The third and last blind spot from the same field report. 1.52.0 gave the operator a breadcrumb
(*where am I*) and a close block (*what now*). Neither answered the question a newcomer has
first: **what is this, and what is it about to cost me?** Someone typing `/uscha-discovery` was
interrogated immediately — no idea how long, what comes out, or that they could stop.
Smoke suite: 394/394, green on Windows, Linux and macOS.

## The banner
The seven conversational skills now open with:

```
[uscha · discovery · START]
Method: you bring the idea, the method builds the rest. Facts block, guesses advise;
        nothing closes on a checkbox, and the human approves the merge.
Here:   I grill you ONE question at a time, each with my recommended answer. You decide.
Output: CONTEXT.md · SPEC.md · docs/adr/*.md · ACCEPTANCE.md · RISKS.md
Next:   /uscha-devloop builds against the package. No code until the package exists.
Stop:   say so at any point — whatever is already written stays.
```

## Shown ONCE — the gate is the whole design
Anti-ceremony is a meta-invariant of this method, and a banner on every invocation is ceremony:
by the thirtieth run it is noise you scroll past, and it devalues the breadcrumbs you *do* want
read. So it is **gated on measured project state**: it appears only when the project has no
uscha artifacts yet — no `QA-LEDGER.json`, no `SPEC.md`/`ACCEPTANCE.md`, no `docs/adr/`. For the skills that write those artifacts
(`discovery`, `adr-refine`, `devloop`) that self-limits to one banner and then silence. Honest
limit: `characterize`, `reverse-discovery` and a ledger-less `sysdoc` write none of the three,
so re-running one of those before any of the first group would show the banner again -- the
gate reads project state, and on a pure facts/golden run that state genuinely has not moved.
Same principle as the close block's derived `Next`: read the state, don't narrate.

**`Next` may name the nominal route here** — and only here. On a first run there is no measured
state to derive from, so the nominal path *is* the honest answer. From the close block onward,
derived state wins (an open ADR experiment or a red gate changes what genuinely comes next).

**The two readouts are excluded on purpose.** `uscha-mirador` and `uscha-status` declare "one
compact block, nothing else"; a banner would contradict the skill it was added to — the same
mistake a fresh review caught in 1.52.0's first pass.

## Bilingual by construction
The labels (`START`, `Method`, `Here`, `Output`, `Next`, `Stop`) stay verbatim in English — that
is what makes them mechanically checkable — while the wording after each label is rendered in
the operator's language. Write to it in Spanish and the block reads in Spanish under English
labels. The instruction says so explicitly, because the canonical wording shipped in the
SKILL.md is English and an agent could otherwise copy it through untranslated.

Regression: smoke **T109** — the seven conversational skills, on both twin trees, must carry the
section, a `[uscha · <skill> · START]` header naming their own skill, all six labels, and the
first-run condition itself (so a future edit cannot quietly turn the banner into ceremony); the
two readouts must NOT carry it.
