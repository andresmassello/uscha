# uscha-kit 1.53.1 — the macOS branch is executed from any OS (2026-07-26)

Since the CI matrix went manual, macOS has been **UNMEASURED**. This release does not change
that status — it measures how big the gap actually is, and closes the part that never needed a
Mac. Smoke suite: 393/393, green on native Windows and real Linux (WSL).

## The gap, measured instead of feared
Grepping the kit for platform branches gives a precise answer: **every OS branch is `win32` vs
POSIX — and POSIX is measured on Linux — except exactly one instruction, duplicated:**

```python
elif sys.platform == "darwin":
    subprocess.Popen(["open", path])
```

That is the entire macOS-specific surface of the kit: the `open` arm of `_open_best_effort` in
`install-uscha.py` and `mirador-render.py` (plus its twin). The engine, the router, the
installer's transactional logic and the nine skills contain no other `darwin` reference.

## What changed
That arm never needed a Mac to be **run** — only to be run natively. Smoke **T108** patches
`sys.platform`, stubs the syscall, and executes it on every run, from any OS. It asserts:

- darwin shells out to `open`;
- Linux still gets `xdg-open`, so the mac command cannot leak across platforms;
- a Mac where `open` is unreachable **fails silently** rather than taking the process down
  (the arm lives inside a `try/except` — losing that would turn a cosmetic failure into a
  crashed install).

Verified by mutation: swapping `open` for `xdg-open`, and removing the `except`, each fail the
suite.

## What this is NOT
It is **not** a macOS run and does not claim to be. `docs/CROSS-PLATFORM.md` still reports macOS
as UNMEASURED. A real Mac could still differ in path semantics, permissions or interpreter
resolution. What changed is that the one divergence a Linux+Windows suite structurally could
never reach is now exercised every run — the residual risk is a native filesystem/interpreter
difference, not untested mac code.
