import json
import sys
from typing import List, Dict, Optional, Tuple, Any


def validate_input(data: Any) -> Tuple[bool, Optional[List[Dict]]]:
    """Validate input and return (is_valid, jobs_or_none)"""
    # Must be a list
    if not isinstance(data, list):
        return False, None

    # Empty list is valid
    if len(data) == 0:
        return True, []

    jobs = []
    seen_ids = set()

    for job in data:
        # Must be a dict
        if not isinstance(job, dict):
            return False, None

        # Check required fields exist and are integers (not booleans)
        required_fields = ['id', 'priority', 'arrival', 'duration']
        for field in required_fields:
            if field not in job:
                return False, None
            # Boolean is a subclass of int in Python, so we need explicit check
            if isinstance(job[field], bool) or not isinstance(job[field], int):
                return False, None

        # Check optional deadline
        if 'deadline' in job:
            if isinstance(job['deadline'], bool) or not isinstance(job['deadline'], int):
                return False, None

        # Check arrival and duration are non-negative
        if job['arrival'] < 0 or job['duration'] < 0:
            return False, None

        # Check id is unique
        job_id = job['id']
        if job_id in seen_ids:
            return False, None
        seen_ids.add(job_id)

        jobs.append(job)

    return True, jobs


def run_scheduler(jobs: List[Dict]) -> Dict:
    """Run the scheduler and return the result dict"""
    if not jobs:
        return {"events": [], "completed": [], "missed": []}

    # Initialize job states
    job_data = {}
    for job in jobs:
        job_data[job['id']] = {
            'priority': job['priority'],
            'arrival': job['arrival'],
            'duration': job['duration'],
            'deadline': job.get('deadline'),
            'remaining': job['duration'],
            'has_run': False,
        }

    events = []
    completed = []
    missed = []

    current_tick = 0
    running_job_id = None
    active_jobs = set()  # Jobs that have arrived but not completed/missed

    while True:
        # Step 1: Handle arrivals
        arrived_ids = []
        for job_id, data in job_data.items():
            if job_id not in active_jobs and data['arrival'] == current_tick:
                active_jobs.add(job_id)
                arrived_ids.append(job_id)

        arrived_ids.sort()
        for job_id in arrived_ids:
            events.append([current_tick, "arrive", job_id])

        # Step 2: Check deadlines
        missed_ids = []
        for job_id in list(active_jobs):
            data = job_data[job_id]
            if data['deadline'] is not None:
                if data['deadline'] <= current_tick:
                    missed_ids.append(job_id)

        missed_ids.sort()
        for job_id in missed_ids:
            events.append([current_tick, "missed", job_id])
            missed.append(job_id)
            active_jobs.remove(job_id)

        # Step 3: Selection
        if active_jobs:
            # Select job with highest priority, tiebreak by earliest arrival, then lowest id
            def sort_key(job_id):
                data = job_data[job_id]
                return (-data['priority'], data['arrival'], job_id)

            ready_list = sorted(active_jobs, key=sort_key)
            selected_job_id = ready_list[0]

            # Check if we need to preempt
            if running_job_id is not None and running_job_id != selected_job_id:
                if running_job_id in active_jobs:  # Still active
                    events.append([current_tick, "preempt", running_job_id])

            # Check if we need to emit start or resume
            data = job_data[selected_job_id]
            if running_job_id != selected_job_id:
                if not data['has_run']:
                    events.append([current_tick, "start", selected_job_id])
                else:
                    events.append([current_tick, "resume", selected_job_id])

            running_job_id = selected_job_id

            # Step 4: Execution
            data = job_data[selected_job_id]
            data['has_run'] = True

            if data['remaining'] > 0:
                data['remaining'] -= 1

            if data['remaining'] == 0:
                events.append([current_tick, "complete", selected_job_id])
                completed.append(selected_job_id)
                active_jobs.remove(selected_job_id)
                running_job_id = None
        else:
            # No active jobs
            # Check if there are pending jobs
            pending_jobs = [job_id for job_id in job_data if job_data[job_id]['arrival'] > current_tick]
            if not pending_jobs:
                # No more jobs to process
                break
            else:
                # Emit idle
                events.append([current_tick, "idle", None])
                running_job_id = None

        current_tick += 1

    return {
        "events": events,
        "completed": completed,
        "missed": missed
    }


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        print("ERROR")
        sys.exit(0)

    is_valid, jobs = validate_input(data)

    if not is_valid:
        print("ERROR")
        sys.exit(0)

    result = run_scheduler(jobs)
    print(json.dumps(result))
    sys.exit(0)


if __name__ == '__main__':
    main()
