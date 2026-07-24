# uscha-kit 1.50.2 — cross-platform: the kit runs, and proves it runs, on macOS and Linux (2026-07-24)

The engine was already portable; the *wiring* around it assumed Windows. A field discovery
run installed and ran the whole kit on real Linux and confirmed it: **0 engine defects**, and
a short list of cabling bugs — plus one the static audit had missed because it only shows up
on direct execution. This release fixes them and, more importantly, makes the claim
**measured**: a CI matrix now runs the 385-check suite on ubuntu / macOS / windows × Python
3.8 and 3.13. By the kit's own rule, "cross-platform" was narration until that grid was green.

## The measurement (this is the durable fix)
`.github/workflows/smoke.yml` runs the suite on all three OSes. Its very first run earned its
keep: green on Windows, **red on Linux and macOS**, on a single check — and not one of the
audited findings. The npm-router test asserted `! grep -Fq "$ROUTER_FALLBACK"`, a **substring**
match: on POSIX the fallback `python` is a prefix of the primary `python3`, so the check
believed the fallback had run when it had not (on Windows the fallback is `py -3`, not a
substring, so it always passed). The router is correct; the test now counts installer
invocations. A Windows-only assumption baked into the kit's own cross-platform test, invisible
to every prior local run.

## Runtime fixes
- **The INV-GOLDEN hook had a UTF-8 BOM before its shebang, and CRLF.** On direct execution the
  kernel does not see the shebang, hands the file to `/bin/sh`, which syntax-errors and exits
  2 — the exact PreToolUse *block* code. The guard looked installed while blocking **every**
  tool call on POSIX. Stripped BOM, normalized to LF, set the exec bit. Smoke **T98** now runs
  the hook DIRECTLY (not via an interpreter, which is what masked it), asserting `allow→0`,
  `block→2` on POSIX.
- **The doctor misdiagnosed a healthy hook.** It checked only for the `.ps1` and required
  `powershell`, so a `.py` install (what `uscha install` wires) read as broken on every OS,
  worst on mac/Linux. It now accepts either hook and ties interpretability to the one actually
  registered — `.py` needs only the engine's Python. Smoke **T97**.
- **The statusline wired a bare `python`.** Stock macOS/Linux ship only `python3`; the status
  line and Stop hook died silently. Now OS-resolved (`python3` on POSIX, `python` on Windows),
  with an ours-by-suffix auto-refresh for an upgraded install. Smoke **T89**, now OS-aware.
- **The plugin `hooks.json` invoked PowerShell only** — INV-GOLDEN-01 dead on the plugin path
  on mac/Linux. It now invokes the portable `.py` directly (shebang+exec on POSIX, the `.py`
  association on Windows, enabled by the BOM/exec fix); the `.ps1` was deleted. Smoke **T100**.
  *Honest limit:* CI cannot exercise Claude Code's plugin-marketplace hook execution — that
  path is proven by a real plugin install; `npx uscha install` is the CI-verified path.
- **Reinstall left dead hook entries** (found by simulation): the hook command carries an
  absolute `sys.executable`, so an interpreter move stranded a dead PreToolUse entry while the
  fresh one was merely appended. The installer now prunes any prior uscha hook by script
  basename before adding, preserving a user's foreign hooks. Smoke **T99**.

## Hygiene, made structural
- **Root `.gitattributes`** enforces `* text=auto eol=lf` (`.ps1` stays CRLF, goldens binary),
  so a CRLF can never again ship in a shebang regardless of a contributor's `core.autocrlf`.
  The kit's `.sh` files gained the exec bit.
- **`AGENTS.md`** — the context file Codex and pi read (not `CLAUDE.md`) — was cp1252 mojibake,
  had drifted, and was not emitted by `init`. Replaced with a thin pointer to `CLAUDE.md` (one
  canonical source) and added to the `init` template set.
- The repo's versioning rule said "five" surfaces; T44 checks **six** — corrected. The
  self-application `uscha.config.json` was bumped off its stale `1.44.0`.

## Not broken (recorded so it is not re-audited)
The field run confirmed the engine's own hygiene: paths via `os.path`/`pathlib`, tool
detection via `shutil.which`, all I/O `utf-8`-explicit; the ledger checksum is EOL-immune (it
hashes canonical JSON, not raw bytes); the install transaction never crosses filesystems.
`bin/uscha.js`, the installer's junction/symlink and browser-opening, and `workbench-doctor.sh`
were already correctly cross-platform.

The `pi` target (Earendil) and its design decisions are a **1.51.0** feature, out of this patch.
