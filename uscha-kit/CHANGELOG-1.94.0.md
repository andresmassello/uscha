# uscha-kit 1.94.0 — a stack version is a decision with an expiry date: discovery interrogates the lifecycle, and the engine measures "expired before go-live" (ADR-040) (2026-08-21)

From a field run: sixteen ADRs closed with rigor on domain and invariants, but the stack ADR
fixed a major line ("we use X") as if that were a complete decision. Only in the test phase, ten
days before a declared go-live, did it surface that the chosen minor line had left OSS support
months earlier and that a development tool the operator wanted required the next major — a major
upgrade at the milestone that three questions in discovery would have prevented. The method
interrogated WHAT the system must do and WHY it has that shape, but treated the stack as a given,
not as a risk decision with a due date.

## What changed

- **A mandatory "Stack and lifecycle" round** in `uscha-discovery` and `uscha-adr-refine`, before
  the architecture/stack ADR, one question per turn with the agent's recommendation (the method's
  own pattern): the exact version of every runtime/framework/store and its OSS/LTS end-of-support
  date — **verified against the official source at the moment of asking, never from memory, and
  cited (URL + date checked)**; the support window against the declared go-live and expected life
  (if the line stops being patched during the operation, move it up before building); the
  major-dependency upgrade policy, aligned with the devloop's "zero new dependencies without
  approval"; the observability/admin tools the operator wants from day one (they constrain
  versions); the minimum versions the reused legacy modules support.
- **The stack ADR becomes machine-readable**: a `lifecycle:` frontmatter block of
  `{component, version, eol, source, checked}` and a `go_live:` in the SPEC — with a template
  (`uscha-kit/templates/docs/adr/ADR-stack-template.md`) and a CONSTITUTION item: *no stack ADR
  without a cited end-of-support date for every component it fixes*.
- **The engine measures it, advisory only** (never gates, like spec-drift): `spec-check` gains a
  *lifecycle* dimension — per component `ok` / `expires before go-live (<eol> < <go_live>)` /
  `no EOL cited` / `no source cited`, and the whole dimension `UNMEASURED` (with its reason) when
  no ADR declares a lifecycle block or the SPEC declares no go-live. It surfaces in `spec-check`
  text and `--json`, one advisory line in `readiness`, and the `dashboard --json` block. What the
  engine measures is that a date and a source are CITED and that the date precedes go-live; it
  cannot verify the source's truth — the human's fetch does, and the ADR and the doc row say so.
  No readiness cap, no exit-code effect. `readiness`/`dashboard` carry the block only when some
  ADR declares `lifecycle:` — the conditional-key rule `fast_path`/`spec_drift` already follow, so
  every existing byte-identity holds.
- **Dogfood, honestly**: applied to the kit, the declared "py3.8-clean" floor is a *compatibility
  floor for users*, not the kit's runtime — the rule distinguishes the runtime you run from the
  minimum you support; the kit's SPEC declares no go-live, so the dimension reads UNMEASURED here.

`AC-LC-01..05` (T148) measure it: an expiring component reads `expires before go-live` in spec-check
and the readiness advisory; a supported one reads `ok`; a missing date `no EOL cited`, a missing
source `no source cited`; no go-live → UNMEASURED; and the readiness score is byte-identical with or
without an expiring component (advisory, never a gate).

Suite: 436 checks · 0 fail; acceptance 211/211.
