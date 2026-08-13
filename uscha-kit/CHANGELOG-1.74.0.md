# uscha-kit 1.74.0 — Diamond M4: bootstrap, the identity of a bounded subsystem (2026-08-12)

M4 of the Diamond program, and the first end-to-end run of the whole loop on real Uscha code.
The falsifiable thesis: for a bounded subsystem with a mature canonical package, the
implementation is **not** the unique carrier of the system's identity — independent compilers,
each seeing only the canonical package, produce different code that a **withheld oracle**
(authored first, never shown to the compilers) certifies as the same system.

**The subsystem:** the `INV-GOLDEN-01` PreToolUse guard (`block-approved-writes.py`) — a pure,
fail-closed decision function (`payload → block | allow`) with a sharp, security-relevant
invariant and a standalone shape. "Same behaviour = same system" has teeth here: a guard that
allows one write the original blocks is a different system, measurably.

**The two new organs (subcommands 45–46):**

- `bootstrap-oracle --impl <hook> --oracle <ORACLE.json>` — runs a **withheld** behavioural
  suite against a compiled implementation; exit 0 iff every case matches its expected exit. The
  maker≠checker wall made executable: the oracle predates and is physically separate from every
  compiler input, and the runner consults no model. The oracle's verdict is a `measured` fact,
  so it is *allowed to decide* "same system" (facts decide; it is not an advisory judgment).
- `bootstrap-variance --impls <a> <b> ...` — per-implementation structural metrics (LOC, AST
  nodes, functions, imports) and pairwise divergence, proving the implementations genuinely
  differ. **Advisory evidence, never a gate** — variance proves difference, only the oracle
  certifies sameness.

## The run, and its honest verdict

A tiny public canonical package (SPEC + acceptance + `INV-GOLDEN-01`, `ir-extract`ed into a
pinned 8-node IR) was compiled by **three independent models** (Opus, Sonnet, Haiku) through
the M3 `compile/0.1` contract, blind — each saw only the canonical package, never the original
implementation, never the oracle, never each other. All three `compile-validate`d against the
pinned IR; all three are genuinely different code (110–220 LOC, different imports — Opus reaches
for `shlex`, the others don't).

**Round 1** against the 23-case withheld oracle: Opus 21/23, Sonnet 21/23, Haiku 19/23. The
core finding is a **unanimous convergent divergence**: all three block a `python -c` / `node -e`
inline write to a golden, where the canonical system *allows* it (a documented indirect-write
boundary). Three independent models, reading "fail-closed / when in doubt block", resolved the
canonical package's own tension — its out-of-scope note ("indirect writes are out of reach by
design") versus its default-deny posture — toward the **safer** behaviour. That is not NFR
drift; it is a genuine **S-gap**: the canonical package underdetermined interpreter handling,
and the gap points at *more* safety, not less.

**The S-gap loop (N=2).** The unanimous gap was closed by clarifying the canonical package —
principled, not teaching-to-the-test: the out-of-scope note was made operational (out of scope
= not blocked = allowed), and the pipeline rule was disambiguated. Recompiled blind from the
improved package: **Sonnet converged to 23/23 (oracle green)** — its source grew from 220 to
305 LOC to carry the interpreter-reader logic, the measured cost of closing the S-gap. **Opus's
residual two red cases are a tokenizer artifact, not a semantic gap** (this correction was made
by the independent blind review of `f10b9d1`, which caught a mischaracterization the release
self-review had shipped): Opus-r2 *intends* interpreters as readers, but its shell splitter
treats a bare `(`/`)` as a stage separator, so `shlex` on the oracle's exact quoting isolates a
pseudo-stage whose "verb" is not a known reader and default-deny blocks it — re-quoting the
identical command (outer double quotes) flips the verdict to allow, and Sonnet-r2 is robust to
the same re-quoting. So the semantic gap closed for *both* round-2 compilers; Opus's residual is
a **compiler implementation bug**, not a canonical-package divergence. N=2 stops here.

**Verdict for this subsystem: PARTIAL, boundary drawn.** Three substantially different
implementations behave identically on the core (19–23 of 23 cases); the one semantic divergence
(interpreter handling) closed after the canonical clarification, leaving only Opus-r2's
tokenizer artifact; closing the authoring gap made an independent compiler reconstruct the exact
system. The gap was
**authoring-level, not IR-schema-level**: the IR schema stayed `0.1` (the fix was to the SPEC
prose the compilers read, not to the typed graph). The expected program boundary — functional
identity yes, the rest underdetermined — is borne out and sharpened. And the bootstrap surfaced
a real candidate hardening of the *shipped* hook (three models independently judged blocking
interpreter golden-writes the safer default) — the representation's underdetermination doing its
job.

## What the review caught

The two independent blind judges could not run (API session limit); the adversarial pass was
therefore done inline — a self-review, not the usual independent one, stated plainly. It
reproduced the checks the judges were briefed on and confirmed: the oracle **discriminates**
(degenerate guards — always-allow, always-block, block-on-marker — score 11–12/23, far below
the 21–23 the real compilers reach, so "same system" has teeth); the oracle is **faithful**
(23/23 against the original guard); every number in `BOOTSTRAP-REPORT.md` matches a fresh run
(round-1 21/21/19, round-2 Sonnet 23-green / Opus 21, the variance table); the IR hash is
**identical** across `canonical/` and `canonical-r2/` (the "no IR-schema change" claim holds);
`_run_oracle_case` handles an out-of-contract exit code and a missing `expected_exit` gracefully
(counted as failures, never a crash); and `facts --check` is clean (no truth-pass drift). One
inaccuracy was caught and fixed: the implementations' LOC range was stated as 110–264 where the
three round-1 impls are 110–220 (the 264 was a stale figure; the variance table was always
correct). An independent blind review remains worth running once capacity resets.

**Follow-up (corrected in 1.75.1):** that independent blind review was run against `f10b9d1`. It
confirmed the oracle faithfulness, discrimination (degenerates 11–12/23, a plausible-but-wrong
guard 14/23), report-vs-data, path-traversal containment, and withholding — but caught two
report-honesty defects the inline self-review had missed, both now corrected above: (1) Opus-r2's
residual divergence was described as a designed `-c`/`-e` boundary when it is a **tokenizer
artifact** (re-quoting the same command flips it; Sonnet-r2 is robust); (2) the round-2 winner
(Sonnet-r2) is **305 LOC** — the cost of closing the S-gap — which the report never stated. The
lesson: an inline self-review is not a substitute for an independent one.

`AC-BS-01..06` measured green (T127). Suite: 413 checks; acceptance **98/98** where
`coverage.py` is installed.
