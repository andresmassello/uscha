#!/usr/bin/env python3
"""telemetry-extract.py -- vendor telemetry for the mirador (uscha-kit 1.33.0).

Parses a Claude Code session transcript (*.jsonl) and appends ONE line to the
telemetry sidecar (.uscha/telemetry.jsonl) summarizing that session's token and
wall-time cost, broken down by model.

This is VENDOR telemetry (Claude Code), NOT engine measurement. It lives in the
mirador skill (the vendor adapter), NEVER in qa_ledger.py -- the engine stays
model-agnostic and never sees a token. The mirador shows this in a segregated
strip; it is never gated and never feeds readiness (measured beats narrated).

Usage:
  python3 telemetry-extract.py <transcript.jsonl> [--sidecar .uscha/telemetry.jsonl] [--note "..."]

Best-effort: unknown/older transcript schemas degrade (missing fields -> 0/None),
never crash. If no usage data is found, nothing is appended.
"""
import argparse
import json
import os
import sys
from datetime import datetime


def _ts(v):
    if not v:
        return None
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def extract(transcript_path):
    """Returns (by_model: {model: [tin, tout]}, t_min, t_max, seen: bool)."""
    by_model = {}
    t_min = t_max = None
    seen = False
    with open(transcript_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            ts = _ts(rec.get("timestamp"))
            if ts:
                t_min = ts if (t_min is None or ts < t_min) else t_min
                t_max = ts if (t_max is None or ts > t_max) else t_max
            msg = rec.get("message") or {}
            usage = msg.get("usage")
            if not isinstance(usage, dict):
                continue
            model = msg.get("model") or rec.get("model") or "unknown"
            tin = ((usage.get("input_tokens") or 0)
                   + (usage.get("cache_read_input_tokens") or 0)
                   + (usage.get("cache_creation_input_tokens") or 0))
            tout = usage.get("output_tokens") or 0
            if tin == 0 and tout == 0:
                continue
            agg = by_model.setdefault(model, [0, 0])
            agg[0] += tin
            agg[1] += tout
            seen = True
    return by_model, t_min, t_max, seen


def main():
    ap = argparse.ArgumentParser(description="append a Claude Code session's token/time cost to the mirador telemetry sidecar")
    ap.add_argument("transcript", help="path to a Claude Code session transcript (*.jsonl)")
    ap.add_argument("--sidecar", default=os.path.join(".uscha", "telemetry.jsonl"),
                    help="append-only telemetry file (default: .uscha/telemetry.jsonl)")
    ap.add_argument("--session", default=None,
                    help="session key for idempotent upsert (default: transcript basename); "
                         "re-running replaces this session's line instead of appending -- "
                         "so a watch/refresh loop does not inflate the totals")
    ap.add_argument("--note", default=None, help="optional label for this session line")
    args = ap.parse_args()

    by_model, t_min, t_max, seen = extract(args.transcript)
    if not seen:
        print("[telemetry-extract] no usage data found -- nothing appended", file=sys.stderr)
        return 0

    bm = [{"model": m, "tokens_in": v[0], "tokens_out": v[1]}
          for m, v in sorted(by_model.items())]
    total_in = sum(v["tokens_in"] for v in bm)
    total_out = sum(v["tokens_out"] for v in bm)
    ms = int((t_max - t_min).total_seconds() * 1000) if (t_min and t_max) else None
    at = t_max.isoformat() if t_max else None
    rec = {
        "at": at,
        "model": bm[0]["model"] if len(bm) == 1 else "+".join(v["model"] for v in bm),
        "tokens_in": total_in, "tokens_out": total_out, "ms": ms,
        "by_model": bm,
    }
    session = args.session or os.path.basename(args.transcript)
    rec["session"] = session
    if args.note:
        rec["note"] = args.note

    os.makedirs(os.path.dirname(args.sidecar) or ".", exist_ok=True)
    # upsert by session: re-running (watch mode) REPLACES this session's line instead of
    # appending a duplicate -> a refresh loop never inflates the aggregated totals.
    kept = []
    if os.path.isfile(args.sidecar):
        for line in open(args.sidecar, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                prev = json.loads(line)
            except ValueError:
                continue
            if prev.get("session") != session:
                kept.append(prev)
    kept.append(rec)
    with open(args.sidecar, "w", encoding="utf-8") as f:
        for r in kept:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[telemetry-extract] {session}: {total_in} in / {total_out} out "
          f"across {len(bm)} model(s) -> {args.sidecar} (upsert)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
