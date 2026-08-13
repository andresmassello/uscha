"""In-memory REST-shaped item API, transport-free.

Reads a JSON array of requests from stdin, prints a JSON array of responses.
Pure stdlib, Python 3.8+.
"""

import json
import sys

NOT_FOUND = {"error": "not found"}
METHOD_NOT_ALLOWED = {"error": "method not allowed"}
BAD_REQUEST = {"error": "bad request"}


class Store:
    """The collection. Ids are history, not slots (INV-RH-IDS-01)."""

    def __init__(self):
        self._items = []          # creation order preserved
        self._next_id = 1         # monotonic counter, never rewound

    def create(self, name):
        item = {"id": self._next_id, "name": name}
        self._next_id += 1
        self._items.append(item)
        return item

    def all(self):
        return list(self._items)

    def get(self, item_id):
        for item in self._items:
            if item["id"] == item_id:
                return item
        return None

    def delete(self, item_id):
        for index, item in enumerate(self._items):
            if item["id"] == item_id:
                del self._items[index]
                return True
        return False


def parse_id(segment):
    """A positive integer id, or None. No signs, no whitespace, no leading zeros."""
    if not segment or not segment.isdigit():
        return None
    value = int(segment)
    if value <= 0:
        return None
    return value


def route(path):
    """Classify a path.

    Returns ("collection", None), ("item", id) or (None, None) for undefined paths.
    """
    if not isinstance(path, str) or not path.startswith("/"):
        return (None, None)
    segments = path.split("/")[1:]
    # A trailing slash yields an empty final segment: /items/ is not /items.
    if segments == ["items"]:
        return ("collection", None)
    if len(segments) == 2 and segments[0] == "items":
        item_id = parse_id(segments[1])
        if item_id is None:
            return (None, None)
        return ("item", item_id)
    return (None, None)


def body_name(body):
    """The name from a POST/PUT body, or None if the body is not valid."""
    if not isinstance(body, dict):
        return None
    name = body.get("name")
    if not isinstance(name, str):
        return None
    return name


def handle(request, store):
    if not isinstance(request, dict):
        raise ValueError("request is not an object")
    method = request.get("method")
    path = request.get("path")
    if not isinstance(method, str) or not isinstance(path, str):
        raise ValueError("request lacks a string method/path")
    body = request.get("body")

    kind, item_id = route(path)

    if kind is None:
        return {"status": 404, "body": NOT_FOUND}

    if kind == "collection":
        if method == "POST":
            name = body_name(body)
            if name is None:
                return {"status": 400, "body": BAD_REQUEST}
            return {"status": 201, "body": store.create(name)}
        if method == "GET":
            return {"status": 200, "body": store.all()}
        return {"status": 405, "body": METHOD_NOT_ALLOWED}

    # kind == "item"
    if method == "GET":
        item = store.get(item_id)
        if item is None:
            return {"status": 404, "body": NOT_FOUND}
        return {"status": 200, "body": item}
    if method == "PUT":
        name = body_name(body)
        if name is None:
            return {"status": 400, "body": BAD_REQUEST}
        item = store.get(item_id)
        if item is None:
            return {"status": 404, "body": NOT_FOUND}
        item["name"] = name
        return {"status": 200, "body": item}
    if method == "DELETE":
        if not store.delete(item_id):
            return {"status": 404, "body": NOT_FOUND}
        return {"status": 204, "body": None}
    return {"status": 405, "body": METHOD_NOT_ALLOWED}


def main():
    raw = sys.stdin.read()
    try:
        requests = json.loads(raw)
    except Exception:
        print("ERROR")
        return
    if not isinstance(requests, list):
        print("ERROR")
        return

    store = Store()
    responses = []
    for request in requests:
        try:
            responses.append(handle(request, store))
        except ValueError:
            print("ERROR")
            return
    print(json.dumps(responses))


if __name__ == "__main__":
    main()
    sys.exit(0)
