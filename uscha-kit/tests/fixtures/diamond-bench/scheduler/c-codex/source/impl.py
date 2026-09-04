import json
import sys


REQUIRED_FIELDS = {"id", "priority", "arrival", "duration"}
OPTIONAL_FIELDS = {"deadline"}
ALLOWED_FIELDS = REQUIRED_FIELDS | OPTIONAL_FIELDS


def is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def parse_jobs(value):
    if not isinstance(value, list):
        raise ValueError

    seen_ids = set()
    jobs = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError
        keys = set(item.keys())
        if not REQUIRED_FIELDS.issubset(keys):
            raise ValueError
        if not keys.issubset(ALLOWED_FIELDS):
            raise ValueError

        for field in ALLOWED_FIELDS:
            if field in item and not is_int(item[field]):
                raise ValueError

        job_id = item["id"]
        if job_id in seen_ids:
            raise ValueError
        seen_ids.add(job_id)

        arrival = item["arrival"]
        duration = item["duration"]
        if arrival < 0 or duration < 0:
            raise ValueError

        jobs.append({
            "id": job_id,
            "priority": item["priority"],
            "arrival": arrival,
            "duration": duration,
            "remaining": duration,
            "deadline": item.get("deadline"),
            "started": False,
            "completed": False,
            "missed": False,
        })

    return jobs


def select_job(ready):
    return min(ready, key=lambda job: (-job["priority"], job["arrival"], job["id"]))


def simulate(jobs):
    events = []
    completed = []
    missed = []

    if not jobs:
        return {"events": events, "completed": completed, "missed": missed}

    by_arrival = {}
    for job in jobs:
        by_arrival.setdefault(job["arrival"], []).append(job)
    for arrivals in by_arrival.values():
        arrivals.sort(key=lambda job: job["id"])

    total_jobs = len(jobs)
    done_count = 0
    ready = []
    tick = 0
    last_running = None

    while done_count < total_jobs:
        for job in by_arrival.get(tick, []):
            ready.append(job)
            events.append([tick, "arrive", job["id"]])

        expired = [
            job for job in ready
            if job["deadline"] is not None and job["deadline"] <= tick
        ]
        if expired:
            expired_ids = {job["id"] for job in expired}
            for job in sorted(expired, key=lambda item: item["id"]):
                job["missed"] = True
                missed.append(job["id"])
                events.append([tick, "missed", job["id"]])
                done_count += 1
            ready = [job for job in ready if job["id"] not in expired_ids]

        picked = None
        if ready:
            picked = select_job(ready)
            if last_running is not None and picked["id"] != last_running["id"]:
                if any(job["id"] == last_running["id"] for job in ready):
                    events.append([tick, "preempt", last_running["id"]])
            if last_running is None or picked["id"] != last_running["id"]:
                if picked["started"]:
                    events.append([tick, "resume", picked["id"]])
                else:
                    picked["started"] = True
                    events.append([tick, "start", picked["id"]])

            if picked["remaining"] > 0:
                picked["remaining"] -= 1
            if picked["remaining"] == 0:
                picked["completed"] = True
                completed.append(picked["id"])
                events.append([tick, "complete", picked["id"]])
                ready = [job for job in ready if job["id"] != picked["id"]]
                done_count += 1
                last_running = None
            else:
                last_running = picked
        else:
            future_arrival_exists = any(arrival > tick for arrival in by_arrival)
            if future_arrival_exists:
                events.append([tick, "idle", None])
            last_running = None

        tick += 1

    return {"events": events, "completed": completed, "missed": missed}


def main():
    try:
        raw = sys.stdin.read()
        value = json.loads(raw)
        jobs = parse_jobs(value)
        result = simulate(jobs)
        print(json.dumps(result, separators=(",", ":")))
    except Exception:
        print("ERROR")


if __name__ == "__main__":
    main()
