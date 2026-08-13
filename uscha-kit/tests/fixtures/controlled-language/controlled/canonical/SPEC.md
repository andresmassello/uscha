# SPEC — the INV-GOLDEN PreToolUse guard (EARS + STE authoring)

This canonical package states the same requirements as the free-prose SPEC, written under EARS
requirement templates and STE authoring rules: one requirement per sentence, active voice, a
controlled vocabulary (guard, tool call, marker, block, allow, reader, writer), no ambiguous
pronouns, no synonyms for one concept. The behaviour is unchanged; only the authoring changes.

## Definitions

- The **guard** is a program. The agent host runs the guard before the host runs a tool call.
- The **marker** is the text `.approved`. The guard shall match the marker without regard to
  letter case.
- An **approved golden** is a file. The name of an approved golden contains the marker.
- A tool call **writes** a golden when the tool call creates the golden, edits the golden,
  renames the golden, or deletes the golden.
- A tool call **reads** a golden when the tool call obtains the content of the golden and the
  tool call does not write the golden.

## Verdict channel (ubiquitous requirements)

- The guard shall read one JSON object from standard input.
- The guard shall report one verdict through the process exit code.
- The guard shall exit with code 0 to allow the tool call.
- The guard shall exit with code 2 to block the tool call.
- When the guard blocks the tool call, the guard shall write one short reason to standard error.
- The guard shall match every tool name without regard to letter case.

## Read-only tools (state-driven)

- While the named tool is a recognised read-only tool, the guard shall allow the tool call.
- A recognised read-only tool is a file reader, a text search, a directory listing, a notebook
  reader, or a web fetch or web search.

## Golden protection (event-driven and unwanted-behaviour)

- When a tool call writes an approved golden, the guard shall block the tool call.
- When a tool call only reads an approved golden, the guard shall allow the tool call.

## Shell and command tools (default-deny)

- While the named tool is a shell or command tool, the guard shall read the command text from
  the tool arguments.
- The guard shall treat the command as a writer unless every part of the command is a
  recognised reader.
- If the command names an approved golden and the guard cannot prove the command is a reader by
  a visible signal, then the guard shall block the tool call.
- If the command names an approved golden and the command redirects output to a file, then the
  guard shall block the tool call.
- If the command names an approved golden and the command carries an in-place or output write
  flag, then the guard shall block the tool call.
- If the command names an approved golden and any stage of a pipeline or command sequence is a
  recognised writer, then the guard shall block the tool call.

## Unknown tools (unwanted-behaviour)

- If the named tool is not a recognised read-only tool and is not a shell or command tool, and
  the marker appears at any depth in the tool arguments, then the guard shall block the tool call.

## Fail-closed posture (unwanted-behaviour)

- If the input is not valid JSON, then the guard shall block the tool call.
- If the input is valid JSON and the input is not the expected object shape, then the guard
  shall block the tool call.
- If the guard cannot prove a tool call is a reader by a visible signal, then the guard shall
  block the tool call.

## Out of scope (state honestly; do not implement)

The guard inspects the tool call as text and structure only. The guard cannot obtain the real
filesystem effect of a command. An indirect write is out of the reach of the guard. An indirect
write is a write that a script performs, a write that a runtime name performs, a write that a
symlink performs, or a write that a child process performs. The guard shall not run a command.
The guard shall not resolve a symlink. The guard shall not inspect the content of a script. The
measured byte-level control for an indirect write is located elsewhere.
