# ACCEPTANCE — integer expression evaluator

- [ ] AC-PR-01 a well-formed expression evaluates to its integer value on stdout, exit 0.
- [ ] AC-PR-02 precedence and left-associativity hold: `*`/`/` bind tighter than `+`/`-`, and
  same-precedence operators evaluate left to right.
- [ ] AC-PR-03 parentheses override precedence; unary minus negates.
- [ ] AC-PR-04 division is integer division truncating toward zero; division by zero prints
  `ERROR`.
- [ ] AC-PR-05 any input the grammar cannot parse (stray token, unmatched paren, empty, trailing
  operator) prints exactly `ERROR`.
- [ ] AC-PR-06 the program prints only the value or `ERROR` — no prompts, no extra text.
