# Uscha

**Uscha** is a spec-driven, tool-agnostic methodology for development with
LLM coding agents — *you bring the idea, the method builds the rest* — with its
instantiation in Claude Code, the **uscha-kit**.

> **On the name.** *Uscha* is the methodology's name; the pattern it operationalizes is a *spec-loop* — the concept, not the branding. The name was chosen partly to avoid collision with [spec-loop](https://github.com/dpolivaev/spec-loop) by D. Polivaev — an independently developed, actively maintained project that shares the term and the spec-driven, review-per-increment philosophy while taking a different implementation path (shell-based agent skills via npx). It was found late in this project's development; the two are convergent, not derivative. (The local checkout keeps the path `SpecLoop`.)

> The tool executes · the method governs · evidence decides · the human approves.

## Repo map

```
SpecLoop/
??? package.json        # npm package: @andresmassello/uscha
??? bin/uscha.js        # thin npx router to uscha-kit/install-uscha.py
├── uscha-kit/          # ★ canonical SOURCE of the kit (v1.41.2)
│   ├── .claude/skills/    #   8 skills: uscha-discovery · uscha-adr-refine · uscha-devloop · uscha-sysdoc
│   │                      #             uscha-reverse-discovery · uscha-characterize · uscha-rubric · uscha-mirador
│   ├── .claude/skills/uscha-devloop/qa_ledger.py   # evidence engine (29 subcommands, stdlib)
│   ├── hooks/             #   PreToolUse: the agent never writes .approved (INV-GOLDEN-01)
│   ├── templates/         #   CLAUDE.md · CONSTITUTION.md · .gitattributes · docs/adr
│   └── CHANGELOG-*.md     #   1.2.x → 1.3.0 ("facts block, wired") → 1.4.0 (python) → 1.5.0 (node) → 1.6.0 (go) → 1.7.0 (rust+dotnet) → 1.8.0 (cpp) → 1.9.0 (gradle+swift) → 1.10.0 (traceable acceptance) → 1.11.0 (tests outside the budget) → 1.12.0 (secret-scan) → 1.13.0 (atomic ledger) → 1.14.0 (plateau/stop-signal) → 1.15.0 (golden scrub) → 1.16.0 (regression-capture) → 1.17.0 (threshold provenance) → 1.18.0 (derived FSM) → 1.19.0 (spikes — PragProg backlog CLOSED) → 1.20.0 (global install) → 1.21.0 (namespace uscha-*) → 1.22.0 (doctor) → 1.23.0 (rubric layer) → 1.24.0 (Claude Code plugin) → 1.25.0 (anti-ceremony) → 1.26.0 (waste-check REUSE-FIRST) → 1.27.0 (FTY) → 1.28.0 (measured acceptance %) → 1.29.0 (rebrand → Uscha) → 1.30.0 (dependency gate) → 1.31.0 (evidence freshness + doc-version gate) → 1.32.0 (mirador — bird's-eye view + dashboard --json) → 1.33.0 (mirador telemetry — per-model tokens/time/model + transcript extractor) → 1.34.0 (mirador: project name from config + live watch/auto-refresh) -> 1.35.0 (execution-policy routing) -> 1.36.0 (discovery-intake: production findings + spec-doubt) -> 1.37.0 (ADR experiments: visible hypotheses) -> 1.38.0 (contract closure: SCR bridge + golden labels + calibration) -> 1.39.0 (universal Codex/Claude installer) -> 1.40.0 (npm/npx router) -> 1.40.1 (npm package hygiene) -> 1.40.2 (install docs) -> 1.41.0 (safety release) -> 1.41.1 (adversarial-review hardening: JUnit/integration evidence + Codex rollback) -> 1.41.2 (mirador launch UX: self-resolving render + auto-open + honest readiness title)
├── docs/                  # published artifacts (canonical here; Downloads = snapshots)
│   ├── uscha-claude-code-doc-FINAL.html   # long deck ES (36 slides)
│   ├── uscha-claude-code-doc-EN.html      # long deck EN
│   ├── uscha-playbook{,-EN}.html          # Operator's Manual (trigger/move/gate)
│   ├── uscha-onepager{,-EN}.html          # one-page sheet
│   ├── uscha-team-pitch.html              # team adoption pitch (Vale/Martín story, 14 slides)
│   ├── uscha-team-pitch-extended.html     # extended pitch: + typical day, readiness KPI, 2-story ledger, pilot (22 slides)
│   ├── skills-referencia.html                 # exhaustive reference of the 8 skills (what each does, phase by phase)
│   ├── casos-reales.md                        # logbook: real moments where the method intervenes (anonymized)
│   ├── *.png                                  # system map · 10 steps · reverse-discovery
│   └── diagram-sources/                       # source HTML of the PNGs (re-renderable)
├── formats/               # 6 format explorations (A-F); playbook + atlas-map were adopted
└── audits/                # outputs of the adversarial audits (2026-07)
    ├── audit-metodologia-7-lentes.json        # 33 weaknesses confirmed / 13 refuted
    ├── audit-fidelidad-doc-codigo-idea.json   # 171 claims verified doc↔code↔idea
    ├── truth-pass-6-docs.json                 # 130 truthfulness edits post-wiring
    └── verificacion-team-pitch.json           # 3 lenses over the pitch
```

