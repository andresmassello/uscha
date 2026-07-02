# dev-loop-kit 1.2.7 — skill reverse-discovery (front brownfield)

## Nuevo skill: reverse-discovery
- Hermano brownfield de `discovery`, para migrar/modernizar un sistema EXISTENTE.
- El inverso de discovery: el sistema ya existe y su comportamiento ES la verdad → se
  EXTRAEN hechos, no se propone forma.
- **Facts-only por diseño:** produce SOLO (1) un mapa del sistema (endpoints, contratos,
  grafo de dependencias, candidatos de módulo vía análisis estático) y (2) un golden suite
  capturado mecánicamente en los bordes. NO authorea SPEC/ADR inferidos — eso lo escribe el
  humano leyendo los hechos; las decisiones forward de módulos van a `/adr-refine`.
- Hereda INV-GOLDEN-01: el agente nunca toca los `.approved`.
- Cae limpio del lado "hechos" de la línea hechos-vs-prosa: análisis estático + byte-captura,
  cero heurística sobre prosa → nada frágil que se rompa.
- Flujo migración: reverse-discovery → humano escribe SPEC + /adr-refine → /dev-loop
  (golden-diff + ApplicationModules.verify() verdes) → readiness + human gate.
