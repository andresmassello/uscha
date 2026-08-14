# CONSTITUTION — turnstile state machine

- **INV-SM-TOTAL-01 — the machine is total and closed.** Every (state, event) pair has a
  defined next state; an event outside the known set is rejected, never left undefined or
  silently ignored.
