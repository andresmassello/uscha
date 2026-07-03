# dev-loop-kit 1.16.0 — regression-capture: Find Bugs Once (2026-07-03)

Séptima mejora del backlog PragProg (M1 de `docs/analisis-pragmatic-programmer.md`;
Topic 51 / Tip 94 *"Find Bugs Once"* + Tip 31 *"Failing Test Before Fixing
Code"*). Ataca el cierre narrado de findings: el agente reporta `fixed` y nadie
pregunta **qué test reproduce el bug que dice haber arreglado**.
Smoke suite: 106/106.

## La idea (measured beats narrated, ahora sobre el CIERRE)

- `regression-check --repo X [--fixed N] --diff/--from-git`: cruza los findings
  cerrados con el diff que los arregla. Verdicts:
  - **N/A** — nada cerrado, nada que exigir.
  - **MEASURED** — el diff agrega/modifica líneas en el árbol de test
    (clasificador compartido de los 9 stacks).
  - **NARRATED** — desaparecieron findings sin tocar UN solo test. Aconseja
    por default (exit 0 con warning); `--strict` gatea; `log-gate --kind
    regression --verdict fail` lo persiste si el equipo decide bloquear.
- Sin `--fixed` explícito lee la suma de `fixed` de la iteración más reciente
  del repo en el ledger — el dato ya estaba, ahora se interroga.
- **escape_analysis obligatoria**: resolver un `flag-blocker` ahora EXIGE
  `--escape-analysis "<qué gate/test debió atraparlo y qué se hizo>"` —
  la reflexión es parte del cierre, no opcional (cerrar un BLOCKER sin ella
  es garantía de encontrarlo dos veces). Se persiste en el registro del gate.

## Decisiones de diseño (documentadas, no implícitas)

- La evidencia es a nivel **DIFF** y es mecánica: ¿el diff que arregla agrega
  líneas NO VACÍAS en el árbol de test? — un hecho. El mapeo finding→test
  específico sería adivinanza sin una convención de naming
  (¿`test_regr_<fingerprint>`?): **diferido consciente**, el gate mide lo que
  se puede medir sin inventar.
- **Límite disclosed (hallazgo del review fresco, aplicado)**: es un tripwire,
  no un juez de calidad — una línea de comentario en un test file cuenta como
  evidencia (juzgar contenido entre 9 lenguajes sería adivinanza). Mitigación
  honesta: las líneas en blanco NO cuentan, y las señales
  `has_test_definition`/`has_assertion` se exponen como hechos en el JSON —
  un MEASURED sin ninguna de las dos imprime "evidencia DÉBIL" para el ojo
  humano. La calidad de los tests la juzga pit-check (mutation testing), no
  este gate.
- Advisory-first: NARRATED no bloquea por default — mismo patrón de adopción
  incremental que acceptance trazable (1.10.0) y los advisories de 1.14.0.

## Skills

- `dev-loop`: tras loguear un pass con `--fixed > 0`, correr `regression-check`;
  cierre NARRATED = escribir el test de regresión (el test que falla va ANTES
  del fix).

## Smoke

- **T38**: fix sin tests → NARRATED (exit 0 advisory / `--strict` exit 1) ·
  fix con test nuevo → MEASURED (pasa aun con `--strict`) · `--fixed 0` → N/A ·
  lookup del `fixed` de la última iteración del ledger sin `--fixed`.
- **T4 endurecido**: resolver un blocker sin `--escape-analysis` → rechazado.
