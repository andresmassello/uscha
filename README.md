# SpecLoop

Hogar del proyecto **spec-loop**: una metodología spec-driven, tool-agnóstica, para
desarrollo con LLM coding agents — *vos traés la idea, el método construye el resto* —
y de su instanciación en Claude Code, el **dev-loop-kit**.

> La herramienta ejecuta · el método gobierna · la evidencia decide · el humano aprueba.

## Mapa del repo

```
SpecLoop/
├── dev-loop-kit/          # ★ SOURCE canónico del kit (v1.3.0)
│   ├── .claude/skills/    #   6 skills: discovery · adr-refine · dev-loop · sys-doc
│   │                      #             reverse-discovery · characterize
│   ├── .claude/skills/dev-loop/qa_ledger.py   # motor de evidencia (16 subcomandos, stdlib)
│   ├── hooks/             #   PreToolUse: el agente no escribe .approved (INV-GOLDEN-01)
│   ├── templates/         #   CLAUDE.md · CONSTITUTION.md · .gitattributes · docs/adr
│   └── CHANGELOG-*.md     #   1.2.x → 1.3.0 ("facts block, wired")
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

- **Kit v1.3.0** — los fact gates están CABLEADOS al engine (`log-gate`, `flag-blocker`,
  `resolve-escalation`; UNMEASURED; convergencia per-tool con veto de snapshot medido).
  14/14 smoke tests sintéticos verdes. El principio "facts block, guesses advise" es
  propiedad enforced, no slogan.
- **Docs** — pasados por truth-pass contra el engine real: cada claim describe lo que
  v1.3.0 hace. Convención de estado en los docs: `en el kit` / `nuevo` / `propuesta`.
- **Pendiente** — dogfooding en caso real (criterios de éxito definidos ANTES de correr, que también puedan dar que NO);
  diferidos conscientes en CHANGELOG-1.3.0 (densidad de asserts en rebuild, perfiles A-E
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
