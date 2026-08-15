import json
import sys


def is_int_strict(v):
    return isinstance(v, int) and not isinstance(v, bool)


def validate_and_parse(data):
    """Returns (jobs_list, ok). jobs_list is a list of dicts with keys
    id, priority, arrival, duration, deadline (deadline may be None)."""
    if not isinstance(data, list):
        return None, False

    required = {"id", "priority", "arrival", "duration"}
    optional = {"deadline"}
    allowed = required | optional

    jobs = []
    seen_ids = set()

    for elem in data:
        if not isinstance(elem, dict):
            return None, False

        keys = set(elem.keys())
        if not required.issubset(keys):
            return None, False
        if not keys <= allowed:
            return None, False

        for field in ("id", "priority", "arrival", "duration"):
            if not is_int_strict(elem[field]):
                return None, False

        deadline = None
        if "deadline" in elem:
            if not is_int_strict(elem["deadline"]):
                return None, False
            deadline = elem["deadline"]

        if elem["arrival"] < 0 or elem["duration"] < 0:
            return None, False

        job_id = elem["id"]
        if job_id in seen_ids:
            return None, False
        seen_ids.add(job_id)

        jobs.append({
            "id": job_id,
            "priority": elem["priority"],
            "arrival": elem["arrival"],
            "duration": elem["duration"],
            "deadline": deadline,
        })

    return jobs, True


def simulate(jobs):
    total = len(jobs)
    if total == 0:
        return {"events": [], "completed": [], "missed": []}

    states = {}
    for j in jobs:
        states[j["id"]] = {
            "id": j["id"],
            "priority": j["priority"],
            "arrival": j["arrival"],
            "deadline": j["deadline"],
            "remaining": j["duration"],
            "started": False,
            "arrived": False,
        }

    pending_ids = set(states.keys())
    ready = {}
    events = []
    completed = []
    missed = []
    prev_running_id = None
    done_count = 0
    tick = 0

    while done_count < total:
        # Step 1 -- arrivals
        arriving = sorted(
            (s for s in states.values() if not s["arrived"] and s["arrival"] == tick),
            key=lambda s: s["id"],
        )
        for s in arriving:
            s["arrived"] = True
            pending_ids.discard(s["id"])
            ready[s["id"]] = s
            events.append([tick, "arrive", s["id"]])

        # Step 2 -- deadline check
        missed_ids_this_tick = []

        # 2a: unambiguous misses -- deadline strictly passed, or deadline is
        # this tick but the job cannot possibly finish this tick even if run.
        unambiguous = [
            s for s in ready.values()
            if s["deadline"] is not None
            and (s["deadline"] < tick or (s["deadline"] == tick and s["remaining"] > 1))
        ]
        for s in unambiguous:
            del ready[s["id"]]
            missed_ids_this_tick.append(s["id"])

        # 2b: tentative selection among what remains ready, to resolve the
        # borderline case: a job whose deadline is exactly this tick and
        # whose remaining work is <=1 tick is only spared if it actually
        # gets to run (and thus complete) this very tick.
        winner = None
        if ready:
            winner = min(
                ready.values(),
                key=lambda s: (-s["priority"], s["arrival"], s["id"]),
            )

        borderline_losers = [
            s for s in ready.values()
            if s["deadline"] is not None
            and s["deadline"] == tick
            and s["remaining"] <= 1
            and (winner is None or s["id"] != winner["id"])
        ]
        for s in borderline_losers:
            del ready[s["id"]]
            missed_ids_this_tick.append(s["id"])

        if borderline_losers and ready:
            # the removal of borderline losers cannot change who the winner
            # is (the winner was never a candidate for removal), so no
            # re-selection is necessary.
            pass

        for jid in sorted(missed_ids_this_tick):
            events.append([tick, "missed", jid])
            missed.append(jid)
            done_count += 1

        # Step 3 -- selection
        selected = None
        if ready:
            selected = min(
                ready.values(),
                key=lambda s: (-s["priority"], s["arrival"], s["id"]),
            )

        if selected is None:
            if pending_ids:
                events.append([tick, "idle", None])
        else:
            sid = selected["id"]
            if prev_running_id is not None and prev_running_id != sid and prev_running_id in ready:
                events.append([tick, "preempt", prev_running_id])
            if sid != prev_running_id:
                if not selected["started"]:
                    events.append([tick, "start", sid])
                else:
                    events.append([tick, "resume", sid])

            # Step 4 -- execution
            selected["started"] = True
            if selected["remaining"] > 0:
                selected["remaining"] -= 1
            if selected["remaining"] == 0:
                events.append([tick, "complete", sid])
                completed.append(sid)
                del ready[sid]
                done_count += 1

        prev_running_id = selected["id"] if selected is not None else None

        tick += 1

    return {"events": events, "completed": completed, "missed": missed}


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except Exception:
        print("ERROR")
        return

    jobs, ok = validate_and_parse(data)
    if not ok:
        print("ERROR")
        return

    try:
        result = simulate(jobs)
    except Exception:
        print("ERROR")
        return

    print(json.dumps(result))


if __name__ == "__main__":
    main()
