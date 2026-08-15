# SPEC — a priority job scheduler with preemption and deadlines (EARS + STE authoring)

This canonical package states the same requirements as the free-prose SPEC, written under EARS
requirement templates and STE authoring rules: one requirement per sentence, active voice, a
controlled vocabulary (program, job, tick, ready, running, event, complete, miss), no
ambiguous pronouns, no synonyms for one concept. The behaviour is unchanged; only the
authoring changes.

## Definitions

- The **program** is a single-CPU scheduler simulator over discrete ticks.
- A **tick** is an integer time step. The first tick is 0.
- A **job** is a JSON object with exactly the fields `id` (integer), `priority` (integer; a
  higher number is a higher priority), `arrival` (integer tick ≥ 0), `duration` (integer
  ticks ≥ 0), and optionally `deadline` (integer tick).
- A job is **pending** before its arrival tick; a job is **ready** from its arrival tick until
  the job completes or the job is missed; the **running job** is the ready job the program
  selected in the current tick.
- The **remaining duration** of a job starts equal to `duration` and decreases by one for
  every tick the job runs.
- An **event** is a JSON array `[tick, name, id]`; the event names are `arrive`, `missed`,
  `preempt`, `start`, `resume`, `idle`, `complete`; the `id` of an `idle` event is `null`.
- A **malformed input** is an input that is not a JSON array, or an array with an element that
  is not a job, or an array with a job whose `id`, `priority`, `arrival`, `duration` or
  `deadline` is not an integer (a JSON boolean is not an integer), or a job whose `arrival` or
  `duration` is negative, or two jobs that share one `id`.

## Contract (ubiquitous requirements)

- The program shall read one JSON value from standard input.
- The program shall print one line to standard output.
- The program shall exit with code 0.
- When the input is a JSON array of jobs, the program shall print one JSON object
  `{"events": [...], "completed": [...], "missed": [...]}`.
- When the input is a malformed input, the program shall print exactly `ERROR`.
- When the input array is empty, the program shall print
  `{"events": [], "completed": [], "missed": []}`.

## The tick (event-driven requirements, executed in this order at every tick)

- **Step 1 — arrivals.** When a job's `arrival` equals the current tick, the program shall
  make the job ready and shall emit `[tick, "arrive", id]`; the program shall emit the
  `arrive` events of one tick in ascending `id` order.
- **Step 2 — deadline check.** When a ready job has a `deadline` and the `deadline` is less
  than or equal to the current tick and the job is not complete, the program shall emit
  `[tick, "missed", id]`, shall append the `id` to `missed`, and shall remove the job; the
  program shall emit the `missed` events of one tick in ascending `id` order. A job that
  completed at exactly its `deadline` tick shall not be missed (step 4 of the previous tick
  completes before step 2 of this tick).
- **Step 3 — selection.** While at least one job is ready, the program shall select the ready
  job with the highest `priority`; if two ready jobs share the highest `priority`, then the
  program shall select the job with the earlier `arrival`; if two ready jobs share the highest
  `priority` and the same `arrival`, then the program shall select the job with the lower
  `id`. If the selected job differs from the running job of the previous tick and the previous
  running job is still ready, then the program shall emit `[tick, "preempt", previous id]`. If
  the selected job did not run in the previous tick and the selected job has never run, then
  the program shall emit `[tick, "start", id]`; if the selected job did not run in the previous
  tick and the selected job has run before, then the program shall emit `[tick, "resume", id]`.
  While no job is ready and at least one job is pending, the program shall emit
  `[tick, "idle", null]`.
- **Step 4 — execution.** When a job is selected, the program shall decrease the job's
  remaining duration by one, unless the remaining duration is already zero. When the remaining
  duration reaches zero, the program shall emit `[tick, "complete", id]`, shall append the
  `id` to `completed`, and shall remove the job. When a job's `duration` is zero, the program
  shall emit `start` and `complete` for the job in the same tick.
- The program shall end the simulation after the tick in which the last remaining job
  completes or is missed; the program shall not emit an `idle` event when no job is ready and
  no job is pending.

## Preemption and resumption (state-driven requirements)

- While a job is preempted, the program shall keep the job's remaining duration unchanged.
- When a preempted job is selected again, the program shall emit `resume`; the program shall
  not emit a second `start` for one job.

## Errors (unwanted-behaviour requirements)

- If the input is a malformed input, then the program shall print exactly `ERROR` for the
  whole input; the program shall not print a partial result.

## Out of scope (state honestly; do not implement)

- The program shall not implement multiple CPUs, aging, I/O blocking, priority inheritance,
  or a time slice other than one tick.
- This spec fixes the structure and the values of the JSON output; this spec does not fix the
  whitespace or the key order of the JSON output.
- The program shall read one array and shall print one line: the result object or `ERROR`.
