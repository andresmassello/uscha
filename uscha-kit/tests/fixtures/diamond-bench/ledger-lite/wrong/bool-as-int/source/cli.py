"""The entry point: stdin -> shape validation -> model.post -> stdout. Never computes a balance."""
import json
import sys

import model


def is_int(v):
    return isinstance(v, int)


def valid_shape(data):
    if not isinstance(data, list):
        return False
    for p in data:
        if not isinstance(p, dict) or not isinstance(p.get("id"), str):
            return False
        lines = p.get("lines")
        if not isinstance(lines, list):
            return False
        for ln in lines:
            if not isinstance(ln, dict) or not isinstance(ln.get("account"), str) \
                    or not is_int(ln.get("amount")):
                return False
    return True


def main():
    try:
        data = json.loads(sys.stdin.read())
    except (ValueError, TypeError):
        print("ERROR")
        return
    if not valid_shape(data):
        print("ERROR")
        return
    balances, rejected = model.post(data)
    print(json.dumps({"balances": balances, "rejected": rejected}))


if __name__ == "__main__":
    main()
