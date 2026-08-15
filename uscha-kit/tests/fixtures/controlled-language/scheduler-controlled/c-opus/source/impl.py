#!/usr/bin/env python3
"""Single-CPU priority job scheduler simulator with preemption and deadlines.

Reads one JSON value (an array of jobs) from standard input, simulates the
schedule over discrete ticks, and prints one line: the result JSON object or
exactly ERROR for a malformed input. Always exits with code 0.
"""

import json
import sys

REQUIRED_FIELDS = ("id", "priority", "arrival", "duration")
ALLOWED_FIELDS = frozenset(REQUIRED_FIELDS + ("deadline",))


class MalformedInput(Exception):
    """Raised when the input is not a well-formed array of jobs."""


def as_integer(value):
    """Return value when it is a JSON integer; a JSON boolean is not an integer."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise MalformedInput()
    return value


def parse_jobs(raw):
    """Validate the parsed JSON value and build the job records."""
    if not isinstance(raw, list):
        raise MalformedInput()

    jobs = []
    seen_ids = set()
    for element in raw:
        if not isinstance(element, dict):
            raise MalformedInput()
        if not set(element.keys()).issubset(ALLOWED_FIELDS):
            raise MalformedInput()
        for field in REQUIRED_FIELDS:
            if field not in element:
                raise MalformedInput()

        job = {
            "id": as_integer(element["id"]),
            "priority": as_integer(element["priority"]),
            "arrival": as_integer(element["arrival"]),
            "duration": as_integer(element["duration"]),
            "deadline": None,
        }
        if "deadline" in element:
            job["deadline"] = as_integer(element["deadline"])
        if job["arrival"] < 0 or job["duration"] < 0:
            raise MalformedInput()
        if job["id"] in seen_ids:
            raise MalformedInput()
        seen_ids.add(job["id"])

        job["remaining"] = job["duration"]
        job["has_run"] = False
        jobs.append(job)

    return jobs


def simulate(jobs):
    """Run the tick loop and return the result object."""
    events = []
    completed = []
    missed = []

    pending = sorted(jobs, key=lambda job: (job["arrival"], job["id"]))
    ready = []
    previous_id = None
    tick = 0

    while pending or ready:
        # Step 1 - arrivals, in ascending id order.
        arrived = [job for job in pending if job["arrival"] <= tick]
        if arrived:
            pending = [job for job in pending if job["arrival"] > tick]
            for job in sorted(arrived, key=lambda job: job["id"]):
                ready.append(job)
                events.append([tick, "arrive", job["id"]])

        # Step 2 - deadline check, in ascending id order.
        expired = [
            job
            for job in ready
            if job["deadline"] is not None and job["deadline"] <= tick
        ]
        if expired:
            for job in sorted(expired, key=lambda job: job["id"]):
                events.append([tick, "missed", job["id"]])
                missed.append(job["id"])
            expired_ids = set(job["id"] for job in expired)
            ready = [job for job in ready if job["id"] not in expired_ids]

        # Step 3 - selection.
        selected = None
        if ready:
            selected = min(
                ready,
                key=lambda job: (-job["priority"], job["arrival"], job["id"]),
            )
            if selected["id"] != previous_id:
                if previous_id is not None and any(
                    job["id"] == previous_id for job in ready
                ):
                    events.append([tick, "preempt", previous_id])
                name = "resume" if selected["has_run"] else "start"
                events.append([tick, name, selected["id"]])
            selected["has_run"] = True
        elif pending:
            events.append([tick, "idle", None])

        # Step 4 - execution.
        if selected is None:
            previous_id = None
        else:
            if selected["remaining"] > 0:
                selected["remaining"] -= 1
            if selected["remaining"] == 0:
                events.append([tick, "complete", selected["id"]])
                completed.append(selected["id"])
                ready = [job for job in ready if job["id"] != selected["id"]]
                previous_id = None
            else:
                previous_id = selected["id"]

        tick += 1

    return {"events": events, "completed": completed, "missed": missed}


def main():
    try:
        raw = json.loads(sys.stdin.read())
        jobs = parse_jobs(raw)
    except (MalformedInput, ValueError):
        sys.stdout.write("ERROR\n")
        return
    sys.stdout.write(json.dumps(simulate(jobs)) + "\n")


if __name__ == "__main__":
    main()
