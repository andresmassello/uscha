import json
import sys


def main():
    try:
        # Read JSON array from stdin
        input_str = sys.stdin.read().strip()
        events = json.loads(input_str)

        # Validate input is a JSON array
        if not isinstance(events, list):
            print("ERROR")
            return

        # State machine transitions
        transitions = {
            ("locked", "coin"): "unlocked",
            ("locked", "push"): "locked",
            ("unlocked", "coin"): "unlocked",
            ("unlocked", "push"): "locked",
        }

        # Start in locked state
        state = "locked"

        # Fold events left to right
        for event in events:
            # Validate event is a string
            if not isinstance(event, str):
                print("ERROR")
                return

            # Validate event is known
            if event not in ("coin", "push"):
                print("ERROR")
                return

            # Transition to next state
            state = transitions[(state, event)]

        # Print final state
        print(state)

    except (json.JSONDecodeError, Exception):
        print("ERROR")


if __name__ == "__main__":
    main()
