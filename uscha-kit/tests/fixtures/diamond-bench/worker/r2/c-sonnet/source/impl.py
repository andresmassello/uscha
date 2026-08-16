import sys
import json


def fail():
    print("ERROR")
    sys.exit(0)


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except Exception:
        fail()
        return

    if not isinstance(data, dict):
        fail()
        return
    if "jobs" not in data or not isinstance(data["jobs"], list):
        fail()
        return

    jobs_raw = data["jobs"]

    ids = []
    priority = {}
    needs = {}
    fails = {}
    seen = set()

    for job in jobs_raw:
        if not isinstance(job, dict):
            fail()
            return
        if "id" not in job or not isinstance(job["id"], str):
            fail()
            return
        if "priority" not in job:
            fail()
            return
        pr = job["priority"]
        if isinstance(pr, bool) or not isinstance(pr, int):
            fail()
            return

        jid = job["id"]
        if jid in seen:
            fail()
            return
        seen.add(jid)

        job_needs = job.get("needs", [])
        if job_needs is None:
            job_needs = []
        if not isinstance(job_needs, list):
            fail()
            return
        for n in job_needs:
            if not isinstance(n, str):
                fail()
                return

        job_fails = job.get("fails", False)
        if not isinstance(job_fails, bool):
            fail()
            return

        ids.append(jid)
        priority[jid] = pr
        needs[jid] = job_needs
        fails[jid] = job_fails

    known = set(ids)
    for jid in ids:
        for n in needs[jid]:
            if n not in known:
                fail()
                return

    # Cycle detection via DFS (needs = dependency edges).
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {jid: WHITE for jid in ids}

    def has_cycle(start):
        stack = [(start, iter(needs[start]))]
        color[start] = GRAY
        while stack:
            node, it = stack[-1]
            advanced = False
            for nxt in it:
                if color[nxt] == GRAY:
                    return True
                if color[nxt] == WHITE:
                    color[nxt] = GRAY
                    stack.append((nxt, iter(needs[nxt])))
                    advanced = True
                    break
            if not advanced:
                color[node] = BLACK
                stack.pop()
        return False

    for jid in ids:
        if color[jid] == WHITE:
            if has_cycle(jid):
                fail()
                return

    status = {}
    undecided = set(ids)
    order = []

    while True:
        ready = [
            jid for jid in ids
            if jid in undecided and all(status.get(n) == "ok" for n in needs[jid])
        ]
        if ready:
            chosen = max(ready, key=lambda jid: priority[jid])
            if fails[chosen]:
                status[chosen] = "failed"
            else:
                status[chosen] = "ok"
            order.append(chosen)
            undecided.discard(chosen)
            continue

        newly_skipped = [
            jid for jid in undecided
            if any(status.get(n) in ("failed", "skipped") for n in needs[jid])
        ]
        if newly_skipped:
            for jid in newly_skipped:
                status[jid] = "skipped"
                undecided.discard(jid)
            continue

        break

    result = {"order": order, "status": status}
    print(json.dumps(result))


if __name__ == "__main__":
    main()
