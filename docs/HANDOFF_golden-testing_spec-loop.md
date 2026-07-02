# HANDOFF — Integración de Golden Testing en spec-loop / dev-loop-kit

> **Para:** Claude Code (sesión sobre el kit spec-loop / dev-loop-kit)
> **De:** AM
> **Tipo:** SPEC de integración — implementás vos siguiendo el contrato de abajo.
> **Status:** propuesta a implementar. No toques nada fuera del scope de la sección 5 sin confirmar.

---

## 0. TL;DR

Se detectó un failure mode en una migración de stack: se perdió lógica de negocio de forma **silenciosa** (compila, happy paths OK, pero ramas poco frecuentes cambiaron de comportamiento). La causa raíz identificada en retrospectiva: **no había golden tests sobre el código original** antes de migrar.

Este handoff integra **golden testing (approval testing)** como pieza de primera clase del spec-loop, con un principio no-negociable: **el golden lo captura un script ejecutando el código original con inputs reales; el agente NUNCA genera ni edita los archivos `.approved`.**

---

## 1. Por qué esto y por qué así (leé antes de tocar código)

El insight central, que condiciona todo el diseño:

> En el spec-loop, casi todos los artefactos los authorea el agente (discovery, ADRs, spec, código, unit tests). **El golden suite es la ÚNICA pieza que el agente no puede authorear, y esa es exactamente su razón de existir.**

Si el agente escribe los golden tests, va a codificar el **mismo entendimiento parcial** que causó la pérdida de lógica. El diff daría verde contra su propia interpretación equivocada → el golden se vuelve un espejo del blind spot en vez de un check contra él.

**Regla dura:** el golden se captura ejecutando el código *original* con inputs reales, mecánicamente, por un script — nunca razonando sobre lo que el código "debería" devolver. El agente puede escribir el **harness de captura**; lo que no puede es generar o tocar los `.approved`. Esos archivos son **verdad de campo**.

> Nota de estilo de repo: esto es análogo a los `.md` de WorkLog que no se regeneran desde cero. Los `.approved` tienen el mismo status: si el agente los reescribe, se borra la única referencia no contaminada.

---

## 2. Glosario para no confundir términos

- **Golden test / golden master / approval test / characterization test**: mismo concepto. Testea lo que el código **hace hoy**, no lo que **debería** hacer. Captura output observable → lo congela como referencia (`.approved`) → diff en corridas futuras.
- **Captura (characterize)**: correr el código original con corpus real y serializar todo el output observable de forma determinística.
- **Corpus**: el conjunto de inputs. El golden vale exactamente lo que vale el corpus (ver §6).
- **`.approved`**: la foto congelada y aprobada por humano. Sagrada.
- **`.received`**: output de la corrida actual, que se diffea contra `.approved`.

---

## 3. Objetivo del cambio

Integrar golden testing en el kit de forma que:

1. Ningún módulo entre en fase de migración/modernización sin golden suite capturado y commiteado sobre su comportamiento pre-cambio.
2. El golden diff sea un **gate objetivo** dentro de `/qa`, auditado en `qa_ledger.py`.
3. Las bands `COVERS/PARTIAL/DIVERGE` dejen de depender de juicio del agente en la parte crítica y usen el golden como árbitro.
4. El agente quede **mecánicamente impedido** de tocar `.approved`.

---

## 4. Principio operativo (invariante conceptual)

```
El spec-loop es agente-driven SALVO un punto de anclaje externo que el agente no controla.
Ese ancla es el golden suite.
Es un check SOBRE el agente, no un check que el agente se autootorga.
```

Todo lo de la §5 deriva de esto. Si alguna decisión de implementación entra en conflicto con este principio, gana el principio y me preguntás.

---

## 5. Scope — qué construir

> ⚠️ Antes de editar `CONSTITUTION.md`, `/qa`, o cualquier `SKILL.md` existente: **leé la versión actual del archivo en el repo y mostrámela.** Las sesiones previas pueden haber modificado esos archivos (invariantes, checkboxes, notas) y no quiero que regeneres desde cero y pises progreso.

### 5.1 — Skill nueva: `characterize` (alias `golden-capture`)

Hermana de `discovery`. Instalada en `~/.claude/skills/` (instalación global, mismo patrón que el resto del kit).

**Contrato de la skill:**

| Entrada | Módulo objetivo + fuente de corpus (path a fixtures de input o referencia a datos de prod anonimizados). |
|---|---|
| Paso 1 | Genera el **harness de captura** para el módulo (el agente SÍ escribe esto). |
| Paso 2 | Emite la **lista de fuentes de no-determinismo a normalizar** para ese módulo (ver §7). Locale `es-AR` es obligatorio en el checklist. |
| Paso 3 | Corre la captura → genera `.received`. |
| Paso 4 | **STOP explícito.** Devuelve control a AM para revisión y aprobación manual de los `.approved`. La skill NO auto-completa la aprobación. |

