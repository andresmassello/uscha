#!/usr/bin/env python3
"""Form view-model: initial model + ordered events -> final view.

Reads one JSON object from stdin, prints one JSON line to stdout, exits 0.
On any malformed input, prints exactly ERROR (still exit 0).
"""

import json
import sys


class Malformed(Exception):
    """Raised for any input the contract declares malformed."""


def parse_model(model):
    """Return (order, initial) from the model object.

    order is the field name list in declaration order; initial maps name ->
    value (str or bool). Duplicate names are malformed.
    """
    if not isinstance(model, dict):
        raise Malformed("model must be an object")
    fields = model.get("fields")
    if not isinstance(fields, list):
        raise Malformed("model.fields must be a list")

    order = []
    initial = {}
    for field in fields:
        if not isinstance(field, dict):
            raise Malformed("field must be an object")
        name = field.get("name")
        if not isinstance(name, str):
            raise Malformed("field.name must be a string")
        if "value" not in field:
            raise Malformed("field.value is required")
        value = field["value"]
        # bool is a subclass of int, so check it before anything numeric;
        # only str and bool are field types.
        if not isinstance(value, (str, bool)):
            raise Malformed("field.value must be a string or bool")
        if name in initial:
            raise Malformed("duplicate field name")
        order.append(name)
        initial[name] = value
    return order, initial


def apply_event(event, order, initial, state):
    """Apply one event to state, mutating it. state is a dict with keys
    values, submitted, errors."""
    if not isinstance(event, dict):
        raise Malformed("event must be an object")
    etype = event.get("type")

    if etype == "input":
        name = event.get("field")
        value = event.get("value")
        if not isinstance(name, str) or not isinstance(value, str):
            raise Malformed("input requires string field and value")
        if name not in state["values"]:
            raise Malformed("unknown field")
        if isinstance(state["values"][name], bool):
            raise Malformed("input on a boolean field")
        state["values"][name] = value

    elif etype == "toggle":
        name = event.get("field")
        if not isinstance(name, str):
            raise Malformed("toggle requires a string field")
        if name not in state["values"]:
            raise Malformed("unknown field")
        current = state["values"][name]
        if not isinstance(current, bool):
            raise Malformed("toggle on a string field")
        state["values"][name] = not current

    elif etype == "reset":
        # INV-UI-RESET-01: back to the model the form was born with.
        state["values"] = dict(initial)
        state["submitted"] = False
        state["errors"] = []

    elif etype == "submit":
        empty = [n for n in order
                 if isinstance(state["values"][n], str)
                 and state["values"][n] == ""]
        if empty:
            state["submitted"] = False
            state["errors"] = empty
        else:
            state["submitted"] = True
            state["errors"] = []

    else:
        raise Malformed("unknown event type")


def render(payload):
    if not isinstance(payload, dict):
        raise Malformed("input must be an object")
    if "model" not in payload or "events" not in payload:
        raise Malformed("input requires model and events")
    events = payload["events"]
    if not isinstance(events, list):
        raise Malformed("events must be a list")

    order, initial = parse_model(payload["model"])
    state = {"values": dict(initial), "submitted": False, "errors": []}

    for event in events:
        apply_event(event, order, initial, state)

    return {
        "fields": {name: state["values"][name] for name in order},
        "submitted": state["submitted"],
        "errors": state["errors"],
    }


def main():
    try:
        payload = json.loads(sys.stdin.read())
        view = render(payload)
    except Malformed:
        print("ERROR")
        return 0
    except (ValueError, TypeError, KeyError, AttributeError):
        print("ERROR")
        return 0
    print(json.dumps(view))
    return 0


if __name__ == "__main__":
    sys.exit(main())
