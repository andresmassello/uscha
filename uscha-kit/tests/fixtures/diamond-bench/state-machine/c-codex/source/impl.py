import json
import sys


TRANSITIONS = {
    ("locked", "coin"): "unlocked",
    ("locked", "push"): "locked",
    ("unlocked", "coin"): "unlocked",
    ("unlocked", "push"): "locked",
}


def result_for_input(text):
    try:
        events = json.loads(text)
    except Exception:
        return "ERROR"

    if not isinstance(events, list):
        return "ERROR"

    state = "locked"
    for event in events:
        if not isinstance(event, str):
            return "ERROR"
        next_state = TRANSITIONS.get((state, event))
        if next_state is None:
            return "ERROR"
        state = next_state

    return state


def main():
    print(result_for_input(sys.stdin.read()))


if __name__ == "__main__":
    main()
