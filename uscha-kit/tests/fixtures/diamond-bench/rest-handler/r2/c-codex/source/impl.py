import json
import sys


NOT_FOUND = {"error": "not found"}
METHOD_NOT_ALLOWED = {"error": "method not allowed"}
BAD_REQUEST = {"error": "bad request"}


def response(status, body):
    return {"status": status, "body": body}


def is_valid_request(value):
    return (
        isinstance(value, dict)
        and isinstance(value.get("method"), str)
        and isinstance(value.get("path"), str)
    )


def parse_item_id(path):
    prefix = "/items/"
    if not path.startswith(prefix):
        return None
    raw_id = path[len(prefix):]
    if not raw_id or "/" in raw_id:
        return None
    if not raw_id.isdigit():
        return None
    item_id = int(raw_id)
    if item_id <= 0:
        return None
    return item_id


def valid_name_body(body):
    return isinstance(body, dict) and isinstance(body.get("name"), str)


def handle_collection(method, request, items_in_order, next_id_holder):
    if method == "GET":
        return response(200, [dict(item) for item in items_in_order])

    if method == "POST":
        body = request.get("body")
        if not valid_name_body(body):
            return response(400, BAD_REQUEST)
        item = {"id": next_id_holder[0], "name": body["name"]}
        next_id_holder[0] += 1
        items_in_order.append(item)
        return response(201, dict(item))

    return response(405, METHOD_NOT_ALLOWED)


def handle_item(method, request, item_id, items_in_order):
    item = None
    for current in items_in_order:
        if current["id"] == item_id:
            item = current
            break

    if method == "GET":
        if item is None:
            return response(404, NOT_FOUND)
        return response(200, dict(item))

    if method == "PUT":
        body = request.get("body")
        if not valid_name_body(body):
            return response(400, BAD_REQUEST)
        if item is None:
            return response(404, NOT_FOUND)
        item["name"] = body["name"]
        return response(200, dict(item))

    if method == "DELETE":
        if item is None:
            return response(404, NOT_FOUND)
        items_in_order.remove(item)
        return response(204, None)

    return response(405, METHOD_NOT_ALLOWED)


def handle_request(request, items_in_order, next_id_holder):
    method = request["method"]
    path = request["path"]

    if path == "/items":
        return handle_collection(method, request, items_in_order, next_id_holder)

    item_id = parse_item_id(path)
    if item_id is not None:
        return handle_item(method, request, item_id, items_in_order)

    return response(404, NOT_FOUND)


def main():
    try:
        data = json.loads(sys.stdin.read())
    except Exception:
        print("ERROR")
        return

    if not isinstance(data, list) or not all(is_valid_request(item) for item in data):
        print("ERROR")
        return

    items_in_order = []
    next_id_holder = [1]
    responses = []

    for request in data:
        responses.append(handle_request(request, items_in_order, next_id_holder))

    print(json.dumps(responses))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("ERROR")
