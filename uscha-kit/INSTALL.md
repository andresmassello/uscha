# Install Uscha

Uscha installs as a machine-level helper for coding agents. The recommended path
is npm/npx because it works the same on a fresh Codex or Claude Code machine.

## Quick path

### Codex Desktop

```bash
npx --yes @andresmassello/uscha@latest version
npx --yes @andresmassello/uscha@latest install --target codex --dry-run
npx --yes @andresmassello/uscha@latest install --target codex
npx --yes @andresmassello/uscha@latest doctor --target codex
```

Then restart Codex or open a new thread. The installer registers Uscha as a
personal local plugin under `~/plugins/uscha` and updates
`~/.agents/plugins/marketplace.json`. It preflights that marketplace before replacing the plugin tree and writes the install marker last.

### Claude Code

```bash
npx --yes @andresmassello/uscha@latest install --target claude --dry-run
npx --yes @andresmassello/uscha@latest install --target claude
npx --yes @andresmassello/uscha@latest doctor --target claude
```

This installs the `uscha-*` skills and registers a portable Python `PreToolUse` hook under `~/.claude` while preserving unrelated `settings.json` entries. Restart or reload Claude Code after installing.

### Same machine uses both

```bash
npx --yes @andresmassello/uscha@latest install --target both --dry-run
npx --yes @andresmassello/uscha@latest install --target both
npx --yes @andresmassello/uscha@latest doctor --target both
```

## Prepare a project repo

After the machine install, initialize each project where Uscha should govern the
workflow:

```bash
npx --yes @andresmassello/uscha@latest init --repo . --dry-run
npx --yes @andresmassello/uscha@latest init --repo .
# Existing differing files are preserved; use --force only to replace them deliberately.
npx --yes @andresmassello/uscha@latest init --repo . --force
```

`init` exits nonzero and reports conflicts for differing `uscha.config.json`, `CLAUDE.md`, `CONSTITUTION.md`, or `.gitattributes`; `--dry-run` performs the same conflict check without writing.

Project state stays in the project: `uscha.config.json`, `QA-LEDGER.json`,
`ACCEPTANCE.md`, and approved golden fixtures when used.

## See the dashboard (mirador)

From the root of any project that has a `QA-LEDGER.json`, one command renders the mirador and
opens it — no python, no paths:

```bash
npx --yes @andresmassello/uscha@latest mirador           # one glance: render + open
npx --yes @andresmassello/uscha@latest mirador --watch   # live second-screen view (auto-refresh)
```

It defaults to the `QA-LEDGER.json` convention in the current directory (pass `--ledger` to
point elsewhere) and prints the absolute path it wrote. `--watch` re-renders every `--interval`
seconds (default 30) into one self-reloading tab.

## Requirements

| Requirement | Why |
|-------------|-----|
| Node.js + npm | Runs the universal `npx` entrypoint. |
| Python 3.8+ | Runs the canonical stdlib installer and engine. |
| Git | Used by the method and by project setup checks. |
| Codex Desktop and/or Claude Code | The agent runtime you want to install Uscha into. |

No `pip install` is required. The engine is Python stdlib-only.

## Other install options

| Option | Use when | Tradeoff |
|--------|----------|----------|
| `npx @andresmassello/uscha@latest ...` | Normal install/update on any machine. | Requires npm registry access. |
| Git checkout + `python uscha-kit/install-uscha.py ...` | Developing Uscha itself or testing unreleased changes. | You must clone/pull the repo yourself. |
| `--mode link` from a checkout | This machine develops the kit and installed skills should follow local edits. | Links are great for development, risky for normal users. |
| Claude Code plugin commands | You specifically want Claude Code's native plugin flow. | Codex still needs the npm/git installer path. |
| Manual copy | Debugging the installer. | Easy to drift; not recommended for adoption. |

Development checkout example:

```bash
git clone https://github.com/andresmassello/uscha.git
cd uscha
python uscha-kit/install-uscha.py install --target both --mode link --dry-run
python uscha-kit/install-uscha.py install --target both --mode link
```

Claude Code plugin option:

```text
/plugin marketplace add andresmassello/uscha
/plugin install uscha@uscha
```

## Update and verify

```bash
npm view @andresmassello/uscha version
npx --yes @andresmassello/uscha@latest version
npx --yes @andresmassello/uscha@latest install --target both
npx --yes @andresmassello/uscha@latest doctor --target both
```

`doctor` exits 1 for any unhealthy target in either text or `--json` mode. It checks installed skill presence, manifest/marketplace or hook registration, marker, and version; it does not measure file-content integrity.

If `npm view` returns `404` immediately after a new release, wait a few minutes:
npm search/dist-tags can propagate before the package metadata endpoint used by
`npx`. Do not republish the same version while propagation is in progress.
