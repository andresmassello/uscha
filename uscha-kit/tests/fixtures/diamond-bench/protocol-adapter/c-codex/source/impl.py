import json
import re
import sys

TYPE_RE = re.compile(r"^[A-Z]+$")
KEY_RE = re.compile(r"^[a-z]+$")


def is_legal_type(value):
    return isinstance(value, str) and TYPE_RE.match(value) is not None


def is_legal_key(value):
    return isinstance(value, str) and KEY_RE.match(value) is not None


def is_legal_value(value):
    return isinstance(value, str) and "|" not in value and "=" not in value


def decode_frame(frame):
    if not isinstance(frame, str) or frame == "":
        raise ValueError

    segments = frame.split("|")
    frame_type = segments[0]
    if not is_legal_type(frame_type):
        raise ValueError

    fields = []
    for segment in segments[1:]:
        if segment.count("=") != 1:
            raise ValueError
        key, value = segment.split("=", 1)
        if not is_legal_key(key) or not is_legal_value(value):
            raise ValueError
        fields.append([key, value])

    return {"type": frame_type, "fields": fields}


def validate_message(message):
    if not isinstance(message, dict) or set(message.keys()) != {"type", "fields"}:
        raise ValueError

    frame_type = message["type"]
    fields = message["fields"]
    if not is_legal_type(frame_type) or not isinstance(fields, list):
        raise ValueError

    normalized_fields = []
    for pair in fields:
        if not isinstance(pair, list) or len(pair) != 2:
            raise ValueError
        key, value = pair
        if not is_legal_key(key) or not is_legal_value(value):
            raise ValueError
        normalized_fields.append([key, value])

    return frame_type, normalized_fields


def encode_message(message):
    frame_type, fields = validate_message(message)
    segments = [frame_type]
    for key, value in fields:
        segments.append(key + "=" + value)
    return "|".join(segments)


def handle(payload):
    if not isinstance(payload, dict) or "direction" not in payload:
        raise ValueError

    direction = payload["direction"]
    if direction == "decode":
        if set(payload.keys()) != {"direction", "frames"}:
            raise ValueError
        frames = payload["frames"]
        if not isinstance(frames, list):
            raise ValueError
        return [decode_frame(frame) for frame in frames]

    if direction == "encode":
        if set(payload.keys()) != {"direction", "messages"}:
            raise ValueError
        messages = payload["messages"]
        if not isinstance(messages, list):
            raise ValueError
        return [encode_message(message) for message in messages]

    raise ValueError


def main():
    try:
        data = sys.stdin.read()
        payload = json.loads(data)
        result = handle(payload)
        sys.stdout.write(json.dumps(result, separators=(",", ":")))
    except Exception:
        sys.stdout.write("ERROR")


if __name__ == "__main__":
    main()
