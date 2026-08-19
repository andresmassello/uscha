#!/bin/sh
# check-terminado.sh -- INV-T1: TERMINADO sin evidencia vinculada al estado
# exacto del codigo es una afirmacion falsa. Este check la rechaza.
#
# Uso: scripts/check-terminado.sh
#
# Valida, contra EVIDENCIA.md:
#   1. working tree limpio (estado actual = estado commiteado)
#   2. commit_sha del sello == HEAD actual
#   3. diff_sha256 del sello == recomputo del diff base..HEAD
#   4. cada archivo de evidencia existe y su sha256 coincide (logs no intercambiados)
#
# Exit: 0 = TERMINADO habilitado. 1 = rechazado (motivos en stdout). 2 = error de uso.

set -u

die() { printf 'check-terminado: ERROR: %s\n' "$1" >&2; exit 2; }

sha256() {
    if command -v sha256sum >/dev/null 2>&1; then sha256sum "$@" | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then shasum -a 256 "$@" | awk '{print $1}'
    else die "no hay sha256sum ni shasum"
    fi
}

command -v git >/dev/null 2>&1 || die "falta git"
git rev-parse --git-dir >/dev/null 2>&1 || die "no es un repo git"
cd "$(git rev-parse --show-toplevel)" || die "no puedo ir a la raiz del repo"

FALLAS=0
falla() { printf 'check-terminado: RECHAZO: %s\n' "$1"; FALLAS=$((FALLAS + 1)); }

[ -f EVIDENCIA.md ] || { falla "no existe EVIDENCIA.md (nadie sello nada)"; printf 'check-terminado: NO hay TERMINADO.\n'; exit 1; }

S_COMMIT=$(sed -n 's/^commit_sha: //p' EVIDENCIA.md)
S_BASE=$(sed -n 's/^base: //p' EVIDENCIA.md)
S_DIFF=$(sed -n 's/^diff_sha256: //p' EVIDENCIA.md)
if [ -z "$S_COMMIT" ] || [ -z "$S_BASE" ] || [ -z "$S_DIFF" ]; then
    falla "EVIDENCIA.md malformada (faltan campos del sello)"
fi

# Tree limpio, eximiendo untracked que el sello cubre por hash:
# EVIDENCIA.md y los archivos listados en el propio sello.
en_sello() {
    sed -n 's/^  \(.*\) sha256:[0-9a-f]\{64\}$/\1/p' EVIDENCIA.md | grep -Fxq "$1"
}
SUCIO=0
_st=$(git status --porcelain -uall)
if [ -n "$_st" ]; then
    while IFS= read -r _linea; do
        [ -n "$_linea" ] || continue
        case $_linea in
            "?? EVIDENCIA.md") continue ;;
            "?? "*) if en_sello "${_linea#\?\? }"; then continue; fi ;;
        esac
        SUCIO=1
    done <<EOF
$_st
EOF
fi
if [ "$SUCIO" -eq 1 ]; then
    falla "working tree sucio: hay cambios que ningun sello cubre"
fi

HEAD_SHA=$(git rev-parse HEAD)
if [ -n "$S_COMMIT" ] && [ "$S_COMMIT" != "$HEAD_SHA" ]; then
    falla "sello stale: sellado sobre $S_COMMIT pero HEAD es $HEAD_SHA"
fi

if [ -n "$S_BASE" ] && [ -n "$S_DIFF" ]; then
    DIFF_AHORA=$(git diff "$S_BASE" HEAD 2>/dev/null | sha256)
    if [ "$DIFF_AHORA" != "$S_DIFF" ]; then
        falla "diff divergente: el codigo revisado no es el codigo actual"
    fi
fi

# Archivos de evidencia: lineas "  <ruta> sha256:<hash>"
sed -n 's/^  \(.*\) sha256:\([0-9a-f]\{64\}\)$/\1 \2/p' EVIDENCIA.md |
while read -r ruta hash; do
    if [ ! -f "$ruta" ]; then
        printf 'check-terminado: RECHAZO: evidencia desaparecida: %s\n' "$ruta"
        printf '%s\n' "$ruta" >> .uscha-check-fallas.tmp
    elif [ "$(sha256 "$ruta")" != "$hash" ]; then
        printf 'check-terminado: RECHAZO: evidencia alterada tras el sello: %s\n' "$ruta"
        printf '%s\n' "$ruta" >> .uscha-check-fallas.tmp
    fi
done
# (subshell del pipe: las fallas de archivos se comunican via archivo temporal)
if [ -f .uscha-check-fallas.tmp ]; then
    FALLAS=$((FALLAS + $(wc -l < .uscha-check-fallas.tmp)))
    rm -f .uscha-check-fallas.tmp
fi

if [ "$FALLAS" -gt 0 ]; then
    printf 'check-terminado: NO hay TERMINADO (%s fallas). Resellar con evidencia.sh sobre el estado actual.\n' "$FALLAS"
    exit 1
fi

printf 'check-terminado: OK -- evidencia vigente para %s. TERMINADO habilitado.\n' "$HEAD_SHA"
exit 0
