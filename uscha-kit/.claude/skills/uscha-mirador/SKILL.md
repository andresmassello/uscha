---
name: uscha-mirador
description: >
  Bird's-eye status view ("mirador") of a spec-loop project: one glance at
  readiness, sub-scores, the phase path, invariants, QA loops and a readiness
  time-lapse. Runs `qa_ledger.py dashboard --json` (read-only, deterministic,
  zero LLM narration), injects that JSON into mirador.template.html, writes
  mirador.html at the project root and opens it. The skill WIRES, it does not
  calculate — every number comes from the ledger (truth-pass: a field with no
  source shows null and the template degrades, never invented). Invoke for
  "mirador", "vista de estado", "bird's-eye", "dashboard del proyecto".
allowed-tools: Read, Write, Glob, Grep, Bash
---

# uscha-mirador — vista bird's-eye del estado

Pinta el estado REAL del proyecto de un vistazo. No narra ni estima: cablea el JSON
que emite el engine al template. Read-only.

## Contrato

- **Fuente de la verdad:** `qa_ledger.py dashboard --json` — agrega SOLO estado que el
  ledger ya tiene (readiness, subscores, phases, specs, adrs, inv, capas, loops,
  snapshots, evidence). Un campo sin fuente sale `null`/`[]`; el template degrada. **Nunca
  se inventa un dato.**
- **Template:** `mirador.template.html` (en esta carpeta). El bloque de datos vive entre
  `/*MIRADOR_DATA_START*/` y `/*MIRADOR_DATA_END*/`; el `const DATA` de ejemplo que trae es
  el **fallback offline**. El skill reemplaza SOLO esa región; no toca el resto del HTML.

## Flujo

1. **Resolvé el engine.** Usá el primero que exista:
   - `./.claude/skills/uscha-devloop/qa_ledger.py` (instalación por proyecto)
   - `~/.claude/skills/uscha-devloop/qa_ledger.py` (instalación global)

2. **Resolvé el ledger.** `QA-LEDGER.json` en el cwd (o el `--ledger` que indique el
   usuario). Si no existe, avisá: hay que correr `uscha-devloop` (o `qa_ledger.py init`)
   antes — sin ledger no hay estado que mirar.

3. **Generá el JSON del estado** (read-only, no escribe nada):
   ```bash
   python3 <engine> dashboard --ledger QA-LEDGER.json --json > .mirador-data.json
   ```
   Para el time-lapse: el histórico se llena con `qa_ledger.py readiness --record`
   (opt-in) en los checkpoints del loop; si aún no se registró, `snapshots` sale `[]` y
   el time-lapse queda vacío (es prospectivo, no se backfillea).

4. **Inyectá en el template.** Leé `mirador.template.html`, reemplazá TODO lo que hay
   entre `/*MIRADOR_DATA_START*/` y `/*MIRADOR_DATA_END*/` (inclusive del `const DATA`
   viejo) por:
   ```
   /*MIRADOR_DATA_START*/
   const DATA = <el JSON de .mirador-data.json>;
   /*MIRADOR_DATA_END*/
   ```
   No toques nada fuera de esa región. Escribí el resultado como `mirador.html` en la raíz
   del proyecto.

5. **Abrí el archivo** (best-effort, no falla si no puede — headless/CI):
   - Windows: `start "" mirador.html`
   - macOS: `open mirador.html`
   - Linux: `xdg-open mirador.html`

   Imprimí SIEMPRE la ruta absoluta de `mirador.html` (aunque no se pueda abrir).

6. **Limpieza:** borrá `.mirador-data.json` (temporal).

## Reglas

- **Cero cálculo en el skill.** Los números vienen del ledger. Si un panel se ve vacío,
  es porque el engine no tiene esa fuente todavía (truth-pass), no porque falte pintarlo.
- **Read-only.** El skill no corre gates ni modifica el ledger. `dashboard` es de solo
  lectura; el único que escribe (opt-in) es `readiness --record`, y eso lo decide el loop,
  no este skill.
- **`mirador.html` es un artefacto generado** — sugerí agregarlo al `.gitignore` del
  proyecto; se regenera cuando quieras.
