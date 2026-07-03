# Referencia exhaustiva de las skills del método — dev-loop-kit 1.19.0

> Documento de lectura. La fuente de verdad son los seis `SKILL.md` de
> `dev-loop-kit/.claude/skills/` — este doc los describe, no los reemplaza ni los
> extiende. Si algo acá contradice un SKILL.md, gana el SKILL.md (y es un bug de
> este doc: regla truth-pass del repo).

---

## El mapa: cómo se encadenan

El método tiene **dos frentes de entrada** (según de dónde arrancás), **un motor de
construcción** y **dos satélites** (captura de comportamiento y reporte):

```
GREENFIELD  (solo tenés la idea)          BROWNFIELD  (el sistema ya existe)
┌──────────────┐                          ┌────────────────────┐
│  /discovery  │  la skill PROPONE        │ /reverse-discovery │  la skill EXTRAE
│              │  la forma; el humano     │                    │  HECHOS; el humano
│              │  aprueba                 │  (usa /characterize│  escribe la SPEC
└──────┬───────┘                          │   como sub-paso)   │  leyendo esos hechos
       │                                  └─────────┬──────────┘
       │  paquete de spec                           │  SYSTEM-MAP + golden aprobado
       ▼                                            ▼
┌──────────────┐   feature conocida:        el humano escribe la SPEC de migración
│ /adr-refine  │◄── entrevista de           y toma las decisiones FORWARD acá
│              │    precisión (sin
└──────┬───────┘    proponer forma)
       │  ADR set + ACCEPTANCE.md
       ▼
┌──────────────┐    gates de hecho, ledger, convergencia, readiness
│  /dev-loop   │──► PR gateado con `phase --require pr-ready` ──► merge = HUMANO
└──────┬───────┘
       │  QA-LEDGER.json (métricas reales)
       ▼
┌──────────────┐
│   /sys-doc   │  deck HTML de dos vistas (comercial + técnica), a pedido
└──────────────┘
```

La pieza transversal es el **engine** (`qa_ledger.py`, 21 subcomandos, Python stdlib):
las skills instruyen al agente, el engine mide y bloquea. El lema operativo:
*los gates que leen HECHOS bloquean; los que adivinan sobre prosa, avisan* — y el
detalle comando por comando vive en el playbook (`docs/spec-loop-playbook.html`).

---

## 1. discovery — de la idea pelada al paquete de spec

**Qué es.** El frente greenfield. El humano trae la idea, las restricciones y el
material de referencia; **la skill trae la forma**: interroga hasta que exista una
forma compartida del sistema y escribe los documentos sobre la marcha.

**Cuándo se invoca.** "discovery", "modelá esto desde una idea", "solo tengo la
idea, no sé el cómo todavía". Cuándo NO: si la feature ya tiene forma clara y solo
falta precisión, eso es `adr-refine`; si el sistema ya existe y hay que migrarlo,
eso es `reverse-discovery`.

**Principios no negociables (5):**
1. **Una pregunta por vez, cada una CON respuesta recomendada.** Es la inversión que
   hace funcionar el discovery: la skill propone (entidades, endpoints, arquitectura,
   una decisión default) y el humano confirma o corrige. Jamás una lista de 20
   preguntas; jamás pedirle al humano estructura que la skill puede proponer.
2. **Explorar antes de preguntar.** Si un doc de referencia, URL, PDF, el codebase o
   un `CONTEXT.md`/`docs/adr/` existente responde la pregunta, se lee primero. Al
   humano solo llega lo que genuinamente requiere su criterio.
3. **Proponer la forma.** Entidades núcleo, superficie de operaciones, 2–3 opciones
   de arquitectura con trade-offs. El árbol de diseño se camina rama por rama.
4. **Interrogar, no acordar.** Contradicciones, términos difusos o sobrecargados,
   modos de falla ausentes, restricciones no dichas. Un discovery donde la skill
   acordó con todo, falló.
5. **Archivos lazy e inline.** Un archivo se crea recién cuando hay algo real que
   escribir, y se actualiza en el momento en que una decisión cristaliza — nunca
   batch al final.

**Inputs.** La idea (obligatoria, puede venir mal formada) · material de referencia
(opcional: manuales, PDFs, URLs, API specs — se leen ANTES de proponer) · codebase
existente (opcional — se explora respetando `CONTEXT.md` y ADRs).

