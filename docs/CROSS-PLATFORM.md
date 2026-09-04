# Cross-platform support — audit (measured)

Status: **done — cross-platform is measured, not narrated.** Windows, macOS and Linux each run
the full smoke suite (**444 checks at kit 1.98.0**) on the CI matrix: **three cells on a branch
push or PR, all six on a tag or a manual dispatch** (since 1.97.0 — the table under *The
measurement* says which cells and why). This document is the audit trail of getting there —
kept as the record of what was found and fixed, not an open roadmap.

## Verdict up front

**This is not a port.** The measurement engine (`uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py`)
is already portable — it builds paths with `os.path`/`pathlib`, finds tools with
`shutil.which`, and has no OS-exclusive branch lacking a POSIX counterpart. So is most of the
surface around it: the npm router `bin/uscha.js` (platform-gated Python probing), the
installer's junction-vs-symlink logic and browser opening (`_open_best_effort`), its home and
skill-dir resolution (`Path.home()`, dot-dirs), `workbench-doctor.sh`'s `windows_shell()`
split, and the smoke suite's platform-gated fixtures.

The real work was **three narrow seams and one missing measurement** — all now closed. The
measurement came first, because — by the kit's own rule — *cross-platform stays narrated until
the suite runs green on Linux and macOS.* It now does, on every push — three cells on a branch,
all six on a tag.

## The measurement (do this first)

`.github/workflows/smoke.yml` runs the smoke suite on `ubuntu-latest` / `macos-latest` /
`windows-latest` × Python `3.8` (the declared floor) and `3.13` — the full six on a tag or a
manual dispatch, a three-cell subset on a branch push or PR (see the next section for which
three and why). The audit below is **static** — nobody has executed the suite on a real Linux or macOS
box. CI turns the audit's hypotheses into facts, surfaces anything the static read missed, and
gives every fix below a red-to-green signal to build against. **Start here, then fix #1–#3 with
evidence in hand.**

### How many cells run, and when (1.97.0)

The grid is not the same size on every event, and the difference is stated rather than left to
be discovered from a checks list:

| event | cells | which |
|---|---|---|
| push to a branch, pull request | **3** | `ubuntu`/3.13, `macos`/3.13, `windows`/3.8 |
| tag `v*`, manual dispatch | **6** | the full `ubuntu`/`macos`/`windows` × `3.8`/`3.13` grid |

Six cells of a ~35-minute suite on every push bought the same answer several times — which is why
the grid was reduced in 1.97.0, and not why it exists in the first place. The grid exists
for the failures that are **invisible outside it**, and each of those has exactly one home in the
reduced set: the bash 3.2 quoting trap lives on `macos` (macOS ships that bash whatever Python is
installed), the Windows 8.3 short-path trap lives on `windows` under `runneradmin`, and the
3.8-vs-3.9+ interpreter split is covered by pinning `windows` to the floor — which is also the
slowest cell, so the wall clock barely moves. What the reduced grid does **not** measure, said out
loud: `ubuntu`/3.8, `macos`/3.8, `windows`/3.13.

Nothing is published on three cells. `tools/release.py` tags right after the push (1.98.1);
before it creates the tag (I8), the tag then triggers the 6-cell run on the same SHA, and
`publish.yml` reuses **that** run — selected by `head_branch` (the tag name), never by "the
newest run for this SHA", because both runs exist on that commit and "newest" is a race whose
losing side would publish on three cells. No tag run, no publish-by-reuse: the job falls back to
running the suite in the publish job itself and says, in the receipt, that it is one cell.

Implementation note: GitHub does not expose the `matrix` context to a job-level `if:`, so a
per-cell condition is not expressible. A small `grid` job computes the matrix JSON and the
`smoke` job consumes it with `fromJSON` — which also means a reduced run has three jobs rather
than six with three skipped.

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

### Field evidence (kit 1.50.1 on real Linux — Python 3.12, Node 22)

A separate discovery run installed and ran the FULL kit on Linux and confirmed this
document's central claim independently: **the engine and all three installer commands are
already portable — 0 engine defects.** `doctor --target both` reported `ok: true`, 9/9 skills,
hook present + registered, on both targets. It also found what a static read could not — a
BLOCKER this audit missed (P0-4 below) — and measured the T75/router bug that the CI matrix had
already turned red. Findings folded in below.

