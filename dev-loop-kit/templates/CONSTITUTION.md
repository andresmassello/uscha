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

## Reuso — "REUSE-FIRST" (principio; el proxy AVISA, gatea si se declara)

> Muda de duplicacion (Poppendieck cap. 4): el codigo IA reinventa en vez de reusar
> (GitClear *Maintainability Gap*: +81% de duplicacion desde 2023). `simplicity-check`
> NO la ve — puntua el diff en AISLAMIENTO, nunca contra lo que ya existe. La mide
> `qa_ledger.py waste-check` (clones Type-1/2 del diff vs el repo). El HECHO —un bloque
> de 5+ lineas ya existe en `archivo:linea`— es medido; el VEREDICTO "wasteful" es
> heuristica con falsos positivos conocidos (boilerplate, DTOs, SQL/JSON embebido), asi
> que **avisa por default** y gatea SOLO con `defaults.waste.gate: true` o `--gate`
> (procedencia: el config commiteado ES la declaracion). CWE-1041 / DRY.

- [ ] No reimplementar lo que ya existe en el repo — reuso antes que clon
- [ ] Duplicacion dentro del cambio acotada — extraer un helper antes de clonar
- [ ] Un WASTEFUL, si el humano declaro el gate, se reusa/refactoriza, no se converge

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

## Anti-ceremonia — Lean sobre el propio método (meta-invariante)

> El riesgo no es un gate malo: es la **suma** de gates buenos volviendo `/dev-loop` una
> auditoría. Eso es *over-processing* — muda de ceremonia (Poppendieck cap. 4). Aplica a la
> herramienta, no al código: si un paso no agrega valor **para el humano**, es desperdicio.
> Es una **meta-invariante** — el criterio que TODO gate futuro debe pasar antes de entrar.
> Hoy solo la regla 3 está mecanizada (el veredicto único de `readiness`, kit 1.25.0); el
> resto es disciplina de diseño y criterio de review, no algo que el engine chequee.

- [ ] **Corre sin que el humano tipee nada** — un script/agente lo autocompleta; sin formularios de rutina
- [ ] **Habla solo cuando importa** — falla, o perfil de riesgo alto; si habla siempre, se silencia por defecto
- [ ] **Colapsa en `readiness`** — un número + una línea, no otra pantalla (`--verbose` abre el detalle)
- [ ] **Un cambio trivial lo saltea** — gateado por perfil de riesgo <!-- principio: perfiles A–E aún NO mecanizados en el engine -->

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
- La invariante **Reuso (REUSE-FIRST)** la mide `qa_ledger.py waste-check`: clones Type-1/2
  del diff vs el repo (`dup_vs_repo` es la senal dominante). **Advisory por default** (avisa
  con `archivo:linea` a reusar, exit 0); con `defaults.waste.gate: true` o `--gate` un
  **WASTEFUL** es exit 1 y se persiste con `log-gate --kind waste --verdict fail` (cap de
  readiness ≤ 65, bloquea convergencia). Proxy honesto Type-1/2, jamas semantico ni por AST.
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
- La meta-invariante **Anti-ceremonia** no la mide ningún subcomando: es el filtro de admisión
  de gates nuevos (¿autocorre? ¿calla salvo cuando importa? ¿colapsa en `readiness`? ¿lo saltea
  un cambio trivial?). Su única pata mecanizada hoy es el veredicto único de `readiness` (kit
  1.25.0): los gates persistidos se muestran colapsados en una línea por defecto y se abren con
  `--verbose`. Un gate que no pasa las cuatro preguntas no entra al kit — se documenta por qué.
- **Un ADR que contradiga la CONSTITUTION no es válido**: se escala, no se aprueba. Si una
  decisión necesitaría violar un invariante, primero se discute cambiar la CONSTITUTION
  (decisión humana explícita), nunca se "rodea" en silencio.
