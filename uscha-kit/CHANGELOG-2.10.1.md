# uscha-kit 2.10.1 — the 2.10.0 suite measured on every CI cell: a no-commit repo built instead of a read-only .git deleted, a witness assertion instead of a timing one, and the serial cell pinned to an image that has Python 3.8 (2026-10-31)

## What changed

2.10.0 reached `main` sealed and green locally (464 ok · 0 fail on Linux), and its first six-cell
CI run was red. No tag was created, so nothing was published; 2.10.1 is the release that
carries 2.10.0's content to npm. The engine does not change. The three causes, all in the
instrument:

- **Windows (three cells): T173 died before counting.** AC-GI-20 built its "git but no commit
  yet" repo by copying a committed fixture and deleting its `.git`. Git writes its objects
  read-only, Windows refuses to delete a read-only file, and `shutil.rmtree` raised
  `PermissionError` — the whole unit died, and its 24 criteria read UNMEASURED. The fixture is now
  built without a commit in the first place (`base_py(..., commit=False)`).
- **macOS (two cells): AC-GI-31 asserted timing.** Beside the witness verdict readiness reports
  (`evidence_unattested`, which agreed on every cell), the case also asserted that readiness's
  `converged` flag was false. That flag reads ADR-039's clock rule too, whose one-second tolerance a
  fast machine lands inside when the edit follows the run in the same second. The case now asserts
  what it exists for: `phase` refuses the edited repo, keeps the other `pr-ready`, and readiness
  names the same stale run for the same repo only.
- **ubuntu/py3.8 (the serial cell): no Python 3.8 on the image.** `ubuntu-latest` moved to Ubuntu
  26.04, which has no Python 3.8 build, so `setup-python` failed before the suite ran. The cell is
  pinned to `ubuntu-22.04`, still ubuntu, still py3.8, still `USCHA_JOBS=1`; AC-PD-05 checks the
  pinned name and ADR-054 says why.

See `CHANGELOG-2.10.0.md` for the release content (witnessed evidence, ADR-055).

## Evidence

Suite: __SUITE__ checks · 0 fail; acceptance __ACC__.
