import sys
import json

def main():
    try:
        # Read entire stdin
        data = sys.stdin.read()

        # Parse as JSON
        records = json.loads(data)

        # Validate it's an array
        if not isinstance(records, list):
            print("ERROR")
            return

        # Transform records
        output = []
        for record in records:
            # Validate record is a dict (JSON object)
            if not isinstance(record, dict):
                print("ERROR")
                return

            # Validate all required fields are present
            required_fields = {'first', 'last', 'age'}
            if not all(field in record for field in required_fields):
                print("ERROR")
                return

            first = record['first']
            last = record['last']
            age = record['age']

            # Validate field types
            if not isinstance(first, str):
                print("ERROR")
                return
            if not isinstance(last, str):
                print("ERROR")
                return
            # age must be an integer (reject bool which is int subclass in Python)
            if not isinstance(age, int) or isinstance(age, bool):
                print("ERROR")
                return

            # Build output record
            output.append({
                "name": first + " " + last,
                "adult": age >= 18
            })

        # Output as JSON
        print(json.dumps(output))

    except (json.JSONDecodeError, ValueError):
        print("ERROR")
    except Exception:
        # Catch any other unexpected errors
        print("ERROR")

if __name__ == "__main__":
    main()
