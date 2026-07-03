# The Pragmatic Programmer (20th Anniversary Ed.) × spec-loop

Análisis del libro completo (Hunt & Thomas, 497 pp) contra la metodología:
12 lectores en paralelo con el contexto de spec-loop, síntesis con dedupe
(148 conceptos crudos → lo de abajo). Fuente verificada:
<https://pragprog.com/titles/tpp20/the-pragmatic-programmer-20th-anniversary-edition/>

Tres baldes: **valida** (el libro defiende algo que spec-loop ya hace),
**mejora** (cambio concreto que el kit podría adoptar — backlog 2.0),
**tensión** (fricción real con el diseño, con su resolución propuesta).

## Validaciones (convergencia libro ↔ metodología)

- **Topic 38: Programming by Coincidence — Tip 62 'Don't Assume It — Prove It' (+ Tip 36 'You Can't Write Perfect Software': el pragmático no confía ni en sí mismo)**
  ↔ 'measured beats narrated' + UNMEASURED son la operacionalización exacta del tip: el relato del agente ('funciona') vale 0 hasta que existe un reporte medido, y el engine desconfía del agente igual que el pragmático desconfía de sí mismo — gates de hechos ingeridos (JUnit/JaCoCo), jamás de prosa.

- **Topic 34: Shared State Is Incorrect State — 'Make the Resource Transactional' (protección por convención falla en cuanto alguien se olvida)**
  ↔ Enforcement centralizado en el recurso, no en la buena voluntad: INV-GOLDEN-01 no le PIDE al agente que no escriba los .approved — un hook lo BLOQUEA; los gates viven en qa_ledger.py, no en instrucciones que el agente puede ignorar.

- **Topic 36: Blackboards — Tip 60 'Use Blackboards to Coordinate Workflow'**
  ↔ qa_ledger ES un blackboard: 9 stacks de tools publican HECHOS sin conocerse entre sí, el orden de llegada es irrelevante, los gates disparan sobre hechos ('facts block') y UNMEASURED formaliza el hecho ausente (silencio = 0, jamás 1). El libro confirma que es el patrón correcto para datos multi-fuente.

- **Topic 24: Dead Programs Tell No Lies — Tip 38 'Crash Early' (+ Topic 41 cierre: tolerar tests perma-rojos hace ignorar toda la suite)**
  ↔ Diseño fail-closed del engine: gates que BLOQUEAN en vez de degradar, y el cap 'tests rojos ≤35' del readiness es Tip 91 convertido en KPI — un pipeline que se planta hace menos daño que uno que aprueba a medias con datos ausentes.

- **Topic 3: Software Entropy — 'First, Do No Harm' (los bomberos tienden la alfombra antes de arrastrar mangueras)**
  ↔ gate-check: bloquear en el diff el borrado de tests y la baja de thresholds es 'no rompas ventanas mientras apagás el incendio' formalizado como gate de HECHO (bloquea), no como consejo.

- **Topic 40: Refactoring (las 3 reglas de Fowler) + Topic 51 'test for real' + Topic 20 'los tests artificiales no ejercitan la aplicación real'**
  ↔ characterize + golden-diff: byte-compare contra .approved generados ejecutando el código ORIGINAL con corpus REAL es la garantía mecánica de 'no cambió el comportamiento externo' — y el humano aprueba (INV-GOLDEN-01) porque el agente solo vería su propia pincelada.

- **Topic 23: Design by Contract — Semantic Invariants ('leyes inviolables centrales al SIGNIFICADO' vs políticas que cambian con la gestión)**
  ↔ La jerarquía CONSTITUTION > SPEC > ADR es la misma partición del libro: invariante semántico inviolable arriba, necesidad/política cambiable en la SPEC, decisión con contexto en el ADR.

- **Topic 35: Actors and Processes — Tip 59 'los actores comparten NADA'**
  ↔ El review fresco adversarial antes de merge es un actor share-nothing respecto del builder: no hereda su estado mental ni sus sesgos, solo recibe el mensaje (diff + SPEC). Es el fundamento teórico del dato empírico del kit: 6/6 reviews frescos cazaron bugs reales de schema.


