# ACCEPTANCE — keyed record store

- [ ] AC-CS-01 create stores a new key and returns ok; create on an existing key returns
  {"ok": false, "error": "exists"} and does NOT overwrite (never upsert).
- [ ] AC-CS-02 read returns the stored value, or {"ok": false, "error": "missing"}.
- [ ] AC-CS-03 update replaces the value of an existing key; update on a missing key returns
  "missing" and does NOT insert.
- [ ] AC-CS-04 delete removes an existing key (a later create on it succeeds); delete on a
  missing key returns "missing".
- [ ] AC-CS-05 list returns the current keys sorted lexicographically.
- [ ] AC-CS-06 an unknown op or one missing its required fields returns {"ok": false, "error":
  "bad op"}; a failed operation never aborts the batch; non-array input prints exactly ERROR.
