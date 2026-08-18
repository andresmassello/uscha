---
governs:
  - uscha-kit/install-uscha.py
  - uscha-kit/.claude/skills/uscha-devloop/uscha_top.py
  - uscha-kit/skills/uscha-devloop/uscha_top.py
---
# ADR-031: `uscha top` is a raw-ANSI terminal projection of the ledger — no curses, no server, wired the way `mirador` is, so the programmer meets the method where they already live

## Status: Accepted (M1 shipped in 1.86.0; the `mtime` poll shipped in 1.88.0 for M2; curated 2026-08-17)

## Context
The existing `mirador` (`uscha-mirador`) renders a static HTML dashboard post-hoc. It is a report:
you open a browser tab to read it, and a report in a tab that is not already open does not get
opened. The measured lesson of adoption is gravity — the programmer lives in the terminal, and a
status view that runs over SSH on any host of the fleet is the one that gets looked at. `uscha top`
is that view: a k9s/htop-style TUI that projects the QA ledger (board of obligations + live feed +
verdicts mode), the merge of three concepts Andrés already evaluated in a mockup.

Constraints inherited from the kit and confirmed against the engine audit:

- **stdlib-only, py3.8-clean** (repo-wide, like `qa_ledger.py`). `curses` is disqualified: it does
  not exist on native Windows without the external `windows-curses` dependency, which violates
  stdlib-only. Windows Terminal and Windows 10+ conhost support VT sequences; legacy conhost needs
  VT processing enabled explicitly.
- **CLI wiring precedent (audit E.8, corrected):** `bin/uscha.js` does **not** route subcommands to
  `qa_ledger.py` — it forwards `process.argv` to `install-uscha.py`'s own `argparse`, which knows
  only `version|install|doctor|init|uninstall|mirador`. The real precedent is `cmd_mirador`
  (`_kit_script_path`, L761-768; `subprocess.call` with `sys.executable`, L771-807): it resolves
  a sibling script inside the kit tree across both skill-tree layouts and execs it. Wiring `uscha
  top` means adding a `top` subparser to `install-uscha.py` that mirrors `mirador` exactly — not a
  change to `bin/uscha.js`.
- **Windows is first-class** (maintainer decision #5), not "best-effort" as the handoff §1 drafted it.
  This ADR overrides the handoff on that point (see Consequences).

## Decision
- **A new terminal application `uscha top`**, launched by a `top` subparser added to
  `install-uscha.py` that resolves and execs a new entry script `uscha_top.py`, resolving it exactly
  as `_kit_script_path` resolves the mirador renderer (both skill-tree layouts:
  `.claude/skills/uscha-devloop/` and the `skills/` twin, kept byte-identical per AC-01).
- **Raw ANSI/VT renderer, no curses.** The renderer emits VT100/VT sequences directly to stdout.
  Input is read per-platform, detected at runtime: `termios`+`tty` on POSIX, `msvcrt` on Windows.
  On legacy Windows conhost, VT output processing is enabled via `SetConsoleMode`
  (`ENABLE_VIRTUAL_TERMINAL_PROCESSING`) through `ctypes` (stdlib); if that call fails, the app does
  not emit raw escapes into a terminal that cannot interpret them — it degrades to the `--once` plain
  frame and exits 0 (ADR-034 owns the render contract; this ADR owns the platform matrix).
- **No server.** State is read from files by polling `mtime` every N seconds (`--refresh`, default 2).
  No sockets, no SSE. This phase is portable and dependency-free by construction.
- **Two data boundaries, both delegated, never re-implemented in the TUI:**
  - *read* — the app shells out to the engine subcommand `qa_ledger.py top --json` (ADR-032) and
    renders that JSON. It derives no KPI itself (single-derivation rule, the 1.48.1/mirador lesson).
  - *write* — the app shells out to the existing `qa_ledger.py curate` subcommand (ADR-033). It is
    the *medium* of the human verdict, never a promoter. **(1.89.0)** the `top` subparser forwards
    `--human` to `uscha_top.py` the way it already forwards `--refresh`/`--once`, so the verdict's
    author is nameable from the launcher and not only from a direct invocation; absent, it is not
    passed and the TUI falls back to `$USERNAME`/`$USER`, then to `curate`'s own default.
- **UI copy is English** (repo convention since kit 1.55.0), e.g.
  `DONE 14/24 (58%) · machine owes 2 · you owe 4 · untagged 4`.

## Platform matrix (v0.1)
| Surface | Renderer | Input | VT enablement |
|---|---|---|---|
| POSIX / WSL2 | raw VT to stdout | `termios`+`tty` | native |
| Windows Terminal / conhost (Win10+) | raw VT to stdout | `msvcrt` | native |
| legacy conhost (VT off) | raw VT after enable | `msvcrt` | `SetConsoleMode` via `ctypes`; on failure → `--once` |
| no TTY (pipe / CI) | one plain frame | none | n/a — `--once`, exit 0 |

## Consequences / Risks
+ The status view runs anywhere Python and a terminal do; no browser, no daemon, no dependency.
+ The `mirador`-resolution precedent means wiring is a known, small pattern, not new plumbing.
- **Override of handoff §1:** the handoff drafted Windows as "best-effort" with POSIX primary.
  Maintainer decision #5 makes Windows first-class; this ADR follows the decision. The cost is the
  `ctypes`/`SetConsoleMode` path and its failure fallback, both testable without a real terminal.
- A raw-ANSI renderer re-implements the sliver of curses the app needs (cursor moves, clear, color).
  That sliver is small, deterministic, and — unlike curses — portable and dependency-free; the
  golden-frame oracle (ADR-034) pins its output byte-for-byte.
- `mirador` HTML is untouched (out of scope §8); the two coexist as report vs. live view.

## Verification
- [ ] `uscha top` is reachable through the same wiring path as `mirador` (`install-uscha.py` subparser) and runs stdlib-only, py3.8-clean (AC-T-18)
- [ ] no TTY -> `--once` prints one plain frame and exits 0 (AC-T-20)
- [ ] Windows legacy conhost: VT enabled via `SetConsoleMode` (ctypes); on failure the app degrades to the `--once` plain frame, never raw escapes (AC-T-22)
- [ ] 80x24 degradation keeps the layout intact, feed shortens first (AC-T-21)
- [ ] no server: the state is re-read only when a watched file's `mtime`/size moved, polled every `--refresh` s (default 2, floor 0.5); the primitive is asserted directly, the TTY session is not (AC-T-12)

## What this ADR does NOT decide
- The JSON shape or the per-obligation state ladder — **ADR-032**.
- The verdict write path and its invariants — **ADR-033**.
- The purity of `render()` and the golden-frame oracle — **ADR-034**.
- Any engine persistence the deferred fields need (age, verdict medians, obligation-count burn-up,
  a designed spec-pin, `AC_TAG` widening) — **ADR-035**.
- Phase-2 keys (`d` spec↔code diff, `o` rerun) and the spec-lens editor — deferred, out of scope §8.
