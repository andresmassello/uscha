# ACCEPTANCE — turnstile state machine

- [ ] AC-SM-01 an empty event array ends in the start state `locked`.
- [ ] AC-SM-02 `coin` unlocks a locked turnstile; `push` locks an unlocked one.
- [ ] AC-SM-03 `coin` on an unlocked turnstile stays `unlocked`; `push` on a locked one stays
  `locked` (the machine is total over its events).
- [ ] AC-SM-04 events fold left to right from `locked`; the final state is printed.
- [ ] AC-SM-05 an unknown or non-string event prints exactly `ERROR`.
- [ ] AC-SM-06 input that is not a JSON array prints exactly `ERROR`.
