# dev-loop-kit 1.2.8 — golden testing completo (characterize + hook + gitattributes)

## Nuevo skill: characterize (golden-capture)
- Captura el golden del código ORIGINAL con inputs reales, por un harness determinístico.
- 4 fases: harness → checklist de no-determinismo (locale es-AR obligatorio) → captura
  (.received) → STOP para aprobación humana. NUNCA crea/edita un .approved.
- Lo orquesta reverse-discovery en su fase 2.

## Nuevo hook: hooks/block-approved-writes.ps1 (PreToolUse, INV-GOLDEN-01)
- Bloquea mecánicamente que el agente escriba/renombre cualquier *.approved.* (Write/Edit/
  Bash-write → exit 2). Deja pasar lecturas. Probado.
- WIRING (pegar en settings.json — no lo puede hacer el agente por el guardrail de self-mod):
    "hooks": { "PreToolUse": [ { "matcher": "*", "hooks": [
      { "type": "command",
        "command": "powershell -NoProfile -ExecutionPolicy Bypass -File \"<KIT>/hooks/block-approved-writes.ps1\"" }
    ] } ] }

## Nuevo: templates/.gitattributes
- `*.approved.* binary` + `*.received.* binary` — line endings no generan diffs falsos
  (crítico Windows/SQL Server). Copiar a la raíz del repo de migración.

## Estado del golden testing (del HANDOFF) — AHORA completo en el kit
- golden-diff (gate, byte-compare) ✓ · characterize (captura) ✓ · reverse-discovery (front
  brownfield) ✓ · INV-GOLDEN-01 (CONSTITUTION) ✓ · hook PreToolUse ✓ · .gitattributes ✓
