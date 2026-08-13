#!/usr/bin/env python3
"""Form view-model: initial model + event sequence -> final view.

Reads a JSON object from stdin:
    {"model": {"fields": [{"name": str, "value": str|bool}, ...]},
     "events": [event, ...]}

Prints the final view as JSON:
    {"fields": {name: value, ...}, "submitted": bool, "errors": [name, ...]}

Malformed input prints exactly ERROR. Always exits 0.
"""

import json
import sys


class Malformed(Exception):
    """Raised for any shape error, unknown field, or type mismatch."""


def _is_str(v):
    return isinstance(v, str)


def _is_bool(v):
    return isinstance(v, bool)


def parse_model(model):
    """Return (order, initial) from a validated model object.

    order preserves declaration order; initial maps name -> value.
    Duplicate names are malformed (AC-UI-06).
    """
    if not isinstance(model, dict):
        raise Malformed()
    if "fields" not in model:
        raise Malformed()
    fields = model["fields"]
    if not isinstance(fields, list):
        raise Malformed()

    order = []
    initial = {}
    for field in fields:
        if not isinstance(field, dict):
            raise Malformed()
        if "name" not in field or "value" not in field:
            raise Malformed()
        name = field["name"]
        value = field["value"]
        if not _is_str(name):
            raise Malformed()
        # bool is checked before str; a value must be exactly one of the two.
        if not (_is_bool(value) or _is_str(value)):
            raise Malformed()
        if name in initial:
            raise Malformed()  # duplicate field name
        order.append(name)
        initial[name] = value
    return order, initial


def parse_events(events):
    """Validate the events container and return it as a list."""
    if not isinstance(events, list):
        raise Malformed()
    return events


def apply_event(event, order, initial, current, state):
    """Apply one event, mutating `current` and `state` in place.

    state is {"submitted": bool, "errors": [str, ...]}.
    """
    if not isinstance(event, dict):
        raise Malformed()
    if "type" not in event:
        raise Malformed()
    etype = event["type"]
    if not _is_str(etype):
        raise Malformed()

    if etype == "input":
        if "field" not in event or "value" not in event:
            raise Malformed()
        name = event["field"]
        value = event["value"]
        if not _is_str(name) or not _is_str(value):
            raise Malformed()
        if name not in current:
            raise Malformed()  # unknown field
        if _is_bool(current[name]):
            raise Malformed()  # input on a boolean field
        current[name] = value

    elif etype == "toggle":
        if "field" not in event:
            raise Malformed()
        name = event["field"]
        if not _is_str(name):
            raise Malformed()
        if name not in current:
            raise Malformed()  # unknown field
        if not _is_bool(current[name]):
            raise Malformed()  # toggle on a string field
        current[name] = not current[name]

    elif etype == "reset":
        # INV-UI-RESET-01: back to the INITIAL model, never a cleared one.
        for name in order:
            current[name] = initial[name]
        state["submitted"] = False
        state["errors"] = []

    elif etype == "submit":
        # Validation reports offending fields; it never mutates them.
        empty = [n for n in order if _is_str(current[n]) and current[n] == ""]
        if empty:
            state["submitted"] = False
            state["errors"] = empty
        else:
            state["submitted"] = True
            state["errors"] = []

    else:
        raise Malformed()  # unknown event type


def run(payload):
    """Pure function: parsed stdin payload -> view dict."""
    if not isinstance(payload, dict):
        raise Malformed()
    if "model" not in payload or "events" not in payload:
        raise Malformed()

    order, initial = parse_model(payload["model"])
    events = parse_events(payload["events"])

    current = dict(initial)
    state = {"submitted": False, "errors": []}

    for event in events:
        apply_event(event, order, initial, current, state)

    return {
        "fields": {name: current[name] for name in order},
        "submitted": state["submitted"],
        "errors": list(state["errors"]),
    }


def main():
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except Exception:
        print("ERROR")
        return 0
    try:
        view = run(payload)
    except Malformed:
        print("ERROR")
        return 0
    except Exception:
        print("ERROR")
        return 0
    print(json.dumps(view))
    return 0


if __name__ == "__main__":
    sys.exit(main())
