# SPEC-AMBIGUITIES — a register of known under-specifications in the Diamond canonical packages

This is a register, not a to-do list. It names the sentences in the v1 canonical packages
(`uscha-kit/tests/fixtures/diamond-bench/<entry>/canonical/`) that admit more than one honest
reading, and records how four independently blind compilers (`c-codex`, `c-haiku`, `c-opus`,
`c-sonnet` — see `docs/adr/ADR-042-cross-vendor-arm-v0.1.md` for the model map) actually read
each one, quoting each compiler's `unresolved_intent` declaration where it exists, and what the
withheld oracle (`<entry>/oracle/ORACLE.json`) does with the disagreement.

## The decision, and why (2026-09-20)

The nine items below were handed over as a known list from an earlier pass over the bench. This
register re-verifies each one against the fixture files rather than re-typing the handover: some
hold up as written, some hold up only partially (the ambiguity is real but the sentence describing
it needed correcting), and the extra-fields item (AMB-01) turned out to cover four entries with
solid evidence, not the seven originally claimed — see AMB-01 for the corrected count and the
method used to reach it.

The canonical packages (`canonical/`) are **frozen at v1**. They are not edited here or anywhere
near this change. Sharpening a sentence now, after the withheld oracle's answer is already known,
would tune the benchmark to its own answer key — the oracle was authored blind to the
compilations, and a package edit made with the oracle's verdict in hand is no longer blind to
anything. It would also invalidate the four `c-*` compilations and the `r2/c-*` re-runs that exist
today for each entry: they were produced against the current wording, and a wording change makes
them compilations of a package that no longer exists. A possible future "v2 package" round may
sharpen some or all of these together, with one clean recompilation across all vendors — this
register is that round's input, not a substitute for it.

## How to read a row

Each item names the entries it touches, quotes the exact sentence(s) with `file:line`, gives the
readings different compilers took (quoting a compiler's own `unresolved_intent` declaration when
it named the choice explicitly — these live in `<entry>/<compiler>/COMPILATION.json`, which is
pretty-printed, so the quoted line number is stable), says what the withheld oracle does with the
disagreement (accepts every reading it received, or punishes one — naming the oracle case by its
`name` field in `ORACLE.json`), what that means for the entry's verdict in `DIAMOND-BENCH.md`, and
the one-sentence "v2 sharpening" that would close the ambiguity in a future package round. Where
the fixture does not let a claim be checked, the row says so — `not determinable from the fixture`
— rather than guessing.

**v1 frozen.** Every quote below is read-only evidence about the *existing* package text. Nothing
in this document is a proposed edit to `canonical/`.

---

## AMB-01 — the extra-fields split (ignore vs reject unknown object keys)

**Entries affected:** `protocol-adapter`, `scheduler`, `transformer`, `ui-render` (four entries,
not the seven originally handed over — see "What the handover got wrong" below).

**The pattern.** Several canonical SPECs describe an input object as having "exactly" a fixed set
of fields, then never say — inside the `## Errors` list — that an *extra* field is one of the
malformed cases. Some compilers read "exactly the fields X, Y, Z" as a shape constraint (extra
keys are malformed) and some read the silence in the `## Errors` list as the operative contract
(extra keys are simply not looked at). Both readings are internally consistent; the SPEC does not
adjudicate between them.

### transformer (the one that moved the verdict)

- Quote: `uscha-kit/tests/fixtures/diamond-bench/transformer/canonical/SPEC.md:8-9` — "standard
  input is a JSON array of records, each an object with exactly the fields `first` (string),
  `last` (string), and `age` (integer)".
- Quote: `uscha-kit/tests/fixtures/diamond-bench/transformer/canonical/SPEC.md:31` — "No other
  fields are read or preserved; no sorting, no deduplication, no filtering."
- Readings: `c-codex` rejects — `transformer/c-codex/COMPILATION.json:39` declares "Reject
  records with extra fields in addition to first, last, and age." with rationale "The contract
  says each input record is an object with exactly those fields, so additional keys are treated
  as malformed rather than ignored." `c-haiku` and `c-sonnet` tolerate extras (declared in their
  own `unresolved_intent`); `c-opus` tolerates extras too, but by omission — its source
  (`transformer/c-opus/source/impl.py:30-31`) only checks that `first`/`last`/`age` are present
  and never rejects on an extra key.
