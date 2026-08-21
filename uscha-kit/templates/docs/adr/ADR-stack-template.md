---
# The machine-readable half of a stack ADR (ADR-040). One entry per component this ADR
# FIXES: runtime, web framework, ORM, database, Node, bundler, message broker, cache.
#
#   component  the name as your team says it
#   version    the EXACT version or minor line you are fixing -- not the major family
#   eol        end of OSS/LTS support, YYYY-MM-DD. `unknown` is allowed and reads as a
#              NAMED absence ("no EOL cited"), never as a pass
#   source     the OFFICIAL page the date came from. Fetch it while you ask; never
#              answer from memory
#   checked    the day you actually looked, YYYY-MM-DD
#
# `qa_ledger.py spec-check` reads this block and compares each `eol` against the
# `go_live` declared in the SPEC. It is ADVISORY: it never gates and never caps
# readiness. It measures that a date and a source were CITED -- it cannot verify that
# the source tells the truth. That check is the human's.
lifecycle:
  - component: <runtime, e.g. the language runtime>
    version: "<exact version or minor line>"
    eol: YYYY-MM-DD
    source: https://<official support page>
    checked: YYYY-MM-DD
  - component: <web framework>
    version: "<exact version or minor line>"
    eol: YYYY-MM-DD
    source: https://<official support page>
    checked: YYYY-MM-DD
  - component: <database / store>
    version: "<exact version or minor line>"
    eol: unknown
    source: https://<official support page>
    checked: YYYY-MM-DD
---
# ADR-NNN: <the stack this project fixes, and until when it is supported>

## Status: Accepted

> The SPEC must declare the milestone this block is compared against, as frontmatter
> `go_live: YYYY-MM-DD` or a `**Go-live:** YYYY-MM-DD` line. Without it the whole
> dimension reads UNMEASURED, with the reason named.

## Context
<Why this stack, and what already constrains it: reused legacy modules and the minimum
versions they support, the operator's development/observability tooling (consoles, APM,
admin UIs) — those constrain versions, so they are asked BEFORE the stack is fixed, not
after — and the expected operating life of the system beyond go-live.>

## Alternatives
- A) <option> — support window <until when>, cost <…>
- B) <option> — support window <until when>, cost <…>

## Decision
- <The exact versions fixed, one line each, with the date they stop being supported.>
- **Upgrade policy**: <who approves a major upgrade, and when it is scheduled>. A new
  dependency is never added without explicit approval (the dev-loop's "zero new
  dependencies without approval" rule).

## Reasons
- <why this line, and why its support window covers the operation, not just the launch>

## Consequences
+ <the good>
- <the cost: the upgrade already on the calendar, and who owns it>

## Implementation Plan
- Affected paths: <build files, lockfiles, CI images, base images>
- Tests: <the suite that proves the fixed versions actually run>

## Verification
- [ ] Every component this ADR fixes carries a `version`, an `eol` and the `source` it
      was read from, checked on a named day.
- [ ] No component's `eol` falls before the SPEC's `go_live`; where one does, the upgrade
      is scheduled BEFORE the build, not after.
