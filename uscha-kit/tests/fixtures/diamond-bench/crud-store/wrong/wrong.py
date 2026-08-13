# plausible-wrong: upsert semantics (create overwrites, update inserts)
import json, sys
try:
    ops = json.load(sys.stdin)
    if not isinstance(ops, list):
        raise ValueError
    store, out = {}, []
    for o in ops:
        op = o.get("op")
        if op in ("create", "update") and isinstance(o.get("key"), str) and "value" in o:
            store[o["key"]] = o["value"]                # WRONG: silent upsert both ways
            out.append({"ok": True, "result": None})
        elif op == "read" and isinstance(o.get("key"), str):
            out.append({"ok": True, "result": store[o["key"]]} if o["key"] in store
                       else {"ok": False, "error": "missing"})
        elif op == "delete" and isinstance(o.get("key"), str):
            if o["key"] in store:
                del store[o["key"]]; out.append({"ok": True, "result": None})
            else:
                out.append({"ok": False, "error": "missing"})
        elif op == "list":
            out.append({"ok": True, "result": sorted(store.keys())})
        else:
            out.append({"ok": False, "error": "bad op"})
    print(json.dumps(out))
except Exception:
    print("ERROR")