**La agenda de interrogatorio (10 pasos, en orden; se saltea lo que las referencias
ya responden):**
1. **Propósito / valor / por qué ahora** — qué trabajo elimina, qué cuesta no hacerlo.
2. **Modelo de dominio** — la skill propone las entidades núcleo y sus relaciones.
3. **Superficie de operaciones / API** — endpoints y contratos (idempotencia, códigos).
4. **Decisiones grandes (→ ADR)** — 2–3 opciones con trade-offs y default recomendado:
   persistencia, protocolo, idempotencia, sync/async, multi-tenancy.
5. **Comportamiento y casos sucios** — happy path y DESPUÉS fallas, reintentos,
   estados parciales, concurrencia, qué NO debe pasar jamás.
6. **Restricciones inviolables (→ `CONSTITUTION.md`)** — reglas de dominio, seguridad
   y operación que no se rompen (plata al centavo, numeración sin huecos, secretos
   jamás logueados). Un invariante por línea, con referencia CWE donde mapee.
   Alimentan el severity gate: una violación es BLOCKER, nunca un trade-off.
7. **Out of scope** — límites explícitos con referencias forward.
8. **Acceptance / Definition of Done** — criterios concretos y chequeables + métricas.
9. **Quality bar (→ config, 1.17.0)** — "¿qué nivel de calidad BASTA acá y qué
   dimensiones son negociables?". Lo que el humano declara va a
   `dev-loop.config.json`; un umbral declarado lee como **requerimiento (config)**
   en el output del engine, uno no declarado queda como default del kit (opinión)
   y así se etiqueta. Declarar es commitear el config.
10. **Riesgos residuales y dependencias** — y por cada riesgo de incertidumbre ALTA
    (1.19.0): "¿amerita un spike time-boxed antes de congelar la SPEC?". El spike
    corre en rama `spike/*` y su ÚNICO output legítimo es un ADR con lecciones —
    jamás código mergeable; `phase --require pr-ready` rechaza cualquier rama
    `spike/*`, estilo INV-GOLDEN-01.

**Artefactos que produce (lazy, a medida que cristaliza):**
- `CONTEXT.md` — glosario de dominio (solo términos con sentido para expertos del
  dominio, desacoplado de implementación).
- `CONSTITUTION.md` — invariantes que ningún ADR/SPEC puede violar; la capa ARRIBA
  de los ADRs.
- `DOMAIN-MODEL.md` — las entidades propuestas y aprobadas (el modelo, no el
  vocabulario).
- `SPEC.md` — objetivo/valor, riesgo, scope/out-of-scope, comportamiento,
  entradas/salidas/errores, acceptance, test plan, operación, rollback.
- `docs/adr/ADR-NNN-<slug>.md` — una por decisión durable, con **Implementation
  Plan** (paths afectados, patrones, tests) y **Verification** (checkboxes que un
  agente puede chequear): el ADR como spec ejecutable.
- `ACCEPTANCE.md` — la DoD como checkboxes con **ID estable trazable**
  (`- [ ] AC-01 — cuando X entonces Y`, secuenciales, nunca reusados). Aguas abajo
  un criterio solo cierra MEDIDO cuando un testcase verde lleva su tag en el nombre.
- `RISKS.md` — riesgos residuales, supuestos, puntos que requieren aprobación humana.
- `HANDOFF.md` — qué leer antes de codear + reglas duras de "no hacer" + evidencia
  exigida.

**Regla de sobriedad para ADRs** — se escribe uno solo si se cumplen LAS TRES:
difícil de revertir · sorprendente sin contexto · trade-off real. Lo demás es ruido
que entierra los importantes.

**Convergencia.** Termina cuando existe forma compartida: entidades, operaciones y
decisiones grandes tomadas (o registradas como supuestos explícitos), cada modo de
falla con comportamiento definido, out-of-scope explícito, DoD chequeable. La skill
lo declara, finaliza el paquete y entrega el handoff (un prompt que instruye al
implementador a resumir el comportamiento, marcar ambigüedades y proponer plan de
archivos+tests ANTES de tocar código — y a no editar la SPEC para que su
implementación parezca correcta).

---

## 2. adr-refine — entrevistar, después destilar

**Qué es.** La misma entrevista de discovery aplicada a una feature CONOCIDA: la
forma ya está clara, falta precisión. **No es un generador: es un interrogador que
destila.** El valor está en las preguntas, no en acordar.

