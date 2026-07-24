# CLAUDE.md — repo protocol (Uscha)

**Permanent** rules for this repo. Claude Code reads them at every session. What is specific to
each change lives in `SPEC.md` / `docs/adr/` / `ACCEPTANCE.md`, not here.

> Codex, pi and other agents read `AGENTS.md`, not this file. `uscha init` writes an
> `AGENTS.md` that points here, so there is one canonical source — keep the rules in THIS
> file and let the pointer do its job.

## Non-negotiable rules

1. **Don't code from a vague idea.** If there is no `SPEC.md` + `ACCEPTANCE.md`, model
   first: `/uscha-discovery` (new system) or `/uscha-adr-refine` (known feature). Only once the
   package is written do you build.
2. **Truth lives in files, not in the chat.** Before touching code, read `SPEC.md`,
   `ACCEPTANCE.md` and `docs/adr/*.md`. Don't rely on the conversation: context
   resets, and sub-agents and CI read the repo.
3. **Converge, don't chase zero.** Apply only the findings ≥ severity gate; the rest
   goes to `ISSUES-DEFERRED.md`. The loop ends when it converges, not when "there are no issues".
4. **ADR + CONSTITUTION discipline during the build.** Before touching an area, read
   `CONSTITUTION.md` (inviolable invariants) and the ADRs for the area. Stop and propose an ADR if
   you are going to: introduce a new dependency, create a new pattern, choose between non-obvious
   alternatives, or contradict an accepted ADR. **A CONSTITUTION violation is a BLOCKER: it is
   escalated, never worked around.** Link the code with `// ADR: <slug> — see docs/adr/...`.
5. **Evidence captured, not narrated.** Evidence is produced by execution (tests,
   gates, coverage) — it is not transcribed by hand. Absent = no evidence, never "OK".
6. **Legacy baseline.** In old code: 0 new HIGH/CRITICAL findings, 0 regressions,
   no new warnings in touched files. Old debt is frozen, new debt is blocked.
7. **Change budget.** Max iterations/files per the plan; 0 schema changes without an
   ADR; 0 new dependencies without approval. If the scope is exceeded or a fix reverts another
   → escalate (don't keep going alone).
8. **Never edit the SPEC/ADR to make the implementation look correct.** If reality
   forces a SPEC change, version it and go back to Ready.
9. **Human gate.** Don't merge or release automatically. You stop at the PR; the merge and
   the smoke test in a real environment are decided by a person.

## Truth hierarchy

`CONSTITUTION.md` (what is never acceptable) ▸ `SPEC.md` (what must happen) ▸ `docs/adr/` (why this shape). The CONSTITUTION sits above the ADRs: no ADR or SPEC may violate it. `/uscha-discovery`, `/uscha-adr-refine` and `/uscha-devloop` read it before proposing or touching anything.

## Commands (skills)

- `/uscha-discovery` — idea → CONTEXT/DOMAIN-MODEL/CONSTITUTION/SPEC/ADR/ACCEPTANCE/RISKS/HANDOFF
- `/uscha-adr-refine` — known feature → SPEC + ADR + ACCEPTANCE
- `/uscha-devloop` — plan → build → QA loop → PR (stops at the merge)
- `/uscha-sysdoc` — documents the system from the ledger
- `/uscha-status` — one-glance progress readout in chat (statusline on demand)

## Project adapter (TO COMPLETE per repo)

> This is the only stack-specific part. Complete it and delete this reminder.

- **Build:** `<e.g. mvn -q compile>`
- **Tests:** `<e.g. mvn -q test>`
- **Static gate:** `<e.g. mvn -q verify -Pqa  → checkstyle-result.xml, pmd.xml, spotbugsXml.xml>`
- **Coverage:** `<e.g. target/site/jacoco/jacoco.xml>`
- **No-go zones:** `<folders/files that are not touched>`
- **Secrets / credentials:** `<where they are and what NOT to log>`
