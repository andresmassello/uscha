# SPEC — a turnstile state machine (Diamond bench archetype: stateful reducer)

A program that folds a sequence of events over a turnstile and prints the resulting state. The
only compiler input; describes behaviour, not an implementation and not a test case.

## Contract

- **Input:** standard input is a JSON array of event strings, e.g. `["coin", "push"]`.
- **Output:** print the final state name to standard output and exit 0. On any input that is not
  a JSON array of known event strings, print exactly `ERROR`.

## The machine

Two states: **`locked`** (the start state) and **`unlocked`**. Two events:

- **`coin`** — in `locked`, go to `unlocked`; in `unlocked`, stay `unlocked`.
- **`push`** — in `unlocked`, go to `locked`; in `locked`, stay `locked`.

Fold the events left to right from the start state `locked`; print the state you end in. An
**empty** array ends in `locked` (the start state). The machine is **total** over its two
events: every (state, event) pair has a defined next state, listed above.

## Errors

- An event that is not one of `coin` / `push` (an unknown string, or a non-string element) →
  `ERROR`.
- Input that is not a JSON array (a JSON object, a bare number, invalid JSON) → `ERROR`.

## Out of scope (state honestly; do not implement)

No other events, no counters, no emitted actions beyond the final state name, no timing. The
program reads one array and prints one line: a state name or `ERROR`.
