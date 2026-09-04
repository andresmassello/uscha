#!/usr/bin/env python3
"""Cross-vendor arm of the Diamond Bench: dispatch a BLIND compilation through the OpenAI
Codex CLI and stage the result as a `c-codex/` compilation the engine can validate.

Doctrine (ADR-016/017): this script is a DISPATCHER and a HARVESTER. It never judges a
compilation -- `qa_ledger.py compile-validate` does, fail-closed, and only a compilation that
exits 0 is promoted into the bench. A refused compilation is staged as `x-codex-REFUSED/`,
which the bench's `c-*` discovery cannot see, so a bad run can never quietly become evidence.

BLINDNESS is enforced by construction, not by asking:
  * the working directory handed to the model is an EMPTY temp dir OUTSIDE the repo;
  * the canonical package is INLINED in the prompt -- it never touches that disk;
  * the oracle is never rendered, and a mechanical leak audit re-checks that on the way out;
  * CODEX_HOME is an isolated directory holding only what auth needs, so no user AGENTS.md,
    memory, skill or rules file can reach the model (`--ignore-user-config` only stops
    config.toml from LOADING -- it says nothing about the rest of that directory).

The run contract and stack constraints handed to the model are lifted VERBATIM from the
entry's existing `c-opus/COMPILATION.json` `implementation_constraints` -- for SEVEN of the
twelve entries. That is the default and it is deliberate: it is what the Claude arms
compiled against, and an arm given different constraints is not a comparable arm, it is a
different experiment. The other five (see CANONICAL_CONTRACTS below: crud-store,
protocol-adapter, rest-handler, ui-render, worker) had c-opus constraints that were post-hoc
narration of that implementation rather than a run contract, so they carry a two-line
contract derived from their own canonical SPEC instead -- handing one arm's design decisions
to another vendor makes the second arm a transcription, not an independent compilation.
`tools/codex-arm/slots.json` records `source` PER ENTRY, so the asymmetry is inspectable.

WRITE MODES -- read this before changing the default:
  `tool`   the model creates the source file itself, as the historical Claude arms did.
  `return` the model returns the complete source inside its JSON and THIS script writes it.
On a machine whose administrator policy (e.g. C:/ProgramData/OpenAI/Codex/requirements.toml)
removes `never` from `allowed_approval_policies`, `codex exec` falls back to `on-request` and
then fails every write with "file change approval is not supported in exec mode" -- the model
cannot create a file at all. `return` is the default because it is the mode that works
without bypassing anybody's security policy; the deviation is recorded in the run report as
`write_mode` so no reader mistakes one arm's mechanics for the other's.
"""

import argparse
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
ENGINE = os.path.join(REPO, "uscha-kit", ".claude", "skills", "uscha-devloop", "qa_ledger.py")
DEFAULT_BENCH = os.path.join(REPO, "uscha-kit", "tests", "fixtures", "diamond-bench")
DEFAULT_OUT = os.path.join(REPO, "tools", ".codex-arm")
SLOTS = os.path.join(HERE, "codex-arm", "slots.json")

# gpt-5.6-* is refused by codex-cli 0.142.5 ("requires a newer version of Codex", HTTP 400),
# so the default is the newest slug this CLI can actually dispatch. --model overrides.
DEFAULT_MODEL = "gpt-5.5"
DEFAULT_EFFORT = "high"

