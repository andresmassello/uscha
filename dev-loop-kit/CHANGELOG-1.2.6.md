# dev-loop-kit 1.2.6 — fix golden-diff (judgment-day, 2 jueces, coincidencia)

## Fix (cmd_golden_diff) — verificado contra los casos reproducidos por los jueces
- **[CRITICAL] `str.replace` global** reemplazaba TODAS las ocurrencias de `.received.`:
  con el marcador en una carpeta padre (snapshots por fecha) o dos veces en el nombre,
  derivaba el `.approved` mal → DIVERGE falso, y en el peor caso un **FALSE CLEAN** (dejaba
  pasar una divergencia, exit 0). Fix: `_golden_approved_path()` deriva solo del BASENAME,
  última ocurrencia (rpartition), nunca del path del directorio.
- **[real] directorios `*.received.*`** se escaneaban como fixtures → filtro `os.path.isfile`.
- **[gap] `Foo.received` sin extensión** se salteaba (false CLEAN) → segundo glob `*.received`.
- Read-only confirmado por ambos jueces: cero write/rename; el agente no puede authorear el golden.
