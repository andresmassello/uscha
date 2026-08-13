# SPEC — an in-memory REST-shaped item API (transport-free)

## Contract
- Input: the whole of stdin is a JSON array of requests, each an object
  `{"method": <string>, "path": <string>, "body": <object, optional>}`.
- Output: print a JSON array of responses to stdout and exit 0. Each request maps to one
  response object `{"status": <int>, "body": <value>}`, in request order. On input that is not
  a JSON array of request objects, print exactly `ERROR` (still exit 0).
- The system holds one in-memory collection of items; state persists ACROSS the requests of one
  input array (request 3 sees what request 1 created). Each run starts empty.

## The resource
An item is `{"id": <int>, "name": <string>}`. Ids are assigned by the system: 1 for the first
item ever created in the run, then 2, 3, ... — a monotonic counter. **An id is never reused,
even after its item is deleted.**

## Routes
- `POST /items` with body `{"name": <string>}` → `201` with the created item as body.
- `GET /items` → `200` with the array of all current items, in creation order.
- `GET /items/<id>` → `200` with the item, or `404` with body `{"error": "not found"}`.
- `PUT /items/<id>` with body `{"name": <string>}` → `200` with the updated item, or `404`
  with `{"error": "not found"}`.
- `DELETE /items/<id>` → `204` with body `null`, or `404` with `{"error": "not found"}`.

## Errors, precisely
- A path the API does not define (e.g. `/users`, `/items/1/extra`) → `404` with
  `{"error": "not found"}`.
- A DEFINED path with a method it does not support (e.g. `DELETE /items`, `POST /items/3`)
  → `405` with `{"error": "method not allowed"}`. **405, not 404 — the path exists.**
- `POST /items` or `PUT /items/<id>` whose body is missing, not an object, or has no `name`
  string → `400` with `{"error": "bad request"}`.
- A `<id>` path segment that is not a positive integer → `404` with `{"error": "not found"}`.
- One bad request does NOT abort the batch: it produces its error response and the sequence
  continues.

## Out of scope (do not implement)
No sockets, no HTTP parsing, no headers, no query strings, no persistence beyond one run, no
pagination, no fields besides id and name. The JSON output's formatting is not fixed — only its
structure and values.
