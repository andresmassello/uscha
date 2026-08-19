#!/bin/sh
# suite-cierre.sh -- suite funcional de evidencia.sh + check-terminado.sh (INV-T1)
# Autocontenida: crea un repo fixture temporal. Sin dependencias fuera de git y sh.
# Uso: sh test/suite-cierre.sh [interprete]   (default: sh; probar tambien con dash)
# Exit: 0 = todo verde, 1 = alguna falla.
#
# Historial: esta suite cazo 2 bugs reales pre-release:
#   - auto-referencia del sello (EVIDENCIA.md ensuciaba el tree que exige limpio)
#   - git status --porcelain colapsa dirs untracked (?? logs/ vs ?? logs/bats.log)

set -u

SH=${1:-sh}
AQUI=$(cd "$(dirname "$0")/.." && pwd)
FX=$(mktemp -d "${TMPDIR:-/tmp}/fx-cierre.XXXXXX") || { echo "mktemp fallo"; exit 1; }
trap 'rm -rf "$FX"' EXIT INT TERM

cd "$FX" || exit 1
git init -q && git config user.email t@t && git config user.name t
mkdir -p logs scripts
cp "$AQUI/scripts/evidencia.sh" "$AQUI/scripts/check-terminado.sh" scripts/
printf 'codigo v1\n' > main.sh
printf 'scripts/\n' > .gitignore
git add -A && git commit -qm v1 && git tag v1.0.0
printf 'codigo v2\n' > main.sh && git add -A && git commit -qm v2
printf 'ok: 12 tests passed\n' > logs/bats.log

P=0; F=0
ok() { P=$((P+1)); printf '%s: OK\n' "$1"; }
no() { F=$((F+1)); printf '%s: FALLO\n' "$1"; }
sella()  { "$SH" scripts/evidencia.sh "$@" >/dev/null 2>&1; }
checkt() { "$SH" scripts/check-terminado.sh >/dev/null 2>&1; }

if sella logs/bats.log; then ok "T1 sellado con log untracked"; else no "T1 sellado con log untracked"; fi
if checkt; then ok "T2 check vigente"; else no "T2 check vigente"; fi

echo hack >> main.sh
if checkt; then no "T3 rechazo tracked modificado"; else ok "T3 rechazo tracked modificado"; fi
git checkout -q main.sh

printf 'colado\n' > colado.sh
if checkt; then no "T4 rechazo untracked no sellado"; else ok "T4 rechazo untracked no sellado"; fi
rm colado.sh

printf 'codigo v3\n' > main.sh && git add main.sh && git commit -qm v3
if checkt; then no "T5 rechazo sello stale"; else ok "T5 rechazo sello stale"; fi

if sella logs/bats.log; then ok "T6 re-sellado"; else no "T6 re-sellado"; fi
if checkt; then ok "T6b re-sellado vigente"; else no "T6b re-sellado vigente"; fi

printf 'FAILED en realidad\n' > logs/bats.log
if checkt; then no "T7 rechazo log alterado"; else ok "T7 rechazo log alterado"; fi

rm logs/bats.log
if checkt; then no "T8 rechazo log desaparecido"; else ok "T8 rechazo log desaparecido"; fi

echo hack >> main.sh; printf 'x\n' > logs/bats.log
if sella logs/bats.log; then no "T9 sellador rechaza tree sucio"; else ok "T9 sellador rechaza tree sucio"; fi
git checkout -q main.sh

if sella logs/bats.log && checkt; then ok "T10 ciclo final completo"; else no "T10 ciclo final completo"; fi

printf '=== suite-cierre (%s): %s pasan, %s fallan ===\n' "$SH" "$P" "$F"
[ "$F" -eq 0 ]
