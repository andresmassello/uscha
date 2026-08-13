# plausible-wrong: reset CLEARS fields (instead of restoring the initial model) and submit
# always sets submitted true (no validation)
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
            cur = {n: ("" if isinstance(initial[n], str) else False) for n in names}  # WRONG
            submitted, errors = False, []
        elif t == "submit":
            submitted, errors = True, []               # WRONG: no validation
        else:
            raise ValueError
    print(json.dumps({"fields": cur, "submitted": submitted, "errors": errors}))
except Exception:
    print("ERROR")
