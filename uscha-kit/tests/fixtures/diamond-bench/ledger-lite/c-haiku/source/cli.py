import sys
import json
import model


def main():
    try:
        # Read and parse JSON from stdin
        input_text = sys.stdin.read()
        data = json.loads(input_text)

        # Shape validation: root must be array
        if not isinstance(data, list):
            print("ERROR")
            return

        postings = []

        for element in data:
            # Shape validation: each element must be object (dict)
            if not isinstance(element, dict):
                print("ERROR")
                return

            # Shape validation: must have 'id' and 'lines' keys
            if 'id' not in element or 'lines' not in element:
                print("ERROR")
                return

            posting_id = element['id']
            lines_raw = element['lines']

            # Shape validation: id must be string
            if not isinstance(posting_id, str):
                print("ERROR")
                return

            # Shape validation: lines must be array
            if not isinstance(lines_raw, list):
                print("ERROR")
                return

            # Validate each line in the lines array
            lines = []
            for line in lines_raw:
                # Shape validation: line must be object (dict)
                if not isinstance(line, dict):
                    print("ERROR")
                    return

                # Shape validation: line must have 'account' and 'amount' keys
                if 'account' not in line or 'amount' not in line:
                    print("ERROR")
                    return

                account = line['account']
                amount = line['amount']

                # Shape validation: account must be string
                if not isinstance(account, str):
                    print("ERROR")
                    return

                # Shape validation: amount must be integer (not boolean)
                # Note: in Python, bool is a subclass of int, so check that explicitly
                if not isinstance(amount, int) or isinstance(amount, bool):
                    print("ERROR")
                    return

                lines.append({'account': account, 'amount': amount})

            postings.append({'id': posting_id, 'lines': lines})

        # Call the model to compute balances and rejections
        balances, rejected = model.post(postings)

        # Format and output result
        result = {
            'balances': balances,
            'rejected': rejected
        }
        print(json.dumps(result))

    except json.JSONDecodeError:
        # JSON parsing failed
        print("ERROR")
    except Exception:
        # Catch any other unexpected errors
        print("ERROR")


if __name__ == '__main__':
    main()
