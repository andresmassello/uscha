# CONSTITUTION — priority job scheduler (EARS + STE)

- **INV-SC-PROGRESS-01 — preemption never loses work.** The program shall keep a preempted
  job's remaining duration exactly equal to the value at the moment of preemption; the program
  shall not restart, duplicate, or drop a job's progress for any reason other than a missed
  deadline.
