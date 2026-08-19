#!/usr/bin/env bash
# Regenerates site/docs/ from the canonical sources in docs/, then runs the factual-drift
# gate (ADR-012) over every authored site page. Exit non-zero = do NOT deploy.
# site/docs/ is BUILD OUTPUT -- never edit it by hand; edit docs/ and re-run this.
set -euo pipefail
cd "$(dirname "$0")/.."

rm -rf site/docs
mkdir -p site/docs

cp docs/uscha-claude-code-doc.html docs/uscha-claude-code-doc-EN.html \
   docs/uscha-dev-course.html docs/uscha-dev-course-EN.html \
   site/docs/

cp -r docs/paper site/docs/paper

# Field notes: docs/field-notes/*.md are canonical; the site pages are rendered from them.
"${PYTHON:-python}" site/build-field-notes.py

echo "site/docs synced from docs/"

# --- factual-drift gate (ADR-012): every published claim must match the derived facts ---
# Same scope as the smoke suite's T0-live check. Catches the residue a hand sweep misses:
# a stale footer version on one page while the landing reads green.
PY="${PYTHON:-python}"
QL="uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py"
"$PY" "$QL" facts --check \
  README.md uscha-kit/README.md \
  site/index.html site/es/index.html site/llms.txt \
  site/how/index.html site/es/how/index.html \
  site/diamond/index.html site/es/diamond/index.html \
  site/why/index.html site/es/why/index.html \
  site/docs/uscha-claude-code-doc.html site/docs/uscha-claude-code-doc-EN.html   site/docs/paper/uscha-paper.html   site/docs/uscha-dev-course.html site/docs/uscha-dev-course-EN.html   site/field-notes/001-treasury-migration/index.html site/es/field-notes/001-treasury-migration/index.html
echo "facts gate: site claims match the derived facts -- safe to deploy"