**Cuándo se invoca.** "refine the ADR", "let's spec this before coding", "ayudame a
definir esto antes de desarrollar". Es la contraparte front-half de dev-loop.

**Principios no negociables (5):**
1. **Interrogar, no validar** — el trabajo es superficializar lo implícito y
   encontrar los agujeros.
2. **Converger, no quedarse sin preguntas** — la entrevista termina por criterio
   OBJETIVO (abajo), no cuando el humano parece cansado. Es la misma disciplina del
   "converge, don't chase zero" de dev-loop, aplicada al frente.
3. **Cero artefactos antes de converger** — si piden "escribilo ya", primero se
   nombran los gaps abiertos.
4. **Un tema por vez** — se camina la agenda por lotes enfocados, reflejando lo
   escuchado ("Decidido: … / Sigue abierto: …") antes de avanzar.
5. **Los "decidilo vos" se registran como supuestos explícitos** — ante una
   deferencia en decisión consecuente, se devuelve el trade-off UNA vez; si el
   humano insiste, queda como supuesto explícito en el ADR, jamás default
   silencioso.

**Fase A — la entrevista (agenda de 7):** problema y por qué ahora · decisiones
implícitas (sync/async, storage, protocolo, idempotencia, límites transaccionales,
quién es dueño del estado — cada una con alternativa considerada) · comportamiento
(happy path y luego los casos SUCIOS: timeouts, reintentos, 4xx vs 5xx,
concurrencia, estados parciales) · restricciones inviolables (→ `CONSTITUTION.md`;
**un ADR jamás puede contradecir la CONSTITUTION** — si una decisión lo haría, se
escala, no se registra) · out of scope · DoD + métricas de éxito · dependencias.

**Convergencia — TODAS deben cumplirse:** cada decisión con fundamento y al menos
una alternativa considerada · cada modo de falla nombrado con comportamiento
definido · out-of-scope explícito · DoD con cada ítem chequeable · ningún OPEN GAP
sin resolver (resuelto = decidido O registrado como supuesto explícito).

**Fase B — destilar (solo tras converger):**
- Un ADR por decisión que valga registrarse, en formato fijo: Estado · Contexto
  (con opciones A/B/C) · Decisión · Razones · Consecuencias (+ y −) ·
  Implementation Plan · Verification (checkboxes). Numeración continúa desde el ADR
  más alto existente. **Las decisiones negativas cuentan**: "lo que NO vamos a usar
  y por qué" es un ADR válido.
- `ACCEPTANCE.md` en el root (o el path del config): Definición de hecho ·
  Cómo medimos éxito · Out of scope · Decisiones registradas.
- Si surgió un invariante nuevo en el paso 4, se agrega a `CONSTITUTION.md` — nunca
  dejarlo en un ADR donde después pueda "negociarse".

**Anti-patrones explícitos:** generar un ADR desde un pedido de una línea sin
entrevistar · aceptar "hacelo como quieras" sin registrar el supuesto · escribir un
criterio de acceptance no chequeable ("que funcione bien") · emitir artefactos antes
de las condiciones de convergencia.

**Relación con discovery.** Ambas emiten el mismo paquete; se elige por punto de
partida: discovery PROPONE la forma (solo hay una idea), adr-refine PRECISA una
forma que ya se conoce.

---

## 3. dev-loop — el orquestador de construcción + QA

**Qué es.** El motor del método: un ciclo disciplinado de desarrollo + QA sobre uno
o más repos, con cada paso registrado en un ledger determinístico
(`QA-LEDGER.json`) y freno duro en el merge gate humano. **Todas las métricas salen
del ledger — jamás estimar de memoria.** El ledger tiene dos niveles: registros
**medidos** (snapshots, ingest-gate, log-gate — parseados de artefactos reales;
pueden bloquear) y conteos **auto-reportados** del agente (log-step — narración
para la retrospectiva; un rojo medido siempre pisa un verde narrado).

**Para quién es / cuándo NO.** Un operador llevando UN cambio no trivial o con
riesgo. **NO para trabajo trivial o descartable** — un fix de un archivo corre
build+test y se saltea discovery/ADR/sys-doc (tabla de perfiles de riesgo del
playbook).

