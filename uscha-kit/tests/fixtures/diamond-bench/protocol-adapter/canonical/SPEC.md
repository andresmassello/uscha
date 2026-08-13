# SPEC — a wire/JSON protocol adapter (codec)

## The wire format
A FRAME is one string: segments joined by `|`. The first segment is the TYPE — one or more
uppercase letters (A-Z only). Each following segment is a FIELD, `key=value`: the key is one or
more lowercase letters (a-z only); the value is any string not containing `|` or `=` (it may be
empty). A frame has zero or more fields. Field ORDER is meaningful and preserved.

Examples: `PING` · `MSG|id=7|text=hola` · `ACK|of=`.

## Contract
- Input: the whole of stdin is a JSON object, either
  `{"direction": "decode", "frames": [<string>, ...]}` or
  `{"direction": "encode", "messages": [<message>, ...]}`.
- A MESSAGE is `{"type": <string>, "fields": [[<key>, <value>], ...]}` — fields as an ARRAY of
  pairs, because order is meaningful (a JSON object would lose it).
- Output, decode: print the JSON array of messages (one per frame, in order) and exit 0.
- Output, encode: print the JSON array of frame strings (one per message, in order) and exit 0.
- Round-trip law: encode(decode(frames)) reproduces the frames byte-for-byte, and
  decode(encode(messages)) reproduces the messages.

## Errors, precisely — the batch is atomic
On ANY malformed frame (empty string, a TYPE that is not all-uppercase A-Z, a field segment
without `=`, a key that is not all-lowercase a-z, a value containing `=`) or malformed message
(a type/key/value that could not be produced by a legal frame), print exactly `ERROR` — for the
WHOLE batch. **No partial output: one bad frame rejects the input.** Malformed top-level shape
or an unknown direction → `ERROR`.

## Out of scope (do not implement)
No escaping mechanism (a value simply cannot contain `|` or `=`), no checksums, no streaming,
no binary. Output formatting is free; only structure and values are fixed — except encoded
frames, whose exact bytes ARE the contract.
