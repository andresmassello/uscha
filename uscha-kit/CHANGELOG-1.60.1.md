# uscha-kit 1.60.1 — the first tokenless publish, and the gate that earned it (2026-08-02)

Same feature set as 1.60.0. This patch exists because **1.60.0 was tagged but never reached
npm**: the publish workflow fired on its tag, ran the full smoke suite *inside the job that
publishes*, and stopped there. Nothing was uploaded. That is the gate doing exactly what it
was built for, on its very first real run.

## What it caught

`npm pack --dry-run --json` returns a **list** under npm 11 (what Node 20 ships, and what the
smoke job uses) and a different shape under `npm@latest`, which the publish job installs
because trusted publishing requires npm ≥ 11.5.1. The packaging test indexed `[0]`
unconditionally and died with `KeyError: 0` — a message that names nothing and points the
diagnosis at the wrong step. The test now accepts both shapes and, when it is neither, prints
what it actually got: npm emits an error *object* on that same channel, so "unknown shape" is
not a hypothetical branch.

A second bug surfaced inside the first fix: the new diagnostic used a `\n` escape in a block
that lives inside a double-quoted shell string, where the shell consumes the backslash before
Python ever sees the line. Same family as the no-backticks note already sitting in that block.

## Why a patch and not a moved tag

`v1.60.0` is public and carries a GitHub release. Moving it would make the tag *lie* — anyone
who already fetched it would hold a different tree under the same name, which is the precise
failure the branch protection on `main` exists to prevent. Tags do not move here. npm goes
1.59.0 → 1.60.1, and the gap is this note.

## Publishing

This is the first release published by **trusted publishing (OIDC)**: no npm token exists in
the repository's secrets or on any machine. GitHub mints a short-lived token for this exact
workflow in this exact repository, npm verifies it against the trusted publisher configured on
npmjs.com, and provenance attestation is generated automatically. The human act did not
disappear — it moved to the tag, which was already the release ritual.

402/402 on Windows, Linux and the full CI matrix.
