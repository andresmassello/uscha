# CONSTITUTION — keyed record store

- **INV-CS-STRICT-01 — create creates and update updates.** Create on an existing key and
  update on a missing key are errors, never silent upserts; results appear in operation order
  and one failed operation never aborts the batch.
