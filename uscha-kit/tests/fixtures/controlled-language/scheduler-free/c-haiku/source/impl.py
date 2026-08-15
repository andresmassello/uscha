import json
import sys


def main():
    try:
        line = sys.stdin.read()
        jobs_input = json.loads(line)

        if not isinstance(jobs_input, list):
            print("ERROR")
            return

        jobs = {}
        seen_ids = set()

        for job_data in jobs_input:
            if not isinstance(job_data, dict):
                print("ERROR")
                return

            if 'id' not in job_data or 'priority' not in job_data or 'arrival' not in job_data or 'duration' not in job_data:
                print("ERROR")
                return

            id_val = job_data['id']
            priority = job_data['priority']
            arrival = job_data['arrival']
            duration = job_data['duration']
            deadline = job_data.get('deadline', None)

            for val in [id_val, priority, arrival, duration]:
                if not isinstance(val, int) or isinstance(val, bool):
                    print("ERROR")
                    return

            if deadline is not None and (not isinstance(deadline, int) or isinstance(deadline, bool)):
                print("ERROR")
                return

            if arrival < 0 or duration < 0:
                print("ERROR")
                return

            if id_val in seen_ids:
                print("ERROR")
                return

            seen_ids.add(id_val)
            jobs[id_val] = {
                'priority': priority,
                'arrival': arrival,
                'duration': duration,
                'deadline': deadline,
                'remaining': duration,
                'started': False
            }

        events = []
        completed = []
        missed = []
        ready = set()
        running = None

        if not jobs:
            result = {
                "events": [],
                "completed": [],
                "missed": []
            }
            print(json.dumps(result))
            return

        tick = 0
        while True:
            # Step 1: Arrivals
            arrivals = sorted([jid for jid in jobs if jobs[jid]['arrival'] == tick and jid not in completed and jid not in missed])
            for jid in arrivals:
                ready.add(jid)
                events.append([tick, "arrive", jid])

            # Step 2: Deadline check
            check_set = ready.copy()
            if running:
                check_set.add(running)

            to_miss = []
            for jid in check_set:
                job = jobs[jid]
                if job['deadline'] is not None and job['deadline'] < tick:
                    to_miss.append(jid)

            to_miss.sort()
            for jid in to_miss:
                ready.discard(jid)
                if running == jid:
                    running = None
                events.append([tick, "missed", jid])
                missed.append(jid)

            # Step 3: Selection
            candidates = ready.copy()
            if running:
                candidates.add(running)

            if candidates:
                best = min(candidates, key=lambda jid: (-jobs[jid]['priority'], jobs[jid]['arrival'], jid))

                if best == running:
                    pass
                else:
                    if running and running in candidates:
                        events.append([tick, "preempt", running])
                        ready.add(running)
                    ready.discard(best)
                    if jobs[best]['started']:
                        events.append([tick, "resume", best])
                    else:
                        events.append([tick, "start", best])
                        jobs[best]['started'] = True
                    running = best
            else:
                events.append([tick, "idle", None])
                running = None

            # Step 4: Execution
            if running:
                jobs[running]['remaining'] -= 1
                if jobs[running]['remaining'] == 0:
                    events.append([tick, "complete", running])
                    completed.append(running)
                    running = None

            # Check termination
            remaining_count = sum(1 for jid in jobs if jid not in completed and jid not in missed)
            if remaining_count == 0:
                break

            tick += 1

        result = {
            "events": events,
            "completed": completed,
            "missed": missed
        }
        print(json.dumps(result))

    except (json.JSONDecodeError, ValueError, KeyError, AttributeError):
        print("ERROR")
    except:
        print("ERROR")


if __name__ == "__main__":
    main()
