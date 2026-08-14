"""Turnstile state machine.

Reads a JSON array of event strings from standard input, folds the events
left to right over a two-state turnstile, and prints the final state name.
Any input that is not a JSON array of known event strings prints ERROR.
"""

import json
import sys

START_STATE = "locked"

# Total transition table over the two states and the two events.
# INV-SM-TOTAL-01: every (state, event) pair has an explicit next state.
TRANSITIONS = {
    ("locked", "coin"): "unlocked",
    ("locked", "push"): "locked",
    ("unlocked", "coin"): "unlocked",
    ("unlocked", "push"): "locked",
}

EVENTS = ("coin", "push")


def fold(events):
    """Fold events from the start state; return None if any event is unknown."""
    state = START_STATE
    for event in events:
        # A bool is an int, not a str, so this rejects non-string elements.
        if not isinstance(event, str) or event not in EVENTS:
            return None
        state = TRANSITIONS[(state, event)]
    return state


def run(raw):
    try:
        parsed = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        return "ERROR"
    if not isinstance(parsed, list):
        return "ERROR"
    state = fold(parsed)
    if state is None:
        return "ERROR"
    return state


def main():
    try:
        raw = sys.stdin.read()
    except (OSError, UnicodeDecodeError):
        print("ERROR")
        return 0
    print(run(raw))
    return 0


if __name__ == "__main__":
    sys.exit(main())
