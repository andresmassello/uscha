# CONSTITUTION.md — invariantes del proyecto (spec-loop)

La capa **por encima de los ADR**. Registra lo que **ningún ADR ni SPEC puede violar**,
gane el trade-off que gane. Un ADR *elige* entre alternativas; la CONSTITUTION *prohíbe*.

> Jerarquía de la verdad: **SPEC** = qué debe pasar · **ADR** = por qué esta forma ·
> **CONSTITUTION** = qué nunca es aceptable.

Versionada, una por proyecto. La leen `/discovery`, `/adr-refine` y `/dev-loop` **antes**
de proponer o tocar nada. Una violación es un finding **BLOCKER** (no negociable): el agente
DEBE registrarla — `qa_ledger.py flag-blocker --kind constitution` — y una vez registrada
bloquea convergencia y capea el readiness ≤65 hasta `--resolve` (decisión humana). El engine
no lee este archivo: la obligación de detectar y registrar la violación es del agente/humano;
el enforcement del registro sí es del engine. Nunca se resuelve "rodeándola" en código.

## Seguridad (no-negociable)

- [ ] Secretos nunca en logs ni en el repo            <!-- CWE-532 / CWE-798 -->
- [ ] Toda entrada externa validada antes de usar      <!-- CWE-20 -->
- [ ] Solo SQL parametrizado, nunca concatenado        <!-- CWE-89 -->
- [ ] Credenciales / certificados cifrados en reposo
- [ ] Nunca cruzar ambientes ni credenciales (dev / prod)

## Dominio (COMPLETAR por proyecto)

> Reglas de negocio que no se pueden romper jamás. Ejemplos (reemplazar por los de tu dominio):

- [ ] Idempotencia obligatoria en operaciones críticas
- [ ] Numeración secuencial sin huecos lógicos
- [ ] Exactitud al centavo; jamás dos efectos por un mismo `requestId`

## Operación (no-negociable)

- [ ] Sin migration destructiva sin rollback explícito
- [ ] Ningún merge ni release automático — human gate siempre
- [ ] Evidencia capturada por ejecución, nunca narrada

## Simplicidad — "Reduce" (no-negociable)

> La ley 1 de Maeda y el "Simplicity First" de Karpathy, hechos gate determinístico.
> No es CC por AST: son *proxies* medibles sobre el diff. Lo mide
> `qa_ledger.py simplicity-check`; un veredicto **OVERBUILT** es finding **BLOCKER**.

- [ ] Código mínimo que resuelve lo pedido — sin features, capas ni "flexibilidad" no solicitadas <!-- YAGNI / generalidad especulativa -->
- [ ] Sin abstracciones especulativas — cada tipo/capa nuevo se justifica contra la SPEC <!-- YAGNI -->
- [ ] Anidación acotada — aplanar con guard clauses / extraer función <!-- CWE-1124 -->
- [ ] Cambio acotado al presupuesto (`defaults.simplicity`) — restar antes de sumar
- [ ] "¿Un senior diría que esto está sobre-construido?" Si sí, se recorta antes de convergir

## Tests efectivos — "coverage miente" (no-negociable)

> Coverage dice que la línea *corrió*; no que un test la *verifica*. La efectividad se
> mide con mutation testing (PIT): si al mutar el código el test no se cae, el test no
> aserta. Lo mide `qa_ledger.py pit-check` sobre el `mutations.xml`.

- [ ] Los tests ASERTAN comportamiento, no solo ejecutan código <!-- assertion-gap -->
- [ ] Test-strength por encima del gate (`--min-score`) en el área tocada
- [ ] Cero mutantes vivos en lógica de dominio / camino crítico sin justificación explícita
- [ ] Coverage alto con mutantes vivos = falsa seguridad; se cierra la brecha, no se ignora

## Integridad del gate — "no gamear al que mide" (no-negociable)

