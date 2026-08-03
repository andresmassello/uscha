# Uscha

**Spec-driven development for LLM coding agents.** *You bring the idea, the method builds
the rest.* Uscha gives a coding agent a spec to build against, a QA loop that converges
instead of looping forever, and a deterministic ledger that records what was **measured** —
never what was claimed.

> The tool executes · the method governs · evidence decides · the human approves.

**[uscha.dev](https://uscha.dev)** — the method, the five rules, the skills, the library
(essay, 2-day dev course, reference, paper).

```bash
npx --yes @andresmassello/uscha@latest install --target claude   # Claude Code
npx --yes @andresmassello/uscha@latest install --target codex    # Codex
npx --yes @andresmassello/uscha@latest install --target cursor   # Cursor
npx --yes @andresmassello/uscha@latest install --target copilot  # VS Code / GitHub Copilot
npx --yes @andresmassello/uscha@latest install --target gemini   # Gemini CLI
npx --yes @andresmassello/uscha@latest install --target cline    # Cline
npx --yes @andresmassello/uscha@latest install --target pi       # pi (Earendil)
npx --yes @andresmassello/uscha@latest install --target all      # every target at once

npx --yes @andresmassello/uscha@latest doctor --target all
```

The nine skills implement the **Agent Skills** standard, so the last five targets are the same
skills placed under each agent's own documented root. Honest scope: only Claude Code and Codex
have been exercised against a real agent — for the rest, that they load is a *documented
expectation, not a measurement*. What is measured is that the files land where each agent
documents reading them and that `doctor` reads them back. INV-GOLDEN-01 is mechanically
enforced only on Claude Code (a blocking PreToolUse hook); everywhere else `doctor` reports it
as `advisory` rather than implying a guard it cannot see.
(`both` stays a legacy alias for codex+claude.) Then, in your project:

```bash
npx --yes @andresmassello/uscha@latest init
```

Requires **Python 3.8+** on the machine (the engine is Python stdlib — no pip installs, no
runtime dependencies). The npm package is a thin router; the canonical installer is
`uscha-kit/install-uscha.py`.

**Kit v1.61.0** <!-- uscha:version --> · [uscha.dev](https://uscha.dev) ·
[changelog](https://github.com/andresmassello/uscha/blob/main/uscha-kit/CHANGELOG.md)
(the per-release changelogs live in the repo, not in the npm tarball)

---

## The problem it solves

An agent will tell you the tests pass. It will tell you the feature is done. It is often
right — and when it is wrong, you find out in production.

Uscha refuses to take the agent's word for anything. Every claim that matters has to be
backed by a report the agent did not write: a JUnit file, a coverage report, a linter's
output. **Facts block; guesses advise.** A checkbox ticked by hand is recorded as
`narrated` and does not close a criterion. A test named after that criterion, green, in an
ingested report — that closes it.

The result is a readiness score you can actually trust, because you can click any number
and see which file, which test, and when.

## What you get

**Nine skills** that drive the method end to end:

| Skill | What it does |
|---|---|
| `/uscha-discovery` | Idea → spec package (CONTEXT, SPEC, ADRs, CONSTITUTION, ACCEPTANCE) |
| `/uscha-adr-refine` | Known feature → ADR + ACCEPTANCE, by interrogating you first |
| `/uscha-reverse-discovery` | Existing system → extracted facts (brownfield migrations) |
| `/uscha-characterize` | Capture a golden suite of current behavior before touching it |
| `/uscha-devloop` | Plan → build → severity-gated QA loop → PR (stops at the merge) |
| `/uscha-rubric` | Grade the non-testable (conventions, ergonomics) against a versioned rubric |
| `/uscha-sysdoc` | Generate a system deck from the ledger |
| `/uscha-mirador` | Bird's-eye HTML dashboard: readiness, trail, acceptance, loops |
| `/uscha-status` | One-line progress readout, in chat |

**A measurement engine** (`qa_ledger.py`, 32 subcommands, Python stdlib) that ingests
evidence from **11 language stacks** — maven, gradle, ant, python, node, go, rust, dotnet,
cpp, swift, flutter — and computes a readiness score with hard caps and visible provenance.

## Compatibility matrix

Generated from `TARGETS`/`SKILL_ROOTS` in the installer, so it cannot drift from the code.

| target | agent | installs to | INV-GOLDEN-01 | exercised against a real agent |
|---|---|---|---|---|
| `codex` | Codex | `~/plugins/uscha` | advisory | **yes** |
| `claude` | Claude Code | `~/.claude/skills` | **enforced** (PreToolUse hook, best-effort) | **yes** |
| `pi` | pi (Earendil) | `~/.agents/skills` | advisory | no — placement + read-back only |
| `cursor` | Cursor | `~/.cursor/skills` | advisory | no — placement + read-back only |
| `copilot` | VS Code / Copilot | `~/.copilot/skills` | advisory | no — placement + read-back only |
| `gemini` | Gemini CLI | `~/.gemini/skills` | advisory | no — placement + read-back only |
| `cline` | Cline | `~/.cline/skills` | advisory | no — placement + read-back only |

**"Exercised" is the column that matters.** For every target but Claude Code and Codex, what
is measured is that the nine skills land where that agent documents reading them and that
`doctor` reads them back — *that they load is a documented expectation, not a measurement.*
INV-GOLDEN-01 is mechanically attempted only where a blocking pre-tool hook exists; everywhere
else `doctor` reports `advisory` rather than implying a guard it cannot see.

| OS | how it is verified | status |
|---|---|---|
| Linux | CI matrix (py3.8 + py3.13) + local WSL | **measured** |
| Windows | CI matrix (py3.8 + py3.13) + native local | **measured** |
| macOS | CI matrix (py3.8 + py3.13), real runners | **measured** |

## The loop, in short

1. **Model first.** `/uscha-discovery` (new) or `/uscha-adr-refine` (known feature) writes
   the spec package. No code until the package exists.
2. **Build.** `/uscha-devloop` implements against the SPEC, with tests as a guardrail.
3. **QA loop.** Independent review passes (maker ≠ checker) run until the change
   **converges** — findings at or above the severity gate are fixed, the rest go to
   `ISSUES-DEFERRED.md` with their evidence. Converge, don't chase zero.
4. **Readiness.** One score, one screen: acceptance (measured) 30 · static gate 20 ·
   ADR 15 · coverage 15 · convergence 10 · integration 10, with hard caps that say *why*
   they bit and whether the threshold was your requirement or the kit's default.
5. **You decide.** The agent proposes, measures and stops at the PR. Merging is a human act.

## What makes it different

- **Measured beats narrated.** An acceptance criterion closes on a green test that carries
  its name — never on a checkbox. Stale evidence (a report older than the code) is
  discarded, not honored.
- **Absence is not success.** A gate that never ran scores `UNMEASURED`, which is
  deliberately *not* the same as a measured zero — and it is not silently forgiven either.
- **Receipts.** Every number in the dashboard traces to its evidence: which testcase, which
  report, which timestamp.
- **Anti-ceremony.** Gates stay quiet by default and collapse into one verdict line. The
  method is enforced by the engine, not by asking the agent to be disciplined.
- **Model-agnostic.** The engine never reads tokens, model names or vendor telemetry. Any
  model-reported number enters through an adapter, never the engine.

## Documentation

- **[`uscha-kit/INSTALL.md`](uscha-kit/INSTALL.md)** — full install guide (npm, git, plugin)
- **[`uscha-kit/README.md`](uscha-kit/README.md)** — kit reference: configuration, every
  subcommand, the readiness KPI, the simplicity and rebuild gates
- **[`docs/`](docs/)** — the long deck, the operator's playbook, a skills reference and a
  one-pager (ES + EN)
- **[`docs/paper/`](docs/paper/)** — the method written up as a paper

Each release ships a `uscha-kit/CHANGELOG-X.Y.Z.md` explaining what changed and why.

## Developing Uscha itself

This repository is the source of the kit, and the method is applied to itself: it carries
its own `uscha.config.json`, `ACCEPTANCE.md` and `CONSTITUTION.md`, and its readiness is
measured by the same engine it ships.

```
uscha-kit/              # canonical source of the kit
  .claude/skills/       #   the 9 skills + qa_ledger.py (the engine)
  templates/            #   CLAUDE.md · CONSTITUTION.md · scripts · docs/adr
  tests/smoke-engine.sh #   the suite every engine change must pass
docs/                   # published artifacts (ES/EN twins) + the paper
audits/                 # adversarial audit outputs
```

The rules are in [`CLAUDE.md`](CLAUDE.md). The short version: no doc may claim what the
engine does not do; the ES and EN twins travel together; every engine change carries a
smoke test; and a PreToolUse hook stops the agent from writing a `.approved` golden.
**Scoped honestly**: that hook is a *best-effort* guard and it is registered on the Claude
target only — it inspects a tool call as TEXT, so an indirect write (a script that assembles
the filename, a symlink) gets through, and every other target reports `golden_guard:
advisory`. The MEASURED control is `golden-diff`, which compares bytes.

## History

Born as a methodology for working with Claude Code, distilled with the Böckeler principle
(computational blocks, inferential advises), and put through two adversarial audits (231
agents) that found the central principle **inverted in the code** — 1.3.0 flipped it right.
The details are in `audits/` and in the changelogs.

## License

MIT — see [`LICENSE`](LICENSE).
