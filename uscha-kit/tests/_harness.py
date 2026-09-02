"""Shared helpers for the smoke suite's heredoc blocks (kit 1.95.0).

`smoke-engine.sh` drives the engine from ~150 `"$PY" - <<'PY'` blocks. Each block is its own
interpreter, so anything they share has to be retyped -- and retyped copies drift. This module
holds the two idioms where that was already costing something real:

  * the four-line tail that persists a block's per-criterion verdicts into the sidecar the
    acceptance emitter reads (`sidecar`), retyped by 31 blocks (24 plain, 7 merging); and
  * the full-fixture diamond-bench pass (`bench_cached`), re-run twelve times across six blocks.

Since 1.96.0 it also holds `dogfood_verdict` (ADR-041) -- not a retyped idiom but the opposite
problem: the AC-DF-01 DECISION, which the acceptance emitter and the block that tests it must
share or the test tests nothing.

Blocks import it with

    sys.path.insert(0, os.path.join(kit, "tests"))
    from _harness import sidecar, bench_cached, dogfood_verdict

It is TEST-ONLY and never shipped: `package.json` excludes `uscha-kit/tests/` from the npm
package, so nothing here can reach an installed kit.

Rule of the refactor that introduced it (1.95.0): only IDENTICAL copies were replaced. The
per-block `eng()` / `run()` / `sh()` / `fixture()` wrappers were left where they are -- they are
NOT identical (different cwd, different env, one returns stdout instead of the CompletedProcess,
another takes the working directory as its first argument), and a helper that flattened them
would be changing what those blocks measure. Deleting duplication is not the same as unifying
semantics.
"""

import io
import json
import os
import subprocess


# --------------------------------------------------------------------------- #
# diamond-bench cache
# --------------------------------------------------------------------------- #
# The pristine `tests/fixtures/diamond-bench` tree is READ-ONLY for the suite and the engine is
# deterministic over it (ADR-027 pins the r2 classes, ADR-030 the round-trip numbers; T128 keeps
# a scoped re-run as the determinism probe). Six blocks used to launch twelve full-fixture
# passes -- ~51-61 s and ~648 child processes each -- to assert against the SAME numbers.
#
# The suite now runs each of the three passes ONCE, from the shell, into $BENCH_CACHE_DIR, and
# the consumer blocks read the result back. This is not "trusting a cache": a cache hit here is
# one measurement asserted many times, which is what it always was. What it removes is eleven
# re-executions of a measurement nobody disputed.
#
# A bench over a MUTATED or temporary copy of the fixture (T130's guard copy, T133's r2 gap
# rebuild, T134's node-absent and fidelity copies) is a DIFFERENT measurement and is never
# cacheable: those blocks keep their own calls.
#
# Fail-closed: a missing or corrupt cache file raises here, the block dies with a traceback, and
# its shell verdict is FAIL. An absent measurement never degrades to an empty dict.
BENCH_CACHE_FILES = {
    "bench": "bench.json",         # bench --dir <fixture> --json
    "fidelity": "bench-fid.json",  # bench --dir <fixture> --fidelity --json
    "r2": "bench-r2.json",         # bench-r2 --dir <fixture> --json
    "md": "DIAMOND-BENCH.md",      # the --out doc of the same plain pass
}


def bench_cache_path(kind):
    """Absolute path of one cached full-fixture bench artifact."""
    cache = os.environ.get("BENCH_CACHE_DIR")
    if not cache:
        raise RuntimeError(
            "BENCH_CACHE_DIR is unset: smoke-engine.sh must run the pristine diamond-bench "
            "pass before any consumer block")
    return os.path.join(cache, BENCH_CACHE_FILES[kind])


def bench_cached(kind):
    """The cached full-fixture bench report, parsed. Raises if it was never produced."""
    with io.open(bench_cache_path(kind), encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------------- #
# sidecars
# --------------------------------------------------------------------------- #
def sidecar(kit, name, res, merge=False):
    """Persist a block's per-criterion verdicts where the acceptance emitter reads them.

    `merge=True` reads the existing file first and updates it: the families whose criteria are
    measured by MORE THAN ONE block (`.top-cases.json` -- T137/T138/T141/T145) must not have the
    later block erase the earlier one's keys. The suite deletes every sidecar before T113, so a
    merge can only ever pick up a sidecar written by THIS run.
    """
    side = os.path.join(kit, "reports", "junit")
    os.makedirs(side, exist_ok=True)
    path = os.path.join(side, name)
    out = res
    if merge:
        try:
            with io.open(path, encoding="utf-8") as fh:
                out = json.load(fh)
        except (OSError, ValueError):
            out = {}
        out.update(res)
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(out))