**Principios no negociables (6):**
1. **Convergé, no persigas el cero.** Solo bloquean findings en o sobre el severity
   gate (default BLOCKER/CRITICAL/HIGH); el resto va a `ISSUES-DEFERRED.md`, nunca
   al loop. Pulir Medium/Low para siempre es el modo de falla que esta skill existe
   para prevenir.
2. **Los tests son guardarraíl, no final.** El test command del repo corre después
   de CADA pase que cambió código; suite roja frena el loop.
3. **Generar tests no es correr tests.** `/improve test` (escribir cobertura) corre
   UNA vez al final contra código estabilizado — jamás dentro del loop.
4. **Freno en el merge.** La skill crea el PR y confirma CI verde; NO mergea. El
   merge es del humano.
5. **Protocolo de markdown trackeado.** Antes de modificar un `.md` trackeado se
   pide la versión actual — esos archivos llevan progreso real.
6. **El golden es el único artefacto que no podés authorear.** Para migraciones,
   los `.approved` son verdad de campo aprobada por un HUMANO; la skill emite
   `.received` y frena (hook PreToolUse lo hace mecánicamente imposible —
   INV-GOLDEN-01).

**Las fases, en orden:**

- **Setup** — `init --config dev-loop.config.json`; el config lista cada repo y su
  type (maven|flutter|python|node|go|rust|dotnet|cpp|gradle|swift). Para perfil E
  (migración) se instala además el hook del golden y `.gitattributes`.
- **Fase 0 — Plan (ADR-first).** Se lee `CONSTITUTION.md` PRIMERO. El input es el
  ADR set + `ACCEPTANCE.md` (típicamente de adr-refine). Sin criterios de
  acceptance → frenar y correr adr-refine. El loop apunta al plan, no a "cero
  issues".
- **Fase 1 — Coverage gate → caracterización condicional.** `snapshot --phase pre`
  + `check-coverage`. Cobertura ≥ umbral → la suite existente es el guardarraíl.
  Por debajo → escribir tests de caracterización/contrato EN EL BORDE (API pública,
  no internals), revisados por el humano antes de confiar en ellos. Migración →
  capturar el golden ANTES de tocar nada (skill characterize); sin golden aprobado
  no hay build de migración.
- **Fase 2 — Build.** Implementar según el plan, commits convencionales por paso
  lógico. Disciplina ADR: consultar el ADR antes de tocar área gobernada; triggers
  proactivos (dependencia nueva, patrón nuevo, alternativas reales, contradecir un
  ADR aceptado → proponer ADR al humano); linkear código↔ADR con un comentario;
  **jamás editar la SPEC/ADR para que la implementación parezca correcta**.
- **Fase 2b — Simplicity gate ("Reduce").** `simplicity-check` sobre el diff:
  minimalidad, anidación, abstracciones nuevas (proxies honestos, no CC por AST).
  OVERBUILT (exit 1) es BLOCKER: recortar y re-correr. **Los tests quedan FUERA del
  presupuesto** (1.11.0). El veredicto se persiste con `log-gate --kind simplicity`.
- **Fase 3 — QA loop (por repo).** Las tools de `qa_tools_order` (default
  code-review → judgment-day → improve); un pase de todas = un ciclo. Tras CADA
  pase: aplicar solo fixes ≥ gate, correr tests, loguear con `log-step`
  (narración). En cada pase que cambió código: `gate-check` (¿debilitó el aparato?
  ¿agregó un secreto? — 1.12.0) y, en migración, `golden-diff`; ambos se persisten
  con `log-gate`. **Find Bugs Once (1.16.0)**: si un pase logueó `--fixed > 0`,
  correr `regression-check` — cierre sin línea nueva de test = NARRATED (el test
  que falla va ANTES del fix). El static gate NO se cuenta a mano: `ingest-gate`
  parsea los reportes de los linters, normaliza severidades y computa el `fixed`
  real diffeando finding-IDs. Cierre de ciclo: `converged` (exige TODAS las tools
  limpias + linters limpios + fact gates persistidos limpios; un snapshot rojo veta
  el verde narrado) y `oscillation` (¿el mismo set de findings vuelve?).
- **Fase 4 — Integración (multi-repo).** Con cada repo convergido, la capa
  cross-repo: contratos entre repos como findings gateados, logueado bajo
  `--repo integration`. Verde por-repo no implica costuras verdes.