# For these five entries the c-opus `implementation_constraints` read as post-hoc narration of
# that implementation ("isinstance(v, bool) is tested BEFORE ...", "cycle detection is
# iterative (explicit stack, DFS coloring)") rather than as a run contract. Lifting them would
# hand the cross-vendor arm one arm's DESIGN DECISIONS, and an arm handed another arm's design
# is not an independent compilation of the canonical package -- it is a transcription of it.
# So for these five the run contract is derived from the entry's own canonical SPEC.md
# "## Contract" section instead: the stack and file layout (the one fact the SPEC does not
# state, because the canonical package is stack-agnostic by construction) plus the I/O and exit
# contract the SPEC already fixes. Nothing here is a design choice; it is the same information
# the oracle harness needs to run the unit at all. Authored by hand from the SPEC, not
# extracted mechanically -- which is why slots.json records the provenance per entry and
# ADR-042 names it. The other seven entries keep their c-opus constraints, which already read
# as genuine one-line run contracts.
CANONICAL_CONTRACTS = {
    "crud-store": [
        "Pure Python 3.8+ standard library only; single file `source/impl.py`, run as "
        "`python impl.py`; no third-party packages, no filesystem, no network.",
        "Reads the WHOLE of stdin, prints the result to stdout, and ALWAYS exits 0 -- "
        "malformed input is signalled by printing exactly `ERROR`, never by a non-zero exit.",
    ],
    "protocol-adapter": [
        "Pure Python 3.8+ standard library only; single file `source/impl.py`, run as "
        "`python impl.py`; no third-party packages, no filesystem, no network.",
        "Reads the WHOLE of stdin, prints the result to stdout, and ALWAYS exits 0 -- "
        "malformed input is signalled by printing exactly `ERROR`, never by a non-zero exit.",
    ],
    "rest-handler": [
        "Pure Python 3.8+ standard library only; single file `source/impl.py`, run as "
        "`python impl.py`; no third-party packages, no filesystem, no network.",
        "Reads the WHOLE of stdin, prints the result to stdout, and ALWAYS exits 0 -- "
        "malformed input is signalled by printing exactly `ERROR`, never by a non-zero exit.",
    ],
    "ui-render": [
        "Pure Python 3.8+ standard library only; single file `source/impl.py`, run as "
        "`python impl.py`; no third-party packages, no filesystem, no network.",
        "Reads the WHOLE of stdin, prints the result to stdout, and ALWAYS exits 0 -- "
        "malformed input is signalled by printing exactly `ERROR`, never by a non-zero exit.",
    ],
    "worker": [
        "Pure Python 3.8+ standard library only; single file `source/impl.py`, run as "
        "`python impl.py`; no third-party packages, no filesystem, no network.",
        "Reads the WHOLE of stdin, prints the result to stdout, and ALWAYS exits 0 -- "
        "malformed input is signalled by printing exactly `ERROR`, never by a non-zero exit.",
    ],
}


