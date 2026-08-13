#!/usr/bin/env python3
"""Deterministic job scheduler.

Reads a JSON object {"jobs": [...]} from stdin, computes the single correct
execution schedule under the deterministic rule (dependencies first, then
highest priority, then input order), and prints {"order": [...], "status": {...}}.

Structural problems (malformed input, duplicate ids, unknown needs, cycles)
reject the WHOLE input: print exactly ERROR. Always exit 0.
"""

import json
import sys


class SpecError(Exception):
    """Structural rejection of the input as a whole."""


def parse_jobs(raw):
    """Validate the input document and return the ordered list of jobs.

    Each returned job is a dict with keys: id (str), priority (int),
    needs (list of str), fails (bool).
    """
    if not isinstance(raw, dict):
        raise SpecError("top level is not an object")

    jobs_raw = raw.get("jobs")
    if not isinstance(jobs_raw, list):
        raise SpecError("jobs is missing or not an array")

    jobs = []
    seen = set()
    for entry in jobs_raw:
        if not isinstance(entry, dict):
            raise SpecError("job is not an object")

        job_id = entry.get("id")
        if not isinstance(job_id, str):
            raise SpecError("job id is missing or not a string")
        if job_id in seen:
            raise SpecError("duplicate job id")
        seen.add(job_id)

        priority = entry.get("priority")
        # bool is a subclass of int in Python; a boolean priority is malformed.
        if not isinstance(priority, int) or isinstance(priority, bool):
            raise SpecError("job priority is missing or not an int")

        needs = entry.get("needs", [])
        if needs is None:
            needs = []
        if not isinstance(needs, list):
            raise SpecError("job needs is not an array")
        for need in needs:
            if not isinstance(need, str):
                raise SpecError("need is not a string")

        fails = entry.get("fails", False)
        if fails is None:
            fails = False
        if not isinstance(fails, bool):
            raise SpecError("job fails is not a boolean")

        jobs.append(
            {
                "id": job_id,
                "priority": priority,
                "needs": list(needs),
                "fails": fails,
            }
        )

    return jobs


def check_references_and_cycles(jobs):
    """Reject unknown needs and any dependency cycle (self-loop included)."""
    ids = set(job["id"] for job in jobs)
    for job in jobs:
        for need in job["needs"]:
            if need not in ids:
                raise SpecError("need names an unknown job id")

    by_id = dict((job["id"], job) for job in jobs)

    # Iterative DFS with colors: 0 = unvisited, 1 = on stack, 2 = done.
    color = dict((job["id"], 0) for job in jobs)
    for job in jobs:
        if color[job["id"]] != 0:
            continue
        stack = [(job["id"], iter(by_id[job["id"]]["needs"]))]
        color[job["id"]] = 1
        while stack:
            node, it = stack[-1]
            advanced = False
            for nxt in it:
                if color[nxt] == 1:
                    raise SpecError("dependency cycle")
                if color[nxt] == 0:
                    color[nxt] = 1
                    stack.append((nxt, iter(by_id[nxt]["needs"])))
                    advanced = True
                    break
            if not advanced:
                color[node] = 2
                stack.pop()


def schedule(jobs):
    """Run the deterministic scheduling loop.

    Returns (order, status) where order lists the ids actually executed in
    execution order, and status maps every job id to ok | failed | skipped.
    """
    status = {}
    order = []
    position = dict((job["id"], i) for i, job in enumerate(jobs))
    pending = list(jobs)

    while True:
        ready = []
        for job in pending:
            if job["id"] in status:
                continue
            if all(status.get(need) == "ok" for need in job["needs"]):
                ready.append(job)

        if not ready:
            break

        # Highest priority wins; ties broken by input order (FIFO).
        chosen = min(ready, key=lambda j: (-j["priority"], position[j["id"]]))
        status[chosen["id"]] = "failed" if chosen["fails"] else "ok"
        order.append(chosen["id"])

    # Anything never executed depends (transitively) on a failure.
    for job in jobs:
        if job["id"] not in status:
            status[job["id"]] = "skipped"

    return order, status


def main():
    data = sys.stdin.read()
    try:
        raw = json.loads(data)
        jobs = parse_jobs(raw)
        check_references_and_cycles(jobs)
    except (ValueError, SpecError):
        sys.stdout.write("ERROR\n")
        return 0

    order, status = schedule(jobs)
    sys.stdout.write(json.dumps({"order": order, "status": status}) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
