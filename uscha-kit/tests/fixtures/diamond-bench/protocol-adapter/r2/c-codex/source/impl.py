import json
import re
import sys

TYPE_RE = re.compile(r'^[A-Z]+$')
KEY_RE = re.compile(r'^[a-z]+$')


def is_type(value):
    return isinstance(value, str) and TYPE_RE.fullmatch(value) is not None


def is_key(value):
    return isinstance(value, str) and KEY_RE.fullmatch(value) is not None


def is_value(value):
    return isinstance(value, str) and '|' not in value and '=' not in value


def decode_frame(frame):
    if not isinstance(frame, str) or frame == '':
        raise ValueError

    segments = frame.split('|')
    msg_type = segments[0]
    if not is_type(msg_type):
        raise ValueError

    fields = []
    for segment in segments[1:]:
        if segment.count('=') != 1:
            raise ValueError
        key, value = segment.split('=', 1)
        if not is_key(key) or not is_value(value):
            raise ValueError
        fields.append([key, value])

    return {'type': msg_type, 'fields': fields}


def encode_message(message):
    if not isinstance(message, dict) or set(message.keys()) != {'type', 'fields'}:
        raise ValueError

    msg_type = message['type']
    fields = message['fields']
    if not is_type(msg_type) or not isinstance(fields, list):
        raise ValueError

    segments = [msg_type]
    for pair in fields:
        if not isinstance(pair, list) or len(pair) != 2:
            raise ValueError
        key, value = pair
        if not is_key(key) or not is_value(value):
            raise ValueError
        segments.append(key + '=' + value)

    return '|'.join(segments)


def handle(data):
    if not isinstance(data, dict) or 'direction' not in data:
        raise ValueError

    direction = data['direction']
    if direction == 'decode':
        if set(data.keys()) != {'direction', 'frames'} or not isinstance(data['frames'], list):
            raise ValueError
        return [decode_frame(frame) for frame in data['frames']]

    if direction == 'encode':
        if set(data.keys()) != {'direction', 'messages'} or not isinstance(data['messages'], list):
            raise ValueError
        return [encode_message(message) for message in data['messages']]

    raise ValueError


def main():
    try:
        data = json.loads(sys.stdin.read())
        result = handle(data)
        sys.stdout.write(json.dumps(result, separators=(',', ':')))
    except Exception:
        sys.stdout.write('ERROR')


if __name__ == '__main__':
    main()
