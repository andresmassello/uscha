# uscha-kit 1.30.0 — gate de dependencias: supply-chain hecho visible (2026-07-05)

Origen: intake de research (SLR de agentic-AI arXiv:2605.15245 + survey de seguridad de
agentes). De los 4 papers, la única mejora genuina y doctrina-pura: el modelo de amenaza
"el agente mete una dependencia sin vetear (o envenenada)" — que Uscha no cubría. La
CONSTITUTION ya dice "0 dependencias nuevas sin aprobación", pero como **prosa**. Esto la
hace visible. Smoke suite: 181/181.

## Qué hace (mínimo, sin overengineering)

- **`gate-check` flaguea dependencias nuevas** como señal **BLANDA** (avisa; gatea con
  `--strict`), NO como subcomando nuevo: una dep nueva es exactamente la categoría que
  `gate-check` ya cubre ("el cambio hace algo que necesita sign-off humano" — tests
  borrados, thresholds bajados, secretos). Reusa toda la maquinaria: cero config nuevo,
  cero subcomando.
- Detecta líneas AGREGADAS con forma de dependencia en los manifests de los 9 stacks
  (`package.json`, `requirements*.txt`, `pyproject.toml`, `Cargo.toml`, `go.mod`,
  `pom.xml`, `build.gradle(.kts)`, `Gemfile`, `Podfile`, `*.csproj`). En `--json`:
  campo `new_dependencies`.
- **Advisory por default**: verdict `REVIEW`, exit 0. Con `--strict`, la señal blanda
  (deps + supresiones + asserts removidos) gatea exit 1.

## Por qué así (decisiones de la doctrina)

- **NO subcomando nuevo** — hubiera sido fragmentación/ceremonia. Extender `gate-check`
  es el tamaño correcto: mismo concepto (integridad del cambio), misma maquinaria.
- **Blando, no BLOCKER** — agregar una dependencia suele ser legítimo; solo necesita que
  un humano la vea. Bloquear por default mataría el gate (se desactiva). El humano
  declara `--strict` si su dominio lo exige (procedencia, misma doctrina que 1.17.0).
- **Heurística honesta** — matcheo de líneas por manifest, no un resolver semántico de
  dependencias. Un falso positivo (bump de versión, key no-dep) es benigno porque es
  advisory. Documentado en el código.

## Lo que NO entró del intake (anti-overengineering)

- **Ruteo de modelo por perfil de riesgo** (de ALMAS, arXiv:2510.03463): diferido —
  depende de mecanizar los perfiles A–E (que no existen) y vive en la capa de
  orquestación, no en el engine model-agnostic.
- **Meta-RAG / índice de repo**: diferido — no hay problema de perf medido en el walk del
  waste-check; índice especulativo = YAGNI.

## Smoke (T7b, 4 checks)

Dep nueva en `package.json` → `REVIEW` + listada en `new_dependencies`; sin `--strict`
exit 0 (advisory); con `--strict` exit 1; y un diff de código normal NO flaguea dep
(sin falso positivo).
