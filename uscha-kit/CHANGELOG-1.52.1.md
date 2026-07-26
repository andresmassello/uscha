# uscha-kit 1.52.1 — the suite reads the version instead of pinning it (2026-07-25)

A release-process fix. Six version literals were hardcoded inside
`uscha-kit/tests/smoke-engine.sh`, so **every** bump broke the suite until someone retyped them
one by one. That toll was paid three times in a single day (1.51.1, 1.51.2, 1.51.3) and the
1.41.3 changelog had already flagged it as a follow-up. Smoke suite: 391/391.

## Why it was pure toll
The literals proved nothing. `install-uscha.py`'s `source_version()` reads the same
`uscha-kit/VERSION` file the assertions were pinned to, so a hardcoded `'1.52.0'` never
verified the number — it only verified that a human had remembered to retype it. Nor were they
the drift gate: **T44** is, and it stays exactly as it was (the six surfaces must agree *and*
ship a `CHANGELOG-<version>.md`). Removing the pins therefore costs no coverage.

The suite now derives `KIT_VERSION` from `VERSION` once, and T44 builds the changelog filename
from what it already read.

## The proof
This very release is the test: bumping to 1.52.1 touched **nine files — none of them the test
suite** — and the smoke stayed green. Before this change the same bump would have failed on six
assertions.

Regression: smoke **T106** — a version-shaped literal compared against a `version` /
`source_version` key, or a pinned `CHANGELOG-X.Y.Z.md` filename, fails the suite. The toll
cannot come back quietly.

## Note for whoever bumps next
The release checklist is now: six version surfaces + the repo's self-applied
`uscha.config.json` + both READMEs + a new `CHANGELOG-X.Y.Z.md`. The test suite is no longer
part of it.