- Oracle: case `extra-field-tolerated` (`transformer/oracle/ORACLE.json`, tagged `AC-TR-06`) feeds
  a record with a stray `"extra": 1` key and expects it silently dropped from the output — i.e.
  the oracle picked the tolerate reading and punishes the reject reading.
- Effect on verdict: this is the entire cause of `transformer`'s PASS → PARTIAL move
  (`c-codex` 13/14, the only compiler that read this sentence the other way) — see
  `docs/adr/ADR-042-cross-vendor-arm-v0.1.md`, "The one finding, and why it is the point".
- v2 sharpening: append to SPEC.md's `## Errors` list: "An extra field beyond `first`/`last`/`age`
  is not an error; it is ignored."

### protocol-adapter

- Quote: `uscha-kit/tests/fixtures/diamond-bench/protocol-adapter/canonical/SPEC.md:15` — "A
  MESSAGE is `{"type": <string>, "fields": [[<key>, <value>], ...]}` — fields as an ARRAY of
  pairs, because order is meaningful". No "exactly" wording here, but no tolerance statement
  either; line 26 says only "Malformed top-level shape ... → `ERROR`" without defining "shape".
- Readings: `c-codex` and `c-opus` reject — both source files enforce
  `set(message.keys()) != {"type", "fields"}` as malformed (`protocol-adapter/c-codex/source/impl.py:43`,
  `protocol-adapter/c-opus/source/impl.py:70`); `c-opus`'s own declaration
  (`protocol-adapter/c-opus/COMPILATION.json`, `ir_region: message-object-strictness-on-encode`)
  names the choice explicitly: "does not say whether unknown extra keys are tolerated. Strict
  equality was chosen because decode never produces extra keys". `c-haiku` and `c-sonnet` tolerate
  — both only check `"type" not in msg or "fields" not in msg` (presence, not exclusivity):
  `protocol-adapter/c-haiku/source/impl.py:79`, `protocol-adapter/c-sonnet/source/impl.py:36`.
- Oracle: no case in `protocol-adapter/oracle/ORACLE.json` (15 cases) has "extra" in its name —
  the ambiguity is real but untested.
- Effect on verdict: none. All four compilations are 15/15 GREEN in `DIAMOND-BENCH.md`.
- v2 sharpening: state explicitly whether a message object with a key beyond `type`/`fields` is
  malformed or is read structurally and the extra key ignored.

### scheduler

- Quote: `uscha-kit/tests/fixtures/diamond-bench/scheduler/canonical/SPEC.md:8-10` — "Each job is
  an object with exactly the fields `id` (integer), `priority` ... and optionally `deadline`".
- Readings: `c-codex` and `c-sonnet` reject extras via an explicit allowlist check
  (`scheduler/c-codex/source/impl.py:26` `if not keys.issubset(ALLOWED_FIELDS)`;
  `scheduler/c-sonnet/source/impl.py:36` `if not keys.issubset(allowed_keys)`) — both declared
  this in `unresolved_intent` (`scheduler/c-codex/COMPILATION.json`, `ir_region: AC-SC-07`:
  "The contract says each job object has exactly those fields, while the error list does not
  spell out extra fields; enforcing the contract is the narrower interpretation."). `c-haiku` and
  `c-opus` tolerate extras by omission — neither source file checks for a key set beyond
  presence of the required fields (`scheduler/c-haiku/source/impl.py`,
  `scheduler/c-opus/source/impl.py:37-40`).
- Oracle: no case in `scheduler/oracle/ORACLE.json` (30 cases) has "extra" in its name.
- Effect on verdict: none from this ambiguity specifically. `scheduler` is PARTIAL in
  `DIAMOND-BENCH.md` (`c-haiku` 25/30, `c-sonnet` 26/30), but that mismatch is explained by
  AMB-06 below, not by this one — see AMB-06 for the case-level evidence.
- v2 sharpening: same as protocol-adapter — state whether a job object carrying an unlisted key
  is malformed.

### ui-render

- Quote: `uscha-kit/tests/fixtures/diamond-bench/ui-render/canonical/SPEC.md:9` — "On malformed
  input (shape errors, a duplicate field name, an event naming an unknown field), print exactly
  `ERROR`". "An unknown field" here names a model-field lookup failure (an event's `field` value
  not present in the model), a different concept from a JSON object carrying an extra key —
  the SPEC never separately addresses the latter.
