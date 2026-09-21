#!/usr/bin/env python3
"""Anthropic arm of the Diamond Bench: dispatch a BLIND compilation through headless Claude
Code (`claude -p`) and stage the result as a `c-<alias>/` compilation the engine can validate.

WHY A SCRIPT (ADR-050). The three Claude arms `c-haiku/`, `c-sonnet/` and `c-opus/` were
compiled by hand in Aug 2026 and each recorded its `model`/`model_version` as the bare alias
handed to the API (`"haiku"`, `"sonnet"`, `"opus"`). What each alias resolved to on Anthropic's
backend that month was never captured and cannot be reconstructed (ADR-042 UNMEASURED item 8).
This dispatcher closes that gap for every FUTURE round: it re-runs a Claude arm by SCRIPT, and
it records the EXACT resolved model id the CLI reports for the run, next to the alias. The
alias stays in `compilation_report.model` so the bench's alphabetical model lettering is
unchanged (`{codex: M1, haiku: M2, opus: M3, sonnet: M4}`); the exact id goes in
`compilation_report.model_version` and `backend.model_slug`, which is exactly the provenance
the engine's compile seal deliberately does not enforce (qa_ledger.py COMPILE_SEALED comment).

Doctrine is ADR-016/017's, identical to the Codex arm (ADR-042): this script is a DISPATCHER
and a HARVESTER, never a judge. `qa_ledger.py compile-validate` judges, fail-closed. A
compilation that validates and leaks no oracle string is PROMOTED to the out dir the caller
names; a refused one is staged as `x-<alias>-REFUSED/`, which the bench's `c-*` discovery
cannot see, so a bad run can never quietly become evidence.

BLINDNESS is enforced by construction, not by asking:
  * the working directory handed to the model is an EMPTY temp dir OUTSIDE the repo;
  * the canonical package is INLINED in the prompt -- it never touches that disk;
  * the oracle is never rendered, and a mechanical leak audit re-checks the PROMPT before
    dispatch (a leak there refuses before the model is ever called) and the SOURCE after;
  * an isolated CLAUDE_CONFIG_DIR holds only what this script places there, so no user
    CLAUDE.md, memory, skill, plugin or MCP server in the real config dir reaches the model.

ISOLATION -- what is ENFORCED versus what is a LIMIT (stated because honesty is the point):
  * NO TOOLS is enforced by flags AND asserted by measurement. The dispatch passes
    `--restricted --tools "" --disallowed-tools "*" --strict-mcp-config --permission-prompts
    none`, which removes every built-in tool that runs code or reaches the filesystem/network
    and denies anything that would prompt; and `parse_events()` counts the `tool_use` blocks
    in the returned event stream and this script REFUSES if that count is not 0. That is a
    STRONGER guarantee than the Codex arm, which could only assert 0 shell commands post-hoc:
    here the tool surface is removed AND the empty count is proven from telemetry.
  * CONFIG ISOLATION uses an isolated `CLAUDE_CONFIG_DIR` asserted at CREATION to hold only
    what this script places there. As with the Codex arm's isolated CODEX_HOME, the CLI may
    populate that directory during the run; that it writes no user rules/memory there is a
    MANUAL check on a real round, not an invariant held across it -- named here, not left to
    read as mechanical. The empty cwd + the leak audit remain the load-bearing blindness
    guarantee, exactly as for the Codex arm.
  * The VENDOR SYSTEM PROMPT that Claude Code prepends is not removable from outside the CLI
    and is UNMEASURED, the same asymmetry ADR-042 lists for Codex.

WRITE MODES:
  `return` (default) the model is told to return the complete source inside a JSON that
           conforms to the schema handed to `--json-schema`, writing NO file itself; this
           script writes the returned `files[].content`. This is the mode that needs no write
           tool, so it composes with `--tools ""`. It mirrors the Codex arm's `return` mode, so
           the two arms are one-shot generators judged by a withheld oracle -- what the bench
           measures.
  `tool`   the model creates the source file itself. Requires the Write tool to be enabled
           (`--tools Write`), which relaxes the no-tools guarantee; recorded in `write_mode`.

THIS RELEASE LANDS THE TOOL, dry-run-proven, exactly as bench-compile-codex.py was first
landed. It does not spend money, does not run a live `claude -p` compilation, and does not
touch the frozen v1 `c-haiku/`, `c-sonnet/`, `c-opus/` records. `--dry-run` renders every
prompt, runs the leak audit, and writes nothing that dispatches. A real round -- the user
copying a validated staged run into `c-<alias>/` -- comes later, records the exact id, and is
what finally answers ADR-042 item 8.
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
ENGINE = os.path.join(REPO, "uscha-kit", ".claude", "skills", "uscha-devloop", "qa_ledger.py")
DEFAULT_BENCH = os.path.join(REPO, "uscha-kit", "tests", "fixtures", "diamond-bench")
DEFAULT_OUT = os.path.join(REPO, "tools", ".claude-arm")
# The run contract is VENDOR-NEUTRAL (target_stack, source_units, implementation_constraints,
# canonical_files), so this arm reads the SAME committed slot table the Codex arm regenerates.
# There is no second copy and no --emit-slots here: an arm that compiled against a different
# contract would not be a comparable arm (ADR-042 scaffolding parity). The Codex arm owns the
# --emit-slots path; this one reads what it committed.
SLOTS = os.path.join(HERE, "codex-arm", "slots.json")

MODEL_ALIASES = ("haiku", "sonnet", "opus")
DEFAULT_MODEL = "opus"
DEFAULT_EFFORT = "high"
# The CLI dispatched against when this was written. --cli-version overrides; a real run reads
# `claude --version` and records what it actually said.
DEFAULT_CLI_VERSION = "2.1.270"
# A hard dollar ceiling passed to the CLI (`--max-budget-usd`) so a misconfigured run cannot
# spend without bound. Advisory-generous per entry; --max-budget-usd overrides.
DEFAULT_BUDGET_USD = 1.0
# An exact resolved model id looks like `claude-opus-4-8` or `claude-opus-4-8-20260101`; a bare
# alias does not. Used only to LABEL where the id came from, never to gate.
_EXACT_ID_RE = re.compile(r"^claude-[a-z]+-\d")


# --------------------------------------------------------------------------- #
# engine helpers -- imported, never reimplemented: the IR seal is the engine's
# definition of "which IR was compiled", and a second implementation of it would
# be a second definition. (Same rationale as the Codex arm.)
# --------------------------------------------------------------------------- #
def _engine():
    sys.dont_write_bytecode = True
    import importlib.util
    spec = importlib.util.spec_from_file_location("qa_ledger_claude_arm", ENGINE)
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
def load_slots():
    if not os.path.isfile(SLOTS):
        sys.stderr.write("no slot table at %s -- run "
                         "`bench-compile-codex.py --emit-slots` first\n" % SLOTS)
        sys.exit(2)
    return json.loads(_read_text(SLOTS))["entries"]


# --------------------------------------------------------------------------- #
# prompt -- vendor-neutral and byte-identical to the Codex arm's, so the two arms compile
# against the same words and a prompt sha256 is comparable across vendors.
# --------------------------------------------------------------------------- #
def ir_node_ids(bench, name):
    """The node ids of the entry's reference IR, handed to the model so `unresolved_intent[].
    ir_region` names a REGION OF THE IR rather than an invented slug: compile-ingest
    content-addresses a UINT on (ir_region + decision), so a freeform region makes two
    compilers' report of the SAME gap two different gaps. The ids are derived from the canonical
    package the prompt already carries in full -- naming them leaks nothing new."""
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
# leak audit -- ported verbatim from the Codex arm (ADR-042): the same thresholds, so a leak is
# the same thing for both vendors' arms.
# --------------------------------------------------------------------------- #
def oracle_strings(bench, name):
    """Every string VALUE the withheld oracle carries that is distinctive enough to be a
    fingerprint rather than a coincidence. Two exclusions, both paid for by a false positive on
    the Codex arm's first real run: dict KEYS are the harness's own vocabulary, not the oracle's
    content; and a short bare word is not a fingerprint. A leak looks like
    `bash-tee-pipeline-writes-golden` or `out.approved.json`: long, or carrying a separator that
    makes it a specific identifier rather than a word."""
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
    """A leak is an oracle string present in TEXT and ABSENT from the canonical package. A string
    the canonical package already contains is not evidence of leakage -- it is the spec doing its
    job -- and flagging it would drown the real signal."""
    return sorted(s for s in strings if s in text and s not in canonical_text)


# --------------------------------------------------------------------------- #
# dispatch
# --------------------------------------------------------------------------- #
def claude_bin():
    """The claude executable. CLAUDE_BIN overrides everything. Otherwise resolve `claude` on
    PATH; on Windows the npm install is a `claude.cmd`/`claude.ps1` shim, which CreateProcess
    cannot launch directly with shell=False -- run_entry invokes through the shell on Windows
    when the resolved path is a shim, and native-installer binaries (`.exe`/no extension) run
    directly. (Not exercised under --dry-run: dispatch is the only caller.)"""
    override = os.environ.get("CLAUDE_BIN")
    if override:
        return override
    for cand in ("claude.exe", "claude"):
        found = shutil.which(cand)
        if found:
            return found
    # a .cmd/.ps1 shim only shows up under those names on Windows
    for cand in ("claude.cmd", "claude.ps1", "claude.bat"):
        found = shutil.which(cand)
        if found:
            return found
    sys.stderr.write("claude executable not found -- set CLAUDE_BIN to its full path\n")
    sys.exit(2)


def build_command(work_schema, model, effort, write_mode, budget):
    """The exact `claude -p` invocation. Every flag verified against `claude -p --help` on
    2.1.270:
      -p / --print              non-interactive.
      --output-format stream-json --verbose   the event stream parse_events() reads to prove
                                0 tool_use blocks AND the final `result` event; --verbose is
                                required for stream-json here.
      --model <alias>           the CLI resolves the alias; the run records what it resolved to.
      --effort <level>          low|medium|high|xhigh|max.
      --json-schema <schema>    structured-output validation; in `return` mode this is how the
                                model is told to return the source as JSON, WITHOUT a write tool.
      --restricted              removes the built-in tools that run code and ignores user /
                                project / local settings files.
      --tools ""                disables ALL built-in tools; --disallowed-tools "*" is the belt
                                to that suspenders. (`tool` mode re-enables Write only.)
      --strict-mcp-config       ignore every MCP server not passed on --mcp-config (none is).
      --permission-prompts none anything that would prompt is denied automatically.
      --max-budget-usd <amt>    a hard dollar ceiling; a runaway run stops instead of spending.
    The prompt itself is fed on STDIN (see run_entry), so it is not an argv element."""
    tools = "Write" if write_mode == "tool" else ""
    cmd = [
        claude_bin(), "-p",
        "--output-format", "stream-json",
        "--verbose",
        "--model", model,
        "--effort", effort,
        "--json-schema", json.dumps(work_schema, separators=(",", ":")),
        "--restricted",
        "--tools", tools,
        "--strict-mcp-config",
        "--permission-prompts", "none",
        "--max-budget-usd", str(budget),
    ]
    if write_mode != "tool":
        cmd += ["--disallowed-tools", "*"]
    return cmd


def isolated_config(out_dir):
    """A CLAUDE_CONFIG_DIR holding ONLY what this script places there. `--restricted` ignores
    user/project/local SETTINGS but says nothing about a user `~/.claude/CLAUDE.md`, a memory
    store, a skills directory or a plugin -- relocating the config dir to a synthetic one keeps
    all of that out of reach. The isolation, not any single flag, is what keeps the compilation
    blind.

    SCOPE of the assertion below, stated because it is narrower than it looks (mirrors the Codex
    arm's isolated_home): it runs ONCE, at CREATION, and proves the directory this script builds
    is empty of any user rules/memory/skill file. The CLI may populate that directory during a
    dispatch, so it is NOT an invariant held across the run. What the CLI writes there is a
    MANUAL check on a real round, not a measured one -- named here rather than left to read as
    mechanical."""
    home = os.path.join(out_dir, "claude-config")
    if os.path.isdir(home):
        shutil.rmtree(home, ignore_errors=True)
    os.makedirs(home)
    # asserted, not assumed: this script places nothing here, so anything present would be a
    # user rules/memory/skill/plugin file the model could reach.
    leftover = sorted(os.listdir(home))
    if leftover:
        sys.stderr.write("refusing: isolated CLAUDE_CONFIG_DIR %s is not isolated -- %s\n"
                         % (home, leftover))
        sys.exit(2)
    return home


def _content_blocks(ev):
    """The content blocks of an assistant event, tolerant of the two shapes the stream uses:
    {"type":"assistant","message":{"content":[...]}} and a bare {"content":[...]}."""
    msg = ev.get("message")
    if isinstance(msg, dict) and isinstance(msg.get("content"), list):
        return msg["content"]
    if isinstance(ev.get("content"), list):
        return ev["content"]
    return []


def parse_events(path):
    """What the run actually did, read from the stream-json event stream:
      * tool_use_blocks   how many tool calls the model made. The load-bearing measurement:
                          this arm ASSERTS it is 0, so `--write-mode return` under `--tools ""`
                          is a one-shot generator that touched no tool -- the same posture the
                          Codex arm proved with shell_commands_executed == 0.
      * model_reported    the exact model id the CLI names, hunted across the shapes the stream
                          uses (a `modelUsage` object keyed by exact id in the result event, a
                          `usage.model`, an init/result top-level `model`). Recorded WITH its
                          source so a reader knows which field answered.
      * result_text / structured_output   the model's returned JSON, for `return` mode.
      * errors, session_id, usage, cost.
    tool_use_blocks == 0 is not trusted from flags alone; it is proven here from telemetry."""
    info = {"tool_use_blocks": 0, "tool_names": [], "errors": [], "session_id": None,
            "usage": None, "total_cost_usd": None, "is_error": None, "subtype": None,
            "model_reported": None, "model_source": None, "result_text": None,
            "structured_output": None}
    try:
        lines = open(path, encoding="utf-8").read().splitlines()
    except OSError:
        return info

    def note_model(candidate, source):
        if info["model_reported"] is None and isinstance(candidate, str) and candidate:
            info["model_reported"] = candidate
            info["model_source"] = source

    def exact_from_usage(usage):
        # modelUsage / model_usage: keys are exact model ids in Claude Code's result.
        if isinstance(usage, dict):
            for key in ("modelUsage", "model_usage"):
                mu = usage.get(key)
                if isinstance(mu, dict):
                    for k in mu:
                        if isinstance(k, str) and _EXACT_ID_RE.match(k):
                            return k, key + " key"
                    for k in mu:  # any key, even if it does not match the exact pattern
                        return k, key + " key"
            if isinstance(usage.get("model"), str):
                return usage["model"], "usage.model"
        return None, None

    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        etype = ev.get("type")
        # a top-level modelUsage may ride on any event (init or result)
        mu_val, mu_src = exact_from_usage({"modelUsage": ev.get("modelUsage"),
                                           "model_usage": ev.get("model_usage")})
        if mu_val and _EXACT_ID_RE.match(mu_val):
            note_model(mu_val, mu_src)
        if etype == "system" and ev.get("subtype") == "init":
            # init `model` is often the alias; keep it only as a last resort
            if isinstance(ev.get("model"), str) and _EXACT_ID_RE.match(ev["model"]):
                note_model(ev["model"], "init.model")
        elif etype == "assistant":
            for b in _content_blocks(ev):
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    info["tool_use_blocks"] += 1
                    info["tool_names"].append(b.get("name"))
        elif etype in ("error", "system") and ev.get("subtype") in ("error", "api_error"):
            info["errors"].append(str(ev.get("message") or ev.get("error")))
        elif etype == "result":
            info["is_error"] = ev.get("is_error")
            info["subtype"] = ev.get("subtype")
            info["session_id"] = ev.get("session_id") or info["session_id"]
            info["usage"] = ev.get("usage")
            info["total_cost_usd"] = ev.get("total_cost_usd")
            info["result_text"] = ev.get("result")
            info["structured_output"] = ev.get("structured_output")
            if ev.get("is_error"):
                info["errors"].append(str(ev.get("result") or ev.get("error") or "result error"))
            # exact id from the result's per-model usage, then the result's own model field
            val, src = exact_from_usage(ev.get("usage") or {})
            if val and _EXACT_ID_RE.match(val):
                note_model(val, "result." + (src or "usage"))
            if isinstance(ev.get("model"), str) and _EXACT_ID_RE.match(ev["model"]):
                note_model(ev["model"], "result.model")
    return info


def parse_returned(ev):
    """The model's returned JSON for `return` mode. Prefer the CLI's own structured_output
    (validated against --json-schema); fall back to parsing the result text tolerantly -- a run
    that came back fenced is still measurable, and WHETHER the schema was honoured is recorded."""
    so = ev.get("structured_output")
    if isinstance(so, dict):
        return so, "schema-honoured"
    raw = ev.get("result_text")
    if not isinstance(raw, str):
        return None, "absent"
    body = raw.strip()
    try:
        return json.loads(body), "recovered-from-text"
    except ValueError:
        pass
    if body.startswith("```"):
        body = body.split("\n", 1)[1] if "\n" in body else ""
        if body.rstrip().endswith("```"):
            body = body.rstrip()[:-3]
    start, end = body.find("{"), body.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(body[start:end + 1]), "recovered-from-prose"
        except ValueError:
            pass
    return None, "unparseable"


