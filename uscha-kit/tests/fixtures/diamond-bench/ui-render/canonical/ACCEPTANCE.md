# ACCEPTANCE — form view-model

- [ ] AC-UI-01 input sets a string field; toggle flips a boolean field; events apply in order.
- [ ] AC-UI-02 reset restores every field to its INITIAL model value — not to empty — and
  clears submitted and errors.
- [ ] AC-UI-03 submit with any empty string field keeps submitted false and lists exactly the
  empty fields, in field order, in errors.
- [ ] AC-UI-04 submit with all string fields non-empty sets submitted true and empties errors.
- [ ] AC-UI-05 the view maps every field to its current value and reflects the state after the
  last event; no events renders the initial model.
- [ ] AC-UI-06 an unknown field in an event, a type mismatch (toggle on string, input on bool),
  a duplicate field name, or a malformed shape prints exactly ERROR.
