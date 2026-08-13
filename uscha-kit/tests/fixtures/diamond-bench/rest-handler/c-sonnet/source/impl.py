import sys
import json
import re

_ID_RE = re.compile(r'^[1-9][0-9]*$')


def _is_valid_id(seg):
    return bool(_ID_RE.match(seg))


def _split_path(path):
    """Classify a path into ('collection',), ('item', id_str), or ('undefined',)."""
    if not isinstance(path, str):
        return ('undefined',)
    segments = path.split('/')
    if len(segments) == 2 and segments[0] == '' and segments[1] == 'items':
        return ('collection',)
    if len(segments) == 3 and segments[0] == '' and segments[1] == 'items' and segments[2] != '':
        return ('item', segments[2])
    return ('undefined',)


def _valid_body_name(body):
    if not isinstance(body, dict):
        return None
    name = body.get('name', None)
    if not isinstance(name, str):
        return None
    return name


def _is_request_obj(req):
    if not isinstance(req, dict):
        return False
    if not isinstance(req.get('method'), str):
        return False
    if not isinstance(req.get('path'), str):
        return False
    if 'body' in req:
        # body may be any JSON value (object expected for POST/PUT, validated later)
        pass
    return True


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except Exception:
        print('ERROR')
        return 0

    if not isinstance(data, list):
        print('ERROR')
        return 0

    for req in data:
        if not _is_request_obj(req):
            print('ERROR')
            return 0

    items = []  # list of {"id": int, "name": str}, creation order
    next_id = 1

    responses = []

    for req in data:
        method = req.get('method')
        path = req.get('path')
        body = req.get('body', None)

        kind = _split_path(path)

        if kind[0] == 'undefined':
            responses.append({'status': 404, 'body': {'error': 'not found'}})
            continue

        if kind[0] == 'collection':
            if method == 'GET':
                responses.append({'status': 200, 'body': list(items)})
            elif method == 'POST':
                name = _valid_body_name(body)
                if name is None:
                    responses.append({'status': 400, 'body': {'error': 'bad request'}})
                else:
                    new_item = {'id': next_id, 'name': name}
                    next_id += 1
                    items.append(new_item)
                    responses.append({'status': 201, 'body': dict(new_item)})
            else:
                responses.append({'status': 405, 'body': {'error': 'method not allowed'}})
            continue

        # kind[0] == 'item'
        id_str = kind[1]
        if not _is_valid_id(id_str):
            responses.append({'status': 404, 'body': {'error': 'not found'}})
            continue

        item_id = int(id_str)

        if method == 'GET':
            found = next((it for it in items if it['id'] == item_id), None)
            if found is None:
                responses.append({'status': 404, 'body': {'error': 'not found'}})
            else:
                responses.append({'status': 200, 'body': dict(found)})
        elif method == 'PUT':
            name = _valid_body_name(body)
            if name is None:
                responses.append({'status': 400, 'body': {'error': 'bad request'}})
            else:
                found = next((it for it in items if it['id'] == item_id), None)
                if found is None:
                    responses.append({'status': 404, 'body': {'error': 'not found'}})
                else:
                    found['name'] = name
                    responses.append({'status': 200, 'body': dict(found)})
        elif method == 'DELETE':
            found = next((it for it in items if it['id'] == item_id), None)
            if found is None:
                responses.append({'status': 404, 'body': {'error': 'not found'}})
            else:
                items.remove(found)
                responses.append({'status': 204, 'body': None})
        else:
            responses.append({'status': 405, 'body': {'error': 'method not allowed'}})

    print(json.dumps(responses))
    return 0


if __name__ == '__main__':
    sys.exit(main())
