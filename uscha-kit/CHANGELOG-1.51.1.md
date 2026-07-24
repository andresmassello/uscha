# uscha-kit 1.51.1 — the doctor recognizes the golden hook across an interpreter change (2026-07-24)

A patch on 1.51.0, surfaced by the CI matrix's new real-installer end-to-end step (install
`--target all` → doctor on every OS). On **Windows / Python 3.8** the step failed: `doctor
--target claude` reported `hook_registered: False` for a hook that was, in fact, correctly
installed. Not a CI artifact — a real doctor false-negative. Smoke suite: 388/388.

## Root cause
The installer writes the INV-GOLDEN PreToolUse hook command via
`list2cmdline([sys.executable, <hook path>])` — an **absolute interpreter path** plus the hook
script. The doctor's `hook_registered` then checked for that command by **exact string
equality**. When install-time and doctor-time run under different interpreters — a bare
`python` that resolves to a different `sys.executable` between two invocations, as happened on
the Windows 3.8 runner — the two command strings differ only in their interpreter prefix, and
the exact-match reported the healthy hook as unregistered. That flipped `healthy` and the
`golden_guard` trust signal to a false negative on an otherwise correct install.

## Fix
`hook_registered` now matches a registered `"*"` hook by the **guard script it references**,
not by the full command string — the same robustness the N-1 reinstall prune already uses. The
match is **path-anchored** (`/block-approved-writes.py` or `\block-approved-writes.py`) so a
foreign command that merely *mentions* the name — `...not-block-approved-writes.py`, or the
literal inside a `-c` snippet — cannot read as our enforced guard, since this check feeds
`golden_guard`. Exact command stays a fallback; a `None` command entry is skipped, not a crash.

The interpreter-path sensitivity was latent before 1.51.0 (any Python move after install would
trip it); the real-installer CI step is what finally measured it. This is the step doing its
job — the same way the first matrix run caught the T75 router substring bug.

Regression: smoke **T103** — `hook_registered` matches across an interpreter change (install
wrote interpreter A, doctor computes B, same script → recognized), and does **not** match a
suffix-collision script, a bare `-c` mention, a foreign hook, a `None` command, or empty
settings. The CI real-installer step (all three OSes × Python 3.8/3.13) is the end-to-end proof.
