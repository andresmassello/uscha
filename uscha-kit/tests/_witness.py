"""Suite helper (2.10.0, ADR-055): turn a block's hand-placed report fixtures into evidence BORN
of a recorded `test-run`, without re-implementing anything the engine decides.

Since 2.10.0 the gates honor only a JUnit/coverage report that a `test-run` of the repo's
DECLARED command wrote. Most suite blocks build their reports by hand (that is the fixture: a
precise XML shape), so this helper makes the hand-placed bytes the OUTPUT of a declared command:

  prepare  QL LEDGER REPO   -- move the repo's report set (the engine's own `_witness_inventory`)
                               into a stash outside the repo (under the temp dir) and, when the repo declares no test
                               command, declare one (`repos[R].test_command`) that restores the
                               stash. The ledger is re-saved through the engine's own `_save`,
                               so its integrity checksum stays valid -- the same ledger a config
                               that declared the command at `init` would have produced.
  emit     STASH            -- the declared command: move the stash back into the cwd (the
                               repo path), preserving mtimes, and exit 0.

The block then runs `qa_ledger.py test-run`, which hashes before (reports absent) and after
(reports present): born of the run, by the engine's rule, not by this helper's say-so.
"""
import hashlib
import importlib.util
import os
import shutil
import sys
import tempfile


# Importing the engine by path must not drop a __pycache__ beside the shipped kit.
sys.dont_write_bytecode = True


def _engine(ql):
    spec = importlib.util.spec_from_file_location("qa_ledger_witness", ql)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _stash_for(repo_path):
    # OUTSIDE every repo (a repo at "." would otherwise hold its own stash, where the engine's
    # recursive report globs can see it); keyed by the repo's real path, so concurrent suite
    # units, each with its own temp dirs, never share one
    key = hashlib.sha1(os.path.realpath(repo_path).encode("utf-8")).hexdigest()[:16]
    return os.path.join(tempfile.gettempdir(), "uscha-witness-stash", key)


def prepare(ql, ledger_path, repo):
    eng = _engine(ql)
    ledger = eng._load(ledger_path)
    entry = eng._scope_entry(ledger, repo)
    path, rtype = entry.get("path", "."), entry.get("type", "maven")
    stash = _stash_for(path)
    shutil.rmtree(stash, ignore_errors=True)
    os.makedirs(stash)
    for rel in sorted(eng._witness_inventory(path, rtype)):
        src = os.path.join(path, rel)
        dst = os.path.join(stash, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(src, dst)
    cmd, _origin = eng._resolve_test_command(ledger, repo, ledger_path)
    if cmd is None:
        declared = [sys.executable.replace("\\", "/"),
                    os.path.abspath(__file__).replace("\\", "/"), "emit",
                    stash.replace("\\", "/")]
        if repo == "integration":
            ledger["config"].setdefault("integration", {})["test_command"] = declared
        else:
            for r in ledger["config"].get("repos", []):
                if r.get("name") == repo:
                    r["test_command"] = declared
        eng._save(ledger_path, ledger)


def emit(stash):
    if not os.path.isdir(stash):
        return 0
    for base, _dirs, files in os.walk(stash):
        for fn in files:
            src = os.path.join(base, fn)
            rel = os.path.relpath(src, stash)
            dst = os.path.join(os.getcwd(), rel)
            os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
            shutil.move(src, dst)
    shutil.rmtree(stash, ignore_errors=True)
    return 0


def witness(ql, cwd, ledger_path, repo, env=None):
    """In-process form for the suite's Python blocks: `prepare` from `cwd` (the directory the
    block runs the engine from), then the engine's own `test-run`. Returns the CompletedProcess."""
    import subprocess
    here = os.getcwd()
    os.chdir(cwd)
    try:
        prepare(ql, ledger_path, repo)
    finally:
        os.chdir(here)
    return subprocess.run([sys.executable, ql, "test-run", "--ledger", ledger_path,
                           "--repo", repo], cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env)


if __name__ == "__main__":
    if sys.argv[1] == "prepare":
        prepare(sys.argv[2], sys.argv[3], sys.argv[4])
    elif sys.argv[1] == "emit":
        sys.exit(emit(sys.argv[2]))
    else:
        sys.exit("usage: _witness.py prepare QL LEDGER REPO | emit STASH")
