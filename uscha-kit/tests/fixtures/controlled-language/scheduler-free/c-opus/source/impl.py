"""Priority job scheduler simulator with preemption and deadlines.

Reads one JSON array of jobs from standard input, simulates a single-CPU
scheduler over discrete ticks, and prints one JSON object describing what
happened. Malformed input prints exactly ERROR. Always exits 0.
"""

import json
import sys


def is_int(value):
    """True for JSON integers. Booleans are not integers."""
    return isinstance(value, int) and not isinstance(value, bool)


class Malformed(Exception):
    """Raised when the input does not satisfy the contract."""


def parse_jobs(raw_text):
    """Validate the raw stdin text and return the list of job dicts."""
    try:
        data = json.loads(raw_text)
    except Exception:
        raise Malformed()

    if not isinstance(data, list):
        raise Malformed()

    jobs = []
    seen_ids = set()
    for element in data:
        if not isinstance(element, dict):
            raise Malformed()

        for field in ("id", "priority", "arrival", "duration"):
            if field not in element:
                raise Malformed()
            if not is_int(element[field]):
                raise Malformed()

        if "deadline" in element and element["deadline"] is not None:
            if not is_int(element["deadline"]):
                raise Malformed()

        if element["arrival"] < 0 or element["duration"] < 0:
            raise Malformed()

        job_id = element["id"]
        if job_id in seen_ids:
            raise Malformed()
        seen_ids.add(job_id)

        deadline = element.get("deadline")
        if deadline is not None and not is_int(deadline):
            raise Malformed()

        jobs.append(
            {
                "id": job_id,
                "priority": element["priority"],
                "arrival": element["arrival"],
                "duration": element["duration"],
                "deadline": deadline,
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

    if not jobs:
        return {"events": events, "completed": completed, "missed": missed}

    pending = sorted(jobs, key=lambda job: (job["arrival"], job["id"]))
    pending_index = 0
    ready = []
    last_run_id = None
    tick = 0

    while True:
        if not ready and pending_index >= len(pending):
            break

        # 1. Arrivals.
        arrived = []
        while pending_index < len(pending) and pending[pending_index]["arrival"] == tick:
            arrived.append(pending[pending_index])
            pending_index += 1
        for job in sorted(arrived, key=lambda job: job["id"]):
            events.append([tick, "arrive", job["id"]])
            ready.append(job)

        # 2. Deadline check.
        dropped = [
            job
            for job in ready
            if job["deadline"] is not None and job["deadline"] <= tick
        ]
        for job in sorted(dropped, key=lambda job: job["id"]):
            events.append([tick, "missed", job["id"]])
            missed.append(job["id"])
            ready.remove(job)
            if last_run_id == job["id"]:
                last_run_id = None

        # 3. Selection.
        if ready:
            picked = min(
                ready,
                key=lambda job: (-job["priority"], job["arrival"], job["id"]),
            )
            if picked["id"] != last_run_id:
                if last_run_id is not None and any(
                    job["id"] == last_run_id for job in ready
                ):
                    events.append([tick, "preempt", last_run_id])
                if picked["started"]:
                    events.append([tick, "resume", picked["id"]])
                else:
                    events.append([tick, "start", picked["id"]])
                    picked["started"] = True

            # 4. Execution.
            picked["remaining"] -= 1
            last_run_id = picked["id"]
            if picked["remaining"] <= 0:
                events.append([tick, "complete", picked["id"]])
                completed.append(picked["id"])
                ready.remove(picked)
                last_run_id = None
        else:
            if pending_index < len(pending):
                events.append([tick, "idle", None])
            last_run_id = None

        tick += 1

    return {"events": events, "completed": completed, "missed": missed}


def main():
    try:
        result = simulate(parse_jobs(sys.stdin.read()))
    except Malformed:
        sys.stdout.write("ERROR\n")
        return 0

    sys.stdout.write(json.dumps(result) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