- Readings: `c-codex` rejects extra JSON keys generically —
  `ui-render/c-codex/source/impl.py:9` implements shape checks as
  `set(value.keys()) == set(keys)` (exact match). `c-haiku` tolerates (declared:
  `ui-render/c-haiku/COMPILATION.json`, `ir_region: extra_event_fields`: "permit extra fields in
  event objects without validation or error ... follows Postel's law"). `c-opus` tolerates too,
  and names the tension directly (`ui-render/c-opus/COMPILATION.json`,
  `ir_region: extra-keys-and-missing-keys-on-events`: "rejecting unknown extras is not stated and
  would make the contract needlessly brittle"), matched by its source
  (`ui-render/c-opus/source/impl.py:93,105`, which raises `Malformed()` only for an *unknown
  field name*, never for an extra JSON key). `c-sonnet` tolerates by omission — no `keys()`
  check anywhere in `ui-render/c-sonnet/source/impl.py`.
- Oracle: no case in `ui-render/oracle/ORACLE.json` (13 cases) has "extra" in its name.
- Effect on verdict: none. All four compilations are 13/13 GREEN in `DIAMOND-BENCH.md`.
- v2 sharpening: add one clause to line 9's parenthetical: "(shape errors — including an object
  carrying a key beyond the ones named above — a duplicate field name, ...)" if extras should be
  malformed, or add a sentence to "Out of scope" tolerating them, matching whichever reading the
  package intends.

### What the handover got wrong

The handover named seven entries. This register checked all twelve by reading every compiler's
`unresolved_intent` and, where a compiler didn't declare an opinion, its actual source code for a
key-set check. Four entries hold up as genuine two-sided splits (above). Four more
(`crud-store`, `ledger-lite`, `rate-limiter`, `worker`) were also flagged in the handover, but on
inspection **all four compilers converge on the same reading (tolerate extras) in every one of
them** — `crud-store/c-sonnet/source/impl.py` (no key-set check on an operation object),
`ledger-lite/c-haiku/source/cli.py:25,51` and `ledger-lite/c-sonnet/source/*.py` (no key-set
check), `rate-limiter/c-sonnet/source/impl.js` (no key-set check), `worker/c-haiku/source/impl.py`
and `worker/c-opus/source/impl.py` (no key-set check) all agree with their siblings that already
declared "ignore extras" in `unresolved_intent`. Agreement across all four compilers is not a
split, so these four are not counted here. `guard` and `parser` were also checked and have no
extra-JSON-key ambiguity at all (guard's tension is AMB-09, a different kind of open/closed
question about tool *names*, not object *keys*); `rest-handler` and `state-machine` have no input
object with a field set narrow enough to raise this question.

---

## AMB-02 — parser AC-PR-03: repeated unary minus (`--3`)

**Entries affected:** `parser`.

- Quote: `uscha-kit/tests/fixtures/diamond-bench/parser/canonical/SPEC.md:16-19` — "Expressions
  over integers with the binary operators `+ - * /`, unary minus, and parentheses... Numbers are
  non-negative integer literals (a unary `-` provides negation)." The grammar names "unary minus"
  in the singular and never states whether a unary-minus expression can itself be the operand of
  another unary minus (`--3`, `- -3`).
- Readings: all four compilers converge on **allow**, and three declare it explicitly.
  `c-codex` (`parser/c-codex/COMPILATION.json`, `ir_region: AC-PR-03`): "Allow repeated unary
  minus operators, such as --3 and - -3... the grammar includes unary minus and does not forbid
  nesting unary expressions." `c-opus` (`ir_region: multiple-leading-unary-minus`): "Allow chained
  unary minus (e.g. --3 == 3) via right-recursive unary rule... no stated arity limit." `c-sonnet`
  (`ir_region: factor-grammar`): "chained unary minus (e.g. --3) is accepted... the spec never
  forbids it." `c-haiku` does not declare this item by name, but its own declared rationale for a
  related item (`unary-minus-precedence-strategy`) states its recursive-descent `factor()`
  structure "allows correct parsing of expressions like '5 - -3' and '--5'" — i.e. the same
  reading, reached by construction rather than by a named decision.
- Oracle: `parser/oracle/ORACLE.json` (21 cases) — no case's `raw_stdin` contains `--`. Checked by
  grep across every case; none match.
- Effect on verdict: none. The ambiguity is real (the SPEC never states an arity bound on unary
  minus) but every compiler read it the same way, and the reading is untested, so it never had a
  chance to move a verdict.
- v2 sharpening: state the grammar rule explicitly, e.g. `factor := "-" factor | primary`
  (allowing arbitrary repetition) or `factor := ["-"] primary` (allowing exactly one), and add an
  oracle case exercising it either way.

---

## AMB-03 — rate-limiter (JavaScript): `Number.isInteger` vs `Number.isSafeInteger`

**Entries affected:** `rate-limiter`.

- Quote: `uscha-kit/tests/fixtures/diamond-bench/rate-limiter/canonical/SPEC.md:33-34` — "`capacity`
  or `refill` not an integer (JSON booleans and non-integral numbers are not integers)". The SPEC
  defines "integer" only by excluding booleans and non-integral numbers; it never mentions
  `Number.MAX_SAFE_INTEGER` or a magnitude bound.
- Readings: only `c-codex` names the road not taken —
  `rate-limiter/c-codex/COMPILATION.json:44`: "Use JavaScript Number.isInteger for integer
  validation rather than imposing Number.isSafeInteger... The spec says JSON integers and does
  not define a safe-integer limit; adding one would introduce an extra rejection rule not stated
  by the canonical package." Checked all four sources directly (`grep -n "isInteger\|isSafeInteger"`
  across every `rate-limiter/*/source/impl.js`): every compiler — `c-codex`, `c-haiku`, `c-opus`,
  `c-sonnet` — uses `Number.isInteger` and none uses `Number.isSafeInteger` anywhere in the
  fixture. So this is not a compiler-vs-compiler split; it is one compiler explicitly declining an
  alternative that no compiler (including itself) actually took.
