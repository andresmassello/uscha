# SPEC — a form view-model (small UI, presentation-free)

## Contract
- Input: the whole of stdin is a JSON object `{"model": <model>, "events": [<event>, ...]}`.
  The model is `{"fields": [{"name": <string>, "value": <string or bool>}, ...]}` — the form's
  INITIAL state. Field names are unique.
- Output: print the final VIEW as a JSON object and exit 0:
  `{"fields": {<name>: <current value>, ...}, "submitted": <bool>, "errors": [<field names>]}`.
  On malformed input (shape errors, a duplicate field name, an event naming an unknown field),
  print exactly `ERROR` (still exit 0).

## Events, applied in order
- `{"type": "input", "field": F, "value": V}` — sets string field F to V.
- `{"type": "toggle", "field": F}` — flips boolean field F (toggle on a string field, or input
  on a boolean field, is a malformed input → `ERROR`).
- `{"type": "reset"}` — restores EVERY field to its INITIAL model value (not to empty), sets
  submitted to false, clears errors.
- `{"type": "submit"}` — validation: every STRING field must be non-empty. If any string field
  is the empty string, `submitted` stays false and `errors` becomes the list of the empty
  fields' names, in field order. If all pass, `submitted` becomes true and `errors` empties.
  Later events keep applying after a failed submit.

## The view, precisely
`fields` maps every field name to its CURRENT value; `submitted` and `errors` reflect the state
after the last event. A form with no events renders its initial model, submitted false, errors
empty.

## Out of scope (do not implement)
No rendering to HTML/text, no styling, no focus, no async, no field types beyond string and
bool. Output formatting is free; only structure and values are fixed.
