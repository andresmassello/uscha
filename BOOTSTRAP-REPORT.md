# BOOTSTRAP-REPORT — Diamond M4 v0.1

**Subsystem:** the `INV-GOLDEN-01` PreToolUse guard (`uscha-kit/hooks/block-approved-writes.py`).
**Contract:** `ADR-017`. **Compile interface:** M3 `compile/0.1` (`ADR-016`).
**Fixtures (all in-repo):** `uscha-kit/tests/fixtures/bootstrap-golden-hook/`.

> Truth-pass: every number below is produced by `qa_ledger.py bootstrap-oracle` /
> `bootstrap-variance` / `compile-validate` over the committed fixtures. Reproduce with
> `bash uscha-kit/tests/smoke-engine.sh` (T127) or the commands named in each section.

## Setup

- **Canonical package** (`canonical/`): a SPEC + 7 acceptance items (`AC-GH-01..07`) + the
  governing `INV-GOLDEN-01`, describing the guard's required behaviour with no implementation
  and no test case. `ir-extract`ed into a pinned 8-node IR (`IR.json`, seal `5cce7866…`,
  UNTYPED rate 0.00).
- **Withheld oracle** (`oracle/ORACLE.json`): 23 behavioural cases `{payload, expected_exit}`,
  hand-authored from the canonical system's actual behaviour **before any compilation** and
  **never included in any compiler input**. Faithful to the canonical system: `bootstrap-oracle`
  against the original guard is **23/23 green**.
- **Compilers:** three independent models — **Opus, Sonnet, Haiku** — each compiling the
  canonical package **blind** through `compile/0.1`. No compiler saw the original implementation,
  the oracle, or another compiler's output (asserted mechanically, AC-BS-03).

## Round 1 — oracle results

| Compiler | Oracle | Failing cases |
|----------|--------|---------------|
| Opus     | **21 / 23** | `bash-python-inline-writes-golden`, `bash-node-inline-writes-golden` |
| Sonnet   | **21 / 23** | `bash-python-inline-writes-golden`, `bash-node-inline-writes-golden` |
| Haiku    | **19 / 23** | the two interpreter cases + `bash-diff-reads-goldens`, `bash-reader-pipeline-no-write` |

All three `compile-validate` against the pinned IR (AC-BS-04).

## Variance — the implementations genuinely differ

`bootstrap-variance` over the three round-1 sources:

| Impl | LOC | AST nodes | functions | imports |
|------|-----|-----------|-----------|---------|
| Opus   | 182 | 834 | 7 | json, re, shlex, sys |
| Sonnet | 220 | 998 | 8 | json, re, sys |
| Haiku  | 110 | 541 | 5 | json, sys |

Pairwise: all **distinct** (no byte-identical pair); import Jaccard 0.50–0.75; LOC deltas
38–110. Advisory — variance proves difference; it never certifies "same system" and never
gates. (The heavier reverse-discovery→fidelity-vector-per-compiler arm of the protocol is
folded into this structural variance for v0.1: oracle + variance together answer the thesis for
this subsystem; a full per-compiler fidelity vector is deferred to M5's cross-archetype bench,
where it earns its machinery. Named, not silently dropped.)

## S-gap catalog (measured)

- **S-GAP-01 — interpreter handling (unanimous, 3/3).** An interpreter verb (`python`, `node`)
  invoked with no redirection or write flag: the canonical system treats it as a reader and
  **allows** it (a documented indirect-write boundary — the byte-level control is `golden-diff`);
  all three compilers, reading "fail-closed / when in doubt block", **blocked** it. The canonical
  package underdetermined the allow/block decision for opaque interpreters, its out-of-scope note
  in tension with its default-deny posture.
- **S-GAP-02 — reader pipelines (Haiku).** `cat x.approved | grep foo` — allowed by the
  canonical system; Haiku blocked all pipelines mentioning the marker ("do not parse pipelines").
- **S-GAP-03 — the reader verb set (Haiku).** `diff a.approved b.received` — a reader; Haiku's
  reader allowlist omitted `diff`. The canonical package names the *category*, not the members.

## The loop (N = 2)

The unanimous **S-GAP-01** was closed by clarifying the canonical package (`canonical-r2/`) —
principled, not teaching-to-the-test: the out-of-scope note was made operational (out of scope =
not blocked = allowed) and the pipeline rule disambiguated. Recompiled **blind** from the
improved package:

| Compiler (round 2) | Oracle | Outcome |
|--------------------|--------|---------|
| Sonnet | **23 / 23 — GREEN** | the gap **closed**: an independent compiler reconstructed the exact system (its source grew from 220 to 305 LOC to carry the interpreter-reader logic — the measured cost of closing the S-gap) |
| Opus   | **21 / 23** | the S-gap **closed semantically** — Opus-r2 intends interpreters as readers — but a **tokenizer artifact** leaves the same two cases red: its shell splitter treats a bare `(`/`)` as a stage separator, so `shlex` on the oracle's exact quoting isolates a pseudo-stage whose "verb" is not a known reader and default-deny blocks it. It is **not** a designed `-c`/`-e` boundary: re-quoting the identical command (`python -c "open('x.approved','w')…"` with outer double quotes) flips the verdict to allow. Sonnet-r2 is robust to the same re-quoting |

**Trajectory (corrected by the independent blind review of `f10b9d1`, which caught the
mischaracterization the release self-review had shipped):** 3/3 diverge → one clarification →
the semantic gap closes for both round-2 compilers; Sonnet is oracle-green, Opus's residual two
cases are a punctuation-tokenizer artifact in its own shell splitter (trivially flipped by
re-quoting), not a semantic divergence. Bounded at N=2, the residual is a **compiler
implementation bug**, not a canonical-package gap — reported, not chased.

**IR schema impact:** none. The S-gap was **authoring-level** — the fix was to the SPEC prose
the compilers read, not to the typed graph. The IR schema stayed `0.1` (the AC/INV node set was
unchanged, so the pinned IR hash is identical across rounds). An honest finding in its own right:
this subsystem's gap did not force IR v0.2.

## Verdict

**PARTIAL — boundary drawn.** Three substantially different implementations (round 1: 110–220
LOC; the round-2 winner that reached 23/23 is 305 LOC — different dependency sets throughout)
behave **identically on 19–23 of 23** behavioural cases — functional identity on the core of a
security-relevant guard, certified by evidence the compilers never saw. The one semantic
divergence — interpreter handling — **closed** for both round-2 compilers after the canonical
clarification; Sonnet-r2 is oracle-green, and Opus-r2's residual two red cases are a
punctuation-tokenizer artifact in its own shell splitter (not a semantic gap — re-quoting the
identical command flips them). The expected program boundary — functional identity yes, the rest
underdetermined — is borne out, and the one residual is now correctly attributed to a compiler
bug rather than to the canonical package.

Two program-level results fall out, both honest, both publishable:

1. The canonical package's underdetermination **surfaced a real candidate hardening of the
   shipped guard**: three independent models judged blocking interpreter golden-writes the safer
   default. The representation doing its job — the S-gap is a to-do for the canonical layer, not
   a defect in the experiment.
2. **Convergence was not manufactured.** Variance confirms the implementations genuinely differ;
   the oracle, withheld, is the only arbiter of sameness; the loop is bounded so the canonical
   package cannot be over-fit into a disguised implementation. A partial result, reported as
   partial.
