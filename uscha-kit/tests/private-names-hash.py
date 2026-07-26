#!/usr/bin/env python3
"""Turn the untracked plaintext private-name list into a COMMITTABLE hash list.

Why this exists
---------------
AC-03 ("the kit and its docs contain zero references to client or private project
names") could not be measured in CI: the name list lived only in an untracked
`.uscha-private-names`, so the criterion emitted `<skipped/>` -- UNMEASURED -- on
every public run. A gate nobody can run is a gate nobody can trust, and it hid a
real miss: names sat in four tracked files for weeks.

Hashing the list makes it committable, so CI measures the criterion on every push
without publishing the very names the criterion exists to keep out.

    python uscha-kit/tests/private-names-hash.py        # regenerate the hash file

HONEST LIMITS -- read before relying on this
--------------------------------------------
1. **Whole tokens only.** A hash cannot match a substring or a regex. The
   plaintext list may hold prefixes/regexes for the release machine's stricter
   local run; the hashed list holds only full tokens, and only those are checked
   in CI.
2. **Not secret against a targeted guess.** SHA-256 without a secret salt is
   confirmable: someone who already suspects a name can hash it and compare. This
   stops casual reading, grepping and search-engine indexing -- it is not a vault.
   A secret salt was rejected on purpose: it would put the gate back behind
   invisible config, which is the failure this replaces.
3. The plaintext list stays untracked and remains the stricter superset.
"""
import hashlib
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PLAIN = os.path.join(ROOT, ".uscha-private-names")
HASHED = os.path.join(ROOT, ".uscha-private-names.sha256")

HEADER = """# Hashed private-name list -- COMMITTED ON PURPOSE, generated, do not hand-edit.
# Regenerate: python uscha-kit/tests/private-names-hash.py
#
# One sha256(lowercased token) per line. This lets AC-03 run in CI without
# publishing the names. It matches WHOLE TOKENS ONLY (a hash cannot match a
# prefix or a regex) and it is not secret against someone who already suspects a
# specific name -- see the script's docstring for the full limits.
"""


def tokenize_term(term):
    """A term may be written for the human list (case, separators). Normalize it the
    same way the scanner normalizes what it finds, or the two will never meet."""
    return term.strip().lower()


def main():
    if not os.path.isfile(PLAIN):
        print("[private-names-hash] no %s here -- nothing to hash." % os.path.basename(PLAIN))
        return 1
    terms = []
    for line in io.open(PLAIN, encoding="utf-8"):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        terms.append(s)
    hashes, skipped = [], []
    for t in terms:
        # a regex/prefix cannot be hashed -- keep it in the plaintext list only
        if any(c in t for c in ".^$*+?{}[]|()\\") or t.endswith("_"):
            skipped.append(t)
            continue
        hashes.append(hashlib.sha256(tokenize_term(t).encode("utf-8")).hexdigest())
    hashes = sorted(set(hashes))
    io.open(HASHED, "w", encoding="utf-8", newline="\n").write(
        HEADER + "\n".join(hashes) + "\n")
    print("[private-names-hash] %d term(s) -> %d hash(es) in %s"
          % (len(terms), len(hashes), os.path.basename(HASHED)))
    if skipped:
        print("[private-names-hash] %d term(s) NOT hashable (regex/prefix) -- they stay "
              "local-only and are NOT measured in CI:" % len(skipped))
        for t in skipped:
            print("    (kept private; %d chars)" % len(t))
    return 0


if __name__ == "__main__":
    sys.exit(main())
