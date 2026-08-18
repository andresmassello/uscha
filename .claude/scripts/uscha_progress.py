#!/usr/bin/env python3
"""Refresh the uscha progress for the statusline. Runs on the Stop hook (every time a task
ends). Truth-pass: it reads REAL numbers from the ledger + ACCEPTANCE; a missing source
leaves its field null and the statusline degrades -- it never invents.

Everything project-specific (the tracked repo, its label, its roadmap, its build priority)
comes from uscha.config.json -- NOTHING is hardcoded. Writes .claude/uscha-progress.json.
Fast: it parses JSON + one .md, never runs tests. If there is no uscha.config.json this is
not a uscha project: it writes nothing and the statusline stays hidden.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
CONFIG = ROOT / "uscha.config.json"
OUT = ROOT / ".claude" / "uscha-progress.json"

# tolerant of bold/plain AC ids -- mirrors qa_ledger.py:_AC_ID (AC-01, **AC-01**, `AC_1`)
# and, since kit 1.87.0 (ADR-036), the FAMILY form too (AC-BC-07, AC-T-24, `ac_dd_3`).
# A family starts with a LETTER, so 'AC-7-x' stays the bare AC-7 followed by text --
# the same fallback order the engine applies. The statusline must never count a
# criterion the ledger cannot see, nor miss one it can.
_AC_CORE = r"AC(?:[-_][A-Za-z][A-Za-z0-9]*[-_]|[-_]?)\d+"
_AC = r"[*_`]*\s*" + _AC_CORE + r"[*_`]*"


def _statusline_repo(cfg):
    """The repo the statusline tracks: the first with a label or roadmap, else the first."""
    repos = cfg.get("repos") or []
    for r in repos:
        if r.get("label") or r.get("roadmap"):
            return r
    return repos[0] if repos else None


def _measured(state, repo_name=None):
    """Prefer the engine's MEASURED acceptance -- persisted into ledger['measured'] by
    `readiness --record` -- over counting checkboxes. The statusline summarizes the ledger; it
    must never contradict it (measured beats narrated, kit 1.46.1). Returns True if used."""
    ledger = ROOT / "QA-LEDGER.json"
    if not ledger.is_file():
        return False
    try:
        m = (json.loads(ledger.read_text(encoding="utf-8")) or {}).get("measured")
    except Exception:
        return False
    if not isinstance(m, dict):
        return False
    # WHEN the evidence was captured, and the verdict it produced. Without these a reader
    # cannot tell a fresh measurement from a stale one (kit 1.48.1) -- and a consumer that
    # needs them would have to re-read the ledger, defeating this fast path.
    state["measured_at"], state["score"] = m.get("at"), m.get("score")
    state["band"] = m.get("band")
    # loop odometer (kit 1.47.0): the derived phase + pass count + plateau flag the engine
    # persisted for this repo. Read even when there are no ACs -- phase is its own fact.
    # The FULL per-repo map travels too: a multi-repo readout needs every repo, not just
    # the one the statusline tracks (kit 1.48.1).
    repos = m.get("repos")
    if isinstance(repos, dict):
        state["repos"] = repos
    r = (repos or {}).get(repo_name or "")
    if isinstance(r, dict):
        state["phase"], state["loops"] = r.get("phase"), r.get("loops")
        state["stalled"] = bool(r.get("stalled"))
    if not m.get("acceptance_total"):
        return False
    total, done = m["acceptance_total"], m.get("acceptance_done") or 0
    state["done"], state["total"] = done, total
    state["pct"] = round(100 * done / total)
    state["acceptance_source"] = "measured"
    nx = m.get("next")
    if isinstance(nx, dict) and nx.get("id"):
        txt = re.sub(r"[*_`]", "", str(nx.get("text", ""))).strip()
        state["next"] = f"{nx['id']}: {txt[:44]}"
    return True


def _acceptance(state, cfg):
    acc_name = (cfg.get("defaults") or {}).get("acceptance_file", "ACCEPTANCE.md")
    acc = ROOT / acc_name
    if not acc.is_file():
        return
    text = acc.read_text(encoding="utf-8", errors="ignore")
    # case-insensitive to match qa_ledger.py:_AC_ID exactly: '- [X] AC-01', '- [x] ac-1',
    # '**AC-01**' all count. The statusline must never disagree with the ledger it summarizes.
    done = len(re.findall(r"- \[x\]\s*" + _AC, text, re.IGNORECASE))
    total = len(re.findall(r"- \[[ x]\]\s*" + _AC, text, re.IGNORECASE))
    if total:
        state["done"], state["total"] = done, total
        state["pct"] = round(100 * done / total)
        # ticked by a human, not closed by a green test. The renderer MUST say so: showing
        # a narrated number with the same face as a measured one is the exact dishonesty
        # this kit exists to remove (kit 1.48.1).
        state["acceptance_source"] = "narrated"
    m = re.search(r"- \[ \]\s*[*_`]*\s*(" + _AC_CORE + r")[*_`]*\s*[—–-]\s*(.+)",
                  text, re.IGNORECASE)
    if m:
        nxt = re.sub(r"[*_`]", "", m.group(2)).strip()
        state["next"] = f"{m.group(1)}: {nxt[:44]}"


def _ledger(state, repo_name):
    ledger = ROOT / "QA-LEDGER.json"
    if not ledger.is_file():
        return
    try:
        data = json.loads(ledger.read_text(encoding="utf-8"))
    except Exception:
        return
    node = (data.get("repos") or {}).get(repo_name, {})
    snaps = node.get("snapshots") or []
    if not snaps:
        return
    snap = snaps[-1]
    tests = snap.get("tests") or {}
    cov = snap.get("coverage") or {}
    if tests.get("report_found"):
        state["tests"] = tests.get("passed")
    if cov.get("report_found"):
        state["coverage"] = cov.get("pct")


def _roadmap(state, repo):
    """roadmap[]/build_priority[] declared per-repo in uscha.config.json. An item counts as
    BUILT when its file exists and is non-trivial (>200 bytes) -- a real file, not a promise.
    The 'next' arrow is the first build_priority item not yet built (a PLAN, not a fact)."""
    roadmap = repo.get("roadmap") or []
    if not roadmap:
        return
    paths = {it["name"]: it["path"] for it in roadmap
             if isinstance(it, dict) and it.get("name") and it.get("path")}

    def built(name):
        p = ROOT / paths.get(name, "")
        try:
            return p.is_file() and p.stat().st_size > 200
        except OSError:
            return False

    state["roadmap_done"] = sum(1 for n in paths if built(n))
    state["roadmap_total"] = len(paths)
    priority = repo.get("build_priority") or [it["name"] for it in roadmap
                                              if isinstance(it, dict) and it.get("name")]
    state["roadmap_next"] = next((n for n in priority if n in paths and not built(n)), None)


def main():
    if not CONFIG.is_file():
        return  # not a uscha project -> statusline stays hidden
    try:
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    except Exception:
        return
    repo = _statusline_repo(cfg)
    if not repo:
        return
    state = {"label": repo.get("label") or str(repo.get("name", "uscha")).upper(),
             "pct": None, "done": None, "total": None, "tests": None, "coverage": None,
             "next": None, "phase": None, "loops": None, "stalled": None,
             "acceptance_source": None, "measured_at": None, "score": None, "band": None,
             "repos": None,
             "roadmap_done": None, "roadmap_total": None, "roadmap_next": None}
    # measured (ledger['measured']) wins; checkboxes are only the fallback until the engine
    # has recorded a measurement -- so a fresh project still shows *something*, honestly.
    if not _measured(state, repo.get("name")):
        _acceptance(state, cfg)
    _ledger(state, repo.get("name"))
    _roadmap(state, repo)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(state), encoding="utf-8")


if __name__ == "__main__":
    main()
