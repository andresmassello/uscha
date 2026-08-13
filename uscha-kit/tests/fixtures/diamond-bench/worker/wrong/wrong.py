# plausible-wrong: ignores priorities (plain FIFO over ready jobs) and treats a FAILED job as
# satisfying its dependents' needs (runs dependents of failed jobs)
import json, sys
try:
    d = json.load(sys.stdin)
    jobs = d["jobs"]
    if not isinstance(jobs, list) or not all(isinstance(j, dict) and isinstance(j.get("id"), str)
                                             and isinstance(j.get("priority"), int) for j in jobs):
        raise ValueError
    ids = [j["id"] for j in jobs]
    if len(set(ids)) != len(ids):
        raise ValueError
    byid = {j["id"]: j for j in jobs}
    for j in jobs:
        for n in j.get("needs") or []:
            if n not in byid:
                raise ValueError
    state = {}
    def visit(i):
        if state.get(i) == 1:
            raise ValueError
        if state.get(i) == 2:
            return
        state[i] = 1
        for n in byid[i].get("needs") or []:
            visit(n)
        state[i] = 2
    for i in ids:
        visit(i)
    status, order, done = {}, [], set()
    while True:
        ready = [j for j in jobs if j["id"] not in status
                 and all(n in done for n in (j.get("needs") or []))]
        if not ready:
            break
        j = ready[0]                                   # WRONG: FIFO only, priority ignored
        order.append(j["id"])
        status[j["id"]] = "failed" if j.get("fails") else "ok"
        done.add(j["id"])                              # WRONG: failed counts as done
    for i in ids:
        status.setdefault(i, "skipped")
    print(json.dumps({"order": order, "status": status}))
except Exception:
    print("ERROR")
