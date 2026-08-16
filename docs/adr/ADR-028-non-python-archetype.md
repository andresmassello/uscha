---
governs:
  - uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py
  - uscha-kit/tests/fixtures/diamond-bench/*/
---
# ADR-028: The method leaves Python — a JavaScript archetype enters the bench, with the runner routed by extension, structural metrics that are honest about what a stdlib engine can see, and the static surface produced by the target's own parser (bench-js v0.1)

## Status: Accepted

## Context
Every instrument in the Diamond program is Python-only at four points: the withheld-oracle
runner invokes `sys.executable <impl>`; `_impl_metrics` (the structural-distance input for
inter/intra variance) uses `ast.parse`; `_extract_static_py` (the reverse-discovery organ that
feeds `static_surface` and curation) filters `.py`; the degenerate-stub discovery looks for
`.py`. So the program's central claim — *implementation replaceability certified by a withheld
oracle* — has only ever been demonstrated for one language, and the reader is entitled to ask
whether that is a property of the method or of Python.

The engine is stdlib-only by design (CONSTITUTION). A JavaScript parser is not in Python's
stdlib. Two honest options: (a) parse JS with a regex heuristic — a narrated AST, exactly the
kind of number the method forbids; (b) delegate JS structure to JS itself: Node ships
`acorn`? No — Node ships no parser module either, but Node's `vm`/`Function` can *load* code
and the V8 engine can *report the module's own exports*. What Node CAN do without any
dependency: execute the impl (the oracle runner), and evaluate `Object.keys(module.exports)`
plus a token-level scan that Node itself performs. What it cannot do stdlib-only: a real AST
node count. So the structural metric for JS is **declared narrower** than for Python, and the
report says so.

## Decision
- **Runner routed by extension** — `_run_oracle_case` picks the interpreter from the impl's
  extension: `.py` → `sys.executable` (unchanged), `.js` → `node` (resolved from PATH; absent
  node ⇒ the entry's oracle is UNMEASURED with the reason named, never a fake red or green).
  The bench already requires Node ≥ 18 in CI (the npm-router tests) — the instrument the
  program already trusts.
- **JS structural metrics, honestly narrower** — `_impl_metrics` for `.js`: `loc` (non-blank,
  non-comment lines — same rule as Python's), `imports` = the set of `require('x')` /
  `import ... from 'x'` module specifiers (regex over string literals — this IS a lexical fact,
  not a narrated structure), and `ast_nodes` = **UNMEASURED (None)** — no stdlib JS AST exists.
  `_struct_distance` treats a None `ast_nodes` on either side as "dimension absent": the
  distance is the mean over the dimensions both sides have (LOC + Jaccard for JS pairs; all
  three for Python pairs). The report footer states that JS distances are 2-dimensional. A
  cross-language pair never occurs (one archetype, one language).
- **JS static surface via Node itself** — `_extract_static_js` runs a small Node one-liner
  (shipped as a string constant, no file) that `require`s the impl in a child process with
  `main` guarded (the impl must expose its functions and only run `main()` under
  `require.main === module` — stated in the SPEC contract, verifiable) and prints
  `Object.keys(module.exports)` sorted; each exported function/class becomes an observation
  `source/<unit> exports <name>` with the same content-addressed id scheme. This is the
  target's own runtime reporting its own public surface — measured, not parsed by a heuristic.
  If node is absent, the surface is UNMEASURED and `bench --fidelity` says so for that entry.
- **Stub/wrong discovery by extension set** `{.py, .js}`; oracle cases unchanged in shape
  (stdin JSON → stdout line, exit code) — the contract was language-neutral all along.
- **First JS archetype: `rate-limiter`** (a token-bucket limiter over a JSON event stream:
  `{capacity, refill_per_tick, events:[[tick, "req"|"tick"...]]}` → per-request allow/deny
  log + final tokens; decision-dense enough to discriminate: refill order vs request order at
  the same tick, capacity clamp, zero-capacity, fractional refill forbidden (ints only),
  malformed → `ERROR`). SPEC/ACCEPTANCE/CONSTITUTION, pinned IR, withheld oracle (≥20 cases),
  `stub/stub.js`, `wrong/*.js` one per rule, discrimination gate green BEFORE dispatch,
  3 blind compilations (`c-*/source/impl.js`), curation-ready. Verdict pinned whatever it is.
- **Zero change to Python behaviour**: every existing entry's bench/bench-r2/lang-compare/
  fidelity output must be byte-identical (asserted).

## Reasons
- The claim "the method is language-agnostic" is currently narrated. One JS archetype makes it
  measured — or shows exactly where it breaks.
- Delegating JS structure to Node keeps the engine stdlib-only AND keeps every JS number a
  fact the target runtime produced, not a heuristic the engine invented.

## Consequences
+ The bench's headline gains a non-Python row; the runner, metrics and extractor become
  extension-routed with the Python paths untouched.
+ The narrower JS structural metric is disclosed in the instrument, the ADR and the report.
- Node becomes a soft dependency of `bench`/`bench-r2`/`bench --fidelity` for JS entries; its
  absence is a named UNMEASURED, never a silent pass. CI has it.

## Verification
- [ ] All Python entries' `bench`, `bench-r2`, `bench --fidelity` and `lang-compare` outputs
  are byte-identical before/after this change (AC-JS-01)
- [ ] `rate-limiter` oracle is discriminating (stub red, every wrong/ red) and the three blind
  JS compilations validate against the pinned IR; the bench verdict is computed and pinned;
  with `node` removed from PATH the entry reads UNMEASURED with the reason named (AC-JS-02)
- [ ] `_impl_metrics` on a `.js` file yields loc + imports and `ast_nodes: None`;
  `_struct_distance` over two JS impls uses two dimensions and states so; `_extract_static_js`
  reports the exports Node itself lists, and `bench --fidelity` shows a `static_surface` for
  the JS entry (AC-JS-03)
