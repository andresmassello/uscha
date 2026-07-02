# CLAUDE.md — protocolo del repo (spec-loop)

Reglas **permanentes** de este repo. Claude Code las lee en cada sesión. Lo puntual de
cada cambio vive en `SPEC.md` / `docs/adr/` / `ACCEPTANCE.md`, no acá.

> Si usás otros agentes además de Claude Code, copiá este archivo como `AGENTS.md`
> (mismo contenido) para que también lo lean.

## Reglas innegociables

1. **No codear desde una idea vaga.** Si no hay `SPEC.md` + `ACCEPTANCE.md`, primero
   modelar: `/discovery` (sistema nuevo) o `/adr-refine` (feature conocido). Recién con el
   paquete escrito se construye.
2. **La verdad vive en archivos, no en el chat.** Antes de tocar código, leé `SPEC.md`,
   `ACCEPTANCE.md` y `docs/adr/*.md`. No dependas de la conversación: el contexto se
   resetea, los sub-agentes y el CI leen el repo.
3. **Convergé, no persigas el cero.** Aplicá solo los findings ≥ severity gate; el resto
   va a `ISSUES-DEFERRED.md`. El loop termina cuando converge, no cuando "no hay issues".
4. **Disciplina de ADR + CONSTITUTION durante el build.** Antes de tocar un área, leé
   `CONSTITUTION.md` (invariantes inviolables) y los ADR del área. Pará y proponé un ADR si
   vas a: meter una dependencia nueva, crear un patrón nuevo, elegir entre alternativas no
   obvias, o contradecir un ADR aceptado. **Una violación de la CONSTITUTION es BLOCKER: se
   escala, nunca se rodea.** Linkeá el código con `// ADR: <slug> — ver docs/adr/...`.
5. **Evidencia capturada, no narrada.** La evidencia la produce la ejecución (tests,
   gates, coverage) — no se transcribe a mano. Ausente = sin evidencia, nunca "OK".
6. **Legacy baseline.** En código viejo: 0 findings HIGH/CRITICAL nuevos, 0 regresiones,
   sin warnings nuevos en archivos tocados. La deuda vieja se congela, la nueva se bloquea.
7. **Change budget.** Máx. iteraciones/archivos según el plan; 0 cambios de schema sin
   ADR; 0 dependencias nuevas sin aprobación. Si se supera el scope o un fix revierte otro
   → escalá (no sigas solo).
8. **Nunca edites la SPEC/ADR para que la implementación parezca correcta.** Si la
   realidad obliga a cambiar la SPEC, versionala y volvé a Ready.
9. **Human gate.** No hagas merge ni release automático. Parás en el PR; el merge y el
   smoke en ambiente real los decide una persona.

## Jerarquía de la verdad

`CONSTITUTION.md` (qué nunca es aceptable) ▸ `SPEC.md` (qué debe pasar) ▸ `docs/adr/` (por qué esta forma). La CONSTITUTION está por encima de los ADR: ningún ADR ni SPEC puede violarla. La leen `/discovery`, `/adr-refine` y `/dev-loop` antes de proponer o tocar nada.

## Comandos (skills)

- `/discovery` — idea → CONTEXT/DOMAIN-MODEL/CONSTITUTION/SPEC/ADR/ACCEPTANCE/RISKS/HANDOFF
- `/adr-refine` — feature conocido → SPEC + ADR + ACCEPTANCE
- `/dev-loop` — plan → build → QA loop → PR (para en el merge)
- `/sys-doc` — documenta el sistema desde el ledger

## Adapter del proyecto (COMPLETAR por repo)

> Esto es lo único específico del stack. Completalo y borrá este recordatorio.

- **Build:** `<p.ej. mvn -q compile>`
- **Tests:** `<p.ej. mvn -q test>`
- **Static gate:** `<p.ej. mvn -q verify -Pqa  → checkstyle-result.xml, pmd.xml, spotbugsXml.xml>`
- **Coverage:** `<p.ej. target/site/jacoco/jacoco.xml>`
- **No-go zones:** `<carpetas/archivos que no se tocan>`
- **Secretos / credenciales:** `<dónde están y qué NO loguear>`
