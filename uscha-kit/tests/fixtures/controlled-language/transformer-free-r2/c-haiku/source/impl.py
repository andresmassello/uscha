import json
import sys

def main():
    try:
        # Read JSON from stdin
        input_data = sys.stdin.read()
        records = json.loads(input_data)

        # Validate input is a JSON array
        if not isinstance(records, list):
            print("ERROR")
            return

        # Transform each record
        output = []
        for record in records:
            # Validate record is an object
            if not isinstance(record, dict):
                print("ERROR")
                return

            # Validate required fields exist
            if "first" not in record or "last" not in record or "age" not in record:
                print("ERROR")
                return

            first = record["first"]
            last = record["last"]
            age = record["age"]

            # Validate types: first and last must be strings
            if not isinstance(first, str) or not isinstance(last, str):
                print("ERROR")
                return

            # Validate age: must be int, not bool (bool is subclass of int in Python)
            if not isinstance(age, int) or isinstance(age, bool):
                print("ERROR")
                return

            # Build output record: name = first + space + last, adult = age >= 18
            name = first + " " + last
            adult = age >= 18
            output.append({"name": name, "adult": adult})

        # Print output array as JSON
        print(json.dumps(output))

    except json.JSONDecodeError:
        # Malformed JSON
        print("ERROR")
    except Exception:
        # Any other error
        print("ERROR")

if __name__ == "__main__":
    main()
