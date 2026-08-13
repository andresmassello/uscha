import sys
import json
import re

TYPE_RE = re.compile(r'^[A-Z]+$')
KEY_RE = re.compile(r'^[a-z]+$')


def decode_frame(frame):
    if not isinstance(frame, str):
        return None
    if frame == "":
        return None
    segments = frame.split("|")
    ftype = segments[0]
    if not TYPE_RE.match(ftype):
        return None
    fields = []
    for seg in segments[1:]:
        if "=" not in seg:
            return None
        idx = seg.index("=")
        key = seg[:idx]
        value = seg[idx + 1:]
        if not KEY_RE.match(key):
            return None
        if "=" in value:
            return None
        fields.append([key, value])
    return {"type": ftype, "fields": fields}


def encode_message(msg):
    if not isinstance(msg, dict):
        return None
    if "type" not in msg or "fields" not in msg:
        return None
    ftype = msg["type"]
    fields = msg["fields"]
    if not isinstance(ftype, str) or not TYPE_RE.match(ftype):
        return None
    if not isinstance(fields, list):
        return None
    parts = [ftype]
    for pair in fields:
        if not isinstance(pair, list) or len(pair) != 2:
            return None
        key, value = pair
        if not isinstance(key, str) or not isinstance(value, str):
            return None
        if not KEY_RE.match(key):
            return None
        if "|" in value or "=" in value:
            return None
        parts.append(key + "=" + value)
    return "|".join(parts)


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except Exception:
        print("ERROR")
        return 0

    if not isinstance(data, dict):
        print("ERROR")
        return 0

    direction = data.get("direction")

    if direction == "decode":
        frames = data.get("frames")
        if not isinstance(frames, list):
            print("ERROR")
            return 0
        results = []
        for f in frames:
            r = decode_frame(f)
            if r is None:
                print("ERROR")
                return 0
            results.append(r)
        print(json.dumps(results))
        return 0

    if direction == "encode":
        messages = data.get("messages")
        if not isinstance(messages, list):
            print("ERROR")
            return 0
        results = []
        for m in messages:
            r = encode_message(m)
            if r is None:
                print("ERROR")
                return 0
            results.append(r)
        print(json.dumps(results))
        return 0

    print("ERROR")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
