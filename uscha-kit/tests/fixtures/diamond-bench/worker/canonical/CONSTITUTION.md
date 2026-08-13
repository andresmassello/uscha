# CONSTITUTION — job scheduler

- **INV-WK-DET-01 — one input, one schedule.** The scheduling rule (priority, then input-order
  FIFO, dependencies first) is total and deterministic; failure isolates dependents rather than
  aborting the schedule; structural errors (cycle, unknown or duplicate id) reject the whole
  input rather than emitting a partial schedule.
