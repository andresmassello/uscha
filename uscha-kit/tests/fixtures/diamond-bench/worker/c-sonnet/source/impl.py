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

    jobs = data.get("jobs")
    if not isinstance(jobs, list):
        fail()
        return

    ids = []
    priority = {}
    needs_map = {}
    fails_map = {}
    seen = set()

    for job in jobs:
        if not isinstance(job, dict):
            fail()
            return

        jid = job.get("id")
        if not isinstance(jid, str):
            fail()
            return
        if jid in seen:
            fail()
            return
        seen.add(jid)

        prio = job.get("priority")
        if not isinstance(prio, int) or isinstance(prio, bool):
            fail()
            return

        needs = job.get("needs", [])
        if needs is None:
            needs = []
        if not isinstance(needs, list) or not all(isinstance(n, str) for n in needs):
            fail()
            return

        fails = job.get("fails", False)
        if not isinstance(fails, bool):
            fail()
            return

        ids.append(jid)
        priority[jid] = prio
        needs_map[jid] = needs
        fails_map[jid] = fails

    id_set = set(ids)
    for jid in ids:
        for n in needs_map[jid]:
            if n not in id_set:
                fail()
                return

    # Cycle detection over the "needs" (dependency) graph.
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {jid: WHITE for jid in ids}

    def has_cycle_from(start):
        stack = [(start, iter(needs_map[start]))]
        color[start] = GRAY
        while stack:
            node, it = stack[-1]
            advanced = False
            for n in it:
                if color[n] == GRAY:
                    return True
                if color[n] == WHITE:
                    color[n] = GRAY
                    stack.append((n, iter(needs_map[n])))
                    advanced = True
                    break
            if not advanced:
                color[node] = BLACK
                stack.pop()
        return False

    for jid in ids:
        if color[jid] == WHITE:
            if has_cycle_from(jid):
                fail()
                return

    index = {jid: i for i, jid in enumerate(ids)}
    status = {}
    order = []
    remaining = set(ids)

    while remaining:
        # Propagate "skipped" status to every job that (transitively)
        # depends on a failed or skipped job.
        changed = True
        while changed:
            changed = False
            for jid in list(remaining):
                for n in needs_map[jid]:
                    if status.get(n) in ("failed", "skipped"):
                        status[jid] = "skipped"
                        remaining.discard(jid)
                        changed = True
                        break

        if not remaining:
            break

        ready = [
            jid for jid in remaining
            if all(status.get(n) == "ok" for n in needs_map[jid])
        ]

        if not ready:
            # Unreachable when validation above passed (no cycles, no
            # unknown needs) -- safety guard against an infinite loop.
            break

        ready.sort(key=lambda j: (-priority[j], index[j]))
        chosen = ready[0]
        remaining.discard(chosen)
        order.append(chosen)
        status[chosen] = "failed" if fails_map[chosen] else "ok"

    result = {"order": order, "status": status}
    print(json.dumps(result))
    sys.exit(0)


main()
