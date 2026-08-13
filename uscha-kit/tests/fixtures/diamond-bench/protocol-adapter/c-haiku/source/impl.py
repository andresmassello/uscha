#!/usr/bin/env python3
import json
import sys

def validate_type(type_str):
    """Validate that type is all uppercase A-Z."""
    if not isinstance(type_str, str) or not type_str:
        return False
    return all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' for c in type_str)

def validate_key(key_str):
    """Validate that key is all lowercase a-z."""
    if not isinstance(key_str, str) or not key_str:
        return False
    return all(c in 'abcdefghijklmnopqrstuvwxyz' for c in key_str)

def validate_value(value_str):
    """Validate that value doesn't contain | or =."""
    if not isinstance(value_str, str):
        return False
    return '|' not in value_str and '=' not in value_str

def decode_frames(frames):
    """Decode wire frames to messages. Returns None if any frame is invalid."""
    if not isinstance(frames, list):
        return None

    messages = []

    for frame in frames:
        # Frame must be a non-empty string
        if not isinstance(frame, str) or not frame:
            return None

        # Split by |
        segments = frame.split('|')

        # First segment is type
        type_str = segments[0]
        if not validate_type(type_str):
            return None

        # Process fields
        fields = []
        for segment in segments[1:]:
            # Must contain =
            if '=' not in segment:
                return None

            # Split on first = to handle values that are empty
            key, value = segment.split('=', 1)

            # Validate key and value
            if not validate_key(key):
                return None
            if not validate_value(value):
                return None

            fields.append([key, value])

        messages.append({
            "type": type_str,
            "fields": fields
        })

    return messages

def encode_messages(messages):
    """Encode messages to wire frames. Returns None if any message is invalid."""
    if not isinstance(messages, list):
        return None

    frames = []

    for msg in messages:
        # Validate message structure
        if not isinstance(msg, dict):
            return None
        if "type" not in msg or "fields" not in msg:
            return None

        type_str = msg["type"]
        fields = msg["fields"]

        # Validate type
        if not validate_type(type_str):
            return None

        # Validate fields is array of pairs
        if not isinstance(fields, list):
            return None

        frame_segments = [type_str]
        for field in fields:
            if not isinstance(field, list) or len(field) != 2:
                return None

            key, value = field

            # Validate key and value
            if not validate_key(key):
                return None
            if not validate_value(value):
                return None

            frame_segments.append(f"{key}={value}")

        frame = '|'.join(frame_segments)
        frames.append(frame)

    return frames

def main():
    try:
        # Read input from stdin
        input_data = json.load(sys.stdin)

        # Validate top-level structure
        if not isinstance(input_data, dict):
            print("ERROR")
            return

        if "direction" not in input_data:
            print("ERROR")
            return

        direction = input_data["direction"]

        if direction == "decode":
            if "frames" not in input_data:
                print("ERROR")
                return

            frames = input_data["frames"]
            result = decode_frames(frames)

            if result is None:
                print("ERROR")
                return

            print(json.dumps(result))

        elif direction == "encode":
            if "messages" not in input_data:
                print("ERROR")
                return

            messages = input_data["messages"]
            result = encode_messages(messages)

            if result is None:
                print("ERROR")
                return

            print(json.dumps(result))

        else:
            print("ERROR")

    except (json.JSONDecodeError, ValueError, KeyError, TypeError, AttributeError):
        print("ERROR")

if __name__ == "__main__":
    main()
