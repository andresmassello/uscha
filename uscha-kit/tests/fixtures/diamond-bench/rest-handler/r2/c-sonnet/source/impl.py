import json
import sys


def make_error(message):
    return {"error": message}


def parse_id(segment):
    if not segment.isdigit():
        return None
    if segment[0] == "0" and segment != "0":
        return None
    value = int(segment)
    if value <= 0:
        return None
    return value


def handle(request, items, next_id):
    if not isinstance(request, dict):
        return {"status": 400, "body": make_error("bad request")}, next_id

    method = request.get("method")
    path = request.get("path")
    body = request.get("body", None)

    if not isinstance(method, str) or not isinstance(path, str):
        return {"status": 400, "body": make_error("bad request")}, next_id

    segments = [seg for seg in path.split("/") if seg != ""]

    if segments == ["items"]:
        if method == "POST":
            if not isinstance(body, dict) or not isinstance(body.get("name"), str):
                return {"status": 400, "body": make_error("bad request")}, next_id
            item = {"id": next_id, "name": body["name"]}
            items.append(item)
            return {"status": 201, "body": dict(item)}, next_id + 1
        elif method == "GET":
            return {"status": 200, "body": [dict(it) for it in items]}, next_id
        else:
            return {"status": 405, "body": make_error("method not allowed")}, next_id

    if len(segments) == 2 and segments[0] == "items":
        item_id = parse_id(segments[1])
        if item_id is None:
            return {"status": 404, "body": make_error("not found")}, next_id

        if method == "GET":
            for it in items:
                if it["id"] == item_id:
                    return {"status": 200, "body": dict(it)}, next_id
            return {"status": 404, "body": make_error("not found")}, next_id
        elif method == "PUT":
            if not isinstance(body, dict) or not isinstance(body.get("name"), str):
                return {"status": 400, "body": make_error("bad request")}, next_id
            for it in items:
                if it["id"] == item_id:
                    it["name"] = body["name"]
                    return {"status": 200, "body": dict(it)}, next_id
            return {"status": 404, "body": make_error("not found")}, next_id
        elif method == "DELETE":
            for idx, it in enumerate(items):
                if it["id"] == item_id:
                    del items[idx]
                    return {"status": 204, "body": None}, next_id
            return {"status": 404, "body": make_error("not found")}, next_id
        else:
            return {"status": 405, "body": make_error("method not allowed")}, next_id

    return {"status": 404, "body": make_error("not found")}, next_id


def main():
    raw = sys.stdin.read()
    try:
        requests = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        print("ERROR")
        return

    if not isinstance(requests, list):
        print("ERROR")
        return

    for req in requests:
        if not isinstance(req, dict):
            print("ERROR")
            return

    items = []
    next_id = 1
    responses = []
    for req in requests:
        response, next_id = handle(req, items, next_id)
        responses.append(response)

    print(json.dumps(responses))


if __name__ == "__main__":
    main()
