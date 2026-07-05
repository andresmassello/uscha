# dev-loop-kit 1.11.0 — tests fuera del presupuesto de simplicity (2026-07-03)

Segunda mejora del backlog PragProg (M9 de `docs/analisis-pragmatic-programmer.md`;
Topic 51: *"un buen proyecto puede tener MÁS código de test que de producción, y
vale la pena"*). Elimina un **incentivo perverso activo**: el simplicity-check
contaba las líneas de test junto a las de producción contra un único presupuesto —
el gate castigaba escribir tests y empujaba al agente a testear menos para pasar.
Smoke suite: 73/73.

## La idea

- Escribir tests **nunca** acerca un diff a OVERBUILT. Los archivos de test se
  detectan, se cuentan y se **reportan aparte** (`test_lines_added`,
  `test_files_changed`) — pero no gatean ninguna dimensión del score.
- La otra dirección ya estaba protegida: **borrar** tests lo bloquea gate-check.
  Con esto el incentivo queda alineado en ambas direcciones.

## Engine (qa_ledger.py)

- `_is_simplicity_test_file()`: clasificador type-agnóstico (el diff no trae
  `repo_type`) — unión de las convenciones de los 9 stacks: dirs
  `test/tests/__tests__/Tests/*.Tests`, source sets Gradle (`src/*Test/`),
  `test_*.py`, `*_test.go`, `*.test.ts`/`*.spec.js` (multi-dot incluido),
  `*Test.java`/`*Tests.cs` CamelCase **case-sensitive** — `backtest.cpp` /
  `protest.cc` siguen contando como producción (misma trampa que ya evitan
  dotnet/cpp en `_is_test_path`).
- Dirección de fallo benigna y documentada: un falso positivo solo EXIME del
  presupuesto — nunca bloquea ni borra nada.
- `_simplicity_metrics()`: tercer estado de conteo (`prod`/`test`/fuera);
  las líneas de test no alimentan `lines_added`, `net_lines`, `files_changed`,
  `max_nesting`, `max_hunk_added` ni abstracciones. Output humano: línea
  informativa "tests FUERA del presupuesto: +N líneas en M archivo(s)".

## Smoke

- **T32**: diff sintético 6 líneas prod + 302 de test → el presupuesto ve 6/1;
  batería del clasificador (9 convenciones positivas + backtest/protest/Engine
  negativas).
- **T31** (edges 1.10.0, deuda del release anterior): batería de falsos
  positivos del tag regex (`HVAC2`, `mac1`, `track12` no taggean), classname
  jamás taggea, y semántica flaky de surefire (`<flakyFailure>` que pasó tras
  retry = verde; `<failure>`+`<rerunFailure>` = rojo, veta).

## Hardening (review fresco pre-commit)

- El review detectó que gate-check tenía SU PROPIO clasificador de tests
  (`_gc_is_test_file`) más débil: no reconocía `foo_test.go` (Go),
  `*.Tests/*.cs` (dotnet), `*.spec.tsx` ni `__tests__/` — así que "borrar
  tests lo bloquea gate-check" era overclaim para 4+ stacks. Fix: unión
  fail-closed — gate-check reusa el clasificador compartido de los 9 stacks
  MÁS sus sufijos legacy; solo se AMPLÍA qué cuenta como test, ningún path
  antes protegido se desprotege.
- `_GC_TESTDEF` ampliado con las definiciones de test que faltaban:
  `func TestX` (Go), `[Fact]`/`[Theory]` (xunit), `#[test]` (rust),
  `it(`/`test(`/`describe(` (js) — seguro porque TESTDEF solo se evalúa
  dentro de archivos ya clasificados como test.
- Smoke **T33**: borrado de tests Go/dotnet/JS → BLOCKER (antes invisible).
- Corrección truth-pass en `dev-loop-kit/README.md`: los pesos documentados
  de simplicity (`diff_size 30, nesting 25, abstraction 20...`) no coincidían
  con el engine (`35/30/20/8/7`, abstraction advisory sin peso) — drift
  pre-existente, alineado acá.

## Diferido consciente

- El resto del backlog PragProg (M1 regression-capture, M3 ledger atómico,
  M8 secret-scan, etc.) sigue en `docs/analisis-pragmatic-programmer.md` —
  una mejora por release.
