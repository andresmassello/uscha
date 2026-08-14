import json
import sys


def main():
    try:
        # Read one JSON value from stdin
        input_data = json.load(sys.stdin)

        # Check if input is a JSON array
        if not isinstance(input_data, list):
            print("ERROR")
            return

        # Process the array
        output_array = []

        for record in input_data:
            # Check if element is a JSON object
            if not isinstance(record, dict):
                print("ERROR")
                return

            # Check required fields exist
            if 'first' not in record or 'last' not in record or 'age' not in record:
                print("ERROR")
                return

            first = record['first']
            last = record['last']
            age = record['age']

            # Check field types
            # age must be int, but not bool (bool is subclass of int in Python)
            if not isinstance(first, str):
                print("ERROR")
                return

            if not isinstance(last, str):
                print("ERROR")
                return

            if not isinstance(age, int) or isinstance(age, bool):
                print("ERROR")
                return

            # Create output object
            name = f"{first} {last}"
            adult = age >= 18

            output_object = {
                "name": name,
                "adult": adult
            }

            output_array.append(output_object)

        # Print the output array as JSON
        print(json.dumps(output_array))

    except json.JSONDecodeError:
        print("ERROR")
    except Exception:
        print("ERROR")


if __name__ == "__main__":
    main()
