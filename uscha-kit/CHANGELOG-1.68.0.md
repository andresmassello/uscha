# uscha-kit 1.68.0 — SYSTEM-FACTS: published claims become compiled artifacts (2026-08-10)

T0 of the Diamond program, and the smallest possible statement of its thesis applied to the
project itself: a claim nobody compares against a derived fact WILL drift. The founding
fixture happened live — the site claimed kit **1.65.0** with **32** engine subcommands while
the repo was at **1.67.0** with **35**. Factual drift, in the project about factual drift.

## `facts` — subcommand 36

```bash
python qa_ledger.py facts                     # derive SYSTEM-FACTS.json from the artifacts
python qa_ledger.py facts --check <files...>  # exit 1 on any claim that disagrees, named
```

Facts are derived **from the artifacts themselves, never from prose**: the subcommand list by
introspecting the real `build_parser()`, the skill inventory from the real kit tree, the
version from `VERSION`. No timestamp — regeneration over an unchanged repo is byte-identical.
What has no mechanical source yet (stack matrix, REAL/VISION registry) is **omitted and named
as omitted**, never guessed.

`--check` compares every recognizable claim (kit version, N subcommands/subcomandos,
N skills) in the given files against the derived facts and fails naming `file:line`, the
claim and the fact — and a stale committed `SYSTEM-FACTS.json` is itself drift. The smoke
suite runs the REAL check over the live claim surfaces (README ×2, site index + llms.txt,
both plugin manifests, the command-reference doc ×4 twins), so **factual drift is now a red
CI build**. Historical changelogs are archives, deliberately out of scope (ADR-012):
rewriting an archive to match today falsifies the record.

Exit criteria of T0, both met: an injected wrong claim fails naming the drifted fact
(AC-SF-02), and the real drift died by the mechanism's first green run — the founding red
named every stale number before any of them was fixed by hand. The first live run also
caught a scanner bug of its own: an HTML section-marker comment (`2 Skills`) flagged as a
drifted count — comments are not published claims, and are now excluded.

Also in this release: the command-reference doc's table gains the four subcommands it was
missing (`cleanroom`, `curation-check`, `roundtrip`, `facts`) in all four twins, and the
repo's first **field note** lands in `docs/field-notes/` — a real, anonymized treasury
migration where the engine accepted 16 of 19 claimed criteria, linked from the site library.
Its limitation 1 (cap reasons and stale discards are not persisted as structured events) is
filed as an engine issue.

## What the fresh review caught

- **HIGH** — the Codex twin engine (living one level shallower, `skills/` instead of
  `.claude/skills/`) derived the wrong kit root from a fixed-depth dirname walk: `facts`
  reported version null and 0 skills, silently, from that install location. The twins were
  byte-identical FILES with divergent runtime behavior — a defect AC-01 cannot see. Root is
  now found by marker (walking up to the VERSION file), the skill inventory tries both tree
  layouts, facts that cannot locate their kit exit 2 instead of emitting nulls, and
  `AC-SF-05` runs the twin and asserts byte-identical output.
- **MEDIUM** — `site/es/index.html` had been left at v1.65.0 without the field-note card:
  the exact drift class this release exists to kill, invisible because the ES twin was not
  in the check scope. It is now updated AND in scope — the mechanism widened instead of the
  number being fixed quietly.
- The changelog's own suite count was wrong (407 vs the real total). As meta as it gets, and
  historical changelogs stay out of the gate's scope by design — so this one gets fixed the
  old way, by a reviewer.

Suite: 408 checks. Acceptance: **60/60** where `coverage.py` is installed.