**Acceptance criteria:**
- La skill termina en el paso 4 sin haber creado ni renombrado ningún `.approved`.
- El harness generado es determinístico (misma entrada → mismo `.received` byte a byte).
- El output de la skill incluye el checklist de no-determinismo aplicado.

### 5.2 — Invariante en `CONSTITUTION.md`

Agregar un invariante nuevo (respetá el formato CWE-mapped existente):

> **INV-GOLDEN-01** — Ningún módulo entra en fase de migración/modernización sin un golden suite capturado y commiteado sobre su comportamiento pre-cambio. El agente no genera ni edita archivos `.approved`.
> **CWE-440** (Expected Behavior Violation).

**Acceptance criteria:**
- El invariante queda referenciado desde el gate de `/qa` (§5.4) y desde el outer-loop (§5.6).
- No duplicar si ya existe algo equivalente — en ese caso, reconciliá y avisame.

### 5.3 — Fase 0 en el loop: `Characterize` (previa a `discovery` en migraciones)

Para cualquier `/goal` de tipo migración/modernización, se antepone una fase de caracterización sobre el sistema **viejo**.

- **Salida:** dir de fixtures `.approved` commiteado.
- **Es precondición, no opcional.** La spec de la migración se escribe *contra* ese golden.
- En `discovery`/`adr-refine`, el golden suite pasa a ser artefacto de spec ejecutable de primera clase. La sección de "contrato preservado" del ADR apunta al golden, no a prosa.

**Acceptance criteria:**
- Un `/goal` de migración no puede avanzar a `dev-loop` si no existe el golden suite del módulo.

### 5.4 — Eslabón en el orchestrator `/qa`

Insertar `golden-diff` en la cadena, **antes** de `judgment-day`:

```
deterministic-gate → golden-diff → judgment-day → code-review → improve
```

- `golden-diff` sucio (cualquier `.received` que no matchee su `.approved` sin aprobación) = **rojo duro**, corta la cadena.
- Pasar el resultado a `qa_ledger.py` como entrada auditada: `{ gate: "golden-diff", status: pass|fail, diverged_fixtures: [...] }`, mismo tratamiento que checkstyle/PMD/SpotBugs/FindSecBugs.

**Acceptance criteria:**
- Corrida de `/qa` con un fixture divergente → cadena cortada en `golden-diff`, entrada registrada en el ledger.
- Corrida con golden verde → pasa a `judgment-day`.

### 5.5 — Reconexión de las bands `COVERS / PARTIAL / DIVERGE`

El golden se vuelve el árbitro objetivo donde antes había juicio del agente:

- **DIVERGE** = hay fixtures con diff no aprobado. Deja de ser opinión.
- **PARTIAL** = corpus insuficiente para afirmar cobertura de esa rama (el golden pasa pero el corpus no ejercita el camino).
- **COVERS** = golden verde **y** corpus que ejercita esa rama.

**Acceptance criteria:**
- El clasificador de bands consulta el resultado de `golden-diff` y la cobertura del corpus antes de emitir COVERS.

### 5.6 — Condición del outer-loop

En el test de 4 condiciones para cerrar `/loop`, agregar (o reforzar la de QA-ledger gate):

> **Golden diff limpio sobre el módulo tocado** como condición dura de cierre.

---

## 6. Corpus — de dónde salen los inputs (crítico)

El golden solo protege los caminos que ejercitaste. Lo que se perdió fue probablemente un camino poco frecuente. Fuentes, en orden de valor:

1. **Muestras de producción reales** (anonimizadas si hace falta) — capturan la distribución verdadera, incluidos casos que ni sabíamos que existían.
2. **Edge cases construidos a mano** — límites conocidos: montos en cero, promociones combinadas, contingencia CAEA, tickets con impuestos internos dentro de la base de IVA.
3. **Casos que ya rompieron antes** — cada bug histórico es un input de oro.

**Acceptance criteria:** la skill `characterize` debe pedir/documentar la fuente de corpus y marcar como PARTIAL cualquier módulo cuyo corpus no cubra sus ramas conocidas.

---

## 7. Determinismo — checklist obligatorio del harness

El harness debe controlar/normalizar TODO esto antes de serializar, o el diff miente:

