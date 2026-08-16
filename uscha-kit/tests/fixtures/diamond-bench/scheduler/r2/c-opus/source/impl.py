"""Priority job scheduler with preemption and deadlines.

Reads a JSON array of jobs from standard input, simulates a single-CPU
scheduler over discrete ticks, and prints one JSON result object.
On malformed input, prints exactly ERROR.
"""

import json
import sys

REQUIRED_FIELDS = ("id", "priority", "arrival", "duration")
INT_FIELDS = ("id", "priority", "arrival", "duration", "deadline")


class MalformedInput(Exception):
    """Raised when the input array violates the contract."""


def is_int(value):
    """JSON booleans are not integers, even though bool subclasses int."""
    return isinstance(value, int) and not isinstance(value, bool)


def parse_jobs(raw):
    """Validate the decoded input and return the job list.

    Raises MalformedInput on any contract violation.
    """
    if not isinstance(raw, list):
        raise MalformedInput("input is not a JSON array")

    jobs = []
    seen_ids = set()
    for element in raw:
        if not isinstance(element, dict):
            raise MalformedInput("element is not an object")
        for field in REQUIRED_FIELDS:
            if field not in element:
                raise MalformedInput("missing field")
        for field in INT_FIELDS:
            if field in element and not is_int(element[field]):
                raise MalformedInput("field is not an integer")
        if element["arrival"] < 0 or element["duration"] < 0:
            raise MalformedInput("negative arrival or duration")
        job_id = element["id"]
        if job_id in seen_ids:
            raise MalformedInput("duplicate id")
        seen_ids.add(job_id)
        jobs.append(
            {
                "id": job_id,
                "priority": element["priority"],
                "arrival": element["arrival"],
                "duration": element["duration"],
                "deadline": element.get("deadline"),
                "remaining": element["duration"],
                "started": False,
            }
        )
    return jobs


def simulate(jobs):
    """Run the tick loop and return the result object."""
    events = []
    completed = []
    missed = []

    pending = sorted(jobs, key=lambda j: (j["arrival"], j["id"]))
    ready = []
    last_run_id = None
    tick = 0

    while pending or ready:
        # 1. Arrivals: every job whose arrival equals this tick becomes ready.
        arriving = [j for j in pending if j["arrival"] == tick]
        if arriving:
            pending = [j for j in pending if j["arrival"] != tick]
            for job in sorted(arriving, key=lambda j: j["id"]):
                events.append([tick, "arrive", job["id"]])
                ready.append(job)

        # 2. Deadline check: drop ready jobs already at or past their deadline.
        expired = [
            j for j in ready if j["deadline"] is not None and j["deadline"] <= tick
        ]
        if expired:
            for job in sorted(expired, key=lambda j: j["id"]):
                events.append([tick, "missed", job["id"]])
                missed.append(job["id"])
            expired_ids = set(j["id"] for j in expired)
            ready = [j for j in ready if j["id"] not in expired_ids]
            if last_run_id in expired_ids:
                last_run_id = None

        # 3. Selection: highest priority, then earliest arrival, then lowest id.
        if not ready:
            if pending:
                events.append([tick, "idle", None])
                last_run_id = None
                tick += 1
                continue
            break

        picked = min(
            ready, key=lambda j: (-j["priority"], j["arrival"], j["id"])
        )

        if picked["id"] != last_run_id:
            if last_run_id is not None and any(j["id"] == last_run_id for j in ready):
                events.append([tick, "preempt", last_run_id])
            if picked["started"]:
                events.append([tick, "resume", picked["id"]])
            else:
                events.append([tick, "start", picked["id"]])
                picked["started"] = True

        # 4. Execution: the picked job runs for this tick.
        picked["remaining"] -= 1
        if picked["remaining"] <= 0:
            events.append([tick, "complete", picked["id"]])
            completed.append(picked["id"])
            ready = [j for j in ready if j["id"] != picked["id"]]
            last_run_id = None
        else:
            last_run_id = picked["id"]

        tick += 1

    return {"events": events, "completed": completed, "missed": missed}


def main():
    data = sys.stdin.read()
    try:
        raw = json.loads(data)
        jobs = parse_jobs(raw)
    except (ValueError, MalformedInput):
        print("ERROR")
        return 0
    print(json.dumps(simulate(jobs)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
