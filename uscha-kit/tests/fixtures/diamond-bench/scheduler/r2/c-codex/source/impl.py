import json
import sys


REQUIRED_FIELDS = {"id", "priority", "arrival", "duration"}
ALLOWED_FIELDS = REQUIRED_FIELDS | {"deadline"}


def is_json_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def parse_jobs(value):
    if not isinstance(value, list):
        return None

    seen_ids = set()
    jobs = []
    for item in value:
        if not isinstance(item, dict):
            return None
        keys = set(item.keys())
        if not REQUIRED_FIELDS.issubset(keys):
            return None
        if not keys.issubset(ALLOWED_FIELDS):
            return None

        job_id = item["id"]
        priority = item["priority"]
        arrival = item["arrival"]
        duration = item["duration"]
        deadline = item.get("deadline")

        if not all(is_json_int(x) for x in (job_id, priority, arrival, duration)):
            return None
        if "deadline" in item and not is_json_int(deadline):
            return None
        if arrival < 0 or duration < 0:
            return None
        if job_id in seen_ids:
            return None

        seen_ids.add(job_id)
        jobs.append({
            "id": job_id,
            "priority": priority,
            "arrival": arrival,
            "duration": duration,
            "remaining": duration,
            "deadline": deadline if "deadline" in item else None,
            "has_deadline": "deadline" in item,
            "started": False,
        })

    return jobs


def simulate(jobs):
    events = []
    completed = []
    missed = []

    pending = sorted(jobs, key=lambda j: (j["arrival"], j["id"]))
    ready = {}
    pending_index = 0
    last_running_id = None
    tick = 0

    while pending_index < len(pending) or ready:
        arrived = []
        while pending_index < len(pending) and pending[pending_index]["arrival"] == tick:
            job = pending[pending_index]
            ready[job["id"]] = job
            arrived.append(job)
            pending_index += 1
        for job in sorted(arrived, key=lambda j: j["id"]):
            events.append([tick, "arrive", job["id"]])

        deadline_misses = [
            job for job in ready.values()
            if job["has_deadline"] and job["deadline"] <= tick
        ]
        for job in sorted(deadline_misses, key=lambda j: j["id"]):
            events.append([tick, "missed", job["id"]])
            missed.append(job["id"])
            del ready[job["id"]]

        if not ready:
            last_running_id = None
            if pending_index < len(pending):
                events.append([tick, "idle", None])
            tick += 1
            continue

        picked = min(
            ready.values(),
            key=lambda j: (-j["priority"], j["arrival"], j["id"]),
        )
        picked_id = picked["id"]

        if picked_id != last_running_id:
            if last_running_id in ready:
                events.append([tick, "preempt", last_running_id])
            if picked["started"]:
                events.append([tick, "resume", picked_id])
            else:
                events.append([tick, "start", picked_id])
                picked["started"] = True

        if picked["remaining"] > 0:
            picked["remaining"] -= 1
        if picked["remaining"] == 0:
            events.append([tick, "complete", picked_id])
            completed.append(picked_id)
            del ready[picked_id]
            last_running_id = None
        else:
            last_running_id = picked_id

        tick += 1

    return {"events": events, "completed": completed, "missed": missed}


def main():
    try:
        value = json.loads(sys.stdin.read())
    except Exception:
        print("ERROR")
        return

    jobs = parse_jobs(value)
    if jobs is None:
        print("ERROR")
        return

    print(json.dumps(simulate(jobs), separators=(",", ":")))


if __name__ == "__main__":
    main()
