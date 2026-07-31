# uscha-kit 1.58.0 — spec-drift: the spec maintenance tax, made visible (2026-07-31)

Fast-path Phase 2 from the same handoff that produced 1.57.0. The #1 category-level
criticism of spec-driven development is that specs rot silently — the code moves and the
spec stays where it was, and nothing in the loop notices. This release gives uscha a
mechanical answer, with the doctrinally honest coupling: **advisory, never a gate**, because
whether an older spec still covers newer code is a relevance judgment, and per the core
principle a guess advises while facts block. Gating on commit-date lag would be the method
violating itself (ADR-005 records the decision and the rejected alternatives).

## `spec-drift` — subcommand 31

```bash
python qa_ledger.py spec-drift --repo <name> --json   # advisory report; exit 0 ALWAYS
```

- **Mapping is explicit:** a `governs:` glob list in the frontmatter of `SPEC.md` and each
  `docs/adr/*.md`. The glob dialect is the same one `protected_paths` uses (`**` crosses
  directories, segment-anchored, case-insensitive).
- **Signal:** last commit date of the spec vs. the newest commit touching any governed file
  (chunked `git log`, so a `**` glob over a large tree does not overflow a command line).
  Governed code newer by more than `defaults.spec_drift.max_lag_days` (default 30, or
  `--max-lag-days`) → **`SPEC_STALE`**, listing the files newer than the spec.
- **Absence is named, not passed:** no `governs:` frontmatter → **`UNMAPPED`** — and so is a
  mapping whose globs match no tracked file, because a mapping that matches nothing measures
  nothing. A spec with no commit date reports **`UNTRACKED`**. Neither reads as "no drift".
- **Advisory end to end:** exit code 0 always; the latest run lands in the ledger
  (`spec_drift`) and `dashboard --json` passes it through **only when a run exists** — a
  virgin ledger keeps the exact prior schema, same stability rule the fast-path key follows.
  No readiness input, no gate record, no step counter: a stale spec is a prompt for a human
  conversation, not a blocked pipeline.
- Honest limit (in the ADR): the signal detects *"nobody touched the spec while its code
  moved"*, not *"the spec is wrong"* — and touching a spec merely to silence the advisory
  refreshes the date without improving the content. The advisory prompts a human look; it
  cannot verify substance.

## Measured against its own acceptance

`ACCEPTANCE.md` gained `AC-SD-01..04`; smoke **T114** exercises each against a real git
fixture with pinned commit dates (deterministic lag math on every runner) and feeds a
sidecar so each criterion closes on its own named testcase: stale-beyond-lag lists the
newer files (AC-SD-01), spec-refreshed-after reads CLEAN (AC-SD-02), no-frontmatter reads
UNMAPPED and never CLEAN (AC-SD-03), and the readiness score is numerically identical
before and after an advisory run (AC-SD-04). The stale-sidecar rule from T113 applies: the
sidecar is deleted before the run, so a crash yields UNMEASURED, never a leftover green.

## Also

- The example `uscha.config.json` documents `defaults.spec_drift`.
- The `spec_drift` block in `dashboard --json` is the data contract for any renderer; the
  shipped mirador template does not yet draw a dedicated panel for it (`proposal` — same
  status as the `fast_path` key, the data ships before the pixel).
- The frontmatter parser accepts the bare-scalar shorthand (`governs: src/**`) as a single
  glob instead of silently reporting a misleading empty mapping (fresh-review finding).
- Subcommand count: **31** on every published surface.

Suite: 399 checks, all green.
