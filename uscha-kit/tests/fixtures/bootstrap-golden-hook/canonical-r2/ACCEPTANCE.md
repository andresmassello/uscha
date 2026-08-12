# ACCEPTANCE — the INV-GOLDEN PreToolUse guard

Behavioural requirements. Each is a property the finished guard must have; the specific inputs
that demonstrate them are the checker's, not stated here.

- [ ] AC-GH-01 the guard reads one JSON object from stdin and signals its verdict only through
  the process exit code: 0 to allow, 2 to block; a block also writes a short reason to stderr.
- [ ] AC-GH-02 a call whose effect is to create, edit, rename or delete a file whose name
  contains `.approved` is blocked; the marker is matched case-insensitively.
- [ ] AC-GH-03 a call that only reads a `.approved` file is allowed — reading field truth is
  legitimate.
- [ ] AC-GH-04 read-only tools (a file reader, text search, directory listing, notebook
  reader, web fetch/search) are always allowed, even when they name a `.approved` file; tool
  names are matched case-insensitively.
- [ ] AC-GH-05 for a shell/command tool the rule is default-deny: a command that names a
  `.approved` file and cannot be proven read-only is blocked — including output redirection, an
  in-place/output write flag, or a pipeline in which any later stage writes.
- [ ] AC-GH-06 for any other (including unknown, write-capable) tool, the marker `.approved`
  appearing anywhere in its arguments — at any nesting depth — blocks the call.
- [ ] AC-GH-07 the guard is fail-closed: input that is not valid JSON, or not the expected
  object shape, blocks; a guard that cannot prove a call safe never allows it.
