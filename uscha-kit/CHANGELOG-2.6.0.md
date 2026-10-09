# uscha-kit 2.6.0 — QA-tool readiness is MEASURED: a declared QA tool that is not installed blocks (ADR-051) (2026-10-09)

## The hole

Phase 3 of the devloop runs QA tools — `qa_tools_order`, by default
`code-review → judgment-day → improve` — that the kit **orchestrates but does not ship**. They
are skills or plugins on the operator's machine, not inside `uscha-kit/`.

And nothing checked they were there. `log-step` accepted any tool name with no existence check,
and `_converged` only asked whether a step for each listed tool had been **logged** — never
whether the tool it named actually resolved and ran. So a loop could converge on a clean board
while trusting a QA pass from a tool that was never installed: the agent "ran judgment-day", the
step was logged, the tool was absent, and the ledger could not tell the difference. A **narrated
dimension** — the exact shape this kit spends its life replacing. The installation of a QA tool is
a FACT, as measurable as a workflow file or a report.

## The resolver — six sources, one function

`resolve_qa_tool` maps a tool name to exactly one **source**, first hit wins:

1. `project-skill` — `./.claude/skills/<name>/SKILL.md`
2. `global-skill` — `<root>/<name>/SKILL.md` under **any** agent skills root the installer knows
   (the engine's one `SKILL_INSTALL_ROOTS` table): `~/.claude/skills` — or
   `$CLAUDE_CONFIG_DIR/skills` —, Codex `~/plugins/uscha/skills`, pi `~/.agents/skills`, cursor,
   copilot, gemini, cline. The row names the root that hit (`source_root` on a logged step), so a
   Codex or pi machine is no longer false-blocked.
3. `plugin` — an installed **and enabled** plugin provides it. Enablement is read from the same
   settings files `doctor` walks (`enabledPlugins`, user → project → project-local, later wins);
   installs from `installed_plugins.json` under the Claude config dir (`~/.claude`, or
   `$CLAUDE_CONFIG_DIR`), in both its list and its version-1 single-record shape. Being in a marketplace **cache** is
   not being installed. A plugin provides the tool when `skills/<skill>/SKILL.md` or
   `commands/<skill>.md` exists under an install path (the official `code-review` and
   `open-code-review` ship only `commands/`); both a bare name and a `<plugin>:<skill>` form are
   accepted. A `scope: project` record counts only when its `projectPath` resolves to the cwd
   (`realpath` on both sides — the Windows 8.3 gotcha).
4. `declared-external` — the human listed it in the new `defaults.qa_tools_external`.
5. `builtin-assumed` — the name is a harness built-in (`HARNESS_BUILTINS = ("code-review",)`). The
   engine is a dependency-free Python script and **cannot introspect what the harness provides**,
   so a built-in is **assumed**, reported honestly as "assumed, harness-provided, not measured" — a
   distinct source, never a false clean and never a FAIL. This is load-bearing: `code-review` is
   first in all five profiles, so a fresh Claude Code machine without the official plugin is not
   blocked.
6. `MISSING` — none of the above.

Only **MISSING** blocks. For project/global/plugin the resolved path and a sha256 are returned; a
broken `installed_plugins.json` is treated as "no plugins", never an exception. Tool matching is
literal — `review` and `open-code-review:review` are different names.

## The gate — a FACT under every profile, no profile knob

New subcommand **`qa-tools-check --repo R`** (the engine's 57th) resolves every tool in the
**effective** `qa_tools_order` and persists `gate:qa-tools` through the same `_append_gate_record`
plumbing every FACT gate uses: a MISSING tool is a `fail` (readiness cap ≤ 65, convergence blocked,
`phase --require pr-ready` refuses NAMING the tool); all resolved is a `pass`. Unlike `operability`
(always exit 0, the gate is the profile's), `qa-tools-check` **exits 1** on a MISSING tool: "a
declared tool is not installed" is a fact under **every** profile, so there is no profile knob.
`qa-tools` is a FACT kind written **only** by `qa-tools-check`, declared in
`templates/CONSTITUTION.md` beside `ci`/`corpus`/`smoke`/`operability` — with **no `log-gate`
door**: `log-gate --kind qa-tools` is refused (exit 2, nothing written). The others carry a
measurement made elsewhere; this one the engine measures itself, so a typed `--verdict pass` would
be a narrated pass. With no
`qa_tools_order` declared there is nothing to resolve — **UNMEASURED**, exit 0, persist nothing; a
list is never synthesized.

## Provenance on every step, and the declared-external escape

`log-step` stamps each step with the resolved `source` (and hash where measured). A MISSING tool's
step is recorded `unverified: true` and does **not** count toward `_converged`: a listed tool is
satisfied only by a step that both exists AND resolved, reported on its own line, distinct from
"never ran". The stamp is taken at log time: a step logged while its tool was MISSING stays
`unverified` after the tool is installed — re-log it. `defaults.qa_tools_external` is a human
declaration of harness/plugin-provided tools to treat as present — a fact about the MACHINE, so
a **live** `uscha.config.json` (cwd, then beside the ledger; never the kit's reference config)
that declares it wins over the ledger's frozen copy, through one function that `qa-tools-check`,
`log-step` and `doctor` all call. Declaring a tool after `init` takes effect on the next check with
no re-init and no ledger write. Precedence is **per key**: a live file that declares the key wins
(an explicit `[]` included — a deliberate withdrawal), a live file that OMITS it leaves the frozen
declaration standing (then the default) — so an unrelated live config can no longer discard the
frozen declaration and turn a declared tool into a false MISSING — and a live value of the wrong
shape (e.g. a string) is refused naming the file and the key, the rule `init` applies, shown by
`doctor` as a warn. The origin is reported as `live-config` / `frozen` / `default`, identically by
the gate and by `doctor`: `doctor --json` gains `effective.qa_tools_external` (`{value, origin}`) —
an additive key, since v2.5.0 had none. It is NOT profile-owned, so `init` never writes it — and it replaces the old
`doctor` "ignore this notice" text: `doctor` now resolves each QA tool through the same resolver
(no more false warnings on `code-review`) and stays WARN-only; a MISSING tool is a warn naming it
and pointing at `qa-tools-check`, which is the gate that blocks.

## Old ledgers, and nothing else moves

Steps written before 2.6.0 carry no `source`/`unverified`, so they load unchanged and are treated
as verified exactly as today. Readiness output is byte-identical — the cap rides the existing
BLOCKER machinery, so no new human line and no new `--json` key were added; the byte-identity pins
AC-FA-03 / AC-FR-06 and the additive-key contract AC-RP-04 are untouched.

## Acceptance

- `docs/adr/ADR-051-qa-tool-readiness-measured.md` (Accepted (2.6.0)); `docs/adr/INDEX.md` gains
  its row (method group).
- A new criteria family `AC-QT-01..13`, measured by smoke **T169** under ISOLATED HOMEs so the
  resolver is machine-independent: the profile-C MISSING case (exit 1, cap, named pr-ready
  refusal), an unverified step that cannot converge, the declared-external escape, profile A asking
  only for `code-review`, old-ledger compatibility, `code-review` as `builtin-assumed`, a
  plugin-resolved tool with a hash, the no-order UNMEASURED case, a RED PROBE that neutralises the
  MISSING return, a SHIPPED PROBE against the v2.5.0 engine out of git (UNMEASURED without git),
  a tool declared in the live config after `init` passing with no re-init while `doctor` and the
  gate report the same value and origin, plus the per-key cases — a live file omitting the key
  keeps the frozen declaration, a live `[]` withdraws it, a live string refuses (`-11`), a skill found only under the pi root resolving
  with a path and a hash (`-12`), and `log-gate --kind qa-tools` refused with exit 2 and the
  ledger unchanged (`-13`) — each of the last three with its own red probe.
- The suite now passes on a machine WITHOUT the QA skills (every CI cell): the five older blocks
  that log `judgment-day`/`improve` (T36, T40, T41, T70, T87) declare them external in their
  fixtures, as their intent is convergence and the FSM, not tool resolution.

## Also fixed (stale docs)

- `uscha-kit/WORKBENCH.md` listed "skills del kit (8)" and omitted `uscha-status` — now 9.
- `formats/uscha-A-field-manual.html` named the Phase-3 tool `improve-deep` — the tool is `improve`.
- `README.md` labelled the engine's subcommand table "kit 1.96.0" next to a current count; the
  stale version label is dropped (the count is the derived fact).

## Not in this release

Part A is ENGINE-ONLY plus the two doc spots. The installer is untouched (the "detect and tell"
half of QA-tool readiness is a separate follow-up); no QA skill is bundled or copied.

Suite: 460 checks · 0 fail; acceptance 355/356.