- Oracle: `rate-limiter/oracle/ORACLE.json`'s largest numeric case, `large-values`, uses
  `capacity: 1000` — nowhere near `Number.MAX_SAFE_INTEGER` (2^53 - 1). No case probes the
  boundary between "integer" and "safe integer".
- Effect on verdict: none. All four compilations are 25/25 GREEN.
- v2 sharpening: if the intent is to bound magnitude, state it ("capacity and refill fit in a
  JS-safe integer"); if not, no change is needed — the ambiguity is currently inert because
  nothing implements or tests the stricter reading.

---

## AMB-04 — crud-store / protocol-adapter / transformer: the record byte format is whichever
default `json.dumps` happens to emit

**Entries affected:** `crud-store`, `protocol-adapter`, `transformer` (all three Python-only —
verified: `find crud-store protocol-adapter transformer -iname "*.js"` returns nothing under any
`c-*`; no JavaScript arm exists for any of the three).

- Quotes: `crud-store/canonical/SPEC.md:26` — "formatting is free; only structure and values are
  fixed." `protocol-adapter/canonical/SPEC.md:31` — "Output formatting is free; only structure and
  values are fixed". `transformer/canonical/SPEC.md:32` — "not fixed by this spec — only its
  structure and values are."
- Readings: checked every compiler's output call (`grep -n "json.dumps" .../source/impl.py`) in
  all three entries. `transformer` is uniform: all four compilers call bare `json.dumps(...)` with
  no `separators` argument (default `", "` / `": "` spacing) —
  `transformer/c-codex/source/impl.py:33`, `c-haiku:54`, `c-opus:53`, `c-sonnet:44` — matching
  `c-codex`'s own declared reasoning (`transformer/c-codex/COMPILATION.json`,
  `ir_region: AC-TR-06`: "Use json.dumps with default compactness choices from the Python standard
  library... The canonical package fixes only output structure and values, not whitespace
  formatting."). `crud-store` and `protocol-adapter` are **not** uniform: `c-codex` explicitly
  passes `separators=(",", ":")` (compact, no spaces) in both
  (`crud-store/c-codex/source/impl.py:89`, `protocol-adapter/c-codex/source/impl.py:100`), while
  `c-haiku`/`c-opus`/`c-sonnet` call bare `json.dumps(...)` (default spacing) in both entries —
  so the actual emitted bytes genuinely differ compiler-to-compiler, not just hypothetically.
- Effect on verdict: **none, and not by luck** — `qa_ledger.py`'s `expected_json` comparison
  (`uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py:7066-7068`) is `json.loads(out) ==
  case["expected_json"]`, a parsed-value comparison, not a byte comparison. So the byte-format
  ambiguity is real (confirmed by the differing `separators=` calls above) but is structurally
  invisible to this oracle for any case using `expected_json`. All three entries are unaffected in
  `DIAMOND-BENCH.md` (`crud-store` 12/12, `protocol-adapter` 15/15, `transformer`'s PARTIAL is
  AMB-01, unrelated to formatting).
- v2 sharpening: none needed for the current oracle (it is byte-format-agnostic by construction);
  if a future harness ever compares raw bytes, the SPEC's existing "formatting is free" sentence
  already covers that case and would need no change — the harness would need to stop asserting
  byte equality instead.

---

## AMB-05 — ledger-lite: ADR-001 states the seam and the run command, not the entry-point's
internal organization

**Entries affected:** `ledger-lite`.

- Quote: `uscha-kit/tests/fixtures/diamond-bench/ledger-lite/canonical/docs/adr/ADR-001-model-cli-seam.md:14-15`
  — "`source/cli.py` reads stdin, validates SHAPE only (AC-LG-05), calls `model.post`, prints
  (AC-LG-04). It never inspects amounts for balance and never decides acceptance." This fixes
  *what* `cli.py` does and the seam it must cross through, but never states *how* `cli.py`
  organizes that behavior internally (a `main()` function under a `__main__` guard vs top-level
  script code).
- Correction to the handover's framing: `ledger-lite/canonical/SPEC.md:10-11` (not ADR-001) *does*
  fix the external invocation surface — "`source/cli.py` (the entry point: reads stdin, imports
  `model`, prints). Run as `python cli.py` from the `source/` directory." So the ambiguity is
  narrower than "the entry-point surface is unstated": the *external* run command is stated in
  SPEC.md; only the *internal* code organization is left open by ADR-001.
