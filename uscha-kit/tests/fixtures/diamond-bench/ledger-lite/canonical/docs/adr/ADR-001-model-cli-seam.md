# ADR-001: The model/CLI seam — acceptance and arithmetic live in `model`, I/O and shape live in `cli`

## Status: Accepted

## Context
A ledger has two concerns that rot when mixed: what a posting MEANS (balanced? duplicate?
which balances move) and how it ARRIVES (JSON on stdin, shape validation, printing). One file
doing both is the default a compiler would produce; the system is deliberately two.

## Decision
- `source/model.py` exposes `post(postings) -> (balances, rejected)`; it performs no I/O,
  imports nothing but the standard library, and is the ONLY place a balance is computed or a
  posting accepted/rejected (INV-LG-SEAM-01, AC-LG-06).
- `source/cli.py` reads stdin, validates SHAPE only (AC-LG-05), calls `model.post`, prints
  (AC-LG-04). It never inspects amounts for balance and never decides acceptance.
- The seam is the function `model.post`; nothing else crosses it.

## Consequences
+ The model is testable without I/O; the CLI is replaceable without touching arithmetic.
- Two files to keep in step; the compiler must emit both and trace both.