- [ ] **Timestamps / fechas** — reloj congelado o placeholder estable.
- [ ] **Random / seeds** — seed fijo o generador mockeado.
- [ ] **Orden de iteración** de maps y sets — claves ordenadas antes de serializar.
- [ ] **GUIDs / auto-increment de DB** — normalizados o excluidos del snapshot.
- [ ] **Concurrencia** — el orden entre threads no se filtra al output.
- [ ] **Locale `es-AR`** — separador decimal, formato de fecha, cultura. **Obligatorio y explícito.** Un golden armado en una máquina y corrido en otra con locale distinto se rompe entero. (Contexto Windows/SQL Server: alto riesgo.)
- [ ] **Serialización determinística** — JSON con claves ordenadas, floats con precisión fija, encoding explícito. La foto sale idéntica byte a byte cuando el comportamiento es idéntico.

---

## 8. Guardrails — no negociables

### 8.1 — Los `.approved` son sagrados

- La skill `characterize` **para** en el punto de aprobación (§5.1 paso 4).
- Agregar un hook **`PreToolUse`** que **bloquee** cualquier escritura del agente sobre `**/*.approved.*`.
- Motivo: en la primera corrida donde el diff falle, el agente va a intentar "arreglar" el test editando el golden — que es exactamente el bug que no queremos. El hook lo hace mecánicamente imposible.

**Acceptance criteria:** intento del agente de escribir/renombrar un `.approved` → bloqueado por el hook, con mensaje claro de por qué.

### 8.2 — `.gitattributes`

Agregar:

```
*.approved.* binary
```

Motivo: en Windows/SQL Server los line endings rompen los goldens y generás falsos positivos hasta que abandonás el suite. Esto lo evita.

**Acceptance criteria:** los `.approved` no cambian de hash por cambios de line ending entre máquinas.

---

## 9. Stack del harness — DECISIÓN PENDIENTE de AM

Antes de generar el capturador y el runner, confirmame el target:

- [ ] **Java** → usar **ApprovalTests.Java** (`com.approvaltests:approvaltests`, Maven Central; compatible JUnit 5 / JDK 21). Aprovechar `JsonApprovals.verifyAsJson()` para tickets/respuestas fiscales, y helpers tipo `WithTimeZone` para congelar tiempo/locale. Patrón "old query + new query contra prod" disponible para migraciones read-only.
- [ ] **C++** → harness propio para BatchDaemon (dir de fixtures + runner de diff + serializador determinístico; no hay ApprovalTests nativo cómodo, va custom).
- [ ] **Ambos.**

> Recordatorio: en `characterize`, para el I/O de sistema muchas veces conviene un dir de fixtures + runner propio que normalice y diffee, incluso en Java, en vez de depender solo de la librería.

---

## 10. Secuencia de trabajo sugerida

1. Leer versión actual de `CONSTITUTION.md`, `/qa` y skills existentes → mostrarme.
2. Confirmar §9 (stack del harness).
3. Implementar guardrails primero (§8: hook + `.gitattributes`) — barato y protege todo lo demás.
4. Skill `characterize` (§5.1).
5. Invariante `INV-GOLDEN-01` (§5.2).
6. Fase 0 en el loop (§5.3).
7. Eslabón `golden-diff` en `/qa` + entrada en `qa_ledger.py` (§5.4).
8. Reconexión de bands (§5.5) y condición de outer-loop (§5.6).
9. Validar con un módulo real (candidato: el módulo donde se perdió lógica en la migración).

---

## 11. Definition of Done

- [ ] Skill `characterize` instalada, para en aprobación, no crea `.approved`.
- [ ] Hook `PreToolUse` bloquea escrituras del agente a `**/*.approved.*` (demostrado con un intento fallido).
- [ ] `.gitattributes` con `*.approved.* binary`.
- [ ] `INV-GOLDEN-01` en `CONSTITUTION.md`, mapeado a CWE-440, referenciado desde `/qa` y outer-loop.
- [ ] `golden-diff` en la cadena de `/qa`, corta en rojo, registra en `qa_ledger.py`.
- [ ] Bands consultan golden + cobertura antes de emitir COVERS.
- [ ] Un `/goal` de migración no avanza a `dev-loop` sin golden suite.
- [ ] Validado end-to-end sobre un módulo real: captura → aprobación humana → migración → diff → gate.

---

## 12. Fuera de scope (no hacer sin nuevo handoff)

- Reescribir skills existentes (`discovery`, `adr-refine`, `dev-loop`) más allá de los puntos de enganche descritos.
- Tocar `qa_ledger.py` más allá de agregar la entrada de `golden-diff`.
- Generar corpus sintético "prolijo" que reemplace datos de prod (contradice §6).
