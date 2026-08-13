# SPEC — a job scheduler (concurrent-worker semantics, specified deterministically)

## Stated boundary (read first)
This system captures a concurrent worker's COORDINATION logic — priorities, dependencies,
failure isolation — under a DETERMINISTIC scheduling rule, so that one input has exactly one
correct output. It does not exercise real parallelism, threads, or timing; that is out of its
scope by design.

## Contract
- Input: the whole of stdin is a JSON object `{"jobs": [<job>, ...]}`. A job is
  `{"id": <string>, "priority": <int>, "needs": [<job id>, ...], "fails": <bool, optional>}`
  (`needs` may be absent = no dependencies; `fails` absent = false).
- Output: print a JSON object `{"order": [...], "status": {...}}` and exit 0. On input that is
  not an object with a jobs array of well-formed jobs, on a duplicate job id, on a `needs`
  naming an unknown id, or on a dependency cycle, print exactly `ERROR` (still exit 0).

## Scheduling semantics, precisely
- A job is READY when every job in its `needs` has completed with status `ok`.
- Repeat until nothing is runnable: among READY jobs not yet run, execute the one with the
  HIGHEST `priority`; on a priority tie, the one that appears FIRST in the input array (FIFO —
  the deterministic tie-break).
- Executing a job with `fails: true` gives it status `failed`. A failed job's dependents (and
  transitively theirs) are never executed: status `skipped`.
- `order` is the list of job ids actually EXECUTED (status `ok` or `failed`), in execution
  order. `status` maps every job id to `ok`, `failed`, or `skipped`.

## Out of scope (do not implement)
No real concurrency, no timers, no retries, no partial re-runs, no resource limits. Output
formatting is free; only structure and values are fixed.