- Readings: `c-codex` is the only compiler that names this as a free choice —
  `ledger-lite/c-codex/COMPILATION.json:69` (`ir_region: ADR-001`): "The ADR fixes the seam at
  model.post and the run mode, but leaves entry-point organization open; a main function keeps I/O
  contained and simple." Checked all four `cli.py` files for `__main__`/`def main`: every compiler
  — `c-codex`, `c-haiku`, `c-opus`, `c-sonnet` — independently converged on the same organization
  (a `main()` function called under `if __name__ == "__main__":`) despite the freedom ADR-001
  leaves open.
- Oracle: this cannot be tested by a black-box oracle by construction — `ORACLE.json` only ever
  observes `python cli.py`'s stdout/exit code, never its internal function structure.
- Effect on verdict: none, and unobservable in principle by this harness.
- v2 sharpening: none needed — this is a documentation-only freedom (ADR-001 could optionally
  note "entry-point internal organization is unconstrained" for a future reader's clarity, but no
  behavioral gap exists to close).

---

## AMB-06 — scheduler AC-SC-04: the deadline check's `<=` collides with "not missed at exactly
its deadline tick"

**Entries affected:** `scheduler`.

- Quote: `uscha-kit/tests/fixtures/diamond-bench/scheduler/canonical/SPEC.md:22-24` — "Every ready
  or running job whose `deadline` is defined and is **less than or equal to** the current tick...
  is dropped... A job completing at exactly its deadline tick has NOT missed (completion is
  checked at step 4 of the previous tick)." Also `scheduler/canonical/ACCEPTANCE.md:8-10`
  (AC-SC-04): "a job whose `deadline` is ≤ the current tick and is not complete is dropped... a
  job completing at exactly its deadline tick is NOT missed." The literal `<=` in step 2 and the
  "not missed at exactly its deadline" clause pull in opposite directions for a job whose deadline
  falls on the very tick being evaluated.
