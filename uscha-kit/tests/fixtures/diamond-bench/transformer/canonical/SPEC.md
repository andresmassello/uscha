# SPEC — a record-shape transformer (Diamond bench archetype: data migration / ETL-lite)

A program that reshapes a list of person records. The only compiler input; describes behaviour,
not an implementation and not a test case.

## Contract

- **Input:** standard input is a JSON array of records, each an object with exactly the fields
  `first` (string), `last` (string), and `age` (integer), e.g.
  `[{"first": "Ada", "last": "Lovelace", "age": 36}]`.
- **Output:** print a JSON array to standard output and exit 0. Each input record maps to an
  output object `{"name": <first> + " " + <last>, "adult": <age >= 18>}`. **Output order is the
  input order.** On any malformed input, print exactly `ERROR`.

## The mapping

For each record: `name` is the first name, a single space, and the last name, concatenated;
`adult` is the boolean `age >= 18` (so 18 is an adult, 17 is not). The output array has one
object per input record, in the same order. An empty input array produces an empty output
array.

## Errors

- Input that is not a JSON array → `ERROR`.
- A record that is not an object, or is missing any of `first` / `last` / `age`, or whose `age`
  is not an integer, or whose `first` / `last` is not a string → `ERROR` for the whole input
  (fail the batch; do not emit a partial result).

## Out of scope (state honestly; do not implement)

No other fields are read or preserved; no sorting, no deduplication, no filtering. The JSON
output's formatting (whitespace, key order within an object) is not fixed by this spec — only
its structure and values are. The program reads one array and prints one line: the transformed
array or `ERROR`.
