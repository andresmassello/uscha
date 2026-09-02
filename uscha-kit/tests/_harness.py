"""Shared helpers for the smoke suite's heredoc blocks (kit 1.95.0).

`smoke-engine.sh` drives the engine from ~150 `"$PY" - <<'PY'` blocks. Each block is its own
interpreter, so anything they share has to be retyped -- and retyped copies drift. This module
holds the two idioms where that was already costing something real:

  * the four-line tail that persists a block's per-criterion verdicts into the sidecar the
    acceptance emitter reads (`sidecar`), retyped by 31 blocks (24 plain, 7 merging); and
  * the full-fixture diamond-bench pass (`bench_cached`), re-run twelve times across six blocks.

Blocks import it with

    sys.path.insert(0, os.path.join(kit, "tests"))
    from _harness import sidecar, bench_cached

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
