# uscha-kit 1.56.0 — uninstall, and the paperwork a public repo owes (2026-07-26)

Two external reviews of the now-public repository produced a P1 list. This closes the ones that
are code and documentation; the rest are GitHub/npm settings only the owner can flip, listed at
the end so nobody assumes they are done. Smoke suite: 396/396 on Linux, macOS and Windows.

## `uscha uninstall`
The installer writes into **your** agent's home — skill directories, a `settings.json` entry and
a blocking `PreToolUse` hook — and shipped with no way to undo that. The burden of a clean
removal fell on the user, by hand, in files they did not write.

```bash
npx --yes @andresmassello/uscha@latest uninstall --target all --dry-run
npx --yes @andresmassello/uscha@latest uninstall --target all
```

The risk here is **not** failing to delete ours; it is deleting **theirs**. So:

- Only paths this kit wrote are touched: the nine `uscha-*` skill directories, our hook file,
  our marketplace entry, our marker.
- `settings.json` is edited, never replaced: our `PreToolUse` entries are dropped and every
  foreign hook — including one sitting in the same group — is preserved, as is every unrelated
  setting. An emptied group disappears; a group that was already empty is left alone.
- **Without an install marker it REFUSES**, because there is no proof the files at that root are
  ours. `--force` overrides and says what it assumed.
- `--dry-run` plans and touches nothing.

Regression: smoke **T111** plants a foreign hook, a foreign setting and a foreign skill, then
asserts all three survive a full `--target all` uninstall while every one of ours is gone across
all seven targets — plus the dry-run and the marker refusal.

It also exposed a latent bug in `emit()`: it identified doctor output by the *key name*
`targets`, so any other payload carrying that key crashed on a missing `healthy` field. It now
matches on the payload's **shape**.

## Supply-chain and repository hygiene
- **Actions pinned to full commit SHAs** (`checkout`, `setup-python`, `setup-node`), with the
  version in a trailing comment so an upgrade stays reviewable. A tag can be repointed at new
  code by whoever controls the action, and this workflow runs on every push.
- `permissions: contents: read` and a 20-minute job timeout. The workflow runs on
  `pull_request` — arbitrary code from forks — so it must never see a publishing secret.
- **`SECURITY.md`** with a private reporting route, the security-sensitive components named
  (installer, hook, npm router, report parsers, skills), and an explicit **threat model** that
  says plainly what Uscha does *not* protect against: an adversarial agent, prompt injection,
  forged evidence, hostile report files, and the INV-GOLDEN-01 bypass that smoke T110 asserts.
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SUPPORT.md`, issue and PR templates. The PR template
  asks for *the check that proves it* and for *what is NOT covered*.
- `package.json` gained the missing `author` field.

## Compatibility matrix in the README
**Generated from `TARGETS`/`SKILL_ROOTS` in the installer**, so it cannot drift from the code.
It carries the column that actually matters — *exercised against a real agent* — which is `yes`
for exactly two of seven targets. For the rest, what is measured is that files land where each
agent documents reading them and that `doctor` reads them back.

## NOT done — owner settings, not code
Enable branch protection on `main`; enable private vulnerability reporting and secret scanning
with push protection; configure npm **Trusted Publishing (OIDC)** so releases stop depending on
a long-lived token on a laptop. Until that last one is done, provenance is unattested.
