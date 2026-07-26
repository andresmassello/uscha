# Contributing

Uscha is solo-maintained and opinionated. Issues and small, focused PRs are welcome; large
redesigns are better as an issue first, so nobody spends a weekend on something that will not be
merged.

## The one rule that matters

**No claim without a check.** This project's whole argument is that measured beats narrated, so
a change that adds behaviour must add the check that proves it, in the same commit. A PR that
asserts something in a doc but not in the suite will be asked for the check.

## Before you push

```bash
bash uscha-kit/tests/smoke-engine.sh
```

It must exit 0. It is fast, it needs only Python 3.8+ stdlib (plus Node for four npm-router
checks), and it is the same suite CI runs on Linux, macOS and Windows.

## House rules, and why

| Rule | Reason |
|---|---|
| **Twins stay byte-identical**: `uscha-kit/.claude/skills/` ≡ `uscha-kit/skills/` | the Claude plugin manifest reads one, the Codex one reads the other; a smoke check enforces it |
| **Docs may not claim what the engine does not do** | *under-claim, then wire, then re-claim* — if the code is not there yet, mark it `proposal` |
| **Zero references to real projects or clients** | AC-03 measures this against a hashed list; example repos are `backend-api`, `mobile-app`, … |
| **Six version surfaces move together** + a `CHANGELOG-X.Y.Z.md` | smoke T44 fails otherwise |
| **Never write or rename an approved golden** | it is field truth; a human signs it. The agent emits a `.received` and stops |
| **Conventional commits**, small and atomic | `feat:`, `fix:`, `docs:`, `test:`, `ci:`, `chore:` |

The full version lives in [`CLAUDE.md`](CLAUDE.md) — it is written for coding agents, but it is
the same contract for humans.

## Writing a smoke check

Checks are numbered (`T1`…`Tn`) and each is self-contained: build a fixture, run the engine,
assert on the output, report one `ok`/`FAIL` line. Two traps that have bitten this repo:

- **No backticks in comments inside a `$( … <<'PY' … PY )` block** — the shell executes them as
  command substitution and silently truncates your code.
- **No literal `'` or `"` inside a character class there either** — bash 3.2, which macOS still
  ships, hunts for the matching quote to the end of the file. Write `\x27` / `\x22`. Both of
  these are invisible on Linux and Windows; only the macOS CI cell catches them.

## Reporting security issues

Do **not** open a public issue. See [`SECURITY.md`](SECURITY.md).
