## Orientation markers (non-negotiable)

The operator must never have to ask "where am I?" or "what happens now?".

This skill is a **one-shot read-only readout**: its block IS the answer. It therefore does NOT
take the conversational close block — that would be exactly the padding this skill forbids.
It carries the two minimal markers instead.

**Open with a breadcrumb:**

`[uscha · {{skill}} · step <n> → <target>]`

**End with the two routing lines, and nothing else:**

```
Next: <the next action, derived from what this readout just showed>
Run:  <the exact command or skill to invoke>
```

`Next` is **derived** from the state you just read — never copied from a fixed route,
including any `Flow:` line in this file. If nothing is actionable, say that plainly rather
than inventing a step. Keep the CONTENT in the conversation's language and the labels
(`Next`, `Run`) verbatim — the smoke suite checks for them.
