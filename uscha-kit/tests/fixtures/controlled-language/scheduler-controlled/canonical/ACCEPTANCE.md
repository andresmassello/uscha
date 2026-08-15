# ACCEPTANCE — priority job scheduler (EARS + STE)

- [ ] AC-SC-01 when a job's `arrival` equals the current tick, the program shall make the job
  ready and shall emit one `arrive` event; the program shall order the `arrive` events of one
  tick by ascending `id`.
- [ ] AC-SC-02 at each tick the program shall run the ready job with the highest `priority`;
  the program shall break ties by earliest `arrival`, then by lowest `id`.
- [ ] AC-SC-03 when a higher-priority job arrives, the program shall preempt the running job
  (`preempt` event); the program shall keep the preempted job's remaining duration and shall
  emit `resume` when the job runs again, never a second `start`.
- [ ] AC-SC-04 when a job's `deadline` is less than or equal to the current tick and the job
  is not complete, the program shall drop the job with a `missed` event before selection; a
  job that completes at exactly its `deadline` tick shall not be missed.
- [ ] AC-SC-05 when a job's `duration` is 0, the program shall emit `start` and `complete` at
  the same tick; when no job is ready and a job is pending, the program shall emit `idle`.
- [ ] AC-SC-06 the program shall print `events` in tick order, `completed` in completion order
  and `missed` in miss order; when the input is empty, the program shall print empty arrays.
- [ ] AC-SC-07 if the input is malformed (not an array, missing or mistyped fields, a boolean
  where an integer is required, negative arrival or duration, duplicate ids), then the
  program shall print exactly `ERROR` for the whole input.
