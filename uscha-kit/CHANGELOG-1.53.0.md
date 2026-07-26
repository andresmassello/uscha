# uscha-kit 1.53.0 — four more agents, from one table row each (2026-07-25)

The nine skills implement the **Agent Skills** standard, which is why `pi` loaded them
unmodified in 1.51.0. Four more agents read that same standard, so they cost a table row each:
**Cursor**, **VS Code / GitHub Copilot**, **Gemini CLI** and **Cline**. Smoke suite: 392/392,
green on native Windows and on real Linux (WSL Ubuntu 22.04, Python 3.10, Node 24).

## One installer, not five copies
`install_pi` became `install_skills_only(target, ...)`, driven by a `SKILL_ROOTS` table:

| target | root | agent |
|---|---|---|
| `pi` | `~/.agents/skills` | pi (Earendil) |
| `cursor` | `~/.cursor/skills` | Cursor |
| `copilot` | `~/.copilot/skills` | VS Code / GitHub Copilot |
| `gemini` | `~/.gemini/skills` | Gemini CLI |
| `cline` | `~/.cline/skills` | Cline |

`TARGETS` is derived from that table, `--target all` picks new rows up automatically, and the
argparse choices are generated rather than restated — so a sixth agent is one line, with no
second place to forget. The doctor grew one shared branch instead of four. Each install keeps
the transactional shape (stage → back up → atomic replace → marker last), so a late failure
rolls that target back with nothing lost.

**`both` deliberately does NOT grow.** It stays the legacy alias for codex+claude, so existing
scripts keep their exact prior behavior no matter how many targets land.

## `golden_guard` stays honest
INV-GOLDEN-01 is **mechanically enforced on Claude Code only**, where a blocking PreToolUse
hook exists. Every Agent-Skills target reports `advisory` — none of them exposes a blocking
pre-tool hook. pi is the one in waiting: its `tool_call` extension ships
(`uscha-kit/pi/golden-guard.js`), but stays advisory until a real pi run measures the block.

**Not verified, and said plainly:** no target beyond Claude Code and Codex has been exercised
against a real agent. The installer places files where each agent documents reading them; that
they load is a documented expectation, not a measurement. What IS measured: the files land at
the right root, the doctor reads them back, and the marker/version round-trips.

## Fix — the installed Codex manifest still pointed at GitHub
1.51.3 pointed every published surface at uscha.dev, but the Codex plugin manifest that lands
on disk is **generated** (`plugin_manifest()`), not copied from the repo file. Only the repo
file was updated, so every Codex install since then wrote `homepage: github…` while T104
reported the site link healthy — the check was measuring the wrong artifact. The generator is
fixed and **T104 now asserts the generated manifest too**, not just the file.

Regression: smoke **T107** — every `SKILL_ROOTS` row installs its 9 skills plus a marker at its
own root, the doctor reads each back as healthy with `golden_guard: advisory`, no two rows
share a root (a copy-paste typo would make one target clobber another), and `both` is asserted
to still be exactly codex+claude. **T101** was rescoped: it pinned the full `all` roster, so it
broke on every new target; the roster is T107's subject, and T101 now only asserts that `all`
includes `pi`.
