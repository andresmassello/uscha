import json
import sys

def main():
    try:
        # Read from stdin
        input_data = sys.stdin.read().strip()
        events = json.loads(input_data)

        # Check if it's a list
        if not isinstance(events, list):
            print("ERROR")
            return

        # Start state
        state = "locked"

        # Process each event
        for event in events:
            # Check if event is a string
            if not isinstance(event, str):
                print("ERROR")
                return

            # Apply state transition based on event
            if event == "coin":
                if state == "locked":
                    state = "unlocked"
                # else stays unlocked
            elif event == "push":
                if state == "unlocked":
                    state = "locked"
                # else stays locked
            else:
                # Unknown event
                print("ERROR")
                return

        # Print the final state
        print(state)
    except (json.JSONDecodeError, ValueError):
        # Invalid JSON
        print("ERROR")

if __name__ == "__main__":
    main()