- **Fase 5 — Verify.** Recién ahora `/improve test` escribe la cobertura fina;
  suite completa verde y cobertura ≥ umbral; `snapshot --phase post`.
- **Fase 5b — Rebuild test (opcional; perfil C+/E o periódico).** ¿El paquete de
  spec alcanza para regenerar el sistema? `rebuild --mode baseline` → regenerar
  producción desde SPEC/ADR/ACCEPTANCE preservando los tests → `--mode compare`.
  La señal dominante es la suite preservada: un test que pasaba y falla en el
  regenerado = comportamiento que la SPEC dejó implícito. La divergencia es un gap
  de spec, no un bug de código.
- **Fase 6 — PR.** `phase --require pr-ready` POR REPO antes de abrir el PR: el
  estado se COMPUTA del ledger, jamás se declara; exit 1 lista los hechos que
  faltan. Rama `spike/*` jamás pasa (1.19.0). Después: historial limpio, PR, CI
  verde, **STOP** — el humano mergea.
- **Fase 7 — Smoke list.** Checklist de smoke manual concreto (rutas reales,
  endpoints, flujos de device) para que el humano verifique.
- **Fase 8 — Docs + retrospectiva.** `summary` (humano y `--json` para sys-doc) y
  el **readiness KPI** — se muestra tras CUALQUIER tarea: acceptance MEDIDA 30 /
  static 20 / adr 15 / coverage 15 / convergencia 10 / integración 10, caps duros
  (tests rojos ≤35, BLOCKER/CRITICAL ≤65, escalación ≤75) con procedencia
  etiquetada (1.17.0), trazabilidad AC-n (1.10.0) y los dos advisories (1.14.0):
  stall → volver a ADR; stop-signal → candidato a PR.

**Contrato de escalación — FRENAR y preguntar al humano cuando:** se llegó al cap
de iteraciones sin converger · hay oscilación · un test que pasaba falla y el fix
no es trivial · dos tools se contradicen · un fix requiere decisión ADR · un cambio
violaría la CONSTITUTION (jamás se negocia; cambiarla es decisión humana separada).
Cada escalación se registra (`escalate`) y su CIERRE también
(`resolve-escalation`); una violación de CONSTITUTION se flaggea además como
blocker de primera clase (`flag-blocker --kind constitution`), y resolverla exige
`--escape-analysis` (1.16.0): qué gate/test debió atraparla y qué se hizo.

---

## 4. characterize — congelar el comportamiento actual como verdad de campo

**Qué es.** Captura la suite golden/approval del comportamiento ACTUAL de un
módulo — **el único artefacto del loop que el agente no puede authorear, y esa es
exactamente su razón de existir**. Si el agente escribiera el golden razonando
sobre lo que el código "debería" devolver, codificaría la misma lectura parcial
que pierde lógica en silencio. Se captura lo que el código HACE, mecánicamente,
ejecutándolo.

**Cuándo se invoca.** "characterize", "golden-capture", "capturá el comportamiento
viejo" — antes de cualquier migración/modernización. dev-loop la dispara en Fase 1
para perfil E; reverse-discovery la orquesta como su Fase 2.

**La división de autoría:** el agente PUEDE escribir el harness de captura; NO
puede crear, renombrar ni editar ningún `.approved`.

**Protocolo (4 fases):**
1. **Harness de captura** (lo escribe el agente): determinístico, corre el módulo
   ORIGINAL sobre el corpus y serializa TODO output observable. Mismo input →
   mismo `.received`, byte a byte.
2. **Checklist de no-determinismo** (se emite aplicado, ítem por ítem):
   timestamps/fechas congelados · random/seeds fijos · orden de iteración de
   maps/sets ordenado · GUIDs/auto-increment normalizados · concurrencia sin
   filtrar orden de threads · **locale objetivo explícito y obligatorio** (separador
   decimal, formato de fecha — un golden armado en una máquina y corrido en otra
   con locale distinto rompe entero; Windows/SQL Server: riesgo alto) ·
   serialización determinística (claves ordenadas, precisión de float fija,
   encoding explícito).
