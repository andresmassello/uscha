import json
import sys


TRANSITIONS = {
    ("locked", "coin"): "unlocked",
    ("locked", "push"): "locked",
    ("unlocked", "coin"): "unlocked",
    ("unlocked", "push"): "locked",
}


def main():
    try:
        events = json.loads(sys.stdin.read())
    except Exception:
        print("ERROR")
        return

    if not isinstance(events, list):
        print("ERROR")
        return

    state = "locked"
    for event in events:
        if not isinstance(event, str) or event not in ("coin", "push"):
            print("ERROR")
            return
        state = TRANSITIONS[(state, event)]

    print(state)


if __name__ == "__main__":
    main()
