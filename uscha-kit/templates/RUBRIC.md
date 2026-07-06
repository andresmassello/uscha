# RUBRIC — <name of the change or project>

> The rubric is the ACCEPTANCE of the NON-testable: a versioned qualitative criterion,
> with weights, anchors and threshold. A grader (any agent, any LLM, or a
> human) scores it criterion by criterion WITH `file:line` evidence and emits the JSON
> of the contract (see `templates/rubric-grader-prompt.md`); `qa_ledger.py rubric-ingest`
> absorbs it. By default it ADVISES; it gates only if you declare it
> (`defaults.rubric.gate: true` in the config, or `--gate`).
>
> Parseable format: `- [ ] RB-01 (peso 3) — criterion`. The weight is optional
> (default 1). The anchors are for the grader; the engine does not parse them.

threshold: 0.80

## Criteria

- [ ] RB-01 (peso 3) — Sane error handling: every external call has a timeout,
  the failure is translated into an actionable message and exceptions are not swallowed.
  - anchor-pass: `client.get(url, timeout=5)` + retry with backoff + log with context.
  - anchor-fail: `except Exception: pass`, or a `catch` that only re-raises without context.
- [ ] RB-02 (peso 2) — Repo conventions respected: naming, package structure
  and style consistent with the neighboring code (not with the author's preference).
  - anchor-pass: the new file is indistinguishable in style from its siblings.
  - anchor-fail: a module with camelCase in a snake_case repo.
- [ ] RB-03 (peso 2) — API/surface ergonomics: names that say what they do,
  parameters without surprises, the common case is the easy one.
- [ ] RB-04 (peso 1) — The change's documentation explains the WHY, it does not paraphrase
  the code.

## Negative criteria

> Things that must NOT appear. If the grader finds them (verdict `fail` WITH
> evidence), they subtract their weight from the score.

- [ ] RB-NEG-01 (peso 2) — Comments that narrate the correctness of the change itself
  ("now correctly handles...") instead of documenting the code.
- [ ] RB-NEG-02 (peso 1) — Speculative abstractions: interfaces/layers with a single
  use and no request in the SPEC.
