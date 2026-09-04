import json
import sys


class MalformedInput(Exception):
    pass


def exact_keys(obj, keys):
    if not isinstance(obj, dict) or set(obj.keys()) != set(keys):
        raise MalformedInput()


def is_bool(value):
    return type(value) is bool


def parse_payload(raw):
    try:
        payload = json.loads(raw)
    except Exception:
        raise MalformedInput()

    exact_keys(payload, ("model", "events"))
    model = payload["model"]
    events = payload["events"]

    exact_keys(model, ("fields",))
    fields_in = model["fields"]
    if not isinstance(fields_in, list) or not isinstance(events, list):
        raise MalformedInput()

    names = []
    initial = {}
    for field in fields_in:
        exact_keys(field, ("name", "value"))
        name = field["name"]
        value = field["value"]
        if not isinstance(name, str):
            raise MalformedInput()
        if name in initial:
            raise MalformedInput()
        if not (isinstance(value, str) or is_bool(value)):
            raise MalformedInput()
        names.append(name)
        initial[name] = value

    return names, initial, events


def validate_event_shape(event):
    if not isinstance(event, dict) or "type" not in event:
        raise MalformedInput()
    event_type = event["type"]
    if event_type == "input":
        exact_keys(event, ("type", "field", "value"))
    elif event_type == "toggle":
        exact_keys(event, ("type", "field"))
    elif event_type in ("reset", "submit"):
        exact_keys(event, ("type",))
    else:
        raise MalformedInput()
    return event_type


def apply_events(names, initial, events):
    current = dict(initial)
    submitted = False
    errors = []

    for event in events:
        event_type = validate_event_shape(event)

        if event_type == "input":
            field = event["field"]
            value = event["value"]
            if not isinstance(field, str) or field not in current:
                raise MalformedInput()
            if not isinstance(current[field], str) or not isinstance(value, str):
                raise MalformedInput()
            current[field] = value

        elif event_type == "toggle":
            field = event["field"]
            if not isinstance(field, str) or field not in current:
                raise MalformedInput()
            if not is_bool(current[field]):
                raise MalformedInput()
            current[field] = not current[field]

        elif event_type == "reset":
            current = dict(initial)
            submitted = False
            errors = []

        elif event_type == "submit":
            errors = [name for name in names if isinstance(current[name], str) and current[name] == ""]
            submitted = not errors

    return {
        "fields": {name: current[name] for name in names},
        "submitted": submitted,
        "errors": errors,
    }


def main():
    try:
        raw = sys.stdin.read()
        names, initial, events = parse_payload(raw)
        view = apply_events(names, initial, events)
        print(json.dumps(view, separators=(",", ":")))
    except Exception:
        print("ERROR")


if __name__ == "__main__":
    main()