# --------------------------------------------------------------------------- #
# staging
# --------------------------------------------------------------------------- #
def stage(eng, bench, name, slot, ret, work, staged, model_alias, model_slug, effort, ev,
          started, finished, write_mode, cli_version, tool_use_blocks):
    """Write the c-<alias> candidate: the model's units, then a COMPILATION.json sealed with the
    engine's own `_compile_seal`. Refusals happen later, in compile-validate.

    `compilation_report.model` is the ALIAS (so bench lettering is unchanged) and
    `model_version` is the EXACT resolved id -- the ADR-050 provenance the seal does not
    enforce. `backend` mirrors the Codex arm field-for-field with vendor "anthropic"."""
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
    # the exact id, if the CLI named one; otherwise honestly say it was not reported
    if model_slug and _EXACT_ID_RE.match(model_slug):
        model_version = "%s via claude-code %s" % (model_slug, cli_version)
        backend_slug = model_slug
    else:
        model_version = "%s (exact id not reported by claude-code %s)" % (model_alias,
                                                                          cli_version)
        backend_slug = model_slug or None
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
            "model": model_alias,
            "model_version": model_version,
            "timestamps": {"started": started, "finished": finished},
            "constraint_handling": "; ".join(ret.get("implementation_constraints") or []
                                             ) or "not declared by the compiler",
            "backend": {
                "vendor": "anthropic",
                "cli": "claude-code %s" % cli_version,
                "model_slug": backend_slug,
                "reasoning_effort": effort,
                "sandbox": "restricted-no-tools",
                "approval": "permission-prompts none; --restricted",
                "write_mode": write_mode,
                "tool_use_blocks": tool_use_blocks,
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
def validate_and_place(ir, staged, target_root, name, arm, r2, source_leaks):
    """Run the ENGINE's compile-validate over a staged compilation and copy it where its verdict
    says it belongs: `<arm>/` (or `r2/<arm>/`) when the engine exits 0 and no oracle string
    leaked into the source, `x-<alias>-REFUSED/` otherwise, where `arm` is `c-<alias>`.

    The asymmetry is the whole point (ADR-016/020): the bench discovers compilations by the
    `c-*` prefix, so a refused one is INVISIBLE to it by construction while still on disk under a
    name that says what happened. This script never judges; it only places what the engine
    judged. Returns (status, dest, reason, validate_exit, validate_stdout)."""
    vout = subprocess.run(
        [sys.executable, ENGINE, "compile-validate", "--ir", ir,
         "--compilation", os.path.join(staged, "COMPILATION.json")],
        capture_output=True, text=True)
    alias = arm[2:] if arm.startswith("c-") else arm
    sub_dir = os.path.join("r2", arm) if r2 else arm
    if vout.returncode == 0 and not source_leaks:
        status, reason = "PROMOTED", None
        dest = os.path.join(target_root, name, sub_dir)
    else:
        status = "REFUSED"
        reason = ("compile-validate exit %d" % vout.returncode if vout.returncode
                  else "oracle strings leaked into the source")
        dest = os.path.join(target_root, name, "x-%s-REFUSED" % alias)
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
def run_entry(args, eng, name, slot, out_dir, config_dir, cli_version):
    bench = args.bench
    arm = "c-%s" % args.model
    rec = {"entry": name, "status": "PENDING", "write_mode": args.write_mode,
           "model": args.model, "arm": arm, "effort": args.effort}
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
    schema = output_schema(slot, args.write_mode)
    _write_lf(os.path.join(run_dir, "PROMPT.txt"), prompt)
    _write_lf(os.path.join(run_dir, "schema.json"), json.dumps(schema, indent=2) + "\n")
    if rec["prompt_leaks"]:
        rec["status"] = "REFUSED"
        rec["reason"] = "oracle strings present in the prompt: %s" % rec["prompt_leaks"][:5]
        return rec
    if args.dry_run:
        rec["status"] = "DRY-RUN"
        return rec

    work = tempfile.mkdtemp(prefix="uscha-cla-")
    if os.path.realpath(work).lower().startswith(os.path.realpath(REPO).lower()):
        sys.stderr.write("refusing: temp workspace %s is inside the repo\n" % work)
        sys.exit(2)
    cmd = build_command(schema, args.model, args.effort, args.write_mode, args.budget)
    rec["command"] = subprocess.list2cmdline(cmd)
    env = dict(os.environ)
    env["CLAUDE_CONFIG_DIR"] = config_dir
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    # On Windows a `.cmd`/`.ps1`/`.bat` shim cannot be launched with shell=False.
    use_shell = os.name == "nt" and os.path.splitext(cmd[0])[1].lower() in (".cmd", ".ps1",
                                                                            ".bat")
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    t0 = datetime.datetime.now()
    with open(os.path.join(run_dir, "PROMPT.txt"), "rb") as fin, \
            open(os.path.join(run_dir, "events.jsonl"), "wb") as fout, \
            open(os.path.join(run_dir, "stderr.txt"), "wb") as ferr:
        proc = subprocess.run(subprocess.list2cmdline(cmd) if use_shell else cmd,
                              cwd=work, stdin=fin, stdout=fout, stderr=ferr, env=env,
                              shell=use_shell)
    rec["wall_seconds"] = round((datetime.datetime.now() - t0).total_seconds(), 1)
    finished = datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec["exit_code"] = proc.returncode
    ev = parse_events(os.path.join(run_dir, "events.jsonl"))
    rec["events"] = {k: ev[k] for k in ("tool_use_blocks", "tool_names", "session_id",
                                        "usage", "total_cost_usd", "is_error", "subtype",
                                        "model_reported", "model_source", "errors")}
    joined = " ".join(str(e) for e in ev["errors"])
    low = joined.lower()
    if "401" in joined or "not logged in" in low or "unauthorized" in low \
            or "invalid api key" in low or "authentication" in low:
        sys.stderr.write("claude auth error, refusing to continue: %s\n" % joined[:400])
        sys.exit(2)

    # the load-bearing isolation assertion: the model touched no tool. --tools "" removes them;
    # this proves the count from the event stream, and REFUSES if the stream disagrees.
    if ev["tool_use_blocks"] != 0:
        rec["status"] = "REFUSED"
        rec["reason"] = ("the dispatch made %d tool call(s) (%s) -- the no-tools guarantee did "
                         "not hold; refusing to stage a compilation that reached a tool"
                         % (ev["tool_use_blocks"], ev["tool_names"][:5]))
        shutil.rmtree(work, ignore_errors=True)
        return rec

    ret, honoured = parse_returned(ev)
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
                           ev["model_reported"], args.effort, ev, started, finished,
                           args.write_mode, cli_version, ev["tool_use_blocks"])
    shutil.rmtree(work, ignore_errors=True)
    if comp is None:
        rec["status"] = "REFUSED"
        rec["reason"] = "; ".join(problems)
        return rec
    rec["staging_problems"] = problems
    rec["model_version"] = comp["compilation_report"]["model_version"]

    body = "".join(_read_text(os.path.join(staged, u["unit"].replace("/", os.sep)))
                   for u in comp["source"])
    rec["source_leaks"] = leaks(body, canon_text, strings)

    status, dest, reason, vexit, vout = validate_and_place(
        os.path.join(bench, name, "IR.json"), staged, args.target_root or out_dir, name,
        arm, args.r2, rec["source_leaks"])
    rec["validate_exit"] = vexit
    rec["validate_stdout"] = vout
    rec["status"] = status
    if reason:
        rec["reason"] = reason
    rec["destination"] = dest
    return rec


