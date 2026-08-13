# plausible-wrong: SKIPS malformed frames (partial output instead of atomic ERROR) and sorts
# fields alphabetically (order not preserved)
import json, re, sys
try:
    d = json.load(sys.stdin)
    direction = d.get("direction")
    if direction == "decode":
        frames = d["frames"]
        if not isinstance(frames, list):
            raise ValueError
        out = []
        for f in frames:
            segs = f.split("|")
            if not re.fullmatch(r"[A-Z]+", segs[0] if segs else ""):
                continue                               # WRONG: skip, not atomic ERROR
            fields = []
            ok = True
            for s in segs[1:]:
                m = re.fullmatch(r"([a-z]+)=([^|=]*)", s)
                if not m:
                    ok = False
                    break
                fields.append([m.group(1), m.group(2)])
            if not ok:
                continue                               # WRONG: skip
            fields.sort(key=lambda kv: kv[0])          # WRONG: sorts fields
            out.append({"type": segs[0], "fields": fields})
        print(json.dumps(out))
    elif direction == "encode":
        msgs = d["messages"]
        out = []
        for msg in msgs:
            parts = [msg["type"]]
            for kv in sorted(msg["fields"], key=lambda kv: kv[0]):   # WRONG: sorts
                parts.append("%s=%s" % (kv[0], kv[1]))
            out.append("|".join(parts))
        print(json.dumps(out))
    else:
        raise ValueError
except Exception:
    print("ERROR")
