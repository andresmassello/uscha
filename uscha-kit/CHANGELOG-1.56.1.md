# uscha-kit 1.56.1 — a ceiling in front of every XML parse (2026-07-26)

A third external review made one concrete, still-open point: the engine parses report XML with
the standard library and **no size limit**. `ISSUES-DEFERRED.md` had already recorded the risk
and the reason (`defusedxml` is unavailable — stdlib-only is a hard contract), but recording a
risk is not mitigating it. Smoke suite: 397/397 on Linux, macOS and Windows.

## What changed
Every one of the **seven** `ET.parse` call sites now goes through `_parse_xml()`, which refuses
anything above **`MAX_REPORT_BYTES` (64 MB)** — orders of magnitude above any real JUnit or
coverage run. It accepts both a path and an open file object, because the call sites use both.

The reports the engine ingests are produced by **someone else's build**. An unbounded read is a
denial of service against the operator's own machine, and that is the realistic failure: a
runaway generator, a corrupt file, a test suite that exploded. That one is now closed.

## The limit, stated rather than implied
A ceiling is **not** protection against a determined attacker — entity expansion *under* the
ceiling still expands. `SECURITY.md` says exactly that instead of implying the parser is
hardened. Anyone who wants real hardening needs `defusedxml`, and taking a dependency would
break the constraint that makes this engine installable anywhere with nothing but Python.

Regression: smoke **T112** — the ceiling raises on an oversized report, a normal report still
parses, and **no direct `ET.parse` survives outside the helper** (asserted by counting call
sites, so a future patch cannot quietly reintroduce an unguarded parse).
