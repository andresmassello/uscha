import sys
import json


def fail():
    print("ERROR")
    sys.exit(0)


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except Exception:
        fail()
        return

    if not isinstance(data, dict):
        fail()
        return

    if "model" not in data or "events" not in data:
        fail()
        return

    model = data["model"]
    events = data["events"]

    if not isinstance(model, dict):
        fail()
        return
    if "fields" not in model or not isinstance(model["fields"], list):
        fail()
        return
    if not isinstance(events, list):
        fail()
        return

    field_order = []
    initial_values = {}
    field_types = {}

    for f in model["fields"]:
        if not isinstance(f, dict):
            fail()
            return
        if "name" not in f or "value" not in f:
            fail()
            return
        name = f["name"]
        value = f["value"]
        if not isinstance(name, str):
            fail()
            return
        if isinstance(value, bool):
            vtype = bool
        elif isinstance(value, str):
            vtype = str
        else:
            fail()
            return
        if name in initial_values:
            fail()
            return
        field_order.append(name)
        initial_values[name] = value
        field_types[name] = vtype

    current = dict(initial_values)
    submitted = False
    errors = []

    for ev in events:
        if not isinstance(ev, dict):
            fail()
            return
        etype = ev.get("type")
        if etype == "input":
            if "field" not in ev or "value" not in ev:
                fail()
                return
            field = ev["field"]
            value = ev["value"]
            if not isinstance(field, str) or field not in current:
                fail()
                return
            if field_types[field] is not str:
                fail()
                return
            if not isinstance(value, str):
                fail()
                return
            current[field] = value
        elif etype == "toggle":
            if "field" not in ev:
                fail()
                return
            field = ev["field"]
            if not isinstance(field, str) or field not in current:
                fail()
                return
            if field_types[field] is not bool:
                fail()
                return
            current[field] = not current[field]
        elif etype == "reset":
            current = dict(initial_values)
            submitted = False
            errors = []
        elif etype == "submit":
            empty = [
                name
                for name in field_order
                if field_types[name] is str and current[name] == ""
            ]
            if empty:
                submitted = False
                errors = empty
            else:
                submitted = True
                errors = []
        else:
            fail()
            return

    result = {
        "fields": {name: current[name] for name in field_order},
        "submitted": submitted,
        "errors": errors,
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
