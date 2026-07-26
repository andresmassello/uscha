# uscha-kit 1.55.2 — the golden guard, honestly (2026-07-26)

An external review audited the INV-GOLDEN-01 hook — something none of this project's own
reviews had ever done — and every technical finding was correct. The guard for the method's
flagship invariant was a **narrated** control wearing a mechanical claim, in a project whose
entire thesis is *measured beats narrated*. Smoke suite: 395/395.

## What was wrong
- **FAIL-OPEN.** An unparseable payload returned 0 (allow). A guard that opens when it is
  confused is not a guard.
- **Case-sensitive.** A capitalised golden walked past — on Windows and macOS, where the
  filesystem is case-insensitive, that is a real bypass, not a curiosity.
- **Blocked harmless reads.** Reading a golden was refused, which trains people to work around
  the guard. It bit this project's own maintenance work more than once.
- **Five tool names.** Anything else write-capable was never inspected.
- **Universal claims.** The README said *"the agent never writes"*, the kit README said *"the
  agent CANNOT write"*, ACCEPTANCE said *"mechanically"* — about a hook registered on the
  **Claude target only**, while every Agent-Skills target reports `golden_guard: advisory`.

## What changed
The hook is **fail-CLOSED**, **case-insensitive**, distinguishes **reads from writes** (reads
pass — `golden-diff` has to read the file it compares against), and **default-denies unknown
tools**: if a golden appears anywhere in an unrecognised tool's arguments, it blocks.

The four claims now say what is true: a **best-effort** guard, **Claude-only**, matching text.
The **measured** control is `golden-diff`, which compares bytes.

## The limit is asserted now, not merely written down
A hook that reads text can never catch an indirect write — a script that assembles the filename
from pieces, a symlink, a spawned process. Rather than leave that in a docstring, **T110 asserts
it**: the indirect-write case is tested and expected to PASS, so the blind spot is measured and
nobody mistakes the guard for a sandbox.

T110 covers 22 adversarial cases: writes in every case form, redirection, append, move, copy,
delete, tee, reader-then-redirect, in-place edit, unknown tools with nested arguments, malformed
and non-dict payloads, and the legitimate reads that must keep working. It immediately caught a
bug in the NEW hook: a piped write slipped through, because the pipeline separators were blanked
before the parser looked for them.

## Also
`smoke.yml` gained `permissions: contents: read` and a 20-minute job timeout. It runs on
`pull_request`, i.e. on arbitrary code from forks, so it must never see a publishing secret.
