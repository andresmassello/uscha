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

### Field evidence (kit 1.50.1 on real Linux — Python 3.12, Node 22)

A separate discovery run installed and ran the FULL kit on Linux and confirmed this
document's central claim independently: **the engine and all three installer commands are
already portable — 0 engine defects.** `doctor --target both` reported `ok: true`, 9/9 skills,
hook present + registered, on both targets. It also found what a static read could not — a
BLOCKER this audit missed (P0-4 below) — and measured the T75/router bug that the CI matrix had
already turned red. Findings folded in below.

**macOS is measured (1.51.x):** the CI matrix runs the suite on real `macos-latest` runners,
and a CI step now runs the REAL installer end-to-end there (`install --target all` →
`doctor --target all`, asserting `ok: true` + per-target `golden_guard`). Its one difference
from Linux — case-insensitive-by-default — is guarded by smoke **T102** (fails on any two
tracked paths that collide when lowercased). What is STILL out of CI reach: the
plugin-marketplace hook execution (P0-3) and pi's `tool_call` block (the `advisory`
golden_guard), both needing a real Claude-Code-plugin / real-pi run — not a macOS gap.

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
