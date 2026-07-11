#!/usr/bin/env python3
"""mirador-render.py -- render mirador.html from the live ledger (uscha-kit 1.34.0).

Standalone renderer used by the uscha-mirador skill AND by mirador-watch (the live
second-screen loop). It:
  1. runs `qa_ledger.py dashboard --json` (read-only engine call),
  2. if the telemetry sidecar exists, aggregates it (per-model merge) and merges a
     `telemetry` object into DATA -- vendor-reported, NEVER from the engine,
  3. injects `const DATA` between the template's markers and writes mirador.html.

The engine stays model-agnostic: telemetry is merged HERE, in the adapter, never in
qa_ledger.py.

Usage:
  python3 mirador-render.py --engine <qa_ledger.py> --ledger QA-LEDGER.json \
      --template mirador.template.html --out mirador.html \
      [--sidecar .uscha/telemetry.jsonl] [--refresh 30]
"""
import argparse
import json
import os
import re
import subprocess
import sys


def aggregate_telemetry(path):
    """Sum the sidecar's per-session lines into one telemetry object, merging by_model
    (tokens per model) across sessions. Returns None if the file is absent/empty."""
    if not path or not os.path.isfile(path):
        return None
    lines = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            lines.append(json.loads(line))
        except ValueError:
            continue
    if not lines:
        return None
    tin = sum(l.get("tokens_in") or 0 for l in lines)
    tout = sum(l.get("tokens_out") or 0 for l in lines)
    ms = sum(l.get("ms") or 0 for l in lines)
    by = {}
    for l in lines:
        for m in l.get("by_model") or []:
            agg = by.setdefault(m.get("model", "unknown"), [0, 0])
            agg[0] += m.get("tokens_in") or 0
            agg[1] += m.get("tokens_out") or 0
    by_model = [{"model": k, "tokens_in": v[0], "tokens_out": v[1]}
                for k, v in sorted(by.items())]
    effort = next((l.get("effort") for l in reversed(lines) if l.get("effort")), None)
    model = (by_model[0]["model"] if len(by_model) == 1
             else "+".join(m["model"] for m in by_model) if by_model else None)
    return {"source": "Claude Code", "sessions": len(lines),
            "tokens_in": tin, "tokens_out": tout, "ms": ms or None,
            "model": model, "effort": effort, "by_model": by_model}


def _json_for_html_script(value):
    """Serialize JSON without allowing data to terminate the enclosing script."""
    return (json.dumps(value, ensure_ascii=False)
            .replace("&", r"\u0026")
            .replace("<", r"\u003c")
            .replace(">", r"\u003e")
            .replace("\u2028", r"\u2028")
            .replace("\u2029", r"\u2029"))


def main():
    ap = argparse.ArgumentParser(description="render mirador.html from the ledger (+ optional vendor telemetry)")
    ap.add_argument("--engine", required=True, help="path to qa_ledger.py")
    ap.add_argument("--ledger", default="QA-LEDGER.json")
    ap.add_argument("--template", required=True, help="path to mirador.template.html")
    ap.add_argument("--out", default="mirador.html")
    ap.add_argument("--sidecar", default=os.path.join(".uscha", "telemetry.jsonl"))
    ap.add_argument("--refresh", type=int, default=0,
                    help="if >0, the page auto-reloads every N seconds (live second-screen view)")
    args = ap.parse_args()

    try:
        raw = subprocess.check_output(
            [sys.executable, args.engine, "dashboard", "--ledger", args.ledger, "--json"],
            text=True, encoding="utf-8")
    except (subprocess.CalledProcessError, OSError) as e:
        print(f"[mirador-render] dashboard failed: {e}", file=sys.stderr)
        return 1
    try:
        data = json.loads(raw)
    except ValueError as e:
        print(f"[mirador-render] dashboard returned invalid JSON: {e}", file=sys.stderr)
        return 1

    tel = aggregate_telemetry(args.sidecar)
    if tel:
        data["telemetry"] = tel  # vendor-reported, merged in the adapter -- never by the engine

    try:
        tpl = open(args.template, encoding="utf-8").read()
    except OSError as e:
        print(f"[mirador-render] cannot read template {args.template}: {e}", file=sys.stderr)
        return 1
    payload = ("/*MIRADOR_DATA_START*/\nconst DATA = "
               + _json_for_html_script(data) + ";\n/*MIRADOR_DATA_END*/")
    out = re.sub(r"/\*MIRADOR_DATA_START\*/.*?/\*MIRADOR_DATA_END\*/",
                 lambda m: payload, tpl, count=1, flags=re.S)
    if args.refresh and args.refresh > 0:
        # opt-in live reload: a meta-refresh, injected only when watching
        out = out.replace("</head>",
                          f'<meta http-equiv="refresh" content="{args.refresh}">\n</head>', 1)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(out)
    score = (data.get("readiness") or {}).get("score")
    print(f"[mirador-render] wrote {args.out} (readiness {score}, "
          f"telemetry {'on' if tel else 'off'}, refresh {args.refresh or 'off'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
