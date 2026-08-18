# uscha-kit 1.86.1 — what four blind judges found in 1.86.0, fixed the same day (2026-08-18)

1.86.0 shipped after one blind review. Then four more judges — risk, readability, reliability,
resilience + truth-pass — read the committed diff independently. No blocker; six confirmed
findings, one rejected with reasons, one deferred by name. All fixed here.

## Fixed

- **The instrument had a hole (ADR-012).** `facts --check` compared the *number* of subcommands a
  document claims against the derived facts, and the doc's parser-surface table said "52" while
  listing 51 rows without `top`. Number right, table wrong, gate green. The `top` row is added
  (EN + ES twins + site mirrors) and `facts --check` now also diffs the table's row names against
  `subcommands.list` — a missing or extra row is drift by name (T139 proves a doctored copy fails).
- **`quarantine_obs` leaked into measured rows.** `top --json` emitted the matching observation id
  even when the obligation's state was `MEASURED_*` (a green tag vetoes quarantine). It is `null`
  unless the state is `QUARANTINE`; a fixture with both signals on one AC pins it.
- **Missing ledger showed a traceback** through the direct `uscha_top.py` entry point (the `uscha
  top` wrapper already said it cleanly). Both the TUI and the engine's `_load` now say
  `ledger 'X' not found here -- run the dev loop first, or pass --ledger` and exit 1.
- **Duplication.** The per-repo green/red aggregation existed twice (`readiness`, `top`) — now
  one `_sum_ac_tags` (readiness output byte-identical before/after); three identical sibling-script
  resolvers in `install-uscha.py` — now one `_kit_script_path`; a dead `DEFAULT_SIZE` removed.
- **Coverage the judges asked for:** the real `spec_pin: null` path (a ledger in a temp dir outside
  any git work tree), a zero-obligations frozen state with its two golden frames (`DONE 0/0 (0%)`,
  never 100%), and the repo-skip branch of the quarantine scan (exit 0, pure JSON, stderr names it).

## Rejected, with the reason on record

The reliability judge read a nested non-git subdirectory pinning its parent repo's HEAD as a
fabricated `spec_pin`. It is not: a subdirectory of a git work tree is versioned by that tree — the
monorepo-subproject case — and that HEAD is the honest pin of those files. Bounding the call to
`--show-toplevel == path` would break legitimate subprojects. What was true in the finding is that
the null path had no real test; it has one now, and ADR-032 / SPEC §3 say exactly when null happens.

## Deferred, by name

`uscha_top` measures line width in codepoints, not display columns — CJK/wide project names can
overflow the terminal (ISSUES-DEFERRED). No fixture, no affected user today.

The re-judge of these fixes caught one more thing, fixed here too: the friendly missing-file message
was hardcoded to "ledger … pass --ledger" while `_load` also serves `init --config` and `rebuild
--baseline`; each call site now names its own file kind and flag (pinned by the suite).

Suite: 427 checks · 0 fail; acceptance 165/172 (7 UNMEASURED on purpose: `AC-T-11..17`, M2/M3).
