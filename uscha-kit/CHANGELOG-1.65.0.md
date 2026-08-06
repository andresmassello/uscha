# uscha-kit 1.65.0 — the oracle learns the fix verdict, and the loop reports back (2026-08-06)

Reverse discovery, slice 2 — the oracle half the interview split off from 1.64.0's curation
core. Small on purpose: two mechanisms, both mechanical, both measured.

## Declared divergences — `fix` reaches the golden

A `fix` verdict (ADR-010) says the new system must NOT match the legacy capture. Until now
`golden-diff` had one notion of difference: a blocker. Now the divergence is **declared** in
`golden.divergences.json` — fixture, ADR, reason — and:

- A **declared** pair that diverges reads `expected_divergence`, named with its ADR. Never
  tolerated implicitly: the declaration is the tolerance, reviewed in the PR like everything
  else.
- An **undeclared** divergence blocks exactly as before.
- A declared pair that comes back **byte-identical goes red**: the fix the declaration
  describes is not in the output. An expected divergence that is not observed is a finding,
  not a quiet pass.
- Malformed declarations exit 2 (the `golden.scrub.json` posture): a typo must not degrade
  into "no declarations" — that silence would re-block every expected divergence, or hide a
  declared one.
- Declarations no fixture consumed are reported (`unconsumed_declarations`) — a likely typo,
  visible instead of silent.

## `roundtrip` — subcommand 35, advisory

```bash
python qa_ledger.py roundtrip --repo <name> [--json]
```

Which PROMOTED candidates (the `preserve` + `fix` buckets of the behavior ledger) are
traceable in the code via an embedded `uscha-spec: <candidate>` marker. Coverage by id and a
list of the missing — **deliberately not semantic matching** (ADR-011: that stays out of
scope until it can be measured, and this id layer is its declared prerequisite). Advisory end
to end: exit 0 always, a report, never a gate.

With this, the originating reverse-discovery handoff is fully shipped: candidates in
quarantine (1.64.0), verdicts on the record (1.64.0), the legacy as an oracle that knows the
difference between preserved behavior and declared fixes, and the loop reporting which specs
survived the trip back.

## What the fresh review caught

- **HIGH, an untested interaction**: a declared pair whose raw bytes differ only in a
  scrub-masked volatile landed in the `matched_scrubbed` branch -- a silent, counted pass --
  and the declaration was marked consumed, vanishing from every signal. Scrub-equal IS "not
  observed": behaviorally identical once volatiles are masked means the declared fix is
  absent. The branch now goes red naming the ADR, and T121 covers the interaction.
- **Basename-only keying collided across nested suites**: a declaration for one module's
  fixture would have laundered an unrelated module's undeclared divergence. Lookup now goes
  relpath-first (the `_golden_label` pattern, solved a few dozen lines away), basename as
  the flat-layout convenience -- and only the key that MATCHED is marked consumed, so an
  unexercised twin key still shows as unconsumed.
- `roundtrip` read every tracked file unbounded; a 2MB ceiling now applies (the T112
  lesson: never fully trust the size of content produced by someone else's build).

`AC-RD-08..11` measured green. Suite: 406 checks. Acceptance: **53/53** where `coverage.py`
is installed.