**macOS is MEASURED again (2026-07-26).** It went UNMEASURED for one day: on 2026-07-25 the
account ran out of Actions minutes and every push produced a run that died in 6 seconds with
*"The job was not started because recent account payments have failed"* — six red cells that
measured nothing, so the workflow was set to `workflow_dispatch` only rather than leave a red
grid that reads like a real failure. Making the repo **public** restored free standard runners,
and the matrix is back on every push: `ubuntu` / `macos` / `windows` × Python 3.8/3.13 (since
1.97.0 the six run on tags and dispatches, three on branch pushes — see above), plus the
REAL installer end-to-end (`install --target all` → `doctor --target all`, asserting `ok: true`
and per-target `golden_guard`).

**The first macOS run after the gap failed — and that is the whole argument for the cell.**
Both macOS cells died *before a single assertion*:

```
line 4162: unexpected EOF while looking for matching `"'
```

A parse failure, not a test failure. macOS still ships **bash 3.2** (2007, for GPLv3 reasons),
and a smoke check written that week used a literal `['"]` character class inside a
`VAR=$(... <<'PY' ... PY )` block; bash 3.2 hunts for the matching quote to the end of the file
and gives up. Bash 4/5 — Linux and git-bash — parse it fine, so **393/393 locally said nothing
was wrong**. Fixed by writing the quotes as `\x27`/`\x22`, and recorded in `CLAUDE.md` next to
its sibling trap (backticks in comments inside those same heredocs, which the shell executes as
command substitution). Neither is reachable from the dev machine. That is the case for keeping
a real macOS runner rather than reasoning about macOS.

| Platform | How it is verified | Status |
|---|---|---|
| Windows | CI matrix (py3.8 + py3.13) + native local runs | **measured, 393/393** |
| Linux | CI matrix (py3.8 + py3.13) + real Ubuntu 22.04 via WSL (Python 3.10, Node 24) | **measured, 393/393** |
| macOS | CI matrix (py3.8 + py3.13) on real `macos-latest` runners | **measured, 393/393** |

**Local verification still works and is still worth running** — it is faster than a push and it
caught real defects while CI was down: `bash uscha-kit/tests/smoke-engine.sh` natively, and
`wsl -e bash -lc "cd /mnt/c/... && bash uscha-kit/tests/smoke-engine.sh"` for real Linux. What
it structurally cannot reach is exactly what bit above: an old-bash parse difference.

The Linux row needs Node on the WSL side (Ubuntu 22.04's `apt` ships Node 12, below the kit's
declared `">=18"`, so it is the wrong tool for the job). Node's official prebuilt tarball
extracted under `~/.local/node` — no `sudo`, no system package, reversible by deleting the
folder — gives the four npm-router checks a real POSIX `node`. Shimming Windows `node.exe`
through WSL interop was rejected deliberately: `bin/uscha.js` would see `win32` and hand back a
FALSE green on the very test whose point is POSIX interpreter selection.

### How big is the macOS gap, actually? (measured, 1.53.1)

Grepping the kit for platform branches gives a precise answer rather than a worry: **every OS
branch in the kit is `win32` vs POSIX — and POSIX is measured on Linux — except for exactly one
instruction, duplicated:**

```python
elif sys.platform == "darwin":
    subprocess.Popen(["open", path])
```

That is the whole macOS-specific surface: the `open` arm of `_open_best_effort` in
`install-uscha.py` and in `mirador-render.py` (plus its twin). Nothing else in the engine, the
installer, the router or the skills says `darwin`.

That arm does not need a Mac to be *run* — only to be run *natively*. Smoke **T108** patches
`sys.platform`, stubs the syscall and **executes it**: it asserts darwin shells out to `open`,
that Linux still gets `xdg-open` (so the mac command cannot leak across), and that a Mac where
`open` is unreachable **fails silently** instead of taking the process down. Verified by
mutation: swapping `open` for `xdg-open`, or removing the `except`, both fail the suite.

**T108 is still worth keeping even now that macOS runs in CI:** it executes that arm on EVERY run and on every OS, so a Linux-only or Windows-only local run cannot silently break it between pushes. A real
Mac could still differ in path semantics, permissions or interpreter resolution. What changed is
that the one divergence a Linux+Windows suite structurally could never reach is now exercised on
every run, on every OS — the residual risk is a native filesystem/interpreter difference, not
untested mac code.

Per the kit's own rule, the remaining gap is stated, not papered over: *absence is not success*. macOS's one
difference from Linux — case-insensitive-by-default — is still guarded on every run by smoke
**T102** (fails on any two tracked paths that collide when lowercased), which is platform-independent.
Also still out of reach: the plugin-marketplace hook execution (P0-3) and pi's `tool_call` block
(the `advisory` golden_guard), both needing a real Claude-Code-plugin / real-pi run.

### BLOCKERS — a documented install path fails, or the guard silently blocks everything

| # | Finding | Evidence |
|---|---------|----------|
| 0 | ~~**The `.py` hook has a UTF-8 BOM before its shebang, and CRLF**~~ **DONE (1.50.2).** On direct execution the kernel did not recognize `\xef\xbb\xbf#!…`, handed the file to `/bin/sh`, which syntax-errored and **exited 2 — the exact PreToolUse BLOCK code.** The guard appeared installed while blocking EVERY tool call. Stripped BOM, normalized to LF, set the exec bit (`100755` in the index). Regression: smoke **T98** — byte hygiene (no BOM/CRLF) on every OS, and DIRECT execution (`allow→0`, `block→2`) on POSIX. Field-measured; missed by the static audit and by the kit's own hook test (which ran the hook *through* an interpreter). | fixed; `head -c3` → `#!/` |
| 1 | ~~**`hooks.json` invokes PowerShell only.**~~ **DONE (1.50.2).** The plugin `hooks.json` now invokes the portable `.py` directly (`"${CLAUDE_PLUGIN_ROOT}/hooks/block-approved-writes.py"`) — enabled by P0-0's exec bit + clean shebang: it runs via the shebang on POSIX and the `.py` association on Windows. The `.ps1` was deleted (D-05 b+d); the doctor, both SKILL.md twins and the CLAUDE.md note were updated. Regression: smoke **T100**. **Verification gap (honest):** the smoke cannot exercise Claude Code's plugin-marketplace hook execution; whether it runs a bare `.py` path as intended on each OS is proven only by a real plugin install, not by CI. The primary, fully-CI-verified cross-platform path remains `npx uscha install`. | `uscha-kit/hooks/hooks.json` |

Note the kit ships **two** install mechanisms that disagree on the canonical hook: the plugin
flow (`.ps1`, above) and `install-uscha.py` (which wires the portable `.py` hook correctly,
per-OS). The `.py` hook is a full equivalent of the `.ps1` — same stdin-JSON → block-on-
`.approved` → exit 2 logic. **This needs its own ADR**: pick one canonical, portable hook
mechanism and make both paths agree.

### DEGRADED — a feature silently dies or the tooling lies

| # | Finding | Evidence |
|---|---------|----------|
| 2 | **The doctor misdiagnoses a healthy hook on every OS.** `qa_ledger.py` checks for the substring `block-approved-writes.ps1`, but `install-uscha.py` registers a command referencing `block-approved-writes.py`. The substring never matches an installer-written `settings.json` → the hook is reported "presente pero NO registrado" everywhere. On macOS/Linux it is worse: the doctor also probes `powershell`/`pwsh` unconditionally and false-warns about the missing interpreter the `.py` hook never needs. | `qa_ledger.py:6007` (`HOOK_NAME = "…​.ps1"`) vs `install-uscha.py:24` (`"…​.py"`); `qa_ledger.py:6106` (unconditional `powershell`/`pwsh` probe) |
| 3 | ~~**The statusline wires a bare `python`.**~~ **DONE (1.51.0).** `install-uscha.py` now resolves `_STATUSLINE_PY = "python" if os.name == "nt" else "python3"` — matching `bin/uscha.js` and `workbench-doctor.sh`; `init` runs on the target machine so `os.name` is right. An upgraded install whose statusLine still runs our script under the old interpreter is auto-refreshed (ours-by-suffix), not reported as a foreign conflict. Regression: smoke **T89**, now OS-aware, validated by the CI matrix (`python3` asserted on the Linux/macOS cells). | `install-uscha.py` (`_STATUSLINE_PY`) |

### LATENT — inert today, protects against future breakage

| # | Finding | Evidence |
|---|---------|----------|
| 4 | **No repo-root `.gitattributes` enforcing LF.** The committed `.sh`/`.py` blobs are LF-clean today only incidentally. Nothing stops a future commit from introducing CRLF, which breaks a `#!/usr/bin/env bash` shebang on Linux (`bad interpreter: …^M`). The only `.gitattributes` shipped is `uscha-kit/templates/.gitattributes` (golden-fixture binary protection, for end-user projects). | repo root has no `.gitattributes`; `git check-attr text eol -- uscha-kit/tests/smoke-engine.sh` → `unspecified` |
| 5 | **Shipped `.sh` lack the exec bit** (mode `100644`). Masked today because every documented invocation prefixes `bash`/`python`. A future `./script.sh` snippet would fail with "Permission denied" on a fresh clone. | `git ls-files -s uscha-kit/**/*.sh` |

## Ordered work list

1. **CI matrix** (`smoke.yml`) — land it, read the first three-OS run. *This is the roadmap's
   own measurement step; everything below is scoped by what it turns red.* ← this change.
2. ~~**Doctor honesty (#2)**~~ — **DONE.** `qa_ledger.py` now recognizes `.py` OR `.ps1`
   (`HOOK_NAMES`, `.py` canonical), and ties interpretability to the hook actually registered:
   the `.py` runs on the engine's own Python (always present), only the `.ps1` needs
   `powershell`/`pwsh`. A healthy `.py` install now reads OK on every OS; a plugin `.ps1`
   install on Linux without pwsh now warns *honestly* (that gap is finding #1). Regression:
   smoke **T97** — a `.py`-registered hook reads OK, and the CI Linux/macOS runners (no
   powershell) are the negative control proving it needs none.
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

## Beyond the runtime fixes (field-run roadmap)

The Linux discovery run also scoped two larger threads, out of this document's original
"three seams" but part of the same goal:

- **`AGENTS.md` (P0-5)** — has cp1252 double-encoding mojibake, has drifted from `CLAUDE.md`
  (missing the `.uscha-private-names`/AC-03 paragraph), and is NOT in `templates/`, so `init`
  never emits it — yet it is the context file Codex and pi read (they do not read `CLAUDE.md`).
- ~~**N-1 — stale hook accumulation**~~ **DONE (1.50.2).** `prepared_settings` now prunes any
  prior uscha hook (matched by the script basename, not the exact command) before adding the
  current one, so a reinstall after an interpreter move self-heals; a user's foreign PreToolUse
  hook is preserved untouched. Regression: smoke **T99** — a planted stale entry is pruned,
  the current stays once, foreign preserved, idempotent on re-run.
- **N-6 — root dogfooding config drift**: repo-root `uscha.config.json` says `1.44.0` vs kit
  `1.50.1`. T44 checks the KIT's config, so it does not gate; a one-line cleanup.
  **CLOSED in 1.96.0**: the field is removed rather than re-synchronised. It was a SEVENTH
  version surface that nothing gated and exactly one cosmetic `doctor` line read, so
  keeping it in step by hand with six files it has nothing to do with bought nothing.
  `uscha-kit/uscha.config.json` -- the template a consumer copies -- stays one of the six.
- **A third install target, `pi`** (Earendil, Agent Skills standard): the 9 skills load
  unmodified; INV-GOLDEN-01 is portable to pi's blocking `tool_call` event as a small
  extension. This is a FEATURE, with ten design decisions (D-01…D-10 in the field handoff) the
  human must make before code — target root, `--target all` vs `both`, the hook extension's
  build story, etc.

**Version plan** (from the field handoff, cleaner than a single bundle): the portability
FIXES (P0-0 BOM, P0-2 statusline ✓, P0-3 hook, P0-6 EOL/exec, P0-5 AGENTS.md, plus the
already-shipped T75 and doctor fixes) ship as a **1.50.2** patch; the `pi` target ships as a
**1.51.0** feature. (Note: repo rule 6 says "five" version surfaces but T44 checks six — fix
the doc in the same commit; with `pi` the plugin count grows again.)

## What is explicitly NOT broken

Recorded so the roadmap does not re-audit them: the engine's path/JSON/subprocess handling;
`bin/uscha.js` Python probing (`python3` first on non-Windows); the installer's
junction/symlink placement and browser opening; `mirador-render.py`'s browser opening; home
and skill-dir resolution; `workbench-doctor.sh`'s OS detection; and the smoke suite's
platform-gated router/doctor fixtures. All already correctly cross-platform.