## Mejoras accionables (backlog 2.0 — NO implementadas, candidatas)

### M1. Topic 51 — Tip 94 'Find Bugs Once' (+ Tip 31 'Failing Test Before Fixing Code' + Topic 20 'The Element of Surprise')

Gate 'regression-capture': un finding NO pasa a estado cerrado en el ledger sin referencia a un test nuevo/modificado que lo reproduzca (cruzar fingerprint del finding con el diff y la ingesta JUnit — todo dato que el ledger ya tiene). Para findings blocker, exigir además campo 'escape_analysis': qué gate/test debió atraparlo y qué acción se tomó (test nuevo, gate nuevo, búsqueda de hermanos del bug). Cierre sin test queda como guess (aconseja), jamás como fact (cierra).

*Dónde vive:* engine (qa_ledger.py: gate nuevo + campo en el schema de finding) + skill dev-loop (regla de cierre de iteración)

### M2. Topic 50 — Tip 87 'Do What Works, Not What's Fashionable' (SPEC-coconut) + Topic 9 'Representational Duplication' + Topic 41 (anécdota Jeffries/Sudoku)

Acceptance-check: IDs estables por criterio en ACCEPTANCE (formato parseable); cada criterio debe mapear a ≥1 test MEDIDO en el ledger. Criterio sin test mapeado = UNMEASURED = 0 (advise); SPEC con CERO criterios trazables = block. El readiness pasa a estar dominado por 'criterios cerrados sobre totales', con techo a la contribución de coverage/tests-verdes — suelda la forma al contenido y desactiva el Goodhart del agente.

*Dónde vive:* engine (spec-check + nueva dimensión dominante del readiness KPI) + doc ACCEPTANCE (template con IDs)

### M3. Topic 34 — nonatomic updates ('los recursos compartidos mutables incluyen ARCHIVOS': los autores sufrieron builds rotos por cwd compartido)

Hardening del ledger: escritura atómica (write-temp + rename), file-lock opcional, y gate de auto-integridad al cargar (validación de schema + checksum de la iteración previa) que BLOQUEA si el ledger quedó inconsistente. Hoy el JSON compartido entre iteraciones/hooks/agentes puede corromperse en silencio y todo el edificio 'measured beats narrated' se apoya en ese archivo.

*Dónde vive:* engine (qa_ledger.py: capa de I/O y carga)

### M4. Topic 29 — Juggling the Real World: FSM como tabla de datos + estado de workflow en storage externo

Codificar el dev-loop como FSM explícita en qa_ledger.py: tabla de datos con estados (plan, build, qa, escalated, pr-ready) × eventos (reporte ingerido, gate fallido, aprobación humana). Una transición ilegal (ej. pr-ready sin convergencia, PR sin review fresco) se vuelve hecho bloqueante MECÁNICO en vez de prosa repartida entre skills que el agente puede ignorar.

*Dónde vive:* engine (qa_ledger.py: tabla de transiciones + validador) + skill dev-loop (referencia a la tabla en vez de instrucción textual)

### M5. Topic 5 — Tip 8 'Make Quality a Requirements Issue' + Topic 8 'ETC es un valor, no una regla'

Quality bar por SPEC: discovery agrega la pregunta '¿qué nivel de calidad basta y qué dimensiones son negociables (perf, cobertura, seguridad)?'; la SPEC declara sus thresholds/presupuestos. El engine mantiene sus números actuales solo como defaults ADVISORY: un umbral únicamente BLOQUEA cuando fue declarado en la SPEC — ahí es requerimiento del humano, no opinión del kit. El principio (fact gate) es universal; el número, no.

*Dónde vive:* skill discovery (pregunta nueva) + doc SPEC (campo quality-bar) + engine (caps y presupuestos parametrizables por SPEC con fallback advisory)