# --------------------------------------------------------------------------- #
# run manifest -- the harvested shape, analogous to CODEX-ARM-RUN.json (ADR-042). Written to the
# out dir (gitignored), NOT into the fixture. A default run fills run1; a --r2 run merges its
# run2 blocks into any manifest already there, exactly as CODEX-ARM-RUN.json was assembled from
# two rounds. No prompt bytes are stored -- a prompt is the canonical package plus the run
# contract in slots.json, both committed, so the sha256 is re-derivable.
# --------------------------------------------------------------------------- #
def update_manifest(path, args, cli_version, records, generated):
    man = {}
    if os.path.isfile(path):
        try:
            man = json.loads(_read_text(path))
        except ValueError:
            man = {}
    man.setdefault("_generated_by", "tools/bench-compile-claude.py (ADR-050)")
    man["_contract"] = (
        "The Anthropic arm's run record. `model` is the ALIAS handed to the CLI (so the bench's "
        "model lettering is unchanged); `model_slug` is the EXACT id the CLI reported for the "
        "run -- the provenance ADR-042 item 8 said future rounds must capture. No prompt bytes "
        "are stored: a prompt is the canonical package (committed beside the fixture) plus the "
        "run contract in tools/codex-arm/slots.json, so the sha256 is re-derivable -- "
        "`bench-compile-claude.py --dry-run` re-renders it.")
    man["vendor"] = "anthropic"
    man["cli"] = "claude-code %s" % cli_version
    man["model"] = args.model
    man["reasoning_effort"] = args.effort
    man["write_mode"] = args.write_mode
    man["sandbox"] = "restricted-no-tools"
    man["dry_run"] = args.dry_run
    which = "run2" if args.r2 else "run1"
    man["%s_generated" % which] = generated
    entries = man.setdefault("entries", {})
    slug = None
    for r in records:
        e = entries.setdefault(r["entry"], {})
        e["prompt_sha256"] = r.get("prompt_sha256")
        e["prompt_bytes"] = r.get("prompt_bytes")
        e["oracle_strings_checked"] = r.get("oracle_strings_checked")
        if args.dry_run:
            e.setdefault(which, None)
            continue
        block = {"status": r.get("status"), "wall_seconds": r.get("wall_seconds"),
                 "tool_use_blocks": (r.get("events") or {}).get("tool_use_blocks"),
                 "validate_exit": r.get("validate_exit"),
                 "output_schema_honoured": r.get("output_schema_honoured"),
                 "model_version": r.get("model_version"),
                 "model_slug": (r.get("events") or {}).get("model_reported")}
        e[which] = block
        slug = slug or (r.get("events") or {}).get("model_reported")
    man["model_slug"] = slug if slug else man.get("model_slug")
    # totals over what is on record now
    tot = {"tool_use_blocks": 0, "refused": 0, "promoted_round1": 0, "promoted_round2": 0}
    for e in entries.values():
        for rk, pk in (("run1", "promoted_round1"), ("run2", "promoted_round2")):
            b = e.get(rk)
            if isinstance(b, dict):
                if b.get("status") == "PROMOTED":
                    tot[pk] += 1
                elif b.get("status") == "REFUSED":
                    tot["refused"] += 1
                tot["tool_use_blocks"] += (b.get("tool_use_blocks") or 0)
    man["totals"] = tot
    _write_lf(path, json.dumps(man, indent=2, ensure_ascii=False) + "\n")
    return path


