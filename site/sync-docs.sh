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
# The file list is READ from tools/facts-gated-files.txt -- the ONE list, shared with the smoke
# suite's T0-live and with tools/release.py. Until 1.97.0 this script and the suite each carried
# their own, and the difference was a hole: the release wrote the `site/docs/` copies (which the
# `rm -rf site/docs` above deletes) while their canonical `docs/` twins were only checked.
# Pure shell on purpose: bash 3.2 has no `mapfile`, and this must run wherever the deploy does.
PY="${PYTHON:-python}"
QL="uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py"
GATED=""
while IFS= read -r line || [ -n "$line" ]; do
  case "$line" in ''|'#'*) continue;; esac
  GATED="$GATED $line"
done < tools/facts-gated-files.txt
[ -n "$GATED" ] || { echo "tools/facts-gated-files.txt is empty or missing -- refusing to deploy on an unmeasured claim set"; exit 1; }
# shellcheck disable=SC2086
"$PY" "$QL" facts --check $GATED
echo "facts gate: site claims match the derived facts -- safe to deploy"
