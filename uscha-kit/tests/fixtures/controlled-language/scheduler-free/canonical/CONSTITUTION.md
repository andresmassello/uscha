# CONSTITUTION — priority job scheduler

- **INV-SC-PROGRESS-01 — preemption never loses work.** A preempted job's remaining duration
  is exactly what it was when preempted; the scheduler never restarts, duplicates, or drops a
  job's progress for any reason other than a missed deadline.
