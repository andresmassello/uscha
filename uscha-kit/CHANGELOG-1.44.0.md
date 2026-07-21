# uscha-kit 1.44.0 — brownfield truth: what the engine could not measure, it now says (2026-07-21)

Field release. Everything here comes from a retrospective of a real run: a gzip migration
across two legacy Java 8 / Ant repositories with fiscal data, taken end to end
(reverse-discovery → approved golden → adr-refine → devloop → merge). The run succeeded, and
it surfaced four defects that all share one root: **the engine knew something and did not say
it**. Smoke suite: 366/366.

Not in this release: the inert `risk_profile` (declared in config, read by nobody) — the
deepest finding of the same retro. It gets its own release; see the note at the end.

## Fixes

### 1 — coverage: "no report at all" is not the same fact as "a measured 0%"
`static_unmeasured` already taught the engine that *silence is not success* for the static
gate. Coverage had no equivalent: a repo with no instrumentation scored exactly like a repo
whose report says 0%, and the operator had no way to tell which — the field report had to read
`qa_ledger.py` to find out. Two legacy repos with 18 green tests sat at readiness **66.7**
purely because of this, an artificial ceiling in exactly the brownfield scenario
`reverse-discovery` targets.

Fix: the coverage parsers already returned `report_found`; the readiness dimension now uses it.
`coverage_unmeasured` is exposed per repo (`facts`) and aggregated
(`facts.coverage_unmeasured_repos`), and readiness prints the repos with the remedy named.

The score is deliberately **unchanged** (still 0.0): auto-redistributing the weight would let
any repo raise its score by DELETING its instrumentation — the precise anti-pattern
`static_unmeasured` exists to prevent. The relief is a **human declaration**:
`defaults.readiness_weights.coverage = 0` redistributes the weight, is versioned in the config,
and carries provenance (config = requirement, kit 1.17.0). Silence never buys points; a
declaration does. `qa_ledger.py`. Regression: smoke **T82** (pins the field's 66.7 → 100.0).

### 2 — no `ant` project type
Supported types were maven, gradle, flutter, python, node, go, rust, dotnet, cpp, swift. Ant —
the dominant build tool in legacy Java, i.e. the terrain the brownfield front is FOR — was
missing, so the field run had to declare two Ant projects as `maven`. Added `ant`: because Ant
has no standard output layout (the `todir` is build-file defined), its reports are discovered
**recursively by name** (`**/TEST-*.xml`, `**/jacoco.xml`) instead of guessing one convention.
Also added to the lint-capable set for `static_unmeasured`.

Recursive discovery needs two guards, both found by an adversarial review of this very
release: (a) reports are pruned of **third-party trees only** (`node_modules`, `vendor`,
`.git`, `.venv`...) — deliberately NOT of `build/`, `target/` or `coverage/`, because reports
LIVE in build output and the existing `SKIP_DIRS` (built for scanning SOURCE) would have
hidden exactly the files being looked for; and (b) name-based discovery is **tolerant**: a
`TEST-*.xml` that turns out not to be a JUnit `<testsuite>` — or that has a valid root but
impossible counters, e.g. a truncated run — is dropped instead of aborting the whole run with
`SystemExit(2)`. Precise patterns (maven/gradle) keep the hard failure.

Crucially, a drop is **never silent**: `report_found` now means a *usable* report, and every
dropped file is returned in `skipped_reports`, persisted in the snapshot, exposed per repo
(`facts.dropped_reports`) and aggregated (`facts.dropped_report_repos`), and named by
`readiness` on **stdout** — because `dashboard --json` (the mirador) captures stdout, so a
stderr-only warning would be invisible exactly where operators look. Dropping evidence quietly
would be silence buying a pass, which is the one thing this engine must not do.
Regression: smoke **T83**.

**Known limitation (by design, for now):** because report discovery for `ant` searches by name
and deliberately does not prune `build/`/`target/` (reports live there), a nested sibling Maven
or Gradle module inside an `ant` repo will have its reports swept into the parent's totals.
That is the trade for a build tool with no convention; declare such modules as their own repos
in `uscha.config.json` to keep their evidence separate.

### 3 — JUnit discovery too narrow (an integrity issue, not a convenience one)
The engine looked for `target/surefire-reports/TEST-*.xml`, `reports/junit.xml` and
`junit.xml`. A runner writing a DIRECTORY of per-class XML under `reports/junit/` was invisible,
so the operator **hand-copied reports** to a path the engine knew. That is not friction: a
hand-placed report breaks the *evidence captured by execution* invariant, which is the whole
defense against a forged report. Now `reports/junit/**/*.xml` is discovered too.
Regression: smoke **T83**.

### 4 — a Windows reserved filename took down a whole gate
`waste-check` died with `ValueError: path is on mount '\\.\nul'` on a repo containing a file
named `nul`; the gate simply never ran. Reserved device names (`nul`, `con`, `aux`, `prn`,
`com1..9`, `lpt1..9`) are now skipped in all four tree walks. Detection splits on the FIRST
dot, not the last: Windows treats `nul.tar.gz` as the device too, and an initial fix using
`os.path.splitext` left that crash reachable (`_newest_source`, `count_loc`,
`_test_file_set`, `_waste_repo_hashes`). A weird filename degrades to a skip, never a crash.
Regression: smoke **T84** (multi-extension cases, and no false positives: `nullable.py`,
`console.ts`, `com1x.go`).

## Note on the risk profile
The same retro verified that `risk_profile` appears **zero times** in the engine: it is declared
and read by nobody, so the decision of "how much process does this change deserve" rests
entirely on the operator. That is the difference between a methodology and a convention, and it
is too deep to bundle here — it is the next release.

## Note on the test suite
The installer/npm smoke checks still hardcode the version string, so this bump updated those
literals.
