# SPEC — the INV-GOLDEN PreToolUse guard (Diamond M4 bootstrap subsystem, round 2)

This is the canonical package for a bounded subsystem: the guard that enforces
`INV-GOLDEN-01`. It is the *only* input a compiler receives. It describes the REQUIRED
behaviour and its intent — not an implementation, and not any test case.

> **Round-2 note (provenance, not a compiler instruction):** round 1 revealed an S-gap —
> three independent compilers all blocked interpreter verbs (`python`/`node`) writing a golden,
> where the canonical system allows them. The "Interpreters and shells are readers" and
> "pipelines" paragraphs below make the previously-implicit boundary explicit. Nothing else
> changed.

## What the subsystem is

A **PreToolUse guard**: a small program an agent host runs *before* it executes a tool call,
to decide whether that call may proceed. It reads one JSON object describing the pending tool
call on standard input, and communicates its verdict entirely through its **process exit
code**:

- **exit 0 — ALLOW.** The tool call may proceed.
- **exit 2 — BLOCK.** The tool call must not proceed. A short human-readable explanation of
  why is written to standard error.

No other exit code is part of the contract.

## The input

A single JSON object on stdin. The two fields the guard cares about:

- `tool_name` — a string naming the tool about to run (e.g. `"Bash"`, `"Write"`, `"Edit"`,
  `"Read"`, or any other tool the host supports, including tools this guard has never heard of).
- `tool_input` — an object holding that tool's arguments. Its shape depends on the tool; for a
  shell tool it carries the command line under `command`; for others it may carry file paths,
  content, or arbitrary nested arguments.

Tool names must be matched **case-insensitively** (`"Bash"`, `"bash"`, `"BASH"` are the same
tool).

## What must be protected

An **approved golden** is field truth a human has signed off on. A file is an approved golden
when its name contains the marker **`.approved`** (for example `entry.approved.json`,
`snapshot.approved`, `a/b/case.APPROVED.txt`). The marker match is **case-insensitive**,
because the filesystems this runs on (Windows, macOS) are.

The invariant (`INV-GOLDEN-01`): **an agent may create, edit, rename or delete an approved
golden only never — a human is the sole author of that file.** Reading an approved golden is
legitimate and must be allowed: the tooling that compares against a golden has to read it.

So the guard's whole job is a single distinction on any tool call that touches a `.approved`
file: **is this call going to WRITE (create / modify / rename / delete) it, or only READ it?**
Writes are blocked; reads pass.

## The decision, by tool kind

**Read-only tools.** Some tools cannot write by their nature — a file reader, a text search, a
directory listing, a web fetch/search, a notebook reader. A call to one of these is always
allowed, even when it names a `.approved` file: reading field truth is the point. The guard
recognises this family of read-only tools by name.

**A shell / command tool** (e.g. `Bash`). Its `command` string can do anything, so the rule is
a **default-deny** one: block the call when the command *both* names a `.approved` file *and*
cannot be shown to be read-only. Treat the command as a WRITE unless every part of it is a
recognised read-only operation. In particular, the following are writes even when the command
superficially begins with a "reader":

- any **output redirection** (a command that redirects its output to a file can create or
  overwrite a golden — `read-a-golden > another.approved` still writes one);
- an in-place / output **write flag** on an otherwise-reading tool (the flags editors and
  formatters use to write their result back out instead of to the screen);
- a **pipeline or command sequence** in which *any* stage is a writer — it is not enough for
  the command to *start* with a reader; a later stage that writes a golden must still block
  (a value piped into a tee-like writer writes a file).

When in doubt about a *visible* writing path, block. A guard that opens because it could not
prove the call safe is not a guard.

**Interpreters and shells are readers for this guard.** A general-purpose interpreter or shell
verb — `python`, `node`, `ruby`, `perl`, `bash`, `sh` and the like — invoked **without an
output redirection and without a write flag** is treated as a **read-only** operation and is
**NOT blocked**, even when its arguments name a `.approved` file. Any write it performs happens
through a script or an inline expression whose contents the guard cannot inspect — an
**indirect write**, which is out of scope by design (see the final section). Blocking it would
be guessing at an effect the guard cannot see, and the guard does not guess. The guard blocks
the **visible** writing paths — a redirection, a write flag, or a recognised writer verb such
as `tee`, `cp`, `mv`, `rm` — not the opaque ones. This is a deliberate boundary, not an
oversight: the measured byte-level control for indirect writes lives elsewhere.

**Pipelines.** Being a pipeline is not itself a reason to block. A pipeline every stage of
which is a reader — `cat x.approved | grep foo` — is **allowed**. A pipeline blocks only when a
stage is a recognised writer, or the command carries a redirection or a write flag. Do not
block a command merely because it contains a `|`.

**Any other tool** — including a write-capable tool the guard has never heard of. Here the
guard cannot reason about semantics, so it is conservative: if the marker `.approved` appears
**anywhere** in that tool's arguments (at any depth of the arguments object — nested objects,
lists, strings), block the call. An unknown tool must not slip a golden write through merely by
being unknown.

## Posture: fail-closed

The guard defends field truth, so it fails **closed**, never open:

- If the input on stdin is **not valid JSON**, block. A guard that cannot read its input cannot
  prove the call is safe.
- If the input is valid JSON but **not the expected object shape**, block.
- If a call cannot be proven read-only *by a visible path* — that is, a recognised writer, a
  redirection, or a write flag — block. (An interpreter/shell verb with none of those visible
  writing signals is a reader, per the section above, not a "cannot prove" case.)

A guard that allows when it is confused about a *visible* writing path silently disables
itself; that is the one failure this subsystem must never have.

## Out of scope (state honestly; do not implement)

This guard inspects the tool call as **text/structure only**. It is a guardrail against
accident and casual shortcut, not a sandbox: it cannot know a command's real filesystem
effects, so an *indirect* write (a script whose contents it never sees, a filename assembled at
runtime from pieces, a symlink, a child process, an interpreter expression) is out of its reach
**by design** — and therefore **not blocked**. Do not attempt to execute commands, resolve
symlinks, or inspect script contents to close that gap — the measured byte-level control lives
elsewhere. This subsystem's whole responsibility is the text/structure decision described
above, done correctly and fail-closed.
