---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/.claude/skills/uscha-devloop/SKILL.md
  - uscha-kit/skills/uscha-devloop/SKILL.md
  - uscha-kit/hooks/hooks.json
  - uscha-kit/install-uscha.py
  - uscha-kit/README.md
---
# ADR-058: Human acts are DECLARED and RECORDED, kept out of the agent's shell — and a PR request runs the gate first

## Status: Proposed — **the SKILL text (PR-request protocol, proactive report of a QA step that could not run, STOP and ask the human) shipped in 2.10.0; `--human`/`--note`, the agent-marker refusal and the PR hook proposed for 2.12.0**

## Context

- **A-F6.** `cmd_resolve_escalation` (qa_ledger.py:9402-9422) records `resolved_at` and an
  optional note — no actor. The engine calls it "un acto humano registrado" (:4013) and
  `uscha-kit/README.md:61` says "a human runs `resolve-escalation`", while the devloop SKILL tells
  the AGENT to run it (SKILL.md:256-257, and :849). A fast-path DENY escalation (INV-RIGOR-02) is
  lifted by the agent with one command. `curate` stamps the OS user when `--human` is absent
  (:6366), so an agent's call carries the human's name.
- **Field feedback** (a real project, kept generic). The operator asked the agent to "push the
  branch and open the PR" right after the build. The agent opened a ready-for-review PR without
  running `phase --require pr-ready` and without saying the ledger read `qa` (no QA steps, no
  test evidence); the missing facts appeared only in the PR body, and the operator had to ask
  "what does uscha say?". Earlier, a QA tool call was refused by the harness; the agent stopped
  without telling the operator the QA loop was left unrun. SKILL Phase 6 says "if it exits 1,
  do NOT open the PR" but not what to do when the human asks anyway.

## Decision

1. **PR-request protocol (SKILL Phase 6).** On any request that amounts to opening a PR, the
   agent runs `phase --require pr-ready` for every repo FIRST. Green → the Phase 6 checklist.
   Red → it shows the missing facts verbatim and asks ONE question: run the QA loop first
   (recommended) or open a DRAFT PR with the missing facts in its body. It never opens a
   ready-for-review PR while red. Pushing a branch is not opening a PR. `test_site: "ci"` repos
   (ADR-055) are always opened as drafts by the agent.
2. **Exception path: draft-only** (owner Q3). While red, the agent opens drafts only; "ready for
   review" is the human's own action in the forge, which the forge authenticates. When the agent
   opens a draft while red it records `pr-opened-not-ready {repo, at, commit, phase, missing[],
   requested_by, note, origin: agent}` (ADR-044 vocabulary); `readiness` and the retrospective
   print it as an exception, never as normal; it changes no derived state.
3. **PreToolUse hook `guard-pr-gate.py`** (Claude target, registered beside the golden hook).
   It blocks `gh pr create` without `--draft`/`-d`, `gh pr ready`, and forge-MCP
   create/update-pull-request calls whose `draft` is not true, when the read-only
   `qa_ledger.py pr-gate --cwd <cwd>` reports that a repo mapped to the cwd (configured path
   containing it, realpath on both sides; none matched → every repo) is not pr-ready. No
   `QA-LEDGER.json` up the cwd → allow (the hook is global). Ledger found but the engine
   missing or failing, or an unparseable payload → block, naming the cause. `doctor` reports
   `pr_guard: enforced | advisory` the way it reports `golden_guard`.
4. **Proactive report (SKILL Phase 3).** When a QA tool cannot run (permission denied, missing,
   crashed), the agent tells the operator at that moment which step did not run, that the loop
   is incomplete, and that the repo cannot reach pr-ready until it runs. It logs no step for it.
