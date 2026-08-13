# CONSTITUTION — REST-shaped item API

- **INV-RH-IDS-01 — ids are history, not slots.** The id counter is monotonic for the run; a
  deleted item's id is never reassigned; responses appear in request order and one request's
  error never aborts the rest of the batch.
