#!/usr/bin/env bash
# Regenerates site/docs/ from the canonical sources in docs/.
# site/docs/ is BUILD OUTPUT — never edit it by hand; edit docs/ and re-run this.
set -euo pipefail
cd "$(dirname "$0")/.."

rm -rf site/docs
mkdir -p site/docs

cp docs/uscha-claude-code-doc.html docs/uscha-claude-code-doc-EN.html \
   docs/uscha-dev-course.html docs/uscha-dev-course-EN.html \
   site/docs/

cp -r docs/paper site/docs/paper

echo "site/docs synced from docs/"
