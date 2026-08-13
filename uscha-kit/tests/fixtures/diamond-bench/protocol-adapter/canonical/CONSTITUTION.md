# CONSTITUTION — protocol adapter

- **INV-PA-ATOMIC-01 — the batch is atomic and the round-trip is law.** One malformed frame or
  message rejects the whole input (never partial output), and encode∘decode / decode∘encode are
  identities on legal inputs — the adapter never loses, reorders, or invents a field.
