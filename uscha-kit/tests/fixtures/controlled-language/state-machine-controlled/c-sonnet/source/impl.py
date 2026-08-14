import json
import sys


def main():
    raw = sys.stdin.read()

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        print("ERROR")
        return

    if not isinstance(data, list):
        print("ERROR")
        return

    state = "locked"

    for element in data:
        if not isinstance(element, str):
            print("ERROR")
            return
        if element == "coin":
            if state == "locked":
                state = "unlocked"
            else:
                state = "unlocked"
        elif element == "push":
            if state == "unlocked":
                state = "locked"
            else:
                state = "locked"
        else:
            print("ERROR")
            return

    print(state)


if __name__ == "__main__":
    main()
