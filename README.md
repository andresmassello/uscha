# Uscha

**Uscha** es una metodología spec-driven, tool-agnóstica, para desarrollo con
LLM coding agents — *vos traés la idea, el método construye el resto* — con su
instanciación en Claude Code, el **uscha-kit**.

> **Uscha** es el nombre; el patrón que operacionaliza es un *spec-loop* — un loop
> spec-driven de build-and-verify. "spec-loop" es el **concepto**, no el naming.
> (El checkout local conserva el path `SpecLoop`.)

> La herramienta ejecuta · el método gobierna · la evidencia decide · el humano aprueba.

## Mapa del repo

```
SpecLoop/
├── uscha-kit/          # ★ SOURCE canónico del kit (v1.31.0)
│   ├── .claude/skills/    #   7 skills: uscha-discovery · uscha-adr-refine · uscha-devloop · uscha-sysdoc
│   │                      #             uscha-reverse-discovery · uscha-characterize · uscha-rubric
│   ├── .claude/skills/uscha-devloop/qa_ledger.py   # motor de evidencia (24 subcomandos, stdlib)
│   ├── hooks/             #   PreToolUse: el agente no escribe .approved (INV-GOLDEN-01)
│   ├── templates/         #   CLAUDE.md · CONSTITUTION.md · .gitattributes · docs/adr
│   └── CHANGELOG-*.md     #   1.2.x → 1.3.0 ("facts block, wired") → 1.4.0 (python) → 1.5.0 (node) → 1.6.0 (go) → 1.7.0 (rust+dotnet) → 1.8.0 (cpp) → 1.9.0 (gradle+swift) → 1.10.0 (acceptance trazable) → 1.11.0 (tests fuera del presupuesto) → 1.12.0 (secret-scan) → 1.13.0 (ledger atómico) → 1.14.0 (plateau/stop-signal) → 1.15.0 (golden scrub) → 1.16.0 (regression-capture) → 1.17.0 (procedencia de umbrales) → 1.18.0 (FSM derivada) → 1.19.0 (spikes — backlog PragProg CERRADO) → 1.20.0 (instalación global) → 1.21.0 (namespace uscha-*) → 1.22.0 (doctor) → 1.23.0 (rubric layer) → 1.24.0 (plugin de Claude Code) → 1.25.0 (anti-ceremonia) → 1.26.0 (waste-check REUSE-FIRST) → 1.27.0 (FTY) → 1.28.0 (acceptance medido %) → 1.29.0 (rebrand → Uscha) → 1.30.0 (gate de dependencias) → 1.31.0 (freshness de evidencia + gate de doc-version)
├── docs/                  # artefactos publicados (canónicos acá; Downloads = snapshots)
│   ├── uscha-claude-code-doc-FINAL.html   # deck largo ES (36 slides)
│   ├── uscha-claude-code-doc-EN.html      # deck largo EN
│   ├── uscha-playbook{,-EN}.html          # Manual del Operador (trigger/move/gate)
│   ├── uscha-onepager{,-EN}.html          # ficha de una página
│   ├── uscha-team-pitch.html              # pitch de adopción para el equipo (historia Vale/Martín, 14 slides)
│   ├── uscha-team-pitch-extended.html     # pitch extendido: + día-tipo, KPI readiness, ledger 2 pisos, piloto (22 slides)
│   ├── skills-referencia.html                 # referencia exhaustiva de las 7 skills (qué hace cada una, fase por fase)
│   ├── casos-reales.md                        # bitácora: momentos reales donde el método interviene (anonimizados)
│   ├── *.png                                  # mapa del sistema · 10 pasos · reverse-discovery
│   └── diagram-sources/                       # HTML fuente de los PNG (re-renderizables)
├── formats/               # 6 exploraciones de formato (A-F); se adoptaron playbook + atlas-map
└── audits/                # outputs de las auditorías adversariales (2026-07)
    ├── audit-metodologia-7-lentes.json        # 33 debilidades confirmadas / 13 refutadas
    ├── audit-fidelidad-doc-codigo-idea.json   # 171 claims verificados doc↔código↔idea
    ├── truth-pass-6-docs.json                 # 130 edits de veracidad post-cableado
    └── verificacion-team-pitch.json           # 3 lentes sobre el pitch
```

