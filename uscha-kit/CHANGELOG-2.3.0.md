# uscha-kit 2.3.0 — the deck stops being Claude-only, and the paper cites the review it did not have (2026-09-20)

This is a DOCUMENTATION release: no engine change, no ADR. It covers everything that landed on
main since v2.2.0.

## The deck: seven agents, not one

`docs/uscha-claude-code-doc.html` / `-EN.html` said "Claude Code" nineteen times and "Codex"
zero, although the kit installs on seven agents (`uscha-kit/install-uscha.py`: `TARGETS =
("codex", "claude") + SKILL_ROOTS`, where `SKILL_ROOTS` is `pi`, `cursor`, `copilot`, `gemini`,
`cline`). The opening slide, the specification-overview diagram's bottom-strip label, and the
"pieces that hold it up" slide are reframed to the agent generically; the latter gains a table —
Claude Code (skills, sub-agents, hooks including the INV-GOLDEN-01 write hook, `--add-dir`),
Codex (`.codex-plugin` + skills + `AGENTS.md`; no native hooks, so the golden guard is **not**
enforced there — said plainly, not hidden), and the five skill-root targets (skills only) — plus
an honesty line: verified on Codex is installation, `AGENTS.md`, the portable prompts and the
cross-vendor compilation arm (ADR-042); NOT verified is a full `/uscha-devloop` run end to end on
Codex. The "reproduce the environment" slide, which documents the *author's own* Claude Code
Desktop setup, now says so explicitly and adds the cross-agent install line
(`npx --yes @andresmassello/uscha@latest install --target codex`) next to it. Every other "Claude
Code" mention that is factually about Claude Code (CLAUDE.md's own read loop, the Implementation
Plan, the workbench, the worked session) is unchanged.

## Two new slides: the deck's narrative catches up to 2.x

Both twins gain two slides, inserted right before "When NOT to use Uscha" so no `#NN` deep link
in `site/` or `README.md` shifts (none reference this doc by slide number):

- **The Diamond, measured** — twelve archetypes, a withheld oracle, four blind compilers from
  two vendors, 8 of 12 PASS (`8 PASS · 4 PARTIAL`), round-trip recoverability 0.815, and 221
  human curation verdicts (213 preserve, 8 fix, none unjudged).
- **2.x: the kit under its own instruments** — ADR-041 (the release ritual as a refusing script,
  freshness by git ancestry), the facts gate (1.97.0, born because the homepage said "9/12" for
  nine releases after the number moved), 2.0.0 (`init` generates instead of copying, so risk
  presets take effect for the first time), 2.1.0 (SIMPLICITY advisory by default, ADR-043), and
  2.2.0's five ADRs (`origin: agent`, `corpus-run`, `smoke-ingest`, `operability`, the installed-skill
  version marker).

The deck is now 38 slides in both twins (was 36); `AC-VC-02`'s changed-line count between the
twins since `base` stays symmetric.

## The paper cites an independent finding on the review side

`docs/paper/uscha-paper.tex` and its hand-maintained HTML twin gain a Related Work paragraph
citing N. Garg, "When Spec-Driven Development Pays Off" (InfoQ, September 2026, accepted at
GAISS 2026) — verified by reading the published article, not taken on faith. Its measurement is
reviewer attribution and time, not regeneration under a withheld oracle, so it is cited as
independent evidence at the review stage, explicitly **not** as validation of the Diamond
program; the source's own confound (part of the "specify first" effect may be a reasoning effect)
is stated as the source states it. Two lines join Limitations — no control isolates a
reasoning-first baseline here, so the quality claim is defensible only for multi-constraint work;
the human cost of spec-anchored review is unmeasured in this work — and Future Work gains a short
paragraph: as models improve, the package's value plausibly shifts from "regenerates better"
toward an auditable contract, every verdict attributable to a named criterion and, where a human
judged, to the person who signed it. The PDF is regenerated from the HTML twin.

## Site and README: who signed what

`site/index.html`, `site/es/index.html` and `README.md` each gain one paragraph: every verdict in
the ledger is tied to a named criterion, and where a human judged it, to the person who signed
it — sourced from the ledger itself, `bench-curate --human` for the Diamond bench's compiled
artifacts, and the `origin: agent` markers. No compliance claim, no named standard.

## Also since v2.2.0

- The cross-vendor Diamond arm finished human curation: 87 preserve verdicts recorded for the 21
  remaining Codex compilations, joining the 26 from the guard archetype — 221 total, the
  cross-vendor arm fully curated.
- The paper's round 2: the cross-vendor flip, the post-1.90.0 arc, Figure 2 regenerated from a
  source that now exists.
- The discovery skill gained two advisory habits, stated as constraints rather than left
  implicit: magnitudes carry a number or a range, and rules are written so a reader can tell what
  they forbid.
- The Pages deploy was restored after reconnecting the repository.

`base` in `tools/narrated-claims.txt` moved from `v1.97.0` to `223ec9e` (commit b6e07b3, after 2.2.0), and this release leaves it there — the commit that carries the
deliberately asymmetric ES deck edit (the parser-surface paragraph got its own line while the EN
twin already had it) — because this release's deck edits are symmetric between the twins by
construction (`AC-VC-02` verifies it) and there is no new asymmetry to record.

## Not in this release

No engine change. `qa_ledger.py` is untouched, so nothing here moves a version surface's derived
fact beyond what `facts --write` already renders from `uscha-kit/VERSION`.

Suite: __SUITE__ checks · 0 fail; acceptance __ACC__.
