# FIELD NOTE 001 — Migración de tesorería legacy: lo que atrapó el ledger

**Estado:** proyecto real, anonimizado. Los números son exactos y salen del `QA-LEDGER.json`, `ACCEPTANCE.md` e historial git del proyecto. Las atribuciones causales inferidas (no registradas) están marcadas como tales — ver Limitaciones.
**Forma del proyecto:** migración de un sistema de tesorería legacy en PHP (codebase legacy fuertemente customizado) a Java/Spring Boot + SQL Server + React. Perfil de riesgo E (migración). 6 módulos de tesorería, 12 ADRs, 12 invariantes de constitución, 21 criterios de aceptación, 48 fixtures golden capturados del sistema legacy, 44 tests backend al cierre, ~2 días de actividad de ledger en 5 PRs squash-merged.
**Honestidad primero:** el sistema **no está en producción**. Readiness final 79.4 (IN PROGRESS); los dos criterios abiertos (AC-13, AC-14) son los gates humanos de cutover, por diseño. Esta nota no es "hicimos un sistema de tesorería en dos días" — es el registro de cada vez que el grafo medido contradijo un "terminado" declarado o aparente.

---

## El número de cabecera

El agente marcó **19 de 21** checkboxes de aceptación. El motor aceptó **16**.

Los otros 3 estaban marcados pero sin test verde que los nombre — el ledger los clasifica *narrated-only* y se niega a contarlos ("measured beats narrated: NO cierra"). Un checkbox es un claim. Evidencia es una corrida de tests que el motor ingirió. La brecha entre 19 y 16 es la tesis completa de la herramienta en una línea.

## Cinco capturas, desde el ledger

**A — Readiness clavado en 49/NOT-READY durante 10 snapshots verdes consecutivos.** Los tests crecieron 15 → 40 (todos en verde), cobertura ~80%, durante casi 8 horas — y el score no se movió de 49 en 10 registros consecutivos. Saltó a 82.6 solo inmediatamente después de registrarse el gate golden-diff (48/48 CLEAN). *Atribución inferida, números exactos:* la config tenía `golden_required=true` bajo perfil E; la razón del cap no se persiste por entrada (ver Limitaciones y el follow-up de engine). Los tests verdes no pudieron sustituir la única evidencia que el perfil de riesgo exigía.

**B — BLOCKER de constitución: endpoints de plata sin auth.** Los módulos de dinero (ledger, facturas, cuentas) estaban construidos y en verde cuando el gate de constitución registró 1 BLOCKER: INV-12, "no auth/authz on any endpoint yet". Readiness capada. Cerrado cinco iteraciones después con evidencia: `@PreAuthorize` por grupo en cada controller más un `AuthzContractTest` probando allow/deny/admin-bypass. Los tests decían listo; un invariante inviolable dijo no.

**C — Review adversarial sobre código verde, ronda 1:** con `tests_passed=true`, una pasada de code-review reportó 18 hallazgos, **7 en o sobre el severity gate** (BLOCKER/CRITICAL/HIGH) en los paths de plata. 5 arreglados, 8 diferidos con rationale en `ISSUES-DEFERRED.md`.

**D — Review adversarial sobre código verde, ronda 2:** de nuevo con tests verdes: 6 hallazgos, 2 gated — **#1 BLOCKER: ETL no atómico por fila** (una fila mala abortaba toda la migración) y **#2 HIGH: session fixation (CWE-384)**. Ambos arreglados; 3 MEDIUM diferidos con rationale.

**E — Evidencia stale descartada; el score se desplomó dos veces.** Al re-registrar readiness, el motor rechazó reportes JUnit más viejos que el código: el score cayó de la zona de 82.6 a **53.5**, y recuperó 82.6 solo tras re-correr la suite sobre evidencia fresca; el patrón se repitió al día siguiente (**54.0** → 79.4). Dos snapshots quedaron en el ledger marcados `freshness=stale`. *Atribución inferida del patrón caída-y-recuperación; scores exactos.* El verde de ayer no es el verde de hoy.

## Lo que "tests en verde" solo hubiera shippeado

Leyendo B, C y D juntos: un sistema de tesorería con **endpoints de plata sin autenticación, un ETL de migración no atómico y una vulnerabilidad de session fixation — todo con la suite completa en verde.** Nada de eso lo atrapó la suite: lo atraparon el gate de constitución y las pasadas de review adversarial cuyos hallazgos entran al mismo ledger que todo lo demás. Esa es la diferencia práctica entre "el agente corrió tests" y "el grafo está medido".

## Limitaciones (leer antes de citar)

1. **Las causas no se persisten por entrada.** El ledger registra scores e iteraciones, no eventos estructurados de "cap aplicado" / "N reportes stale descartados". Los casos A y E llevan números exactos con causas inferidas, y así están marcados.
2. **Los false dones están subcontados.** Solo se cuentan los rechazos que dejaron evento en el ledger. Las auto-correcciones del agente antes de registrar estado no dejan rastro; el número real de "done" prematuros es probablemente mayor.
3. **Los conteos de review son auto-reportados** por la pasada de review al ledger; no fueron re-verificados independientemente para esta nota.
4. **La cobertura sobreestima la confianza justo donde más importa:** 73.75% es line coverage JaCoCo sobre tests unitarios contra H2, no SQL Server. La fidelidad decimal/dialecto de los módulos de dinero sobre el motor real está explícitamente diferida (Testcontainers MSSQL en `ISSUES-DEFERRED.md`).
5. **Los golden congelan el comportamiento del sistema legacy** (captura byte-determinística, 46/47 idénticos en dos corridas, 1 scrub declarado). La fidelidad del sistema nuevo se prueba por tests AC-tagged, no por byte-diff — "regresiones atrapadas por el golden sobre el sistema nuevo" no es un claim que este proyecto pueda hacer en términos de bytes.
6. **Los squash-merges colapsaron el historial:** 6 commits en main subrepresentan las iteraciones reales; los loops por feature no se registraron.

## Follow-up de engine que este proyecto generó

La limitación 1 es un hallazgo de producto, no solo un caveat: el motor debería persistir eventos estructurados de **caps de readiness (con razón)** y **descartes de evidencia stale (con conteo)** para que los casos A y E de la próxima field note estén registrados, no inferidos. Cargado como mejora contra el kit.

---

*Método: [Uscha](https://uscha.dev) — desarrollo spec-driven con un QA ledger determinístico donde los hechos bloquean y la narración aconseja. Esta nota se extrajo solo-lectura de los artefactos del proyecto; el pedido de extracción y sus reglas se publican junto al kit.*
