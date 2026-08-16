# CONSTITUTION — token-bucket rate limiter

- **INV-RL-CLAMP-01 — tokens never leave `[0, capacity]`.** No sequence of events can make
  the token count negative or exceed `capacity`; a `req` at zero tokens is denied, a `tick` at
  full capacity is a no-op.
