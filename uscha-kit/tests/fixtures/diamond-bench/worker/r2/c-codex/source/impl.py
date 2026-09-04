import json
import sys


ERROR_TEXT = "ERROR"


def is_plain_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def parse_and_validate(raw):
    try:
        data = json.loads(raw)
    except Exception:
        raise ValueError("invalid json")

    if not isinstance(data, dict):
        raise ValueError("root must be object")

    jobs_value = data.get("jobs")
    if not isinstance(jobs_value, list):
        raise ValueError("jobs must be array")

    jobs = []
    seen = set()

    for index, item in enumerate(jobs_value):
        if not isinstance(item, dict):
            raise ValueError("job must be object")

        job_id = item.get("id")
        priority = item.get("priority")
        needs = item.get("needs", [])
        fails = item.get("fails", False)

        if not isinstance(job_id, str):
            raise ValueError("id must be string")
        if not is_plain_int(priority):
            raise ValueError("priority must be int")
        if not isinstance(needs, list) or any(not isinstance(dep, str) for dep in needs):
            raise ValueError("needs must be string array")
        if not isinstance(fails, bool):
            raise ValueError("fails must be bool")
        if job_id in seen:
            raise ValueError("duplicate id")

        seen.add(job_id)
        jobs.append({
            "id": job_id,
            "priority": priority,
            "needs": list(needs),
            "fails": fails,
            "index": index,
        })

    known_ids = set(seen)
    for job in jobs:
        for dep in job["needs"]:
            if dep not in known_ids:
                raise ValueError("unknown dependency")

    reject_cycles(jobs)
    return jobs


def reject_cycles(jobs):
    by_id = {job["id"]: job for job in jobs}
    visiting = set()
    visited = set()

    def visit(job_id):
        if job_id in visited:
            return
        if job_id in visiting:
            raise ValueError("dependency cycle")

        visiting.add(job_id)
        for dep in by_id[job_id]["needs"]:
            visit(dep)
        visiting.remove(job_id)
        visited.add(job_id)

    for job in jobs:
        visit(job["id"])


def schedule(jobs):
    statuses = {job["id"]: None for job in jobs}
    order = []

    while True:
        ready = []
        for job in jobs:
            job_id = job["id"]
            if statuses[job_id] is not None:
                continue
            if all(statuses[dep] == "ok" for dep in job["needs"]):
                ready.append(job)

        if not ready:
            break

        chosen = min(ready, key=lambda job: (-job["priority"], job["index"]))
        chosen_id = chosen["id"]
        statuses[chosen_id] = "failed" if chosen["fails"] else "ok"
        order.append(chosen_id)

    for job in jobs:
        job_id = job["id"]
        if statuses[job_id] is None:
            statuses[job_id] = "skipped"

    return {"order": order, "status": statuses}


def main():
    try:
        raw = sys.stdin.read()
        jobs = parse_and_validate(raw)
        result = schedule(jobs)
        sys.stdout.write(json.dumps(result, separators=(",", ":")))
    except Exception:
        sys.stdout.write(ERROR_TEXT)


if __name__ == "__main__":
    main()
