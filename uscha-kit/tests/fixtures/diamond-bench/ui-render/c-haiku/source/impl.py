import json
import sys


def main():
    try:
        # Read entire stdin
        raw_input = sys.stdin.read()

        # Parse JSON
        data = json.loads(raw_input)

        # Validate top-level structure
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

        if not isinstance(model["fields"], list):
            print("ERROR")
            return

        if not isinstance(events, list):
            print("ERROR")
            return

        # Parse initial fields
        initial_fields = {}
        field_types = {}  # "string" or "bool"
        field_order = []  # Track order for error list

        for field_entry in model["fields"]:
            if not isinstance(field_entry, dict):
                print("ERROR")
                return

            if "name" not in field_entry or "value" not in field_entry:
                print("ERROR")
                return

            name = field_entry["name"]
            value = field_entry["value"]

            if not isinstance(name, str):
                print("ERROR")
                return

            # Check for duplicate field names
            if name in initial_fields:
                print("ERROR")
                return

            # Determine field type
            if isinstance(value, bool):
                field_type = "bool"
            elif isinstance(value, str):
                field_type = "string"
            else:
                print("ERROR")
                return

            initial_fields[name] = value
            field_types[name] = field_type
            field_order.append(name)

        # Initialize current state
        current_fields = dict(initial_fields)
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
                # Set a string field
                if "field" not in event or "value" not in event:
                    print("ERROR")
                    return

                field = event["field"]
                value = event["value"]

                if field not in field_types:
                    print("ERROR")
                    return

                if field_types[field] != "string":
                    print("ERROR")
                    return

                if not isinstance(value, str):
                    print("ERROR")
                    return

                current_fields[field] = value

            elif event_type == "toggle":
                # Flip a boolean field
                if "field" not in event:
                    print("ERROR")
                    return

                field = event["field"]

                if field not in field_types:
                    print("ERROR")
                    return

                if field_types[field] != "bool":
                    print("ERROR")
                    return

                current_fields[field] = not current_fields[field]

            elif event_type == "reset":
                # Restore all fields to initial values
                current_fields = dict(initial_fields)
                submitted = False
                errors = []

            elif event_type == "submit":
                # Validate all string fields are non-empty
                errors = []

                for field_name in field_order:
                    if field_types[field_name] == "string":
                        if current_fields[field_name] == "":
                            errors.append(field_name)

                if errors:
                    submitted = False
                else:
                    submitted = True

            else:
                # Unknown event type
                print("ERROR")
                return

        # Build and print the view
        view = {
            "fields": current_fields,
            "submitted": submitted,
            "errors": errors
        }

        print(json.dumps(view))

    except json.JSONDecodeError:
        print("ERROR")
    except Exception:
        print("ERROR")


if __name__ == "__main__":
    main()