- Readings: `c-codex` and `c-opus` implement the literal `<=`
  (`scheduler/c-codex/source/impl.py:89`: `job["deadline"] <= tick`;
  `scheduler/c-opus/source/impl.py:106`: `job["deadline"] <= tick`). `c-haiku` and `c-sonnet`
  implement strict `<` instead, and `c-sonnet` names the reasoning explicitly in a source comment
  (`scheduler/c-sonnet/source/impl.py:97-105`): "Using a strict '<' (rather than '<=') is what
  makes this consistent with 'a job completing at exactly its deadline tick has NOT missed': at
  tick == deadline the job is still eligible to be [run]"; `scheduler/c-haiku/source/impl.py:90`
  uses the same strict comparison without a comment.
- Oracle: traced case `deadline-at-arrival-tick-missed` (`scheduler/oracle/ORACLE.json`, tagged
  `AC-SC-04`) by hand against both readings. Payload: a job with `arrival: 2, deadline: 2,
  duration: 1`. At tick 2 the job arrives and becomes ready-or-running in the same tick the
  deadline check runs. Under `<=` (2 ≤ 2 is true) it is dropped as `missed` before selection —
  matching `expected_json`, whose `events` end in `[2, "missed", 1]` with `completed: []`. Under
  strict `<` (2 < 2 is false) it is NOT dropped, proceeds to selection, starts, and completes that
  same tick — producing a `start`/`complete` pair instead of `missed`, which would fail this case.
  So the oracle resolved the tension in favor of the literal `<=`, against the "not missed at
  exactly deadline" reading `c-sonnet`'s comment argues for.
- Effect on verdict: this is very likely the cause of `scheduler`'s PARTIAL verdict for `c-haiku`
  (25/30) and `c-sonnet` (26/30) against `c-codex`/`c-opus` (30/30 GREEN) in `DIAMOND-BENCH.md` —
  the hand-traced case above shows the `<`-vs-`<=` choice does produce a concrete oracle mismatch
  on at least one AC-SC-04 case. Whether it is the *only* cause of the 25/30 and 26/30 counts (vs.
  AC-SC-04's other five cases, or a different AC entirely) is **not determinable from the fixture**
  without running the withheld oracle against each compilation, which this register does not do.
- v2 sharpening: reword step 2 to remove the collision, e.g. "...is defined and is **strictly
  less than** the current tick..." (matching what the oracle actually enforces), or keep `<=` and
  delete/reword the "not missed at exactly its deadline tick" clause so it no longer reads as an
  exception to it.

---

## AMB-07 — rest-handler: trailing-slash routing was left to the compiler, and one compiler chose
differently

**Entries affected:** `rest-handler`.

- Quote: `uscha-kit/tests/fixtures/diamond-bench/rest-handler/canonical/SPEC.md:26` — "A path the
  API does not define (e.g. `/users`, `/items/1/extra`) → `404`". The two examples given are an
  unrelated path and an over-long path; a *trailing slash* on an otherwise-valid path
  (`/items/`, `/items/5/`) is never named anywhere in SPEC.md or ACCEPTANCE.md.
- Readings: `c-codex` (`rest-handler/c-codex/COMPILATION.json:53`, `ir_region: AC-RH-02`):
  "Paths are matched literally; query strings, trailing slashes such as /items/, and extra path
  segments are treated as undefined paths returning 404." `c-opus`
  (`rest-handler/c-opus/source/impl.py:63`, source comment): "A trailing slash yields an empty
  final segment: /items/ is not /items." `c-sonnet`
  (`rest-handler/c-sonnet/COMPILATION.json:51-53`): "trailing slash on item path... treat as
  undefined path -> 404, not as item route with empty id... falls into the general undefined-path
  404 bucket." All three of those treat a trailing slash as **404**. `c-haiku` diverges:
  `rest-handler/c-haiku/source/impl.py:44-45` — `parts = [p for p in path.split("/") if p]` —
  filters out empty path segments before matching, so `/items/` and `/items` both split to
  `["items"]` and hit the **same route** (200/201/405 depending on method, never 404). This is a
  confirmed 3-vs-1 split, not the unanimous-with-one-silent-holdout pattern seen elsewhere.
- Oracle: `rest-handler/oracle/ORACLE.json` (15 cases) — the only 404-on-unknown-path case,
  `unknown-path-404`, uses payload `/users` (no trailing slash). No case in the fixture exercises
  a trailing slash on any route. Checked by reading all 15 case payloads directly.
- Effect on verdict: not the (sole) cause of `rest-handler`'s PARTIAL verdict as far as this
  register can determine — the ambiguity is untested by the oracle, so it cannot be what makes
  `c-haiku` and `c-opus` read 14/15 in `DIAMOND-BENCH.md`. What specific case does cause that
  14/15 is **not determinable from the fixture** without running the oracle against each
  compilation.
- v2 sharpening: add one bullet to `## Errors`: "A trailing slash on an otherwise-valid path
  (`/items/`, `/items/5/`) is undefined and returns 404" (or the opposite, if collapsing it into
  the matching route is intended), plus one oracle case exercising it.

