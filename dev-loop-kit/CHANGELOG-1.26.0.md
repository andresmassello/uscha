# dev-loop-kit 1.26.0 — REUSE-FIRST: la muda que el gate no veía (2026-07-04)

Origen: el handoff anti-ceremony+reuse+compliance, ítem 2. La muda dominante del
código IA —**duplicación / reinvención en vez de reuso**— caía en el punto ciego del
kit: `simplicity-check` puntúa el diff en AISLAMIENTO, nunca contra lo que ya existe.
Evidencia: GitClear *Maintainability Gap* (2026): +81% de duplicación desde 2023,
código refactorizado/movido en 3,8%. Entra con el acople corregido respecto del
handoff original: **advisory-first**, no BLOCKER-por-default. Smoke suite: 157/157.

## Qué hace

- **`qa_ledger.py waste-check`** (subcomando 24): detección determinística de clones
  Type-1/Type-2 del diff **vs el repo** (stdlib, sin LLM, sin red).
  - Input igual que `simplicity-check` (`--diff` · `--from-git [--base]` · stdin) +
    `--repo-root` para escanear lo existente.
  - Ventana de `W=5` líneas normalizadas (strip + colapso de whitespace, se descartan
    blancas y comment-only; una línea < `min_line_len` u sólo-puntuación no es
    significativa). Métricas: `dup_windows_vs_repo` (la señal dominante),
    `dup_windows_internal`, `dup_ratio`, `call_density` (informativo).
  - Bandas `LEAN ≥85 · ACCEPTABLE ≥65 · WASTEFUL <65`. Flags accionables que nombran
    el `archivo:linea` a reusar. `--json` con el contrato completo.
  - Excluye tests (como simplicity) y **los archivos que el diff toca** (no auto-match):
    captura el caso dominante — clon en archivo nuevo / desde archivos no tocados.
- **`log-gate --kind waste`**: persiste el veredicto → entra al veredicto único de
  `readiness` (1.25.0) como línea `gate:waste` y, si gateado, capea ≤65 / bloquea
  convergencia por la maquinaria existente.
- **`defaults.waste`** en config: `window_size`, `max_dup_windows_vs_repo`,
  `max_dup_ratio`, `min_line_len`, `allow_paths` (boilerplate legítimo), `gate`.
- **CONSTITUTION**: invariante **REUSE-FIRST** framed honesta (ver abajo).
- **SKILL** Fase 2c: corre `waste-check` junto al simplicity gate; en perfil A (trivial)
  no corre.

## Decisión de acople: advisory-first (corrige el handoff)

El handoff proponía `WASTEFUL → exit 1` + hard cap POR DEFAULT. Eso viola la
meta-invariante anti-ceremonia (1.25.0) regla 2: un detector Type-1/2 *habla siempre*
(boilerplate, DTOs, SQL/JSON embebido) → si bloquea por falsos positivos, se desactiva
y muere. Split honesto: el **HECHO** (un bloque de 5+ líneas ya existe en `X:linea`) es
medido; el **VEREDICTO** "wasteful" es heurística. Por eso: **avisa por default** (exit
0 con flags), gatea SOLO con `defaults.waste.gate: true` o `--gate` (procedencia 1.17.0:
el config commiteado ES la declaración). Un WASTEFUL declarado-gate persiste registro
bloqueante; sin declarar, sólo aconseja.

Nota: esto ELIMINA la dependencia de los perfiles A–E (que no están mecanizados): un
advisory default-quiet no necesita el perfil-skip para no ser ceremonia.

## Desviaciones honestas del handoff

- **`connectivity` NO puntúa** — se reporta informativa (como `new_functions` en
  simplicity). "Densidad de llamadas a símbolos existentes" es un proxy que
  false-positivea entre lenguajes; scorearlo sería ruido. Peso movido a
  `repo_reuse 55 · internal_dup 45`.
- **`max_dup_windows_vs_repo: 0` por default** es seguro PRECISAMENTE porque es
  advisory: cualquier clon vs repo baja el score y avisa, sin bloquear. Quien gatea
  sube el budget o usa `allow_paths`.

## Smoke (T46, 9 checks)

Repo sintético `wrepo/` + 4 fixtures: LEAN (código único → 0 clones), clon-vs-repo
(→ WASTEFUL, advisory exit 0, flag nombra el original; con `--gate` exit 1), clon
interno (`dup_windows_internal ≥ 1`), clon en archivo de TEST (excluido). Más:
determinismo (misma entrada → mismo score) y `log-gate --kind waste` visible en el
veredicto único de readiness.

## Límite honesto

Proxy Type-1/Type-2 sobre líneas normalizadas, NO detección semántica (Type-3/4:
renombres/reordenamientos) ni CC por AST. Es la definición operativa de GitClear —
suficiente para AVISAR, no para probar equivalencia semántica. El escaneo del repo es
O(archivos·líneas); en un monorepo enorme es un one-shot, no corre en cada pase.
