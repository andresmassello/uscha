import json
import sys

def main():
    try:
        input_data = json.loads(sys.stdin.read())

        if not isinstance(input_data, list):
            print("ERROR")
            return

        result = []
        for record in input_data:
            if not isinstance(record, dict):
                print("ERROR")
                return

            if 'first' not in record or 'last' not in record or 'age' not in record:
                print("ERROR")
                return

            first = record['first']
            last = record['last']
            age = record['age']

            if not isinstance(first, str) or not isinstance(last, str):
                print("ERROR")
                return

            if not isinstance(age, int) or isinstance(age, bool):
                print("ERROR")
                return

            name = first + " " + last
            adult = age >= 18

            result.append({
                "name": name,
                "adult": adult
            })

        print(json.dumps(result))

    except (json.JSONDecodeError, ValueError, KeyError, TypeError):
        print("ERROR")

if __name__ == "__main__":
    main()
