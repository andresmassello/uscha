# SPEC — a priority job scheduler with preemption and deadlines (Diamond bench archetype: decision-dense control logic)

A program that simulates a single-CPU scheduler over discrete ticks and prints what happened.
The only compiler input; describes behaviour, not an implementation and not a test case.

## Contract

- **Input:** standard input is a JSON array of jobs. Each job is an object with exactly the
  fields `id` (integer), `priority` (integer; higher number = higher priority), `arrival`
  (integer tick ≥ 0), `duration` (integer ticks ≥ 0), and optionally `deadline` (integer tick).
  Example: `[{"id": 1, "priority": 5, "arrival": 0, "duration": 3},
  {"id": 2, "priority": 9, "arrival": 1, "duration": 1, "deadline": 3}]`.
- **Output:** print one JSON object to standard output and exit 0:
  `{"events": [[<tick>, <event>, <id>], ...], "completed": [<id>, ...], "missed": [<id>, ...]}`.
  On any malformed input, print exactly `ERROR`.

## The simulation

Time is a sequence of integer ticks starting at 0. At each tick, in this order:

1. **Arrivals.** Every job whose `arrival` equals the current tick becomes ready. Emit
   `[tick, "arrive", id]` for each, in ascending `id` order.
2. **Deadline check.** Every ready or running job whose `deadline` is defined and is **less
   than or equal to** the current tick, and which has not yet completed, is dropped: emit
   `[tick, "missed", id]` (ascending `id` order) and remove it. A job completing at exactly its
   deadline tick has NOT missed (completion is checked at step 4 of the previous tick).
3. **Selection.** Among the ready jobs (including the one that was running last tick, if
   any), pick the one with the highest `priority`; ties break by earliest `arrival`, then by
   lowest `id`. If the picked job differs from the job that ran last tick and last tick's job
   is still ready, emit `[tick, "preempt", <last id>]`. If the picked job was not running last
   tick, emit `[tick, "start", id]` on its first-ever run or `[tick, "resume", id]` on a later
   run. If no job is ready, emit `[tick, "idle", null]`.
4. **Execution.** The picked job runs for this tick: its remaining duration decreases by one.
   If its remaining duration reaches zero, emit `[tick, "complete", id]` and remove it from
   the ready set. A job with `duration` 0 completes in the same tick it starts (emits `start`
   then `complete` at that tick).

The simulation ends after the tick in which the last remaining job completes or is missed —
no `idle` event is emitted once no job is ready and no job is still to arrive. `idle` appears
only on ticks where nothing is ready but at least one job has yet to arrive. `completed`
lists ids in completion order; `missed` lists ids in miss order. An empty input array
produces `{"events": [], "completed": [], "missed": []}`.

## Preemption and resumption

A running job keeps its remaining duration when preempted; when it is selected again it
emits `resume` (not `start`) and continues from where it left off. Preemption never resets
progress.

## Errors

- Input that is not a JSON array → `ERROR`.
- Any element that is not an object, or is missing any of `id`/`priority`/`arrival`/`duration`,
  or whose `id`/`priority`/`arrival`/`duration`/`deadline` is not an integer (JSON booleans are
  not integers), or whose `arrival` or `duration` is negative → `ERROR` for the whole input.
- Duplicate `id` values → `ERROR`.

## Out of scope (state honestly; do not implement)

No multiple CPUs, no aging, no I/O blocking, no priority inheritance, no time slices other
than one tick. The JSON output's formatting is not fixed by this spec — only its structure
and values are. The program reads one array and prints one line: the result object or `ERROR`.
