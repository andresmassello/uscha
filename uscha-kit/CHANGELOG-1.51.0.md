# uscha-kit 1.51.0 — a third install target: pi (Earendil) (2026-07-24)

After the 1.50.2 portability patch made the kit run everywhere, this adds **pi** — Earendil's
`@earendil-works/pi-coding-agent` — as a first-class install target alongside `codex` and
`claude`. The 9 skills implement the Agent Skills standard, so they load into pi unmodified.
Smoke suite: 386/386.

## The target
`install --target pi` places the 9 `uscha-*` skill directories flat under **`~/.agents/skills/`**
— the harness-neutral sibling of the `codex` target's `~/.agents/plugins/` — plus an install
marker so the doctor can measure presence and version. Skills only: no plugin manifest, no
`settings.json`, no hook. It uses the same transactional install as the Claude target (stage →
back up → atomic replace → marker last), so a late failure rolls the target back with nothing
lost.

- **`--target all`** installs codex + claude + pi in one run. **`both` stays a legacy alias**
  for codex + claude, so existing scripts and users keep their exact prior behavior.
- `doctor --target pi` reports `healthy`, `version_match`, and the skill roster, exactly like
  the other targets.

## `golden_guard`: INV-GOLDEN-01 per target, reported honestly
The doctor now reports, per target, whether the golden-write guard is **mechanical** or
**advisory** — the field `golden_guard`:

- **claude: `enforced`** when the PreToolUse hook is registered (else `advisory`).
- **codex: `advisory`** — the Codex plugin has no hooks mechanism, so INV-GOLDEN-01 has always
  been advisory there (this just makes it visible).
- **pi: `advisory`.** pi's blocking `tool_call` event can enforce the invariant, and the guard
  ships as a precompiled extension — `uscha-kit/pi/golden-guard.js`, plain JS, no build step, to
  respect the kit's stdlib-only limit. But the kit reports **advisory, not enforced**, because
  the block has not been measured against a real pi run — the same honesty the plugin
  `hooks.json` gap follows. A verified pi run flips it to enforced; until then the kit does not
  claim enforcement it hasn't seen.

## Not done (out of this release)
Verified against a real pi install: the extension's actual load path and the `tool_call` block
(the `advisory` above is exactly this gap). Also unverified: the Codex install roots on POSIX,
and a real macOS end-to-end `npx` install (the CI matrix runs the suite on macOS runners, but
not a user-style install flow). `AGENTS.md` (shipped 1.50.2) is the context file pi reads.

Regression: smoke **T101** — pi installs 9 skills + marker under `~/.agents/skills`; doctor
reads healthy for a real install and unhealthy for an empty home; `golden_guard` is `advisory`
for pi and `enforced` for a hook-registered Claude install; `--target all` resolves to all
three while `both` stays codex+claude.
