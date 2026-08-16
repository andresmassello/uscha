import sys
import json


def fail():
    print("ERROR")
    sys.exit(0)


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        fail()

    if not isinstance(data, dict):
        fail()
    if "model" not in data or "events" not in data:
        fail()

    model = data["model"]
    events = data["events"]

    if not isinstance(model, dict) or "fields" not in model:
        fail()
    fields_spec = model["fields"]
    if not isinstance(fields_spec, list):
        fail()
    if not isinstance(events, list):
        fail()

    initial = {}
    order = []
    types = {}
    seen = set()

    for f in fields_spec:
        if not isinstance(f, dict):
            fail()
        if "name" not in f or "value" not in f:
            fail()
        name = f["name"]
        value = f["value"]
        if not isinstance(name, str):
            fail()
        if name in seen:
            fail()
        seen.add(name)
        if isinstance(value, bool):
            ftype = "bool"
        elif isinstance(value, str):
            ftype = "str"
        else:
            fail()
        initial[name] = value
        types[name] = ftype
        order.append(name)

    current = dict(initial)
    submitted = False
    errors = []

    for ev in events:
        if not isinstance(ev, dict) or "type" not in ev:
            fail()
        etype = ev["type"]

        if etype == "input":
            if "field" not in ev or "value" not in ev:
                fail()
            fname = ev["field"]
            val = ev["value"]
            if not isinstance(fname, str) or fname not in types:
                fail()
            if types[fname] != "str":
                fail()
            if not isinstance(val, str):
                fail()
            current[fname] = val

        elif etype == "toggle":
            if "field" not in ev:
                fail()
            fname = ev["field"]
            if not isinstance(fname, str) or fname not in types:
                fail()
            if types[fname] != "bool":
                fail()
            current[fname] = not current[fname]

        elif etype == "reset":
            current = dict(initial)
            submitted = False
            errors = []

        elif etype == "submit":
            empty = [n for n in order if types[n] == "str" and current[n] == ""]
            if empty:
                submitted = False
                errors = empty
            else:
                submitted = True
                errors = []

        else:
            fail()

    out = {"fields": current, "submitted": submitted, "errors": errors}
    print(json.dumps(out))
    sys.exit(0)


if __name__ == "__main__":
    main()
