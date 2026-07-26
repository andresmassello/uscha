## What and why

<!-- The problem, then the change. Link the issue if there is one. -->

## The check that proves it

<!-- REQUIRED for behaviour changes. Which smoke check (Tnn) did you add or extend, and what
     does it assert? "No claim without a check" is this project's whole argument. -->

## Verification

- [ ] `bash uscha-kit/tests/smoke-engine.sh` exits 0
- [ ] Twins byte-identical (`uscha-kit/.claude/skills/` = `uscha-kit/skills/`), if skills changed
- [ ] Docs updated in the same commit, or the claim is marked `proposal`
- [ ] Six version surfaces + `CHANGELOG-X.Y.Z.md`, if this is a release
- [ ] No real project or client names (AC-03 measures it)

## What is NOT covered

<!-- Honest limits. What did you not test, and why. UNMEASURED is an acceptable answer here;
     silently implying coverage is not. -->