---

## AMB-08 — state-machine: AC-SM-04's "fold left to right" vs AC-SM-06/05's fail-fast reading

**Entries affected:** `state-machine`.

- Quote: `uscha-kit/tests/fixtures/diamond-bench/state-machine/canonical/ACCEPTANCE.md:7` (AC-SM-04)
  — "events fold left to right from `locked`; the final state is printed." Quote:
  `state-machine/canonical/ACCEPTANCE.md:9` (AC-SM-06) — "input that is not a JSON array prints
  exactly `ERROR`." Neither ACCEPTANCE.md nor SPEC.md states whether validating "every element is
  a known event string" happens as a single up-front pass before any folding begins, or whether
  the fold proceeds event-by-event and stops the instant an invalid one is reached.
- Readings: `c-codex` names the choice explicitly
  (`state-machine/c-codex/COMPILATION.json:54`, `ir_region: AC-SM-04`): "Stop processing and print
  ERROR immediately when an invalid event is encountered... the package does not require
  continuing after detecting an error." No other compiler declares an opinion on this specific
  point in `unresolved_intent`; `c-haiku`'s own declared `ir_region: event-validation-order`
  describes a single-pass structure ("JSON parse -> isinstance(list) -> loop: isinstance(str) ->
  event in {'coin','push'}") that validates-then-folds per element in one loop, which is
  behaviorally the same "stop at first bad event" outcome `c-codex` names, just reached by a
  different code shape.
- Oracle: `state-machine/oracle/ORACLE.json` cannot distinguish the two readings — the machine's
  only observable output is the single final state string or `ERROR`; there is no partial-output
  or per-event field in the output contract (`SPEC.md`'s Output line: "print the final state name
  to standard output"), so a fold-then-fail and a validate-then-fold implementation are
  indistinguishable from outside the process for any input.
- Effect on verdict: none, and unobservable in principle by this black-box harness. All four
  compilations are 12/12 GREEN in `DIAMOND-BENCH.md`.
- v2 sharpening: none needed — the ambiguity is real in the text but has no externally observable
  consequence given the current output contract (a single final line), so sharpening it would only
  be worthwhile if a future package version adds a partial-output or error-detail field.

---

## AMB-09 — guard AC-GH-04: an explicitly open-world tool-name space, closed by each compiler
into a different list

**Entries affected:** `guard`.

- Quote: `uscha-kit/tests/fixtures/diamond-bench/guard/canonical/SPEC.md:24-25` — `tool_name` is
  "a string naming the tool about to run (e.g. `"Bash"`, `"Write"`, `"Edit"`, `"Read"`, or any
  other tool the host supports, **including tools this guard has never heard of**)." Quote:
  `guard/canonical/SPEC.md:52-53` — "Some tools cannot write by their nature — a file reader, a
  text search, a directory listing, a web fetch/search, a notebook reader... **The guard
  recognises this family of read-only tools by name.**" Quote:
  `guard/canonical/ACCEPTANCE.md:12-13` (AC-GH-04) — "read-only tools (a file reader, text search,
  directory listing, notebook reader, web fetch/search) are always allowed... tool names are
  matched case-insensitively." The SPEC explicitly anticipates unknown tool names (open world) in
  one paragraph, then demands the guard recognize the read-only family "by name" in the next —
  which is only possible with a closed enumeration of exact strings the SPEC never supplies (only
  category descriptions: "a file reader", not `"Read"`).
