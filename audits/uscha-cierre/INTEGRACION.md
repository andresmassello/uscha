# uscha-cierre -- lo que SI va a uscha (INV-T1 + Esceptico)

Destilado del diseño del tribunal (SPEC-TRIBUNAL-01): esta es la parte con
relacion valor/peso alta. El tribunal completo queda en incubadora hasta que
EVAL-F0 tenga datos.

## Contenido

| Pieza | Que es | Costo para el usuario |
|---|---|---|
| `scripts/evidencia.sh` | Sella EVIDENCIA.md: commit_sha + diff_sha256 + hash de cada log de respaldo. Rechaza working tree sucio | 0 comandos nuevos: lo invoca el loop al final de los gates |
| `scripts/check-terminado.sh` | El enforcement de INV-T1: recomputa y rechaza TERMINADO si el sello es stale, el diff divergio, o un log fue alterado/borrado | 0: es el guard del KPI TERMINADO |
| `ESCEPTICO.md` | Prompt de auditoria de claims (1 llamada LLM, opcional). Output markdown corto | 0 comandos; 1 llamada al modelo si esta habilitado |

## El invariante

> **INV-T1**: TERMINADO exige EVIDENCIA.md cuyo commit_sha y diff_sha256
> coincidan con el estado actual, con todos los archivos de respaldo intactos.
> Evidencia stale, alterada o ausente = no hay TERMINADO.

Cierra tres agujeros concretos: (1) "tests pass" de una corrida vieja,
(2) codigo tocado despues de la revision, (3) logs intercambiados o editados.

## Cableado al loop (sin comandos nuevos)

```
gates verdes
    -> evidencia.sh -b <tag-anterior> logs/gate-*.log     # sella
    -> [opcional] ESCEPTICO.md sobre claims + EVIDENCIA   # audita
    -> check-terminado.sh && declarar TERMINADO           # enforcement
```

En el SKILL/CLAUDE.md del proyecto alcanza con una linea:
"Antes de declarar TERMINADO: correr scripts/check-terminado.sh; si falla,
resellar con evidencia.sh sobre el estado actual y adjuntar el motivo."

## Lo que NO entra (y por que queda registrado)

- Tribunal de 4 jueces, severidades, dismissals, ratchet: en incubadora
  (`uscha-tribunal.zip`) hasta correr EVAL-F0. Institucionalizar la version
  cara sin evidencia contradiria el propio kit.
- Bypass por tamanio de diff: prohibido por diseño (loophole de fetear
  entregas). El opt-out honesto es por proyecto y explicito.

## Verificado (2026-08-18)

shellcheck -s sh y checkbashisms: limpios (scripts y suite). Suite funcional:
11/11 bajo sh y bajo dash (test/suite-cierre.sh, autocontenida). La suite cazo
2 bugs pre-release: auto-referencia del sello y colapso de dirs untracked en
porcelain (fix: -uall). ESCEPTICO.md sin calibrar contra corridas reales: es
hipotesis hasta que lo uses.
