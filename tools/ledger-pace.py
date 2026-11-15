#!/usr/bin/env python3
"""ledger-pace -- where does the time of a uscha project go? (read-only field report)

Reads a project's QA-LEDGER.json (and, when present, its git history and the mirador's
.uscha/telemetry.jsonl) and prints a report to judge the method's PACE against what each
step buys:

  1. Overview         -- span of the ledger, events, test runs, escalations, production findings.
  2. Work sessions     -- events clustered by inactivity (default gap 4 h): duration, QA rounds,
                          test runs, commits and lines changed in that window (git, best-effort).
  3. QA yield per tool -- rounds, findings, GATED findings, fixed / deferred, rounds that found
                          nothing gated. A tool that never finds anything gated is pure cost.
  4. Test runs         -- count, pass/fail, wall time (median, p90, total), runs per session.
  5. Escapes           -- production findings and escalations, as recorded.
  6. Token / wall cost -- from .uscha/telemetry.jsonl, if the mirador wrote one.

It never writes anything and never runs the project's tests. Every number comes from a file it
names; a section with no source says so instead of guessing. Stdlib only, Python 3.8+.

  python ledger-pace.py C:\\Work\\Proyecto\\QA-LEDGER.json
  python ledger-pace.py C:\\Work\\Proyecto              (finds QA-LEDGER.json in the folder)
  python ledger-pace.py <ledger> --gap-hours 2 --json pace.json --no-git
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone


def ts(v):
    if not v:
        return None
    try:
        d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def fmt_dur(seconds):
    if seconds is None:
        return "-"
    seconds = int(round(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return "%dh%02dm" % (h, m)
    if m:
        return "%dm%02ds" % (m, s)
    return "%ds" % s


def pct(values, q):
    if not values:
        return None
    v = sorted(values)
    k = (len(v) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (k - lo)


def table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


# ---------------------------------------------------------------- sources

def load_ledger(path):
    if os.path.isdir(path):
        path = os.path.join(path, "QA-LEDGER.json")
    with open(path, encoding="utf-8") as fh:
        return os.path.realpath(path), json.load(fh)


def events(led):
    """Every timestamped thing the ledger recorded, as (time, kind, repo, detail)."""
    ev = []
    for s in led.get("steps") or []:
        t = ts(s.get("at"))
        if t:
            ev.append((t, s.get("kind") or "step", s.get("repo"), s))
    for r in led.get("test_runs") or []:
        t = ts(r.get("started_at"))
        if t:
            ev.append((t, "test-run", r.get("repo"), r))
    # the engine also logs these as steps (kind "production-finding", "escalation", ...): read the
    # top-level list only when no such step exists, or every one is counted twice
    step_kinds = {(s.get("kind") or "") for s in led.get("steps") or []}
    for key, kind in (("escalations", "escalation"), ("production_findings", "production-finding"),
                      ("spec_doubts", "spec-doubt"), ("spec_change_requests", "spec-change-request")):
        if kind in step_kinds:
            continue
        for x in led.get(key) or []:
            t = ts(x.get("at") or x.get("created_at") or x.get("opened_at"))
            if t:
                ev.append((t, key, x.get("repo"), x))
    for x in led.get("readiness_history") or []:
        t = ts(x.get("at"))
        if t:
            ev.append((t, "readiness", None, x))
    ev.sort(key=lambda e: e[0])
    return ev


def git_commits(repo_dir):
    """(time, sha, added, deleted, files) per commit, or None when git is not usable here."""
    try:
        out = subprocess.run(
            ["git", "-C", repo_dir, "log", "--no-merges", "--numstat",
             "--pretty=format:@@%H %cI"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
            errors="replace", timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    commits, cur = [], None
    for line in out.stdout.splitlines():
        if line.startswith("@@"):
            sha, _, when = line[2:].partition(" ")
            cur = [ts(when), sha, 0, 0, 0]
            commits.append(cur)
        elif line.strip() and cur is not None:
            parts = line.split("\t")
            if len(parts) >= 3:
                cur[4] += 1
                if parts[0].isdigit():
                    cur[2] += int(parts[0])
                if parts[1].isdigit():
                    cur[3] += int(parts[1])
    return [tuple(c) for c in commits if c[0]]


def telemetry(repo_dir):
    p = os.path.join(repo_dir, ".uscha", "telemetry.jsonl")
    if not os.path.isfile(p):
        return p, None
    rows = []
    with open(p, encoding="utf-8") as fh:
        for line in fh:
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    return p, rows


# ---------------------------------------------------------------- analysis

def sessions(ev, gap_s):
    out, cur = [], []
    for e in ev:
        if cur and (e[0] - cur[-1][0]).total_seconds() > gap_s:
            out.append(cur)
            cur = []
        cur.append(e)
    if cur:
        out.append(cur)
    return out


def qa_yield(led):
    by = {}
    for repo, r in (led.get("repos") or {}).items():
        for it in r.get("iterations") or []:
            key = (it.get("category") or "?", it.get("tool") or "?")
            a = by.setdefault(key, {"rounds": 0, "reported": 0, "gated": 0, "fixed": 0,
                                    "deferred": 0, "suppressed": 0, "regressions": 0,
                                    "empty_gated": 0, "repos": set()})
            a["rounds"] += 1
            a["repos"].add(repo)
            for f, k in (("reported", "reported"), ("gated_reported", "gated"), ("fixed", "fixed"),
                         ("deferred", "deferred"), ("suppressed", "suppressed"),
                         ("new_regressions", "regressions")):
                v = it.get(f)
                a[k] += v if isinstance(v, int) else 0
            if not it.get("gated_reported"):
                a["empty_gated"] += 1
    return by


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("ledger", help="QA-LEDGER.json, or the folder that holds it")
    ap.add_argument("--gap-hours", type=float, default=4.0,
                    help="inactivity that splits two work sessions (default 4)")
    ap.add_argument("--no-git", action="store_true", help="do not read the git history")
    ap.add_argument("--json", default=None, help="also write the numbers as JSON to this file")
    a = ap.parse_args(argv)

    path, led = load_ledger(a.ledger)
    root = os.path.dirname(path)
    ev = events(led)
    out = {"ledger": path, "generated_at": datetime.now(timezone.utc).isoformat()}
    P = []
    P.append("# Pace report -- %s" % (led.get("config", {}).get("project")
                                       or os.path.basename(root)))
    P.append("Source: `%s` (read-only). Gap between work sessions: %.1f h." % (path, a.gap_hours))

    # 1 overview
    P.append("\n## 1. Overview")
    if not ev:
        P.append("The ledger has no timestamped events: nothing to measure.")
        print("\n".join(P))
        return 0
    span = (ev[-1][0] - ev[0][0]).total_seconds()
    kinds = {}
    for e in ev:
        kinds[e[1]] = kinds.get(e[1], 0) + 1
    P.append("From %s to %s (%s calendar). Events by kind: %s." % (
        ev[0][0].date(), ev[-1][0].date(), fmt_dur(span),
        ", ".join("%s %d" % kv for kv in sorted(kinds.items(), key=lambda kv: -kv[1]))))
    out["overview"] = {"first": ev[0][0].isoformat(), "last": ev[-1][0].isoformat(),
                       "events": kinds}

    commits = None if a.no_git else git_commits(root)

    # 2 sessions
    P.append("\n## 2. Work sessions (events within %.1f h of each other)" % a.gap_hours)
    ss = sessions(ev, a.gap_hours * 3600)
    rows, srows = [], []
    for i, s in enumerate(ss, 1):
        t0, t1 = s[0][0], s[-1][0]
        qa = sum(1 for e in s if e[1] in ("qa-step", "static-gate"))
        trs = [e for e in s if e[1] == "test-run"]
        tr_wall = sum((e[3].get("wall_ms") or 0) for e in trs) / 1000.0
        c_in = [c for c in commits or [] if t0 <= c[0] <= t1] if commits is not None else None
        lines = sum(c[2] + c[3] for c in c_in) if c_in is not None else None
        row = {"n": i, "start": t0.isoformat(), "duration_s": (t1 - t0).total_seconds(),
               "events": len(s), "qa_rounds": qa, "test_runs": len(trs),
               "test_wall_s": tr_wall, "commits": len(c_in) if c_in is not None else None,
               "lines_changed": lines}
        srows.append(row)
        rows.append([i, t0.strftime("%Y-%m-%d %H:%M"), fmt_dur(row["duration_s"]), len(s), qa,
                     len(trs), fmt_dur(tr_wall),
                     "-" if c_in is None else len(c_in), "-" if lines is None else lines])
    P.append(table(["#", "start (UTC)", "span", "events", "QA rounds", "test runs",
                    "test wall", "commits", "lines +/-"], rows[-40:]))
    if len(rows) > 40:
        P.append("(last 40 of %d sessions shown; all are in --json)" % len(rows))
    if commits is None and not a.no_git:
        P.append("git history not readable from `%s`: commits and lines show `-`." % root)
    P.append("A session's span runs from its first to its last recorded event; work before the "
             "first event or after the last is not seen.")
    out["sessions"] = srows

    # 3 QA yield
    P.append("\n## 3. QA yield per tool")
    by = qa_yield(led)
    if not by:
        P.append("No QA iterations recorded.")
    else:
        rows = []
        for (cat, tool), x in sorted(by.items(), key=lambda kv: (-kv[1]["rounds"], kv[0])):
            rows.append([tool, cat, x["rounds"], x["reported"], x["gated"],
                         "%.2f" % (x["gated"] / float(x["rounds"])), x["fixed"], x["deferred"],
                         x["suppressed"], x["regressions"],
                         "%d/%d" % (x["empty_gated"], x["rounds"])])
        P.append(table(["tool", "category", "rounds", "findings", "GATED", "gated/round",
                        "fixed", "deferred", "suppressed", "new regressions",
                        "rounds with 0 gated"], rows))
        P.append("Counts are what each step logged (`log-step`): the agent narrates them; a "
                 "witnessed review (2.11+) is still the agent's count of the tool's output.")
        out["qa_yield"] = {"%s/%s" % k: dict(v, repos=sorted(v["repos"])) for k, v in by.items()}

    # 4 tests
    P.append("\n## 4. Test runs")
    trs = led.get("test_runs") or []
    if not trs:
        P.append("No `test-run` records (tests ingested by hand, or none run through the engine).")
    else:
        walls = [r["wall_ms"] / 1000.0 for r in trs if isinstance(r.get("wall_ms"), (int, float))]
        st = {}
        for r in trs:
            st[r.get("status") or "?"] = st.get(r.get("status") or "?", 0) + 1
        P.append("%d runs (%s). Wall time: median %s, p90 %s, total %s." % (
            len(trs), ", ".join("%s %d" % kv for kv in sorted(st.items())),
            fmt_dur(pct(walls, 0.5)), fmt_dur(pct(walls, 0.9)), fmt_dur(sum(walls))))
        cmds = {}
        for r in trs:
            cmds[r.get("command") or "?"] = cmds.get(r.get("command") or "?", 0) + 1
        P.append("Commands: " + "; ".join("`%s` x%d" % kv for kv in cmds.items()))
        out["tests"] = {"runs": len(trs), "status": st, "wall_s": walls}

    # 5 escapes
    P.append("\n## 5. Escapes and escalations")
    pf, es = led.get("production_findings") or [], led.get("escalations") or []
    P.append("Production findings recorded: %d. Escalations: %d. Spec doubts: %d." % (
        len(pf), len(es), len(led.get("spec_doubts") or [])))
    for x in pf[:10]:
        P.append("- PF: %s" % json.dumps(x, ensure_ascii=False)[:200])
    P.append("A bug fixed in production but never logged with `production-finding` is not here: "
             "this section is as complete as the logging.")
    out["escapes"] = {"production_findings": len(pf), "escalations": len(es)}

    # 6 telemetry
    P.append("\n## 6. Token and wall cost (vendor telemetry)")
    tp, tel = telemetry(root)
    if tel is None:
        P.append("No `%s`: run the mirador's `telemetry-extract.py` on session transcripts to "
                 "add cost per session." % tp)
    else:
        tin = sum(r.get("tokens_in") or 0 for r in tel)
        tout = sum(r.get("tokens_out") or 0 for r in tel)
        ms = sum(r.get("ms") or 0 for r in tel)
        P.append("%d session(s) in `%s`: tokens in %s, out %s, wall %s." % (
            len(tel), tp, "{:,}".format(tin), "{:,}".format(tout), fmt_dur(ms / 1000.0)))
        out["telemetry"] = {"sessions": len(tel), "tokens_in": tin, "tokens_out": tout, "ms": ms}

    print("\n".join(P))
    if a.json:
        # %TEMP% (cmd) and $env:TEMP (PowerShell) both reach here; expand what the shell did not
        target = os.path.expanduser(os.path.expandvars(a.json))
        with open(target, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=2, default=str)
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
