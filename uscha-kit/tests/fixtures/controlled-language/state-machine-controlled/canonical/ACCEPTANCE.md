# ACCEPTANCE — turnstile state machine (EARS + STE)

- [ ] AC-SM-01 when the input array is empty, the program shall print the start state `locked`.
- [ ] AC-SM-02 while the state is `locked`, when the program folds `coin`, the program shall
  move the state to `unlocked`; while the state is `unlocked`, when the program folds `push`,
  the program shall move the state to `locked`.
- [ ] AC-SM-03 while the state is `unlocked`, when the program folds `coin`, the program shall
  keep the state `unlocked`; while the state is `locked`, when the program folds `push`, the
  program shall keep the state `locked`; the machine shall be total over the two events.
- [ ] AC-SM-04 the program shall fold the events from left to right, shall start the fold in
  `locked`, and shall print the final state name.
- [ ] AC-SM-05 if an array element is an unknown event or is not a string, then the program
  shall print exactly `ERROR`.
- [ ] AC-SM-06 if the input is not a JSON array, then the program shall print exactly `ERROR`.
