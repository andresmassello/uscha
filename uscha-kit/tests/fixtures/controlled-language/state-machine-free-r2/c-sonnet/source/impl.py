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
    for event in events:
        if not isinstance(event, str):
            print("ERROR")
            return
        if event == "coin":
            state = "unlocked"
        elif event == "push":
            state = "locked"
        else:
            print("ERROR")
            return

    print(state)


if __name__ == "__main__":
    main()
