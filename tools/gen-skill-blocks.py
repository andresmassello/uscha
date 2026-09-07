#!/usr/bin/env python3
"""Render the orientation block into every SKILL.md from ONE source of truth.

Seven of the nine skills carry a byte-identical orientation block ("First contact" +
"Orientation markers"); `mirador` and `status` carry a shorter two-marker variant.
The runtime files must stay whole -- an agent loads one SKILL.md and nothing else, so
there is no include mechanism to lean on. The duplication therefore stays on disk and
moves its SOURCE here: the canonical text lives once under `tools/skill-blocks/`, and
this generator writes it into the marked region of each SKILL.md, in both skill trees.

    tools/skill-blocks/orientation-block.md        the full variant (7 skills)
    tools/skill-blocks/orientation-block-short.md  the short variant (mirador, status)
    tools/skill-blocks/skills.json                 per-skill parameters

Placeholders: `{{skill}}` (the breadcrumb name, e.g. `adr-refine`), `{{here}}` (the
per-skill `Here:` / `Output:` / `Next:` lines, verbatim, full variant only) and
`{{version}}` (the kit version, read from `uscha-kit/VERSION`).

`{{version}}` is what makes an installed skill dateable. A field report (2.2.0) found skills
installed under `~/.claude/skills/uscha-*` from kit 1.54.0 while the kit itself was at 1.97.0:
the discovery ran on the old prose and NOTHING said so, because a SKILL.md carried no version at
all. Every block now opens with `<!-- uscha kit: X.Y.Z ... -->`, `doctor` compares that marker
against the kit's own VERSION, and `tools/release.py` re-renders these regions in step 2 -- right
after the six version surfaces move, before the facts gate -- so the marker can never lag the
release that shipped it.

Usage
    python tools/gen-skill-blocks.py            rewrite every marked region in place
    python tools/gen-skill-blocks.py --check    verify only; never writes
    python tools/gen-skill-blocks.py --root D   resolve the templates and both skill trees
                                                under D instead of this file's repo

`--root` exists so the generator can be MEASURED (smoke T152): the suite drives it over a
throwaway copy of the two skill trees, mutates one word inside a region there, and asserts the
exit code -- without that flag the only tree it could be tested against is the live repo, and a
test that mutates the repo it is testing is not a test.

Exit codes
    0  everything matches (--check) or was written
    1  at least one region differs from the rendered template (--check only)
    2  configuration error: a missing file, an unknown variant, an absent marker
"""

import argparse
import io
import json
import os
import sys

BEGIN = "<!-- uscha:orientation-block:begin -->"
END = "<!-- uscha:orientation-block:end -->"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLOCKS = os.path.join("tools", "skill-blocks")
TREES = (os.path.join("uscha-kit", ".claude", "skills"),
         os.path.join("uscha-kit", "skills"))
TEMPLATES = {"full": "orientation-block.md", "short": "orientation-block-short.md"}
VERSION_FILE = os.path.join("uscha-kit", "VERSION")


class ConfigError(Exception):
    """A fault in the inputs, not a drift in the output. Always exit 2."""


def read_lines(path):
    if not os.path.isfile(path):
        raise ConfigError("missing file: %s" % path)
    return io.open(path, encoding="utf-8", newline="").read().split("\n")


def load_templates(root):
    out = {}
    for variant, name in TEMPLATES.items():
        lines = read_lines(os.path.join(root, BLOCKS, name))
        while lines and lines[-1] == "":
            lines.pop()
        out[variant] = lines
    return out


def load_version(root):
    """The kit version the blocks are stamped with, from the SAME file the six surfaces move.

    A ConfigError (exit 2) rather than a default when it is missing: a block stamped with a
    guessed version would be worse than one with no stamp at all -- `doctor` would compare an
    installed skill against a number nobody wrote."""
    path = os.path.join(root, VERSION_FILE)
    if not os.path.isfile(path):
        raise ConfigError("missing file: %s" % path)
    body = io.open(path, encoding="utf-8").read().strip()
    if not body:
        raise ConfigError("%s is empty -- there is no version to stamp" % path)
    return body.split()[-1]


