# plausible-wrong: sorts the errors list ALPHABETICALLY instead of preserving
# field order (the discrimination gap the ADR-020 blind review exposed)
import json, sys
try:
    d = json.load(sys.stdin)
    fields = d["model"]["fields"]
    events = d["events"]
    if not isinstance(fields, list) or not isinstance(events, list):
        raise ValueError
    names = [f["name"] for f in fields]
    if len(set(names)) != len(names):
        raise ValueError
    initial = {f["name"]: f["value"] for f in fields}
    if not all(isinstance(v, (str, bool)) for v in initial.values()):
        raise ValueError
    cur = dict(initial)
    submitted, errors = False, []
    for e in events:
        t = e.get("type")
        if t == "input":
            f = e.get("field")
            if f not in cur or not isinstance(cur[f], str):
                raise ValueError
            cur[f] = e["value"]
        elif t == "toggle":
            f = e.get("field")
            if f not in cur or not isinstance(cur[f], bool):
                raise ValueError
            cur[f] = not cur[f]
        elif t == "reset":
            cur = dict(initial); submitted, errors = False, []
        elif t == "submit":
            empty = [n for n in names if isinstance(cur[n], str) and cur[n] == ""]
            if empty:
                submitted, errors = False, sorted(empty)
            else:
                submitted, errors = True, []
        else:
            raise ValueError
    print(json.dumps({"fields": cur, "submitted": submitted, "errors": errors}))
except Exception:
    print("ERROR")
