# RUBRIC — <nombre del cambio o del proyecto>

> La rúbrica es el ACCEPTANCE de lo NO-testeable: criterio cualitativo versionado,
> con pesos, anchors y umbral. Un grader (cualquier agente, cualquier LLM, o un
> humano) la puntúa criterio por criterio CON EVIDENCIA `file:line` y emite el JSON
> del contrato (ver `templates/rubric-grader-prompt.md`); `qa_ledger.py rubric-ingest`
> lo absorbe. Por default ACONSEJA; gatea solo si lo declarás
> (`defaults.rubric.gate: true` en el config, o `--gate`).
>
> Formato parseable: `- [ ] RB-01 (peso 3) — criterio`. El peso es opcional
> (default 1). Los anchors son para el grader, el engine no los parsea.

threshold: 0.80

## Criterios

- [ ] RB-01 (peso 3) — Manejo de errores sano: toda llamada externa tiene timeout,
  la falla se traduce a un mensaje accionable y no se traga excepciones.
  - anchor-pass: `client.get(url, timeout=5)` + reintento con backoff + log con contexto.
  - anchor-fail: `except Exception: pass`, o un `catch` que solo re-lanza sin contexto.
- [ ] RB-02 (peso 2) — Convenciones del repo respetadas: naming, estructura de
  paquetes y estilo consistentes con el código vecino (no con la preferencia del autor).
  - anchor-pass: el archivo nuevo es indistinguible en estilo de sus hermanos.
  - anchor-fail: un módulo con camelCase en un repo snake_case.
- [ ] RB-03 (peso 2) — Ergonomía de la API/superficie: nombres que dicen qué hacen,
  parámetros sin sorpresas, el caso común es el fácil.
- [ ] RB-04 (peso 1) — La documentación del cambio explica el PORQUÉ, no parafrasea
  el código.

## Criterios negativos

> Cosas que NO deben aparecer. Si el grader las encuentra (verdict `fail` CON
> evidencia), restan su peso del score.

- [ ] RB-NEG-01 (peso 2) — Comentarios que narran la corrección del propio cambio
  ("now correctly handles...") en vez de documentar el código.
- [ ] RB-NEG-02 (peso 1) — Abstracciones especulativas: interfaces/capas con un solo
  uso y sin pedido en la SPEC.