# --------------------------------------------------------------------------- #
# dogfooding freshness (ADR-041)
# --------------------------------------------------------------------------- #
# AC-DF-01 asks one question -- was the ledger recorded AFTER the engine changed? -- and until
# 1.96.0 it answered with a wall clock (`readiness_history[-1].at` vs the engine commit's
# committer time). A clock and a commit are different units, and closing that gap cost a
# throwaway `readiness --record` before every suite run: a record taken on a tree whose tests
# had not been re-run, whose only job was to be newer than a commit. It manufactured the green
# it reported, it created the amend trap, and ~46% of readiness_history since 2026-08-18 is that
# step rather than the product.
#
# The question is about ORDER, and git records order exactly. `dogfood_verdict` asks it that way
# and nothing else does: PYACC's emitter and T150 (which drives the four outcomes over a real
# temp repo) call THIS function. A criterion whose test re-implements the criterion tests nothing.
def _git(root, *argv):
    """One git read under `root`, or None when git cannot be run at all.

    git absent, or a path that is not a work tree, is an ordinary state of the world here and
    must degrade to UNMEASURED -- the same posture the engine takes in `_seal_git`."""
    try:
        return subprocess.run(["git"] + list(argv), cwd=root, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, text=True, encoding="utf-8",
                              errors="replace")
    except (OSError, UnicodeDecodeError):
        # errors="replace" should make the decode unreachable; the except stays because a
        # verdict function that raises turns UNMEASURED into a crashed block.
        return None


def last_commit(root, rel):
    """The last commit that touched `rel` (a path relative to `root`), or None."""
    r = _git(root, "log", "-1", "--format=%H", "--", rel)
    if r is None or r.returncode != 0:
        return None
    out = r.stdout.split()
    return out[0] if out else None


def _ancestor(root, a, b):
    """True/False when git answers, None when it errors. `merge-base --is-ancestor` exits 0 for
    yes and 1 for no; ANY other code is git failing to answer, and reading that as `no` would
    turn a PASS into a FAIL on a hiccup."""
    r = _git(root, "merge-base", "--is-ancestor", a, b)
    if r is None or r.returncode not in (0, 1):
        return None
    return r.returncode == 0


def dogfood_verdict(root, engine_rel, ledger_rel):
    """AC-DF-01 by git ancestry (ADR-041).

    "pass" -- one commit carried both, or the engine commit is contained in the ledger commit
              (the X -> X+1 ritual);
    "skip" -- UNMEASURED: the ledger commit is contained in the engine commit, i.e. HEAD is the
              code commit X and the evidence lands in the next one; or the clone is shallow;
    "fail" -- diverged: neither commit contains the other, so the ledger was recorded on a
              history that does not contain the engine change;
    None   -- the question could not be asked: no git work tree, or neither path has ever been
              committed. Absence, never a silent pass.

    The shallow guard is kept verbatim from 1.93.0: at depth 1 `git log -1 -- <path>` returns
    HEAD for every path that exists, so engine and ledger always look like the same commit and
    the criterion would pass without measuring anything (reproduced on a local --depth 1 clone).
    CI checks out full history for exactly this reason."""
    shallow = _git(root, "rev-parse", "--is-shallow-repository")
    if shallow is None or shallow.returncode != 0:
        return None
    if shallow.stdout.strip() == "true":
        return "skip"
    engine_c = last_commit(root, engine_rel)
    ledger_c = last_commit(root, ledger_rel)
    if not engine_c or not ledger_c:
        return None
    if engine_c == ledger_c:
        return "pass"
    forward = _ancestor(root, engine_c, ledger_c)
    if forward is None:
        return None
    if forward:
        return "pass"
    backward = _ancestor(root, ledger_c, engine_c)
    if backward is None:
        return None
    return "skip" if backward else "fail"
