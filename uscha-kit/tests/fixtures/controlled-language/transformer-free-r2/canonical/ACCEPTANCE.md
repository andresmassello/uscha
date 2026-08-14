# ACCEPTANCE — record-shape transformer

- [ ] AC-TR-01 each record maps to `{name, adult}` with `name` = first + space + last.
- [ ] AC-TR-02 `adult` is `age >= 18` (18 is an adult, 17 is not).
- [ ] AC-TR-03 output order equals input order; an empty array maps to an empty array.
- [ ] AC-TR-04 input that is not a JSON array prints exactly `ERROR`.
- [ ] AC-TR-05 a record missing any of first/last/age, or with a wrong-typed field, prints
  exactly `ERROR` for the whole batch (no partial output).
- [ ] AC-TR-06 only the structure and values of the output are fixed, not its JSON formatting.
