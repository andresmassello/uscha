import json
import sys


ALLOWED_KEYS = {"id", "priority", "arrival", "duration", "deadline"}
REQUIRED_KEYS = {"id", "priority", "arrival", "duration"}


class InvalidInput(Exception):
    pass


def parse_jobs(data):
    if not isinstance(data, list):
        raise InvalidInput("not an array")

    jobs = []
    seen_ids = set()

    for item in data:
        if not isinstance(item, dict):
            raise InvalidInput("element not an object")

        keys = set(item.keys())
        if not REQUIRED_KEYS.issubset(keys):
            raise InvalidInput("missing required field")
        if not keys.issubset(ALLOWED_KEYS):
            raise InvalidInput("unexpected field")

        for field in ("id", "priority", "arrival", "duration"):
            value = item[field]
            if type(value) is not int:
                raise InvalidInput("field not an integer: %s" % field)

        deadline = None
        if "deadline" in item:
            if type(item["deadline"]) is not int:
                raise InvalidInput("deadline not an integer")
            deadline = item["deadline"]

        if item["arrival"] < 0:
            raise InvalidInput("negative arrival")
        if item["duration"] < 0:
            raise InvalidInput("negative duration")

        job_id = item["id"]
        if job_id in seen_ids:
            raise InvalidInput("duplicate id")
        seen_ids.add(job_id)

        jobs.append({
            "id": job_id,
            "priority": item["priority"],
            "arrival": item["arrival"],
            "duration": item["duration"],
            "deadline": deadline,
            "remaining": item["duration"],
        })

    return jobs


def simulate(jobs):
    by_id = {job["id"]: job for job in jobs}
    resolved = set()
    ready = set()
    started = set()

    events = []
    completed = []
    missed = []

    running_last_tick = None
    tick = 0

    all_ids = set(by_id.keys())

    while resolved != all_ids:
        # Step 1: arrivals
        arriving = sorted(
            jid for jid, job in by_id.items()
            if job["arrival"] == tick and jid not in resolved and jid not in ready
        )
        for jid in arriving:
            ready.add(jid)
            events.append([tick, "arrive", jid])

        # Step 2: deadline check
        missing_now = []
        for jid in sorted(ready):
            job = by_id[jid]
            if job["deadline"] is not None and job["deadline"] <= tick:
                missing_now.append(jid)
        for jid in missing_now:
            ready.discard(jid)
            resolved.add(jid)
            missed.append(jid)
            events.append([tick, "missed", jid])

        # Step 3: selection
        picked = None
        if ready:
            picked = min(
                ready,
                key=lambda jid: (-by_id[jid]["priority"], by_id[jid]["arrival"], jid),
            )
            if picked != running_last_tick:
                if running_last_tick is not None and running_last_tick in ready:
                    events.append([tick, "preempt", running_last_tick])
                if picked not in started:
                    started.add(picked)
                    events.append([tick, "start", picked])
                else:
                    events.append([tick, "resume", picked])
        else:
            events.append([tick, "idle", None])

        # Step 4: execution
        if picked is not None:
            job = by_id[picked]
            job["remaining"] -= 1
            if job["remaining"] <= 0:
                events.append([tick, "complete", picked])
                completed.append(picked)
                ready.discard(picked)
                resolved.add(picked)
            running_last_tick = picked
        else:
            running_last_tick = None

        tick += 1

    return {"events": events, "completed": completed, "missed": missed}


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
        jobs = parse_jobs(data)
        result = simulate(jobs)
    except Exception:
        print("ERROR")
        return

    print(json.dumps(result))


if __name__ == "__main__":
    main()
