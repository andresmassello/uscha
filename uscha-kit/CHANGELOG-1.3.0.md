# dev-loop-kit 1.3.0 — "facts block, wired" (2026-07-01)

Release temático: el kit ahora **cumple su propio principio de cabecera**. Dos auditorías
adversariales (7 lentes de metodología + fidelidad doc↔código↔idea, 231 agentes) encontraron
que los fact-gates existían pero no alimentaban ni convergencia ni readiness, mientras que
los números auto-reportados del agente sí. 1.3.0 invierte eso de vuelta: *under-claim,
then wire, then re-claim*.

## Engine (qa_ledger.py)

### Nuevo
- **`log-gate`** — persiste el veredicto de un fact gate (golden-diff / gate-check /
  pit-check / simplicity) como record static-gate-shaped: `fail` → BLOCKER que capea
  readiness ≤65 y bloquea convergencia; `pass` → limpia el gate (latest-per-tool);
  `not-run` → evento registrado que NUNCA lee como verde (la ausencia no es evidencia).
- **`flag-blocker [--resolve]`** — violación de CONSTITUTION/invariante como BLOCKER de
  primera clase por la MISMA plomería que un BLOCKER de linter. El enforcement "capea ≤65 y
  bloquea convergencia" ahora es real una vez registrada la violación.
- **`resolve-escalation`** — cerrar el gate humano es un evento registrado (`resolved_at`),
  no una implicación.

### Endurecido
- **readiness**: un repo linteable cuyo static gate nunca corrió puntúa UNMEASURED (0.0),
  no 1.0 — *el silencio no es éxito*. La dimensión agregada es el promedio per-repo (que ya
  codifica UNMEASURED). El cap de escalación es independiente de converged y se sostiene
  hasta `resolve-escalation`.
- **converged**: con `qa_tools_order` exige el último step POR HERRAMIENTA (rellenar la
  ventana con steps limpios ya no esconde findings) y un snapshot rojo MEDIDO veta el verde
  narrado del agente (`--tests-passed`).
- **gate-check**: borrado de archivo de test entero (`+++ /dev/null`) ya no es invisible;
  thresholds bajados O borrados se detectan cross-hunk por keyword; con `--repo` compara los
  totales de tests ejecutados entre snapshots (caída medida → REVIEW).
- **golden-diff**: cero fixtures = **NOT-RUN (exit 2)**, nunca CLEAN — también en `--json`
  (antes reportaba CLEAN con 0 comparaciones).
- **simplicity-check**: min-floor en dims pesadas — un diff >1.5× del presupuesto de
  tamaño/crecimiento no se promedia a ACCEPTABLE con dims baratas verdes.
- **spec-check**: veredictos partidos por la propia regla del kit — los 2 chequeos
  ESTRUCTURALES (falta out-of-scope / sin criterios de aceptación) son HECHOS y bloquean
  (exit 1); la prosa (vagos/EARS/stack) sigue advisory (`--strict` gatea).
- **oscillation**: detecta por Jaccard ≥0.8 sobre finding_ids (períodos 2-3) — un finding-ID
  corrido ya no esconde el loop; fallback al fingerprint exacto.

## Hook (block-approved-writes.ps1)
- Bloquea CUALQUIER comando Bash que referencie un path `.approved` (la co-ocurrencia de
  keywords era bypasseable vía `python -c "open(p,'w')"` / paths por variable / dd).

## Skill dev-loop (SKILL.md)
- Línea de audiencia arriba de todo: *un operador, un cambio con riesgo, ledger, human gate*
  — y disclaimer NOT-for-trivial.
- Contrato de dos tiers explícito: medido (puede bloquear) vs auto-reportado (narración).
- **El golden ahora es alcanzable desde el camino principal**: captura en Phase 1 (perfil E,
  vía `characterize`/`reverse-discovery`), `golden-diff` + `gate-check` persistidos con
  `log-gate` en cada pass de Phase 3 (3b), hook + `.gitattributes` en Setup.
- Convergencia documentada como es: per-tool + fact gates + snapshot veta narración.
- CONSTITUTION: se registra con `flag-blocker` (obligación del agente), enforcement del
  engine después del registro — se eliminó el "by construction" sin mecanismo.
- readiness: sin `--section` en el llamado documentado (un heading mismatch cereaba la
  dimensión más pesada en silencio); UNMEASURED documentado.
- sys-doc degradado a reporting opcional (era la instancia más clara de scope creep).
- `improve-deep` → `improve` (la skill real); protocolo tracked-md generalizado.

## Kit
- `dev-loop.config.json`: version 1.3.0, `qa_tools_order` con `improve`, repos de ejemplo
  genéricos (`backend-api`/`mobile-app` — antes traía repos del proyecto del autor).
- `templates/CONSTITUTION.md`: enforcement honesto (flag-blocker), CWE-1124 para anidación
  (era 1121), tag CWE-1074 removido de YAGNI (no mapea).
- `README.md`: las SEIS skills (faltaban `characterize` y `reverse-discovery` — justo donde
  vive el flujo golden), on-ramp de migración, subcomandos nuevos, audiencia, generalización.
- `workbench-doctor.sh`: sonda characterize/reverse-discovery/improve (sin improve-deep).
- `VERSION`: 1.3.0.

## Deferido (consciente, no olvidado)
- rebuild: densidad de asserts por test-file en la firma (anti tests-preservados-destripados).
- Perfiles A-E mecanizados en config (`--profile`). Hoy: heurística de proceso, marcada como tal.
