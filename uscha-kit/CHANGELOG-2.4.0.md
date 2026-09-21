# uscha-kit 2.4.0 — a full devloop cycle ran on Codex end to end, and found five gaps the kit had never had to close (2026-09-20)

## The pilot (ADR-049)

On 2026-09-20 the full `/uscha-devloop` cycle ran end to end on OpenAI Codex (desktop app,
GPT-5.6, kit 2.3.0) against a small greenfield Python repo with one acceptance criterion — a
greenfield pilot repo, no client or project name involved. It worked: six green tests, 100% line
coverage, a 33-step ledger, CONVERGED, the criterion closed MEASURED, stopped cleanly at the
merge gate. Its own judgment-day pass found a real SPEC ambiguity and asked the human instead of
picking one silently — the method's own discipline, reproduced on a vendor it was never tuned
against. The run also found five defects, all in the assumptions Claude Code's surface had let
the kit lean on without ever naming them. Each is reproduced and fixed below; ADR-049 is the full
account.

## Fix 1: no coverage report is UNMEASURED, not 0%

`check-coverage` used to print "NO coverage report found ... -> treat as BELOW" and exit 1 — the
same exit and the same word a real, low-scoring report produces. On a fresh repo that read as
"tested and failing" when the truth was "never run". It now exits **2** (fail-closed, the kit's
existing convention for a refused reading) and prints `coverage UNMEASURED -- no coverage report
found`, naming the path it looked for. The devloop SKILL's Phase 1 now separates the two branches
explicitly: BELOW (exit 1, a real report) still means write characterization tests; UNMEASURED
(exit 2, no report) means run the test command with coverage first — characterization is for code
nobody has tested yet, never for code that has not been run at all.

## Fix 2: `uscha init` writes a scoped `.gitignore`

`cmd_init` now writes a minimal, per-repo-type `.gitignore` when the repo has none —
`__pycache__/`, `*.pyc`, `.pytest_cache/`, `.coverage` for python; `node_modules/` for node; and
matching minimal sets for the other repo types `detect_repo_type` already recognises. `reports/`
is never in it, in any repo type's set: it is the ledger's own evidence directory (JUnit,
coverage, smoke), and the devloop SKILL now says so explicitly. An EXISTING `.gitignore` is left
byte-identical — even under `--force` — so a second `init` reports it unchanged.

## Fix 3: progress is visible on surfaces without a statusline

The statusline and its Stop hook only wire into `.claude/settings.json`; on Codex nothing renders
them. The generated orientation block (`tools/skill-blocks/`, rendered into all 18 `SKILL.md`
files) now states that on a surface with no live statusline — Codex, pi, a plain terminal — the
markers are the operator's only signal and MUST appear in the visible reply text, and the final
message of every turn there opens with the compact `uscha-status` readout before the
breadcrumb/close marker.

## Fix 4: closing ticks the checkbox

The pilot's readiness read "measured but unticked: AC-1" at the end of a converged run. The
devloop SKILL now instructs: for every ID `readiness` reports as `measured_unchecked`, flip that
checkbox in `ACCEPTANCE.md` (the engine measured it; ticking is bookkeeping, never the reverse),
then re-run `readiness` and confirm the list is empty before closing.

## Fix 5: `pr-ready` is a phase value, never a subcommand

While reading the pilot's ledger the OPERATOR typed `qa_ledger.py pr-ready` and hit an argparse error -- the agent never did; the correct
form has always been `phase --repo R --require pr-ready`. An audit of every doc, skill, README,
ADR and deck in the repo found the phrasing already correct everywhere it is documented — the
confusion lived in the agent's recall, not in a doc that taught it wrong. The devloop SKILL now
states the rule explicitly, by name, right beside the command.

## Docs

- The deck twins (`docs/uscha-claude-code-doc.html` / `-EN.html`) mark a full `/uscha-devloop` run
  on Codex as **verified** (2026-09-20, Codex desktop app, GPT-5.6, converged clean on a
  greenfield pilot repo), naming the two limits that remain: no hooks on Codex (the golden write
  guard is not enforced there) and no statusline (fix 3 is the mitigation).
- `docs/FIRST-USE.md` / `-EN.md` add the Codex run under "Verified on".
- `uscha-kit/README.md` and the root `README.md` note that `init` now also writes a `.gitignore`.
- `docs/adr/ADR-049-codex-end-to-end-pilot.md`, `docs/adr/INDEX.md` gains its row (method group).

## Also on main since v2.3.0

- `feat(site)`: a real 404 page — Pages was answering missing paths with the home page and a 200.
- `docs(bench)`: the nine known under-specifications of the v1 canonical packages are registered
  (AMB-01..09) — registered, not fixed; ADR-042 links the register.

## Not in this release

No risk-profile default moved, no coverage threshold changed — only what an ABSENT report
reports. No new subcommand: `check-coverage` and `init` keep their existing shape.

Suite: __SUITE__ checks · 0 fail; acceptance __ACC__.
