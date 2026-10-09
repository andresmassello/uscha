---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/.claude/skills/uscha-devloop/SKILL.md
  - uscha-kit/skills/uscha-devloop/SKILL.md
  - uscha-kit/templates/CONSTITUTION.md
---
# ADR-051: QA-tool readiness is MEASURED — a declared QA tool that is not installed blocks, under every profile

## Status: Accepted (2.6.0)

## Context

Phase 3 of the devloop runs QA tools — `qa_tools_order`, by default
`code-review -> judgment-day -> improve` — that the kit **orchestrates but does not ship**. They
are skills or plugins that live on the operator's machine, not inside `uscha-kit/`.

And nothing checked they were there. `log-step` accepted any tool name with no existence check,
and `_converged` only asked whether a step for each listed tool had been **logged** — not whether
the tool it named actually resolved and ran. So a loop could converge on a clean board while
trusting a QA pass from a tool that was never installed: the agent "ran judgment-day", the step
was logged, the tool was absent, and the ledger could not tell the difference. That is the exact
shape this kit exists to refuse — a **narrated dimension**, producing the same output whether the
work happened or not (ADR-048 named the pattern; ADR-043 drew the line between a fact and an
opinion). The installation of a QA tool is a FACT, as measurable as a workflow file or a report.

## Decision

Turn "a declared QA tool is not installed" into a measured fact that blocks.

### The resolver — six sources, one function

`resolve_qa_tool(name, declared_external, project_root, home)` maps a tool name to exactly one
**source**, in this resolution order (first hit wins):

1. `project-skill` — `./.claude/skills/<name>/SKILL.md`
2. `global-skill` — `<root>/<name>/SKILL.md` under **any** agent skills root the installer knows,
   probed in the order of the engine's one `SKILL_INSTALL_ROOTS` table (never retyped): claude
   (`~/.claude/skills`, or `$CLAUDE_CONFIG_DIR/skills` when that variable is set), codex
   (`~/plugins/uscha/skills`), pi (`~/.agents/skills`), cursor, copilot, gemini, cline. The row
   records WHICH root resolved (`root`, and `source_root` on a logged step). Probing only
   `~/.claude/skills` false-blocked a Codex or pi machine that keeps the same skill in its own root.
3. `plugin` — an installed **and enabled** plugin provides it. Enablement is read from the same
   settings files `doctor` walks (user `~/.claude` — or `$CLAUDE_CONFIG_DIR` —, project `.claude`,
   project-local; later wins per key) via `enabledPlugins`; the installs are read from
   `<claude config dir>/plugins/installed_plugins.json` (shape `{"version": N, "plugins":
   {"<name>@<mkt>": [ {scope, installPath, projectPath?, ...} ]}}`; a version-1 registry maps a key
   to ONE record object instead of a list, and both shapes resolve). Being in a **marketplace cache** is not being
   installed — only `installed_plugins.json` lists installs. A plugin provides the tool when
   `skills/<skill>/SKILL.md` **or** `commands/<skill>.md` exists under one of its install paths
   (both the official `code-review` plugin and `open-code-review` ship only `commands/`). Both a
   bare name and a `<plugin>:<skill>` form are accepted (the harness lists e.g.
   `open-code-review:review`). A `scope: project` record is honored only when its `projectPath`
   resolves to the cwd — `os.path.realpath` on BOTH sides (the Windows 8.3 short-path gotcha);
   `scope: user` always counts.
4. `declared-external` — the human listed the tool in `defaults.qa_tools_external` (new knob).
5. `builtin-assumed` — the name is in a hardcoded `HARNESS_BUILTINS = ("code-review",)`. The
   engine is a dependency-free Python script and **cannot introspect what the harness provides**,
   so a built-in is **assumed**, reported honestly as "assumed, harness-provided, not measured" —
   a DISTINCT source, never a false clean and never a FAIL. This is load-bearing: `code-review` is
   first in all five risk profiles, and on a fresh Claude Code machine (no skill dir, no official
   plugin) it has nowhere else to resolve. Without this honest assumption every loop on such a
   machine would be blocked.
6. `MISSING` — none of the above.

For `project-skill` / `global-skill` / `plugin` the resolved path and a sha256 of the SKILL.md
(or plugin command) are returned; `builtin-assumed` / `declared-external` / `MISSING` carry
neither — nothing was measured. A broken or unreadable registry is treated as "no plugins", never
an exception: a malformed `installed_plugins.json` must not turn `code-review` into MISSING (it
still falls to `builtin-assumed`). Tool matching is **literal** — `review` and
`open-code-review:review` are different names, resolved as written.

