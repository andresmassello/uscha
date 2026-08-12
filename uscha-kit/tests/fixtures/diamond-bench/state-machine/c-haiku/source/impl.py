import json
import sys

# Read entire stdin
input_data = sys.stdin.read()

# Try to parse JSON
try:
    events = json.loads(input_data)
except (json.JSONDecodeError, ValueError):
    print("ERROR")
    sys.exit(0)

# Validate it's a JSON array
if not isinstance(events, list):
    print("ERROR")
    sys.exit(0)

# Process events from locked state
state = "locked"

for event in events:
    # Validate event is a string
    if not isinstance(event, str):
        print("ERROR")
        sys.exit(0)

    # Validate event is known
    if event not in ("coin", "push"):
        print("ERROR")
        sys.exit(0)

    # Transition
    if state == "locked":
        if event == "coin":
            state = "unlocked"
        # push on locked: stay locked
    elif state == "unlocked":
        if event == "push":
            state = "locked"
        # coin on unlocked: stay unlocked

# Print final state
print(state)
sys.exit(0)
