import json
import sys


def main():
    raw = sys.stdin.read()

    try:
        events = json.loads(raw)
    except ValueError:
        print("ERROR")
        return

    if not isinstance(events, list):
        print("ERROR")
        return

    state = "locked"

    transitions = {
        ("locked", "coin"): "unlocked",
        ("locked", "push"): "locked",
        ("unlocked", "coin"): "unlocked",
        ("unlocked", "push"): "locked",
    }

    for event in events:
        if not isinstance(event, str):
            print("ERROR")
            return
        key = (state, event)
        if key not in transitions:
            print("ERROR")
            return
        state = transitions[key]

    print(state)


if __name__ == "__main__":
    main()
