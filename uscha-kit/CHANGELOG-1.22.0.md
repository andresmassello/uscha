# dev-loop-kit 1.22.0 — doctor: diagnóstico de la instalación (2026-07-03)

`qa_ledger.py doctor` (subcomando 22) — espíritu flutter doctor: verifica que
spec-loop esté instalado y sano en la máquina de trabajo, Windows y Linux.
Smoke suite: 124/124.

## La idea

- **El engine verifica su PROPIA instalación**: las skills viven al lado de
  `qa_ledger.py` (sea `~/.claude/skills/` global o `.claude/skills/` del
  proyecto), así que doctor inspecciona a sus hermanos y reporta qué modo de
  instalación detectó.
- **Output ASCII puro** (`[OK]` / `[ !]` / `[ X]`): es la herramienta de primer
  contacto en máquinas vírgenes — no puede depender del encoding de la consola.
- **Exit 1 SOLO con errores**; los avisos no fallan (un toolchain ausente en la
  máquina puede vivir en CI). `--json` para consumo programático.

## Qué chequea

| Check | Nivel si falla |
|---|---|
| Python ≥ 3.8 · git en PATH | error |
| Las 6 skills junto al engine, con frontmatter `name:` verificado | error |
| Hook INV-GOLDEN-01: archivo presente · registrado en `settings.json` (PreToolUse) · intérprete powershell/pwsh disponible | aviso (cada capa faltante, con el remedio) |
| `dev-loop.config.json` del cwd: parseable, versión, repos | error si inválido · aviso si ausente |
| ACCEPTANCE del config: criterios + AC-IDs trazables | aviso |
| Skills de QA de `qa_tools_order` (default code-review/judgment-day/improve) presentes en `.claude/skills` del proyecto o del usuario — el loop las orquesta sin traerlas | aviso (las built-in del harness no son detectables por filesystem, y lo dice) |
| Ledger: carga + checksum de integridad (1.13.0) | **error** si corrupto/mutado |
| Toolchain primario por repo type (`mvn`/`pytest`/`npm`/`go`/`cargo`/`dotnet`/`ctest`/`gradlew` del repo/`swift`/`flutter`) | aviso |

## El doctor no solo diagnostica: cura

Cada aviso/error lleva su **remedio accionable** — el comando o el link de
instalación (python.org, git-scm, maven/flutter/nodejs/go/rustup/dotnet/cmake/
gradle/swift, pwsh para el hook en Linux, y los pasos del propio kit para
skills/hook/config faltantes). Espíritu flutter doctor completo: corrés
`doctor`, instalás lo listado, re-corrés hasta verde.

## Hardening (review fresco pre-commit, aplicado)

- `startswith` sin separador final clasificaba `~/.claude/skills-evil/` como
  instalación global → separador + `normcase` (case de drive en Windows).
- El header humano usaba em-dash y el JSON `ensure_ascii=False` — violaba la
  promesa ASCII → header ASCII y `ensure_ascii=True` (el doctor promete bytes
  ASCII SIEMPRE, es la herramienta de primer contacto).
- Detección de registro del hook por substring en la rama PreToolUse: límite
  disclosed en el docstring (falso positivo rebuscado, dirección benigna).

## Notas de plataforma

- Linux: el hook es PowerShell — doctor avisa si no hay `pwsh` (instalarlo o
  portar el twin bash, diferido consciente desde el header del .ps1).
- Windows: junctions de instalación global se atraviesan con normalidad
  (doctor clasifica global vs por-proyecto por el path real del engine).

## Smoke

- **T42**: doctor en sandbox → exit 0 con config y ACCEPTANCE leídos, 6/6
  skills, install clasificada por-proyecto · ledger corrupto → exit 1 (la
  integridad del ledger es error, no aviso).
