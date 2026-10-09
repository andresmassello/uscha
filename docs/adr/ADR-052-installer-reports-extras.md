---
governs:
  - uscha-kit/install-uscha.py
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/skills/uscha-devloop/qa_ledger.py
---
# ADR-052: The installer DETECTS AND TELLS — the dev loop's QA tools and the optional engram are reported, never installed

## Status: Accepted (2.7.0)

## Context

2.6.0 (ADR-051) made "a declared QA tool that is not installed" a FACT gate in the engine:
`qa-tools-check` resolves every tool in `qa_tools_order` and a MISSING one blocks the loop. The
installer said nothing about any of it. A fresh `npx @andresmassello/uscha install` put the nine
kit skills in place and never mentioned that the dev loop's QA tools (`code-review`,
`judgment-day`, `improve`) or the optional memory plugin engram were absent, so a new user first
met MISSING mid-loop, at the gate.

## Decision

The installer **detects and tells**. It reports; it never installs.

- **After the transaction, fail soft.** Detection reads external state only, so it runs AFTER the
  install transaction commits and never changes the exit code of `install` or `doctor`. Any error
  in detection prints `could not check extras: <reason>` and the install still succeeds. The
  transactional install/rollback machinery and the `uscha-install.json` marker schema are
  untouched.
- **One resolver, two callers.** The QA tools are resolved by the engine's own
  `resolve_qa_tool` (ADR-051), imported from the package's engine with `importlib` (no bytecode
  written into the package), never reimplemented. The end-of-install summary and the installer's
  `doctor` (an advisory "extras" section, re-detected live and stateless) call the same path.
  The order is the kit default (`code-review`, `judgment-day`, `improve`), read from the kit's
  reference config and labelled "the kit default order; your project's risk profile may need
  fewer". `code-review` resolves `builtin-assumed` and is reported as "assumed, harness-provided,
  not measured".
- **The target machine, not the caller's.** Resolution is against the `--home` the install
  targets. The resolver's project probes are pointed at a directory that is never created, so
  the directory `npx` runs from does not leak in. A `CLAUDE_CONFIG_DIR` inherited from the shell
  is set aside for an explicit `--home` and honoured when the target is this machine (no
  `--home`), as the harness and `qa-tools-check` honour it.
- **engram is OPTIONAL — uscha does not require it.** Its detection lives only in the installer
  and reads three signals:
  - the `engram` binary on PATH — a walk of the PATH entries, never the current directory unless
    PATH itself names it (`shutil.which` on Windows can search the current directory);
  - the plugin installed AND enabled, through a plugin-level helper, `enabled_plugin_installs`,
    factored out of the engine's registry reader so a plugin name is never pushed through the
    skill resolver. An enabled record whose `installPath` is gone from disk is a stale entry and
    does not count; the installer filters it, the shared helper is unchanged;
  - an MCP server named exactly `engram` — the name the engram plugin's own `.mcp.json`
    declares, never a substring match — wired at MACHINE level: the user-level `mcpServers` of
    `.claude.json`, or the `.mcp.json` of that installed and enabled plugin. A server under
    another project's `projects[<path>]` entry serves that project, not this machine, and does
    not count. Only the Claude configuration is read, for `--target codex` too.

  engram is **present** when it is usable from Claude: the plugin or the MCP server. The binary
  is informational — a machine with only the binary reads missing, with
  `binary found, not wired into Claude`. When it is missing the installer prints
  `claude plugin marketplace add Gentleman-Programming/engram`, `claude plugin install engram` and
  `engram setup claude-code`, and when the binary is not on PATH a note that it is a separate
  download. It never runs any of them.
- **`--dry-run`** writes nothing and lists the checks it would make.

## Why this is an ADR

It changes a published claim. The deck said the kit "never names engram in a single line of what it
publishes"; once the installer reports engram that is false. The claim now reads: the kit declares
no dependencies and installs none, and the installer reports whether the QA tools and the optional
engram are present and how to add them.

## Out of scope

All pending the maintainer's decisions on redistribution and positioning:

- a `--with` flag or any other opt-in install of an extra;
- an interactive prompt;
- copying a QA skill into the target;
- tracking the extras' versions or hashes in the install marker (drift).

## Acceptance

`AC-IX-01..10` (smoke T170), every case under an isolated empty HOME with `CLAUDE_CONFIG_DIR`
dropped and PATH at an empty directory. AC-IX-06 pins the hard boundary both statically (no
process call names `claude`/`engram`, argparse registers no `--with`, there is no call to
`input`) and with `claude`/`engram` stand-ins on PATH that must never be invoked; AC-IX-01 pins
that the target's `skills/` holds exactly the nine kit skills. AC-IX-09 is the red probe and
AC-IX-10 the shipped probe against the v2.6.0 installer.
