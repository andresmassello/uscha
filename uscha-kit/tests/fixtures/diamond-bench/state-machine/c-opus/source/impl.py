import sys
import json


def main():
    raw = sys.stdin.read()
    try:
        events = json.loads(raw)
    except (ValueError, TypeError):
        print("ERROR")
        return

    if not isinstance(events, list):
        print("ERROR")
        return

    transitions = {
        ("locked", "coin"): "unlocked",
        ("locked", "push"): "locked",
        ("unlocked", "coin"): "unlocked",
        ("unlocked", "push"): "locked",
    }
    known_events = {"coin", "push"}

    state = "locked"
    for event in events:
        # A non-string element or an unknown event string is rejected.
        # bool is a subclass of int, not str, so it is caught by the isinstance check.
        if not isinstance(event, str) or event not in known_events:
            print("ERROR")
            return
        state = transitions[(state, event)]

    print(state)


if __name__ == "__main__":
    main()
