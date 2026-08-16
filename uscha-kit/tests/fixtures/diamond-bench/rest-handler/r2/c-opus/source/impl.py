"""In-memory REST-shaped item API (transport-free).

Reads a JSON array of requests from stdin, applies them in order against one
in-memory collection, and prints a JSON array of responses to stdout.

Routing is table-driven so that "path exists but method is wrong" (405) is
structurally distinct from "path does not exist" (404).
"""

import json
import sys

NOT_FOUND = {"error": "not found"}
METHOD_NOT_ALLOWED = {"error": "method not allowed"}
BAD_REQUEST = {"error": "bad request"}


class Store:
    """The single in-memory collection. Ids are history, not slots."""

    def __init__(self):
        self._items = []          # list of dicts, kept in creation order
        self._next_id = 1         # monotonic for the run; never rewound

    def create(self, name):
        item = {"id": self._next_id, "name": name}
        self._next_id += 1
        self._items.append(item)
        return item

    def list_all(self):
        return [dict(item) for item in self._items]

    def _find(self, item_id):
        for item in self._items:
            if item["id"] == item_id:
                return item
        return None

    def get(self, item_id):
        item = self._find(item_id)
        return dict(item) if item is not None else None

    def update(self, item_id, name):
        item = self._find(item_id)
        if item is None:
            return None
        item["name"] = name
        return dict(item)

    def delete(self, item_id):
        item = self._find(item_id)
        if item is None:
            return False
        self._items.remove(item)
        return True


def parse_path(path):
    """Classify a path into a route.

    Returns one of:
      ("collection", None)  -> /items
      ("item", <int>)       -> /items/<positive int>
      ("unknown", None)     -> anything else, including bad id segments
    """
    if not isinstance(path, str):
        return ("unknown", None)
    # A trailing slash is not part of the defined surface; only exact shapes match.
    segments = path.split("/")
    if len(segments) < 2 or segments[0] != "":
        return ("unknown", None)
    parts = segments[1:]
    if len(parts) == 1 and parts[0] == "items":
        return ("collection", None)
    if len(parts) == 2 and parts[0] == "items":
        raw = parts[1]
        # Positive integer only: no sign, no whitespace, no leading zeros ambiguity
        # beyond what int() would accept, no unicode digits.
        if raw.isdigit() and not raw.startswith("0"):
            value = int(raw)
            if value > 0:
                return ("item", value)
        return ("unknown", None)
    return ("unknown", None)


def extract_name(body):
    """Return the name string from a request body, or None if the body is invalid."""
    if not isinstance(body, dict):
        return None
    name = body.get("name")
    if not isinstance(name, str):
        return None
    return name


def handle(store, request):
    if not isinstance(request, dict):
        return None  # signalled by the caller as a malformed input array

    method = request.get("method")
    path = request.get("path")
    if not isinstance(method, str) or not isinstance(path, str):
        return None

    kind, item_id = parse_path(path)

    if kind == "unknown":
        return {"status": 404, "body": dict(NOT_FOUND)}

    if kind == "collection":
        if method == "POST":
            name = extract_name(request.get("body"))
            if name is None:
                return {"status": 400, "body": dict(BAD_REQUEST)}
            return {"status": 201, "body": store.create(name)}
        if method == "GET":
            return {"status": 200, "body": store.list_all()}
        return {"status": 405, "body": dict(METHOD_NOT_ALLOWED)}

    # kind == "item"
    if method == "GET":
        item = store.get(item_id)
        if item is None:
            return {"status": 404, "body": dict(NOT_FOUND)}
        return {"status": 200, "body": item}
    if method == "PUT":
        name = extract_name(request.get("body"))
        if name is None:
            return {"status": 400, "body": dict(BAD_REQUEST)}
        item = store.update(item_id, name)
        if item is None:
            return {"status": 404, "body": dict(NOT_FOUND)}
        return {"status": 200, "body": item}
    if method == "DELETE":
        if not store.delete(item_id):
            return {"status": 404, "body": dict(NOT_FOUND)}
        return {"status": 204, "body": None}
    return {"status": 405, "body": dict(METHOD_NOT_ALLOWED)}


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

    # Validate the shape of every request BEFORE mutating state, so a malformed
    # array never emits a partial batch alongside ERROR.
    for request in requests:
        if not isinstance(request, dict):
            print("ERROR")
            return
        if not isinstance(request.get("method"), str) or not isinstance(request.get("path"), str):
            print("ERROR")
            return

    store = Store()
    responses = [handle(store, request) for request in requests]
    print(json.dumps(responses))


if __name__ == "__main__":
    main()
