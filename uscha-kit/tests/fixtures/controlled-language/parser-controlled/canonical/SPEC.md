# SPEC — integer arithmetic expression evaluator (EARS + STE authoring)

This canonical package states the same requirements as the free-prose parser SPEC, written
under EARS requirement templates and STE authoring rules: one requirement per sentence, active
voice, a controlled vocabulary (evaluator, expression, value, error), no synonyms for one
concept. The behaviour is unchanged; only the authoring changes.

## Definitions

- The **evaluator** is a program. The evaluator shall read the whole of standard input as one
  expression string. Leading whitespace, trailing whitespace, and a trailing newline are legal.
- A **number** is a non-negative integer literal. Unary minus provides negation.
- The output channel is standard output. The evaluator shall exit with code 0 on every input.

## Result reporting (ubiquitous requirements)

- When the expression is well-formed and evaluable, the evaluator shall print the integer value
  and no other text.
- If the grammar cannot evaluate the input, then the evaluator shall print exactly `ERROR` and
  no other text.

## The grammar (ubiquitous requirements)

- The evaluator shall accept expressions over integers with the binary operators `+`, `-`, `*`,
  `/`, the unary minus, and the parentheses `(` `)`.
- The evaluator shall apply this precedence, from highest to lowest: parentheses; unary minus;
  `*` and `/`; `+` and `-`.
- The evaluator shall treat the binary operators `+`, `-`, `*`, `/` as left-associative.
- The evaluator shall treat whitespace between tokens as insignificant.

## Division (event-driven and unwanted-behaviour)

- When the evaluator divides, the evaluator shall perform integer division that truncates
  toward zero. The value of `-7 / 2` is `-3`. The value of `-7 / 2` is not `-4`.
- If a division has a zero divisor, then the evaluator shall print exactly `ERROR`.

## Malformed input (unwanted-behaviour)

- If the input contains a stray token, then the evaluator shall print exactly `ERROR`.
- If the input contains an unmatched parenthesis, then the evaluator shall print exactly
  `ERROR`.
- If the input is empty, then the evaluator shall print exactly `ERROR`.
- If the input ends with a trailing operator, then the evaluator shall print exactly `ERROR`.

## Examples of intent (illustrative)

The value of `2 + 3 * 4` is `14`. The value of `(2 + 3) * 4` is `20`. The value of
`10 - 2 - 3` is `5`. The value of `-(3 + 4)` is `-7`. The value of `7 / 2` is `3`. The input
`2 +` is `ERROR`.

## Out of scope (do not implement)

The evaluator shall not support floating point, variables, functions, exponentiation, or
bitwise operators. The evaluator shall read one expression. The evaluator shall print one line.
The evaluator shall not print text other than the value or `ERROR`.
