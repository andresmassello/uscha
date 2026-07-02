# Bitácora de casos reales

Momentos observados en sesiones reales de trabajo con LLM coding agents donde el método
habría intervenido (o donde intervino). Cada entrada registra HECHOS del transcript —
no impresiones — y mapea el mecanismo exacto de spec-loop que aplica.

Regla de la bitácora: se anota el comportamiento, anonimizado (sin nombres de proyectos,
clientes ni dominios). El valor está en el patrón, no en el culpable.

---

## Caso 001 — "could you check?" → "Diseño cerrado" (2026-07-02)

### Qué pasó (hechos del transcript)

En una sesión real sobre un backend Java, el humano pidió:

> *"got some errors on remote QA server, could you check ? `<repo>/docs/logs<fecha>`"*

Un pedido de **diagnóstico** — "¿podés chequear?". El agente:

1. ✅ Listó y leyó los logs. Contó errores por tipo. — *eso ES chequear*
2. ✅ Leyó el código fuente involucrado para entender las causas. — *diagnóstico legítimo*
3. ❌ Y sin mostrar el diagnóstico ni esperar respuesta, en el mismo turno:
   > *"**Diseño cerrado.** TDD: primero los tests del resolver (back-compat), después el
   > endpoint. Escribo los tests RED del resolver:"*
4. ❌ Editó tests y **código de producción**, y corrió el build.

Entre el pedido "chequeá" y el código modificado: **cero puntos de decisión humana**.
Nadie vio el diagnóstico antes del fix. Nadie eligió entre alternativas. Nadie decidió
que un fix era lo que se quería (¿y si correspondía un rollback? ¿y si el error era
conocido y aceptado?).

### La ironía que hace al caso valioso

El agente dijo "TDD" y trabajó con oficio: tests primero, back-compat, build. **La
ejecución fue competente; la gobernanza fue inexistente.** El problema no es que el
agente sea malo — es que sin método, su sesgo por defecto es a la ACCIÓN, y "check"
escala silenciosamente a "diseño cerrado + producción tocada". A veces el resultado es
correcto y bienvenido; a veces es el incidente de cupones. Sin gobernanza, no se puede
saber cuál de los dos va a ser — y ese es el costo.

### Qué habría hecho spec-loop distinto

| Momento | Mecanismo | Efecto |
|---------|-----------|--------|
| El pedido "check" | **La entrega de un diagnóstico ES el entregable.** El método distingue evaluar de intervenir: los hechos se reportan, el humano decide. | El agente presenta el análisis de los logs y las causas — y PARA. |
| "Diseño cerrado" | **Un diseño lo cierra un humano.** Contrato de escalación del dev-loop: *"un fix que requiere una decisión de diseño (nivel ADR) → STOP y preguntar"*. | La decisión de diseño se presenta con alternativas; la elige el humano (y queda en un ADR — legible para el próximo). |
| Antes de codear | **Phase 0 del dev-loop**: sin criterios de aceptación no se construye — *"si faltan, corré `/adr-refine` primero (o preguntá)"*. | El fix se especifica ANTES: qué comportamiento se espera, qué queda fuera, cómo se verifica. |
| Si igual hubiera codeado | **El merge gate**: el loop abre el PR y para; mergea una persona. | Última red — pero el método pone la fricción ANTES, donde es barata. |

### La frase para la presentación

> "Check" es una pregunta. El agente respondió con un commit.

---

*Plantilla para próximas entradas: **Qué pasó** (hechos, citas del transcript) · **Por
qué importa** (el patrón, no el culpable) · **Qué habría hecho el método** (mecanismo
exacto, no vibes).*
