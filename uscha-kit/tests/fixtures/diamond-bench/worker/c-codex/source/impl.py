import json
import sys


ERROR_TEXT = "ERROR"


def is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def parse_input(text):
    try:
        data = json.loads(text)
    except Exception:
        return None

    if not isinstance(data, dict):
        return None

    jobs = data.get("jobs")
    if not isinstance(jobs, list):
        return None

    seen = set()
    parsed = []

    for index, job in enumerate(jobs):
        if not isinstance(job, dict):
            return None

        job_id = job.get("id")
        priority = job.get("priority")
        needs = job.get("needs", [])
        fails = job.get("fails", False)

        if not isinstance(job_id, str):
            return None
        if not is_int(priority):
            return None
        if not isinstance(needs, list):
            return None
        if not all(isinstance(need, str) for need in needs):
            return None
        if not isinstance(fails, bool):
            return None
        if job_id in seen:
            return None

        seen.add(job_id)
        parsed.append({
            "id": job_id,
            "priority": priority,
            "needs": list(needs),
            "fails": fails,
            "index": index,
        })

    known_ids = seen
    for job in parsed:
        for need in job["needs"]:
            if need not in known_ids:
                return None

    return parsed


def has_cycle(jobs):
    by_id = {job["id"]: job for job in jobs}
    visiting = set()
    visited = set()

    def visit(job_id):
        if job_id in visiting:
            return True
        if job_id in visited:
            return False

        visiting.add(job_id)
        for need in by_id[job_id]["needs"]:
            if visit(need):
                return True
        visiting.remove(job_id)
        visited.add(job_id)
        return False

    for job in jobs:
        if visit(job["id"]):
            return True
    return False


def schedule(jobs):
    status = {}
    executed = set()
    order = []

    while True:
        ready = []
        for job in jobs:
            job_id = job["id"]
            if job_id in executed:
                continue
            if all(status.get(need) == "ok" for need in job["needs"]):
                ready.append(job)

        if not ready:
            break

        ready.sort(key=lambda job: (-job["priority"], job["index"]))
        job = ready[0]
        job_id = job["id"]
        status[job_id] = "failed" if job["fails"] else "ok"
        executed.add(job_id)
        order.append(job_id)

    for job in jobs:
        job_id = job["id"]
        if job_id not in status:
            status[job_id] = "skipped"

    ordered_status = {job["id"]: status[job["id"]] for job in jobs}
    return {"order": order, "status": ordered_status}


def main():
    try:
        jobs = parse_input(sys.stdin.read())
        if jobs is None or has_cycle(jobs):
            print(ERROR_TEXT)
            return
        print(json.dumps(schedule(jobs), separators=(",", ":")))
    except Exception:
        print(ERROR_TEXT)


if __name__ == "__main__":
    main()
