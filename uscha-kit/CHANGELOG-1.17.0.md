# dev-loop-kit 1.17.0 — procedencia visible de umbrales (2026-07-03)

Octava mejora del backlog PragProg (M5 de `docs/analisis-pragmatic-programmer.md`;
Tip 8 *"Make Quality a Requirements Issue"* + Topic 8 *"ETC es un valor, no una
regla"*). Resolución elegida por el humano entre tres opciones: **procedencia
visible** — ni fiel-al-libro (advisory por default hubiera desarmado el
anti-Goodhart) ni rechazo. Smoke suite: 111/111.

## La idea (el conteo es hecho · el umbral es opinión · salvo que lo declares)

- **Que el cap EXISTA es principio, no opinión**: "tests rojos ⇒ no estás
  ready" es una definición. Los caps siguen mordiendo por default — nada se
  afloja, ningún usuario existente ve su score subir en silencio.
- **El NÚMERO es opinión del kit SALVO que el humano lo declare.** El acto de
  declaración ya existía: el `dev-loop.config.json` commiteado es humano-owned.
  Valor explícito en `config.defaults` = requerimiento; fallback a la
  constante del engine = default del kit. Cero schema nuevo.
- Lo que faltaba era la **etiqueta**: ahora cada umbral que muerde dice de
  dónde vino.

## Engine (qa_ledger.py)

- `readiness`: el cap que muerde se etiqueta — `capped at 35: tests red —
  umbral default del kit` vs `— umbral requerimiento (config)`. El threshold
  de coverage se etiqueta en la línea resumen (`thr 60, declarado` /
  `default del kit`). JSON expone `cap_source` y `thresholds_declared`.
- `simplicity-check`: los presupuestos declarados (config o CLI) llevan `*`
  en la tabla; sin ninguno declarado imprime el aviso "todos los presupuestos
  son defaults del kit — opinión, no requerimiento". JSON expone
  `budgets_declared`.

## Skills

- `discovery`: paso 9 nuevo en la agenda — **quality bar**: "¿qué nivel de
  calidad BASTA acá y qué dimensiones son negociables?" con propuesta acorde
  al perfil de riesgo (un core de pagos no es un dashboard interno). Lo que el
  humano declara va al config — declarar ES commitear el config.

## Smoke

- **T39**: cap declarado (`readiness_caps.tests_red` en config) → etiqueta
  `requerimiento (config)` en JSON y texto · sandbox sin caps declarados →
  lista vacía · simplicity sin declarar → aviso de opinión · presupuesto por
  CLI → listado en `budgets_declared`.