### M6. Topic 37 — 'Listen to Your Lizard Brain' (el barro) + Topic 5 'Know When to Stop' (la pintura sobre-refinada)

Detector de plateau sobre el histórico de readiness, con dos salidas: (a) stall-check — KPI plano o cayendo N iteraciones consecutivas → el engine deja de aconsejar 'seguí iterando' y emite 'probable problema de diseño/SPEC: volver a ADR o re-planear' con escalación al humano; (b) stop-signal — delta < epsilon y solo quedan findings advisory (cero facts bloqueantes) → recomendar cortar e ir a PR. La convergencia per-tool existe pero hoy no emite ninguna de las dos recomendaciones.

*Dónde vive:* engine (qa_ledger.py: análisis del histórico de iteraciones)

### M7. Topic 41 (cierre) — 'no apoyar tests en cosas no confiables' (timestamps exactos, wording de errores, posiciones absolutas)

Canonicalización del golden master: characterize gana un paso donde se declaran reglas de scrub/mask de campos volátiles ANTES de que el humano apruebe los .approved, y golden-diff aplica esas reglas en el byte-compare. Sin esto, cualquier salida del código original con timestamps/ids vuelve el golden master perma-rojo o perma-frágil — y un golden perma-rojo mata la credibilidad de todo el gate.

*Dónde vive:* skill characterize (paso de declaración de volátiles) + engine (golden-diff con soporte de reglas de scrub)

### M8. Topic 43 — Stay Safe Out There ('nunca commitear secretos, API keys ni credenciales')

Secret-scan del diff como gate nuevo de gate-check: regex stdlib para patrones de keys/tokens/passwords/paths de .p12 que BLOQUEA como hecho, exactamente igual que hoy bloquea borrar tests o bajar thresholds. Python stdlib puro, barato, encaja sin fricción en 'facts block, guesses advise'.

*Dónde vive:* engine (gate-check)

### M9. Topic 51 — 'un buen proyecto puede tener MÁS código de test que de producción, y vale la pena'

Excluir los árboles de test del presupuesto de líneas/archivos del simplicity-check (o darles presupuesto propio y generoso). Si el presupuesto cuenta tests junto a producción, el gate castiga escribir tests y empuja al agente a testear menos para pasar el presupuesto — incentivo perverso directo contra el corazón del kit. Combinado con gate-check (que ya bloquea borrarlos), el incentivo queda alineado en ambas direcciones.

*Dónde vive:* engine (simplicity-check: scope del presupuesto)

### M10. Topic 13 — Tip 21 'Prototype to Learn' + Topic 37 'It's Playtime!' (+ Topic 4 'Be a Catalyst for Change')

