# uscha-kit 2.12.0 — human acts are declared and kept out of the agent's shell, and a pull request stays a draft while the gate is red (ADR-058)

## What changed

The last slice of the gate-integrity work (`docs/gate-integrity/SPEC.md` §3.6). It closes the
v2.9.0 audit's A-F6 and the field finding ADR-058 was written for.

- **Human acts.** `resolve-escalation` and the `--resolve` of `production-finding`, `spec-doubt`
  and `spec-change-request` -- exactly the four ways out of the `escalated` phase -- now require
  `--human NAME --note TEXT`, record `resolved_by`, `resolution_note` and `human_declared: true`,
  and refuse (exit 2, nothing written) when the process carries a known agent-shell marker. The
  table starts with `CLAUDECODE`, which Claude Code sets to `1` in its Bash tool. The refusal
  prints the filled-in command for the human to paste into their own terminal.
- **Legacy and `curate`.** Resolutions recorded before 2.12.0 load unchanged and `readiness`
  names them ("actor not recorded"). `curate` keeps its OS-user default (the `uscha top` VERDICTS
  flow is a human at the keyboard) and records `human_source: flag | os-user`.
- **`qa_ledger.py pr-gate [--cwd DIR]`** (read-only): finds `QA-LEDGER.json` up from the cwd,
  maps the cwd to the configured repos that contain it (none matched -> every repo) and prints
  whether each is `pr-ready`, with the missing facts. Exit 0 when all are, or when there is no
  ledger; 1 otherwise.
- **`hooks/guard-pr-gate.py`**, a PreToolUse hook on the Claude target: while `pr-gate` reads
  red it blocks `gh pr create` without `--draft`/`-d`, `gh pr ready`, a forge MCP create without
  `draft: true` and an MCP update that sets `draft: false`. Drafts pass; "ready for review" stays
  the human's act in the forge. No ledger up the cwd -> allow; a ledger with no readable engine,
  or an unparseable payload -> block, naming the cause. Registered by the installer and by the
  plugin's `hooks.json`; `doctor` reports `pr_guard: enforced | advisory` beside `golden_guard`;
  `uninstall` removes it.
- **`qa_ledger.py pr-opened-not-ready --repo R --requested-by NAME --note TEXT`** records a draft
  the agent opened while red (`origin: agent`, commit, phase, missing facts). `readiness` prints it
  as an EXCEPTION; it changes no derived state.
- **The devloop SKILL** (both twins): the human-act commands carry `--human`/`--note`, the agent
  shows them filled in and never unsets the marker; Phase 6 records a red-gate draft with
  `pr-opened-not-ready` and treats a hook block as the gate speaking.

## Behavior changes on upgrade (read before upgrading)

- **The four escalation-lifting commands need `--human` and `--note`.** Scripts that call them
  must pass both; from Claude Code's shell they refuse -- the human runs them.
- **On Claude Code, `gh pr create` without `--draft` is blocked in a uscha project whose gate is
  red.** Reinstall (`npx --yes @andresmassello/uscha@latest install --target claude`) to register the hook.
- The published subcommand count moves from 59 to 61 (`pr-gate`, `pr-opened-not-ready`), with
  their rows in both command-reference docs.

## Pins that moved, on purpose

- The suite's calls to the four commands pass `--human tester --note ...`, so each validation
  case still measures its own rule; `ledger-integrity-regressions.py` likewise.
- The suite unsets `CLAUDECODE` for everything it runs (a test harness, not the agent's hands);
  T175 sets it back where the refusal is what it measures.

## Honest limits

- `--human` proves that a name and a reason were typed outside a known agent shell -- not
  identity. An agent can unset the variable (a deliberate act, visible in its command text), and
  Codex, pi and the other targets expose no marker the engine knows: there the act is declared,
  not refused.
- The hook reads the tool call as TEXT and exists only on Claude Code: `gh api`, a script that
  opens the PR, or a browser get through. The measured control is still `phase --require
  pr-ready`; the only authenticated human act is the forge's own "ready for review" or merge.

## How it is pinned

`AC-GI-40..46, -48` (smoke T175): the A-F6 reproduction and the four refusals under `CLAUDECODE=1`
through the real engine; legacy rows and `human_source`; the hook driven with JSON payloads on
stdin for every PR shape it reads, red and green, plus the no-ledger, no-engine and bad-payload
paths; the exception record; and install/doctor/uninstall over a settings file with a foreign
hook. Each case was red against 2.11.0 before the code existed.

## Evidence

Suite: __SUITE__ checks · 0 fail; acceptance __ACC__.
