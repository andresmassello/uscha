import json
import sys

def main():
    try:
        # Read input
        input_text = sys.stdin.read()
        data = json.loads(input_text)

        # Validate input structure
        if not isinstance(data, dict):
            print("ERROR")
            return

        if "model" not in data or "events" not in data:
            print("ERROR")
            return

        model = data["model"]
        events = data["events"]

        if not isinstance(model, dict) or "fields" not in model:
            print("ERROR")
            return

        if not isinstance(events, list):
            print("ERROR")
            return

        fields_list = model["fields"]
        if not isinstance(fields_list, list):
            print("ERROR")
            return

        # Validate and build initial state
        initial_state = {}
        field_types = {}  # Track whether each field is string or bool

        for field in fields_list:
            if not isinstance(field, dict):
                print("ERROR")
                return

            if "name" not in field or "value" not in field:
                print("ERROR")
                return

            name = field["name"]
            value = field["value"]

            if not isinstance(name, str):
                print("ERROR")
                return

            # Check for duplicate field names
            if name in initial_state:
                print("ERROR")
                return

            # Validate value type (string or bool only)
            if isinstance(value, str):
                field_types[name] = "string"
                initial_state[name] = value
            elif isinstance(value, bool):
                field_types[name] = "bool"
                initial_state[name] = value
            else:
                print("ERROR")
                return

        # Initialize current state
        current_state = initial_state.copy()
        submitted = False
        errors = []

        # Process events
        for event in events:
            if not isinstance(event, dict):
                print("ERROR")
                return

            if "type" not in event:
                print("ERROR")
                return

            event_type = event["type"]

            if event_type == "input":
                if "field" not in event or "value" not in event:
                    print("ERROR")
                    return

                field_name = event["field"]
                value = event["value"]

                if field_name not in initial_state:
                    print("ERROR")
                    return

                if field_types[field_name] != "string":
                    print("ERROR")
                    return

                if not isinstance(value, str):
                    print("ERROR")
                    return

                current_state[field_name] = value

            elif event_type == "toggle":
                if "field" not in event:
                    print("ERROR")
                    return

                field_name = event["field"]

                if field_name not in initial_state:
                    print("ERROR")
                    return

                if field_types[field_name] != "bool":
                    print("ERROR")
                    return

                current_state[field_name] = not current_state[field_name]

            elif event_type == "reset":
                current_state = initial_state.copy()
                submitted = False
                errors = []

            elif event_type == "submit":
                # Validate all string fields are non-empty
                empty_fields = []
                for name in initial_state:
                    if field_types[name] == "string" and current_state[name] == "":
                        empty_fields.append(name)

                if empty_fields:
                    submitted = False
                    errors = empty_fields
                else:
                    submitted = True
                    errors = []

            else:
                print("ERROR")
                return

        # Build output
        output = {
            "fields": current_state,
            "submitted": submitted,
            "errors": errors
        }

        print(json.dumps(output))

    except Exception:
        print("ERROR")

if __name__ == "__main__":
    main()
