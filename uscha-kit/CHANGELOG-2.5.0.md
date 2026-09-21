# uscha-kit 2.5.0 — the Anthropic arm: a Claude arm re-run by SCRIPT, recording the EXACT model id (ADR-050) (2026-09-21)

## The one debt ADR-042 could not pay

The cross-vendor arm (1.99.0, ADR-042) ended with an UNMEASURED list, and its last item was a
provenance gap it could not close from where it stood:

> The Anthropic arms record only a bare alias, not an exact model id. `c-haiku/`, `c-sonnet/` and
> `c-opus/` each write `model`/`model_version` as the alias handed to the API. What each alias
> resolved to on Anthropic's backend in Aug 2026 was never captured and cannot be reconstructed
> after the fact. Future rounds must record an exact model id for every arm, Anthropic included.

The three Claude arms were compiled by hand. There was no script to re-run one, and the engine
itself carried the standing instruction (in the `COMPILE_SEALED` comment): *a future compiler
script SHOULD populate `compilation_report.model_version` with the exact resolved model id, never
a bare alias.* This release lands that script for the Anthropic arm.

## `tools/bench-compile-claude.py` — the Codex arm's protocol, vendor swapped

The new dispatcher is the Anthropic-arm counterpart of `tools/bench-compile-codex.py`. It
dispatches a BLIND compilation through headless Claude Code (`claude -p`, CLI 2.1.270) and stages
the result as a `c-<alias>/` compilation the engine validates, mirroring every blind-isolation
guarantee of the Codex arm:

- **Blind by construction.** An EMPTY temp workdir outside the repo; the canonical package inlined
  in the prompt, never on disk; the oracle never rendered; a leak audit (ported verbatim, same
  thresholds) that re-checks the PROMPT before dispatch — refusing before `claude` is called — and
  the SOURCE after.
- **The engine judges, the script never does.** `compile-validate` decides, sealed with the
  engine's own `_compile_seal`; a refused compilation is staged as `x-<alias>-REFUSED/`, invisible
  to the bench's `c-*` discovery.
- **One shared run contract.** The arm reads the SAME committed `tools/codex-arm/slots.json` the
  Codex arm regenerates — the contract is vendor-neutral, and a second copy is how two copies start
  to differ. The rendered prompt is therefore byte-identical to the Codex arm's, and its twelve
  sha256s re-derive exactly.

## The alias stays; the exact id rides beside it

`compilation_report.model` remains the bare alias (`haiku`/`sonnet`/`opus`), so the bench's
anonymised lettering — built over sorted model names — is unchanged
(`{codex: M1, haiku: M2, opus: M3, sonnet: M4}`) and no published `M<n>` claim moves.
`compilation_report.model_version` and `backend.model_slug` carry the EXACT resolved model id the
CLI reports (e.g. `claude-opus-4-8 via claude-code 2.1.270`), hunted out of the `claude -p` event
stream. That is the provenance ADR-042 item 8 said future rounds must capture — and where the CLI
names no id the record says so honestly, never passing the alias off as one.

## Isolation: enforced versus limit, stated plainly

The no-tools guarantee is STRONGER than the Codex arm's. The dispatch passes
`--restricted --tools "" --disallowed-tools "*" --strict-mcp-config --permission-prompts none`
(every flag verified against `claude -p --help` on 2.1.270), which removes the tool surface; and
the script counts the `tool_use` blocks in the event stream and REFUSES if the count is not 0 — the
tool surface is removed AND the empty count is proven from telemetry, where the Codex arm could
only assert 0 shell commands post-hoc. Config isolation uses an isolated `CLAUDE_CONFIG_DIR`
asserted at creation to hold only what the script places there; as with the Codex arm's isolated
home, what the CLI writes there during a run is a MANUAL check, not an invariant. Write mode is
`return` (no write tool needed, so it composes with `--tools ""`), and a hard `--max-budget-usd`
ceiling rides every dispatch.

## Landed dry-run-proven, no live round, frozen arms untouched

Exactly as `bench-compile-codex.py` was first landed: the tool exists, is proven by `--dry-run`
plus a smoke test, and spends nothing. No live `claude -p` compilation was run, no money was
spent, and the frozen v1 `c-haiku/`, `c-sonnet/`, `c-opus/` records are untouched — they still
validate and still record the bare alias, which is what proves this release rewrote none of them.
A real round — the user copying a validated staged run into `c-<alias>/` — comes later and finally
records the exact id.

## Acceptance

- `docs/adr/ADR-050-anthropic-arm-headless-claude.md` (Accepted (2.5.0)); `docs/adr/INDEX.md`
  gains its row (research-program group).
- A new criteria family `AC-CA-01..06`, measured by smoke **T168** the way T157 tests the Codex
  arm — WITHOUT invoking a live `claude`: dry-run rendering, the leak audit with a RED PROBE,
  re-derivable and cross-vendor-identical hashes, a returned-payload staging that validates and
  carries an exact id (alias-vs-exact asserted), the unchanged four-key lettering, and the no-tools
  count. `AC-CA-01..04`/`06` read the repo-root dispatcher, so from an extracted kit they report
  UNMEASURED, never a silent pass.

## Also on main since v2.4.0

- `docs(bench)`: every published Diamond result is dated (September 2026) and its four compilers
  named; the record notes that the Anthropic arms captured only an alias (ADR-042 item 8) — the
  gap this release lands the instrument to close.

## Not in this release

No live compilation, no spend, no change to the frozen v1 arms or the bench verdicts. No new
engine subcommand: `bench-compile-claude.py` is a repo-root research tool, so the published
subcommand count does not move.

Suite: 459 checks · 0 fail; acceptance 342/343.
