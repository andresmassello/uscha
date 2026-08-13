# ACCEPTANCE — the INV-GOLDEN PreToolUse guard (EARS + STE)

- [ ] AC-GH-01 the guard shall read one JSON object from standard input and shall report its
  verdict through the process exit code: the guard shall exit 0 to allow and shall exit 2 to
  block; when the guard blocks, the guard shall write one short reason to standard error.
- [ ] AC-GH-02 when a tool call creates, edits, renames, or deletes a file whose name contains
  the marker, the guard shall block the call; the guard shall match the marker without regard to
  letter case.
- [ ] AC-GH-03 when a tool call only reads a file whose name contains the marker, the guard shall
  allow the call.
- [ ] AC-GH-04 while the named tool is a recognised read-only tool, the guard shall allow the
  call even when the arguments name a file that contains the marker; the guard shall match the
  tool name without regard to letter case.
- [ ] AC-GH-05 while the named tool is a shell or command tool, the guard shall apply default-deny:
  if the command names a file that contains the marker and the guard cannot prove the command is
  a reader by a visible signal, then the guard shall block the call, including on output
  redirection, on an in-place or output write flag, and on a pipeline whose stage is a writer.
- [ ] AC-GH-06 if the named tool is any other tool and the marker appears at any depth in the
  arguments, then the guard shall block the call.
- [ ] AC-GH-07 the guard shall fail closed: if the input is not valid JSON, or the input is not
  the expected object shape, then the guard shall block the call.
