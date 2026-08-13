"""Wire/JSON protocol adapter (codec).

Reads a JSON object on stdin describing a batch to decode or encode and
prints the resulting JSON array. The batch is atomic: any malformed frame
or message rejects the whole input with the single token ERROR.

Wire format: TYPE[|key=value]*
  TYPE  -> one or more uppercase A-Z
  key   -> one or more lowercase a-z
  value -> any string without '|' or '='
"""

import json
import sys

ERROR = "ERROR"


def is_type(token):
    """A legal TYPE: one or more characters, all uppercase A-Z."""
    if not token:
        return False
    for ch in token:
        if not ("A" <= ch <= "Z"):
            return False
    return True


def is_key(token):
    """A legal field key: one or more characters, all lowercase a-z."""
    if not token:
        return False
    for ch in token:
        if not ("a" <= ch <= "z"):
            return False
    return True


def is_value(token):
    """A legal field value: any string (possibly empty) without '|' or '='."""
    return "|" not in token and "=" not in token


def decode_frame(frame):
    """Return {"type", "fields"} for a legal frame, or None if malformed."""
    if not isinstance(frame, str) or frame == "":
        return None
    segments = frame.split("|")
    type_token = segments[0]
    if not is_type(type_token):
        return None
    fields = []
    for segment in segments[1:]:
        # A field segment must contain '=' and split into exactly key/value:
        # a second '=' would land in the value, which is illegal.
        parts = segment.split("=")
        if len(parts) != 2:
            return None
        key, value = parts
        if not is_key(key) or not is_value(value):
            return None
        fields.append([key, value])
    return {"type": type_token, "fields": fields}


def encode_message(message):
    """Return the frame string for a legal message, or None if malformed."""
    if not isinstance(message, dict):
        return None
    if set(message.keys()) != {"type", "fields"}:
        return None
    type_token = message["type"]
    if not isinstance(type_token, str) or not is_type(type_token):
        return None
    fields = message["fields"]
    if not isinstance(fields, list):
        return None
    segments = [type_token]
    for pair in fields:
        if not isinstance(pair, list) or len(pair) != 2:
            return None
        key, value = pair
        if not isinstance(key, str) or not isinstance(value, str):
            return None
        if not is_key(key) or not is_value(value):
            return None
        segments.append(key + "=" + value)
    return "|".join(segments)


def run(payload):
    """Return the output JSON-serializable value, or None to signal ERROR."""
    if not isinstance(payload, dict):
        return None
    direction = payload.get("direction")

    if direction == "decode":
        frames = payload.get("frames")
        if not isinstance(frames, list):
            return None
        messages = []
        for frame in frames:
            message = decode_frame(frame)
            if message is None:
                return None
            messages.append(message)
        return messages

    if direction == "encode":
        source = payload.get("messages")
        if not isinstance(source, list):
            return None
        frames = []
        for message in source:
            frame = encode_message(message)
            if frame is None:
                return None
            frames.append(frame)
        return frames

    return None


def main():
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except Exception:
        print(ERROR)
        return 0
    result = run(payload)
    if result is None:
        print(ERROR)
        return 0
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
