# CLAUDE.md — SpecLoop (desarrollo del método y del kit)

Este repo es el **hogar del proyecto spec-loop**: el source del `dev-loop-kit` y sus
artefactos de documentación. Acá se desarrolla EL MÉTODO — y el método se aplica a sí
mismo.

## Reglas del repo

1. **El source canónico del kit es `dev-loop-kit/`.** Los zips en Downloads son builds;
   los docs en Downloads son snapshots. Ante conflicto, gana este repo.
2. **Truth-pass obligatorio**: ningún doc de `docs/` puede afirmar algo que
   `dev-loop-kit/.claude/skills/specloop-devloop/qa_ledger.py` no haga. Si cambiás el engine,
   actualizás los docs en el MISMO cambio (o marcás el claim como `propuesta`).
   *Under-claim, then wire, then re-claim.*
3. **Los gemelos van juntos**: cada doc ES tiene su -EN. Un edit en uno exige el edit
   equivalente en el otro.
4. **Cero referencias a proyectos/clientes**: el kit y los docs son genéricos
   (repos de ejemplo: `backend-api`/`mobile-app`). Verificar con grep antes de commitear
   (ojo: `rg` necesita `--hidden` para ver `.claude/`).
5. **Cambios al engine llevan smoke test**: `bash dev-loop-kit/tests/smoke-engine.sh`
   tiene que salir 0 ANTES de commitear cualquier cambio a `qa_ledger.py`. Si el cambio
   agrega comportamiento, se agrega su check a la suite en el mismo commit.
6. **Versionado**: bump de `VERSION` + `dev-loop.config.json` + `CHANGELOG-X.Y.Z.md`
   en el mismo commit. Los tres tienen que coincidir.
7. **Commits convencionales** (`feat:`, `fix:`, `docs:`…), chicos y atómicos.
8. **INV-GOLDEN-01 rige acá también**: nunca escribir/renombrar un `.approved`
   (el hook del kit aplica sobre este repo como sobre cualquier otro).

## Gotchas conocidos

- Los PNG de `docs/` se regeneran desde `docs/diagram-sources/*.html` con Edge headless
  (`--force-device-scale-factor=2`) + autocrop PIL (el render corta ~70px abajo si la
  ventana queda corta).
- Los decks HTML son paginados por JS (`querySelectorAll('.slide')`): insertar una
  `<section class="slide">` se auto-integra a la navegación; los deep-links `#NN`
  corren al insertar slides.
- PowerShell 5.1 rompe con em-dashes/emoji en `.ps1` — el hook se mantiene ASCII.

> La herramienta ejecuta · el método gobierna · la evidencia decide · el humano aprueba.
