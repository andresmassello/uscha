import json
import sys


NOT_FOUND = {"error": "not found"}
METHOD_NOT_ALLOWED = {"error": "method not allowed"}
BAD_REQUEST = {"error": "bad request"}


def response(status, body):
    return {"status": status, "body": body}


def parse_item_id(path):
    prefix = "/items/"
    if not isinstance(path, str) or not path.startswith(prefix):
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


def handle_collection(method, request, items, next_id):
    if method == "GET":
        return response(200, [dict(item) for item in items]), next_id

    if method == "POST":
        body = request.get("body")
        if not valid_name_body(body):
            return response(400, dict(BAD_REQUEST)), next_id
        item = {"id": next_id, "name": body["name"]}
        items.append(item)
        return response(201, dict(item)), next_id + 1

    return response(405, dict(METHOD_NOT_ALLOWED)), next_id


def handle_item(method, request, item_id, items_by_id, next_id):
    item = items_by_id.get(item_id)

    if method == "GET":
        if item is None:
            return response(404, dict(NOT_FOUND)), next_id
        return response(200, dict(item)), next_id

    if method == "PUT":
        body = request.get("body")
        if not valid_name_body(body):
            return response(400, dict(BAD_REQUEST)), next_id
        if item is None:
            return response(404, dict(NOT_FOUND)), next_id
        item["name"] = body["name"]
        return response(200, dict(item)), next_id

    if method == "DELETE":
        if item is None:
            return response(404, dict(NOT_FOUND)), next_id
        items_by_id.pop(item_id)
        return response(204, None), next_id

    return response(405, dict(METHOD_NOT_ALLOWED)), next_id


def handle_request(request, items, items_by_id, next_id):
    method = request["method"]
    path = request["path"]

    if path == "/items":
        return handle_collection(method, request, items, next_id)

    item_id = parse_item_id(path)
    if item_id is not None:
        return handle_item(method, request, item_id, items_by_id, next_id)

    return response(404, dict(NOT_FOUND)), next_id


def is_request_object(value):
    return (
        isinstance(value, dict)
        and isinstance(value.get("method"), str)
        and isinstance(value.get("path"), str)
    )


def run(requests):
    items = []
    items_by_id = {}
    next_id = 1
    responses = []

    for request in requests:
        reply, next_id = handle_request(request, items, items_by_id, next_id)
        if reply["status"] == 201:
            items_by_id[reply["body"]["id"]] = items[-1]
        elif request["path"].startswith("/items/") and reply["status"] == 204:
            item_id = parse_item_id(request["path"])
            items[:] = [item for item in items if item["id"] != item_id]
        responses.append(reply)

    return responses


def main():
    try:
        raw_input = sys.stdin.read()
        requests = json.loads(raw_input)
        if not isinstance(requests, list) or not all(is_request_object(req) for req in requests):
            print("ERROR")
            return
        print(json.dumps(run(requests), separators=(",", ":")))
    except Exception:
        print("ERROR")


if __name__ == "__main__":
    main()
