# uscha-kit 1.67.0 — the handoff's last residue: clean-room reaches the readouts (2026-08-10)

A re-audit of the originating three-phase handoff against the shipped repo found exactly one
unimplemented line: §2.3 asked `/uscha-status` and the mirador to show the clean-room state,
and neither did. The gate itself has blocked `pr-ready` (naming the missing SHA) since
1.63.0 — but a gate you only discover by being blocked is visibility by ambush.

- The **mirador modes card** now draws the latest clean-room run per repo: `GREEN` green,
  `RED` red, everything else (`SETUP_FAILED`, `WORKTREE_*`) amber, with the SHA and the
  wall-clock (the cost stays visible). Same card, same conditional rule: no runs → no rows,
  and a ledger with none of the mode keys hides the card entirely.
- **`/uscha-status`** gains its one line: `clean-room: GREEN @ <sha8> (12.3s)`, with
  `(stale for gate)` appended when `mode: "final"` is declared and the run no longer matches
  HEAD. Absent key → no line.

With this, every deliverable in the fast-path/clean-room/spec-drift handoff is either
shipped or explicitly superseded by a recorded decision (the config-executed suite → ADR-008;
the always-on gate default → ADR-007/008; the shared drift engine → ADR-011).

Suite: 406 checks. Acceptance: **55/55** where `coverage.py` is installed.
