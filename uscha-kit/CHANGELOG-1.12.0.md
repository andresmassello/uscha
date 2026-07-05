# dev-loop-kit 1.12.0 — secret-scan en gate-check (2026-07-03)

Tercera mejora del backlog PragProg (M8 de `docs/analisis-pragmatic-programmer.md`;
Topic 43 *"Stay Safe Out There — nunca commitear secretos, API keys ni
credenciales"*). Un secreto agregado al diff bloquea como HECHO, exactamente
igual que hoy bloquea borrar tests o bajar thresholds. Python stdlib puro.
Smoke suite: 79/79.

## La idea (facts block, guesses advise — aplicado a secretos)

- **Alta precisión = BLOCKER**: clave privada PEM, AWS access key (`AKIA…`),
  GitHub token (`ghp_`/`github_pat_`), Slack (`xox?-`), Google API key
  (`AIza…`), y archivos contenedores de claves (`.p12/.pfx/.jks/.keystore/.key`)
  agregados o modificados — también en modo binario (línea `Binary files`,
  que no trae `+++`).
- **Genérico = advisory**: literales tipo `password = "…"` y JWTs — en
  fixtures de test abundan placeholders y bloquearlos castigaría escribir
  tests. `--strict` los gatea.
- Solo se escanean líneas **agregadas**: sacar un secreto del código es bueno
  y el diff que lo saca no debe frenarse. Borrar un `.p12` tampoco bloquea
  (el lado `b/` del diff es `/dev/null` y no matchea).

## Engine (qa_ledger.py)

- `_GC_SECRETS_HARD` (lista etiquetada de patrones) + `_GC_SECRET_SOFT` +
  `_GC_KEYFILE`, cableados al loop de `cmd_gate_check`: `secrets_added` suma
  al veredicto hard, `secret_literals` al soft. JSON expone ambos.
- Los patrones no se auto-matchean como source (verificado): después de
  `-----BEGIN ` en el código viene `(?:RSA`, no `PRIVATE KEY`.
- Límite conocido (corner self-hosting): los fixtures del smoke contienen la
  AKIA de ejemplo canónica de AWS — un gate-check del diff del PROPIO kit
  la flaggea. Correcto: el gate no exime archivos de test a propósito
  (un secreto en un test sigue siendo un secreto).

## Smoke

- **T34**: AKIA agregada → BLOCKER · PEM privado → BLOCKER · `.p12` binario
  agregado → BLOCKER · borrado de `.p12` → CLEAN · literal password →
  REVIEW exit 0 / `--strict` exit 1.

## Diferido consciente

- Entropía/base64 genérico (detectores adivinos) NO entra: violaría
  "facts block, guesses advise" — solo patrones con lectura inequívoca
  bloquean. El resto del backlog PragProg sigue en
  `docs/analisis-pragmatic-programmer.md`.
