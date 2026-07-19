# Loop abierto vs. grafo medido: por qué existe uscha

> El agente ejecuta · el método gobierna · la evidencia decide · el humano aprueba.

Hay dos formas de poner un agente de IA a trabajar sobre código. La diferencia entre
ellas es, literalmente, la razón de ser de uscha.

## Los dos paradigmas

```
        LOOP ABIERTO                          GRAFO MEDIDO
   El agente decide el recorrido        Vos definís los caminos posibles

      INVESTIGA                              REPRODUCIR BUG
         |                                        |
      MODIFICA CODIGO                        ¿LO REPRODUCE? --NO--> PEDIR INFO
         |                                        | SI
      EJECUTA TESTS                          HALLAR CAUSA
         |                                        |
      REVISA RESULTADO                       INTENTAR FIX
         |                                        |
      ¿RESUELTO?                             TESTS
       /      \                                   |
      SI       NO                            ¿PASAN? --NO--> VOLVER A CORREGIR --> (fix)
      |         |                                 | SI
   TERMINA   DECIDE QUE INTENTAR            REVISION
                |                                 |
             INVESTIGA (loop)              ¿APROBADO? --NO--> CORREGIR
                                                  | SI
                                             TERMINA
```

## El pecado del loop abierto

Mirá el rombo de la izquierda: **`REVISA RESULTADO -> ¿RESUELTO?`**.

¿Quién contesta ese "¿resuelto?"? **El agente, evaluándose a sí mismo.** Ese es el agujero
de todo el paradigma de loop abierto: el modelo decide cuándo terminó, *narra* que está
listo, y vos le creés. No hay nada afuera del agente que lo contradiga.

uscha fue diseñado para cerrar exactamente ese agujero. Su doctrina:

- **Lo medido le gana a lo narrado** (*measured beats narrated*).
- **Los hechos bloquean; las conjeturas avisan** (*facts block, guesses advise*).

## uscha ES el grafo — pero con dos vueltas de tuerca

La columna derecha describe casi literalmente el *dev-loop* de uscha:

| Grafo genérico de fix          | uscha                                                              |
| ------------------------------ | ------------------------------------------------------------------ |
| Reproducir bug / ¿lo reproduce?| `regression-capture` / caracterización: reproducir ANTES de tocar |
| Hallar causa -> fix -> tests   | build con los tests como guardrail entre pasos                     |
| ¿Pasan? NO -> volver a corregir| el loop de convergencia **acotado** (no infinito)                  |
| Revisión -> ¿aprobado?         | el QA loop (`code-review` / `judgment-day`) medido por el ledger   |
| ¿Aprobado? SI -> termina       | **la compuerta humana** (merge gate)                               |

Y por encima de ese grafo de fix vive el **macro-grafo de fases** —
`idea -> discovery -> spec -> adr/constitution -> build -> qa loop -> verify -> produccion`—
un FSM derivado que el mirador dibuja como "el sendero".

Usar un grafo no es la novedad; muchos frameworks ya predican "definí el grafo de estados".
Lo propio de uscha son **dos cosas** que el diagrama insinúa pero no dice:

1. **Quién contesta las compuertas.** En el loop abierto, "¿resuelto?" lo contesta el agente.
   En uscha, cada compuerta — `¿pasan?`, `¿aprobado?` — la contesta **evidencia medida**: el
   ledger, los gates, la cobertura, el golden. Se saca el juicio de la cabeza del modelo y se
   lo pone en un artefacto determinista y auditable.

2. **El loop no desaparece: se enjaula.** Sigue existiendo, pero adentro de un nodo del grafo
   (el de convergencia de QA), y es **acotado**: converge, o **escala a un humano** cuando se
   estanca (plateau / stop-signal). Nunca es el "decide qué intentar" que gira para siempre.

## Una honestidad

uscha no es "dibujá cualquier grafo que quieras". Es un **pipeline fijo de fases + loops
acotados adentro + compuertas medidas**. Lo que VOS definís no es la topología, son las
**guardas**: `SPEC.md`, `ACCEPTANCE.md`, `CONSTITUTION.md`, los invariantes. Esos son los
límites que el agente no puede cruzar; el grafo macro ya viene dado.

## La frase que lo cierra

El loop abierto te da un agente que **cree** que terminó.

uscha te da un agente que **no puede terminar** hasta que la evidencia lo habilite y un humano
lo apruebe.

---

*Ver también: el [paper](paper/uscha-paper.pdf) para el desarrollo formal, y
[casos-reales.md](casos-reales.md) para el método aplicado.*