## Estado (2026-07-05)

- **Kit v1.31.0** <!-- uscha:version --> — los fact gates están CABLEADOS al engine (1.3.0: `log-gate`,
  `flag-blocker`, `resolve-escalation`; UNMEASURED; convergencia per-tool con veto de
  snapshot medido) y el engine mide repos **Python** (1.4.0: pytest/Cobertura + ruff +
  mypy) **TypeScript/JS** (1.5.0: lcov + jest-junit + eslint + tsc) **Go** (1.6.0: cover profile
  nativo + gotestsum + golangci via checkstyle), **Rust** (1.7.0: Cobertura +
  nextest + clippy) **C#/.NET** (1.7.0: coverlet + junit
  logger + SARIF/Roslyn), **C++** (1.8.0: gcovr/Cobertura + ctest junit +
  clang-tidy), **Kotlin/JVM Gradle** y **Swift** (1.9.0: cero parsers nuevos —
  JaCoCo/lcov/JUnit/checkstyle reusados; detekt + SwiftLint). **Acceptance trazable** (1.10.0: AC-n cierra por testcase
  MEDIDO, dimensión dominante del readiness — M2 del backlog PragProg). **Tests fuera
  del presupuesto de simplicity** (1.11.0: escribir tests no penaliza el gate — M9).
  **Secret-scan en gate-check** (1.12.0: claves privadas/tokens/contenedores agregados
  bloquean como hecho — M8). **Ledger atómico** (1.13.0: checksum de integridad + carga
  blindada — M3). **Plateau/stop-signal** (1.14.0: stall y candidato-a-PR como
  advisories — M6). **Golden scrub** (1.15.0: volátiles declarados enmascaran con
  masking visible — M7). **Regression-capture** (1.16.0: cierre de findings sin test =
  narrado; escape-analysis obligatoria al resolver blockers — M1). **Procedencia de
  umbrales** (1.17.0: cada umbral se etiqueta por procedencia — requerimiento
  declarado en config vs opinión default del kit; el cap que muerde lo dice en el
  headline — M5). **FSM derivada** (1.18.0: `phase` computa el estado del workflow
  desde los hechos del ledger, jamás declarado; el PR se gatea con `--require
  pr-ready` — M4). **Spikes formales** (1.19.0: rama `spike/*` jamás pasa el gate de
  PR; el output legítimo es un ADR con lecciones — M10). Smoke suite 185/185 verde.
  **El backlog PragProg está CERRADO: 10 de 10** (ver
  `docs/analisis-pragmatic-programmer.md`).
  Licencia: MIT. El principio "facts block, guesses advise" es propiedad enforced,
  no slogan.
- **Docs** — pasados por truth-pass contra el engine real: cada claim describe lo que
  v1.31.0 hace; el anexo de referencias tiene **links verificados por fetch** a las 10
  fuentes. Convención de estado en los docs: `en el kit` / `nuevo` / `propuesta`.
- **En curso** — dogfooding en caso real (proyecto piloto, Python): el adapter 1.4.0 lo desbloqueó;
  queda el dry-run de solo lectura (criterio 2 del HANDOFF python-adapter) y el on-ramp.
  Diferidos conscientes en CHANGELOG-1.4.0 (densidad de asserts en rebuild, perfiles A-E
  mecanizados).

## Cómo se re-empaqueta el kit

```bash
powershell -NoProfile -Command "Compress-Archive -Path 'uscha-kit' -DestinationPath 'uscha-kit-X.Y.Z.zip' -Force"
```

Los zips son artefactos de build: no se commitean. El source del kit en este repo es la verdad.

## Historia

Nació como metodología de trabajo con Claude Code, se destiló con el principio
Böckeler (computacional bloquea / inferencial aconseja), sobrevivió dos auditorías
adversariales (231 agentes) que encontraron el principio central invertido en el código
— y la 1.3.0 lo dio vuelta. Los detalles, en `audits/` y en los CHANGELOG.
