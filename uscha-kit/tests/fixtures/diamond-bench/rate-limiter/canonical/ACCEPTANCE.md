# ACCEPTANCE — token-bucket rate limiter (JavaScript target)

- [ ] AC-RL-01 the bucket starts full (`tokens = capacity`); a `req` with `tokens ≥ 1` logs
  `allow` and consumes one token; a `req` with `tokens = 0` logs `deny` and consumes nothing.
- [ ] AC-RL-02 a `tick` adds `refill` tokens clamped at `capacity`; `refill` 0 never
  replenishes; `capacity` 0 denies every request.
- [ ] AC-RL-03 events are processed strictly in array order; the output `log` has exactly one
  entry per `req`, in order, and `tokens` is the count after the last event.
- [ ] AC-RL-04 an empty `events` array yields `{"log": [], "tokens": capacity}`.
- [ ] AC-RL-05 malformed input (not an object, missing/mistyped/negative `capacity`/`refill`,
  boolean or non-integral number where an integer is required, `events` not an array, an
  unknown event string) prints exactly `ERROR` with no partial log.
- [ ] AC-RL-06 the file exposes its functions on `module.exports` and runs `main` only under
  `require.main === module`; loading it with `require` has no side effects.