3. **Correr la captura** → `.received`. **Declarar volátiles ANTES de aprobar
   (1.15.0):** lo que varía entre corridas correctas y no se puede volver
   determinístico en la fuente (timestamps, request ids) se declara en
   `golden.scrub.json`; `golden-diff` enmascara AMBOS lados antes de comparar
   (solo texto, binario sigue byte a byte) y reporta cada match vía scrub APARTE —
   el masking jamás es invisible. El scrub es para lo que genuinamente no se
   controla; primero se arregla el determinismo en la fuente. gate-check flaggea
   cualquier edición posterior del archivo de reglas.
4. **STOP para aprobación humana.** La skill devuelve el control para que el
   humano revise y apruebe los `.approved` — y `golden.scrub.json` si existe (las
   reglas de scrub son contrato, igual que los goldens). **La skill termina acá.**

**El corpus (crítico — el golden solo protege los paths que ejercitás):** en orden
de valor: muestras reales de producción (anonimizadas si hace falta — la
distribución verdadera, con casos que nadie sabía que existían) → edge cases a
mano (ceros, límites, estados de error) → inputs de bugs históricos (cada bug
pasado es un input del golden). Módulo cuyo corpus no ejercita sus ramas conocidas
= **PARTIAL**, jamás "cubierto".

**Guardrails:** hook `PreToolUse` sobre `**/*.approved.*` hace la escritura
mecánicamente imposible · `.gitattributes` con `*.approved.* binary` (los line
endings no pueden crear diffs falsos) · jamás sobreescribir un golden aprobado —
si existe un `.approved`, es del humano: se deja intacto y se muestra el diff.

**Stack de harness:** Java → ApprovalTests.Java (JUnit 5); C++/otros → dir de
fixtures + serializador determinístico + runner custom.

**Relación:** el `.approved` capturado es el árbitro que `golden-diff` compara
byte a byte durante dev-loop.

---

## 5. reverse-discovery — extraer los hechos de un sistema existente

**Qué es.** El frente brownfield, el inverso de discovery: el sistema ya corre y
su comportamiento observable ES la verdad. **No se inventa nada — se caracteriza
lo que ya está, como hechos.**

**Cuándo se invoca.** "reverse-discovery", "migrar/modernizar este sistema",
"caracterizar el sistema viejo antes de tocarlo".

**El único no-negociable: producir SOLO hechos.** Un mapa del sistema (de análisis
estático) y una suite golden (byte-capturada) son HECHOS — verificables, no
opiniones. **NO se authorea una SPEC de "qué hace" ni ADRs de "por qué está
construido así"**: eso es inferencia, y si el agente la escribe codifica su propia
(mala) lectura del código — el punto ciego exacto que el golden existe para
contrarrestar. La skill emite hechos; el humano infiere el significado. Si el
agente se descubre escribiendo un requerimiento o un rationale: frenar — eso es
del humano (y de adr-refine para las decisiones FORWARD).

**Protocolo (3 fases):**
1. **Map (hecho).** Solo análisis estático → `SYSTEM-MAP.md`: cada
   endpoint/operación/topic público con su contrato (schemas, status codes,
   idempotencia donde sea observable) · grafo de dependencias (quién llama a quién,
   DB, APIs externas — ciclos y hubs flaggeados) · candidatos a módulo (observación
   del layout ACTUAL y sus costuras naturales, NO propuesta del nuevo). Todo
   trazable a código: nada de "esto parece que…".
2. **Characterize (hecho).** El golden en los bordes del sistema, delegando en la
   skill `characterize` (o siguiendo su contrato inline si no está instalada):
   harness determinístico, checklist de no-determinismo, `.received`, STOP para
   aprobación humana. Corpus insuficiente = PARTIAL.
3. **Summary (hechos, sin opinión).** `DISCOVERY-SUMMARY.md`: el mapa + el reporte
   de cobertura del golden (qué bordes están capturados y aprobados, cuáles PARTIAL
   y por qué). Es la base de hechos que el humano lee para escribir la SPEC de
   migración. Sin editorializar.

**Lo que NO hace (trabajo del humano):** escribir la SPEC del comportamiento viejo
(el golden ES la spec ejecutable) · escribir ADRs de las decisiones implícitas del
sistema viejo · decidir la estructura NUEVA (límites de módulos, shared kernel,
sync vs eventos — decisiones forward → adr-refine).

**Por qué es segura por construcción.** Vive entera del lado HECHOS de la línea
hechos-vs-prosa: análisis estático y byte-capture, ambos verificables. Si un paso
requiriera adivinar, salió del scope de la skill.

