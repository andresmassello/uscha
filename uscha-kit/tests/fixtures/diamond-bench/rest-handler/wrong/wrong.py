# plausible-wrong: 405 conflated into 404, and ids reused after delete (len+1 counter)
import json, sys, re
try:
    reqs = json.load(sys.stdin)
    if not isinstance(reqs, list):
        raise ValueError
    items, order, out = {}, [], []
    for r in reqs:
        m, p, b = r.get("method"), r.get("path"), r.get("body")
        seg = re.fullmatch(r"/items/(\d+)", p or "")
        if p == "/items" and m == "POST":
            if isinstance(b, dict) and isinstance(b.get("name"), str):
                i = len(items) + 1                      # WRONG: reuses ids
                it = {"id": i, "name": b["name"]}
                items[i] = it; order.append(i)
                out.append({"status": 201, "body": it})
            else:
                out.append({"status": 400, "body": {"error": "bad request"}})
        elif p == "/items" and m == "GET":
            out.append({"status": 200, "body": [items[i] for i in order]})
        elif seg and m == "GET":
            i = int(seg.group(1))
            out.append({"status": 200, "body": items[i]} if i in items
                       else {"status": 404, "body": {"error": "not found"}})
        elif seg and m == "PUT":
            i = int(seg.group(1))
            if not (isinstance(b, dict) and isinstance(b.get("name"), str)):
                out.append({"status": 400, "body": {"error": "bad request"}})
            elif i in items:
                items[i]["name"] = b["name"]; out.append({"status": 200, "body": items[i]})
            else:
                out.append({"status": 404, "body": {"error": "not found"}})
        elif seg and m == "DELETE":
            i = int(seg.group(1))
            if i in items:
                del items[i]; order.remove(i); out.append({"status": 204, "body": None})
            else:
                out.append({"status": 404, "body": {"error": "not found"}})
        else:
            out.append({"status": 404, "body": {"error": "not found"}})   # WRONG: no 405
    print(json.dumps(out))
except Exception:
    print("ERROR")