## Status (2026-07-10)

- **Kit v1.41.2** <!-- uscha:version --> — the fact-gates are WIRED into the engine (1.3.0: `log-gate`,
  `flag-blocker`, `resolve-escalation`; UNMEASURED; per-tool convergence with a veto from
  the measured snapshot) and the engine measures **Python** repos (1.4.0: pytest/Cobertura + ruff +
  mypy) **TypeScript/JS** (1.5.0: lcov + jest-junit + eslint + tsc) **Go** (1.6.0: native cover
  profile + gotestsum + golangci via checkstyle), **Rust** (1.7.0: Cobertura +
  nextest + clippy) **C#/.NET** (1.7.0: coverlet + junit
  logger + SARIF/Roslyn), **C++** (1.8.0: gcovr/Cobertura + ctest junit +
  clang-tidy), **Kotlin/JVM Gradle** and **Swift** (1.9.0: zero new parsers —
  JaCoCo/lcov/JUnit/checkstyle reused; detekt + SwiftLint). **Traceable acceptance** (1.10.0: AC-n closes on a
  MEASURED testcase, the dominant dimension of readiness — M2 of the PragProg backlog). **Tests outside
  the simplicity budget** (1.11.0: writing tests does not penalize the gate — M9).
  **Secret-scan in gate-check** (1.12.0: added private keys/tokens/containers
  block as a fact — M8). **Atomic ledger** (1.13.0: integrity checksum + hardened
  load — M3). **Plateau/stop-signal** (1.14.0: stall and PR-candidate as
  advisories — M6). **Golden scrub** (1.15.0: declared volatiles are masked with
  visible masking — M7). **Regression-capture** (1.16.0: closing findings without a test =
  narrated; escape-analysis mandatory when resolving blockers — M1). **Threshold
  provenance** (1.17.0: each threshold is tagged by provenance — a requirement
  declared in config vs the kit's default opinion; the biting cap says so in the
  headline — M5). **Derived FSM** (1.18.0: `phase` computes the workflow state
  from the ledger's facts, never declared; the PR is gated with `--require
  pr-ready` — M4). **Formal spikes** (1.19.0: a `spike/*` branch never passes the PR
  gate; the legitimate output is an ADR with lessons — M10). **Execution policy routing** (1.35.0: phase-level methodology/model/effort metadata for the operator and Mirador, not readiness scoring). **Discovery intake** (1.36.0: production findings + spec-doubt/SPEC-WRONG enter the ledger and reopen discovery instead of disappearing into narration). **ADR experiments** (1.37.0: `Status: Experiment` is visible/advisory in dashboard/Mirador with feedback/review metadata, not a readiness score). **Contract closure** (1.38.0: structured `spec-change-request`, golden intended vs observed-accidental labels, and post-merge calibration metrics). **Universal installer** (1.39.0: one machine installer for Codex plugin adoption and Claude global install, with dry-run/doctor/version checks). **npm/npx router** (1.40.0: `@andresmassello/uscha` exposes `uscha`/`uscha-kit` and delegates to the canonical Python installer). **Safety release** (1.41.0: WU1–WU7 plus post-audit P0/P1 hardening for evidence freshness, fail-closed reports, Mirador safety, installer transactions, ledger integrity, and current documentation). Smoke suite 357/357 green.
  **The PragProg backlog is CLOSED: 10 of 10** (see
  `docs/analisis-pragmatic-programmer.md`).
  License: MIT. The principle "facts block, guesses advise" is an enforced property,
  not a slogan.
- **Docs** — passed through truth-pass against the real engine: every claim describes what
  v1.41.0 does; the references appendix has **fetch-verified links** to the 10
  sources. Status convention in the docs: `in the kit` / `new` / `proposal`.
- **In progress** — dogfooding on a real case (pilot project, Python): the 1.4.0 adapter unblocked it;
  what remains is the read-only dry-run (criterion 2 of the python-adapter HANDOFF) and the on-ramp.
  Conscious deferrals in CHANGELOG-1.4.0 (assert density in rebuild, mechanized A-E
  profiles).


## Install

Recommended for Codex and Claude Code:

```bash
npx --yes @andresmassello/uscha@latest install --target codex
npx --yes @andresmassello/uscha@latest doctor --target codex
# or both Codex + Claude Code:
npx --yes @andresmassello/uscha@latest install --target both
npx --yes @andresmassello/uscha@latest doctor --target both
```

Full install guide: [`uscha-kit/INSTALL.md`](uscha-kit/INSTALL.md).

The npm package is only a thin router. The canonical installer remains
`uscha-kit/install-uscha.py`, and Python 3.8+ is still required on the target
machine.

## How the kit is re-packaged

```bash
powershell -NoProfile -Command "Compress-Archive -Path 'uscha-kit' -DestinationPath 'uscha-kit-X.Y.Z.zip' -Force"
```

The zips are build artifacts: they are not committed. The kit source in this repo is the truth.

## History

It was born as a methodology for working with Claude Code, was distilled with the
Böckeler principle (computational blocks / inferential advises), survived two
adversarial audits (231 agents) that found the central principle inverted in the code
— and 1.3.0 flipped it right. The details are in `audits/` and in the CHANGELOGs.
