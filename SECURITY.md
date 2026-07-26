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
- **Hostile evidence files.** XML parsing uses the Python standard library (`defusedxml` is
  unavailable: stdlib-only is a hard contract). Since 1.56.1 every parse goes through a **64 MB
  ceiling** (`MAX_REPORT_BYTES`, asserted by smoke T112), which stops the realistic failure --
  a runaway or oversized report exhausting memory. It is **not** protection against a
  determined attacker: entity expansion *under* the ceiling still expands.
- **Supply chain upstream of us** — a compromised npm registry, GitHub Action, or agent runtime.

## Security notes (for whoever runs a scanner here)

A static scanner will flag the following. Each is a deliberate decision with its reasoning, not
an oversight — so you can judge it instead of filing it.

**`sha1` — 4 call sites, and none of them is security.** It fingerprints findings so the engine
can detect *oscillation* (the same finding disappearing and returning across QA cycles), and it
hashes line windows for duplicate detection in `waste-check`. Collisions there produce a wrong
*advisory count*, never an authorization or integrity decision. Ledger integrity uses **sha256**
(`_integrity_hash`). Flagged by ruff as `S324`.

**`ET.parse` on report files.** Flagged as `S314`. ruff prescribes `defusedxml`, which is a new
runtime dependency — and *stdlib-only* is the constraint that lets this engine run anywhere
Python does, with no `pip install`. Since 1.56.1 every parse goes through a 64 MB ceiling
(above). The residual risk is stated, not hidden: entity expansion under the ceiling still
expands.

**ruff's `S` (bandit) rule set is deliberately NOT enabled.** `ruff.toml` selects
`["E4", "E7", "E9", "F", "B"]`. Enabling `S` yields 61 findings that the engine would map to
HIGH, of which the ones that matter are the two above — both already analysed and decided. A
gate that fires 61 times for two real items trains the reader to ignore the gate, which is
worse than not having it. The full analysis lives in
[`ISSUES-DEFERRED.md`](ISSUES-DEFERRED.md), with severity and evidence per finding.

**The coverage number is scoped to the engine.** `uscha.config.json` declares exactly one repo
(`uscha`) with a threshold of 60. It is not a claim about anything else, and the ledger records
which repo produced which report.

**No model telemetry reaches the engine.** `qa_ledger.py` never reads tokens, model names or
vendor data — smoke **AC-04** asserts it. Vendor-reported numbers can only enter through an
adapter (the mirador's telemetry strip), never through the measurement path.

## What is measured

Claims in this repository are backed by the smoke suite (`uscha-kit/tests/smoke-engine.sh`),
run on Linux, macOS and Windows in CI. Where something is **not** measured, the docs say
UNMEASURED rather than implying coverage. If you find a claim that is not backed by a check,
that is a defect worth reporting too — by the project's own rules.
