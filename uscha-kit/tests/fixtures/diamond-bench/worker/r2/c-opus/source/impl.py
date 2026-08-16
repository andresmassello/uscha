#!/usr/bin/env python3
"""Deterministic job scheduler.

Reads one JSON object {"jobs": [...]} from stdin, prints one line with
{"order": [...], "status": {...}} or exactly ERROR. Always exits 0.

Scheduling rule (total and deterministic, INV-WK-DET-01):
  - a job is READY when every id in its `needs` has completed with status ok;
  - among READY jobs, the highest `priority` runs first;
  - a priority tie breaks by position in the input array (FIFO).
Executing a job with `fails: true` marks it failed; its dependents, transitively,
are never executed and are marked skipped.

Structural problems (duplicate id, unknown id in needs, dependency cycle) and
malformed input reject the WHOLE input: print ERROR, never a partial schedule.
"""

import json
import sys


class Invalid(Exception):
    """Raised for malformed input or a structural rejection."""


def _is_int(value):
    # bool is a subclass of int in Python; a boolean is not a priority.
    return isinstance(value, int) and not isinstance(value, bool)


def parse_jobs(payload):
    """Validate the payload and return the job list in input order."""
    if not isinstance(payload, dict):
        raise Invalid("top level is not an object")
    if "jobs" not in payload:
        raise Invalid("missing jobs")
    raw_jobs = payload["jobs"]
    if not isinstance(raw_jobs, list):
        raise Invalid("jobs is not an array")

    jobs = []
    seen = set()
    for raw in raw_jobs:
        if not isinstance(raw, dict):
            raise Invalid("job is not an object")

        job_id = raw.get("id")
        if not isinstance(job_id, str):
            raise Invalid("job id is not a string")
        if job_id in seen:
            raise Invalid("duplicate job id")
        seen.add(job_id)

        priority = raw.get("priority")
        if not _is_int(priority):
            raise Invalid("job priority is not an integer")

        raw_needs = raw.get("needs", [])
        if raw_needs is None:
            raw_needs = []
        if not isinstance(raw_needs, list):
            raise Invalid("needs is not an array")
        needs = []
        for need in raw_needs:
            if not isinstance(need, str):
                raise Invalid("need is not a string")
            needs.append(need)

        fails = raw.get("fails", False)
        if fails is None:
            fails = False
        if not isinstance(fails, bool):
            raise Invalid("fails is not a boolean")

        jobs.append({
            "id": job_id,
            "priority": priority,
            "needs": needs,
            "fails": fails,
        })

    known = seen
    for job in jobs:
        for need in job["needs"]:
            if need not in known:
                raise Invalid("unknown id in needs")

    return jobs


def assert_acyclic(jobs):
    """Reject any dependency cycle anywhere in the graph."""
    needs_of = dict((job["id"], job["needs"]) for job in jobs)
    # 0 = unvisited, 1 = on the current path, 2 = done
    state = dict((job["id"], 0) for job in jobs)

    for job in jobs:
        if state[job["id"]] != 0:
            continue
        # Iterative DFS so deep graphs cannot blow the recursion limit.
        stack = [(job["id"], 0)]
        state[job["id"]] = 1
        while stack:
            node, index = stack[-1]
            deps = needs_of[node]
            if index < len(deps):
                stack[-1] = (node, index + 1)
                dep = deps[index]
                if state[dep] == 1:
                    raise Invalid("dependency cycle")
                if state[dep] == 0:
                    state[dep] = 1
                    stack.append((dep, 0))
            else:
                state[node] = 2
                stack.pop()


def schedule(jobs):
    """Run the deterministic schedule; return (order, status)."""
    status = {}
    order = []
    # Position in the input array is the FIFO tie-break.
    position = dict((job["id"], i) for i, job in enumerate(jobs))

    while True:
        candidate = None
        for job in jobs:
            if job["id"] in status:
                continue
            if not all(status.get(need) == "ok" for need in job["needs"]):
                continue
            if candidate is None:
                candidate = job
            elif job["priority"] > candidate["priority"]:
                candidate = job
            elif (job["priority"] == candidate["priority"]
                  and position[job["id"]] < position[candidate["id"]]):
                candidate = job
        if candidate is None:
            break
        status[candidate["id"]] = "failed" if candidate["fails"] else "ok"
        order.append(candidate["id"])

    # Whatever never became runnable depends (transitively) on a failure.
    for job in jobs:
        if job["id"] not in status:
            status[job["id"]] = "skipped"

    return order, status


def main():
    try:
        payload = json.loads(sys.stdin.read())
        jobs = parse_jobs(payload)
        assert_acyclic(jobs)
        order, status = schedule(jobs)
        sys.stdout.write(json.dumps({"order": order, "status": status}) + "\n")
    except Exception:
        sys.stdout.write("ERROR\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
