# Open loop vs. measured graph: why uscha exists

> The agent executes · the method governs · evidence decides · the human approves.

There are two ways to put an AI agent to work on code. The difference between them is,
literally, uscha's reason for being.

## The two paradigms

```
        OPEN LOOP                             MEASURED GRAPH
   The agent decides the path            You define the possible paths

      INVESTIGATE                            REPRODUCE BUG
         |                                        |
      MODIFY CODE                            REPRODUCED? --NO--> ASK FOR INFO
         |                                        | YES
      RUN TESTS                              FIND ROOT CAUSE
         |                                        |
      REVIEW RESULT                          ATTEMPT FIX
         |                                        |
      RESOLVED?                              TESTS
       /      \                                   |
      YES      NO                            PASS? --NO--> FIX AGAIN --> (fix)
      |         |                                 | YES
    DONE     DECIDE WHAT TO TRY            REVIEW
                |                                 |
            INVESTIGATE (loop)            APPROVED? --NO--> CORRECT
                                                  | YES
                                             DONE
```

## The sin of the open loop

Look at the diamond on the left: **`REVIEW RESULT -> RESOLVED?`**.

Who answers that "resolved?" **The agent, judging itself.** That is the hole at the center of
the whole open-loop paradigm: the model decides when it is finished, *narrates* that it is
done, and you believe it. Nothing outside the agent can contradict it.

uscha was designed to close exactly that hole. Its doctrine:

- **Measured beats narrated.**
- **Facts block, guesses advise.**

## uscha IS the graph — but with two twists

The right-hand column describes uscha's dev-loop almost literally:

| Generic fix graph            | uscha                                                            |
| ---------------------------- | ---------------------------------------------------------------- |
| Reproduce bug / reproduced?  | `regression-capture` / characterization: reproduce BEFORE touching |
| Root cause -> fix -> tests   | build with tests as the guardrail between passes                 |
| Pass? NO -> fix again        | the **bounded** convergence loop (not infinite)                  |
| Review -> approved?          | the QA loop (`code-review` / `judgment-day`), measured by the ledger |
| Approved? YES -> done        | **the human gate** (merge gate)                                  |

And above that fix graph lives the **macro-graph of phases** —
`idea -> discovery -> spec -> adr/constitution -> build -> qa loop -> verify -> production` —
a derived FSM that the mirador draws as "the trail".

Using a graph is not the novelty; plenty of frameworks already preach "define the state graph".
What is uscha's own are **two things** the diagram hints at but does not say:

1. **Who answers the gates.** In the open loop, "resolved?" is answered by the agent. In uscha,
   every gate — `pass?`, `approved?` — is answered by **measured evidence**: the ledger, the
   gates, coverage, the golden suite. The judgment is taken out of the model's head and put
   into a deterministic, auditable artifact.

2. **The loop does not vanish: it is caged.** It still exists, but inside a graph node (the QA
   convergence node), and it is **bounded**: it converges, or it **escalates to a human** when
   it stalls (plateau / stop-signal). It is never the "decide what to try" that spins forever.

## One honest caveat

uscha is not "draw whatever graph you like". It is a **fixed pipeline of phases + bounded loops
inside + measured gates**. What YOU define is not the topology, it is the **guardrails**:
`SPEC.md`, `ACCEPTANCE.md`, `CONSTITUTION.md`, the invariants. Those are the limits the agent
cannot cross; the macro-graph is given.

## The line that sums it up

The open loop gives you an agent that **believes** it is finished.

uscha gives you an agent that **cannot finish** until the evidence permits it and a human
approves it.

---

*See also: the [paper](paper/uscha-paper.pdf) for the formal treatment, and
[casos-reales.md](casos-reales.md) for the method applied.*
