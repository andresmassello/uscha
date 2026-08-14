import json
import sys

def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        print("ERROR")
        return

    if not isinstance(data, list):
        print("ERROR")
        return

    state = "locked"

    for event in data:
        if not isinstance(event, str):
            print("ERROR")
            return

        if event not in ["coin", "push"]:
            print("ERROR")
            return

        if state == "locked":
            if event == "coin":
                state = "unlocked"
        elif state == "unlocked":
            if event == "push":
                state = "locked"

    print(state)

if __name__ == "__main__":
    main()
