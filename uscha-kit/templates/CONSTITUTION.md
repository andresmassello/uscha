# CONSTITUTION.md — project invariants (Uscha)

The layer **above the ADRs**. It records what **no ADR or SPEC may violate**,
whatever trade-off wins. An ADR *chooses* between alternatives; the CONSTITUTION *forbids*.

> Truth hierarchy: **SPEC** = what must happen · **ADR** = why this shape ·
> **CONSTITUTION** = what is never acceptable.

Versioned, one per project. `/uscha-discovery`, `/uscha-adr-refine` and `/uscha-devloop` read it **before**
proposing or touching anything. A violation is a **BLOCKER** finding (non-negotiable): the agent
MUST record it — `qa_ledger.py flag-blocker --kind constitution` — and once recorded it
blocks convergence and caps readiness ≤65 until `--resolve` (a human decision). The engine
does not read this file: the obligation to detect and record the violation belongs to the agent/human;
enforcing the record is the engine's job. It is never resolved by "working around it" in code.

## Security (non-negotiable)

- [ ] Secrets never in logs or in the repo            <!-- CWE-532 / CWE-798 -->
- [ ] Every external input validated before use      <!-- CWE-20 -->
- [ ] Only parameterized SQL, never concatenated        <!-- CWE-89 -->
- [ ] Credentials / certificates encrypted at rest
- [ ] Never cross environments or credentials (dev / prod)

## Domain (TO COMPLETE per project)

> Business rules that can never be broken. Examples (replace with those of your domain):

- [ ] Mandatory idempotency on critical operations
- [ ] Sequential numbering with no logical gaps
- [ ] Exactness to the cent; never two effects for the same `requestId`

## Operation (non-negotiable)

- [ ] No destructive migration without an explicit rollback
- [ ] No automatic merge or release — human gate always
- [ ] Evidence captured by execution, never narrated

## Simplicity — "Reduce" (non-negotiable)

> Maeda's law 1 and Karpathy's "Simplicity First", made a deterministic gate.
> It is not CC by AST: they are measurable *proxies* over the diff. Measured by
> `qa_ledger.py simplicity-check`; an **OVERBUILT** verdict is a **BLOCKER** finding.

- [ ] Minimal code that solves what was asked — no unrequested features, layers or "flexibility" <!-- YAGNI / speculative generality -->
- [ ] No speculative abstractions — every new type/layer is justified against the SPEC <!-- YAGNI -->
- [ ] Bounded nesting — flatten with guard clauses / extract function <!-- CWE-1124 -->
- [ ] Change bounded to the budget (`defaults.simplicity`) — subtract before adding
- [ ] "Would a senior say this is overbuilt?" If yes, it is trimmed before converging

## Reuse — "REUSE-FIRST" (principle; the proxy ADVISES, gates if declared)

> Waste of duplication (Poppendieck ch. 4): AI code reinvents instead of reusing
> (GitClear *Maintainability Gap*: +81% duplication since 2023). `simplicity-check`
> does NOT see it — it scores the diff in ISOLATION, never against what already exists. Measured by
> `qa_ledger.py waste-check` (Type-1/2 clones of the diff vs the repo). The FACT —a block
> of 5+ lines already exists at `file:line`— is measured; the "wasteful" VERDICT is a
> heuristic with known false positives (boilerplate, DTOs, embedded SQL/JSON), so
> it **advises by default** and gates ONLY with `defaults.waste.gate: true` or `--gate`
> (provenance: the committed config IS the declaration). CWE-1041 / DRY.

- [ ] Don't reimplement what already exists in the repo — reuse before cloning
- [ ] Duplication within the change bounded — extract a helper before cloning
- [ ] A WASTEFUL, if the human declared the gate, is reused/refactored, not converged

## Effective tests — "coverage lies" (non-negotiable)

> Coverage says the line *ran*; not that a test *verifies* it. Effectiveness is
> measured with mutation testing (PIT): if mutating the code doesn't break the test, the test
> doesn't assert. Measured by `qa_ledger.py pit-check` over `mutations.xml`.

- [ ] Tests ASSERT behavior, not just execute code <!-- assertion-gap -->
- [ ] Test-strength above the gate (`--min-score`) in the touched area
- [ ] Zero live mutants in domain logic / critical path without explicit justification
- [ ] High coverage with live mutants = false safety; the gap is closed, not ignored

## Gate integrity — "don't game the meter" (non-negotiable)

