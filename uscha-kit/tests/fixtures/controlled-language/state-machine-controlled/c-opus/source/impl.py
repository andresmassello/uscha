"""Turnstile state machine.

Reads one JSON value from standard input, folds the event array left to right
starting in the state `locked`, and prints one line: the final state name, or
exactly `ERROR` when the input is not a JSON array of known event strings.

Exits with code 0 in every case.
"""

import json
import sys

LOCKED = "locked"
UNLOCKED = "unlocked"
START_STATE = LOCKED

COIN = "coin"
PUSH = "push"

# INV-SM-TOTAL-01: every (state, event) pair has exactly one next state.
# The table below is the whole machine; a pair absent from it is a defect,
# and an event outside the known set is rejected before lookup.
TRANSITIONS = {
    (LOCKED, COIN): UNLOCKED,
    (UNLOCKED, COIN): UNLOCKED,
    (UNLOCKED, PUSH): LOCKED,
    (LOCKED, PUSH): LOCKED,
}

ERROR = "ERROR"


def fold(events):
    """Fold the events from left to right. Returns the final state name.

    Raises ValueError when an element is not a string or is an unknown event.
    """
    state = START_STATE
    for element in events:
        # bool is a subclass of int, not str, so no extra guard is needed here;
        # anything that is not exactly a str is not an event.
        if not isinstance(element, str):
            raise ValueError("element is not a string")
        key = (state, element)
        if key not in TRANSITIONS:
            raise ValueError("unknown event")
        state = TRANSITIONS[key]
    return state


def run(raw_input_text):
    """Return the single output line for the given raw standard-input text."""
    try:
        value = json.loads(raw_input_text)
    except Exception:
        return ERROR
    # A JSON object, a bare number, a string, a bool or null is not an array.
    if not isinstance(value, list):
        return ERROR
    try:
        return fold(value)
    except ValueError:
        return ERROR


def main():
    try:
        raw = sys.stdin.read()
    except Exception:
        raw = ""
    sys.stdout.write(run(raw) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
