# CHANGELOG 1.36.0 — discovery intake: production findings + spec-doubt

## La idea

Uscha no puede terminar en el merge si la realidad vuelve con evidencia. Dos señales antes quedaban fuera del ledger: un bug encontrado en producción y una SPEC que el builder descubre dudosa o equivocada. Este release les da una entrada formal al siguiente ciclo de discovery.

## Nuevo

- `qa_ledger.py production-finding`:
  - crea `PF-001`, `PF-002`, ... con `repo`, `severity`, `source`, `title`, `evidence`.
  - `--resolve --id PF-001 --note "..."` registra que el hallazgo entró al próximo ciclo.
- `qa_ledger.py spec-doubt`:
  - crea `SD-001`, `SD-002`, ... con `kind` (`spec-doubt`, `spec-wrong`, `ambiguous`, `missing-acceptance`), `repo`, `severity`, `note`, `evidence`.
  - `--resolve --id SD-001 --decision "SPEC amended"` registra la revisión humana.
- `readiness --json` agrega `discovery_intake` y facts:
  - `production_findings_open`
  - `spec_doubts_open`
- La vista default de `readiness` habla solo cuando importa: imprime una línea si hay production findings o spec-doubts abiertos.
- `phase` deriva `escalated` si hay `spec-doubt` abierto o production finding gateado abierto; no hay `pr-ready` mientras la SPEC esté dudosa o la producción haya devuelto una señal severa.
- `dashboard --json` transporta `discovery_intake` para Mirador/adapters.

## Doctrina

- Production finding = hecho de campo. Entra al ledger, no a una nota perdida.
- SPEC-WRONG/spec-doubt = escape hatch legítimo del builder. El agente NO decide silenciosamente entre desviarse de la SPEC o transcribir una mentira.
- Resolver exige un acto registrado: feedback incorporado, SPEC amendada, o revisión humana explícita.

## Smoke

- `bash uscha-kit/tests/smoke-engine.sh`: 207 ok / 0 fail.
- Nuevos checks:
  - T60: production finding crea PF-001, aparece en `discovery_intake`, avisa en readiness default, y se limpia al resolver.
  - T61: spec-doubt crea SD-001, aparece en `discovery_intake`, `phase` deriva `escalated`, y se limpia al resolver.