# --------------------------------------------------------------------------- #
def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--bench", default=DEFAULT_BENCH, help="the diamond-bench directory")
    p.add_argument("--entry", action="append", help="entry name (repeatable; default all)")
    p.add_argument("--r2", action="store_true", help="write r2/c-<alias>/ (second round)")
    p.add_argument("--model", default=DEFAULT_MODEL, choices=MODEL_ALIASES,
                   help="the model ALIAS; the arm dir is c-<alias> and the exact id is recorded")
    p.add_argument("--effort", default=DEFAULT_EFFORT,
                   choices=("low", "medium", "high", "xhigh", "max"))
    p.add_argument("--write-mode", choices=("tool", "return"), default="return",
                   dest="write_mode")
    p.add_argument("--budget", type=float, default=DEFAULT_BUDGET_USD,
                   help="hard --max-budget-usd ceiling per dispatch")
    p.add_argument("--cli-version", default=None,
                   help="override the recorded CLI version (default: `claude --version`)")
    p.add_argument("--dry-run", action="store_true", help="render prompts, dispatch nothing")
    p.add_argument("--out", default=DEFAULT_OUT, help="run artifacts (gitignored)")
    p.add_argument("--target-root", default=None,
                   help="where c-<alias>/ is written; default the out dir (NOT the fixture)")
    args = p.parse_args()

    slots = load_slots()
    names = args.entry or sorted(slots)
    unknown = [n for n in names if n not in slots]
    if unknown:
        sys.stderr.write("unknown entries: %s\n" % ", ".join(unknown))
        return 2

    eng = _engine()
    cli_version = args.cli_version or DEFAULT_CLI_VERSION
    if not args.cli_version:
        try:
            out = subprocess.run([claude_bin(), "--version"], capture_output=True,
                                 text=True).stdout.strip()
            # `2.1.270 (Claude Code)` -> `2.1.270`
            cli_version = out.split()[0] if out else DEFAULT_CLI_VERSION
        except (OSError, IndexError):
            pass
    stamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    out_dir = os.path.join(args.out, stamp)
    os.makedirs(out_dir)
    config_dir = None if args.dry_run else isolated_config(args.out)

    records = []
    for name in names:
        rec = run_entry(args, eng, name, slots[name], out_dir, config_dir, cli_version)
        records.append(rec)
        print("[%-16s] %-9s %s" % (
            name, rec["status"],
            rec.get("reason") or ("%ss, tools=%d, validate=%s, %s"
                                  % (rec.get("wall_seconds"),
                                     (rec.get("events") or {}).get("tool_use_blocks", 0),
                                     rec.get("validate_exit"), rec.get("model_version"))
                                  if not args.dry_run
                                  else "%d bytes, leaks=%d" % (rec["prompt_bytes"],
                                                               len(rec["prompt_leaks"])))))
    generated = datetime.datetime.now(datetime.timezone.utc).isoformat()
    report = {"generated": generated, "claude_cli": cli_version, "model": args.model,
              "effort": args.effort, "write_mode": args.write_mode, "bench": args.bench,
              "target_root": args.target_root or out_dir, "dry_run": args.dry_run,
              "entries": records}
    rpath = os.path.join(out_dir, "RUN-REPORT.json")
    _write_lf(rpath, json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    mpath = update_manifest(os.path.join(args.out, "CLAUDE-ARM-RUN.json"), args, cli_version,
                            records, generated)
    print("report: %s" % rpath)
    print("manifest: %s" % mpath)
    return 0 if all(r["status"] in ("PROMOTED", "DRY-RUN") for r in records) else 1


if __name__ == "__main__":
    sys.exit(main())