- Readings: all four compilers built a different closed list, and `c-codex` names the tension
  explicitly (`guard/c-codex/COMPILATION.json:39`, `ir_region: AC-GH-04`): "Recognize a
  conservative explicit set of read-only tool names: Read, Grep, Glob, LS, List, Find, Search,
  WebFetch, WebSearch, NotebookRead, after case-insensitive normalization... The package names
  tool families but not host-specific exact names; an explicit allowlist avoids treating arbitrary
  unknown tools as safe merely because their names contain read-like words." The four actual lists
  (read directly from each `guard/*/source/guard.py`):
  - `c-codex` (`guard/c-codex/source/guard.py:8-19`, 11 names): read, fileread, grep, glob, ls,
    list, find, search, webfetch, websearch, notebookread.
  - `c-haiku` (`guard/c-haiku/source/guard.py:36-46`, 6 names): read, grep, glob, **monitor**,
    webfetch, websearch — the only compiler that includes `monitor`, and the only one missing
    `ls`, `notebookread`, `find`, `list`, `search`.
  - `c-opus` (`guard/c-opus/source/guard.py:29-37`, 7 names): read, grep, glob, ls, notebookread,
    webfetch, websearch.
  - `c-sonnet` (`guard/c-sonnet/source/guard.py:23-31`, 7 names): read, grep, glob, ls, webfetch,
    websearch, notebookread (same 7 as `c-opus`).
- Oracle: `guard/oracle/ORACLE.json`'s four cases tagged `AC-GH-04` (`read-tool-reads-golden`,
  `grep-tool-searches-golden`, `glob-tool-names-golden`, `websearch-mentions-golden`) only exercise
  `Read`, `Grep`, `Glob`, `WebSearch` — tools every one of the four lists agrees on. So AC-GH-04's
  own oracle cases do not discriminate between the four lists; whether the extra names each
  compiler chose (`ls`/`notebookread`/`find`/`list`/`search`/`monitor`) are exercised by some
  *other* AC's cases (e.g. AC-GH-06's "any other tool" bucket) is **not determinable from the
  fixture** without running the oracle against each compilation.
- Effect on verdict: `guard` is PARTIAL in `DIAMOND-BENCH.md` (`c-codex` 20/23, `c-haiku` 19/23,
  `c-opus` 21/23, `c-sonnet` 21/23), and this ambiguity is a plausible contributor given the
  confirmed divergence in the read-only lists above — but `guard` also carries other declared
  ambiguities in the same fixture (e.g. `c-codex`'s AC-GH-06 declaration about marker detection in
  non-string values, `c-opus`'s AC-GH-05 declaration about the shell-command allowlist), so
  attributing guard's specific miss counts to this one ambiguity alone is **not determinable from
  the fixture**.
- v2 sharpening: replace "The guard recognises this family of read-only tools by name" with an
  explicit list of exact tool-name strings the package commits to (e.g. the union used across the
  four compilers here, or a smaller canonical subset), and state explicitly what happens to a tool
  name that is read-like by description but not on the list (currently open to either "allow by
  family" or "block, unrecognized" — the four compilers picked different points on that spectrum).

---

## Summary table

| ID | Entries | Oracle stance | Verdict effect |
|----|---------|---------------|-----------------|
| AMB-01 | protocol-adapter, scheduler, transformer, ui-render | accepts both (untested) except transformer, which punishes the reject reading | transformer PASS → PARTIAL (the only case); none for the other three |
| AMB-02 | parser | untested (no `--` case exists) | none — all 4 compilers converged anyway |
| AMB-03 | rate-limiter | untested (no near-`MAX_SAFE_INTEGER` case) | none — no compiler took the stricter reading either |
| AMB-04 | crud-store, protocol-adapter, transformer | structurally invisible (`expected_json` compares parsed values, not bytes) | none, by construction |
| AMB-05 | ledger-lite | unobservable in principle (black-box on `python cli.py`) | none — all 4 compilers converged anyway |
| AMB-06 | scheduler | resolves in favor of literal `<=` (traced case `deadline-at-arrival-tick-missed`) | likely explains scheduler's PARTIAL (c-haiku 25/30, c-sonnet 26/30) — not fully isolated from AC-SC-04's other cases |
| AMB-07 | rest-handler | untested (no trailing-slash case exists) | not the (sole) cause of rest-handler's PARTIAL — real cause not determinable from the fixture |
| AMB-08 | state-machine | unobservable in principle (single final-state output, no partial field) | none — all 4 compilations 12/12 GREEN |
| AMB-09 | guard | AC-GH-04's own cases don't discriminate the four lists; other ACs untraced | plausible contributor to guard's PARTIAL; not isolated from guard's other ambiguities |
