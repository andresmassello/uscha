# SPEC — a token-bucket rate limiter (Diamond bench archetype: stateful policy, JavaScript target)

A program that replays a stream of ticks and requests through a token bucket and prints what
happened. The only compiler input; describes behaviour, not an implementation and not a test
case. **Target: JavaScript (Node ≥ 18, no dependencies).**

## Contract

- **Input:** standard input is one JSON object
  `{"capacity": <int ≥ 0>, "refill": <int ≥ 0>, "events": [<event>, ...]}`.
  An event is either the string `"tick"` or the string `"req"`.
- **Output:** print one JSON object to standard output and exit 0:
  `{"log": [<"allow"|"deny">, ...], "tokens": <int>}` — one log entry per `"req"` in event
  order, and the bucket's token count after the last event. On any malformed input, print
  exactly `ERROR`.
- **Module shape:** the program is a single file `source/impl.js` that exposes its functions
  on `module.exports` and runs its main routine only when executed directly
  (`require.main === module`). Loading the file with `require` must have no side effects.

## The bucket

- The bucket starts **full**: `tokens = capacity`.
- A `"req"` event **consumes one token if `tokens ≥ 1`** (log `"allow"`, `tokens` decreases by
  one); otherwise it is denied (log `"deny"`, `tokens` unchanged).
- A `"tick"` event **adds `refill` tokens, clamped at `capacity`**: `tokens = min(capacity,
  tokens + refill)`.
- Events are processed strictly in array order; there is no implicit tick between requests.
- `capacity` 0 denies every request forever; `refill` 0 never replenishes.

## Errors

- Input that is not a JSON object → `ERROR`.
- Missing `capacity`, `refill` or `events`; `capacity` or `refill` not an integer (JSON
  booleans and non-integral numbers are not integers) or negative; `events` not an array; any
  event that is not exactly `"tick"` or `"req"` → `ERROR` for the whole input (no partial
  log).

## Out of scope (state honestly; do not implement)

No time source, no burst windows, no per-key buckets, no fractional tokens. The JSON output's
formatting is not fixed by this spec — only its structure and values are. The program reads one
object and prints one line: the result object or `ERROR`.
