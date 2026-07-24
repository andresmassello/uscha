#!/usr/bin/env bash
# Regenerates site/docs/ from the canonical sources in docs/.
# site/docs/ is BUILD OUTPUT — never edit it by hand; edit docs/ and re-run this.
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p site/docs
cp docs/uscha-playbook.html docs/uscha-playbook-EN.html \
   docs/skills-referencia.html docs/skills-referencia-EN.html \
   docs/uscha-onepager.html docs/uscha-onepager-EN.html \
   docs/uscha-team-pitch-extended.html docs/uscha-team-pitch-extended-EN.html \
   site/docs/

rm -rf site/docs/paper
cp -r docs/paper site/docs/paper

echo "site/docs synced from docs/"
