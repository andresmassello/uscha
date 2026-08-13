# ACCEPTANCE — REST-shaped item API

- [ ] AC-RH-01 POST /items creates an item with a monotonic id (1, 2, 3, ...) and returns 201
  with the item; ids are never reused, even after a delete.
- [ ] AC-RH-02 GET /items returns all current items in creation order; GET /items/<id> returns
  the item or 404 {"error": "not found"}.
- [ ] AC-RH-03 PUT /items/<id> updates the name and returns 200 with the item, or 404 when the
  id does not exist; DELETE /items/<id> returns 204 with body null, or 404.
- [ ] AC-RH-04 a defined path with an unsupported method returns 405 {"error": "method not
  allowed"} — distinct from 404 (the path exists).
- [ ] AC-RH-05 a POST/PUT body that is missing, not an object, or lacks a name string returns
  400 {"error": "bad request"}; a bad request never aborts the batch.
- [ ] AC-RH-06 state persists across the requests of one input array and starts empty each run;
  input that is not a JSON array of request objects prints exactly ERROR.
