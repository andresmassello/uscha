# ACCEPTANCE — job scheduler

- [ ] AC-WK-01 jobs run dependencies-first: a job never executes before every job in its needs
  has completed ok.
- [ ] AC-WK-02 among ready jobs, the highest priority runs first; a priority tie breaks by
  input order (FIFO) — the schedule is deterministic.
- [ ] AC-WK-03 a job with fails true gets status failed; its dependents, transitively, are
  never executed and get status skipped.
- [ ] AC-WK-04 order lists exactly the executed jobs (ok or failed) in execution order; status
  maps every job to ok, failed, or skipped.
- [ ] AC-WK-05 a duplicate job id, an unknown id in needs, or a dependency cycle prints exactly
  ERROR — never a partial schedule.
- [ ] AC-WK-06 malformed input (not an object with a well-formed jobs array) prints exactly
  ERROR.
