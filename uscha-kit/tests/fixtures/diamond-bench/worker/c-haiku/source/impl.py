import sys
import json

def main():
    try:
        # Read input
        stdin_data = sys.stdin.read()
        data = json.loads(stdin_data)

        # Validate structure
        if not isinstance(data, dict) or 'jobs' not in data:
            print("ERROR")
            return

        if not isinstance(data['jobs'], list):
            print("ERROR")
            return

        jobs = data['jobs']

        # Parse and validate jobs
        job_dict = {}

        for idx, job in enumerate(jobs):
            if not isinstance(job, dict) or 'id' not in job or 'priority' not in job:
                print("ERROR")
                return

            job_id = job['id']
            priority = job['priority']

            # Check for duplicate id
            if job_id in job_dict:
                print("ERROR")
                return

            # Validate types
            if not isinstance(job_id, str) or not isinstance(priority, int):
                print("ERROR")
                return

            needs = job.get('needs', [])
            if not isinstance(needs, list):
                print("ERROR")
                return

            fails = job.get('fails', False)
            if not isinstance(fails, bool):
                print("ERROR")
                return

            job_dict[job_id] = {
                'priority': priority,
                'needs': needs,
                'fails': fails,
                'index': idx
            }

        # Validate that all needs refer to existing jobs
        for job_id, job in job_dict.items():
            for need_id in job['needs']:
                if need_id not in job_dict:
                    print("ERROR")
                    return

        # Check for cycles using DFS
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {job_id: WHITE for job_id in job_dict}

        def has_cycle_dfs(node):
            if color[node] == GRAY:
                return True
            if color[node] == BLACK:
                return False

            color[node] = GRAY
            for neighbor in job_dict[node]['needs']:
                if has_cycle_dfs(neighbor):
                    return True
            color[node] = BLACK
            return False

        for job_id in job_dict:
            if color[job_id] == WHITE:
                if has_cycle_dfs(job_id):
                    print("ERROR")
                    return

        # Schedule jobs
        status = {job_id: None for job_id in job_dict}
        executed = []

        def mark_dependents_skipped(skipped_job_id):
            for other_id, other_job in job_dict.items():
                if status[other_id] is None and skipped_job_id in other_job['needs']:
                    status[other_id] = 'skipped'
                    mark_dependents_skipped(other_id)

        # Scheduling loop
        while True:
            ready = []
            for job_id, job in job_dict.items():
                if status[job_id] is not None:
                    continue

                all_ok = True
                for need_id in job['needs']:
                    if status[need_id] != 'ok':
                        all_ok = False
                        break

                if all_ok:
                    ready.append(job_id)

            if not ready:
                break

            ready.sort(key=lambda jid: (-job_dict[jid]['priority'], job_dict[jid]['index']))

            job_id = ready[0]
            job = job_dict[job_id]

            if job['fails']:
                status[job_id] = 'failed'
                mark_dependents_skipped(job_id)
            else:
                status[job_id] = 'ok'

            executed.append(job_id)

        # Mark remaining jobs as skipped
        for job_id in job_dict:
            if status[job_id] is None:
                status[job_id] = 'skipped'

        # Output result
        result = {
            'order': executed,
            'status': status
        }
        print(json.dumps(result))

    except (json.JSONDecodeError, TypeError, KeyError, ValueError):
        print("ERROR")

if __name__ == '__main__':
    main()
