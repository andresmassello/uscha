# uscha-kit 1.41.0 — safety release

Significant backwards-compatible release covering WU1–WU7.

- **WU1:** measured `pr-ready`, fail-closed Ruff/JUnit schemas, and validated counters.
- **WU2:** safe init, authoritative doctor, portable active Claude hook, marketplace preflight, and staged rollback.
- **WU3:** evidence-bearing PF/SD/SCR closure, config validation, and monotonic iterations/counters.
- **WU4:** integration readiness heterogeneous-event false-green prevention, unknown escalation repo rejection, and Spanish ADR label folding.
- **WU5:** ADR templates use AC IDs; the resolved constitution blocker example includes `--escape-analysis`.
- **WU6:** npm router probes usable Python >=3.8 before one installer invocation with no retry; workbench-doctor uses portable Python and the current skill roster.
- **WU7:** complete Claude installation transaction with rollback across managed skills, hook, settings, and marker; T77 covers existing and absent marker rollback.
- **P0 hardening:** Mirador script/DOM injection removed; structured static reports including Clippy fail closed; stale JUnit evidence cannot satisfy `pr-ready`.
- **P1 installer hardening:** init preflights all targets and rejects symlinks; Codex restores marketplace state during rollback; hook matcher and malformed Claude settings are validated.
- **P1 ledger hardening:** readiness configuration is validated completely and PF/SD/SCR closure is immutable after its first resolution.
- **Documentation truth-pass:** exact 29-command reference, npx-first Codex/Claude adoption, eight-skill inventory, completed EN twins, and refreshed diagrams.
- Smoke suite: **351/351 green**.

Known boundary: Codex and Claude targets are independently transactional; `--target both` remains sequential rather than cross-target atomic.