**Flow de migración completo:** reverse-discovery (hechos) → el humano escribe la
SPEC + adr-refine (decisiones de partición forward) → dev-loop (reestructura con
golden-diff verde todo el camino) → readiness + gate humano.

---

## 6. sys-doc — el deck de sistema en dos vistas

**Qué es.** Genera UN archivo `.html` autocontenido y navegable (estilo
PowerPoint: teclado + click) que documenta un sistema en dos pistas conmutables en
cualquier momento: **comercial/CEO** (qué hace, valor, postura de riesgo, estado —
sin código, lenguaje de negocio, framing plata/tiempo/confiabilidad) y **técnica**
(arquitectura, módulos, flujo de datos, contratos, resultados de QA, cobertura,
deferred).

**Cuándo se invoca.** "document this system", "make the system deck",
"commercial + tech doc". Se invoca A PEDIDO desde dev-loop Fase 8 (es reporte, no
parte del build verificado).

**Inputs (y la regla de oro):**
1. **Métricas — autoritativas del ledger**: `summary --json` y `readiness --json`;
   los números se usan VERBATIM — jamás inventar cifras. Del summary:
   `total_steps`, `by_tool`, `by_repo`, `aggregate`, `escalations`. Del readiness:
   `score`, `status`, `cap_reason`, `dimensions`, `acceptance`, `by_repo`. El
   readiness se renderiza como semáforo (verde ≥80, ámbar 50–79, rojo <50) y
   SIEMPRE se imprime el `cap_reason` cuando hay cap activo.
2. **Entendimiento del sistema**: ADR/PLAN, CLAUDE.md, layout de módulos,
   contratos clave. Sin ledger → preguntar si proceder sin sección de QA.

**Estructura (10 slides):** título · switcher de pista (default Comercial) ·
[comercial] qué hace · valor y estado · calidad de un vistazo (sin jerga) ·
[técnica] arquitectura (SVG inline: repos como cajas, flujo como flechas,
externos distintos) · contratos/seams entre repos · resultados QA (tabla por tool:
reported/fixed/%fixed/deferred/suppressed, cobertura por repo, tests/kLOC,
escalaciones) · deferred issues (resumen HONESTO de `ISSUES-DEFERRED.md`) ·
checklist de smoke.

**Restricciones de build:** un solo `.html` con todo inline (funciona abierto
desde disco, deployable tal cual) · **sin localStorage/sessionStorage** (estado de
navegación en variables JS) · navegación con flechas, prev/next, índice de dots,
Esc = grilla overview · diagramas SVG a mano con `currentColor`/variables CSS (ni
raster ni libs externas) · estética dark control-room con la pista comercial
limpia · accesible (headings semánticos, aria-labels, contraste AA, imprimible).

**Output.** `docs/system-deck.html` (o el path que dé el humano); se presenta el
path y las 2–3 cosas que mirar primero — el HTML no se pega en el chat.

---

## Transversales a todas las skills

- **Protocolo de markdown trackeado** (las 6 lo llevan): antes de sobreescribir un
  `.md` trackeado que ya existe, se pide la versión actual — jamás reemplazar
  progreso real en silencio.
- **INV-GOLDEN-01** (characterize, reverse-discovery, dev-loop): el agente jamás
  escribe/renombra/edita un `.approved`; un hook PreToolUse lo vuelve
  mecánicamente imposible. Vale incluso en tests: el path CLEAN de golden-diff no
  se auto-testea porque crear un fixture aprobado es un acto humano.
- **CONSTITUTION.md como capa suprema** (discovery, adr-refine, dev-loop): los
  invariantes están ARRIBA de los ADRs; una violación es BLOCKER y se escala,
  jamás se negocia; enmendar la CONSTITUTION es una decisión humana explícita.
- **Hechos vs prosa** (todas, vía engine): los gates que leen hechos bloquean
  (golden-diff, gate-check, simplicity, spec-check estructural, phase); los que
  adivinan sobre prosa avisan (spec-check prosa, regression-check, advisories del
  readiness) — `--strict` permite gatearlos cuando el equipo lo decide.
- **El humano en tres puntos fijos**: aprueba la forma (discovery/adr-refine),
  aprueba el golden (characterize), y mergea (dev-loop). El agente propone, mide y
  frena; el humano decide.

> La herramienta ejecuta · el método gobierna · la evidencia decide · el humano aprueba.
