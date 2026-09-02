# uscha-kit 1.95.0 — the suite gets cheaper: the same measurements in 14 minutes instead of 22 (2026-09-02)

No engine behaviour changes in this release and no acceptance semantics change. Every criterion
that read green at 1.94.1 reads green here, from the same assertion or from one that is provably
the same assertion, and the acceptance report is **byte-identical** to the one 1.94.1 committed —
that identity is the rail this whole release was built against, not a nice-to-have.

What changed is the price: **21m55s → 13m55s** on the release machine, a 37% cut, and **544 fewer
lines** of suite. The suite was paying for the same measurement over and over, and it was paying it
in the two places nobody looks: a fixture pass re-executed twelve times, and an idiom retyped
twenty-eight times. Neither is a bug. Both are the kind of cost that quietly decides how often a
developer is willing to run the thing that tells them the truth — and a truth-telling instrument
nobody runs is worth what an untested claim is worth.

## What changed

### The Diamond Bench ran twelve times to answer three questions

`T128`, `T132`, `T133`, `T134`, `T135` and `T136` each launched their own full pass over the
pristine `tests/fixtures/diamond-bench` tree: **seven plain `bench --json`, two `--fidelity`, three
`bench-r2`**. Each pass is ~50-60 s and ~648 child processes on Windows, and every one of them
produced the same numbers — the fixture is read-only for the suite and the engine is deterministic
over it, which is exactly what ADR-027 (the r2 classes) and ADR-030 (the round-trip figures) pin.
Twelve runs of one measurement were never twelve measurements.

The three passes now run **once**, from the shell, into `$BENCH_CACHE_DIR`, and the consumer blocks
read the result back through `_harness.bench_cached`. The plain pass emits `--out` and `--json`
together, so one run yields both the JSON and `DIAMOND-BENCH.md`. Nothing about the classification
was softened: a missing or corrupt cache file **raises**, the block dies with a traceback and its
shell verdict is `FAIL` — an absent measurement never degrades to an empty dict. A bench over a
MUTATED or temporary copy of the fixture is a different measurement and still runs in its own block
(T130's `guard` copy, T133's broken-`r2` rebuild, T134's node-absent and one-entry fidelity copies),
and T128 keeps its scoped `guard`-only `--fidelity` re-run as the determinism probe it always was.

The word to be careful with is "cache". A cache hit here is one measurement asserted many times,
which is what it always was; what disappeared is eleven **re-executions** of a number nobody
disputed. If the fixture ever stops being read-only, or the engine ever stops being deterministic
over it, that is a change to ADR-027/ADR-030 and this cache is the first thing that has to go.

### One acceptance table instead of twenty-eight copies of one

Every block that measures `ACCEPTANCE.md` ids drops a sidecar under `reports/junit/`, and the
acceptance emitter turns each id into its own named testcase — SKIP when the sidecar or the key is
absent (UNMEASURED, never a silent pass), green on `True`, red otherwise, naming the block that
measured it. That contract is four facts wide: which sidecar, what to label the testcase, which
block measures it, which ids it owns.

It was written out **twenty-eight times**: 28 near-identical reader functions and 28 near-identical
loops, ~390 lines in which a family that had quietly drifted from the idiom — a missing `None`
guard, a green-by-absence — would have been invisible in the noise. That is not a hypothetical
failure mode; 1.94.1 shipped precisely because two checks in this suite were reporting red and
throwing it away. It is now one `FAMILIES` table and one loop, and the table is the only thing a
new family adds. The 28 `rm -f` lines that clear stale sidecars became one glob over a directory
that is gitignored build output and holds nothing else, so tomorrow's family is covered without
anyone remembering a line.

`_harness.py` (test-only; `package.json` already excludes `uscha-kit/tests/` from the npm package)
carries the two shared idioms: the sidecar read-merge-write and the bench cache. The per-block
`eng()` / `run()` / `sh()` / `fixture()` wrappers were deliberately **left where they are**. They
are not identical copies — different cwd, different env, one returns stdout instead of the
`CompletedProcess`, another takes the working directory as its first argument — and a helper that
flattened them would be changing what those blocks measure. Deleting duplication is not the same as
unifying semantics; only the first one is free.

### Five things that could not fire

- **T106** ("the suite reads the version, it never pins it") was a static self-lint of this very
  file for version-shaped literals. It emitted no acceptance row, and the drift it existed to catch
  is already gated where it matters: `T44` fails the suite unless all six version surfaces agree
  AND a `CHANGELOG-<version>.md` exists for that version. A self-lint of the test file is not the
  same guarantee as a gate on the artifact.
- **The P0-A roll-up's `else FAIL=$((FAIL+1))` arm.** The P0-A block runs under `set -eu`: a failed
  assertion kills the suite inside the block, so the roll-up below is only ever reached with
  `P0_A_STATUS=0`. The arm was unreachable. (P0-B and P0-C are different — those blocks record a
  status and keep going, so their FAIL arms stay.)
- **`_oracle_hash`** was `_sha256_file` written out a second time, down to the `OSError -> None`.
  It now calls it. The arm's withheld oracle is hashed by exact bytes, same as a manifest unit;
  that was already the rule, and now it is also the same code.
- **Four band lookups with four unreachable defaults.** `_band`, `_simplicity_band`,
  `_rebuild_band` and `_waste_band` were the same four-line loop over four tables, each ending in a
  trailing `return "<LABEL>"` that restated the table's own floor-0 row — a fifth band nobody could
  reach. They share one `_banded(score, bands)` whose default IS the last row, so the answer is
  unchanged for every input, including a score below zero.
- **`+ _n("TRACED")`** in `cmd_top`'s `unmeasured` count. `cmd_top` assigns exactly four states
  twenty lines above that sum (`MEASURED_FAIL`, `MEASURED_PASS`, `QUARANTINE`, `UNMEASURED`);
  `TRACED` and `TAGGED` are declared in `TOP_STATES` so the renderer can class them gray and are
  never emitted in v0.1, so the addend was a constant zero. `top --json` exposes no `traced` count,
  so no golden frame moves.

Two candidates were **kept**, and the reason is the same in both cases — they were not dead:

- **`--adr` on `spec-change-request`.** No doc, skill or test passes it, but `cmd_spec_change_request`
  persists `args.adr` into the recorded row (`"adr": args.adr`). Removing the flag would change the
  ledger's recorded schema, which is a behaviour change, not a refactor — and its twin `--spec` is
  used the same way.
- **The three `WANT_VERDICT` maps** in T134, T135 and T136. They look like copies and are not: each
  one deliberately OMITS the archetype its own ADR introduces (T134 drops `rate-limiter`, T135 drops
  `ledger-lite`, T136 pins all twelve), because what each is asserting is "the OTHERS did not move".
  Collapsing them into one map would weaken exactly the claim they exist to make. T136's `bench_ok`
  is now a cache read, so it costs nothing to keep asserting.

## The rail

`reports/junit/uscha-acceptance.xml` carries no timestamps, durations or hostnames, so
run-to-run identity is a strict byte comparison — verified before the change by re-running the
unchanged suite against the committed report, which came back byte-identical. The report produced
after the change is byte-identical to that: same 217 testcases, same names, same order, same
verdicts. The suite's own check count drops by exactly the one deleted block (439 → 438) and by
nothing else.

The obvious next saving was left alone on purpose, because it is a separate change with its own
rail: `T136` still runs `bench-roundtrip` over the full fixture **twice**, once for the JSON and
once for the `--out` document, and that subcommand takes `--out` and `--json` in one pass exactly
the way `bench` does.

Suite: 438 checks · 0 fail; acceptance 217/217.
