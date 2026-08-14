# ACCEPTANCE — record-shape transformer (EARS + STE)

- [ ] AC-TR-01 when the program maps a record, the program shall emit an output object with
  `name` and `adult`; the program shall set `name` to first + one space + last.
- [ ] AC-TR-02 the program shall set `adult` to the value of `age >= 18`; the age 18 shall map
  to `true`; the age 17 shall map to `false`.
- [ ] AC-TR-03 the program shall keep the output order equal to the input order; when the input
  array is empty, the program shall print an empty array.
- [ ] AC-TR-04 if the input is not a JSON array, then the program shall print exactly `ERROR`.
- [ ] AC-TR-05 if a record misses any of the fields first/last/age, or a field carries a wrong
  type, then the program shall print exactly `ERROR` for the whole batch; the program shall not
  emit a partial result.
- [ ] AC-TR-06 this spec fixes the structure and the values of the output; this spec does not
  fix the JSON formatting.
