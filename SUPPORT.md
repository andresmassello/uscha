# Support

**Solo-maintained project.** Best effort, no SLA. That is the honest expectation to set before
you depend on it.

## Where to go

| You want | Go to |
|---|---|
| To understand the method | **[uscha.dev](https://uscha.dev)** — paradigm, the five rules, the library (essay, 2-day course, reference, paper) |
| Install / configuration reference | [`uscha-kit/INSTALL.md`](uscha-kit/INSTALL.md), [`uscha-kit/README.md`](uscha-kit/README.md) |
| Something behaves differently than documented | [open a bug](https://github.com/andresmassello/uscha/issues/new/choose) |
| A security or privacy problem | [`SECURITY.md`](SECURITY.md) — **privately**, never a public issue |
| What changed in a release | `uscha-kit/CHANGELOG-X.Y.Z.md` in the repo |

## Before opening an issue

Run this and paste the output — it carries version, OS, Python, and what is installed where:

```bash
npx --yes @andresmassello/uscha@latest doctor --target all
```

## Supported

Only the **latest published version**. There are no backport branches.

Only **Claude Code** and **Codex** have been exercised against a real agent. The other targets
(cursor, copilot, gemini, cline, pi) are measured only to the point that files land where each
agent documents reading them, and that `doctor` reads them back — that they load is a documented
expectation, not a measurement. See the compatibility matrix in the README.
