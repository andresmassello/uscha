# ACCEPTANCE — integer arithmetic expression evaluator (EARS + STE)

- [ ] AC-PR-01 when the expression is well-formed, the evaluator shall print its integer value
  on standard output and shall exit 0.
- [ ] AC-PR-02 the evaluator shall apply the stated precedence and shall treat the binary
  operators as left-associative.
- [ ] AC-PR-03 parentheses shall override precedence; the unary minus shall negate.
- [ ] AC-PR-04 division shall truncate toward zero; if the divisor is zero, then the evaluator
  shall print exactly ERROR.
- [ ] AC-PR-05 if the grammar cannot parse the input, then the evaluator shall print exactly
  ERROR.
- [ ] AC-PR-06 the evaluator shall print only the value or ERROR.
