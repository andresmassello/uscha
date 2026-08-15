# ACCEPTANCE — priority job scheduler

- [ ] AC-SC-01 jobs become ready at their `arrival` tick (an `arrive` event each, ascending id).
- [ ] AC-SC-02 at each tick the ready job with the highest `priority` runs; ties break by
  earliest `arrival`, then lowest `id`.
- [ ] AC-SC-03 a higher-priority arrival preempts the running job (`preempt` event); the
  preempted job keeps its remaining duration and later emits `resume`, never a second `start`.
- [ ] AC-SC-04 a job whose `deadline` is ≤ the current tick and is not complete is dropped with
  a `missed` event before selection; a job completing at exactly its deadline tick is NOT
  missed.
- [ ] AC-SC-05 a job with `duration` 0 emits `start` and `complete` at the same tick; a tick
  with no ready job emits `idle`.
- [ ] AC-SC-06 the output object carries `events` in tick order, `completed` in completion
  order and `missed` in miss order; an empty input yields empty arrays.
- [ ] AC-SC-07 malformed input (not an array, missing/mistyped fields, boolean where integer,
  negative arrival/duration, duplicate ids) prints exactly `ERROR` for the whole input.
