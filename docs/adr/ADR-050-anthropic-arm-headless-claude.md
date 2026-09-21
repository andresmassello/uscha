---
governs:
  - tools/bench-compile-claude.py
  - uscha-kit/tests/smoke-engine.sh
---
# ADR-050: The Anthropic arm — a Claude arm re-run by SCRIPT through headless Claude Code, recording the EXACT model id (anthropic-arm v0.1)

## Status: Accepted (2.5.0)

## Context

ADR-042 built the cross-vendor arm and, at the end of its UNMEASURED list, named a debt it
could not pay:

> **The Anthropic arms record only a bare alias, not an exact model id.** `c-haiku/`,
> `c-sonnet/` and `c-opus/` each write `model`/`model_version` as the alias handed to the API —
> `"haiku"`, `"sonnet"`, `"opus"`. What each alias resolved to on Anthropic's backend in Aug
> 2026 was never captured and cannot be reconstructed after the fact. Future rounds must record
> an exact model id for every arm, Anthropic included.

The three Claude arms were compiled by hand. There was no script to re-run one, and no place in
the compilation record for the exact model id even if there had been. The engine itself carries
the standing instruction, in the comment above `COMPILE_SEALED`: *"A future compiler script
SHOULD populate `compilation_report.model_version` with the exact resolved model id (as
bench-compile-codex.py does with `gpt-5.5 via codex-cli ...`), never a bare alias — provenance
the seal deliberately does not enforce."*

This ADR is that script for the Anthropic arm.

## Decision

### `tools/bench-compile-claude.py` — the Codex arm's protocol, vendor swapped to headless Claude

`tools/bench-compile-claude.py` dispatches a BLIND compilation through headless Claude Code
(`claude -p`, CLI 2.1.270) and stages the result as a `c-<alias>/` compilation the engine
validates. It is the Anthropic-arm counterpart of `tools/bench-compile-codex.py` and mirrors
every one of its blind-isolation guarantees:

