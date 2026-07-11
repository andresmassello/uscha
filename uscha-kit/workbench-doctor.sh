#!/usr/bin/env bash
# workbench-doctor — qué tengo instalado del workbench (genérico, sin el stack del proyecto)
# Uso:  bash workbench-doctor.sh
set +e

line() { printf '  %-20s %s\n' "$1" "$2"; }

probe() { # $1 = etiqueta, $2 = binario, $3.. = comando de versión
  local label="$1"; local bin="$2"; shift 2
  if command -v "$bin" >/dev/null 2>&1; then
    line "$label" "OK   $("$@" 2>/dev/null | head -n1)"
  else
    line "$label" "FALTA (no está '$bin' en PATH)"
  fi
}

windows_shell() {
  case "$(uname -s 2>/dev/null)" in
    MINGW*|MSYS*|CYGWIN*) return 0 ;;
  esac
  [ "${OS:-}" = "Windows_NT" ]
}

python_candidate() {
  local command="$1" version major minor
  shift
  command -v "$command" >/dev/null 2>&1 || return 1
  version="$("$command" "$@" --version 2>&1)" || return 1
  if [[ "$version" =~ Python[[:space:]]+([0-9]+)\.([0-9]+) ]]; then
    major="${BASH_REMATCH[1]}"; minor="${BASH_REMATCH[2]}"
    if [ "$major" -gt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -ge 8 ]; }; then
      PYTHON_COMMAND="$command${*:+ $*}"
      PYTHON_VERSION="$version"
      return 0
    fi
  fi
  return 1
}

find_python() {
  if windows_shell; then
    python_candidate python || python_candidate py -3
  else
    python_candidate python3 || python_candidate python
  fi
}
KITDIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Workbench doctor ==="
if [ -f "$KITDIR/VERSION" ]; then line "uscha-kit" "$(cat "$KITDIR/VERSION")"; else line "uscha-kit" "VERSION no encontrado"; fi

echo "--- herramientas ---"
probe "Claude Code"      claude  claude --version
if find_python; then
  line "Python 3.8+" "OK   $PYTHON_VERSION ($PYTHON_COMMAND)"
else
  line "Python 3.8+" "FALTA (requiere un Python >=3.8 utilizable en PATH)"
fi
probe "git"              git     git --version
probe "GitHub CLI (opc)" gh      gh --version
probe "Node (solo npm)"  node    node --version

echo "--- skills en ~/.claude/skills ---"
SK="$HOME/.claude/skills"
SOURCE_SKILLS="$KITDIR/.claude/skills"
if [ -d "$SK" ]; then
  SKILL_COUNT=0
  for source_skill in "$SOURCE_SKILLS"/uscha-*; do
    [ -d "$source_skill" ] || continue
    SKILL_COUNT=$((SKILL_COUNT+1))
    skill_name="$(basename "$source_skill")"
    if [ -e "$SK/$skill_name/SKILL.md" ] || [ -e "$SK/$skill_name.md" ]; then
      line "$skill_name" "OK"
    else
      line "$skill_name" "—"
    fi
  done
  [ "$SKILL_COUNT" -gt 0 ] || echo "  (no hay skills uscha-* en la fuente del kit)"
else
  echo "  (no existe $SK — todavía no instalaste skills globales)"
fi

echo "--- salud nativa de Claude Code ---"
if command -v claude >/dev/null 2>&1; then
  echo "  corré:  claude doctor   ·   claude whoami"
else
  echo "  Claude Code no instalado (ver WORKBENCH.md §2)"
fi
echo "=== fin ==="
