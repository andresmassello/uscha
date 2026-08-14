# SPEC — a record-shape transformer (EARS + STE authoring)

This canonical package states the same requirements as the free-prose SPEC, written under EARS
requirement templates and STE authoring rules: one requirement per sentence, active voice, a
controlled vocabulary (program, record, field, output object, batch), no ambiguous pronouns,
no synonyms for one concept. The behaviour is unchanged; only the authoring changes.

## Definitions

- The **program** is a record-shape transformer.
- A **record** is a JSON object with exactly the fields `first` (string), `last` (string), and
  `age` (integer).
- An **output object** is a JSON object with the fields `name` (string) and `adult` (boolean).
- A **malformed input** is an input that is not a JSON array, or an input array that contains
  an element that is not a record.

## Contract (ubiquitous requirements)

- The program shall read one JSON value from standard input.
- The program shall print one line to standard output.
- The program shall exit with code 0.
- When the input is a JSON array of records, the program shall print a JSON array of output
  objects.
- When the input is a malformed input, the program shall print exactly `ERROR`.

## The mapping (event-driven requirements)

- When the program maps a record, the program shall set `name` to the value of `first`, one
  space character, and the value of `last`, concatenated in that order.
- When the program maps a record, the program shall set `adult` to the boolean value of the
  comparison `age >= 18`; the age 18 shall map to `true`; the age 17 shall map to `false`.
- The program shall emit one output object per input record.
- The program shall keep the output order equal to the input order.
- When the input array is empty, the program shall print an empty JSON array.

## Errors (unwanted-behaviour requirements)

- If the input is not a JSON array, then the program shall print exactly `ERROR`.
- If an array element is not a JSON object, then the program shall print exactly `ERROR`.
- If a record misses the field `first`, the field `last`, or the field `age`, then the program
  shall print exactly `ERROR`.
- If the field `age` is not an integer, then the program shall print exactly `ERROR`.
- If the field `first` or the field `last` is not a string, then the program shall print
  exactly `ERROR`.
- When the program prints `ERROR`, the program shall fail the whole batch; the program shall
  not emit a partial result.

## Out of scope (state honestly; do not implement)

- The program shall not read other fields; the program shall not preserve other fields.
- The program shall not sort, deduplicate, or filter records.
- This spec fixes the structure and the values of the JSON output; this spec does not fix the
  whitespace or the key order of the JSON output.
- The program shall read one array and shall print one line: the transformed array or `ERROR`.
