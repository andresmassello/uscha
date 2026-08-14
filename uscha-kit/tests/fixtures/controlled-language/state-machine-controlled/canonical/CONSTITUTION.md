# CONSTITUTION — turnstile state machine (EARS + STE)

- **INV-SM-TOTAL-01 — the machine is total and closed.** Every pair of one state and one event
  shall have exactly one defined next state; the program shall reject an event outside the
  known set; the program shall not leave a pair undefined; the program shall not ignore an
  event silently.