Spike formal: en discovery, cada item de RISKS con incertidumbre alta dispara la pregunta '¿amerita un spike time-boxed antes de congelar la SPEC?'. El output legítimo del spike es un ADR con lecciones (hechos que alimentan la SPEC), JAMÁS código mergeable; gate-check bloquea que ramas spike/* (o label equivalente) lleguen a PR — la versión ejecutable, estilo INV-GOLDEN-01, de 'make it clear this code is disposable'. Resuelve además la tensión con Stone Soup sin romper spec-first.

*Dónde vive:* skill discovery (pregunta sobre RISKS) + engine (gate-check sobre ramas/labels spike) + doc ADR (tipo 'spike learnings')


## Tensiones (el libro contra spec-loop — con resolución propuesta)

1. **Preface 1ª ed. ('no hay best solution, solo sistemas apropiados a las circunstancias') + Topic 8 ('ETC es un VALOR que guía el juicio, no una regla mecánica')**
   Los caps del readiness KPI y los presupuestos del simplicity-check son números universales hardcodeados — para el libro, receta de gurú aplicada a ciegas. La resolución respeta el propio lema del kit: el conteo medido es HECHO, pero el umbral es OPINIÓN; los números del engine deben ser defaults advisory y solo bloquear cuando el humano los declaró en la SPEC (ahí son requerimiento, cf. Tip 8). El principio del fact-gate es universal; el número, no.

2. **Topic 12: Tracer Bullets — crítica a 'specify the system to death'**
   Spec-first congela el 'qué' antes del primer disparo; con requisitos vagos eso es disparar por cálculo muerto. Mitigación concreta: regla en el paso plan de dev-loop — la iteración 1 debe ser un tracer end-to-end que atraviese todas las capas y ejercite el criterio de aceptación núcleo; si el tracer refuta la SPEC, se vuelve a discovery ANTES de construir el resto. Feedback barato temprano es compatible con anti-inmediatez: ajustar puntería no es un atajo.

3. **Topic 14 (aside '¿Por qué los usuarios de negocio no leen las features Cucumber?') + Topic 45 (Documenting Requirements: 'los requisitos se APRENDEN, no se recolectan')**
   La SPEC aprobada en discovery puede ser el documento firmado-para-sacarte-de-la-oficina: las necesidades reales emergen jugando con código que corre. Mitigación triple: (1) checkpoint de demo con código corriendo ante el dueño de la SPEC en la primera iteración ejecutable, antes del gate de merge; (2) finding tipo 'SPEC-WRONG' en el ledger que baja readiness y reabre discovery en vez de empujar el código a cumplir criterios equivocados; (3) presupuesto de tamaño para SPECs en spec-check (espíritu index-card, simétrico al simplicity-check del código).

4. **Topic 11: Reversibility — Tip 18 'There Are No Final Decisions'**
   CONSTITUTION como 'invariantes inviolables' sin camino de enmienda fosiliza para siempre una mala decisión: si dependés fuertemente de un hecho, casi con garantía va a cambiar. Resolución: CONSTITUTION deliberadamente mínima + procedimiento de enmienda explícito (solo humano, con ADR que documente por qué cayó el invariante). El engine sigue bloqueando contra la versión vigente; lo que cambia es que el documento no es inmutable, es human-gated.

5. **Topic 15: Estimating — crítica a PERT ('la fórmula presta autoridad no ganada al número')**
   El humano puede leer 'readiness 82' como verdad porque salió de una fórmula con caps. Resolución: el reporte del KPI muestra SIEMPRE su descomposición (qué dimensiones están UNMEASURED, qué caps aplicaron), opcionalmente se expresa como banda en vez de punto, y se trackea calibración KPI-vs-resultado real post-merge para detectar si el número infla confianza.

6. **Topic 41 (Jeffries/Sudoku: 'seduced by the green tests passed message') + Topic 51 Tip 93 ('Test State Coverage, Not Code Coverage') + Topic 23 (sidebar DBC/TDD: los tests son evidencia muestral sesgada a happy path)**
   El engine trata tests verdes y coverage como HECHO fuerte, pero el libro demuestra que son evidencia muestral débil e invitan al Goodhart del agente — pulir la métrica sin acercarse a la solución es EL modo de falla típico de un LLM. Resolución: asimetría explícita en el KPI (coverage bajo capa hacia abajo; coverage alto NO suma evidencia positiva), readiness dominado por criterios de ACCEPTANCE cerrados, y dimensión complementaria de 'test strength' vía mutation smoke (Tip 92) y property tests derivados de invariantes de CONSTITUTION.

7. **Topic 23: Design by Contract — 'Dynamic Contracts and Agents' (los agentes autónomos pueden RECHAZAR y renegociar contratos)**
   El libro imagina agentes con autoridad para renegociar el contrato; spec-loop fija la autoridad contractual en el humano (gate de merge, .approved que el agente jamás escribe, escalación capa el KPI a 75). Resolución que preserva 'humano dirige': formalizar el canal — un 'SPEC change request' estructurado que el agente puede emitir al escalar (nunca editar SPEC/CONSTITUTION en silencio), con el humano como único firmante. Convierte la renegociación implícita del libro en un paso auditable del loop.

8. **Topic 25: Assertive Programming — sidebar 'Use Assertions in Production, Win Big Money'**
   El feedback de mayor valor llega DESPUÉS del ship (usuarios reales cazan lo que ningún test encontró), pero dev-loop se detiene en el merge por diseño y UNMEASURED solo rige en build-time: post-merge todo es silencio y spec-loop no lo cuenta. Decisión a tomar explícitamente: o documentar ese out-of-scope en la CONSTITUTION, o agregar el tipo de entrada 'production finding' al ledger que alimente el próximo ciclo de discovery.

9. **Chapter 7 intro: While You Are Coding ('tratar el código como transcripción mecánica del diseño es la mayor causa de fracaso')**
   'Humano dirige / IA ejecuta' + SPEC con criterios verificables puede degenerar en tratar el build como transcripción, cuando hay decisiones de juicio cada minuto. Resolución: finding tipo 'spec-doubt' que el builder levanta cuando la SPEC choca con la realidad del código — aconseja (guess) y capea readiness hasta que el humano lo revise, en vez de que el agente elija en silencio entre desviarse o transcribir mal.

10. **Topic 32: Configuration — sidebar 'Don't Overdo It' (2ª advertencia: no empujar decisiones debatibles a config; implementar UNA manera y validar con feedback real)**
   La entrevista de discovery/adr-refine empuja a resolver todo upfront, pero el libro dice que ciertas decisiones se resuelven mejor empíricamente (ship + feedback) que deliberando en frío. Resolución: el template de ADR admite status 'experimento' con criterio de feedback y fecha de revisión — la decisión queda registrada como hipótesis medible en vez de forzar al humano a decidir sin datos o degradar la duda a un flag configurable; dev-loop no bloquea si el ADR declara el experimento explícitamente.

11. **Topic 38: Programming by Coincidence — 'Accidents of Implementation' (apoyarse en comportamiento accidental es una bomba de tiempo)**
   characterize consagra TODO el comportamiento observado como contrato, incluidas las coincidencias (el kit ya tiene el caso real: el QR que replica un bug de prod). Es programar por coincidencia institucionalizada. Mitigación: al aprobar los .approved, el humano etiqueta cada comportamiento como 'intended' vs 'observed-accidental', para que una limpieza futura sepa qué es contrato y qué es accidente congelado — sin debilitar el byte-compare de hoy.

12. **Topic 48 ('There Can Never Be an Agile Process' + Tip 85 'la reflexión de proceso hay que AGENDARLA') + Topic 49 (Team Tracer Bullets: los gates-handoff son waste)**
   Un proceso codificado con gates y caps fijos que jamás experimenta consigo mismo es Agile-in-a-Box, y el libro condena los gates donde el trabajo se detiene esperando humanos y papeleo. Defensa parcial de spec-loop: sus gates son checks automáticos de hechos que corren en segundos dentro del loop, y el ÚNICO handoff humano (el merge) es deliberado y de alto valor. Lo que falta: retro post-merge AGENDADA que mida el propio kit desde el ledger (tasa de falsos positivos por gate, latencia por gate, caps que nunca disparan, iteraciones desperdiciadas por oscilación), con tuning de thresholds explícito y humano-aprobado — gate-check ya impide bajarlos en silencio, así que el canal legítimo de adaptación existe; falta el ritual que lo alimente.


## Estado

**M2 IMPLEMENTADA en kit 1.10.0** (acceptance-check trazable — ver
CHANGELOG-1.10.0). **M9 IMPLEMENTADA en kit 1.11.0** (tests fuera del
presupuesto de simplicity — ver CHANGELOG-1.11.0). **M8 IMPLEMENTADA en kit
1.12.0** (secret-scan en gate-check — ver CHANGELOG-1.12.0). El resto sigue
siendo backlog. Prioridad sugerida al retomarse: M3 (ledger atómico — todo el
edificio se apoya en ese archivo), M6 (plateau/stop-signal — advisory puro).
M5/M4/M10/M1 requieren decisión humana de diseño (caps advisory-por-default,
FSM del workflow, convención de ramas spike, schema de cierre de findings).
