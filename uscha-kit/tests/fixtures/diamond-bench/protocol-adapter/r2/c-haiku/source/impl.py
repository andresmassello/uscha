#!/usr/bin/env python3
"""Wire/JSON protocol adapter (codec) for frame encode/decode."""

import sys
import json


def is_valid_type(type_str):
    """Check if type is non-empty and all uppercase A-Z."""
    return len(type_str) > 0 and all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' for c in type_str)


def is_valid_key(key):
    """Check if key is non-empty and all lowercase a-z."""
    return len(key) > 0 and all(c in 'abcdefghijklmnopqrstuvwxyz' for c in key)


def is_valid_value(value):
    """Check if value does not contain | or =."""
    return '|' not in value and '=' not in value


def decode_frame(frame):
    """
    Decode a single frame string into a message dict.
    Returns message dict on success, None on any malformation.
    """
    if not isinstance(frame, str):
        return None

    # Empty frame is malformed
    if frame == '':
        return None

    segments = frame.split('|')

    # First segment is TYPE
    type_str = segments[0]
    if not is_valid_type(type_str):
        return None

    fields = []
    for i in range(1, len(segments)):
        segment = segments[i]

        # Each field segment must contain =
        if '=' not in segment:
            return None

        # Split on first = only to get key and value
        key, value = segment.split('=', 1)

        # Validate key and value
        if not is_valid_key(key):
            return None

        if not is_valid_value(value):
            return None

        fields.append([key, value])

    return {"type": type_str, "fields": fields}


def encode_message(message):
    """
    Encode a single message dict into a frame string.
    Returns frame string on success, None on any malformation.
    """
    if not isinstance(message, dict):
        return None

    if 'type' not in message or 'fields' not in message:
        return None

    type_str = message['type']
    fields = message['fields']

    # Validate type
    if not isinstance(type_str, str):
        return None
    if not is_valid_type(type_str):
        return None

    # Validate fields is a list
    if not isinstance(fields, list):
        return None

    segments = [type_str]

    for field in fields:
        # Each field must be a 2-element list [key, value]
        if not isinstance(field, list) or len(field) != 2:
            return None

        key, value = field

        # Both key and value must be strings
        if not isinstance(key, str) or not isinstance(value, str):
            return None

        # Validate key and value
        if not is_valid_key(key):
            return None

        if not is_valid_value(value):
            return None

        segments.append(f"{key}={value}")

    return '|'.join(segments)


def main():
    """Main entry point: read JSON from stdin, process, print result."""
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        print("ERROR")
        return

    if not isinstance(input_data, dict):
        print("ERROR")
        return

    direction = input_data.get('direction')

    if direction == 'decode':
        frames = input_data.get('frames')
        if not isinstance(frames, list):
            print("ERROR")
            return

        messages = []
        for frame in frames:
            message = decode_frame(frame)
            if message is None:
                print("ERROR")
                return
            messages.append(message)

        print(json.dumps(messages))

    elif direction == 'encode':
        messages = input_data.get('messages')
        if not isinstance(messages, list):
            print("ERROR")
            return

        frames = []
        for message in messages:
            frame = encode_message(message)
            if frame is None:
                print("ERROR")
                return
            frames.append(frame)

        print(json.dumps(frames))

    else:
        print("ERROR")
        return


if __name__ == '__main__':
    main()
