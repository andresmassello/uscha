import sys
import json
import re

TYPE_RE = re.compile(r'^[A-Z]+$')
KEY_RE = re.compile(r'^[a-z]+$')


def decode_frame(frame):
    if not isinstance(frame, str):
        raise ValueError("frame must be a string")
    if frame == '':
        raise ValueError("empty frame")
    segments = frame.split('|')
    type_seg = segments[0]
    if not TYPE_RE.match(type_seg):
        raise ValueError("bad type")
    fields = []
    for seg in segments[1:]:
        if seg.count('=') != 1:
            raise ValueError("field must have exactly one '='")
        idx = seg.index('=')
        key = seg[:idx]
        value = seg[idx + 1:]
        if not KEY_RE.match(key):
            raise ValueError("bad key")
        fields.append([key, value])
    return {"type": type_seg, "fields": fields}


def encode_message(msg):
    if not isinstance(msg, dict):
        raise ValueError("message must be an object")
    if "type" not in msg or "fields" not in msg:
        raise ValueError("message missing type/fields")
    type_ = msg["type"]
    fields = msg["fields"]
    if not isinstance(type_, str) or not TYPE_RE.match(type_):
        raise ValueError("bad type")
    if not isinstance(fields, list):
        raise ValueError("fields must be a list")
    parts = [type_]
    for pair in fields:
        if not isinstance(pair, list) or len(pair) != 2:
            raise ValueError("field must be a [key, value] pair")
        key, value = pair
        if not isinstance(key, str) or not KEY_RE.match(key):
            raise ValueError("bad key")
        if not isinstance(value, str):
            raise ValueError("value must be a string")
        if '|' in value or '=' in value:
            raise ValueError("value contains '|' or '='")
        parts.append(key + "=" + value)
    return "|".join(parts)


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        print("ERROR")
        return

    try:
        if not isinstance(data, dict):
            raise ValueError("top-level input must be an object")
        direction = data.get("direction")
        if direction == "decode":
            frames = data.get("frames")
            if not isinstance(frames, list):
                raise ValueError("frames must be a list")
            result = [decode_frame(f) for f in frames]
        elif direction == "encode":
            messages = data.get("messages")
            if not isinstance(messages, list):
                raise ValueError("messages must be a list")
            result = [encode_message(m) for m in messages]
        else:
            raise ValueError("unknown direction")
        print(json.dumps(result))
    except Exception:
        print("ERROR")


if __name__ == "__main__":
    main()
