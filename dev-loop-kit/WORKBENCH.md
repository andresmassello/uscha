# Workbench — armado, verificación y actualización

La capa **genérica** que hace correr la metodología en cualquier proyecto: Claude Code +
Python + git/gh + los skills del kit. Lo **específico de cada stack** (JDK/Maven, MSSQL,
los linters del static gate, drivers) es el *adapter* del proyecto y vive en el
`CLAUDE.md`/`AGENTS.md` de cada repo — **no entra acá**.

> Fuente de los datos de instalación de Claude Code: docs oficiales
> (https://docs.claude.com/en/docs/claude-code/overview). Verificá con `claude doctor`.

---

## 1. Componentes del workbench

| Componente | Para qué | Mínimo |
|---|---|---|
| **Claude Code** | el agente / orquestador | cuenta Pro, Max, Team, Enterprise o Console |
| **Python 3.8+** | corre `qa_ledger.py` (stdlib pura, sin dependencias) | `python3` en PATH |
| **git** | versionado | 2.x, con `user.name`/`user.email` |
| **gh** (GitHub CLI) | crear repo / abrir PR | opcional pero recomendado |
| **skills del kit** | `discovery`, `adr-refine`, `dev-loop`, `sys-doc` | copiados a `~/.claude/skills/` |
| **skills de QA** | `code-review`, `judgment-day`, `improve` | tus skills globales (el dev-loop los **orquesta**, no los trae) |

---

## 2. Instalar Claude Code

**Native installer (recomendado — no requiere Node, se auto-actualiza):**

```bash
# macOS / Linux / WSL
curl -fsSL https://claude.ai/install.sh | bash

# Windows PowerShell
irm https://claude.ai/install.ps1 | iex

# Windows CMD
curl -fsSL https://claude.ai/install.cmd -o install.cmd && install.cmd && del install.cmd

# Homebrew (macOS / Linux)
brew install --cask claude-code
```

**npm (alternativa — requiere Node.js 18+; útil para fijar versión en CI):**

```bash
npm install -g @anthropic-ai/claude-code
# NO usar sudo. Si hay EACCES: nvm, o  npm config set prefix '~/.npm-global'
```

**Login:** ejecutá `claude` y seguí el OAuth del navegador (cuenta con suscripción).
Para headless/servidor: `export ANTHROPIC_API_KEY=...`.

**Windows:** WSL2 es el camino recomendado (instalás y corrés `claude` *dentro* de WSL).
Alternativa: Git for Windows (provee Git Bash para la tool Bash; la tool PowerShell se
habilita con `CLAUDE_CODE_USE_POWERSHELL_TOOL=1`).

**Verificar:** `claude --version` y `claude doctor`.

---

## 3. Python (para el ledger)

`qa_ledger.py` usa **solo la librería estándar**, Python 3.8+. No hay `pip` ni venv.

- **Linux/macOS:** suele venir `python3`. Verificá `python3 --version`; si falta, instalá
  con el gestor del SO (`apt`, `brew`, etc.).
- **Windows nativo:** no existe `python3` por defecto. Dos opciones:
  1. **WSL2** (recomendado): adentro `python3` existe.
  2. **Python de python.org** + shim. En PowerShell:
     ```powershell
     '@py -3 %*' | Out-File -Encoding ascii "$env:USERPROFILE\.local\bin\python3.cmd"
     ```
     y agregá esa carpeta al `PATH`.

---

## 4. git + gh

```bash
git config --global user.name  "Tu Nombre"
git config --global user.email "tu@mail.com"
gh auth login          # habilita gh repo create / gh pr
```

---

## 5. Instalar los skills del kit

**Global (todos los repos):**

```bash
mkdir -p ~/.claude/skills
cp -r dev-loop-kit/.claude/skills/* ~/.claude/skills/
# Windows:  %USERPROFILE%\.claude\skills\
```

**Per-repo (solo este repo):**

```bash
cp -r dev-loop-kit/.claude/skills  <repo>/.claude/
cp dev-loop-kit/dev-loop.config.json  <repo>/      # config en la raíz del repo
```

**Verificar:** abrí `claude` y mirá `/help` — deberían aparecer `/discovery`,
`/adr-refine`, `/dev-loop`, `/sys-doc`. O `ls ~/.claude/skills`.

---

## 6. Los skills de QA externos (dependencia)

El `dev-loop` **orquesta** `code-review` / `judgment-day` / `improve` — **no los empaqueta**.
Tienen que estar en `~/.claude/skills/` (tus skills globales). Si usás otros nombres,
editá `qa_tools_order` en `dev-loop.config.json`. Si no los tenés, el loop no encuentra
las tools de juicio (igual corre el static gate determinístico).

---

## 7. Permisos (settings.local.json)

Para que el loop no frene pidiendo permiso en cada comando, configurá
`<repo>/.claude/settings.local.json` con lo que aceptes ejecutar, por ejemplo:

```json
{ "permissions": { "allow": [ "Bash(python3:*)", "Bash(git:*)", "Bash(gh:*)" ] } }
```

Granular o con wildcards, según tu confianza en el repo.

---

## 8. Qué NO entra acá (adapter por proyecto)

JDK/Maven, MSSQL y drivers, los linters del static gate (Checkstyle/PMD/SpotBugs/
FindSecBugs), Node del app, etc. Eso es el *adapter* del stack y se documenta en el
`CLAUDE.md`/`AGENTS.md` de cada repo. El workbench es lo que **no** cambia entre proyectos.

---

## 9. Cómo sé qué tengo (doctor)

```bash
bash dev-loop-kit/workbench-doctor.sh
```

Reporta: versión del kit, Claude Code, Python, git, gh, Node (si aplica), y qué skills
están instalados en `~/.claude/skills/`. Complementá con la salud nativa:

```bash
claude --version        # versión instalada
claude doctor           # diagnóstico de instalación/config
claude whoami           # cuenta autenticada
```

---

## 10. Cómo actualizo el workbench

- **Claude Code:** el native installer se auto-actualiza en background. Forzar ya:
  `claude update`. Homebrew/WinGet/Linux pkg: actualización manual. npm:
  `npm update -g @anthropic-ai/claude-code` (o `@latest`). Controlar el auto-update:
  `DISABLE_AUTOUPDATER` / `DISABLE_UPDATES` en el `env` de `settings.json`.
- **Skills del kit:** re-copiá la versión nueva a `~/.claude/skills/` (o `git pull` si lo
  tenés en repo). Mirá `VERSION` para saber qué versión del kit corrés.
- **Python / git / gh:** gestor del SO o nvm.
- **Después de cualquier update:** corré `workbench-doctor.sh` otra vez.

---

## Checklist mínimo

- [ ] `claude --version` OK y `claude doctor` sin errores
- [ ] `python3 --version` ≥ 3.8
- [ ] git configurado (`user.name` / `user.email`)
- [ ] `gh auth login` hecho (si vas a abrir PRs)
- [ ] `/discovery` `/adr-refine` `/dev-loop` `/sys-doc` aparecen en `/help`
- [ ] `code-review` / `judgment-day` / `improve` presentes (o `qa_tools_order` ajustado)
- [ ] `dev-loop.config.json` en la raíz del repo
