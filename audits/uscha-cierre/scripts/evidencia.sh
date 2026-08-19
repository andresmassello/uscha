#!/bin/sh
# evidencia.sh -- INV-T1: sella EVIDENCIA.md vinculada al estado EXACTO del codigo.
#
# Uso:
#   scripts/evidencia.sh [-b <base-ref>] [archivo-de-evidencia ...]
#
#   -b <ref>   base del scope (default: ultimo tag; si no hay tags, arbol vacio)
#   archivos   logs/artefactos que respaldan los claims (bats.log, matriz.log, ...)
#              se registran CON su sha256: un log intercambiado despues no valida.
#
# Regla: solo se sella sobre working tree LIMPIO. Cambios sin commitear = estado
# no capturable = evidencia imposible por definicion.
#
# Salida: EVIDENCIA.md en la raiz del repo. Exit 0 ok, 2 error.

set -u

die() { printf 'evidencia: ERROR: %s\n' "$1" >&2; exit 2; }

sha256() {
    if command -v sha256sum >/dev/null 2>&1; then sha256sum "$@" | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then shasum -a 256 "$@" | awk '{print $1}'
    else die "no hay sha256sum ni shasum"
    fi
}

command -v git >/dev/null 2>&1 || die "falta git"
git rev-parse --git-dir >/dev/null 2>&1 || die "no es un repo git"

BASE=""
while getopts b: opt; do
    case $opt in
        b) BASE=$OPTARG ;;
        *) die "uso: $0 [-b base-ref] [archivos...]" ;;
    esac
done
shift $((OPTIND - 1))

cd "$(git rev-parse --show-toplevel)" || die "no puedo ir a la raiz del repo"

# Tree limpio, con dos exenciones seguras: EVIDENCIA.md (el sello anterior) y
# los archivos de evidencia pasados como args si estan untracked -- a esos los
# cubre el hash del sello, no el tree check.
es_arg() {
    _buscado=$1; shift
    for _a in "$@"; do [ "$_a" = "$_buscado" ] && return 0; done
    return 1
}
SUCIO=0
_st=$(git status --porcelain -uall)
if [ -n "$_st" ]; then
    while IFS= read -r _linea; do
        [ -n "$_linea" ] || continue
        case $_linea in
            "?? EVIDENCIA.md") continue ;;
            "?? "*) if es_arg "${_linea#\?\? }" "$@"; then continue; fi ;;
        esac
        SUCIO=1
    done <<EOF
$_st
EOF
fi
[ "$SUCIO" -eq 0 ] || die "working tree sucio: commitea o descarta antes de sellar (INV-T1)"

EMPTY_TREE=4b825dc642cb6eb9a060e54bf8d69288fbee4904
if [ -z "$BASE" ]; then
    BASE=$(git describe --tags --abbrev=0 2>/dev/null || printf '%s' "$EMPTY_TREE")
fi
git cat-file -e "$BASE^{commit}" 2>/dev/null || [ "$BASE" = "$EMPTY_TREE" ] || die "base-ref invalida: $BASE"

COMMIT_SHA=$(git rev-parse HEAD)
DIFF_SHA=$(git diff "$BASE" HEAD | sha256)
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Los archivos de evidencia deben existir; se registran con hash propio.
for f in "$@"; do
    [ -f "$f" ] || die "archivo de evidencia inexistente: $f"
done

{
    printf '# EVIDENCIA -- sello INV-T1\n\n'
    printf 'commit_sha: %s\n' "$COMMIT_SHA"
    printf 'base: %s\n' "$BASE"
    printf 'diff_sha256: %s\n' "$DIFF_SHA"
    printf 'fecha: %s\n' "$TS"
    printf 'archivos:\n'
    if [ $# -eq 0 ]; then
        printf '  (ninguno declarado)\n'
    else
        for f in "$@"; do
            printf '  %s sha256:%s\n' "$f" "$(sha256 "$f")"
        done
    fi
    printf '\nEste sello vale UNICAMENTE para el commit y diff de arriba.\n'
    printf 'check-terminado.sh recomputa y rechaza cualquier divergencia.\n'
} > EVIDENCIA.md

printf 'evidencia: sellado %s (base %s, %s archivos)\n' "$COMMIT_SHA" "$BASE" "$#"
exit 0
