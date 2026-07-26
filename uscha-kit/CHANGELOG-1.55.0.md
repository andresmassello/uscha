# uscha-kit 1.55.0 — the engine speaks English (2026-07-26)

The kit is published on npm, the site and every doc are in English, and the repo went public
today. The engine, meanwhile, was still printing **Spanish** at the operator. A Spanish speaker
saw a coherent tool; everyone else got English docs, English labels — and a measurement engine
answering in another language. Smoke suite: 394/394 on Windows and real Linux.

## What changed
Every user-facing message `qa_ledger.py` prints is now English: the **doctor** (its whole
happy path and every remediation hint), **readiness** and all its advisories, **phase**,
**flag-blocker**, **simplicity**, **waste**, **pit-check**, **gate-integrity**,
**regression-capture**, **rubric**, **spec-check**, **golden-diff** and the scrub.

Roughly 100 strings across ~7 passes. The wording was not merely translated: several messages
were tightened while they were being rewritten (they had accumulated shorthand only the author
could parse).

## What deliberately did NOT change
- **Spanish input aliases stay.** `qa_ledger.py` accepts Spanish key names in ADR experiment
  blocks (`criterios_de_promocion`, `senal_de_feedback`, …) as aliases for their English
  canonical keys. Those are *input tolerance*, not output: removing them would break every ADR
  a Spanish-speaking user has already written. They are untouched, on purpose.
- **Ledger keys, enum values and finding IDs** — part of the data contract, never text.
- **Docstrings and code comments** remain largely Spanish. They are invisible to users and
  changing ~6000 lines of them buys an operator nothing; it is a separate arc if it is ever
  worth doing at all.

## Honest limit
The sweep was driven by extracting printed literals, and a heuristic pass still reports ~12
candidates — inspected, and they are false positives (English strings containing words like
"no", identifiers, extractor artifacts). Some rarely-hit branch may still carry a Spanish
sentence. This claims "every message found by extracting print sites and by running the
commands", not "provably zero".

## If you grep our output
Assertions that matched Spanish engine text will break. That is exactly what happened here: the
smoke suite had **9** such assertions and each one failed loudly the moment its string changed —
they are updated in this release. If your CI greps `qa_ledger.py` output, expect the same and
treat it as the same kind of signal.
