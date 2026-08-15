# WRONG on purpose (ADR-025 discrimination fixture): ties break by id, ignoring earlier arrival
import json
import sys


def is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def fail():
    print("ERROR")
    sys.exit(0)


def main():
    try:
        jobs = json.loads(sys.stdin.read())
    except (ValueError, TypeError):
        fail()
    if not isinstance(jobs, list):
        fail()
    seen = set()
    parsed = []
    for j in jobs:
        if not isinstance(j, dict):
            fail()
        for k in ("id", "priority", "arrival", "duration"):
            if k not in j or not is_int(j[k]):
                fail()
        if "deadline" in j and not is_int(j["deadline"]):
            fail()
        if j["arrival"] < 0 or j["duration"] < 0:
            fail()
        if j["id"] in seen:
            fail()
        seen.add(j["id"])
        parsed.append({"id": j["id"], "priority": j["priority"], "arrival": j["arrival"],
                       "remaining": j["duration"], "deadline": j.get("deadline"),
                       "started": False})
    events, completed, missed = [], [], []
    ready = []          # list of job dicts
    pending = sorted(parsed, key=lambda x: (x["arrival"], x["id"]))
    last_id = None
    tick = 0
    while pending or ready:
        # 1 arrivals
        arriving = [p for p in pending if p["arrival"] == tick]
        for p in sorted(arriving, key=lambda x: x["id"]):
            events.append([tick, "arrive", p["id"]])
            ready.append(p)
        pending = [p for p in pending if p["arrival"] != tick]
        # 2 deadline check
        dropped = [r for r in ready if r["deadline"] is not None and r["deadline"] <= tick]
        for r in sorted(dropped, key=lambda x: x["id"]):
            events.append([tick, "missed", r["id"]])
            missed.append(r["id"])
            ready.remove(r)
            if last_id == r["id"]:
                last_id = None
        # 3 selection
        if not ready:
            if not pending:
                break          # nothing left anywhere: the simulation ended last tick
            events.append([tick, "idle", None])
            last_id = None
            tick += 1
            continue
        pick = sorted(ready, key=lambda x: (-x["priority"], x["id"]))[0]
        if pick["id"] != last_id:
            if last_id is not None and any(r["id"] == last_id for r in ready):
                events.append([tick, "preempt", last_id])
            events.append([tick, "start" if not pick["started"] else "resume", pick["id"]])
            pick["started"] = True
        # 4 execution
        if pick["remaining"] > 0:
            pick["remaining"] -= 1
        if pick["remaining"] == 0:
            events.append([tick, "complete", pick["id"]])
            completed.append(pick["id"])
            ready.remove(pick)
            last_id = None
        else:
            last_id = pick["id"]
        tick += 1
    print(json.dumps({"events": events, "completed": completed, "missed": missed}))
    sys.exit(0)


if __name__ == "__main__":
    main()
