# dev-loop-kit 1.23.0 — rubric layer: el ACCEPTANCE de lo no-testeable (2026-07-03)

Origen: evaluación del concepto "rubrics" de Claude Code (Outcomes/graders) contra
el método. Veredicto: la ARQUITECTURA no aporta nada nuevo (maker≠checker con
contexto aislado ya existe); el edge real es **el artefacto** — criterio cualitativo
versionado. Entra con el acople corregido respecto de la propuesta original:
**advisory-first**, jamás dimensión ponderada del readiness (un grade LLM es guess
estructurado, no hecho medido — doctrina 1.10.0). Smoke suite: 139/139.

## Restricción de diseño: cero dependencia de un agente específico

Tres capas de acople decreciente — pedido explícito del humano:

1. **Núcleo (engine stdlib, cero LLM)**: `RUBRIC.md` + `spec-check --rubric` +
   `rubric-ingest` + advisory en readiness + doctor. Un humano puede llenar el JSON
   del grader a mano y todo funciona — **el smoke T43 lo prueba ejecutablemente**
   (el grader.json del test se llena a mano, sin ningún LLM).
2. **Interfaz**: el contrato JSON
   `{"criteria":[{"id","verdict":"pass|fail","evidence","note"}]}` — la ÚNICA
   superficie entre el método y cualquier grader. IDs normalizados por número
   (RB-01 == RB_1 == rb1, mismo criterio que AC-n).
3. **Graders pluggables**: `templates/rubric-grader-prompt.md` (markdown plano,
   corre pegado en Codex, Gemini CLI, Cursor, un curl, o un humano) + la skill
   `specloop-rubric` como adapter FINO de Claude Code (documentado como adapter).

## Qué hace

- **`RUBRIC.md`** (template en `templates/`): criterios `- [ ] RB-01 (peso 3) — …`
  con anchor-pass/anchor-fail (calibran al grader, el engine no los parsea),
  criterios negativos `RB-NEG-nn` (si aparecen, restan su peso) y `threshold: 0.NN`.
- **`spec-check --rubric`**: estructura = HECHO (archivo ausente, cero criterios
  positivos, IDs duplicados normalizados, threshold ausente o fuera de (0,1] →
  exit 1).
- **`rubric-ingest`** (subcomando 23): valida el contrato (IDs desconocidos =
  error — el grader no inventa criterios), aplica **evidence-or-nothing** (un
  veredicto que afecta el score sin cita `file:line` NO puntúa y se lista como no
  sustentado), computa el score ponderado vs threshold y persiste un registro
  `rubric:grade` en el ledger. **Advisory por default**: BELOW no gatea. Con
  `--gate` o `defaults.rubric.gate: true` (procedencia: declaración humana), un
  BELOW escribe registro gateado → bloquea convergencia y capea readiness ≤65 por
  la maquinaria existente; un grade limpio posterior lo levanta (latest-wins).
- **readiness**: muestra el último grade por repo como línea advisory — NO es
  dimensión con peso (measured beats narrated).
- **doctor**: si `defaults.rubric.file` está declarado, chequea existencia y
  estructura (aviso con remedio).
- **`specloop-rubric`** (7ma skill): el adapter de Claude Code — contexto aislado
  (solo diff + rúbrica, jamás el razonamiento del maker), sesgo a `fail` ante la
  duda, y prohibido declararse el gate a sí misma.

## Hardening (review fresco pre-commit, 4 hallazgos aplicados)

- `threshold: 0.8.0` (malformado) crasheaba con ValueError cruda → se trata como
  ausente y bloquea con mensaje.
- Entradas no-dict en `criteria` crasheaban → contrato roto, error explícito.
- **IDs duplicados en el reporte** (RB-01 y RB-1 del mismo criterio): el último
  pisaba al primero en silencio — vector de gaming del grader → contrato roto,
  un veredicto por criterio.
- El check de smoke "convergencia bloqueada por el gate" era VACUO (converged ya
  salía 1 en ledger virgen por 'no agent steps') → el fixture ahora converge
  ANTES, y se verifica además que un grade limpio LIBERA la convergencia
  (latest-wins).

## La ventaja (por qué entra al método)

El criterio cualitativo (convenciones, ergonomía de API, sanidad del error
handling, calidad de docs) hoy vivía en la cabeza de cada pase de QA. Ahora es
**versionado, diffeable, auditable** (cada veredicto con evidencia al ledger) y
**portable** (viaja en el repo; cualquier humano/agente hereda el estándar).
Anchors + negativos bajan la varianza del grader.

## Límite honesto

Nicho más chico que en la era en que se evaluó la idea: el acceptance trazable
(1.10.0) ya cierra lo testeable — esta capa cubre SOLO lo genuinamente cualitativo,
y siempre como guess estructurado: nunca reemplaza un gate duro.
