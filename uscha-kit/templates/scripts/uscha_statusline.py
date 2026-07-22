#!/usr/bin/env python3
"""uscha statusline: a colored progress meter for the active change. Claude Code re-renders
it every turn. It reads only .claude/uscha-progress.json (refreshed by the Stop hook,
uscha_progress.py) and is a DUMB renderer -- every datum, including the project label, comes
from that file. Fast, no tests, model-agnostic.

Red <50 · Yellow 50-79 · Green >=80. Degrades to an EMPTY line (hidden) when there is no
progress file -- truth-pass: it never invents a number, and it never hardcodes a project.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

R = "\033[0m"
B = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
FILE = ROOT / ".claude" / "uscha-progress.json"
WIDTH = 12


def _bar(pct, color):
    fill = round(WIDTH * pct / 100)
    return f"{color}{'█' * fill}{R}{DIM}{'░' * (WIDTH - fill)}{R}"


def _color(pct):
    return GREEN if pct >= 80 else YELLOW if pct >= 50 else RED


def main():
    # Windows: the default console (cp1252) chokes on the block/dot glyphs; force UTF-8.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    # the statusline receives session JSON on stdin; we don't need it, drain it.
    try:
        sys.stdin.read()
    except Exception:
        pass

    # No progress file (project without uscha, or no task run yet) -> hidden line. Never a
    # hardcoded fallback: an empty stdout is how Claude Code hides the statusline.
    if not FILE.exists():
        print("")
        return
    try:
        s = json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:
        print("")
        return

    label = s.get("label") or "uscha"
    pct = s.get("pct")
    parts = [f"{B}{label}{R}"]
    if pct is None:
        parts.append(f"{DIM}avance n/d{R}")
    else:
        parts.append(f"{_bar(pct, _color(pct))} {_color(pct)}{pct}%{R}")
        if s.get("total"):
            parts.append(f"AC {s['done']}/{s['total']}")
    if s.get("tests") is not None:
        parts.append(f"{GREEN}{s['tests']}✓{R}")
    if s.get("coverage") is not None:
        parts.append(f"{s['coverage']:.0f}%cov")
    if s.get("next"):
        parts.append(f"{DIM}→ {s['next']}{R}")
    lines = ["  ·  ".join(parts)]

    # second line: the project roadmap, only if the config declared one
    rdone, rtotal = s.get("roadmap_done"), s.get("roadmap_total")
    if rtotal:
        rpct = round(100 * rdone / rtotal)
        rparts = [f"{DIM}roadmap{R}",
                  f"{_bar(rpct, _color(rpct))} {_color(rpct)}{rdone}/{rtotal}{R}"]
        if s.get("roadmap_next"):
            rparts.append(f"{DIM}→ sigue {s['roadmap_next']}{R}")
        lines.append("  ·  ".join(rparts))

    print("\n".join(lines))


if __name__ == "__main__":
    main()
