import json
import sys


_ERROR = "ERROR"


def _is_exact_dict(value, keys):
    return isinstance(value, dict) and set(value.keys()) == set(keys)


def _load_payload():
    try:
        return json.loads(sys.stdin.read())
    except Exception:
        return None


def _build_initial_state(payload):
    if not _is_exact_dict(payload, ("model", "events")):
        return None

    model = payload["model"]
    events = payload["events"]
    if not _is_exact_dict(model, ("fields",)) or not isinstance(model["fields"], list):
        return None
    if not isinstance(events, list):
        return None

    initial = {}
    kinds = {}
    order = []

    for field in model["fields"]:
        if not _is_exact_dict(field, ("name", "value")):
            return None
        name = field["name"]
        value = field["value"]
        if not isinstance(name, str):
            return None
        if name in initial:
            return None
        if isinstance(value, bool):
            kind = "bool"
        elif isinstance(value, str):
            kind = "string"
        else:
            return None
        initial[name] = value
        kinds[name] = kind
        order.append(name)

    return initial, kinds, order, events


def _apply_events(initial, kinds, order, events):
    current = dict(initial)
    submitted = False
    errors = []

    for event in events:
        if not isinstance(event, dict) or "type" not in event:
            return None
        event_type = event["type"]

        if event_type == "input":
            if not _is_exact_dict(event, ("type", "field", "value")):
                return None
            field = event["field"]
            value = event["value"]
            if not isinstance(field, str) or field not in current:
                return None
            if kinds[field] != "string" or not isinstance(value, str):
                return None
            current[field] = value

        elif event_type == "toggle":
            if not _is_exact_dict(event, ("type", "field")):
                return None
            field = event["field"]
            if not isinstance(field, str) or field not in current:
                return None
            if kinds[field] != "bool":
                return None
            current[field] = not current[field]

        elif event_type == "reset":
            if not _is_exact_dict(event, ("type",)):
                return None
            current = dict(initial)
            submitted = False
            errors = []

        elif event_type == "submit":
            if not _is_exact_dict(event, ("type",)):
                return None
            empty_fields = [name for name in order if kinds[name] == "string" and current[name] == ""]
            if empty_fields:
                submitted = False
                errors = empty_fields
            else:
                submitted = True
                errors = []

        else:
            return None

    return {
        "fields": {name: current[name] for name in order},
        "submitted": submitted,
        "errors": errors,
    }


def main():
    try:
        payload = _load_payload()
        state = _build_initial_state(payload)
        if state is None:
            sys.stdout.write(_ERROR)
            return
        view = _apply_events(*state)
        if view is None:
            sys.stdout.write(_ERROR)
            return
        sys.stdout.write(json.dumps(view, separators=(",", ":")))
    except Exception:
        sys.stdout.write(_ERROR)


if __name__ == "__main__":
    main()
