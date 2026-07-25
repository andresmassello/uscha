# uscha-kit 1.52.0 — orientation markers: the operator always knows where they are (2026-07-25)

Field feedback from a real run (a discovery driven through Codex): *"the one using it gets a
bit lost — there is no visual feedback, it feels magic/invisible"*, and *"discovery finished
and the agent just sat there; it never said 'ok, discovery is done, now we go to…'"*.

Both are real defects in the method's user experience, and neither was a rendering problem —
the generated HTML was fine. The gap was **in the conversation**. Smoke suite: 390/390.

## What was actually wrong
**No breadcrumb existed at all.** Not one skill asked the agent to say where it was. Nine
skills, zero in-flow orientation.

**The handoff existed, but was the wrong kind.** `uscha-discovery` had a `## Handoff` section
— which produced *a prompt for the next implementer*, not a *navigation signal for the human
operator*. The route was a single documentation line at the bottom
(`Flow: /uscha-discovery → /uscha-devloop → human gate`), describing the flow rather than
instructing the agent to emit it. So the phase converged, the package got written, and the
session went quiet.

And that static line would have been **wrong** in the reported run: the correct next step was
not the dev-loop — ADR experiments 002–005 were open, and their spikes had to close before any
implementation. A canned arrow sends the operator to the wrong place.

## Two markers, in all nine skills
**A breadcrumb opens every turn:**

```
[uscha · discovery · Q4 → SPEC]
```

`<step>` counts what has actually happened (`Q<n>`, `pass <n>`, `step <n>`) and **carries no
denominator**: the phase converges, its length is not known in advance, and an invented total
(`Q4/12`) is exactly the narrated number the method forbids. `<target>` names the artifact the
turn feeds, so the operator sees *why* they are being asked.

**A close block ends every skill — stopping silently is now a defect:**

```
[uscha · discovery · CLOSED]
Produced: CONTEXT.md · SPEC.md · ADR-001..005 · ACCEPTANCE.md
Blocks:   ADR-002..005 are open experiments — their spikes must close before build
Next:     validate ADR-002 (the temporal matrix) → an ADR with evidence, not code
Run:      /uscha-adr-refine ADR-002
```

`Blocks` and `Next` are **derived from the state just produced**, never copied from a fixed
route — open experiments, an unclosed spike, an unapproved golden or a red gate each change
what genuinely comes next. This is the method's own doctrine (*derived, not narrated*) finally
applied to its own UX.

Two more rules keep the marker from becoming the thing it replaces:
- **The count must be measured where a measurement exists.** When the ledger already counts QA
  passes (`loop_count`), the breadcrumb uses that number instead of the agent keeping a
  parallel tally — otherwise the new UI layer would quietly reintroduce a narrated number.
- **The existing `Flow:` lines are subordinated, not trusted.** Three skills carried a fixed
  arrow (`/uscha-discovery → /uscha-devloop → human gate` and friends). Those are now marked
  in place as the *nominal* route that the derived `Next:`/`Run:` overrides — leaving them
  unqualified would have contradicted this release's own diagnosis.

**Two variants, because one shape does not fit all nine.** `uscha-status` and `uscha-mirador`
are one-shot read-only readouts whose own contract is *"one compact block, nothing else —
never pad it"*. Bolting the conversational close block onto them would contradict the skill it
was added to, so they carry the breadcrumb plus the routing pair (`Next:`/`Run:`) and nothing
more. The close block is also explicitly distinguished, in-file, from the **implementation
handoff** three skills already emit — that one is a prompt for whoever implements next, this
one is navigation for the operator, and both may appear.

The labels (`CLOSED`, `Produced`, `Blocks`, `Next`, `Run`) stay verbatim in English while the
content follows the conversation's language: language-stable labels are what makes the
convention mechanically checkable.

Regression: smoke **T105** — all nine skills, on **both twin trees**, must declare the section
and a breadcrumb naming **their own** skill; the conversational seven must carry the exact
`[uscha · <skill> · CLOSED]` header (asserting the *header*, not the bare word — a header
naming a sibling used to slip through while the breadcrumb stayed correct), the five labels,
the anti-denominator rule and the measured-count rule; the two readouts must NOT carry the
conversational block. Verified by mutation: each of those drifts was injected into a real
SKILL.md and T105 caught every one. A convention only works if it is identical everywhere;
T57 mechanized this same class of drift for skill counts.

## Also
The README's install block now shows all three targets (`claude`, `codex`, `pi`, plus `all`)
instead of showing `--target claude` and relegating the others to prose below the copyable
snippet.
