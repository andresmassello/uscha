# uscha-kit 1.40.2

## Changed

- Reworked install documentation around the npm/npx path for Codex, Claude Code, and mixed-machine setups.
- Added `uscha-kit/INSTALL.md` as the focused install guide.
- Kept Git checkout/link mode, Claude Code plugin commands, and manual copy as secondary/debugging options with tradeoffs.

## Verification

- `npm view @andresmassello/uscha version`
- `npx --yes @andresmassello/uscha@latest version --json`
- `bash uscha-kit/tests/smoke-engine.sh`
