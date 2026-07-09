#!/usr/bin/env bash
# mirador-watch.sh -- live second-screen mirador (uscha-kit 1.34.0).
# Regenerates mirador.html every N seconds from the current ledger; the page is rendered
# with a meta-refresh at the same interval, so a browser open on it updates on its own.
#
# Usage (run in a spare terminal, from the project root):
#   bash <kit>/.claude/skills/uscha-mirador/mirador-watch.sh [interval_seconds]
# then open mirador.html in a browser on your second screen. Ctrl-C to stop.
#
# Overridable via env: ENGINE, LEDGER, TEMPLATE, OUT, PYTHON.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
INTERVAL="${1:-30}"
ENGINE="${ENGINE:-$HERE/../uscha-devloop/qa_ledger.py}"
LEDGER="${LEDGER:-QA-LEDGER.json}"
TEMPLATE="${TEMPLATE:-$HERE/mirador.template.html}"
OUT="${OUT:-mirador.html}"
PY="${PYTHON:-python3}"
command -v "$PY" >/dev/null 2>&1 || PY=python
echo "mirador-watch: regenerating $OUT every ${INTERVAL}s (Ctrl-C to stop). Open $OUT in a browser."
while true; do
  "$PY" "$HERE/mirador-render.py" --engine "$ENGINE" --ledger "$LEDGER" \
    --template "$TEMPLATE" --out "$OUT" --refresh "$INTERVAL" || \
    echo "mirador-watch: render failed (ledger missing? run uscha-devloop first) -- retrying"
  sleep "$INTERVAL"
done
