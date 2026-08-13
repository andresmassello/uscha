# SPEC — integer arithmetic expression evaluator (Diamond bench archetype: parser / pure function)

A small program that reads one arithmetic expression and prints its integer value. The only
compiler input; describes required behaviour, not an implementation and not a test case.

## Contract

- **Input:** the whole of standard input is a single expression string (it may contain leading
  or trailing whitespace and a trailing newline).
- **Output:** print the result to standard output and exit 0. On success, print the integer
  value with no extra text. On any input the grammar below cannot evaluate, print exactly
  `ERROR` (and still exit 0). Output nothing else.

## The grammar

Expressions over **integers** with the binary operators `+ - * /`, unary minus, and
parentheses `( )`. Standard precedence: parentheses, then unary minus, then `*` and `/`, then
`+` and `-`. Binary `+ - * /` are **left-associative**. Whitespace between tokens is
insignificant. Numbers are non-negative integer literals (a unary `-` provides negation).

- **Division is integer division that truncates toward zero** (so `-7 / 2` is `-3`, not `-4`).
- **Division by zero is an error** — print `ERROR`.
- Anything the grammar cannot parse — a stray token, an unmatched parenthesis, an empty input, a
  trailing operator — is an error: print `ERROR`.

## Examples of intent (illustrative, not the checker's cases)

`2 + 3 * 4` is `14`. `(2 + 3) * 4` is `20`. `10 - 2 - 3` is `5` (left-associative). `-(3 + 4)`
is `-7`. `7 / 2` is `3`. A malformed `2 +` is `ERROR`.

## Out of scope (state honestly; do not implement)

No floating point, no variables, no functions, no exponentiation, no bitwise operators. The
program reads one expression and prints one line. It does not read files, take arguments, or
produce any output other than the value or `ERROR`.
