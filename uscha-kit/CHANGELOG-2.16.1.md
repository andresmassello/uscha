# uscha-kit 2.16.1 -- `review_tiers.base`: the review pace for a project whose trunk is not main

One optional key, found as the limit 2.16.0 named. No new subcommand, no schema change.

## What changed

- **`review_tiers.base` names the change's base.** Under `review_tiers` the change's files are the
  commits since the merge-base with a base branch, plus the working tree. 2.16.0 tried a fixed
  list (`origin/HEAD`, `origin/main`, `main`, `origin/master`, `master`), so a project whose trunk is
  `develop`, `trunk` or a release branch was refused (fail closed) and could not use the pace. The
  block now takes an optional `base`: a git ref such as `develop` or `origin/develop`.
  - When set, it is the ONLY base. There is no fallback list: an existing `main` is not consulted.
  - A configured base that does not resolve fails closed exactly like an unresolved list, when the
    branch has commits: `review-start` exits 2 with the ledger unchanged, and `phase` / `converged`
    refuse, the message naming the ref and `review_tiers.base`.
  - When absent, nothing changes: the same list, the same fail-closed rule (AC-RP-41).
  - A value that is not a nonempty string (`""`, a number, blanks), or that starts with a dash
    (`--independent` would make `git merge-base` print HEAD and read as an empty change), is refused
    naming `review_tiers.base` and, read live, the config file -- the way a malformed live block
    already is. The ledger's frozen copy of the block is validated the same way, naming the ledger
    (AC-RP-42, AC-RP-43). The ref is resolved to a commit first and its SHA goes to `merge-base`.
  - The key is read live from `uscha.config.json` like the rest of the block (ADR-051): it works with
    no re-init. `init` does not write it and `doctor` prints nothing new.
- ADR-062 carries a dated amendment (decision 8). Base resolution is outside ReviewPace.tla's
  abstraction -- the model takes a change, not how its files are computed -- so there is no model
  change; AC-RP-37..41 replay the cases against the engine.

## Behavior changes on upgrade (read before upgrading)

- None for a project that does not set `review_tiers.base`.

## Honest limits

- The base is one ref. A project with several long-lived trunks names the one its changes are
  reviewed against; the others are not tried.
- A configured ref is resolved with `git merge-base HEAD <ref>`: a local branch that is stale, or a
  remote-tracking ref that was never fetched, gives the base it has. The engine does not fetch.
- Lifts the 2.16.0 limit "the base is the first branch of a fixed list; a project whose base is named
  otherwise is refused": it is no longer refused when it sets `review_tiers.base`. Without the key the
  limit stands.

## Evidence

Suite: 471 checks · 0 fail; acceptance 525/526.