# --------------------------------------------------------------------------- #
# engine helpers -- imported, never reimplemented: the IR seal is the engine's
# definition of "which IR was compiled", and a second implementation of it would
# be a second definition.
# --------------------------------------------------------------------------- #
def _engine():
    sys.dont_write_bytecode = True
    import importlib.util
    spec = importlib.util.spec_from_file_location("qa_ledger_xv", ENGINE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def _read_text(path):
    with open(path, encoding="utf-8-sig") as fh:
        return fh.read()


def _write_lf(path, text):
    """Every byte this script stages is UTF-8 without a BOM and LF-terminated. compile-validate
    hashes the EXACT bytes of a unit, so the newline policy is part of the contract."""
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


# --------------------------------------------------------------------------- #
# slots
# --------------------------------------------------------------------------- #
def emit_slots(bench):
    """Regenerate tools/codex-arm/slots.json from the committed c-opus compilations. The slot
    table is a COMMITTED artifact so the arm's inputs are inspectable without running it --
    the same reason PROMPT-TEMPLATE.md is committed (ADR-021)."""
    entries = {}
    for name in sorted(os.listdir(bench)):
        d = os.path.join(bench, name)
        ref = os.path.join(d, "c-opus", "COMPILATION.json")
        if not os.path.isdir(d) or not os.path.isfile(ref):
            continue
        c = json.loads(_read_text(ref))
        canon = os.path.join(d, "canonical")
        files = []
        for root, _dirs, fs in os.walk(canon):
            for f in sorted(fs):
                if f.endswith(".md"):
                    rel = os.path.relpath(os.path.join(root, f), canon)
                    files.append(rel.replace(os.sep, "/"))
        # SPEC / ACCEPTANCE / CONSTITUTION first, then any docs/adr/*.md
        head = [f for f in ("SPEC.md", "ACCEPTANCE.md", "CONSTITUTION.md") if f in files]
        canonical = CANONICAL_CONTRACTS.get(name)
        entries[name] = {
            "target_stack": c.get("target_stack"),
            "source_units": [u["unit"] for u in c.get("source") or []],
            "tests_units": [u["unit"] for u in c.get("tests") or []],
            "source": "canonical" if canonical else "c-opus constraints",
            "implementation_constraints": (canonical
                                           or c.get("implementation_constraints") or []),
            "canonical_files": head + sorted(f for f in files if f not in head),
        }
    doc = {
        "_generated_by": "tools/bench-compile-codex.py --emit-slots",
        "_contract": "the run contract and stack constraints handed to the cross-vendor arm. "
                     "Each entry records where its contract CAME FROM in `source`: "
                     "`c-opus constraints` means it was lifted VERBATIM from that entry's "
                     "c-opus implementation_constraints, so both arms compile against the same "
                     "constraints (ADR-021 scaffolding parity). The oracle is NEVER a slot.",
        "_residual": "RESOLVED in ADR-042. For five entries (crud-store, protocol-adapter, "
                     "rest-handler, ui-render, worker) the c-opus constraints read as post-hoc "
                     "narration of that implementation rather than as a run contract, and "
                     "lifting them verbatim would hand the cross-vendor arm one arm's design "
                     "decisions. Those five carry `source: canonical` instead: a two-line "
                     "contract authored from the entry's own canonical SPEC.md `## Contract` "
                     "section -- stack and file layout plus the I/O and exit contract, the "
                     "same information the oracle harness needs to run the unit at all, and no "
                     "design choice. The other seven (guard, parser, rate-limiter, "
                     "ledger-lite, scheduler, state-machine, transformer) already carried "
                     "genuine one-line run contracts and keep `source: c-opus constraints`.",
        "entries": entries,
    }
    _write_lf(SLOTS, json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    return doc


def load_slots():
    if not os.path.isfile(SLOTS):
        sys.stderr.write("no slot table at %s -- run --emit-slots first\n" % SLOTS)
        sys.exit(2)
    return json.loads(_read_text(SLOTS))["entries"]


# --------------------------------------------------------------------------- #
# prompt
# --------------------------------------------------------------------------- #
def ir_node_ids(bench, name):
    """The node ids of the entry's reference IR. They are handed to the model so that
    `unresolved_intent[].ir_region` names a REGION OF THE IR rather than a slug the compiler
    invented: compile-ingest content-addresses a UINT on (ir_region + decision), so a freeform
    region makes two compilers' report of the SAME gap two different gaps. The ids are derived
    from the canonical package the prompt already carries in full -- naming them leaks nothing
    the model cannot already read a few lines above."""
    try:
        with open(os.path.join(bench, name, "IR.json"), encoding="utf-8-sig") as fh:
            graph = json.load(fh)
    except (OSError, ValueError):
        return []
    return [n["id"] for n in (graph.get("nodes") or []) if n.get("id")]


def render_prompt(bench, name, slot, write_mode):
    canon_dir = os.path.join(bench, name, "canonical")
    parts = []
    units = slot["source_units"]
    targets = ", ".join(units)
    if write_mode == "tool":
        opener = ("You are an LLM COMPILER. Your FIRST action MUST be to create the file(s) "
                  "named below in the current working directory. Then return the JSON.")
        files_clause = ""
    else:
        opener = ("You are an LLM COMPILER. Do NOT create, edit or run any file: return the "
                  "complete source of the file(s) named below inside the JSON.")
        files_clause = (',\n "files":[{"path":"<unit>","content":"<the COMPLETE source of '
                        'that unit>"}]')
    parts.append(opener)
    parts.append(
        "BLIND: implement ONLY from this prompt. Do NOT read, search or list any file you did "
        "not create. Do NOT look for a spec, a test, an oracle or a reference implementation "
        "anywhere on this machine. No network.")
    parts.append("")
    parts.append("WRITE to exactly: %s" % targets)
    parts.append("RUN CONTRACT and STACK CONSTRAINTS (binding):")
    for c in slot["implementation_constraints"]:
        parts.append("- %s" % c)
    parts.append("Write ONLY the file(s) named above.")
    parts.append("")
    parts.append("CANONICAL PACKAGE (your only input):")
    canon_texts = []
    for rel in slot["canonical_files"]:
        text = _read_text(os.path.join(canon_dir, rel.replace("/", os.sep)))
        canon_texts.append(text)
        parts.append("--- %s ---" % rel)
        parts.append(text.rstrip("\n"))
    parts.append("")
    manifest_units = json.dumps(units)
    parts.append("Return ONLY this JSON (no prose, no fences):")
    parts.append('{"target_stack":"%s","implementation_constraints":["..."],'
                 '"source_units":%s,\n "tests_units":[],'
                 '"trace_manifest":[{"unit":"%s","implements":["<ids from the canonical '
                 'package>"]}],\n "unresolved_intent":[{"ir_region":"<id>","decision":"<the '
                 'choice you made>","rationale":"<why>"}]%s'
                 % (slot["target_stack"], manifest_units, units[0], files_clause))
    parts.append("}")
    parts.append("unresolved_intent NON-EMPTY and SPECIFIC (2-5 entries): each one a real "
                 "freedom the canonical package left you, not a restatement of it.")
    ids = ir_node_ids(bench, name)
    if ids:
        parts.append("Each ir_region MUST be exactly one of these ids from the canonical "
                     "package: %s" % ", ".join(ids))
    if write_mode == "tool":
        parts.append("Return the JSON only after writing the file(s).")
    return "\n".join(parts) + "\n", "\n".join(canon_texts)


def output_schema(slot, write_mode):
    unit_obj = {"type": "object", "additionalProperties": False,
                "required": ["unit", "implements"],
                "properties": {"unit": {"type": "string"},
                               "implements": {"type": "array", "items": {"type": "string"}}}}
    ui_obj = {"type": "object", "additionalProperties": False,
              "required": ["ir_region", "decision", "rationale"],
              "properties": {"ir_region": {"type": "string"},
                             "decision": {"type": "string"},
                             "rationale": {"type": "string"}}}
    props = {
        "target_stack": {"type": "string"},
        "implementation_constraints": {"type": "array", "items": {"type": "string"}},
        "source_units": {"type": "array", "items": {"type": "string"}},
        "tests_units": {"type": "array", "items": {"type": "string"}},
        "trace_manifest": {"type": "array", "items": unit_obj},
        "unresolved_intent": {"type": "array", "items": ui_obj},
    }
    if write_mode == "return":
        props["files"] = {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["path", "content"],
            "properties": {"path": {"type": "string"}, "content": {"type": "string"}}}}
    return {"type": "object", "additionalProperties": False,
            "required": sorted(props.keys()), "properties": props}


# --------------------------------------------------------------------------- #
# leak audit
# --------------------------------------------------------------------------- #
def oracle_strings(bench, name):
    """Every string VALUE the withheld oracle carries -- case names, payload values, expected
    values -- that is distinctive enough to be a fingerprint rather than a coincidence.

    Two exclusions, both paid for by a false positive on the first real run:
      * dict KEYS are the oracle harness's own vocabulary (`payload`, `expected_exit`), not
        the oracle's content, and `payload` is a variable name any implementation may pick;
      * a short bare word is not a fingerprint -- `pattern` appears in a case payload AND is
        the natural name of a parameter the spec itself describes. A leak looks like
        `bash-tee-pipeline-writes-golden` or `out.approved.json`: long, or carrying a
        separator that makes it a specific identifier rather than a word."""
    path = os.path.join(bench, name, "oracle", "ORACLE.json")
    out = set()

    def distinctive(s):
        return len(s) >= 6 and (len(s) >= 12 or any(c in s for c in "-./_ "))

    def walk(o):
        if isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
        elif isinstance(o, str) and distinctive(o):
            out.add(o)
    try:
        walk(json.loads(_read_text(path)))
    except (OSError, ValueError):
        return set()
    return out


def leaks(text, canonical_text, strings):
    """A leak is an oracle string present in TEXT and ABSENT from the canonical package. A
    string the canonical package already contains is not evidence of leakage -- it is the
    spec doing its job -- and flagging it would drown the real signal (the first naive
    version of this check reported dozens of such matches)."""
    return sorted(s for s in strings if s in text and s not in canonical_text)


# --------------------------------------------------------------------------- #
# dispatch
# --------------------------------------------------------------------------- #
def codex_bin():
    """The codex executable. On Windows `codex` on PATH is a `.CMD` shim, which CreateProcess
    cannot launch directly (WinError 2 with shell=False), so resolve the vendored `.exe` the
    shim wraps. CODEX_BIN overrides everything when the layout is not the npm one."""
    override = os.environ.get("CODEX_BIN")
    if override:
        return override
    import glob as _glob
    for cand in ("codex.exe", "codex"):
        found = shutil.which(cand)
        if found and os.path.splitext(found)[1].lower() in (".exe", ""):
            return found
        if found:
            root = os.path.dirname(found)
            hits = _glob.glob(os.path.join(root, "node_modules", "@openai", "codex",
                                           "node_modules", "@openai", "codex-*", "vendor",
                                           "*", "bin", "codex.exe"))
            if hits:
                return sorted(hits)[0]
    sys.stderr.write("codex executable not found -- set CODEX_BIN to its full path\n")
    sys.exit(2)


def build_command(work, run_dir, model, effort, codex_home):
    """The exact codex invocation. Flags verified against `codex exec --help` on 0.142.5:
    `--ask-for-approval` does NOT exist on this subcommand ("unexpected argument"), so the
    approval posture is expressed as `-c approval_policy=never` -- which an administrator
    `requirements.toml` may still override; the run report records what the CLI said."""
    return [
        codex_bin(), "exec",
        "--cd", work,
        "--skip-git-repo-check",
        "--ignore-user-config",
        "--ignore-rules",
        "--ephemeral",
        "--sandbox", "workspace-write",
        "--model", model,
        "-c", 'approval_policy="never"',
        "-c", 'model_reasoning_effort="%s"' % effort,
        "-c", "sandbox_workspace_write.network_access=false",
        "--output-schema", os.path.join(run_dir, "schema.json"),
        "--output-last-message", os.path.join(run_dir, "last.json"),
        "--color", "never",
        "--json", "-",
    ]


def isolated_home(out_dir):
    """A CODEX_HOME holding ONLY what auth needs. `--ignore-user-config` stops config.toml
    from loading and nothing else, so an AGENTS.md, a memory database or a skills directory in
    the real CODEX_HOME would still be in play. Isolation, not a flag, is what keeps the
    compilation blind.

    SCOPE of the assertion below, stated because it is narrower than it looks: it runs ONCE,
    at CREATION, and proves the directory this script builds holds auth.json and nothing
    else. The CLI then populates that home during dispatch 1 (config.toml, skills/.system,
    plugins/cache, a sqlite file), so it is NOT an invariant held across the run. What the
    vendor's own CLI writes there was inspected by hand for this run and holds no user
    AGENTS.md, memory or rules file -- a MANUAL check today, not a measured one."""
    home = os.path.join(out_dir, "codex-home")

    def _force(func, path, _exc):
        # copy2 carries the real auth.json's read-only bit over, and Windows refuses to
        # unlink a read-only file. ignore_errors would leave the directory standing and the
        # makedirs below would raise on the SECOND run -- after the first has already
        # dispatched, which is the worst possible moment to discover it.
        os.chmod(path, 0o600)
        func(path)

    if os.path.isdir(home):
        try:
            shutil.rmtree(home, onerror=_force)
        except OSError as exc:
            sys.stderr.write("cannot clear %s: %s\n" % (home, exc))
            sys.exit(2)
    os.makedirs(home)
    src = os.environ.get("CODEX_HOME") or os.path.join(os.path.expanduser("~"), ".codex")
    auth = os.path.join(src, "auth.json")
    if not os.path.isfile(auth):
        sys.stderr.write("no auth.json under %s -- run `codex login` yourself; this script "
                         "never prompts for credentials\n" % src)
        sys.exit(2)
    shutil.copy2(auth, os.path.join(home, "auth.json"))
    # the isolation is the load-bearing part, so it is ASSERTED, not assumed: anything other
    # than auth.json in this directory is a rules/memory/AGENTS.md file the model could read.
    leftover = sorted(f for f in os.listdir(home) if f != "auth.json")
    if leftover:
        sys.stderr.write("refusing: isolated CODEX_HOME %s is not isolated -- %s\n"
                         % (home, leftover))
        sys.exit(2)
    return home


def parse_events(path, work):
    """What the run actually did, read from the JSONL event stream: how many shell commands
    ran, whether anything reached outside the working directory, whether an approval or an
    auth error killed it."""
    info = {"shell_commands_executed": 0, "commands": [], "errors": [],
            "files_read_outside_workspace": [], "declined": 0, "usage": None,
            "thread_id": None, "file_changes": []}
    work_r = os.path.realpath(work).lower()
    try:
        lines = open(path, encoding="utf-8").read().splitlines()
    except OSError:
        return info
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("type") == "thread.started":
            info["thread_id"] = ev.get("thread_id")
        if ev.get("type") in ("error", "turn.failed"):
            info["errors"].append(str(ev.get("message") or ev.get("error")))
        item = ev.get("item") or {}
        if ev.get("type") == "turn.completed":
            info["usage"] = ev.get("usage")
        if ev.get("type") != "item.completed":
            continue
        if item.get("type") == "error":
            info["errors"].append(item.get("message"))
        elif item.get("type") == "command_execution":
            info["shell_commands_executed"] += 1
            cmd = item.get("command") or ""
            info["commands"].append({"command": cmd, "status": item.get("status"),
                                     "exit_code": item.get("exit_code")})
            if item.get("status") == "declined":
                info["declined"] += 1
            for tok in cmd.replace("\\\\", "\\").split():
                t = tok.strip('"\'').lower()
                if (len(t) > 3 and t[1:3] == ":\\") and not t.startswith(work_r):
                    info["files_read_outside_workspace"].append(tok.strip('"\''))
        elif item.get("type") == "file_change":
            for ch in item.get("changes") or []:
                info["file_changes"].append({"path": ch.get("path"),
                                             "kind": ch.get("kind"),
                                             "status": item.get("status")})
                p = str(ch.get("path") or "").lower()
                if p and not os.path.realpath(p).lower().startswith(work_r):
                    info["files_read_outside_workspace"].append(ch.get("path"))
    return info


def parse_last(path):
    """The model's returned JSON. Tolerant on purpose: --output-schema is a request, not a
    guarantee, and a run that came back fenced is still measurable -- but WHETHER the schema
    was honoured is recorded, because that is one of the facts the pilot exists to establish."""
    try:
        raw = _read_text(path)
    except OSError:
        return None, "absent", None
    stripped = raw.strip()
    try:
        return json.loads(stripped), "schema-honoured", raw
    except ValueError:
        pass
    body = stripped
    if body.startswith("```"):
        body = body.split("\n", 1)[1] if "\n" in body else ""
        if body.rstrip().endswith("```"):
            body = body.rstrip()[:-3]
    start, end = body.find("{"), body.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(body[start:end + 1]), "recovered-from-prose", raw
        except ValueError:
            pass
    return None, "unparseable", raw


# --------------------------------------------------------------------------- #
# staging
# --------------------------------------------------------------------------- #
def stage(eng, bench, name, slot, ret, work, staged, model, effort, ev, started, finished,
          write_mode, cli_version):
    """Write the c-codex candidate: the model's units, then a COMPILATION.json sealed with the
    engine's own `_compile_seal`. Refusals happen later, in compile-validate."""
    graph, errs = eng._load_ir_at(os.path.join(bench, name, "IR.json"))
    if graph is None or errs:
        return None, ["reference IR unusable: %s" % "; ".join(errs or ["absent"])]
    declared = ret.get("source_units") or slot["source_units"]
    problems = []
    written = []
    for unit in declared:
        text = None
        if write_mode == "return":
            for f in ret.get("files") or []:
                if f.get("path") in (unit, os.path.basename(unit)):
                    text = f.get("content")
                    break
        else:
            src = os.path.join(work, unit.replace("/", os.sep))
            if os.path.isfile(src):
                with open(src, "rb") as fh:
                    text = fh.read().decode("utf-8-sig")
        if text is None:
            problems.append("declared unit not produced: %s" % unit)
            continue
        text = text.replace("\r\n", "\n")
        if not text.endswith("\n"):
            text += "\n"
        dest = os.path.join(staged, unit.replace("/", os.sep))
        _write_lf(dest, text)
        written.append(unit)
    if not written:
        return None, problems or ["no source unit produced"]
    source = []
    for unit in written:
        with open(os.path.join(staged, unit.replace("/", os.sep)), "rb") as fh:
            source.append({"unit": unit, "sha256": _sha256_bytes(fh.read())})
    comp = {
        "schema_version": eng.COMPILE_SCHEMA,
        "canonical_ir": {"ir_hash": graph.get("_integrity"),
                         "schema_version": graph.get("schema_version")},
        "target_stack": ret.get("target_stack") or slot["target_stack"],
        "implementation_constraints": ret.get("implementation_constraints") or [],
        "source": source,
        "tests": [],
        "trace_manifest": [e for e in (ret.get("trace_manifest") or [])
                           if isinstance(e, dict)],
        "unresolved_intent": [e for e in (ret.get("unresolved_intent") or [])
                              if isinstance(e, dict)],
        "compilation_report": {
            "stack": ret.get("target_stack") or slot["target_stack"],
            "model": "codex",
            "model_version": "%s via codex-cli %s" % (model, cli_version),
            "timestamps": {"started": started, "finished": finished},
            "constraint_handling": "; ".join(ret.get("implementation_constraints") or []
                                             ) or "not declared by the compiler",
            "backend": {
                "vendor": "openai",
                "cli": "codex-cli %s" % cli_version,
                "model_slug": model,
                "reasoning_effort": effort,
                "sandbox": "workspace-write",
                "approval": "requested never; see run report for what the CLI applied",
                "write_mode": write_mode,
                "shell_commands_executed": ev["shell_commands_executed"],
                "files_read_outside_workspace": ev["files_read_outside_workspace"],
            },
        },
    }
    comp["_integrity"] = eng._compile_seal(comp)
    _write_lf(os.path.join(staged, "COMPILATION.json"),
              json.dumps(comp, indent=2, ensure_ascii=False) + "\n")
    return comp, problems


# --------------------------------------------------------------------------- #
# validate and place
# --------------------------------------------------------------------------- #
def validate_and_place(ir, staged, target_root, name, r2, source_leaks):
    """Run the ENGINE's compile-validate over a staged compilation and copy it where its
    verdict says it belongs: `c-codex/` (or `r2/c-codex/`) when the engine exits 0 and no
    oracle string leaked into the source, `x-codex-REFUSED/` otherwise.

    The asymmetry is the whole point (ADR-016/020). `bench` discovers compilations by the
    `c-*` prefix, so a refused one is INVISIBLE to the bench by construction -- it cannot
    quietly become evidence -- while still being on disk under a name that says what happened.
    This script never judges; it only places what the engine judged.

    Returns (status, dest, reason, validate_exit, validate_stdout)."""
    vout = subprocess.run(
        [sys.executable, ENGINE, "compile-validate", "--ir", ir,
         "--compilation", os.path.join(staged, "COMPILATION.json")],
        capture_output=True, text=True)
    sub_dir = os.path.join("r2", "c-codex") if r2 else "c-codex"
    if vout.returncode == 0 and not source_leaks:
        status, reason = "PROMOTED", None
        dest = os.path.join(target_root, name, sub_dir)
    else:
        status = "REFUSED"
        reason = ("compile-validate exit %d" % vout.returncode if vout.returncode
                  else "oracle strings leaked into the source")
        dest = os.path.join(target_root, name, "x-codex-REFUSED")
        _write_lf(os.path.join(staged, "VALIDATE-STDERR.txt"),
                  (vout.stdout or "") + "\n" + (vout.stderr or ""))
    if os.path.isdir(dest):
        shutil.rmtree(dest, ignore_errors=True)
    if not os.path.isdir(os.path.dirname(dest)):
        os.makedirs(os.path.dirname(dest))
    shutil.copytree(staged, dest)
    return status, dest, reason, vout.returncode, vout.stdout[-2000:]


# --------------------------------------------------------------------------- #
# one entry
# --------------------------------------------------------------------------- #
def run_entry(args, eng, name, slot, out_dir, home, cli_version):
    bench = args.bench
    rec = {"entry": name, "status": "PENDING", "write_mode": args.write_mode,
           "model": args.model, "effort": args.effort}
    prompt, canon_text = render_prompt(bench, name, slot, args.write_mode)
    rec["prompt_bytes"] = len(prompt.encode("utf-8"))
    rec["prompt_sha256"] = _sha256_bytes(prompt.encode("utf-8"))
    strings = oracle_strings(bench, name)
    rec["oracle_strings_checked"] = len(strings)
    rec["prompt_leaks"] = leaks(prompt, canon_text, strings)
    run_dir = os.path.join(out_dir, name)
    if os.path.isdir(run_dir):
        shutil.rmtree(run_dir, ignore_errors=True)
    os.makedirs(run_dir)
    _write_lf(os.path.join(run_dir, "PROMPT.txt"), prompt)
    _write_lf(os.path.join(run_dir, "schema.json"),
              json.dumps(output_schema(slot, args.write_mode), indent=2) + "\n")
    if rec["prompt_leaks"]:
        rec["status"] = "REFUSED"
        rec["reason"] = "oracle strings present in the prompt: %s" % rec["prompt_leaks"][:5]
        return rec
    if args.dry_run:
        rec["status"] = "DRY-RUN"
        return rec

    work = tempfile.mkdtemp(prefix="uscha-xv-")
    if os.path.realpath(work).lower().startswith(os.path.realpath(REPO).lower()):
        sys.stderr.write("refusing: temp workspace %s is inside the repo\n" % work)
        sys.exit(2)
    cmd = build_command(work, run_dir, args.model, args.effort, home)
    rec["command"] = subprocess.list2cmdline(cmd)
    env = dict(os.environ)
    env["CODEX_HOME"] = home
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    t0 = datetime.datetime.now()
    with open(os.path.join(run_dir, "PROMPT.txt"), "rb") as fin, \
            open(os.path.join(run_dir, "events.jsonl"), "wb") as fout, \
            open(os.path.join(run_dir, "stderr.txt"), "wb") as ferr:
        proc = subprocess.run(cmd, stdin=fin, stdout=fout, stderr=ferr, env=env, shell=False)
    rec["wall_seconds"] = round((datetime.datetime.now() - t0).total_seconds(), 1)
    finished = datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec["exit_code"] = proc.returncode
    ev = parse_events(os.path.join(run_dir, "events.jsonl"), work)
    rec["events"] = {k: ev[k] for k in ("shell_commands_executed", "declined", "usage",
                                        "thread_id", "files_read_outside_workspace",
                                        "file_changes", "errors")}
    joined = " ".join(str(e) for e in ev["errors"])
    if "401" in joined or "not logged in" in joined.lower() or "unauthorized" in joined.lower():
        sys.stderr.write("codex auth error, refusing to continue: %s\n" % joined[:400])
        sys.exit(2)
    ret, honoured, raw = parse_last(os.path.join(run_dir, "last.json"))
    rec["output_schema_honoured"] = honoured
    if ret is None:
        rec["status"] = "REFUSED"
        rec["reason"] = "no parseable JSON returned (%s); errors: %s" % (honoured, joined[:300])
        shutil.rmtree(work, ignore_errors=True)
        return rec

    leftovers = []
    for root, _d, fs in os.walk(work):
        for f in fs:
            leftovers.append(os.path.relpath(os.path.join(root, f), work).replace(os.sep, "/"))
    declared = set(ret.get("source_units") or slot["source_units"])
    rec["workspace_files"] = sorted(leftovers)
    rec["workspace_undeclared"] = sorted(f for f in leftovers if f not in declared)

    staged = os.path.join(run_dir, "staged")
    comp, problems = stage(eng, bench, name, slot, ret, work, staged, args.model,
                           args.effort, ev, started, finished, args.write_mode, cli_version)
    shutil.rmtree(work, ignore_errors=True)
    if comp is None:
        rec["status"] = "REFUSED"
        rec["reason"] = "; ".join(problems)
        return rec
    rec["staging_problems"] = problems

    body = "".join(_read_text(os.path.join(staged, u["unit"].replace("/", os.sep)))
                   for u in comp["source"])
    rec["source_leaks"] = leaks(body, canon_text, strings)

    status, dest, reason, vexit, vout = validate_and_place(
        os.path.join(bench, name, "IR.json"), staged, args.target_root or bench, name,
        args.r2, rec["source_leaks"])
    rec["validate_exit"] = vexit
    rec["validate_stdout"] = vout
    rec["status"] = status
    if reason:
        rec["reason"] = reason
    rec["destination"] = dest
    return rec


# --------------------------------------------------------------------------- #
def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--bench", default=DEFAULT_BENCH, help="the diamond-bench directory")
    p.add_argument("--entry", action="append", help="entry name (repeatable; default all)")
    p.add_argument("--r2", action="store_true", help="write r2/c-codex/ (second round)")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--effort", default=DEFAULT_EFFORT)
    p.add_argument("--write-mode", choices=("tool", "return"), default="return",
                   dest="write_mode")
    p.add_argument("--dry-run", action="store_true", help="render prompts, dispatch nothing")
    p.add_argument("--out", default=DEFAULT_OUT, help="run artifacts (gitignored)")
    p.add_argument("--target-root", default=None,
                   help="where c-codex/ is written; default the bench dir itself")
    p.add_argument("--emit-slots", action="store_true", help="regenerate the slot table")
    args = p.parse_args()

    if args.emit_slots:
        doc = emit_slots(args.bench)
        print("wrote %s (%d entries)" % (SLOTS, len(doc["entries"])))
        return 0

    slots = load_slots()
    names = args.entry or sorted(slots)
    unknown = [n for n in names if n not in slots]
    if unknown:
        sys.stderr.write("unknown entries: %s\n" % ", ".join(unknown))
        return 2

    eng = _engine()
    stamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    out_dir = os.path.join(args.out, stamp)
    os.makedirs(out_dir)
    cli_version = "unknown"
    try:
        cli_version = subprocess.run([codex_bin(), "--version"], capture_output=True,
                                     text=True).stdout.strip().split()[-1]
    except (OSError, IndexError):
        pass
    home = None if args.dry_run else isolated_home(args.out)

    records = []
    for name in names:
        rec = run_entry(args, eng, name, slots[name], out_dir, home, cli_version)
        records.append(rec)
        print("[%-16s] %-9s %s" % (
            name, rec["status"],
            rec.get("reason") or ("%ss, %d cmds, validate=%s"
                                  % (rec.get("wall_seconds"),
                                     (rec.get("events") or {}).get("shell_commands_executed", 0),
                                     rec.get("validate_exit"))
                                  if not args.dry_run
                                  else "%d bytes, leaks=%d" % (rec["prompt_bytes"],
                                                               len(rec["prompt_leaks"])))))
    report = {"generated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "codex_cli": cli_version, "model": args.model, "effort": args.effort,
              "write_mode": args.write_mode, "bench": args.bench,
              "target_root": args.target_root or args.bench,
              "dry_run": args.dry_run, "entries": records}
    path = os.path.join(out_dir, "RUN-REPORT.json")
    _write_lf(path, json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print("report: %s" % path)
    return 0 if all(r["status"] in ("PROMOTED", "DRY-RUN") for r in records) else 1


if __name__ == "__main__":
    sys.exit(main())
