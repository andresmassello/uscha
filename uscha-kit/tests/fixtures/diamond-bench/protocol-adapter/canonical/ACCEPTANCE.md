# ACCEPTANCE — protocol adapter

- [ ] AC-PA-01 decode turns each frame into {type, fields as ordered pairs}; field order is
  preserved exactly.
- [ ] AC-PA-02 encode turns each message into its frame string; the frame bytes are exact
  (segments joined by |, fields as key=value).
- [ ] AC-PA-03 round-trip holds both ways: encode(decode(frames)) == frames byte-for-byte and
  decode(encode(messages)) == messages.
- [ ] AC-PA-04 an empty value is legal (key=) and survives the round-trip; a frame with zero
  fields is legal.
- [ ] AC-PA-05 any malformed frame or message (bad TYPE case, field without =, bad key, value
  with = or |) prints exactly ERROR for the whole batch — never partial output.
- [ ] AC-PA-06 malformed top-level shape or unknown direction prints exactly ERROR.
