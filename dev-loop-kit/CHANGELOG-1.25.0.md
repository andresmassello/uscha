# dev-loop-kit 1.25.0 — anti-ceremonia: Lean sobre el propio método (2026-07-04)

Origen: el kit llegó a 23 subcomandos, 7 skills, hooks y una CONSTITUTION de 7
invariantes. El riesgo #1 dejó de ser un gate malo — es la **suma** de gates buenos
volviendo `/dev-loop` una auditoría. Eso es *over-processing*, muda de ceremonia
(Poppendieck cap. 4). Este release aplica Lean a la herramienta misma: una
meta-invariante que gobierna qué gate futuro entra, y el cambio de UX que la hace
real — **un veredicto único**. Smoke suite: 148/148.

## Qué hace

- **Meta-invariante "Anti-ceremonia"** (`templates/CONSTITUTION.md`): la prueba ácida
  que TODO gate futuro debe pasar antes de entrar — (1) corre sin que el humano tipee
  nada, (2) habla solo cuando importa, (3) colapsa en `readiness`, (4) un cambio
  trivial lo saltea. Es principio + criterio de review, no un check del engine.
- **Veredicto único en `readiness`** (la regla 3, mecanizada): por default `readiness`
  es UNA pantalla — la línea de veredicto, los warnings condicionales que sí dispararon
  (habla solo cuando importa) y una línea `--- gates:` que **colapsa** cada fact gate
  persistido (`gate:*`, `rubric:grade`, `blocker:*`) en `N ok · M bloqueando
  (repo/gate…)`. `--verbose` abre la tabla de dimensiones, el resumen
  acceptance/coverage/churn y el desglose por repo.
- **`readiness --json`** gana una sección `"gates"` aditiva (la consume sys-doc/CI).

## Decisión de acople: presentación, no re-peso

El rollup **lee hechos ya persistidos en el ledger — jamás recomputa el score**. Un
gate es "bloqueando" sii su último registro gateó ≥1 finding (`gated_reported > 0`),
que es exactamente la señal que ya alimentaba el cap ≤65. Consecuencia dura: el número
de readiness es **idéntico** al de 1.24.0 — el smoke lo prueba (las ~30 aserciones de
readiness previas siguen verdes sin tocarse). No entra como dimensión ponderada: plegar
sub-scores al peso rompería el anti-Goodhart (la dimensión dominante es measured-
acceptance a propósito).

## Qué NO entra (y por qué)

- **Perfiles de riesgo A–E mecanizados**: la regla ácida 4 ("un cambio trivial lo
  saltea") es principio hasta que exista el clasificador. Los perfiles hoy son doctrina
  (CONSTITUTION/SKILL), no máquina — el engine no tiene `--profile`. Mecanizarlos es su
  propio ADR (¿por tamaño de diff? ¿por paths? ¿por declaración?), release aparte.
- **`rebuild` en el rollup**: es eje de completitud (COVERS/PARTIAL/DIVERGE), no un
  gate pass/fail; no tiene `--kind` en `log-gate` y queda fuera a propósito.

## Smoke (T45, 8 checks nuevos)

Ledger fresco aislado: default emite el veredicto y **colapsa** dimensiones y by-repo;
`--verbose` los expande; un `log-gate --kind simplicity --verdict fail` aparece nombrado
en la línea de gates; un grade limpio posterior (latest-wins) la libera; `--json`
expone `gates[]` con `blocking` correcto.

## Límite honesto

El rollup mejora la **legibilidad**, no cambia qué se mide: los mismos hechos, una sola
pantalla. La meta-invariante es disciplina — su valor depende de que se aplique al
admitir cada gate futuro (empezando por `waste-check`, que por eso entrará
advisory-first y default-quiet, no como BLOCKER).
