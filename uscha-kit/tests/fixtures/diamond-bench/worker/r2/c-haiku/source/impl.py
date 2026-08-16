import json
import sys
from typing import Dict, List, Set

def main():
    try:
        # Read input
        input_text = sys.stdin.read()
        data = json.loads(input_text)

        # Validate input structure
        if not isinstance(data, dict):
            print("ERROR")
            return

        if 'jobs' not in data:
            print("ERROR")
            return

        jobs = data['jobs']
        if not isinstance(jobs, list):
            print("ERROR")
            return

        # Parse and validate jobs
        job_map: Dict[str, dict] = {}

        for idx, job in enumerate(jobs):
            if not isinstance(job, dict):
                print("ERROR")
                return

            # Check required fields
            if 'id' not in job:
                print("ERROR")
                return

            if 'priority' not in job:
                print("ERROR")
                return

            job_id = job['id']

            if not isinstance(job_id, str):
                print("ERROR")
                return

            # Check for duplicate id
            if job_id in job_map:
                print("ERROR")
                return

            priority = job['priority']
            if not isinstance(priority, int):
                print("ERROR")
                return

            # Get needs (optional, default empty)
            needs = job.get('needs', [])
            if not isinstance(needs, list):
                print("ERROR")
                return

            # Validate that all items in needs are strings
            for need in needs:
                if not isinstance(need, str):
                    print("ERROR")
                    return

            needs_set = set(needs)

            # Get fails (optional, default false)
            fails = job.get('fails', False)
            if not isinstance(fails, bool):
                print("ERROR")
                return

            job_map[job_id] = {
                'priority': priority,
                'needs': needs_set,
                'fails': fails,
                'index': idx
            }

        # Check for unknown ids in needs
        for job_id, job_info in job_map.items():
            for need_id in job_info['needs']:
                if need_id not in job_map:
                    print("ERROR")
                    return

        # Check for cycles
        if has_cycle(job_map):
            print("ERROR")
            return

        # Schedule jobs
        order: List[str] = []
        status: Dict[str, str] = {job_id: None for job_id in job_map}
        executed: Set[str] = set()

        # Scheduling loop
        while len(executed) < len(job_map):
            # Find all ready jobs
            ready_jobs: List[tuple] = []

            for job_id, job_info in job_map.items():
                if job_id in executed:
                    continue

                # Check if all dependencies have status ok
                can_run = True
                for dep_id in job_info['needs']:
                    if status[dep_id] != 'ok':
                        can_run = False
                        break

                if can_run:
                    ready_jobs.append((job_info['index'], job_id))

            if not ready_jobs:
                # No more ready jobs; mark remaining as skipped
                for job_id in job_map:
                    if status[job_id] is None:
                        status[job_id] = 'skipped'
                break

            # Sort by priority (descending) then by input order (ascending)
            ready_jobs.sort(key=lambda x: (-job_map[x[1]]['priority'], x[0]))

            # Execute the first job
            next_job_id = ready_jobs[0][1]
            next_job_info = job_map[next_job_id]

            # Execute
            if next_job_info['fails']:
                status[next_job_id] = 'failed'
            else:
                status[next_job_id] = 'ok'

            order.append(next_job_id)
            executed.add(next_job_id)

        # Ensure all jobs have a status
        for job_id in job_map:
            if status[job_id] is None:
                status[job_id] = 'skipped'

        result = {
            'order': order,
            'status': status
        }

        print(json.dumps(result))

    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        print("ERROR")

def has_cycle(job_map: Dict[str, dict]) -> bool:
    """Check for cycles in the dependency graph using DFS."""
    visited: Set[str] = set()
    rec_stack: Set[str] = set()

    def dfs(node: str) -> bool:
        visited.add(node)
        rec_stack.add(node)

        for neighbor in job_map[node]['needs']:
            if neighbor not in visited:
                if dfs(neighbor):
                    return True
            elif neighbor in rec_stack:
                return True

        rec_stack.remove(node)
        return False

    for job_id in job_map:
        if job_id not in visited:
            if dfs(job_id):
                return True

    return False

if __name__ == '__main__':
    main()
