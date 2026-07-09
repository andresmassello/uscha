# uscha-kit 1.40.0

## Added

- Added npm/npx package router (`@andresmassello/uscha`) with `uscha` and `uscha-kit` CLI bins.
- Added smoke coverage for the Node router delegating to the canonical Python installer.

## Changed

- Documented npm-first install commands for public adoption while keeping `install-uscha.py` as the source of truth.

## Verification

- `node bin/uscha.js version --json`
- `npm pack --dry-run --json`
- `bash uscha-kit/tests/smoke-engine.sh`
