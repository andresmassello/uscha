#!/usr/bin/env python3
"""Wire/JSON protocol adapter (codec).

Reads one JSON object from stdin, prints one line to stdout, exits 0.

Wire format: a FRAME is segments joined by "|". The first segment is the TYPE
(one or more uppercase A-Z). Each following segment is a FIELD "key=value":
the key is one or more lowercase a-z, the value is any string free of "|" and
"=" (possibly empty). Field order is meaningful and preserved.

INV-PA-ATOMIC-01: the batch is atomic (one malformed item rejects the whole
input, never partial output) and encode/decode are mutual identities on legal
inputs.
"""

import json
import sys


class Malformed(Exception):
    """Raised on any illegal frame or message; aborts the whole batch."""


def _is_type(segment):
    """A legal TYPE: one or more characters, all uppercase A-Z."""
    if not segment:
        return False
    for ch in segment:
        if not ("A" <= ch <= "Z"):
            return False
    return True


def _is_key(segment):
    """A legal KEY: one or more characters, all lowercase a-z."""
    if not segment:
        return False
    for ch in segment:
        if not ("a" <= ch <= "z"):
            return False
    return True


def _is_value(segment):
    """A legal VALUE: any string (possibly empty) without "|" or "=" ."""
    return "|" not in segment and "=" not in segment


def decode_frame(frame):
    """Turn one frame string into {"type": ..., "fields": [[k, v], ...]}."""
    if not isinstance(frame, str):
        raise Malformed("frame is not a string")
    if frame == "":
        raise Malformed("empty frame")

    segments = frame.split("|")
    frame_type = segments[0]
    if not _is_type(frame_type):
        raise Malformed("bad TYPE")

    fields = []
    for segment in segments[1:]:
        # A field segment must contain "=" ; the FIRST "=" splits key from
        # value, and any further "=" makes the value illegal.
        if "=" not in segment:
            raise Malformed("field segment without =")
        key, _, value = segment.partition("=")
        if not _is_key(key):
            raise Malformed("bad key")
        if not _is_value(value):
            raise Malformed("bad value")
        fields.append([key, value])

    return {"type": frame_type, "fields": fields}


def encode_message(message):
    """Turn one message into its exact frame string."""
    if not isinstance(message, dict):
        raise Malformed("message is not an object")

    msg_type = message.get("type")
    if not isinstance(msg_type, str) or not _is_type(msg_type):
        raise Malformed("bad message type")

    fields = message.get("fields")
    if not isinstance(fields, list):
        raise Malformed("fields is not an array")

    segments = [msg_type]
    for pair in fields:
        if not isinstance(pair, list) or len(pair) != 2:
            raise Malformed("field is not a [key, value] pair")
        key, value = pair
        if not isinstance(key, str) or not _is_key(key):
            raise Malformed("bad key")
        if not isinstance(value, str) or not _is_value(value):
            raise Malformed("bad value")
        segments.append(key + "=" + value)

    return "|".join(segments)


def run(payload):
    """Dispatch on direction; returns the list to print, or raises Malformed."""
    if not isinstance(payload, dict):
        raise Malformed("top level is not an object")

    direction = payload.get("direction")
    if direction == "decode":
        frames = payload.get("frames")
        if not isinstance(frames, list):
            raise Malformed("frames is not an array")
        # Fully materialized before printing: the batch is atomic.
        return [decode_frame(frame) for frame in frames]

    if direction == "encode":
        messages = payload.get("messages")
        if not isinstance(messages, list):
            raise Malformed("messages is not an array")
        return [encode_message(message) for message in messages]

    raise Malformed("unknown direction")


def main():
    try:
        payload = json.loads(sys.stdin.read())
    except Exception:
        print("ERROR")
        return 0

    try:
        result = run(payload)
    except Malformed:
        print("ERROR")
        return 0
    except Exception:
        print("ERROR")
        return 0

    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