> A maker-optimizer takes the cheapest path to "green", and editing the gate is usually
> the cheapest. The apparatus that measures correctness is NOT modified by the change that it measures,
> without explicit human sign-off. (Osmani lists the red-flags; the rule is the kit's synthesis.)

- [ ] The change does not weaken the gate: no deleting or skipping tests, no disabling lint, no lowering thresholds
- [ ] Mass rewrite of existing asserts = flag (the safety net edited to accept what is broken)
- [ ] No new helper duplicating an existing one <!-- reuse / Reduce -->
- [ ] High blast-radius: the checker is uncorrelated with the maker (another family/profile); the loop that produced the change is not its only approver
- [ ] Test diffs are read more strictly than production ones

## Golden — pre-change behavior (non-negotiable)

> **INV-GOLDEN-01.** In migrations/modernizations, no module enters the change phase without
> a golden suite captured and committed over its PRE-change behavior. The golden is captured by
> a script running the ORIGINAL code with real inputs; the agent **NEVER** generates or edits
> the `.approved` files — it is the one piece the agent cannot author, and that is its reason to exist.
> **CWE-440** (Expected Behavior Violation).

- [ ] Migration: golden suite captured + committed BEFORE touching the module
- [ ] The `.approved` files are field truth; approved by a HUMAN, never by the agent
- [ ] `golden-diff` clean (byte for byte) = hard closing condition of the touched module
- [ ] Corpus documented; a module with insufficient corpus = PARTIAL, never COVERS

## Stack lifecycle — the stack expires (non-negotiable)

> A major version is a family; support is granted to a MINOR line, for a window, by an upstream
> nobody here controls. A stack ADR that fixes a version without its end-of-support date has not
> decided anything — it has deferred the decision to the week before go-live (ADR-040).
> Measured — ADVISORY, never a gate — by `qa_ledger.py spec-check`'s lifecycle dimension.

- [ ] No stack ADR without a cited end-of-support date for every component it fixes <!-- ADR-040 -->
- [ ] The date comes from the OFFICIAL source, fetched when asked, with the URL and the day checked recorded — never from memory
- [ ] No component whose support ends before the declared `go_live` enters the build; the upgrade happens BEFORE, not days after

## Anti-ceremony — Lean over the method itself (meta-invariant)

> The risk is not a bad gate: it is the **sum** of good gates turning `/uscha-devloop` into an
> audit. That is *over-processing* — the waste of ceremony (Poppendieck ch. 4). It applies to the
> tool, not the code: if a step does not add value **for the human**, it is waste.
> It is a **meta-invariant** — the criterion that EVERY future gate must pass before entering.
> Today only rule 3 is mechanized (the single verdict of `readiness`, kit 1.25.0); the
> rest is design discipline and review judgment, not something the engine checks.

- [ ] **Runs without the human typing anything** — a script/agent autocompletes it; no routine forms
- [ ] **Speaks only when it matters** — a failure, or a high-risk profile; if it always speaks, it is silenced by default
- [ ] **Collapses into `readiness`** — one number + one line, not another screen (`--verbose` opens the detail)
- [ ] **A trivial change skips it** — gated by risk profile <!-- principle: profiles A–E are NOT mechanized in the engine, by design -- the paragraph above says why: this is design discipline and review judgment, not a check -->

## How it is enforced

- `/uscha-discovery` and `/uscha-adr-refine` read it and derive the **severity gate** from here (the
  "inviolable constraints" step). Each invariant carries, where it maps, a CWE reference.
- `/uscha-devloop` consults it before touching a governed area; a violation is recorded with
  `qa_ledger.py flag-blocker --kind constitution --note "<invariant>"` and enters the ledger
  as a **BLOCKER** finding (readiness cap ≤ 65, blocks convergence until `--resolve`).
  Detecting it is the agent/human's obligation; once recorded, enforcement is the engine's.
- The **Simplicity** invariant is measured without human judgment: `qa_ledger.py simplicity-check`
  scores the diff (minimality, nesting, abstraction) and returns `SIMPLE / ACCEPTABLE /
  OVERBUILT`. **OVERBUILT** = BLOCKER (exit 1): it is trimmed, not converged.
- The **Reuse (REUSE-FIRST)** invariant is measured by `qa_ledger.py waste-check`: Type-1/2 clones
  of the diff vs the repo (`dup_vs_repo` is the dominant signal). **Advisory by default** (advises
  with `file:line` to reuse, exit 0); with `defaults.waste.gate: true` or `--gate` a
  **WASTEFUL** is exit 1 and is persisted with `log-gate --kind waste --verdict fail` (readiness
  cap ≤ 65, blocks convergence). An honest Type-1/2 proxy, never semantic nor by AST.
- The **Effective tests** invariant is measured with `qa_ledger.py pit-check`: if the mutation
  score falls below the gate or mutants survive on the critical path, it is a **BLOCKER** finding —
  green coverage is not enough. Expensive → *scheduled / incremental* tier, not in the inner loop.
- The **Gate integrity** invariant is measured by `qa_ledger.py gate-check`: deleted or
  disabled tests and lowered thresholds = **BLOCKER** (exit 1); lint suppressions, removed
  asserts and **new dependencies** (the "0 deps without approval" rule, made visible —
  kit 1.30.0) = review (or `--strict`). For high blast-radius a checker
  uncorrelated with the maker (different family/profile) is also required — that is process, not code.
- The **Golden (INV-GOLDEN-01)** invariant is measured by `qa_ledger.py golden-diff`: any `.received`
  that does not match its `.approved` (or is unapproved) = **DIVERGE**, cutting the chain before judgment-day.
  The agent does not touch `.approved` (ideally a `PreToolUse` hook makes it impossible).
- The **Stack lifecycle** invariant is measured by `qa_ledger.py spec-check`: each `lifecycle:`
  entry in `docs/adr/*.md` is compared against the SPEC's `go_live` and reads `ok` / `expires
  before go-live` / `no EOL cited` / `no source cited`, with the whole dimension UNMEASURED (and
  the reason named) when nothing declares it. **Advisory** — it never gates and never caps
  readiness: the engine can see that a date was CITED, never that the citation is true. Verifying
  the source is the human's job; the record makes the omission visible.
- The **Anti-ceremony** meta-invariant is not measured by any subcommand: it is the admission filter
  for new gates (does it autorun? does it stay quiet except when it matters? does it collapse into `readiness`? does a
  trivial change skip it?). Its only mechanized leg today is the single verdict of `readiness` (kit
  1.25.0): persisted gates are shown collapsed on one line by default and are opened with
  `--verbose`. A gate that does not pass the four questions does not enter the kit — the reason is documented.
- **An ADR that contradicts the CONSTITUTION is not valid**: it is escalated, not approved. If a
  decision would need to violate an invariant, changing the CONSTITUTION is discussed first
  (an explicit human decision), never "worked around" silently.
