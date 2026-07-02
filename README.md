# SpecLoop

Hogar del proyecto **spec-loop**: una metodología spec-driven, tool-agnóstica, para
desarrollo con LLM coding agents — *vos traés la idea, el método construye el resto* —
y de su instanciación en Claude Code, el **dev-loop-kit**.

> La herramienta ejecuta · el método gobierna · la evidencia decide · el humano aprueba.

## Mapa del repo

```
SpecLoop/
├── dev-loop-kit/          # ★ SOURCE canónico del kit (v1.9.0)
│   ├── .claude/skills/    #   6 skills: discovery · adr-refine · dev-loop · sys-doc
│   │                      #             reverse-discovery · characterize
│   ├── .claude/skills/dev-loop/qa_ledger.py   # motor de evidencia (19 subcomandos, stdlib)
│   ├── hooks/             #   PreToolUse: el agente no escribe .approved (INV-GOLDEN-01)
│   ├── templates/         #   CLAUDE.md · CONSTITUTION.md · .gitattributes · docs/adr
│   └── CHANGELOG-*.md     #   1.2.x → 1.3.0 ("facts block, wired") → 1.4.0 (python) → 1.5.0 (node) → 1.6.0 (go) → 1.7.0 (rust+dotnet) → 1.8.0 (cpp) → 1.9.0 (gradle+swift)
├── docs/                  # artefactos publicados (canónicos acá; Downloads = snapshots)
│   ├── spec-loop-claude-code-doc-FINAL.html   # deck largo ES (35 slides)
│   ├── spec-loop-claude-code-doc-EN.html      # deck largo EN
│   ├── spec-loop-playbook{,-EN}.html          # Manual del Operador (trigger/move/gate)
│   ├── spec-loop-onepager{,-EN}.html          # ficha de una página
│   ├── spec-loop-team-pitch.html              # pitch de adopción para el equipo (historia Vale/Martín, 14 slides)
│   ├── spec-loop-team-pitch-extended.html     # pitch extendido: + día-tipo, KPI readiness, ledger 2 pisos, piloto (22 slides)
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

## Estado (2026-07-02)

- **Kit v1.9.0** — los fact gates están CABLEADOS al engine (1.3.0: `log-gate`,
  `flag-blocker`, `resolve-escalation`; UNMEASURED; convergencia per-tool con veto de
  snapshot medido) y el engine mide repos **Python** (1.4.0: pytest/Cobertura + ruff +
  mypy) **TypeScript/JS** (1.5.0: lcov + jest-junit + eslint + tsc) **Go** (1.6.0: cover profile
  nativo + gotestsum + golangci via checkstyle), **Rust** (1.7.0: Cobertura +
  nextest + clippy) **C#/.NET** (1.7.0: coverlet + junit
  logger + SARIF/Roslyn), **C++** (1.8.0: gcovr/Cobertura + ctest junit +
  clang-tidy), **Kotlin/JVM Gradle** y **Swift** (1.9.0: cero parsers nuevos —
  JaCoCo/lcov/JUnit/checkstyle reusados; detekt + SwiftLint). Smoke suite 63/63 verde. Licencia: MIT. El principio "facts block, guesses advise" es propiedad
  enforced, no slogan.
- **Docs** — pasados por truth-pass contra el engine real: cada claim describe lo que
  v1.9.0 hace; el anexo de referencias tiene **links verificados por fetch** a las 9
  fuentes. Convención de estado en los docs: `en el kit` / `nuevo` / `propuesta`.
- **En curso** — dogfooding en caso real (proyecto piloto, Python): el adapter 1.4.0 lo desbloqueó;
  queda el dry-run de solo lectura (criterio 2 del HANDOFF python-adapter) y el on-ramp.
  Diferidos conscientes en CHANGELOG-1.4.0 (densidad de asserts en rebuild, perfiles A-E
  mecanizados).

## Cómo se re-empaqueta el kit

```bash
powershell -NoProfile -Command "Compress-Archive -Path 'dev-loop-kit' -DestinationPath 'dev-loop-kit-X.Y.Z.zip' -Force"
```

Los zips son artefactos de build: no se commitean. El source del kit en este repo es la verdad.

## Historia

Nació como metodología de trabajo con Claude Code, se destiló con el principio
Böckeler (computacional bloquea / inferencial aconseja), sobrevivió dos auditorías
adversariales (231 agentes) que encontraron el principio central invertido en el código
— y la 1.3.0 lo dio vuelta. Los detalles, en `audits/` y en los CHANGELOG.
