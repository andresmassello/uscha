import json
import sys

def main():
    try:
        data = json.load(sys.stdin)

        # Validate input is array
        if not isinstance(data, list):
            print("ERROR")
            return

        # Initialize state
        items = {}  # id -> item dict
        next_id = [1]  # Use list to allow mutation in nested function
        creation_order = []  # Track order of creation

        responses = []

        for request in data:
            # Validate request object
            if not isinstance(request, dict):
                print("ERROR")
                return

            method = request.get("method")
            path = request.get("path")
            body = request.get("body")

            # Validate method and path exist
            if not isinstance(method, str) or not isinstance(path, str):
                print("ERROR")
                return

            response = handle_request(method, path, body, items, creation_order, next_id)
            responses.append(response)

        print(json.dumps(responses))

    except (json.JSONDecodeError, ValueError, TypeError):
        print("ERROR")

def handle_request(method, path, body, items, creation_order, next_id):
    # Parse path: split and filter empty strings
    parts = [p for p in path.split("/") if p]

    if len(parts) == 1 and parts[0] == "items":
        # /items
        if method == "GET":
            result_items = [items[id_] for id_ in creation_order]
            return {"status": 200, "body": result_items}
        elif method == "POST":
            # Validate body
            if not isinstance(body, dict) or "name" not in body or not isinstance(body["name"], str):
                return {"status": 400, "body": {"error": "bad request"}}
            new_item = {"id": next_id[0], "name": body["name"]}
            items[next_id[0]] = new_item
            creation_order.append(next_id[0])
            next_id[0] += 1
            return {"status": 201, "body": new_item}
        else:
            # DELETE /items, PUT /items - method not allowed on collection
            return {"status": 405, "body": {"error": "method not allowed"}}

    elif len(parts) == 2 and parts[0] == "items":
        # /items/<id>
        try:
            item_id = int(parts[1])
            if item_id <= 0:
                return {"status": 404, "body": {"error": "not found"}}
        except ValueError:
            return {"status": 404, "body": {"error": "not found"}}

        if method == "GET":
            if item_id in items:
                return {"status": 200, "body": items[item_id]}
            else:
                return {"status": 404, "body": {"error": "not found"}}
        elif method == "PUT":
            # Validate body
            if not isinstance(body, dict) or "name" not in body or not isinstance(body["name"], str):
                return {"status": 400, "body": {"error": "bad request"}}
            if item_id in items:
                items[item_id]["name"] = body["name"]
                return {"status": 200, "body": items[item_id]}
            else:
                return {"status": 404, "body": {"error": "not found"}}
        elif method == "DELETE":
            if item_id in items:
                del items[item_id]
                return {"status": 204, "body": None}
            else:
                return {"status": 404, "body": {"error": "not found"}}
        else:
            # POST /items/<id> - method not allowed on resource
            return {"status": 405, "body": {"error": "method not allowed"}}

    else:
        # Any other path
        return {"status": 404, "body": {"error": "not found"}}

if __name__ == "__main__":
    main()
