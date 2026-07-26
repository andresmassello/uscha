# Security Policy

Uscha is an `npx`-installable tool that **writes into your agent's configuration**: skill
directories under your home, a `settings.json` entry, and a blocking `PreToolUse` hook. That
makes its installer and its hook the parts worth attacking, and the parts we most want reports
about.

## Reporting a vulnerability

**Report privately — do not open a public issue.**

Use GitHub's [private vulnerability reporting](https://github.com/andresmassello/uscha/security/advisories/new)
on this repository. If that is unavailable to you, write to the address on the author's GitHub
profile with `uscha security` in the subject.

A useful report includes:

- Which component (installer, hook, npm router, ledger/report parser, a skill).
- Kit version (`npx @andresmassello/uscha doctor --target all`) and OS.
- Exact reproduction steps, and the smallest input that triggers it.
- What an attacker gains — arbitrary write, arbitrary execution, disclosure, denial of service.
- Whether it needs an already-compromised agent, or works from a normal repository.

You will get an acknowledgement within **7 days**. If a fix is warranted we will agree on a
disclosure date with you; the default is **90 days or on the fix's release, whichever is first**.
Credit is given unless you ask otherwise.

## Supported versions

Only the **latest published version** receives fixes. This is a solo-maintained project; there
are no backport branches. `npx @andresmassello/uscha@latest` is the supported entry point.

## Security-sensitive components

| Component | Why it matters |
|---|---|
| `uscha-kit/install-uscha.py` | writes into `~/.claude`, `~/.agents`, `~/.cursor`, … and registers a hook |
| `uscha-kit/hooks/block-approved-writes.py` | a `PreToolUse` hook — it sees every tool call |
| `bin/uscha.js` | the npm entry point that launches the Python installer |
| `qa_ledger.py` report parsers | ingest JUnit/coverage/linter XML and JSON from your build |
| `uscha-kit/.claude/skills/*` | instructions your agent will follow |

## What Uscha does NOT protect you from

Stated plainly, because a governance tool that implies security guarantees is worse than one
that claims none. **Uscha is an evidence and governance framework. It is not a sandbox, and it
is not a security boundary.**

It does not protect against:

- **A compromised or adversarial agent.** Every control here assumes the agent is trying to do
  the right thing and may be wrong, not that it is hostile.
- **Prompt injection** reaching the agent through source files, issues, test output or docs.
- **INV-GOLDEN-01 bypass.** The hook matches the tool call as *text*. An indirect write — a
  script that assembles the filename, a symlink, a spawned process — is **not** caught. This is
  asserted by smoke T110, not merely documented. The *measured* control is `golden-diff`, which
  compares bytes. And the hook only exists on the Claude target; every other target reports
  `golden_guard: advisory`.
- **Forged evidence.** The ledger measures reports produced by the same environment being
  evaluated. Freshness checks catch stale reports, not a determined forger.
- **Hostile evidence files.** XML/JSON parsing uses the Python standard library. A deliberately
  malformed or enormous report is a plausible denial-of-service against your own machine.
- **Supply chain upstream of us** — a compromised npm registry, GitHub Action, or agent runtime.

## What is measured

Claims in this repository are backed by the smoke suite (`uscha-kit/tests/smoke-engine.sh`),
run on Linux, macOS and Windows in CI. Where something is **not** measured, the docs say
UNMEASURED rather than implying coverage. If you find a claim that is not backed by a check,
that is a defect worth reporting too — by the project's own rules.
