# uscha-kit 2.12.1 — the release ritual no longer refuses on a tag re-created from another clone

## What changed

- **`tools/release.py` preflight reconciles tags before `git fetch --tags`.** When the session that
  runs the ritual cannot push tags, the human creates and pushes the tag from their own clone.
  The tag the ritual made locally is then a different tag OBJECT naming the same commit, and
  `git fetch --tags` fails ("would clobber existing tag") -- so I1 refused the NEXT release
  before it started (2.11.0 and 2.12.0 both hit it). Preflight now reads origin's tags into a
  private namespace first: a local tag that names the SAME commit as origin's is re-pointed to
  origin's object, and the line says so; one that names a DIFFERENT commit is refused naming I1,
  the tag and both commits -- a tag is never moved to another commit silently. The namespace is
  always removed.
- The kit itself does not change: `release.py` is repo-level and not shipped in the package. The
  version moves so the ritual that fixes the ritual is measured by the ritual (repo rule 9).

## How it is pinned

`AC-RL-07` (smoke T151): over a fresh fixture with its own bare origin, a local annotated tag
that differs from origin's but names the same commit passes preflight and ends equal to origin's
object; a local tag forced onto a different commit is refused naming I1, the tag and that commit;
no `refs/uscha-release/` ref is left behind. Red against 2.12.0 first (the refusal both releases
hit).

## Evidence

Suite: __SUITE__ checks · 0 fail; acceptance __ACC__.
