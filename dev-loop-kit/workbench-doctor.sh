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

KITDIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Workbench doctor ==="
if [ -f "$KITDIR/VERSION" ]; then line "dev-loop-kit" "$(cat "$KITDIR/VERSION")"; else line "dev-loop-kit" "VERSION no encontrado"; fi

echo "--- herramientas ---"
probe "Claude Code"      claude  claude --version
probe "Python 3"         python3 python3 --version
probe "git"              git     git --version
probe "GitHub CLI (opc)" gh      gh --version
probe "Node (solo npm)"  node    node --version

echo "--- skills en ~/.claude/skills ---"
SK="$HOME/.claude/skills"
if [ -d "$SK" ]; then
  for s in discovery adr-refine dev-loop sys-doc characterize reverse-discovery code-review judgment-day improve; do
    if [ -e "$SK/$s/SKILL.md" ] || [ -e "$SK/$s.md" ]; then line "$s" "OK"; else line "$s" "—"; fi
  done
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
