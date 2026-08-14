# SPEC — a turnstile state machine (EARS + STE authoring)

This canonical package states the same requirements as the free-prose SPEC, written under EARS
requirement templates and STE authoring rules: one requirement per sentence, active voice, a
controlled vocabulary (program, event, state, fold, print), no ambiguous pronouns, no synonyms
for one concept. The behaviour is unchanged; only the authoring changes.

## Definitions

- The **program** is a stateful reducer over a turnstile.
- A **state** is one of two names: `locked` or `unlocked`. The start state is `locked`.
- An **event** is one of two strings: `coin` or `push`.
- An **unknown event** is an array element that is not the string `coin` and is not the string
  `push`.

## Contract (ubiquitous requirements)

- The program shall read one JSON value from standard input.
- The program shall print one line to standard output.
- The program shall exit with code 0.
- When the input is a JSON array of known event strings, the program shall print the final
  state name.
- When the input is not a JSON array of known event strings, the program shall print exactly
  `ERROR`.

## Transitions (state-driven requirements)

- While the state is `locked`, when the program folds the event `coin`, the program shall move
  the state to `unlocked`.
- While the state is `unlocked`, when the program folds the event `coin`, the program shall
  keep the state `unlocked`.
- While the state is `unlocked`, when the program folds the event `push`, the program shall
  move the state to `locked`.
- While the state is `locked`, when the program folds the event `push`, the program shall keep
  the state `locked`.
- The machine shall be total over the two events: every pair of one state and one event shall
  have exactly one next state, and the four requirements above list every pair.

## Fold (event-driven requirements)

- The program shall fold the events from left to right.
- The program shall start the fold in the state `locked`.
- When the input array is empty, the program shall print the start state `locked`.
- When the fold ends, the program shall print the name of the final state.

## Errors (unwanted-behaviour requirements)

- If an array element is an unknown event, then the program shall print exactly `ERROR`.
- If an array element is not a string, then the program shall print exactly `ERROR`.
- If the input is a JSON object, a bare number, or invalid JSON, then the program shall print
  exactly `ERROR`.

## Out of scope (state honestly; do not implement)

- The program shall not implement other events, counters, emitted actions, or timing.
- The program shall read one array and shall print one line: a state name or `ERROR`.
