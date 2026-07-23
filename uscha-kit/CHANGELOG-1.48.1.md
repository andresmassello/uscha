# uscha-kit 1.48.1 — one derivation: narrated is labeled, escalation agrees across views (2026-07-23)

Found by running the kit's own QA loop (code-review · judgment-day · improve) over releases
1.46.1–1.48.0 while dogfooding it on this repo. code-review came back clean; the other two
passes returned four gated findings, all real. This is the fix cycle. Smoke suite: 378/378.

## The mirador and the statusline disagreed — twice
`cmd_dashboard` built a repo's state from two ad-hoc sources while `_derive_phase` — the FSM
the statusline's odometer reads — used one. Both halves were wrong:

- **Escalation.** The dashboard scanned `ledger["escalations"]` alone; `_derive_phase` also
  treats an open **spec-doubt**, an open **spec-change-request** and a gated **production
  finding** as escalations. A repo blocked by a spec-doubt read `escalated` in the statusline
  and `active`/`converged` in the mirador.
- **Convergence.** The dashboard took `converged` from `_converged()` alone, which ACCEPTS
  agent-reported `tests_passed` when no snapshot was ever taken; `_derive_phase` requires
  MEASURED green tests before it will say `pr-ready`. So a repo whose tests were only narrated
  read **"convergido"** on the mirador — the view a human reads before deciding a merge —
  while the statusline correctly withheld readiness.

The second one was found by the loop's own second cycle, after the first fix closed only the
escalation half. The dashboard now derives its state ENTIRELY from `_derive_phase`. One
derivation, one truth — including about what "converged" is allowed to mean.

## A checkbox no longer wears a measured face
The statusline rendered `AC 5/6` identically whether it came from `ledger["measured"]` (closed
by a green test) or from counting `- [x]` in ACCEPTANCE.md. The 1.46.1 headline said "never
narrated", but the fallback was real and silent. It now travels with its provenance:
`uscha_progress.py` records `acceptance_source` (`measured` | `narrated`) and the renderer
marks the fallback on screen. Measured is the norm and stays unlabeled; narrated always says
so.

## The fast path now carries what its consumers need
`.claude/uscha-progress.json` gained `measured_at`, `score`, `band` and the full per-repo
`repos` odometer. The `uscha-status` skill documented a `recorded <at> · score <band>` line and
a multi-repo `loops` line that its own primary source could not produce — inviting an agent to
either break the declared source order or invent a timestamp. Now the documented output is
fully producible from the fast path, and the SKILL.md says which field feeds each line.

## One helper instead of five copies
"Max iteration for a repo" was computed independently in five places (mirador badge, readiness
churn, persisted odometer, first-time-yield, regression-close). A change to any one of them
would have silently desynced the others — the root-cause pattern behind the bugs above.
Extracted `_repo_loop_count`; every site calls it.

Regression: smoke **T93** — the checkbox fallback is labeled `narrado` on screen; narrated
tests never read as `convergido` on the mirador; and an open spec-doubt reports `escalated` in
BOTH the mirador badge and the persisted odometer.

## How this release was found
Not by an audit — by running the kit's own loop on itself. Cycle 1: `code-review` clean,
`judgment-day` 3 gated, `improve` 1 gated. Fix. Cycle 2: `code-review` clean, `judgment-day`
clean (all three closed), `improve` found the FIRST FIX WAS PARTIAL and reproduced the
remaining contradiction live. Fix. That is the loop doing exactly what it exists to do: a
second pass that refuses to rubber-stamp the first one.
