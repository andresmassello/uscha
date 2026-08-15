import sys
import json


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except Exception:
        print("ERROR")
        return

    if not isinstance(data, list):
        print("ERROR")
        return

    required_keys = {"id", "priority", "arrival", "duration"}
    allowed_keys = {"id", "priority", "arrival", "duration", "deadline"}

    jobs = []
    seen_ids = set()

    for item in data:
        if not isinstance(item, dict):
            print("ERROR")
            return

        keys = set(item.keys())
        if not required_keys.issubset(keys):
            print("ERROR")
            return
        if not keys.issubset(allowed_keys):
            print("ERROR")
            return

        for k in ("id", "priority", "arrival", "duration"):
            if not _is_int(item[k]):
                print("ERROR")
                return

        has_deadline = "deadline" in item
        if has_deadline and not _is_int(item["deadline"]):
            print("ERROR")
            return

        if item["arrival"] < 0 or item["duration"] < 0:
            print("ERROR")
            return

        jid = item["id"]
        if jid in seen_ids:
            print("ERROR")
            return
        seen_ids.add(jid)

        jobs.append({
            "id": jid,
            "priority": item["priority"],
            "arrival": item["arrival"],
            "duration": item["duration"],
            "deadline": item["deadline"] if has_deadline else None,
        })

    if not jobs:
        print(json.dumps({"events": [], "completed": [], "missed": []}))
        return

    remaining = {j["id"]: j["duration"] for j in jobs}
    priority = {j["id"]: j["priority"] for j in jobs}
    arrival = {j["id"]: j["arrival"] for j in jobs}
    deadline = {j["id"]: j["deadline"] for j in jobs}
    all_ids = [j["id"] for j in jobs]
    total = len(all_ids)

    not_arrived = set(all_ids)
    ready = set()
    ever_started = set()
    completed = []
    missed = []
    events = []
    last_run_id = None
    processed = 0
    tick = 0

    while processed < total:
        # Step 1: arrivals
        arriving_now = sorted(i for i in not_arrived if arrival[i] == tick)
        for i in arriving_now:
            events.append([tick, "arrive", i])
            ready.add(i)
            not_arrived.discard(i)

        # Step 2: deadline check.
        # A job is dropped once the current tick has strictly passed its
        # deadline. Using a strict "<" (rather than "<=") is what makes this
        # consistent with "a job completing at exactly its deadline tick has
        # NOT missed": at tick == deadline the job is still eligible to be
        # selected and finish this same tick.
        missed_now = sorted(
            i for i in ready
            if deadline[i] is not None and deadline[i] < tick
        )
        for i in missed_now:
            events.append([tick, "missed", i])
            ready.discard(i)
            missed.append(i)
            processed += 1

        # Step 3: selection
        if not ready:
            if not not_arrived:
                break
            events.append([tick, "idle", None])
            last_run_id = None
            tick += 1
            continue

        selected = min(ready, key=lambda i: (-priority[i], arrival[i], i))

        if last_run_id is not None and last_run_id != selected and last_run_id in ready:
            events.append([tick, "preempt", last_run_id])

        if selected != last_run_id:
            if selected in ever_started:
                events.append([tick, "resume", selected])
            else:
                events.append([tick, "start", selected])
                ever_started.add(selected)

        # Step 4: execution
        remaining[selected] -= 1
        if remaining[selected] <= 0:
            events.append([tick, "complete", selected])
            ready.discard(selected)
            completed.append(selected)
            processed += 1

        last_run_id = selected
        tick += 1

    print(json.dumps({"events": events, "completed": completed, "missed": missed}))


if __name__ == "__main__":
    main()
