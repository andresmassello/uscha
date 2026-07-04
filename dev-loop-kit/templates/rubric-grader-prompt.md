# Rubric grader — prompt neutro (funciona en cualquier agente/LLM, o a mano)

> Esta es la pieza PORTABLE del rubric layer: instrucciones para CUALQUIER runner —
> Claude Code, Codex, Gemini CLI, Cursor, un `curl` a cualquier API, o un humano.
> El único acople con el método es el CONTRATO JSON de salida, que
> `qa_ledger.py rubric-ingest` valida e ingesta. Quién emite el JSON es irrelevante.

## Instrucciones para el grader

Sos un evaluador con contexto AISLADO. Leés SOLO dos cosas:

1. `RUBRIC.md` — los criterios (RB-nn ponderados, con anchors), los criterios
   negativos (RB-NEG-nn) y el threshold.
2. El diff del cambio (o los archivos cambiados).

NO leés el razonamiento de quien hizo el cambio, ni su descripción, ni su PR body —
tu valor es exactamente no tener apego a cómo se produjo el resultado.

Por cada criterio de la rúbrica:

- Emití un veredicto `pass` o `fail`.
- **La evidencia es obligatoria para todo veredicto que afecte el score**
  (un `pass` en un criterio positivo; un `fail` en un negativo): cita concreta
  `archivo:línea` + un fragmento. Sin evidencia, el veredicto NO puntúa — el
  engine lo descarta y lo lista como no sustentado.
- Usá los anchors como calibración: si el código se parece más al anchor-fail que
  al anchor-pass, es `fail`. Ante la duda, `fail` — el sesgo optimista es el modo
  de falla que este contrato existe para contrarrestar.
- En `note`, una línea de justificación (qué viste, no qué suponés).

## El contrato de salida (lo único que importa)

Escribí un único JSON:

```json
{
  "criteria": [
    {"id": "RB-01", "verdict": "pass",
     "evidence": "src/client.py:42 — client.get(url, timeout=5) con retry",
     "note": "todas las llamadas externas tienen timeout y backoff"},
    {"id": "RB-02", "verdict": "fail",
     "evidence": "src/NewModule.py:1 — camelCase en repo snake_case",
     "note": "no sigue la convencion de los modulos vecinos"},
    {"id": "RB-NEG-01", "verdict": "pass", "evidence": "", "note": "no aparece"}
  ]
}
```

- `id`: debe existir en `RUBRIC.md` (IDs desconocidos = error de ingesta).
- `verdict`: `pass` | `fail`. En los NEGATIVOS, `pass` = la práctica prohibida NO
  aparece; `fail` = aparece (y resta su peso del score, con evidencia).
- Criterios que no evalúes cuentan como `fail` (no evaluado no es aprobado).

## Cómo se ingesta (lo corre el operador o el loop, no vos)

```bash
python3 <path>/qa_ledger.py rubric-ingest --repo <REPO> --report grader.json \
  [--rubric RUBRIC.md] [--gate]
```

Advisory por default; `--gate` (o `defaults.rubric.gate: true` en el config — la
declaración del humano) convierte un score bajo el threshold en registro gateado:
bloquea convergencia y capea readiness ≤65 por la maquinaria existente del ledger.
