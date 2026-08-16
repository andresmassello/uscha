"""Turnstile state machine.

Reads one JSON value from standard input: an array of event strings. Folds the
events left to right over the turnstile starting from the state `locked` and
prints the resulting state name. Any input that is not a JSON array of known
event strings prints exactly `ERROR`.
"""

import json
import sys

START_STATE = "locked"

# INV-SM-TOTAL-01: the transition table is total over (state, event) for the
# known event set. Every pair below has an explicit next state; an event outside
# this set is rejected (ERROR), never left undefined and never silently ignored.
TRANSITIONS = {
    ("locked", "coin"): "unlocked",
    ("locked", "push"): "locked",
    ("unlocked", "coin"): "unlocked",
    ("unlocked", "push"): "locked",
}


def final_state(events):
    """Fold events left to right from the start state.

    Returns the final state name, or None if any element is not a known event.
    """
    state = START_STATE
    for event in events:
        # A bool is an int, not a str, so the isinstance check is enough here:
        # only genuine strings can name an event.
        if not isinstance(event, str):
            return None
        nxt = TRANSITIONS.get((state, event))
        if nxt is None:
            return None
        state = nxt
    return state


def run(raw):
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        return "ERROR"
    if not isinstance(value, list):
        return "ERROR"
    state = final_state(value)
    return "ERROR" if state is None else state


def main():
    print(run(sys.stdin.read()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