- **Blind by construction.** The working directory handed to the model is an EMPTY temp dir
  outside the repo; the canonical package is inlined in the prompt and never touches that disk;
  the oracle is never rendered; a mechanical leak audit (`oracle_strings` + `leaks`, ported
  verbatim with the Codex arm's thresholds) re-checks the PROMPT before dispatch — a leak there
  refuses before `claude` is ever called — and the SOURCE after.
- **The engine judges, the script never does.** Every staged compilation goes through
  `qa_ledger.py compile-validate`, sealed with the engine's own `_compile_seal`. A refused one is
  staged as `x-<alias>-REFUSED/`, invisible to the bench's `c-*` discovery, so a bad run cannot
  quietly become evidence.
- **The prompt is byte-identical to the Codex arm's** and re-derivable. Both arms read the SAME
  committed run contract, `tools/codex-arm/slots.json` (target stack, source units,
  implementation constraints, canonical files are vendor-neutral); there is no second slot copy
  and no `--emit-slots` here. Because the prompt is a pure function of the committed canonical
  package plus that slot table, the twelve prompt sha256s re-derive exactly, and they equal the
  Codex arm's committed hashes to the byte (asserted by AC-CA-03).

### The alias stays; the exact id is recorded beside it

`compilation_report.model` is the **alias** (`"haiku"` / `"sonnet"` / `"opus"`), so the bench's
anonymised model lettering — built over sorted model names — is unchanged
(`{codex: M1, haiku: M2, opus: M3, sonnet: M4}`) and no published `M<n>` claim moves.
`compilation_report.model_version` and `backend.model_slug` carry the **exact resolved model
id** the CLI reports for the run (e.g. `claude-opus-4-8 via claude-code 2.1.270`) — the
provenance ADR-042 item 8 said future rounds must capture, and the provenance the compile seal
deliberately does not enforce. The exact id is hunted out of the `claude -p` event stream (the
per-model usage breakdown keyed by exact id, then a `usage.model`, then a result/init `model`
field), and where the CLI names none the record says so honestly rather than passing the alias
off as an id.

### Isolation — what is ENFORCED versus what is a LIMIT (stated because honesty is the point)

- **NO TOOLS is enforced by flags AND asserted by measurement.** The dispatch passes
  `--restricted --tools "" --disallowed-tools "*" --strict-mcp-config --permission-prompts none`
  (every flag verified against `claude -p --help` on 2.1.270): `--restricted` removes the
  built-in tools that run code and ignores user/project/local settings, `--tools ""` disables
  all built-in tools, `--strict-mcp-config` drops every MCP server, and `--permission-prompts
  none` denies anything that would prompt. On top of that, `parse_events()` counts the
  `tool_use` blocks in the returned event stream and the script **REFUSES** if that count is not
  0. This is a STRONGER guarantee than the Codex arm, which could only assert 0 shell commands
  post-hoc: here the tool surface is removed by flag AND the empty count is proven from
  telemetry.
- **Write mode is `return`.** The model is told to return the complete source inside a JSON that
  conforms to the schema passed on `--json-schema`, writing no file itself; the script writes the
  returned bytes. `return` needs no write tool, so it composes with `--tools ""`, and it matches
  the Codex arm's `return` mode — both arms are one-shot generators judged by a withheld oracle,
  which is what the bench measures. A `tool` mode exists for parity (it re-enables only Write) and
  is recorded in `write_mode`; it relaxes the no-tools guarantee and is not the default.
- **CONFIG ISOLATION is asserted at CREATION, a manual check across the run — the same honesty
  caveat as the Codex arm's isolated CODEX_HOME.** The dispatch runs with an isolated
  `CLAUDE_CONFIG_DIR` this script builds and asserts holds only what it placed there (nothing),
  so no user `CLAUDE.md`, memory, skill, plugin or MCP server in the real config dir reaches the
  model. The CLI may populate that directory during a dispatch; that it writes no user
  rules/memory there is a MANUAL check on a real round, not an invariant held across it — named
  here rather than left to read as mechanical. The empty cwd plus the leak audit remain the
  load-bearing blindness guarantee. One residual the isolated `CLAUDE_CONFIG_DIR` does NOT
  cover: an OS-level managed-settings policy (`--restricted`'s own help notes managed settings
  and `--settings` still apply) lives outside that directory, the Claude-side analogue of the
  admin `requirements.toml` ADR-042 named for Codex; on a machine with such a policy the run is
  no longer fully isolated, and a real round must check for one.
- **The vendor system prompt is UNMEASURED.** Claude Code prepends its own system prompt, not
  removable from outside the CLI — the same asymmetry ADR-042 lists for the ~15k-token Codex
  system prompt.

A hard `--max-budget-usd` ceiling is passed on every dispatch so a misconfigured run stops
instead of spending without bound.

### This release LANDS the tool, dry-run-proven, without a live round

Exactly as `bench-compile-codex.py` was first landed: the tool exists, is proven by `--dry-run`
plus a smoke test, and spends nothing. **No live `claude -p` compilation was run in this
release, no money was spent, and the frozen v1 records `c-haiku/`, `c-sonnet/`, `c-opus/` are
untouched** — they still validate and still record the bare alias, which is exactly what proves
this release did not rewrite them. On a clean run the tool stages a validated compilation to a
scratch out-dir the caller names (never into the fixture); a real round is the user copying a
validated staged run into `c-<alias>/`, which finally answers ADR-042 item 8 by recording the
exact id that alias resolved to. The run report `RUN-REPORT.json` and the harvested manifest
`CLAUDE-ARM-RUN.json` (vendor `anthropic`, cli, alias + exact `model_slug`, write mode, per-entry
`prompt_sha256`/`oracle_strings_checked`, run1/run2 blocks, totals including `tool_use_blocks`)
are written to the gitignored out dir, analogous to `CODEX-ARM-RUN.json`; no manifest with real
run data is committed here because no real round was run.

## What is measured

A new criteria family, **`AC-CA-01..06`**, measured by smoke **T168**, the way T157 tests the
Codex arm — WITHOUT invoking a live `claude` (not available in CI, and it costs money):

- **AC-CA-01** — `--dry-run` renders a prompt for all 12 entries and dispatches/stages nothing
  (no `COMPILATION.json` under the temp target).
- **AC-CA-02** — no oracle string reaches any rendered prompt; a distinctive oracle string
  planted into the prompt trips the leak audit; and a RED PROBE breaks the audit (`leaks()` → `[]`)
  to prove the assertion is load-bearing — with it broken, the planted case stops refusing.
- **AC-CA-03** — the prompt sha256 is re-derivable: stable across two `--dry-run` renders, and
  byte-identical to the Codex arm's committed hashes (same slot table, same canonical package).
- **AC-CA-04** — a returned payload stages a `COMPILATION.json` that `compile-validate` exits 0
  on and promotes; `model` is the bare alias while `model_version` and `backend.model_slug` carry
  an EXACT id (the alias-vs-exact distinction asserted directly); a corrupted payload is a NAMED
  refusal into `x-<alias>-REFUSED/`.
- **AC-CA-05** — the anonymised model map is unchanged (`{codex: M1, haiku: M2, opus: M3,
  sonnet: M4}`) and the 36 frozen v1 Claude arm records still carry the bare alias (a
  representative entry's three still `compile-validate`), so this release added a dispatcher, not
  a fifth arm, and rewrote nothing.
- **AC-CA-06** — the no-tools guarantee is measured: a clean event stream counts 0 tool calls
  and recovers the exact id, a stream carrying a `tool_use` counts >0 (which `run_entry` turns
  into a refusal), and `build_command` carries the isolation posture.

`AC-CA-01..04` and `AC-CA-06` read `tools/bench-compile-claude.py`, which lives at the repo root
and is not shipped inside the kit: from an extracted kit they report `None` = UNMEASURED, never a
silent pass. `AC-CA-05` measures the fixture and the bench cache, so it runs from the kit alone.

## What stays UNMEASURED

1. **No live round was run.** The tool is landed and dry-run-proven; the exact ids the aliases
   resolve to are recorded only when the user runs a real round. Until then ADR-042 item 8 is
   *closable*, not *closed*.
2. **The vendor system prompt asymmetry** (above), unchanged from ADR-042.
3. **`CLAUDE_CONFIG_DIR` relocation across the run** is a manual check, not a measured invariant
   (above), unchanged in spirit from the Codex arm's isolated-home caveat.

## Consequences

- `tools/narrated-claims.txt` entry 7 (retired by ADR-042 when the cross-vendor claim was
  answered) is unaffected; this ADR does not retire a published claim, it lands the instrument
  that lets a future round record an exact id.
- The published subcommand count does not move: `bench-compile-claude.py` is a repo-root research
  tool, not an engine subcommand, exactly like `bench-compile-codex.py`.
- ADR-042's UNMEASURED item 8 gains a path to closure and this ADR is linked from it in spirit;
  the item stays UNMEASURED until a real round records the id.

## Alternatives considered

- **Duplicate `slots.json` into a `claude-arm/`.** Rejected: the run contract is vendor-neutral
  and a second copy is how two copies start to differ. The Codex arm owns `--emit-slots`; this
  arm reads what it committed.
- **Record the exact id in a new arm dir `c-claude/`.** Rejected: the arms are `c-<alias>` and the
  lettering is built over sorted model names — a `c-claude` would re-letter the map and move every
  published `M<n>` claim, for no gain. The alias stays in `model`; the exact id rides in
  `model_version`.
- **Run a live round now to close item 8.** Rejected for this release: landing the tool
  dry-run-proven is the same discipline `bench-compile-codex.py` shipped under, and it spends
  nothing. The real round is the user's to run.
- **Use `--bare` for isolation.** Rejected as the default: `--bare` forces API-key auth (OAuth
  and keychain are never read), which would break a subscription user's run. `CLAUDE_CONFIG_DIR`
  isolation plus `--restricted --strict-mcp-config --tools ""` keeps auth working and isolates.
