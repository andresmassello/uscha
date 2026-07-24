# Cross-platform support — audit and roadmap

Status: **planning**. The kit is developed and released on Windows; this document tracks
what it takes to support macOS and Linux honestly.

## Verdict up front

**This is not a port.** The measurement engine (`uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py`)
is already portable — it builds paths with `os.path`/`pathlib`, finds tools with
`shutil.which`, and has no OS-exclusive branch lacking a POSIX counterpart. So is most of the
surface around it: the npm router `bin/uscha.js` (platform-gated Python probing), the
installer's junction-vs-symlink logic and browser opening (`_open_best_effort`), its home and
skill-dir resolution (`Path.home()`, dot-dirs), `workbench-doctor.sh`'s `windows_shell()`
split, and the smoke suite's platform-gated fixtures.

The real work is **three narrow seams and one missing measurement**. And the measurement comes
first, because — by the kit's own rule — *until the suite runs green on Linux and macOS,
"cross-platform" is narrated, not measured.*

## The measurement (do this first)

`.github/workflows/smoke.yml` runs the 381-check smoke suite on a matrix of
`ubuntu-latest` / `macos-latest` / `windows-latest` × Python `3.8` (the declared floor) and
`3.13`. The audit below is **static** — nobody has executed the suite on a real Linux or macOS
box. CI turns the audit's hypotheses into facts, surfaces anything the static read missed, and
gives every fix below a red-to-green signal to build against. **Start here, then fix #1–#3 with
evidence in hand.**

### First run — what CI already found (the point, working)

The very first matrix run confirmed the value of measuring: **Windows green, Linux and macOS
red on both Python versions**, with a single failing check — and it was *not* one of the five
audited findings. The npm-router test's assertion `! grep -Fq "$ROUTER_FALLBACK"` matched a
**substring**: on POSIX the fallback interpreter `python` is a prefix of the primary `python3`,
so the check believed the fallback had run when it had not. The router itself is correct
(`bin/uscha.js` selects an interpreter by its `--version` probe and preserves the installer's
exit code without retrying). The test now counts total installer invocations instead — the
platform-robust way to encode "without another interpreter". A Windows-only assumption baked
into the kit's own cross-platform test, invisible to a static read and to every Windows run.
That is exactly what this workflow exists to catch.

## Findings

Verified by reading the code (file:line), classified for the macOS/Linux goal.

### BLOCKERS — a documented install path fails

| # | Finding | Evidence |
|---|---------|----------|
| 1 | **`hooks.json` invokes PowerShell only.** The packaged Claude Code plugin registers the golden-write guard as `powershell -NoProfile … block-approved-writes.ps1`. `powershell` is absent by default on macOS/Linux, so the plugin-marketplace install path cannot wire INV-GOLDEN-01 there. | `uscha-kit/hooks/hooks.json` · `uscha-kit/.claude-plugin/plugin.json` (`"hooks": "./hooks/hooks.json"`) |

Note the kit ships **two** install mechanisms that disagree on the canonical hook: the plugin
flow (`.ps1`, above) and `install-uscha.py` (which wires the portable `.py` hook correctly,
per-OS). The `.py` hook is a full equivalent of the `.ps1` — same stdin-JSON → block-on-
`.approved` → exit 2 logic. **This needs its own ADR**: pick one canonical, portable hook
mechanism and make both paths agree.

### DEGRADED — a feature silently dies or the tooling lies

| # | Finding | Evidence |
|---|---------|----------|
| 2 | **The doctor misdiagnoses a healthy hook on every OS.** `qa_ledger.py` checks for the substring `block-approved-writes.ps1`, but `install-uscha.py` registers a command referencing `block-approved-writes.py`. The substring never matches an installer-written `settings.json` → the hook is reported "presente pero NO registrado" everywhere. On macOS/Linux it is worse: the doctor also probes `powershell`/`pwsh` unconditionally and false-warns about the missing interpreter the `.py` hook never needs. | `qa_ledger.py:6007` (`HOOK_NAME = "…​.ps1"`) vs `install-uscha.py:24` (`"…​.py"`); `qa_ledger.py:6106` (unconditional `powershell`/`pwsh` probe) |
| 3 | **The statusline wires a bare `python`.** `init` writes `python .claude/scripts/uscha_statusline.py` (and the Stop-hook progress refresher) into the project's `settings.json`. Stock macOS/Linux frequently has only `python3` on PATH — the status line renders nothing and the progress hook no-ops, with no error surfaced. Every other Python invocation in the kit already tries `python3` first on non-Windows; this is the one regression. | `install-uscha.py:477-478` (`STATUSLINE_CMD` / `PROGRESS_CMD`) |

### LATENT — inert today, protects against future breakage

| # | Finding | Evidence |
|---|---------|----------|
| 4 | **No repo-root `.gitattributes` enforcing LF.** The committed `.sh`/`.py` blobs are LF-clean today only incidentally. Nothing stops a future commit from introducing CRLF, which breaks a `#!/usr/bin/env bash` shebang on Linux (`bad interpreter: …^M`). The only `.gitattributes` shipped is `uscha-kit/templates/.gitattributes` (golden-fixture binary protection, for end-user projects). | repo root has no `.gitattributes`; `git check-attr text eol -- uscha-kit/tests/smoke-engine.sh` → `unspecified` |
| 5 | **Shipped `.sh` lack the exec bit** (mode `100644`). Masked today because every documented invocation prefixes `bash`/`python`. A future `./script.sh` snippet would fail with "Permission denied" on a fresh clone. | `git ls-files -s uscha-kit/**/*.sh` |

## Ordered work list

1. **CI matrix** (`smoke.yml`) — land it, read the first three-OS run. *This is the roadmap's
   own measurement step; everything below is scoped by what it turns red.* ← this change.
2. **Doctor honesty (#2)** — accept `.py` OR `.ps1` as a registered hook; tie the
   `powershell`/`pwsh` probe to the hook actually installed instead of firing always. Cheap,
   high-visibility: today a healthy install reports broken.
3. **Statusline `python` → per-OS resolution (#3)** — resolve `python3`-first on non-Windows,
   matching `bin/uscha.js` and `workbench-doctor.sh`. Restores the feature on stock macOS/Linux.
4. **Portable hook — ADR (#1)** — decide one canonical hook mechanism that works on all three
   OSes and reconcile the plugin `hooks.json` with `install-uscha.py`. The largest single
   decision; do it deliberately, not as a one-liner.
5. **Repo-root `.gitattributes` (#4)** — `* text=auto eol=lf`, plus explicit `*.sh`/`*.py`
   `eol=lf`, so a CRLF can never ship in a shebang.
6. **Exec bits (#5)** — `git update-index --chmod=+x` the shipped `.sh`, or leave documented
   `bash X.sh` as the contract and add a smoke check that no doc says `./…​.sh`.

Each engine or installer change carries a smoke check in the same commit (repo rule 5), and
CI must stay green on all three OSes before the kit claims cross-platform support anywhere in
its docs (repo rule 2 — no doc may claim what is not measured).

## What is explicitly NOT broken

Recorded so the roadmap does not re-audit them: the engine's path/JSON/subprocess handling;
`bin/uscha.js` Python probing (`python3` first on non-Windows); the installer's
junction/symlink placement and browser opening; `mirador-render.py`'s browser opening; home
and skill-dir resolution; `workbench-doctor.sh`'s OS detection; and the smoke suite's
platform-gated router/doctor fixtures. All already correctly cross-platform.
