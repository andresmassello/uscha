# SPEC — a keyed record store (CRUD semantics, storage-free)

## Contract
- Input: the whole of stdin is a JSON array of operations. Each operation is an object with an
  `"op"` field: `create`, `read`, `update`, `delete` (each with `"key"`; create/update also with
  `"value"`), or `list` (no other fields required).
- Output: print a JSON array with ONE result per operation, in operation order, and exit 0.
  On input that is not a JSON array of operation objects, print exactly `ERROR` (still exit 0).
- One in-memory store per run, starting empty; state persists across the operations of the run.

## Semantics, precisely
- Keys are strings; values are arbitrary JSON.
- `create`: if the key does NOT exist, store it → `{"ok": true, "result": null}`. If the key
  EXISTS → `{"ok": false, "error": "exists"}`. **Create never overwrites — it is not upsert.**
- `read`: → `{"ok": true, "result": <value>}`, or `{"ok": false, "error": "missing"}`.
- `update`: if the key exists, replace the value → `{"ok": true, "result": null}`; else
  `{"ok": false, "error": "missing"}`. **Update never inserts.**
- `delete`: if the key exists, remove it → `{"ok": true, "result": null}`; else
  `{"ok": false, "error": "missing"}`. After a delete, a create on the same key succeeds.
- `list`: → `{"ok": true, "result": <array of current keys, sorted lexicographically>}`.
- An operation object whose `op` is unknown, or missing a required field for its op
  → `{"ok": false, "error": "bad op"}`. A failed operation never aborts the batch.

## Out of scope (do not implement)
No persistence, no transactions, no TTLs, no nested-key paths, no value validation. Output
formatting is free; only structure and values are fixed.
