# uscha-kit 1.40.1

## Fixed

- Exclude Python bytecode artifacts (`__pycache__`, `*.pyc`, `*.pyo`) from the npm package tarball.
- Strengthen the npm smoke check so package dry-run fails if Python bytecode artifacts would be published.

## Verification

- `npm publish --dry-run --access public`
- `bash uscha-kit/tests/smoke-engine.sh`