5. **Human acts.** The commands that lift `escalated` — exactly the branches of `_derive_phase`
   (:4010-4029): `resolve-escalation`, `spec-doubt --resolve`, `spec-change-request --resolve`,
   `production-finding --resolve` — require `--human NAME --note TEXT`, record `resolved_by`,
   `resolution_note`, `human_declared: true`, and refuse (exit 2, nothing written) when the
   process environment carries a known agent-shell marker. The table starts with `CLAUDECODE`
   (present as `CLAUDECODE=1` in Claude Code's Bash tool environment, measured 2026-10-20); a
   harness with no known marker is UNMEASURED, not trusted. SKILL.md:256-257 and :849 say: STOP,
   show the command, ask the human to run it in their own terminal. `curate` keeps the OS-user
   default (the `uscha top` VERDICTS flow is a human at the keyboard) and records
   `human_source: flag | os-user`.
6. **What is pinned, and why not the agent's words.** The SKILL text is pinned by assertions over
   both twins; the hook by JSON payload probes (exit codes, nothing executed); the engine by
   fixtures. A "smoke test of agent output" is not deterministic — sampling and harness versions
   change the words — so it would be flaky or would pin one model's phrasing.

## What `--human` proves, and what it does not

It proves that a name and a reason were typed, and that the process did not carry a known agent
marker. It does not prove identity: an agent can unset the variable (a deliberate act, visible in
its command text) and Codex/pi expose no marker the engine knows. The only authenticated human
act in this design is the forge's own "ready for review" / merge.

## Alternatives

- **`pr-override --human --note`, HEAD-pinned, letting the hook allow a non-draft PR** (the
  owner's sketch). It records actor and time and changes no derived state, but it is a runtime
  exception to the PR gate — INV-RIGOR-02's letter ("a skipped gate ... never a runtime
  override") — and needs a carve-out in `CONSTITUTION.md` and `uscha-kit/templates/CONSTITUTION.md`.
  Its proof is a declared string where the forge click is authenticated. Not chosen pending Q3;
  if chosen, the event becomes `pr-opened-not-ready` with `human`, and `pr-gate` honors it only
  while `HEAD == commit`.
- **Hook-only refusal of human-act command text.** Bypassed by any `python -c` subprocess; the
  environment marker is inherited by every child process. Kept as the weaker fallback, not used.
- **Require `--human` on `curate` too.** Breaks the `uscha top` VERDICTS flow and the
  reverse-discovery transcription flow for no stronger proof. Rejected; `human_source` recorded.
- **Also `flag-blocker --resolve`.** It clears a fact-gate record and already demands
  `--escape-analysis`; it does not lift `escalated`. Left out of this boundary, stated.

## Consequences

+ The field failure has a written path: gate first, one question, a draft, a recorded exception.
+ An escalation cannot be lifted from the agent's Claude Code shell; elsewhere it is declared.
- Humans type one more command themselves; the agent shows it ready to paste.
- The hook exists only on Claude Code, reads text, and misses `gh api` calls and browser PRs.

## Out of scope

Authenticating identity; forge APIs inside the engine; `flag-blocker --resolve`; `bench-curate`.

## Acceptance (draft, not in ACCEPTANCE.md — rule 8)

- AC-GI-40 — the A-F6 reproduction is refused without `--human`/`--note`; with them it records
  the actor.
- AC-GI-41 — the four escalation-lifting commands refuse under `CLAUDECODE=1`.
- AC-GI-42 — legacy resolved escalations load and read "actor not recorded"; `curate` records
  `human_source`.
- AC-GI-43 — the hook blocks non-draft `gh pr create`, `gh pr ready` and MCP non-draft creates
  while red.
- AC-GI-44 — drafts, and any PR when pr-ready, pass.
- AC-GI-45 — no ledger → allow; engine missing or bad payload → block.
- AC-GI-46 — `pr-opened-not-ready` is recorded and surfaced as an exception.
- AC-GI-47 — both SKILL twins carry the protocol, the proactive report and "STOP and ask".
- AC-GI-48 — install/uninstall/doctor handle `guard-pr-gate.py` like the golden hook.
