import json
import sys
from typing import Any, Dict, List, Optional


class ItemStore:
    def __init__(self):
        self.items: Dict[int, Dict[str, Any]] = {}
        self.next_id = 1

    def create_item(self, name: str) -> Dict[str, Any]:
        item = {"id": self.next_id, "name": name}
        self.items[self.next_id] = item
        self.next_id += 1
        return item

    def get_all_items(self) -> List[Dict[str, Any]]:
        return [self.items[id] for id in sorted(self.items.keys())]

    def get_item(self, item_id: int) -> Optional[Dict[str, Any]]:
        return self.items.get(item_id)

    def update_item(self, item_id: int, name: str) -> Optional[Dict[str, Any]]:
        if item_id in self.items:
            self.items[item_id]["name"] = name
            return self.items[item_id]
        return None

    def delete_item(self, item_id: int) -> bool:
        if item_id in self.items:
            del self.items[item_id]
            return True
        return False


def is_valid_create_body(body: Any) -> bool:
    if not isinstance(body, dict):
        return False
    if "name" not in body:
        return False
    if not isinstance(body["name"], str):
        return False
    return True


def handle_request(method: str, path: str, body: Any, store: ItemStore) -> Dict[str, Any]:
    if path == "/items":
        if method == "GET":
            items_list = store.get_all_items()
            return {"status": 200, "body": items_list}
        elif method == "POST":
            if not is_valid_create_body(body):
                return {"status": 400, "body": {"error": "bad request"}}
            new_item = store.create_item(body["name"])
            return {"status": 201, "body": new_item}
        else:
            return {"status": 405, "body": {"error": "method not allowed"}}

    # Check if it matches /items/<id>
    parts = path.strip("/").split("/")
    if len(parts) == 2 and parts[0] == "items":
        id_str = parts[1]
        try:
            item_id = int(id_str)
            if item_id <= 0:
                return {"status": 404, "body": {"error": "not found"}}
        except ValueError:
            return {"status": 404, "body": {"error": "not found"}}

        if method == "GET":
            item = store.get_item(item_id)
            if item:
                return {"status": 200, "body": item}
            else:
                return {"status": 404, "body": {"error": "not found"}}

        elif method == "PUT":
            if not is_valid_create_body(body):
                return {"status": 400, "body": {"error": "bad request"}}
            item = store.update_item(item_id, body["name"])
            if item:
                return {"status": 200, "body": item}
            else:
                return {"status": 404, "body": {"error": "not found"}}

        elif method == "DELETE":
            if store.delete_item(item_id):
                return {"status": 204, "body": None}
            else:
                return {"status": 404, "body": {"error": "not found"}}

        else:
            return {"status": 405, "body": {"error": "method not allowed"}}

    # Undefined path
    return {"status": 404, "body": {"error": "not found"}}


def main():
    try:
        input_data = json.load(sys.stdin)

        if not isinstance(input_data, list):
            print("ERROR")
            return

        for req in input_data:
            if not isinstance(req, dict):
                print("ERROR")
                return
            if "method" not in req or "path" not in req:
                print("ERROR")
                return
            if not isinstance(req["method"], str) or not isinstance(req["path"], str):
                print("ERROR")
                return

        store = ItemStore()
        responses = []

        for request in input_data:
            method = request["method"]
            path = request["path"]
            body = request.get("body")
            response = handle_request(method, path, body, store)
            responses.append(response)

        print(json.dumps(responses))

    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        print("ERROR")


if __name__ == "__main__":
    main()