Only **MISSING** blocks. The five other sources all count as present.

### The gate — a FACT under every profile, no profile knob

New subcommand `qa-tools-check --repo R` resolves every tool in the **effective** `qa_tools_order`
(never the hardcoded three) and persists `gate:qa-tools` through the same `_append_gate_record`
plumbing every other FACT gate uses: any MISSING tool is a `fail` (readiness cap ≤ 65, convergence
blocked, `phase --require pr-ready` refuses NAMING the tool); all resolved is a `pass`. Unlike
`operability`, whose own exit code is always 0 because the gate is the profile's, `qa-tools-check`
**exits 1** when a tool is MISSING: "a declared tool is not installed" is a fact under **every**
profile, so there is no profile knob and `qa-tools` is NOT advisory-capable. It is a FACT kind
written **only** by `qa-tools-check`, declared in the `CONSTITUTION.md` template beside
`ci`/`corpus`/`smoke`/`operability` — and, unlike them, it has **no `log-gate` door**:
`log-gate --kind qa-tools` is refused by argparse (exit 2, nothing written). `ci`, `corpus` and
`smoke` keep a door because their measurement happens elsewhere (a pipeline, a nightly) and must
be carried in; here the engine measures the fact itself, so a `--verdict pass` typed through a
door would be a narrated pass with no resolution behind it — the false clean uscha refuses.

With no `qa_tools_order` declared (window convergence) there is nothing to resolve:
`qa-tools-check` reports **UNMEASURED**, exits 0 and persists nothing — a list is never
synthesized.

### Provenance on every step

`log-step` stamps each agent step with the resolved `source` (and the SKILL.md / plugin hash where
one was measured). A step whose tool resolves to MISSING is recorded `unverified: true` and does
**not** count toward `_converged`: in the `qa_tools_order` branch a listed tool is satisfied only
by a step that both exists AND resolved, reported on its own line, distinct from "never ran".
The stamp is taken at LOG time: a step logged while its tool was MISSING stays `unverified` after
the tool is installed — the ledger does not rewrite history; re-log the step.

### The declared-external escape

`defaults.qa_tools_external` is a human declaration of tools that are harness built-ins or
plugin-provided and should be treated as present. It is a fact about the **machine** — which
tools are installed — not a run parameter, so a **live** declaration wins over the ledger's
frozen copy: one function (`_effective_qa_external`, over the same `_resolved_defaults` machinery
`doctor` reports) serves `qa-tools-check`, `log-step` provenance and `doctor`. It finds the live
`uscha.config.json` the 1.98.0 way — the cwd, then beside the ledger — never the kit's own
reference config. Precedence is **per key**: a live file that declares `qa_tools_external` wins
(an explicit `[]` included — a deliberate withdrawal); a live file that omits the key falls back
to the frozen value, then to the default, exactly as when no live file exists — an unrelated live
config never silently discards the frozen declaration. A live file that exists but cannot be read
or resolved, or that declares the key with the wrong shape (anything but a list of unique
nonempty strings, the rule `init` applies), refuses, naming the file and the key; `doctor` shows
it as a warn. The origin is recorded as `live-config`,
`frozen` or `default` (declared nowhere), and a `declared-external` step carries it as
`source_origin`. Declaring a tool after `init` therefore takes effect on the next
`qa-tools-check`, with no re-init, and nothing writes the ledger (its integrity hash is
untouched). Only this key moves: `qa_tools_order` stays the frozen run parameter. It is NOT
profile-owned — no risk profile supplies it, so `init` never writes it (AC-RP-06 stays green) —
and it REPLACES the old `doctor`
"ignore this notice" text: `doctor` now resolves each QA tool through the same six-source resolver
(so a plugin/builtin/declared tool no longer false-warns) and stays WARN-only (exit code
unchanged); a MISSING tool is a warn naming it and pointing at `qa-tools-check`, which is the gate
that blocks.

## Consequences

- A loop can no longer converge trusting a QA tool that never ran.
- Old ledgers are unaffected: steps written before 2.6.0 carry no `source`/`unverified`, so they
  load unchanged and are treated as verified exactly as today.
- Readiness output is byte-identical: the cap rides the existing BLOCKER machinery, so no new
  human line and no new `--json` key were added (the byte-identity pins AC-FA-03 and AC-FR-06, and
  the additive-key contract AC-RP-04, are untouched).

## What stays UNMEASURED

- With no `qa_tools_order` declared, there is nothing to resolve — reported UNMEASURED, never a
  pass.
- A **harness built-in** is ASSUMED, not measured: the engine cannot see what the harness
  provides, and it says so rather than reporting a clean it did not observe.