def load_table(root):
    path = os.path.join(root, BLOCKS, "skills.json")
    if not os.path.isfile(path):
        raise ConfigError("missing file: %s" % path)
    fh = io.open(path, encoding="utf-8")
    try:
        return json.load(fh)
    finally:
        fh.close()


def render(skill, params, templates, version):
    variant = params.get("variant")
    if variant not in templates:
        raise ConfigError("%s: unknown variant %r (expected one of %s)"
                          % (skill, variant, ", ".join(sorted(templates))))
    name = params.get("name")
    if not name:
        raise ConfigError("%s: no breadcrumb name in skills.json" % skill)
    here = params.get("here", [])
    if variant == "full" and not here:
        raise ConfigError("%s: the full variant needs a 'here' block" % skill)
    if variant != "full" and here:
        raise ConfigError("%s: the %s variant takes no 'here' block" % (skill, variant))
    out = []
    for line in templates[variant]:
        if line.strip() == "{{here}}":
            out.extend(here)
        else:
            out.append(line.replace("{{skill}}", name).replace("{{version}}", version))
    for line in out:
        if "{{" in line:
            raise ConfigError("%s: unresolved placeholder in %r" % (skill, line))
    return out


def locate(path, lines):
    begins = [i for i, l in enumerate(lines) if l.strip() == BEGIN]
    ends = [i for i, l in enumerate(lines) if l.strip() == END]
    if len(begins) != 1 or len(ends) != 1:
        raise ConfigError("%s: expected exactly one %s and one %s (found %d / %d)"
                          % (path, BEGIN, END, len(begins), len(ends)))
    if ends[0] < begins[0]:
        raise ConfigError("%s: the end marker precedes the begin marker" % path)
    return begins[0], ends[0]


def process(check_only, root):
    templates = load_templates(root)
    table = load_table(root)
    version = load_version(root)
    drifted, written = [], []
    for skill in sorted(table):
        block = render(skill, table[skill], templates, version)
        for tree in TREES:
            path = os.path.join(root, tree, skill, "SKILL.md")
            rel = os.path.join(tree, skill, "SKILL.md").replace(os.sep, "/")
            lines = read_lines(path)
            begin, end = locate(rel, lines)
            if lines[begin + 1:end] == block:
                continue
            if check_only:
                drifted.append(rel)
                continue
            lines[begin + 1:end] = block
            io.open(path, "w", encoding="utf-8", newline="").write("\n".join(lines))
            written.append(rel)
    return drifted, written


def main(argv):
    parser = argparse.ArgumentParser(
        description="Render the orientation block into every SKILL.md from one source.")
    parser.add_argument("--check", action="store_true",
                        help="verify the rendered region matches; write nothing")
    parser.add_argument("--root", default=ROOT,
                        help="repo root holding tools/skill-blocks/ and the two skill trees "
                             "(default: the repo this file lives in)")
    args = parser.parse_args(argv)
    try:
        drifted, written = process(args.check, args.root)
    except ConfigError as exc:
        sys.stderr.write("gen-skill-blocks: %s\n" % exc)
        return 2
    if args.check:
        if drifted:
            sys.stderr.write("gen-skill-blocks: %d region(s) differ from the template:\n"
                             % len(drifted))
            for rel in drifted:
                sys.stderr.write("  %s\n" % rel)
            sys.stderr.write("  the block is generated: edit tools/skill-blocks/, not the"
                             " SKILL.md, then run: python tools/gen-skill-blocks.py\n")
            sys.stderr.write("  (a bumped uscha-kit/VERSION drifts every region too -- the"
                             " block carries `uscha kit: X.Y.Z`; tools/release.py re-renders"
                             " them in step 2)\n")
            return 1
        sys.stdout.write("gen-skill-blocks: every orientation block matches the template\n")
        return 0
    if written:
        sys.stdout.write("gen-skill-blocks: rewrote %d file(s)\n" % len(written))
        for rel in written:
            sys.stdout.write("  %s\n" % rel)
    else:
        sys.stdout.write("gen-skill-blocks: nothing to rewrite\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
