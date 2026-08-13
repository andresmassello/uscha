# The blind-compiler prompt scaffold (committed artifact, ADR-021)

Every v0.2 compilation — both arms of both experiments — used this exact scaffold, with ONLY the
`<TARGET-PATH>`, `<RUN-CONTRACT>` and `<CANONICAL PACKAGE>` slots varying. Committing it is what
turns the "scaffolding byte-matched" claim from an assertion into an inspectable artifact (the
1.76.0 review's point, made again at the v0.2 review: a claim whose mechanism lives outside the
repo is trust, not evidence).

```
You are an LLM COMPILER. Your FIRST action MUST be to use the Write tool to create the file
below. Then return the JSON. BLIND: implement ONLY from this prompt; do NOT read/search/list
any repo file.

WRITE to exactly: <TARGET-PATH>
<RUN-CONTRACT — one sentence: how the program runs, its I/O and exit contract>. Pure stdlib,
Python 3.8+. Write ONLY that file.

CANONICAL PACKAGE (your only input):
<the arm's SPEC.md, ACCEPTANCE.md and CONSTITUTION.md content — the ONLY slot that differs
between a free-prose arm and an EARS+STE arm>

Return ONLY this JSON (no prose/fences):
{"target_stack":"python","implementation_constraints":["..."],"source_units":[<unit>],
 "tests_units":[],"trace_manifest":[{"unit":<unit>,"implements":[<the arm's node ids>]}],
 "unresolved_intent":[{"ir_region":"<id>","decision":"<choice>","rationale":"<why>"}]}
unresolved_intent NON-EMPTY and SPECIFIC (2-5). Return JSON only after writing the file.
```

Honest residual: the historical prompts themselves are not replayable artifacts (subagent
invocations are not persisted by the host), so what the repo can evidence is this template plus
the structural fingerprints of its outputs (Write-first file creation, the JSON return shape,
model-diverse `unresolved_intent`). The v0.1 M4-reused arm (`free/`) predates this template —
that is exactly why `guard-free-r2/` exists.
