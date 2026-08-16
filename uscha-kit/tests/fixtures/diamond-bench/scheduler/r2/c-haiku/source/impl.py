import sys
import json

def main():
    try:
        line = sys.stdin.read()
        jobs_input = json.loads(line)

        if not isinstance(jobs_input, list):
            print("ERROR")
            return

        jobs = {}
        for job_data in jobs_input:
            if not isinstance(job_data, dict):
                print("ERROR")
                return

            required = {'id', 'priority', 'arrival', 'duration'}
            if not required.issubset(job_data.keys()):
                print("ERROR")
                return

            id_val = job_data['id']
            priority = job_data['priority']
            arrival = job_data['arrival']
            duration = job_data['duration']

            # Validate types (reject booleans since JSON bool is not int)
            if not isinstance(id_val, int) or isinstance(id_val, bool):
                print("ERROR")
                return
            if not isinstance(priority, int) or isinstance(priority, bool):
                print("ERROR")
                return
            if not isinstance(arrival, int) or isinstance(arrival, bool):
                print("ERROR")
                return
            if not isinstance(duration, int) or isinstance(duration, bool):
                print("ERROR")
                return

            if arrival < 0 or duration < 0:
                print("ERROR")
                return

            if id_val in jobs:
                print("ERROR")
                return

            deadline = None
            if 'deadline' in job_data:
                deadline = job_data['deadline']
                if not isinstance(deadline, int) or isinstance(deadline, bool):
                    print("ERROR")
                    return

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

        if not jobs:
            print(json.dumps({"events": [], "completed": [], "missed": []}))
            return

        ready = set()
        running = None
        current_tick = 0

        while True:
            # Step 1: Arrivals
            arriving = sorted([id_val for id_val, job in jobs.items() if job['arrival'] == current_tick])
            for id_val in arriving:
                ready.add(id_val)
                events.append([current_tick, "arrive", id_val])

            # Step 2: Deadline check
            to_check = set(ready)
            if running is not None:
                to_check.add(running)

            to_miss = []
            for id_val in sorted(to_check):
                job = jobs[id_val]
                if job['deadline'] is not None and job['deadline'] <= current_tick:
                    # Job completes at exactly deadline tick if it's running with remaining == 1
                    if id_val == running and job['remaining'] == 1:
                        pass
                    else:
                        to_miss.append(id_val)

            for id_val in to_miss:
                ready.discard(id_val)
                if running == id_val:
                    running = None
                del jobs[id_val]
                missed.append(id_val)
                events.append([current_tick, "missed", id_val])

            # Step 3: Selection
            candidates = list(ready)
            if running is not None:
                candidates.append(running)

            if candidates:
                def sort_key(id_val):
                    job = jobs[id_val]
                    return (-job['priority'], job['arrival'], id_val)

                selected = min(candidates, key=sort_key)

                if running != selected:
                    if running is not None:
                        ready.add(running)
                        events.append([current_tick, "preempt", running])

                    ready.discard(selected)
                    if jobs[selected]['started']:
                        events.append([current_tick, "resume", selected])
                    else:
                        events.append([current_tick, "start", selected])
                        jobs[selected]['started'] = True
                    running = selected
                else:
                    ready.discard(selected)
            else:
                if jobs:
                    events.append([current_tick, "idle", None])
                running = None

            # Step 4: Execution
            if running is not None:
                jobs[running]['remaining'] -= 1
                if jobs[running]['remaining'] == 0:
                    events.append([current_tick, "complete", running])
                    completed.append(running)
                    del jobs[running]
                    running = None

            if not jobs and not ready and running is None:
                break

            current_tick += 1

            if current_tick > 1000000:
                break

        result = {
            "events": events,
            "completed": completed,
            "missed": missed
        }
        print(json.dumps(result))

    except (json.JSONDecodeError, ValueError, KeyError, TypeError):
        print("ERROR")

if __name__ == "__main__":
    main()
