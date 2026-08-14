# uscha-kit

**Kit version:** v1.80.0 <!-- uscha:version --> · **[uscha.dev](https://uscha.dev)**

Spec-driven orchestrator + multi-repo QA for Claude Code, with a deterministic ledger.
**Nine skills** (`uscha-discovery`, `uscha-adr-refine`, `uscha-devloop`, `uscha-sysdoc`, `uscha-reverse-discovery`,
`uscha-characterize`, `uscha-rubric`, `uscha-mirador`, `uscha-status`) and a measurement engine (`qa_ledger.py`).

**Who it's for:** a solo operator carrying ONE non-trivial or risky change, kept
honest by a deterministic ledger and a human gate at the merge. It is NOT for trivial
changes (a one-liner runs build+test and that's it).

## What's inside

```
uscha-kit/
?? INSTALL.md                   # install guide: npx, Codex, Claude Code, alternatives
?? install-uscha.py             # canonical installer used by npm/npx
├─ uscha.config.json            # config: repos, thresholds, commands
├─ hooks/
│  └─ block-approved-writes.py     # PreToolUse: best-effort block on writing a golden (Claude only)
├─ templates/
│  ├─ CLAUDE.md                    # permanent repo protocol
│  ├─ CONSTITUTION.md              # inviolable invariants (fill in the domain)
│  ├─ .gitattributes               # *.approved.* binary — so line endings don't lie
│  └─ docs/adr/                    # ADR scaffold
?? .codex-plugin/plugin.json      # Codex plugin manifest
?? skills/                         # Codex plugin mirror of .claude/skills (smoke checks sync)
└─ .claude/skills/
   ├─ uscha-discovery/                   # vague idea → 1x1 grilling → CONSTITUTION/SPEC/ADR/ACCEPTANCE…
   ├─ uscha-adr-refine/                  # known feature: precision interview → ADR + ACCEPTANCE
   ├─ uscha-reverse-discovery/           # brownfield: FACTS map of the existing system (does not propose shape)
   ├─ uscha-characterize/                # captures the golden by running the ORIGINAL code (stops at human approval)
   ├─ uscha-devloop/
   │  ├─ SKILL.md                  # orchestrator: plan → build → QA loop → PR
   │  └─ qa_ledger.py              # measurement + ledger + gates (ingest/log-gate/golden-diff/gate-check/pit/simplicity/rebuild)
   ├─ uscha-sysdoc/                     # (optional) two-view HTML deck from the ledger
   └─ uscha-rubric/                      # (optional) rubric grading — thin adapter; the core is agnostic
```

## Fast-path (ADR-003) — measured entry for trivial changes

A one-line fix should not pay the ceremony of a schema migration. `fastpath-eval` grants the
shortcut from **measured signals**, never from anyone's opinion of "small":

```bash
python qa_ledger.py fastpath-eval --repo <name> --json            # dry-run: verdict only
python qa_ledger.py fastpath-eval --repo <name> --intent "fix: x" # records it in the ledger
```

Config (`defaults.fast_path`; absent block = feature off, behavior identical to earlier
releases): `max_files_changed` (3) and `max_loc_delta` (80) measured from
`git diff --numstat` against the merge-base with `origin/main` (fallback `main`) **plus
untracked files** — a new file is still a change; `protected_paths` globs deny regardless of
size; `require_asserting_test` caps readiness while a fast-path run has no measured test.

**Fail-closed:** no git, no resolvable base, no config → `DENY` with the reason named.
"Could not measure" never grants the shortcut. **Escalation:** re-running `fastpath-eval`
mid-run (the devloop does, before the PR step) with thresholds now exceeded flips the run to
`ESCALATED` through the standard escalation machinery — the derived phase blocks `pr-ready`
and readiness is capped until a human runs `resolve-escalation`, after producing the ADR +
ACCEPTANCE the change turned out to deserve. **The override is asymmetric (INV-RIGOR-02):**
you can always force the full path; nothing can force `ALLOW` over a measured `DENY`.

## Golden coverage (ADR-006) — the veto knows what a golden actually covers

A golden freezes behavior. Changing code a golden exercises is never a trivial change — but
until the engine knew WHICH source files a golden covers, that veto could not be measured, so
ADR-004 deferred it rather than ship a gate that pretended. `golden-coverage` builds the
mapping **by measurement**:

```bash
python qa_ledger.py golden-coverage --harness tests/golden/harness-x.py --golden tests/golden/x.approved.json
```

It runs the harness under `coverage.py` and records the source files that actually executed
into `golden.coverage.json` at the repo root (same convention as `golden.scrub.json`). The
harnesses drive their subject through a **subprocess**, so instrumentation is injected into
every python they spawn — measuring only the parent would record nothing and produce an empty
map, which would read as "this golden covers nothing".

Then, **opt-in**, the fast-path grows a `golden_touched` signal:

```json
"fast_path": { "forbid_when_golden_touched": true }
```

Absent or `false` → the veto does not exist and behavior is identical to earlier releases.
Declared → **fail-closed**: touching a mapped file denies (naming the golden and the file), and
so does a missing manifest, because "could not measure" never grants the shortcut. A malformed
manifest exits 2 rather than degrading into a silent "no mapping". Every verdict carries the
capture commit and tool version in the signal's `source` — provenance, not a freshness gate:
an aged map's real risk is a false negative, which cannot be detected without re-capturing.

Two honest limits (ADR-006): `coverage.py` is Python-only, so a harness in another language
cannot produce a map — declaring the veto there yields a permanent `DENY`, and the remedy is
not to declare it. And **file** granularity over-fires on monolithic files: in a repo whose
engine is one large module, the veto fires on nearly every change to it. When it errs, it errs
toward more ceremony, never less.

## Spec-drift (ADR-005) — the spec maintenance tax, made visible

Specs rot silently: the code moves and `SPEC.md` stays where it was. `spec-drift` detects
that lag **mechanically** — and reports it as **advisory, never a gate**, because whether an
older spec still covers newer code is a relevance judgment, and a guess advises.

```bash
python qa_ledger.py spec-drift --repo <name> --json   # advisory report; exit 0 always
```

Map specs to code with a `governs:` glob list in the frontmatter of `SPEC.md` and each
`docs/adr/*.md`:

```markdown
---
governs:
  - src/payments/**
  - db/**
---
```

Per document: **`SPEC_STALE`** when governed code outran the spec by more than
`defaults.spec_drift.max_lag_days` (default 30), listing the newer files; **`CLEAN`** when it
did not; **`UNMAPPED`** when there is no `governs:` frontmatter *or its globs match nothing*
— absence of a mapping is absence of measurement, not "no drift"; **`UNTRACKED`** when the
spec has no commit date to compare; **`NO-CODE`** when it declares `governs: []`, i.e. a
decision that governs no source (negative ADRs) — a declaration, not an omission. The latest run lands in the ledger (`spec_drift`) so the
mirador can surface it. No readiness impact, no exit-code gate: a stale spec is a prompt for
a human conversation, not a blocked pipeline.

## Evidence origin (ADR-007) - green, but green at *what*?

Freshness compares file mtimes, so the ledger could say "tests green" without being able to
say which commit that was true of. Every snapshot now stamps where it came from:

```json
"origin": { "commit": "5d17cf4...", "dirty": false }
```

Measured with `git rev-parse HEAD` and `git status --porcelain` in the repo path. **Untracked
files count as dirty** - an untracked file the suite depends on is exactly the contamination
worth recording. **No git, no repo -> both `null`**, and `dirty: null` never reads as clean:
a tree state nobody could measure is not a clean one.

Advisory throughout: `snapshot` prints `origin=<sha8>/<clean|dirty|unknown>`,
`dashboard --json` carries `evidence_origin` when a snapshot has one, `/uscha-status` says one
line when the latest evidence was dirty. Readiness, phase and convergence are untouched -
knowing a tree was dirty does not tell you the evidence is wrong, only that it was not
produced from a commit alone. The git-worktree clean-room that would answer the stronger
question is deliberately deferred; ADR-007 records why.

## Clean-room (ADR-008) - verify the commit, not your tree

A suite can pass in your working tree *because of uncommitted state* and fail against the
commit alone. The ledger records that as measured, with provenance true of the TREE and not of
the COMMIT that will merge.

```bash
python qa_ledger.py cleanroom --repo <name> --run "<your test command>" [--setup "npm ci"]
```

It creates a detached `git worktree` of the commit, verifies it is clean by construction, runs
what you gave it, records `ref` / `worktree_sha` / `status` / wall-clock, and removes the
worktree unconditionally (a zombie worktree is a defect). Status is specific:
`GREEN`, `RED`, `SETUP_FAILED` (a bootstrap failure is not a failing suite),
`WORKTREE_FAILED`, `WORKTREE_DIRTY`.

**The engine never decides what to run.** The command arrives via `--run`, the same contract
`golden-coverage` uses for `--harness`: the engine owns isolation, the SHA binding and
cleanup, and never turns a config file into a code-execution surface. That is also why it
works for any stack - it never had to know the stack.

**Opt-in gate:** `defaults.clean_room.mode` absent or `"off"` and nothing changes. `"final"`
makes `pr-ready` require a GREEN run pinned to the current HEAD; a new commit makes the
previous run stale for the gate.

Honest limit: this is **not** a substitute for CI. A local worktree runs on your machine, your
OS, your shell - environment variance is invisible to it. Different failure class, different
instrument.

## Curation (ADR-009/010) - candidates in quarantine, verdicts on the record

Reverse discovery's brownfield entry: the agent may author CANDIDATE specs of a legacy
system - in `discovery/`, with mandatory `evidence` (`test|code|inference`) and
`confidence` frontmatter, refs the engine resolves against real files - and **nothing is
promoted without a human verdict**:

```bash
python qa_ledger.py curation-check --repo <name> [--json]
```

Verdicts live in `BEHAVIOR-LEDGER.md` (`preserve` / `fix` / `undefined`, one ADR each) -
a human-readable table with machine-enforced rules: strict shape (`exit 2` on malformed,
because under this gate a silent "no verdicts" would UNBLOCK what it guards), append-only
verified against git (revert = new row + new ADR, never an edit; latest row wins). While
any candidate lacks a verdict, `pr-ready` is blocked naming it (INV-CURATION-01) - the
quarantine is measured, not promised. No `discovery/` directory -> the feature does not
exist and nothing changes.

## Oracle divergences + roundtrip (slice 2)

A `fix` verdict means the new system must NOT match the legacy golden - and that divergence
is **declared**, never tolerated implicitly:

```json
// golden.divergences.json
{ "divergences": { "invoice-totals.approved.json": {
    "adr": "ADR-RD-003", "reason": "IVA now rounds; legacy truncated" } } }
```

`golden-diff` then reads the pair as `expected_divergence` (named, with its ADR) instead of
a blocker - and a declared pair that comes back **identical** goes red: the fix the
declaration describes is not in the output. Malformed declarations exit 2.

`roundtrip --repo <name>` is the advisory closing of the loop, v1: which promoted
candidates are traceable in the code via an embedded `uscha-spec: <candidate>` marker -
coverage by id, deliberately not semantic matching, exit 0 always.

## End-to-end flow

`uscha-discovery` is the front for something new (you only have the idea); `uscha-adr-refine` is the front
for a known feature; `uscha-devloop` builds and verifies. They meet at the `ACCEPTANCE.md`.

```
/uscha-discovery     # idea only + reference material → 1x1 grilling (proposes, you decide)
   ↓           #   writes CONTEXT.md, CONSTITUTION.md, SPEC.md, docs/adr/*.md, ACCEPTANCE.md, RISKS.md, HANDOFF.md
/uscha-devloop      # plan → build → QA loop (fact gates to the ledger) → PR (stops at the merge)
   ↓
/uscha-sysdoc       # (optional, on request) documents the system from the ledger
```

(For an already known feature, instead of `/uscha-discovery` you use `/uscha-adr-refine`.)

**Migration/legacy on-ramp (profile E):** the golden is the field truth and is captured
BEFORE touching anything.

```
/uscha-reverse-discovery   # FACTS map of the old system (endpoints, contracts, dependencies)
   ↓
/uscha-characterize        # runs the ORIGINAL code with a real corpus → .received → STOPS:
   ↓                 #   a HUMAN approves the golden (a best-effort hook discourages the agent; golden-diff measures)
/uscha-devloop            # migrates; golden-diff byte-compares against the .approved on each pass
```

## Requirements

- **Python 3.8+** (stdlib only — no `pip install`). `cloc` is NOT needed; the LOC is
  counted in Python.
- For `ingest-gate` and coverage to work, your Maven build must emit the
  reports (your `java-qa-gate` already has the plugins; these are the paths the ledger
  expects):

  | data        | plugin / goal                                   | file |
  |-------------|--------------------------------------------------|---------|
  | coverage    | `jacoco-maven-plugin` (`report`)                 | `target/site/jacoco/jacoco.xml` (or `jacoco-aggregate/`) |
  | test count  | `maven-surefire-plugin` / `failsafe`             | `target/surefire-reports/TEST-*.xml` |
  | checkstyle  | `maven-checkstyle-plugin` (`checkstyle`)         | `target/checkstyle-result.xml` |
  | pmd         | `maven-pmd-plugin` (`pmd`)                        | `target/pmd.xml` |
  | spotbugs+fsb| `spotbugs-maven-plugin` (+ findsecbugs)          | `target/spotbugsXml.xml` |

  Flutter: coverage from `coverage/lcov.info` (`flutter test --coverage`);
  the test count is approximate (it counts `test(`/`testWidgets(`).

  Python (`type: python`, kit 1.4.0):

  | data        | command                                           | file |
  |-------------|---------------------------------------------------|---------|
  | coverage    | `pytest --cov --cov-report=xml:reports/coverage.xml` | `coverage.xml` or `reports/coverage.xml` (Cobertura) |
  | test count  | `pytest --junitxml=reports/junit.xml`             | `reports/junit.xml` (wrapped root `<testsuites>` supported) |
  | ruff        | `ruff check --output-format=json > reports/ruff.json` | `reports/ruff.json` (S*/E9*/F82*→HIGH · B*→MEDIUM · rest→LOW) |
  | mypy        | `mypy src > reports/mypy.txt`                     | `reports/mypy.txt` (error→HIGH · warning→MEDIUM · note→INFO) |

  `ingest-gate` finds them automatically by the repo's type, or with explicit `--ruff/--mypy`.
  Contract identical to Java: a missing report = the gate didn't run (it never credits fixes).

  TypeScript/JS (`type: node`, kit 1.5.0):

  | data        | command                                           | file |
  |-------------|---------------------------------------------------|---------|
  | coverage    | `jest --coverage` (or vitest with lcov reporter)  | `coverage/lcov.info` (same parser as Flutter) |
  | test count  | `jest-junit` / `vitest --reporter=junit`          | `reports/junit.xml` or `junit.xml` (wrapped root supported) |
  | eslint      | `eslint . --format json > reports/eslint.json`    | `reports/eslint.json` (error→HIGH · warn→MEDIUM · `security/*` floor HIGH · ruleId null→HIGH) |
  | tsc         | `tsc --noEmit > reports/tsc.txt`                  | `reports/tsc.txt` (error TS → HIGH) |

  `ingest-gate` finds them by the repo's type, or with explicit `--eslint/--tsc`.
  Same absence contract.

  Go (`type: go`, kit 1.6.0):

  | data        | command                                           | file |
  |-------------|---------------------------------------------------|---------|
  | coverage    | `go test -coverprofile=coverage.out ./...`        | `coverage.out` (native cover profile — % by STATEMENTS, the Go convention) |
  | test count  | `gotestsum --junitfile reports/junit.xml -- ./...`| `reports/junit.xml` (wrapped JUnit supported) |
  | golangci    | `golangci-lint run --output.checkstyle.path=reports/golangci.xml` (v2; in v1: `--out-format checkstyle > ...`) | `reports/golangci.xml` (checkstyle format: error→HIGH · warning→MEDIUM; includes gosec if enabled) |

  `ingest-gate` finds it by the repo's type, or with explicit `--golangci`. The
  `_test.go` tests live alongside the code (Go convention) — the LOC classifies them by suffix.
  `vendor/` and `testdata/` are excluded from the LOC. Same absence contract.
  **Watch out for severities**: golangci-lint emits `severity=error` for EVERYTHING unless you
  configure `severity:` rules — without that, even style nits gate as HIGH;
  configure severities (or a lean linter set) so that MEDIUM really exists.

  Rust (`type: rust`, kit 1.7.0):

  | data        | command                                           | file |
  |-------------|---------------------------------------------------|---------|
  | coverage    | `cargo llvm-cov --cobertura --output-path reports/coverage.xml` | `reports/coverage.xml` (Cobertura — same parser as Python) |
  | test count  | `cargo nextest run` + copy (see note)              | `reports/junit.xml` (wrapped JUnit supported) |
  | clippy      | `cargo clippy --message-format=json > reports/clippy.json` | `reports/clippy.json` (JSONL: error→HIGH · warning→MEDIUM · `code:null` compile-error→HIGH; summaries without span ignored) |

  `ingest-gate` with explicit `--clippy` or by type. Its JSONL evidence is fail-closed:
  each nonblank line must be a UTF-8 Cargo JSON object with a string `reason`; malformed
  records or malformed compiler diagnostics are rejected before ledger mutation. An empty
  file plus valid Cargo summaries and span-less diagnostic summaries remain clean/noise.
  The inline `#[cfg(test)]` tests count as prod LOC (documented limitation); `tests/` = integration.
  **Watch out for junit**: nextest does NOT emit JUnit by default — you have to enable it in
  `.config/nextest.toml` (`[profile.default.junit] path = "junit.xml"`) and the file
  lands in `target/nextest/default/junit.xml`; copy it to `reports/junit.xml`
  (`cp target/nextest/default/junit.xml reports/junit.xml`, already included in the
  example `test_command_rust`).

  C#/.NET (`type: dotnet`, kit 1.7.0):

  | data        | command                                           | file |
  |-------------|---------------------------------------------------|---------|
  | coverage    | coverlet.msbuild: `/p:CollectCoverage=true /p:CoverletOutputFormat=cobertura /p:CoverletOutput=$PWD/reports/coverage.xml` | `reports/coverage.xml` (Cobertura) |
  | test count  | `dotnet test --logger "junit;LogFilePath=$PWD/reports/junit.xml"` (JUnitXml.TestLogger package) | `reports/junit.xml` |
  | roslyn      | `dotnet build /p:ErrorLog="reports/analysis.sarif,version=2"` | `reports/analysis.sarif` (SARIF: error→HIGH · warning→MEDIUM · note→INFO; suppressed ignored) |

  `ingest-gate` with explicit `--sarif` or by type. SARIF is the universal static-analysis
  format — the parser works for any tool that emits it.
  **Watch out for paths**: relative `LogFilePath` and `CoverletOutput` resolve against the
  TEST PROJECT directory, not the repo root — hence the `$PWD`
  (absolute anchoring). With multiple test projects, merge (`/p:MergeWith`) or use one
  report per project. `ErrorLog` without `,version=2` emits SARIF **v1**; the parser
  has a v1 fallback, but ask for v2 (the comma requires the quotes).

  C++ (`type: cpp`, kit 1.8.0):

  | data        | command                                           | file |
  |-------------|---------------------------------------------------|---------|
  | coverage    | `gcovr --cobertura reports/coverage.xml` (over gcov) | `reports/coverage.xml` (Cobertura — same parser) |
  | test count  | `ctest --test-dir build --output-junit ../reports/junit.xml` (CMake ≥3.21) or `--gtest_output=xml:...` | `reports/junit.xml` (flat AND wrapped root supported) |
  | clang-tidy  | `clang-tidy <files> > reports/clang-tidy.txt`     | `reports/clang-tidy.txt` (error→HIGH · warning→MEDIUM · `cert-*`/security floor HIGH) |

  `ingest-gate` with explicit `--clang-tidy` or by type. The build system (CMake/
  Bazel/make) belongs to the per-repo adapter — the kit only requires that the reports exist.
  `cmake-build-*` (any CLion profile) and `_deps` are excluded from the LOC.

  **Text-report boundary:** mypy, tsc, and clang-tidy ingest only their recognized diagnostic
  lines. Their legitimate clean/noise forms include status/success text, tool summaries, and
  (for clang-tidy) passed-through compiler output, so a nonempty unmatched line is not safely
  distinguishable from a clean report. The kit deliberately does **not** invent fail-closed
  heuristics for those text formats; use their structured output where a fail-closed schema is
  required.

  Kotlin/JVM with Gradle (`type: gradle`, kit 1.9.0) — **Kotlin over Maven already
  works with `type: maven`** (`.kt` has always counted; JaCoCo/Surefire don't
  distinguish JVM language). This type is for the common Gradle case:

  | data        | command                                           | file |
  |-------------|---------------------------------------------------|---------|
  | coverage    | `./gradlew test jacocoTestReport`                 | `build/reports/jacoco/test/jacocoTestReport.xml` (JaCoCo — same parser as maven) |
  | test count  | (same `./gradlew test`)                           | `build/test-results/**/TEST-*.xml` (per-class, like surefire) |
  | detekt      | `./gradlew detekt` **separately** (see note)      | `build/reports/detekt/detekt.xml` (checkstyle format: error→HIGH · warning→MEDIUM; absolute paths relativized) |

  `ingest-gate` with explicit `--detekt` or by type. It works the same for Java-over-
  Gradle. LOC: `src/main` = prod; `src/test` AND custom source sets (`src/
  integrationTest`, `src/functionalTest` — any `src/*Test`) = test
  (`.kt`/`.kts`/`.java`). The JaCoCo requirement: `jacoco` plugin +
  `jacocoTestReport { reports { xml.required = true } }`.
  **Watch out for detekt**: do NOT chain it to the test command — its default is `maxIssues: 0`,
  meaning ONE finding breaks the build and the test run would read red even though
  the tests pass. Run `./gradlew detekt` separately, before the `ingest-gate`
  (the lint gate has its own channel).

  Swift (`type: swift`, kit 1.9.0):

  | data        | command                                           | file |
  |-------------|---------------------------------------------------|---------|
  | coverage    | `swift test --enable-code-coverage` + `llvm-cov export -format=lcov ... > coverage/lcov.info` | `coverage/lcov.info` (lcov — same parser as Flutter/node) |
  | test count  | `swift test --xunit-output reports/junit.xml`     | `reports/junit.xml` **+ `reports/junit-swift-testing.xml`** (they are SUMMED — see note) |
  | swiftlint   | `swiftlint lint --reporter checkstyle > reports/swiftlint.xml` | `reports/swiftlint.xml` (checkstyle format: error→HIGH · warning→MEDIUM; absolute paths relativized) |

  `ingest-gate` with explicit `--swiftlint` or by type. LOC: SwiftPM convention
  (`Sources/` = prod, `Tests/` + `*Tests.swift` = test). The lcov export needs
  the `llvm-cov export` step against the tests binary (the `.profdata` alone is
  not enough) — leave it in your repo's `test_command_swift`; on macOS it is
  `xcrun llvm-cov`, on Linux plain `llvm-cov` (and the binary lives in
  `.build/debug/<Pkg>PackageTests.xctest`).
  **Watch out for Swift Testing**: `--xunit-output` writes the XCTest results to
  `junit.xml` and the **Swift Testing** ones (the default in Swift 6) to a SECOND
  file `junit-swift-testing.xml` — the engine sums BOTH; if it only read the
  first, a Swift 6 package would measure `tests=0` and a real failure would be
  invisible (fail-open).

## Installation

**Recommended path: npm/npx.** Use the same installer for Codex, Claude Code,
or both. Full guide: [`INSTALL.md`](INSTALL.md).

```bash
npx --yes @andresmassello/uscha@latest version
npx --yes @andresmassello/uscha@latest install --target codex --dry-run
npx --yes @andresmassello/uscha@latest install --target codex
npx --yes @andresmassello/uscha@latest doctor --target codex
```

For a machine used by both Codex and Claude Code:

```bash
npx --yes @andresmassello/uscha@latest install --target both --dry-run
npx --yes @andresmassello/uscha@latest install --target both
npx --yes @andresmassello/uscha@latest doctor --target both
```

Use a Git checkout only when developing Uscha itself or testing unreleased
changes:

```bash
python uscha-kit/install-uscha.py install --target both --mode link --dry-run
python uscha-kit/install-uscha.py install --target both --mode link
```

Claude Code's native plugin flow remains available for Claude-only users, but
`npx` is the universal path and also covers Codex.



**Verify the installation with `doctor`** (kit 1.22.0, in the spirit of flutter doctor —
Windows and Linux, ASCII output, exit 1 only on errors):

```bash
python uscha-kit/install-uscha.py doctor --target both
# or engine-only: python3 ~/.claude/skills/uscha-devloop/qa_ledger.py doctor
```

It checks: Python >=3.8 · git · the 9 skills alongside the engine (frontmatter
verified) · the INV-GOLDEN-01 hook (present + registered in settings.json +
powershell/pwsh interpreter) · and if there is a `uscha.config.json` in the cwd:
config parseable, ACCEPTANCE with AC-IDs, ledger integrity, the QA skills
from `qa_tools_order` (the loop orchestrates them without bringing them in) and the
primary toolchain of each repo by type (its absence is a WARNING — it may live only in CI).

## Configure

Edit `uscha.config.json`:

- `repos[]`: name, `path` (relative to the primary repo), `type` (`maven`|`flutter`|`python`|`node`|`go`|`rust`|`dotnet`|`cpp`|`gradle`|`swift`).
- `defaults.coverage_threshold`: triggers the characterization phase if below it.
- `defaults.severity_gate`: which severities block (default BLOCKER/CRITICAL/HIGH).
- `defaults.id_granularity`: `line` or `file` (default `file`: more stable if you refactor a lot).
- `defaults.acceptance_file`: path of the **acceptance task list** (markdown checkboxes) that feeds the ADR completion of readiness. Default `ACCEPTANCE.md`.
- `defaults.constitution_file`: path of the **CONSTITUTION** (inviolable invariants). Default `CONSTITUTION.md`.
- `defaults.rebuild.coverage_tolerance`: coverage points the rebuild can drop without penalty (default 5).
- `defaults.readiness_weights` / `readiness_caps` / `static_gate_zero_at`: weights and caps of the KPI.
- `defaults.execution_policy`: phase-level routing metadata (`method`, `tier`, `model`, `effort`) shown by `execution-policy` and Mirador. It guides the operator; it does **not** affect readiness.
- Discovery intake commands (`production-finding`, `spec-doubt`, `spec-change-request`) persist post-merge production facts, SPEC doubts, and human contract-change bridges so the next cycle reopens discovery/SPEC instead of hiding reality in narration.
- ADRs may use `Status: Experiment` when a decision is an explicit, measured hypothesis. `dashboard --json`/Mirador expose `adr_status`, feedback/review metadata, malformed/expired counts; this is advisory visibility, not readiness scoring.
- `defaults.max_iterations`, `tools_per_cycle`, test commands.

## Multi-repo: mounting the other repos

The skill runs from the primary repo; the others are mounted in the session:

```bash
cd <repo-primario>
claude --add-dir ../backend-api --add-dir ../mobile-app
```

(or `additionalDirectories` in `.claude/settings.json`).

## Use

Inside Claude Code, invoke the orchestrator (with the ADR/PLAN ready or ask it for one):

```
/uscha-devloop
```

The skill handles the phases on its own: plan → coverage gate → (characterization if needed)
→ build → per-repo QA loop → integration → verify → PR (stops at the merge, you approve
it) → smoke list. It logs every step in `QA-LEDGER.json`. At the end:

```
/uscha-sysdoc        # generates docs/system-deck.html (CEO + technical, navigable)
```

## Quick check (engine dry run, without the skill)

To confirm the engine parses your reports correctly BEFORE trusting it with the loop:

```bash
cd <repo-primario>
QL=".claude/skills/uscha-devloop/qa_ledger.py"

python3 $QL --help                                  # see subcommands
python3 $QL init --config uscha.config.json      # creates QA-LEDGER.json

# run your build with the reports, then:
python3 $QL snapshot      --repo backend-api --phase pre
python3 $QL check-coverage --repo backend-api       # exit 0 = OK, 1 = below threshold
python3 $QL ingest-gate   --repo backend-api --iteration 1
python3 $QL summary                                 # human summary
python3 $QL summary --json                          # includes post_merge_calibration
```

If `snapshot`/`ingest-gate` say "no report found", it's because the build hasn't generated
the XML yet — run `mvn test` with the plugins active first.

## Readiness KPI (when finishing any task)

Shows the "ready for release" status as a 0..100 score, **based on the state of the
result, not on effort spent**:

```bash
python3 $QL readiness --acceptance ACCEPTANCE.md
python3 $QL readiness --json            # consumed by uscha-sysdoc (traffic-light widget)
python3 $QL execution-policy --phase qa  # one-line methodology/model/effort routing
python3 $QL production-finding --repo backend-api --severity HIGH --title "..." --evidence "..."
python3 $QL spec-doubt --repo backend-api --kind spec-wrong --note "..." --evidence "..."
python3 $QL spec-change-request --repo backend-api --source SD-001 --requested-change "..." --evidence "..."
```

- Dimensions/weights: **acceptance traced (MEASURED) 30**, ADR/checkboxes 15, coverage 15,
  static gate 20, convergence 10, integration 10. The **ADR completion** comes from your
  acceptance task list (checkboxes `- [x]`/`- [ ]`, read-only) — count the whole file
  (CLI default); `--section` only if you verified that the heading matches
  exactly (a mismatch silently zeroes the dimension).
- **Traceability (kit 1.10.0, the dominant dimension)**: each criterion carries a stable ID
  — `- [ ] AC-01 — when X then Y`. A criterion closes MEASURED only when there exists
  ≥1 GREEN testcase with its tag in the name (`test_ac1_x` / `testAC01X` / `"AC-01: ..."`
  — normalized by number: `AC-01 == AC_1 == ac1`) in the already-ingested JUnit reports,
  and no tagged testcase in red. The checkbox is NARRATIVE; the testcase is FACT: an
  `[x]` without a green test appears as `narrated_only` and does NOT close. Anti-Goodhart: the agent
  can no longer raise the KPI by polishing coverage — only by closing criteria with named
  tests. `spec-check --acceptance ACCEPTANCE.md` validates the structure as a FACT (zero
  traceable criteria or duplicate IDs = BLOCKED). Without IDs: it falls back to the checkbox ratio
  with a warning (legacy, incremental adoption). Flutter doesn't emit JUnit: its criteria don't
  close measured (documented limitation).
- A lintable repo whose static gate **never ran** scores that dimension UNMEASURED (0.0)
  — silence is not success.
- **Hard caps** (they override the ceiling): tests in red → ≤35, open BLOCKER/CRITICAL → ≤65,
  unresolved escalation → ≤75 (holds until `resolve-escalation`, a recorded event).
- Bands: `<50 NOT READY` · `50–79 IN PROGRESS` · `80–94 RELEASE CANDIDATE` · `95–100 READY`.
- Multi-repo: per-repo and aggregate (min() for blockers, LOC-weighted for quality).
- Cycles/regressions are **churn** (process health), reported separately and never
  raise readiness.

## Rebuild test (SPEC completeness)

A different question for the ledger: not "did this build pass?" (correctness) but "is the SPEC
enough to regenerate the system?" (completeness). For profiles C+/E or periodic in CI.

```bash
# 1) in the ORIGINAL tree: capture the signature the rebuild must match
python3 $QL rebuild --mode baseline --config uscha.config.json   # → REBUILD-BASELINE.json
# 2) in a CLEAN tree / new session: regenerate ONLY the production code from
#    SPEC/ADR/ACCEPTANCE, PRESERVING the tests, and run the suite.
# 3) score the regenerated tree against the baseline
python3 $QL rebuild --mode compare --baseline REBUILD-BASELINE.json   # exit 0 = COVERS
python3 $QL rebuild --mode compare --baseline REBUILD-BASELINE.json --json   # consumed by uscha-sysdoc
```

- Dimensions/weights: tests 60, acceptance 20, coverage 15, surface 5. The dominant signal
  is the **preserved suite**: a test that passed and fails in the regenerated code = behavior
  the SPEC left implicit.
- Verdicts: `COVERS ≥90` · `PARTIAL ≥70` · `DIVERGE <70`. The score lists the concrete
  **gaps** — feed them back into the SPEC and re-run. Divergence is a spec hole, not a code bug.

## Simplicity gate — "Reduce" (minimality of the change)

The **Simplicity** invariant of the CONSTITUTION made a deterministic gate: it scores the *diff*
(not CC by AST — they are measurable proxies: minimality, nesting, new abstractions).

```bash
git diff --unified=0 <base> | python3 $QL simplicity-check --config uscha.config.json
python3 $QL simplicity-check --from-git --base main            # uses git for you
python3 $QL simplicity-check --diff changes.diff --json        # consumed by uscha-sysdoc / CI
```

- Dimensions/weights: diff_size 35, nesting 30, net_growth 20, fan_out 8, blob 7
  (abstraction does NOT weigh in the score — it's a guessy proxy, kept as a metric + advisory flag).
- Verdicts: `SIMPLE ≥85` · `ACCEPTABLE ≥65` · `OVERBUILT <65` (exit 1 = BLOCKER: trim and re-run).
  A gross excess (2× budget, or very deep nesting) caps the score at 60 no matter what.
- **Tests OUT of the budget** (kit 1.11.0): the test files (conventions of the
  9 stacks) are counted and reported separately (`test_lines_added`) but do not gate — writing
  tests never pushes the diff to OVERBUILT (deleting them is already blocked by gate-check).
- The flags tell you what to trim (guard clauses, speculative types/layers, giant hunks).
- Budgets in `defaults.simplicity`; adjustable per risk profile. 2-space → `--indent-width 2`.

## Ledger subcommands

`doctor - rubric-ingest - init - snapshot - check-coverage - log-step - ingest-gate - phase -
converged - oscillation - escalate - resolve-escalation - log-gate - flag-blocker -
production-finding - spec-doubt - spec-change-request - regression-check - summary - readiness -
execution-policy - dashboard - rebuild - simplicity-check - waste-check - pit-check - gate-check -
spec-check - golden-diff` - the exact current `qa_ledger.py` parser surface; each supports `--help`.

The **fact gates** (golden-diff, gate-check, pit-check, simplicity) are PERSISTED with
`log-gate`: a fail blocks convergence and caps readiness ≤65 via the ledger. A CONSTITUTION
violation is recorded with `flag-blocker` (same effect, until `--resolve`).

## Notes

- **It doesn't merge on its own.** It creates the PR and stops; the merge is yours.
- **ADR experiments are visible hypotheses.** `Status: Experiment` requires Hypothesis, Feedback Signal, Review By/Trigger, Promote Criteria and Rollback/Supersede Criteria. Missing or expired metadata is shown by `dashboard --json`/Mirador as advisory, not as a hard PR gate.
- **Tracked `.md` protocol.** Before touching CLAUDE.md / plan/delta docs / docs/adr,
  the skill asks for the current version of the file (it doesn't regenerate and overwrite real progress).
- `ingest-gate` credits a fix only if the report EXISTS and came back clean; a missing
  report = the gate didn't run (it doesn't invent zeros).

## Setting up the workbench (generic setup)

Before using the skills you need the base toolchain (Claude Code + Python + git/gh +
the skills installed). It's all in **`WORKBENCH.md`**: installation, verification and
update, without the specifics of each stack (Java/MSSQL/linters = per-repo adapter).

- What I have installed:  `bash workbench-doctor.sh`
- Kit version:      `python uscha-kit/install-uscha.py version` or `cat VERSION`

## Templates for the repo (so the repo becomes "methodology-ready")

The kit installs the skills; these templates leave the **repo** ready. Copy them to the root
of the repo where you're going to work:

```
cp uscha-kit/templates/CLAUDE.md        <repo>/CLAUDE.md        # permanent repo protocol
cp uscha-kit/templates/CONSTITUTION.md  <repo>/CONSTITUTION.md  # inviolable invariants (fill in the domain)
cp -r uscha-kit/templates/docs    <repo>/docs           # docs/adr scaffold
# if you use other agents besides Claude Code:  cp <repo>/CLAUDE.md <repo>/AGENTS.md
```

Then, complete the "Project adapter" block of the `CLAUDE.md` with the build/test/gate
commands of that stack (it's the only project-specific thing).

## Verify the agent reads the kit

Inside Claude Code, ask it:

```
List the active rules from CLAUDE.md and the available skills.
```

The protocol rules and the commands `/uscha-discovery`, `/uscha-adr-refine`,
`/uscha-devloop`, and `/uscha-sysdoc` should appear. (For the machine's toolchain: `bash uscha-kit/workbench-doctor.sh`.)
