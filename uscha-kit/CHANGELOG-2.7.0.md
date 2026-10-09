# uscha-kit 2.7.0 — the installer DETECTS AND TELLS: the dev loop's QA tools and the optional engram are reported, never installed (ADR-052) (2026-10-09)

## The gap

2.6.0 (ADR-051) made "a declared QA tool that is not installed" a FACT gate in the engine:
`qa-tools-check` resolves every tool in `qa_tools_order` and a MISSING one blocks the loop. The
installer still said nothing. A fresh `npx @andresmassello/uscha install` put the nine kit skills in
place and never mentioned that the dev loop's QA tools (`code-review`, `judgment-day`, `improve`)
or the optional memory plugin engram were absent, so a new user first met MISSING mid-loop, at the
gate. 2.6.0's changelog left the "detect and tell" half of QA-tool readiness as a separate
follow-up; this is it.

## What the installer now prints

After the install transaction commits, `install` ends with an **extras report**. On an empty
machine:

```
Extras -- reported only, never installed:
  QA tools for the dev loop (the kit default order; your project's risk profile may need fewer):
    code-review    builtin-assumed -- assumed, harness-provided, not measured
    judgment-day   MISSING
    improve        MISSING
    A MISSING tool blocks the dev loop (qa-tools-check): install it as a skill or plugin, or declare it in defaults.qa_tools_external.
  engram (optional -- uscha does not require it): missing
    binary on PATH: no | plugin installed and enabled: no | MCP server in the Claude config: no
    To add it, run these yourself (this installer never runs them):
      claude plugin marketplace add Gentleman-Programming/engram
      claude plugin install engram
      engram setup claude-code
    The engram binary itself is a separate download.
```

A machine with the engram binary on PATH but nothing wiring it into Claude reads missing:

```
  engram (optional -- uscha does not require it): missing
    binary on PATH: yes | plugin installed and enabled: no | MCP server in the Claude config: no
    binary found, not wired into Claude
    To add it, run these yourself (this installer never runs them):
      claude plugin marketplace add Gentleman-Programming/engram
      claude plugin install engram
      engram setup claude-code
```

- **One resolver, two callers.** The QA tools are resolved by the engine's own `resolve_qa_tool`,
  imported from the package's engine with `importlib` (no bytecode written into the package), never
  reimplemented — so the installer and `qa-tools-check` cannot disagree. The end-of-install summary
  and the installer's `doctor` (a new advisory "extras" section, re-detected live and stateless)
  call the same path; `--json` carries it as an additive `extras` key.
- **The target machine.** Resolution is against the `--home` the install targets; the resolver's
  project probes point at a directory that is never created, so the directory `npx` runs from does
  not leak in. An inherited `CLAUDE_CONFIG_DIR` is set aside for an explicit `--home` and honoured
  when the target is this machine.
- **engram is OPTIONAL.** Three signals: the binary on PATH (a walk of the PATH entries that never
  consults the current directory unless PATH names it — `shutil.which` on Windows can); the plugin
  installed AND enabled with its `installPath` on disk (a stale registry entry does not count); and
  an MCP server named exactly `engram`, the name the engram plugin's own `.mcp.json` declares, wired
  at machine level — the user-level `mcpServers` of `.claude.json` or that plugin's `.mcp.json`,
  never another project's `projects[<path>]` entry. Only the Claude configuration is read, for
  `--target codex` too. engram is **present** when it is usable from Claude — the plugin or the MCP
  server; the binary alone is informational and reads missing, `binary found, not wired into
  Claude`. The plugin check uses a plugin-level helper, `enabled_plugin_installs`, factored out of
  the engine's registry reader (both engine twins, byte-identical): a plugin name is never pushed
  through the skill resolver, and `_resolve_plugin_tool` now reads through the same helper with its
  behaviour unchanged. The stale-installPath filter lives in the installer, not in that helper.
- **Fail soft.** Detection reads external state only and runs after the transaction: any error
  prints `could not check extras: <reason>` and the install still succeeds. `--dry-run` writes
  nothing and lists the checks it would make.

## The hard boundary

The installer installs nothing beyond what it installed in 2.6.0, adds no `--with` flag, shows no
prompt, copies no QA skill and runs no `engram` or `claude plugin` command — each pinned by T170:
argparse registers no `--with` and there is no call to `input` (static AST checks), the target's
`skills/` holds exactly the nine kit skills, and `claude`/`engram` stand-ins on PATH are never
invoked. The exit codes of
`install` and `doctor` are what they were for every existing scenario; a missing extra is never an
error. The transactional install/rollback machinery and the `uscha-install.json` marker schema are
untouched, and no extras version or hash is recorded in the marker (drift tracking is out of
scope).

## Docs (truth-pass)

- The deck twins said the kit "never names engram in a single line of what it publishes" — false
  once the installer reports engram, and already loose because the deck itself names it. Both twins
  now say the kit declares no dependencies and installs none, and the installer reports whether the
  QA tools and the optional engram are present and how to add them, but never installs them.
- `README.md` and `uscha-kit/README.md` describe the extras report; both `FIRST-USE` twins gain one
  line saying the install ends with it from 2.7.0 (no install transcript is shown there, and the
  guide runs the published `@latest`, so no new transcript is claimed before it is published).

## Acceptance

- `docs/adr/ADR-052-installer-reports-extras.md` (Accepted (2.7.0)); `docs/adr/INDEX.md` gains its
  row (method group).
- A new criteria family `AC-IX-01..10`, measured by smoke **T170**, every case under an isolated
  empty HOME/USERPROFILE with `CLAUDE_CONFIG_DIR` dropped and PATH at an empty directory — this
  release's output depends on what the machine has, and the dev box has everything: the empty-home
  contract, a planted global skill, the engram signals (an enabled, disabled, stale or version-1
  plugin, a binary alone, a user-level MCP server, a name that only contains `engram`),
  `--dry-run` writing nothing, an injected detection failure, the hard boundary pinned statically
  AND with `claude`/`engram` stand-ins on PATH that must never be invoked, unchanged exit codes with
  one detection path for both callers, machine scope (the cwd, an engram binary in the cwd,
  another project's MCP server and an inherited config dir do not leak), a
  RED PROBE that forces detection to report everything present, and a SHIPPED PROBE against the
  v2.6.0 installer out of git (UNMEASURED without git).

## Also on main since v2.6.0

- `docs(paper)`: the paper cites Cloudflare's Agent Development Lifecycle in Related Work, as
  positioning, not validation.

## Not in this release

`--with`, interactive prompts, copying QA skills and marker drift tracking — all pending the
maintainer's decisions on redistribution and positioning.

Suite: 461 checks · 0 fail; acceptance 365/366.
