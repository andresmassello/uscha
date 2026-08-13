# CONSTITUTION — form view-model

- **INV-UI-RESET-01 — reset means the initial model.** Reset restores the model the form was
  born with, never a cleared one; validation reports the offending fields rather than mutating
  them; the view is a pure function of initial model + event sequence.