> Un maker-optimizador toma el camino más barato a "verde", y editar el gate suele ser
> lo más barato. El aparato que mide la correctitud NO lo modifica el cambio que mide,
> sin sign-off humano explícito. (Osmani lista los red-flags; la regla es síntesis del kit.)

- [ ] El cambio no debilita el gate: no borra ni skipea tests, no deshabilita lint, no baja thresholds
- [ ] Reescritura masiva de asserts existentes = flag (la red de seguridad editada para aceptar lo roto)
- [ ] Sin helper nuevo que duplique uno existente <!-- reuso / Reduce -->
- [ ] Alto blast-radius: el checker es no-correlacionado con el maker (otra familia/perfil); el loop que produjo el cambio no es su único aprobador
- [ ] Los diffs de tests se leen más estricto que los de producción

## Golden — comportamiento pre-cambio (no-negociable)

> **INV-GOLDEN-01.** En migraciones/modernizaciones, ningún módulo entra en fase de cambio sin
> un golden suite capturado y commiteado sobre su comportamiento PRE-cambio. El golden lo captura
> un script ejecutando el código ORIGINAL con inputs reales; el agente **NUNCA** genera ni edita
> los `.approved` — es la única pieza que el agente no puede authorear, y esa es su razón de existir.
> **CWE-440** (Expected Behavior Violation).

- [ ] Migración: golden suite capturado + commiteado ANTES de tocar el módulo
- [ ] Los `.approved` son verdad de campo; aprobados por un HUMANO, nunca por el agente
- [ ] `golden-diff` limpio (byte a byte) = condición dura de cierre del módulo tocado
- [ ] Corpus documentado; módulo con corpus insuficiente = PARTIAL, nunca COVERS

## Cómo se hace cumplir

- `/discovery` y `/adr-refine` la leen y derivan de acá el **severity gate** (paso
  "restricciones inviolables"). Cada invariante lleva, donde mapea, una referencia CWE.
- `/dev-loop` la consulta antes de tocar un área gobernada; una violación se registra con
  `qa_ledger.py flag-blocker --kind constitution --note "<invariante>"` y entra al ledger
  como finding **BLOCKER** (cap de readiness ≤ 65, bloquea convergencia hasta `--resolve`).
  Detectarla es obligación del agente/humano; una vez registrada, el enforcement es del engine.
- La invariante **Simplicidad** se mide sin criterio humano: `qa_ledger.py simplicity-check`
  puntúa el diff (minimalidad, anidación, abstracción) y devuelve `SIMPLE / ACCEPTABLE /
  OVERBUILT`. **OVERBUILT** = BLOCKER (exit 1): se recorta, no se converge.
- La invariante **Tests efectivos** se mide con `qa_ledger.py pit-check`: si el mutation
  score cae bajo el gate o sobreviven mutantes en el camino crítico, es finding **BLOCKER** —
  coverage verde no alcanza. Caro → tier *scheduled / incremental*, no en el inner loop.
- La invariante **Integridad del gate** la mide `qa_ledger.py gate-check`: tests borrados o
  deshabilitados y thresholds bajados = **BLOCKER** (exit 1); supresiones de lint y asserts
  removidos = revisar (o `--strict`). Para alto blast-radius se exige además un checker
  no-correlacionado con el maker (distinta familia/perfil) — eso es proceso, no código.
- La invariante **Golden (INV-GOLDEN-01)** la mide `qa_ledger.py golden-diff`: cualquier `.received`
  que no matchee su `.approved` (o sin aprobar) = **DIVERGE**, corta la cadena antes de judgment-day.
  El agente no toca `.approved` (idealmente un hook `PreToolUse` lo hace imposible).
- **Un ADR que contradiga la CONSTITUTION no es válido**: se escala, no se aprueba. Si una
  decisión necesitaría violar un invariante, primero se discute cambiar la CONSTITUTION
  (decisión humana explícita), nunca se "rodea" en silencio.
