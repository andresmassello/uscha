#!/usr/bin/env python3
"""
qa_ledger.py — Deterministic measurement + run ledger for the dev-loop orchestrator.

This script owns everything that MUST be exact and reproducible:
  - line coverage      (Maven/JaCoCo XML, Flutter/lcov)
  - test counts        (Surefire/Failsafe XML, Flutter best-effort)
  - source line counts (production vs test, per language)
  - the per-iteration findings log (reported / fixed / deferred / suppressed)
  - the final retrospective summary

Judgment calls (is the loop converged? is it oscillating? must we escalate?) are
made by the dev-loop SKILL reading this data. This script only exposes ADVISORY
helpers for those (`converged`, `oscillation`) so the agent has a deterministic
starting point — but the agent makes the call.

Stdlib only. Python 3.8+.

Usage (see `--help` on each subcommand):
  qa_ledger.py init        --config uscha.config.json [--out QA-LEDGER.json]
  qa_ledger.py snapshot    --repo backend-api    [--phase pre|post]
  qa_ledger.py check-coverage --repo backend-api [--threshold 60]   # exit 0 >=, 1 <
  qa_ledger.py log-step    --repo backend-api --tool code-review --iteration 1 \
                           --reported 12 --gated-reported 4 --fixed 9 \
                           --deferred 2 --suppressed 1 --tests-passed true \
                           --files-changed 7 [--fingerprint a,b,c] [--note "..."]
  qa_ledger.py converged   --repo backend-api --tools-per-cycle 3
  qa_ledger.py oscillation --repo backend-api --tool code-review
  qa_ledger.py escalate    --repo backend-api --reason "cap hit without convergence"
  qa_ledger.py resolve-escalation --repo backend-api [--note "human reviewed and closed"]
  qa_ledger.py summary     [--json]
  qa_ledger.py readiness   [--acceptance ACCEPTANCE.md] [--json]
  qa_ledger.py execution-policy [--phase qa] [--json]
  qa_ledger.py ingest-gate --repo backend-api --iteration 1 [--combined]
  qa_ledger.py ingest-gate --repo data-lib --iteration 1 \
                           [--ruff reports/ruff.json --mypy reports/mypy.txt]
  qa_ledger.py log-gate    --repo backend-api --iteration 1 --kind golden-diff \
                           --verdict pass|fail|not-run [--count N] [--note "..."]
  qa_ledger.py flag-blocker --repo backend-api --kind constitution --note "INV-XX breached" \
                           [--resolve]
  qa_ledger.py production-finding --repo backend-api --severity HIGH --title "..." --evidence "..."
  qa_ledger.py spec-doubt --repo backend-api --kind spec-wrong --note "..." --evidence "..."
  qa_ledger.py spec-change-request --repo backend-api --source SD-001 --requested-change "..." --evidence "..."
  qa_ledger.py rebuild --mode baseline --config uscha.config.json [--out REBUILD-BASELINE.json]
  qa_ledger.py rebuild --mode compare  --baseline REBUILD-BASELINE.json [--json]
  qa_ledger.py simplicity-check --diff changes.diff [--config uscha.config.json] [--json]
  qa_ledger.py simplicity-check --from-git --base main
  qa_ledger.py pit-check --report target/pit-reports/*/mutations.xml [--min-score 60] [--json]
  qa_ledger.py gate-check --from-git --base main [--strict] [--json]
  qa_ledger.py spec-check --spec SPEC.md [--spec ACCEPTANCE.md] [--strict] [--json]
  qa_ledger.py golden-diff [--dir .] [--labels golden-labels.json] [--json]
"""

import argparse
import ast
import glob
import hashlib
import json
import math
import os
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

DEFAULT_LEDGER = "QA-LEDGER.json"

# Directories never counted as source.
SKIP_DIRS = {
    "target", "build", ".git", ".idea", ".gradle", "node_modules",
    ".dart_tool", "out", "bin", "dist", ".mvn", "generated", "generated-sources",
    ".venv", "venv", ".tox", "__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache",
    "coverage", ".next", ".turbo",
    "vendor", "testdata",
    "obj", "TestResults",
    "cmake-build-debug", "cmake-build-release", "_deps",
}

SOURCE_EXT = {
    "maven": {".java", ".kt"},
    "flutter": {".dart"},
    "python": {".py"},
    "node": {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"},
    "go": {".go"},
    "rust": {".rs"},
    "dotnet": {".cs"},
    "cpp": {".cpp", ".cc", ".cxx", ".c", ".h", ".hpp", ".hh", ".hxx"},
    "gradle": {".kt", ".kts", ".java"},
    "swift": {".swift"},
    "generic": {".java", ".kt", ".dart", ".py", ".ts", ".js", ".go", ".rs", ".cs",
                ".cpp", ".swift"},
}


# --------------------------------------------------------------------------- #
# ledger io
# --------------------------------------------------------------------------- #
# Reports come from the user's build, not from us, and the engine is stdlib-only by contract --
# `defusedxml` is not available. A byte ceiling is the honest mitigation for the realistic
# failure (a runaway or hostile report exhausting memory on the operator's own machine). It is
# NOT protection against a determined attacker: entity expansion inside the ceiling still
# expands. SECURITY.md says so rather than implying the parser is hardened.
MAX_REPORT_BYTES = 64 * 1024 * 1024      # 64 MB: orders of magnitude above any real JUnit run


class ReportTooLarge(Exception):
    pass


def _parse_xml(source):
    """ET.parse with a size ceiling. Accepts a path or an open binary/text file object."""
    if hasattr(source, "read"):
        head = source.read(MAX_REPORT_BYTES + 1)
        if len(head) > MAX_REPORT_BYTES:
            raise ReportTooLarge("report exceeds %d bytes" % MAX_REPORT_BYTES)
        if isinstance(head, bytes):
            return ET.ElementTree(ET.fromstring(head))
        return ET.ElementTree(ET.fromstring(head))
    try:
        size = os.path.getsize(str(source))
    except OSError:
        size = 0
    if size > MAX_REPORT_BYTES:
        raise ReportTooLarge("%s exceeds %d bytes" % (source, MAX_REPORT_BYTES))
    return ET.parse(str(source))


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _integrity_hash(data):
    """sha256 canonico del contenido SIN el campo integrity (orden de claves
    normalizado: el hash no depende de como quedo ordenado el dict)."""
    body = {k: v for k, v in data.items() if k != "integrity"}
    blob = json.dumps(body, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _load(path):
    """Carga blindada (kit 1.13.0, Topic 34: los recursos compartidos mutables
    incluyen ARCHIVOS). JSON corrupto/truncado = hecho bloqueante con mensaje
    de recuperacion, no un traceback. Si el archivo trae campo integrity
    (escrito por _save >=1.13.0), el checksum se VERIFICA: una mutacion externa
    o escritura parcial bloquea — todo 'measured beats narrated' se apoya en
    este archivo. Archivos legacy sin integrity cargan sin verificar
    (adopcion incremental, no rotura retroactiva)."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        raise SystemExit(
            f"[qa_ledger] {path} corrupto (JSON invalido: {exc}). Es un artefacto "
            f"fuente-de-verdad del loop — restauralo desde git "
            f"(`git checkout -- {path}`) o desde el ultimo backup; no lo edites a mano.")
    if isinstance(data, dict) and "integrity" in data:
        want = (data.get("integrity") or {}).get("sha256")
        got = _integrity_hash(data)
        if want != got:
            raise SystemExit(
                f"[qa_ledger] {path} NO pasa el checksum de integridad "
                f"(esperado {str(want)[:12]}…, calculado {got[:12]}…): fue mutado "
                f"fuera de qa_ledger o quedo a medio escribir. Restauralo desde git; "
                f"si la edicion externa fue deliberada y la aceptas, borra el campo "
                f"'integrity' del JSON (acto humano explicito).")
    return data


def _save(path, data):
    data["updated_at"] = _now()
    # el hash excluye 'integrity' — calcularlo antes o despues de asignar da igual
    data["integrity"] = {"sha256": _integrity_hash(data)}
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def _repo_node(ledger, name):
    if name == "integration":
        return ledger["integration"]
    if name not in ledger["repos"]:
        raise SystemExit(f"[qa_ledger] unknown repo '{name}'. Run `init` first or check the config.")
    return ledger["repos"][name]


def _repo_cfg(ledger, name):
    for r in ledger["config"].get("repos", []):
        if r["name"] == name:
            return r
    raise SystemExit(f"[qa_ledger] no config entry for repo '{name}'.")


# --------------------------------------------------------------------------- #
# measurement: coverage
# --------------------------------------------------------------------------- #
def _jacoco_line_counter(xml_path):
    """Return (missed, covered) for the report-level LINE counter."""
    try:
        root = _parse_xml(xml_path).getroot()
    except ET.ParseError:
        return 0, 0
    for c in root.findall("counter"):
        if c.get("type") == "LINE":
            return int(c.get("missed", 0)), int(c.get("covered", 0))
    return 0, 0


def maven_coverage(repo_path):
    """
    Prefer an aggregate report if present, else sum per-module reports.
    Returns dict {covered, missed, pct}.
    """
    aggregate = glob.glob(os.path.join(repo_path, "**", "target", "site",
                                       "jacoco-aggregate", "jacoco.xml"),
                          recursive=True)
    if aggregate:
        files = aggregate
    else:
        files = glob.glob(os.path.join(repo_path, "**", "target", "site",
                                       "jacoco", "jacoco.xml"),
                          recursive=True)
    missed = covered = 0
    for f in files:
        m, c = _jacoco_line_counter(f)
        missed += m
        covered += c
    total = missed + covered
    pct = round(covered / total * 100, 2) if total else 0.0
    return {"covered": covered, "missed": missed, "pct": pct,
            "report_found": bool(files),
            "reports": [f.replace("\\", "/") for f in files]}


def flutter_coverage(repo_path):
    """Parse coverage/lcov.info — sum LF (found) / LH (hit).
    Shared by flutter AND node (jest/vitest --coverage emit the same lcov)."""
    lcov = glob.glob(os.path.join(repo_path, "**", "coverage", "lcov.info"),
                     recursive=True)
    found = hit = 0
    for f in lcov:
        try:
            with open(f, "r", encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    if line.startswith("LF:"):
                        found += int(line[3:].strip() or 0)
                    elif line.startswith("LH:"):
                        hit += int(line[3:].strip() or 0)
        except OSError:
            continue
    pct = round(hit / found * 100, 2) if found else 0.0
    return {"covered": hit, "missed": found - hit, "pct": pct,
            "report_found": bool(lcov),
            "reports": [f.replace("\\", "/") for f in lcov]}


def cobertura_coverage(repo_path):
    """Cobertura coverage.xml — emitted by `pytest --cov --cov-report=xml` (python),
    `cargo llvm-cov --cobertura` (rust) and coverlet (dotnet). Root attributes:
    lines-covered / lines-valid. First match wins: coverage.xml,
    reports/coverage.xml. An unreadable report is NOT measured (report_found
    False) — absence is never invented as a number."""
    path = next((p for p in (os.path.join(repo_path, "coverage.xml"),
                             os.path.join(repo_path, "reports", "coverage.xml"))
                 if os.path.isfile(p)), None)
    if not path:
        return {"covered": 0, "missed": 0, "pct": 0.0, "report_found": False}
    try:
        root = _parse_xml(path).getroot()
    except (ET.ParseError, OSError):
        return {"covered": 0, "missed": 0, "pct": 0.0, "report_found": False}
    lc, lv = root.get("lines-covered"), root.get("lines-valid")
    if lc is None or lv is None:
        # parseable XML but NOT a Cobertura root (wrong format dropped here) —
        # a report that measured nothing must never yield an invented 0.0%.
        return {"covered": 0, "missed": 0, "pct": 0.0, "report_found": False}
    try:
        covered, valid = int(float(lc)), int(float(lv))
    except ValueError:
        return {"covered": 0, "missed": 0, "pct": 0.0, "report_found": False}
    pct = round(covered / valid * 100, 2) if valid else 0.0
    return {"covered": covered, "missed": max(0, valid - covered), "pct": pct,
            "report_found": True, "reports": [path.replace("\\", "/")]}


def go_coverage(repo_path):
    """Go cover profile (`go test -coverprofile=coverage.out ./...`): lines of the
    form `import/path/file.go:S.C,E.C numStatements hitCount` — STATEMENT coverage,
    the Go convention. First match wins: coverage.out, cover.out,
    reports/coverage.out. An empty profile (mode line only) scores 0.0 — fail-closed,
    never an invented green."""
    path = next((p for p in (os.path.join(repo_path, "coverage.out"),
                             os.path.join(repo_path, "cover.out"),
                             os.path.join(repo_path, "reports", "coverage.out"))
                 if os.path.isfile(p)), None)
    if not path:
        return {"covered": 0, "missed": 0, "pct": 0.0, "report_found": False}
    # dedupe by block: with -coverpkg=./... the merged profile repeats a block
    # once per test binary — `go tool cover` ORs the hits; counting occurrences
    # would understate pct vs `go tool cover -func`.
    blocks = {}
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                s = line.strip()
                if not s or s.startswith("mode:"):
                    continue
                parts = s.split()
                if len(parts) != 3:
                    continue
                try:
                    n, hits = int(parts[1]), int(parts[2])
                except ValueError:
                    continue
                prev_n, prev_hits = blocks.get(parts[0], (n, 0))
                blocks[parts[0]] = (n, max(prev_hits, hits))
    except OSError:
        return {"covered": 0, "missed": 0, "pct": 0.0, "report_found": False}
    total = sum(n for n, _ in blocks.values())
    covered = sum(n for n, hits in blocks.values() if hits > 0)
    pct = round(covered / total * 100, 2) if total else 0.0
    return {"covered": covered, "missed": total - covered, "pct": pct,
            "report_found": True, "reports": [path.replace("\\", "/")]}


def gradle_coverage(repo_path):
    """JaCoCo XML at Gradle paths (Kotlin/JVM + Java-on-Gradle):
    build/reports/jacoco/test/jacocoTestReport.xml. Same report format as maven —
    only the location differs."""
    files = glob.glob(os.path.join(repo_path, "**", "build", "reports", "jacoco",
                                   "test", "jacocoTestReport.xml"), recursive=True)
    if not files:
        files = glob.glob(os.path.join(repo_path, "**", "build", "reports",
                                       "jacoco", "jacoco.xml"), recursive=True)
    missed = covered = 0
    for f in files:
        m, c = _jacoco_line_counter(f)
        missed += m
        covered += c
    total = missed + covered
    pct = round(covered / total * 100, 2) if total else 0.0
    return {"covered": covered, "missed": missed, "pct": pct,
            "report_found": bool(files),
            "reports": [f.replace("\\", "/") for f in files]}


def ant_coverage(repo_path):
    """Ant + JaCoCo (kit 1.44.0). Ant has no standard output layout -- the jacoco
    report task writes wherever the build file says -- so the report is discovered
    RECURSIVELY by name instead of guessing one convention."""
    files = _ant_reports(repo_path, "jacoco.xml")
    missed = covered = 0
    for f in files:
        m, c = _jacoco_line_counter(f)
        missed += m
        covered += c
    total = missed + covered
    pct = round(covered / total * 100, 2) if total else 0.0
    return {"covered": covered, "missed": missed, "pct": pct,
            "report_found": bool(files),
            "reports": [f.replace("\\", "/") for f in files]}


def coverage(repo_path, repo_type):
    if repo_type == "ant":
        return ant_coverage(repo_path)
    if repo_type == "maven":
        return maven_coverage(repo_path)
    if repo_type == "gradle":
        return gradle_coverage(repo_path)
    if repo_type in ("python", "rust", "dotnet", "cpp"):
        return cobertura_coverage(repo_path)  # cpp: gcovr --cobertura
    if repo_type == "go":
        return go_coverage(repo_path)
    # flutter + node + swift: all emit lcov (swift: llvm-cov export -format=lcov)
    return flutter_coverage(repo_path)


# --------------------------------------------------------------------------- #
# measurement: test counts
# --------------------------------------------------------------------------- #
def _invalid_junit(path, detail):
    print(f"[qa_ledger] invalid JUnit XML report '{path}': {detail}",
          file=sys.stderr)
    raise SystemExit(2)


def _parse_junit_xml(path):
    try:
        root = _parse_xml(path).getroot()
    except (ET.ParseError, OSError) as exc:
        _invalid_junit(path, exc)
    root_kind = _local(root.tag)
    if root_kind not in ("testsuite", "testsuites"):
        _invalid_junit(path, "expected <testsuite> or <testsuites> root")
    if root_kind == "testsuites":
        children = list(root)
        if children and any(_local(child.tag) != "testsuite"
                            for child in children):
            _invalid_junit(path, "<testsuites> may contain only <testsuite> children")

    return root


def _junit_int(element, name, path):
    try:
        value = int(element.get(name, 0))
    except (TypeError, ValueError):
        _invalid_junit(path, f"attribute '{name}' must be an integer")
    if value < 0:
        _invalid_junit(path, f"attribute '{name}' must be non-negative")
    return value


def _junit_counts(element, path):
    counts = tuple(_junit_int(element, name, path)
                   for name in ("tests", "failures", "errors", "skipped"))
    tests, failures, errors, skipped = counts
    # kit 1.41.1 (adversarial-review fix): a <testsuite>'s summary ATTRIBUTES are
    # self-declared and can hide real outcomes -- e.g. failures="0" on a suite that
    # actually contains a <testcase> with a <failure>/<error> element. Honor the real
    # child ELEMENTS, fail-closed (take the worse): present failure/error evidence can
    # never be attribute-declared away. (Attribute-only summary suites with no
    # <testcase> elements keep their declared counts -- the form many emitters use.)
    if _local(element.tag) == "testsuite":
        el_fail = el_err = 0
        for tc in element:
            if _local(tc.tag) != "testcase":
                continue
            kinds = {_local(ch.tag) for ch in tc}
            if "failure" in kinds:
                el_fail += 1
            elif "error" in kinds:
                el_err += 1
        failures = max(failures, el_fail)
        errors = max(errors, el_err)
    if skipped > tests:
        _invalid_junit(path, "attribute 'skipped' cannot exceed 'tests'")
    build_error_only = (
        _local(element.tag) == "testsuites"
        and not list(element)
        and failures == 0
        and errors > 0
    )
    if failures + errors > tests - skipped and not build_error_only:
        _invalid_junit(
            path, "'failures' + 'errors' cannot exceed executed tests")
    return (tests, failures, errors, skipped)


# Report discovery needs a DIFFERENT skip set than source scanning: SKIP_DIRS exists to
# skip build OUTPUT while counting source, but reports LIVE in build output (build/,
# target/, coverage/). Pruning those would hide the very files we are looking for. Here we
# prune only third-party / VCS trees, whose reports are never ours (kit 1.44.0).
_REPORT_SKIP = {".git", "node_modules", "vendor", ".venv", "venv", "__pycache__",
                ".gradle", ".mvn", ".tox"}


def _under_skipped(path, root, skip=_REPORT_SKIP):
    """True if path sits under one of `skip`. Never raises: an unreachable path
    (Windows reserved device name, different mount) is skipped, not fatal."""
    try:
        parts = set(os.path.relpath(path, root).split(os.sep))
    except ValueError:
        return True
    return bool(parts & skip)


def _ant_reports(repo_path, filename_glob):
    """Ant has no standard todir, so its reports are discovered recursively BY NAME --
    minus third-party trees, whose reports are never this repo's."""
    return sorted({f for f in glob.glob(os.path.join(repo_path, "**", filename_glob),
                                        recursive=True)
                   if not _under_skipped(f, repo_path)})


def _perclass_xml_count(patterns, skip_root=None, tolerant=False):
    """Sum per-class JUnit XML files (surefire/failsafe/gradle test-results):
    each file's root is a <testsuite> carrying the counters."""
    tests = failures = errors = skipped = 0
    seen = set()
    used = 0
    dropped = []
    for pat in patterns:
        for f in glob.glob(pat, recursive=True):
            if f in seen:
                continue
            if skip_root is not None and _under_skipped(f, skip_root):
                continue
            seen.add(f)
            if tolerant:
                # name-based recursive discovery (ant): a TEST-*.xml found anywhere may
                # simply not be ours. Skip it instead of aborting the whole run -- but
                # NEVER silently: every drop is returned so the ledger can surface it.
                try:
                    root = _parse_xml(f).getroot()
                except (ET.ParseError, OSError) as exc:
                    dropped.append({"path": f, "reason": f"unreadable XML: {exc}"})
                    continue
                if _local(root.tag) != "testsuite":
                    dropped.append({"path": f, "reason": "not a JUnit <testsuite> report"})
                    continue
                try:
                    # counter validation ALSO exits hard (negative/inconsistent numbers);
                    # inside tolerant discovery that must degrade to a recorded drop.
                    t, fl, er, sk = _junit_counts(root, f)
                except SystemExit:
                    dropped.append({"path": f, "reason": "malformed JUnit counters"})
                    continue
            else:
                root = _parse_junit_xml(f)
                if _local(root.tag) != "testsuite":
                    _invalid_junit(f, "per-class report requires a <testsuite> root")
                t, fl, er, sk = _junit_counts(root, f)
            used += 1
            tests += t
            failures += fl
            errors += er
            skipped += sk
    for d in dropped:
        print(f"[qa_ledger] dropped test report '{d['path']}': {d['reason']}",
              file=sys.stderr)
    executed = tests - skipped
    return {"total": tests, "executed": executed, "failures": failures,
            "errors": errors, "skipped": skipped, "passed": executed - failures - errors,
            # report_found means a USABLE report: files that were dropped do not count
            "report_found": used > 0, "skipped_reports": dropped}


def maven_test_count(repo_path):
    return _perclass_xml_count([
        os.path.join(repo_path, "**", "target", "surefire-reports", "TEST-*.xml"),
        os.path.join(repo_path, "**", "target", "failsafe-reports", "TEST-*.xml"),
    ])


def ant_test_count(repo_path):
    """Ant's <junit> XML formatter always emits per-class TEST-<class>.xml, but the
    todir is build-file defined (build/test/results, reports/junit, test-results...).
    Discover them recursively rather than hardcode one layout (kit 1.44.0)."""
    return _perclass_xml_count([
        os.path.join(repo_path, "**", "TEST-*.xml"),
    ], skip_root=repo_path, tolerant=True)


def gradle_test_count(repo_path):
    return _perclass_xml_count([
        os.path.join(repo_path, "**", "build", "test-results", "**", "TEST-*.xml"),
    ])


def flutter_test_count(repo_path):
    """
    Best-effort: counts `test(` / `testWidgets(` declarations under test/.
    For an exact count run `flutter test --machine` and parse testDone events;
    this static count is an approximation and is flagged as such.
    """
    count = 0
    test_root = os.path.join(repo_path, "test")
    for dirpath, dirnames, filenames in os.walk(test_root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS
                    and not d.startswith("cmake-build-")]
        for fn in filenames:
            if not fn.endswith(".dart"):
                continue
            try:
                with open(os.path.join(dirpath, fn), "r", encoding="utf-8",
                          errors="ignore") as fh:
                    for line in fh:
                        s = line.lstrip()
                        if s.startswith("test(") or s.startswith("testWidgets("):
                            count += 1
            except OSError:
                continue
    return {"total": count, "executed": count, "failures": 0, "errors": 0,
            "skipped": 0, "passed": count, "report_found": count > 0,
            "approximate": True}


def _junit_report_files(repo_path):
    """First-LOCATION-wins selection of JUnit-family reports (shared by the
    test counter and the AC-tag scan — one list of locations, not two)."""
    groups = [
        [os.path.join(repo_path, "reports", "junit.xml")],
        [os.path.join(repo_path, "junit.xml")],
        sorted(glob.glob(os.path.join(repo_path, "reports", "TEST-*.xml"))),
        # kit 1.44.0: runners that write a DIRECTORY of per-class XML under
        # reports/junit/ were invisible -- the operator had to hand-copy reports
        # to a path the engine knew, which breaks "evidence captured by execution".
        sorted(glob.glob(os.path.join(repo_path, "reports", "junit", "**", "*.xml"),
                         recursive=True)),
    ]
    for group in groups:
        found = [f for f in group if os.path.isfile(f)]
        if found:
            return found
    return []


def _junit_files_for(repo_path, repo_type):
    """TODOS los reportes JUnit-family que el engine ya usa para contar tests
    del type dado — para leer nombres de testcase (trazabilidad AC-n).
    flutter no emite JUnit (conteo aproximado): devuelve []."""
    if repo_type == "ant":
        return _ant_reports(repo_path, "TEST-*.xml")
    if repo_type == "maven":
        pats = [os.path.join(repo_path, "**", "target", "surefire-reports", "TEST-*.xml"),
                os.path.join(repo_path, "**", "target", "failsafe-reports", "TEST-*.xml")]
        return sorted({f for p in pats for f in glob.glob(p, recursive=True)})
    if repo_type == "gradle":
        return sorted(set(glob.glob(os.path.join(
            repo_path, "**", "build", "test-results", "**", "TEST-*.xml"),
            recursive=True)))
    if repo_type == "flutter":
        return []
    files = _junit_report_files(repo_path)
    if repo_type == "swift":
        for f in (os.path.join(repo_path, "reports", "junit-swift-testing.xml"),
                  os.path.join(repo_path, "junit-swift-testing.xml")):
            if os.path.isfile(f) and f not in files:
                files.append(f)
    return files


# freshness de los reportes: un TEST-*.xml mas viejo que el codigo fuente es
# STALE — los tests no se re-corrieron tras el ultimo cambio, asi que su verde/
# rojo NO es evidencia vigente. Correlacion barata (mtime del arbol de fuentes
# vs mtime del reporte); sin falso positivo en el flujo real (editar -> testear
# deja el reporte como lo mas nuevo), detecta el caso peligroso (no re-correr).
_SRC_EXT = {
    ".java", ".kt", ".kts", ".scala", ".groovy", ".py", ".js", ".jsx",
    ".ts", ".tsx", ".mjs", ".cjs", ".go", ".rs", ".cs", ".vb", ".fs",
    ".cpp", ".cc", ".cxx", ".c", ".h", ".hpp", ".swift", ".m", ".mm",
    ".rb", ".php", ".dart", ".gradle",
}
_SRC_SKIP_DIRS = SKIP_DIRS | {"reports", "Pods", ".vs"}

# One second admits same-run writes on filesystems with coarse timestamp
# resolution, without letting genuinely older reports mask later source edits.
_JUNIT_FRESHNESS_TOLERANCE_NS = 1_000_000_000


# Windows reserved DEVICE names (kit 1.44.0): a file literally called 'nul' (or con,
# aux, prn, com1..9, lpt1..9) is not a normal path -- os.path.relpath raises
# ValueError("path is on mount '\\.\nul'") and used to take down a whole gate
# mid-walk. A weird filename must degrade to a skip, never crash the run.
_WIN_RESERVED = ({"con", "prn", "aux", "nul"}
                 | {f"com{i}" for i in range(1, 10)}
                 | {f"lpt{i}" for i in range(1, 10)})


def _reserved_name(fn):
    # Windows treats everything before the FIRST dot as the device name: 'nul.tar.gz' is
    # just as reserved as 'nul.txt'. splitext() only strips the LAST extension, which left
    # the very ValueError this guard exists to prevent reachable (kit 1.44.0).
    return fn.split(".", 1)[0].strip().lower() in _WIN_RESERVED


def _newest_source(repo_path, extensions=None):
    """Newest relevant source/test file, excluding the same generated, build,
    report, VCS, dependency, and vendor-like trees used by repo adapters."""
    newest = None
    allowed = extensions or _SRC_EXT
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in _SRC_SKIP_DIRS
                    and not d.startswith("cmake-build-")]
        for fn in files:
            if os.path.splitext(fn)[1].lower() not in allowed:
                continue
            if _reserved_name(fn):
                continue
            path = os.path.join(root, fn)
            try:
                mtime_ns = os.stat(path).st_mtime_ns
            except OSError:
                continue
            if newest is None or mtime_ns > newest["mtime_ns"]:
                newest = {
                    "path": os.path.relpath(path, repo_path).replace("\\", "/"),
                    "mtime_ns": mtime_ns,
                    "mtime": datetime.fromtimestamp(
                        mtime_ns / 1_000_000_000, timezone.utc).isoformat(),
                }
    return newest


def _source_newest_mtime(repo_path):
    """Compatibility helper for AC evidence freshness."""
    newest = _newest_source(repo_path)
    return newest["mtime_ns"] / 1_000_000_000 if newest else 0.0


def _test_evidence_provenance(repo_path, repo_type):
    """Explain which JUnit reports back a snapshot and whether they are newer
    than relevant source/test files. No discoverable source is explicitly
    uncorrelated-but-usable to preserve synthetic/report-only workflows."""
    files = _junit_files_for(repo_path, repo_type)
    reports = []
    for path in files:
        try:
            mtime_ns = os.stat(path).st_mtime_ns
        except OSError:
            continue
        reports.append({
            "path": os.path.relpath(path, repo_path).replace("\\", "/"),
            "mtime_ns": mtime_ns,
            "mtime": datetime.fromtimestamp(
                mtime_ns / 1_000_000_000, timezone.utc).isoformat(),
        })
    if not reports:
        status = "not-applicable" if repo_type == "flutter" else "missing"
        reason = ("approximate static test discovery has no JUnit report"
                  if repo_type == "flutter"
                  else "no selected JUnit report")
        return reports, {"status": status, "reason": reason,
                         "tolerance_ns": _JUNIT_FRESHNESS_TOLERANCE_NS}

    newest = _newest_source(
        repo_path, SOURCE_EXT.get(repo_type, SOURCE_EXT["generic"]))
    if newest is None:
        return reports, {
            "status": "unknown-no-sources",
            "reason": ("no discoverable source/test files; report-only evidence "
                       "remains usable for compatibility"),
            "newest_source": None,
            "tolerance_ns": _JUNIT_FRESHNESS_TOLERANCE_NS,
        }

    stale_reports = [
        report for report in reports
        if newest["mtime_ns"] > report["mtime_ns"] + _JUNIT_FRESHNESS_TOLERANCE_NS
    ]
    if stale_reports:
        paths = ", ".join(report["path"] for report in stale_reports)
        reason = (f"source/test {newest['path']} is newer than JUnit report(s) "
                  f"{paths}")
        status = "stale"
    else:
        reason = "selected JUnit report(s) are current relative to source/test files"
        status = "fresh"
    return reports, {
        "status": status,
        "reason": reason,
        "newest_source": newest,
        "tolerance_ns": _JUNIT_FRESHNESS_TOLERANCE_NS,
    }


# tolerante a los limites de naming de cada lenguaje: test_ac1_x (python/go,
# sin '-'), testAC01X (java camelCase), "AC-01: ..." (nombres libres).
# OJO: \b no sirve — '_' es word character y test_ac1 quedaria invisible;
# boundaries explicitos: separador no-alfanumerico, o salto camelCase a 'AC'.
_AC_TAG = re.compile(
    r"(?:(?<![A-Za-z0-9])[Aa][Cc]|(?<=[a-z])AC)[-_]?0*(\d+)(?!\d)")


def _ac_tags(repo_path, repo_type):
    """Tags AC-n leidos de los NOMBRES de testcase en los reportes JUnit que el
    engine ya ingiere. Devuelve (tags, stale) donde tags = {'AC-n': {'green': x,
    'red': y}} y stale = [rutas de reportes descartados por viejos]. Un criterio
    cierra MEDIDO solo con >=1 testcase verde y 0 rojos (evidencia roja veta:
    fail-closed). Testcases skipped no cuentan para ningun lado.

    FRESHNESS (kit 1.31.0): maven/gradle globbean TEST-*.xml recursivo; un
    reporte mas viejo que el codigo fuente es STALE (el codigo cambio despues de
    correr los tests) y se DESCARTA — no vetea ni cierra. Un AC respaldado solo
    por reportes stale queda UNMEASURED (ni falso-verde ni falso-rojo): honrar
    evidencia stale romperia 'la evidencia decide'. junit_test_count (el conteo
    aproximado) mantiene el limite conocido — su blast radius es menor (no
    cierra ACs, solo aproxima un conteo)."""
    tags = {}
    stale = []
    newest_src = _source_newest_mtime(repo_path)
    for f in _junit_files_for(repo_path, repo_type):
        if newest_src > 0.0:
            try:
                if os.path.getmtime(f) < newest_src:
                    stale.append(f)
                    continue
            except OSError:
                pass
        try:
            root = _parse_xml(f).getroot()
        except (ET.ParseError, OSError):
            continue
        for tc in root.iter():
            if _local(tc.tag) != "testcase":
                continue
            status = "green"
            for child in tc:
                ln = _local(child.tag)
                if ln in ("failure", "error"):
                    status = "red"
                    break
                if ln == "skipped":
                    status = None
                    break
            if status is None:
                continue
            # NOMBRE del testcase unicamente (nunca classname): un modulo/clase
            # cuyo nombre matchea 'ACn' por coincidencia (test_ac3_flow.py) no
            # debe taggear los OTROS tests del mismo archivo/clase.
            blob = tc.get("name") or ""
            for num in _AC_TAG.findall(blob):
                d = tags.setdefault(f"AC-{int(num)}",
                                    {"green": 0, "red": 0, "cases": []})
                d[status] += 1
                # RECEIPT (kit 1.50.0): keep WHICH testcase in WHICH report backed the
                # verdict -- the name and path were always in scope here and were being
                # thrown away. Capped: a receipt cites evidence, it is not a dump.
                if len(d["cases"]) < 8:
                    d["cases"].append({"test": blob,
                                       "report": f.replace("\\", "/"),
                                       "ok": status == "green"})
    return tags, stale


def junit_test_count(repo_path, extra_files=None):
    """JUnit-family XML: `pytest --junitxml=...` (python) and jest-junit /
    vitest --reporter=junit (node). Modern emitters WRAP the root:
    <testsuites><testsuite tests=...>; older ones use <testsuite> as the root.
    Handle both — reading attrs off a <testsuites> root would silently count 0."""
    # first LOCATION wins (mirrors cobertura_coverage): each junit.xml is a FULL-run
    # report — summing locations would double-count, and a stale root junit.xml
    # next to a fresh reports/junit.xml could permanently veto convergence.
    # (The TEST-*.xml set legitimately sums: those are per-class files.)
    files = _junit_report_files(repo_path)
    # extra_files are ADDITIONAL full-run reports of a DISJOINT test set (swift:
    # --xunit-output writes XCTest to junit.xml and Swift Testing results to a
    # SECOND junit-swift-testing.xml) — summing them is correct, and skipping
    # them would let real failures read as green (fail-open).
    for f in (extra_files or []):
        if os.path.isfile(f) and f not in files:
            files.append(f)
    tests = failures = errors = skipped = 0
    for f in files:
        root = _parse_junit_xml(f)
        if _local(root.tag) == "testsuite":
            suites = [root]
        else:
            suites = list(_iter_local(root, "testsuite"))
        t = fl = er = sk = 0
        for s in suites:
            suite_t, suite_fl, suite_er, suite_sk = _junit_counts(s, f)
            t += suite_t
            fl += suite_fl
            er += suite_er
            sk += suite_sk
        if _local(root.tag) == "testsuites":
            # gotestsum puts `errors` ONLY on the <testsuites> root (a package
            # that fails to BUILD has root errors>0 and no suite) — take the max
            # of root attrs vs child sums so a broken build never reads green.
            root_t, root_fl, root_er, root_sk = _junit_counts(root, f)
            child_counts = (t, fl, er, sk)
            root_counts = (root_t, root_fl, root_er, root_sk)
            for name, root_count, child_count in zip(
                    ("tests", "failures", "errors", "skipped"),
                    root_counts, child_counts):
                if name in root.attrib and root_count < child_count:
                    _invalid_junit(
                        f, f"root '{name}' cannot be less than child suite total")
            t = max(t, root_t)
            fl = max(fl, root_fl)
            er = max(er, root_er)
            sk = max(sk, root_sk)
            if suites and fl + er > t - sk:
                _invalid_junit(
                    f, "combined root/child outcomes exceed executed tests")
        tests += t
        failures += fl
        errors += er
        skipped += sk
    executed = tests - skipped
    return {"total": tests, "executed": executed, "failures": failures,
            "errors": errors, "skipped": skipped,
            "passed": executed - failures - errors, "report_found": bool(files)}


def test_count(repo_path, repo_type):
    if repo_type == "ant":
        result = ant_test_count(repo_path)
    elif repo_type == "maven":
        result = maven_test_count(repo_path)
    elif repo_type == "gradle":
        result = gradle_test_count(repo_path)
    elif repo_type == "swift":
        # SwiftPM writes Swift Testing results to a SEPARATE file next to the
        # XCTest one — both must count or a Swift-6 package reads tests=0.
        result = junit_test_count(repo_path, extra_files=[
            os.path.join(repo_path, "reports", "junit-swift-testing.xml"),
            os.path.join(repo_path, "junit-swift-testing.xml")])
    elif repo_type in ("python", "node", "go", "rust", "dotnet", "cpp"):
        # go: gotestsum · rust: cargo-nextest · dotnet: JUnit logger ·
        # cpp: ctest --output-junit / gtest
        result = junit_test_count(repo_path)
    else:
        result = flutter_test_count(repo_path)
    reports, freshness = _test_evidence_provenance(repo_path, repo_type)
    result["reports"] = reports
    result["freshness"] = freshness
    return result


# --------------------------------------------------------------------------- #
# measurement: source lines (production vs test)
# --------------------------------------------------------------------------- #
def _is_test_path(rel, repo_type):
    parts = rel.replace("\\", "/").split("/")
    fn = parts[-1]
    if repo_type == "flutter":
        return parts and parts[0] == "test"
    if repo_type == "python":
        return ("tests" in parts or "test" in parts
                or fn.startswith("test_") or fn.endswith("_test.py"))
    if repo_type == "node":
        base = fn.lower()
        return ("__tests__" in parts or "tests" in parts or "test" in parts
                or any(base.endswith(suf) for suf in
                       (".test.ts", ".test.tsx", ".test.js", ".test.jsx",
                        ".spec.ts", ".spec.tsx", ".spec.js", ".spec.jsx")))
    if repo_type == "go":
        return fn.endswith("_test.go")  # the Go convention: tests live next to code
    if repo_type == "rust":
        # tests/ = integration tests. Inline #[cfg(test)] unit tests count as prod
        # LOC — a known, documented limitation of path-based classification.
        return "tests" in parts
    if repo_type == "dotnet":
        return (any(p.lower() in ("test", "tests") or p.endswith(".Tests")
                    for p in parts[:-1])
                or fn.endswith(("Test.cs", "Tests.cs")))
    if repo_type == "cpp":
        base = fn.lower()
        # gtest CamelCase (FooTest.cpp) matched CASE-SENSITIVE on purpose:
        # a lowered bare 'test.cpp' suffix would swallow backtest.cpp/protest.cpp
        # as test LOC (same trap the dotnet rule avoids with Test.cs/Tests.cs).
        return ("test" in parts or "tests" in parts
                or base.startswith("test_")
                or any(base.endswith(suf) for suf in
                       ("_test.cpp", "_test.cc", "_test.cxx", "_tests.cpp"))
                or fn.endswith(("Test.cpp", "Test.cc", "Test.cxx", "Tests.cpp")))
    if repo_type == "swift":
        # SwiftPM convention: Sources/ + Tests/; XCTest classes end in Tests.swift
        return ("Tests" in parts or "tests" in parts
                or fn.endswith(("Tests.swift", "Test.swift")))
    if repo_type == "gradle":
        # Gradle source sets: src/test/ plus CUSTOM ones (src/integrationTest/,
        # src/functionalTest/ — the convention Gradle's own docs promote): any
        # source-set dir directly under src/ named test or *Test is test LOC.
        for i, p in enumerate(parts[:-1]):
            if p == "src":
                nxt = parts[i + 1]
                if nxt == "test" or nxt.endswith("Test"):
                    return True
        return False
    return "test" in parts and "src" in parts  # src/test/... (maven)


def _is_prod_path(rel, repo_type):
    parts = rel.replace("\\", "/").split("/")
    if repo_type == "flutter":
        return parts and parts[0] == "lib"
    if repo_type in ("python", "node", "go", "rust", "dotnet", "cpp", "swift"):
        # src layout or root package — any source file that isn't a test
        return not _is_test_path(rel, repo_type)
    return "main" in parts and "src" in parts  # src/main/... (maven + gradle)


def count_loc(repo_path, repo_type):
    exts = SOURCE_EXT.get(repo_type, SOURCE_EXT["generic"])
    prod = test = 0
    prod_files = test_files = 0
    for dirpath, dirnames, filenames in os.walk(repo_path):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS
                    and not d.startswith("cmake-build-")]
        for fn in filenames:
            if os.path.splitext(fn)[1] not in exts:
                continue
            if _reserved_name(fn):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, repo_path)
            try:
                with open(full, "r", encoding="utf-8", errors="ignore") as fh:
                    n = sum(1 for line in fh if line.strip())
            except OSError:
                continue
            if _is_test_path(rel, repo_type):
                test += n
                test_files += 1
            elif _is_prod_path(rel, repo_type):
                prod += n
                prod_files += 1
            else:
                prod += n  # source outside the standard layout counts as prod
                prod_files += 1
    return {"prod_loc": prod, "test_loc": test,
            "prod_files": prod_files, "test_files": test_files}


# --------------------------------------------------------------------------- #
# static-gate ingestion (Checkstyle / PMD / SpotBugs / FindSecBugs)
# --------------------------------------------------------------------------- #
# Common severity scale, low -> high.
SEVERITY_ORDER = ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL", "BLOCKER"]

# Checkstyle native severity -> common scale.
CHECKSTYLE_SEVERITY = {"error": "HIGH", "warning": "MEDIUM", "info": "INFO", "ignore": "INFO"}
# PMD priority (1 highest .. 5 lowest) -> common scale.
PMD_PRIORITY = {1: "BLOCKER", 2: "CRITICAL", 3: "HIGH", 4: "MEDIUM", 5: "LOW"}
# SpotBugs priority (1 High, 2 Medium, 3 Low) -> common scale.
SPOTBUGS_PRIORITY = {1: "HIGH", 2: "MEDIUM", 3: "LOW"}
# FindSecBugs findings (category SECURITY in the SpotBugs report) are floored to HIGH.


def _sev_rank(s):
    return SEVERITY_ORDER.index(s) if s in SEVERITY_ORDER else SEVERITY_ORDER.index("MEDIUM")


def _bump(sev, floor):
    return sev if _sev_rank(sev) >= _sev_rank(floor) else floor


def _at_or_above(sev, gate_list):
    if not gate_list:
        return False
    min_rank = min(_sev_rank(g) for g in gate_list)
    return _sev_rank(sev) >= min_rank


def _local(tag):
    """Strip XML namespace from a tag (PMD reports are namespaced)."""
    return tag.split("}")[-1]


def _iter_local(elem, name):
    for child in elem:
        if _local(child.tag) == name:
            yield child


def _rel_src(fname):
    """Stable, machine-independent path: keep from 'src/' onward, else basename."""
    if not fname:
        return "?"
    fname = fname.replace("\\", "/")
    if fname.startswith("src/"):
        return fname  # already repo-relative (mypy/ruff emit these as given on the CLI)
    i = fname.find("/src/")
    if i >= 0:
        return fname[i + 1:]
    return os.path.basename(fname)


def _mk_id(tool, rule, fname, line, granularity):
    loc = _rel_src(fname)
    if granularity == "file":
        return f"{tool}:{rule}:{loc}"
    return f"{tool}:{rule}:{loc}:{line}"


def _find_all(base, patterns, explicit):
    if explicit:
        return [explicit] if os.path.exists(explicit) else []
    found = []
    for pat in patterns:
        found += glob.glob(os.path.join(base, pat), recursive=True)
    return sorted(set(found))


def _invalid_static_report(path, label, detail):
    print(f"[qa_ledger] invalid {label} report '{path}': {detail}",
          file=sys.stderr)
    raise SystemExit(2)


def _parse_static_xml(path, label, root_name):
    try:
        root = _parse_xml(path).getroot()
    except (ET.ParseError, OSError) as exc:
        _invalid_static_report(path, label, exc)
    if _local(root.tag) != root_name:
        _invalid_static_report(
            path, label, f"expected <{root_name}> root, got <{_local(root.tag)}>")
    return root


def parse_checkstyle(path, granularity, tool="checkstyle", base=None):
    """Checkstyle-format XML. Also emitted by golangci-lint (v2:
    --output.checkstyle.path=...; v1: --out-format checkstyle), detekt and
    SwiftLint — pass tool="golangci"/"detekt"/"swiftlint" so findings/IDs
    carry the real gate name. For non-java tools the repo-relative path is
    PRESERVED in the ID (idiomatic Go repos have same-named files in every
    package — basename would collide across packages/modules); absolute
    paths (detekt and SwiftLint print absolute BY DEFAULT) are relativized
    against the repo first, same discipline as eslint/tsc/clang-tidy."""
    out = []
    root = _parse_static_xml(path, f"{tool} Checkstyle XML", "checkstyle")
    for file_index, f in enumerate(_iter_local(root, "file")):
        fname = f.get("name")
        if not fname:
            _invalid_static_report(
                path, f"{tool} Checkstyle XML",
                f"file at index {file_index} is missing required name")
        for error_index, e in enumerate(_iter_local(f, "error")):
            line = e.get("line", "0")
            try:
                int(line)
            except (TypeError, ValueError):
                _invalid_static_report(
                    path, f"{tool} Checkstyle XML",
                    f"error at {file_index}:{error_index} has invalid line")
            sev = CHECKSTYLE_SEVERITY.get((e.get("severity") or "warning").lower(), "MEDIUM")
            rule = (e.get("source") or "?").split(".")[-1]
            if tool != "checkstyle":
                fid = _mk_id_rel(tool, rule, _node_rel(fname, base),
                                 line, granularity)
            else:
                fid = _mk_id(tool, rule, fname, line, granularity)
            out.append((fid, sev, tool))
    return out


def parse_pmd(path, granularity):
    out = []
    root = _parse_static_xml(path, "PMD XML", "pmd")
    for file_index, f in enumerate(_iter_local(root, "file")):
        fname = f.get("name")
        if not fname:
            _invalid_static_report(
                path, "PMD XML", f"file at index {file_index} is missing required name")
        for violation_index, v in enumerate(_iter_local(f, "violation")):
            try:
                pr = int(v.get("priority", "3"))
                beginline = int(v.get("beginline", "0"))
            except (TypeError, ValueError):
                _invalid_static_report(
                    path, "PMD XML",
                    f"violation at {file_index}:{violation_index} has invalid numeric field")
            if pr not in PMD_PRIORITY:
                _invalid_static_report(
                    path, "PMD XML",
                    f"violation at {file_index}:{violation_index} has invalid priority")
            sev = PMD_PRIORITY[pr]
            rule = v.get("rule", "?")
            out.append((_mk_id("pmd", rule, fname, beginline, granularity),
                        sev, "pmd"))
    return out


def parse_spotbugs(path, granularity):
    """SpotBugs report. FindSecBugs findings (category SECURITY) are split out
    under tool 'findsecbugs' and floored to HIGH severity."""
    out = []
    root = _parse_static_xml(path, "SpotBugs XML", "BugCollection")
    for bug_index, b in enumerate(_iter_local(root, "BugInstance")):
        try:
            pr = int(b.get("priority", "2"))
        except (TypeError, ValueError):
            _invalid_static_report(
                path, "SpotBugs XML",
                f"BugInstance at index {bug_index} has invalid priority")
        if pr not in SPOTBUGS_PRIORITY:
            _invalid_static_report(
                path, "SpotBugs XML",
                f"BugInstance at index {bug_index} has invalid priority")
        sev = SPOTBUGS_PRIORITY[pr]
        cat = (b.get("category") or "").upper()
        btype = b.get("type")
        if not btype:
            _invalid_static_report(
                path, "SpotBugs XML",
                f"BugInstance at index {bug_index} is missing required type")
        sl = next((c for c in b if _local(c.tag) == "SourceLine"), None)
        if sl is not None:
            fname = sl.get("sourcepath") or sl.get("classname") or "?"
            line = sl.get("start") or "0"
        else:
            fname, line = "?", "0"
        is_sec = cat == "SECURITY"
        if is_sec:
            sev = _bump(sev, "HIGH")
        tool = "findsecbugs" if is_sec else "spotbugs"
        out.append((_mk_id(tool, btype, fname, line, granularity), sev, tool))
    return out


# Ruff rule-code -> common scale: S* (flake8-bandit / security) and E9* / F82*
# (syntax errors / undefined names — real breakage) -> HIGH; B* (bugbear,
# likely bugs) -> MEDIUM; everything else (style/format) -> LOW.
def _ruff_severity(code):
    c = (code or "").upper()
    # digit-anchored: bare "S"/"B" prefixes over-match SIM/SLF/SLOT/BLE style rules
    if re.match(r"S\d", c) or c.startswith("E9") or c.startswith("F82"):
        return "HIGH"
    if re.match(r"B\d", c):
        return "MEDIUM"
    return "LOW"


def _invalid_ruff(path, detail):
    print(f"[qa_ledger] invalid Ruff JSON report '{path}': {detail}",
          file=sys.stderr)
    raise SystemExit(2)


def parse_ruff(path, granularity):
    """`ruff check --output-format=json` — a JSON array of finding objects."""
    out = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        _invalid_ruff(path, exc)
    if not isinstance(data, list):
        _invalid_ruff(path, "expected a JSON array of findings")
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            _invalid_ruff(path, f"finding at index {index} must be an object")
        code = item.get("code")
        if code is not None and not isinstance(code, str):
            _invalid_ruff(path, f"finding at index {index} has invalid code")
        fname = item.get("filename")
        if fname is not None and not isinstance(fname, str):
            _invalid_ruff(path, f"finding at index {index} has invalid filename")
        location = item.get("location")
        if location is None:
            location = {}
        if not isinstance(location, dict):
            _invalid_ruff(path, f"finding at index {index} has invalid location")
        line = location.get("row", 0)
        if isinstance(line, bool) or not isinstance(line, int):
            _invalid_ruff(path, f"finding at index {index} has invalid location row")
        fname = fname or "?"
        # modern ruff (>=0.5) emits "code": null for SYNTAX errors — real breakage,
        # always HIGH (the legacy E9* branch only covers older ruff versions).
        sev = "HIGH" if code is None else _ruff_severity(code)
        out.append((_mk_id("ruff", code or "syntax-error", fname, line, granularity),
                    sev, "ruff"))
    return out


_MYPY_LINE = re.compile(
    r"^(?P<file>(?:[A-Za-z]:)?[^:\n]+\.pyi?):(?P<line>\d+)(?::\d+)?:\s*"
    r"(?P<kind>error|warning|note):\s*.*?(?:\s+\[(?P<code>[\w-]+)\])?\s*$")


def parse_mypy(path, granularity):
    """mypy text output (`file:line: error: msg [code]`):
    error -> HIGH, warning -> MEDIUM, note -> INFO."""
    sev_map = {"error": "HIGH", "warning": "MEDIUM", "note": "INFO"}
    out = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                m = _MYPY_LINE.match(raw.strip())
                if not m:
                    continue
                code = m.group("code") or "misc"
                out.append((_mk_id("mypy", code, m.group("file"), m.group("line"),
                                   granularity),
                            sev_map.get(m.group("kind"), "MEDIUM"), "mypy"))
    except OSError:
        return out
    return out


def _mk_id_rel(tool, rule, rel, line, granularity):
    """Like _mk_id but PRESERVES a repo-relative path. Node layouts often have no
    src/ anchor and dozens of same-named files (page.tsx, route.ts, index.ts) —
    collapsing to basename would collide finding IDs across directories."""
    loc = (rel or "?").replace("\\", "/")
    if granularity == "file":
        return f"{tool}:{rule}:{loc}"
    return f"{tool}:{rule}:{loc}:{line}"


def _node_rel(fname, base):
    """Relativize fname against the repo base when it lives inside it —
    linters print ABSOLUTE paths by default (eslint, detekt, swiftlint,
    clang-tidy) and finding IDs must survive machine/worktree moves. Paths
    outside the base, already-relative paths, or cross-drive paths come back
    untouched. Deliberately NOT gated on os.path.isabs: its verdict for
    '/posix/style' paths on Windows changed across Python versions."""
    if not fname:
        return "?"
    if base:
        try:
            rp = os.path.relpath(fname, base)
            if not rp.startswith(".."):
                return rp
        except ValueError:  # different drive on Windows
            return fname
    return fname


def parse_eslint(path, granularity, base=None):
    """ESLint JSON format — array of {filePath, messages:[{ruleId, severity,
    line, fatal}]}. fatal:true (parse error) -> HIGH always. ruleId null WITHOUT
    fatal (e.g. unused eslint-disable directives in ESLint 9) follows the message
    severity — never a false blocker. severity 2 -> HIGH, 1 -> MEDIUM; rules from
    security plugins ('security/...') floored to HIGH."""
    out = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        _invalid_static_report(path, "ESLint JSON", exc)
    if not isinstance(data, list):
        _invalid_static_report(path, "ESLint JSON",
                               "expected a JSON array of file results")
    for entry_index, entry in enumerate(data):
        if not isinstance(entry, dict):
            _invalid_static_report(
                path, "ESLint JSON", f"file result at index {entry_index} must be an object")
        file_path = entry.get("filePath")
        if file_path is not None and not isinstance(file_path, str):
            _invalid_static_report(
                path, "ESLint JSON", f"file result at index {entry_index} has invalid filePath")
        messages = entry.get("messages")
        if not isinstance(messages, list):
            _invalid_static_report(
                path, "ESLint JSON", f"file result at index {entry_index} has invalid messages")
        fname = _node_rel(file_path, base)
        for message_index, msg in enumerate(messages):
            if not isinstance(msg, dict):
                _invalid_static_report(
                    path, "ESLint JSON",
                    f"message at {entry_index}:{message_index} must be an object")
            rule = msg.get("ruleId")
            if rule is not None and not isinstance(rule, str):
                _invalid_static_report(
                    path, "ESLint JSON",
                    f"message at {entry_index}:{message_index} has invalid ruleId")
            severity = msg.get("severity")
            if isinstance(severity, bool) or not isinstance(severity, int):
                _invalid_static_report(
                    path, "ESLint JSON",
                    f"message at {entry_index}:{message_index} has invalid severity")
            fatal = msg.get("fatal", False)
            if not isinstance(fatal, bool):
                _invalid_static_report(
                    path, "ESLint JSON",
                    f"message at {entry_index}:{message_index} has invalid fatal")
            line = msg.get("line", 0)
            if line is None:
                line = 0
            if isinstance(line, bool) or not isinstance(line, int):
                _invalid_static_report(
                    path, "ESLint JSON",
                    f"message at {entry_index}:{message_index} has invalid line")
            if fatal:
                sev, rule = "HIGH", "syntax-error"
            elif rule is None:
                sev = "HIGH" if severity == 2 else "MEDIUM"
                rule = "unused-directive"
            else:
                sev = "HIGH" if severity == 2 else "MEDIUM"
                if rule.startswith("security/"):
                    sev = _bump(sev, "HIGH")
            out.append((_mk_id_rel("eslint", rule, fname, line, granularity),
                        sev, "eslint"))
    return out

_TSC_LINE = re.compile(
    r"^(?P<file>(?:[A-Za-z]:)?[^(\n]+\.(?:ts|tsx|js|jsx|mts|cts))"
    r"\((?P<line>\d+),\d+\):\s*(?P<kind>error|warning)\s+(?P<code>TS\d+):")
# config-level/global tsc errors carry NO file prefix (TS18003 no inputs,
# TS5023 unknown option, TS2688 missing types) — dropping them would make a
# broken tsconfig (that checked NOTHING) read as a clean green gate.
_TSC_GLOBAL = re.compile(r"^(?P<kind>error|warning)\s+(?P<code>TS\d+):")


def parse_tsc(path, granularity, base=None):
    """tsc --noEmit text output (`file(line,col): error TSxxxx: msg`):
    error -> HIGH (a type error is real breakage), warning -> MEDIUM.
    File-less global errors (broken tsconfig) -> HIGH with location '?'."""
    out = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                s = raw.strip()
                m = _TSC_LINE.match(s)
                if m:
                    sev = "HIGH" if m.group("kind") == "error" else "MEDIUM"
                    out.append((_mk_id_rel("tsc", m.group("code"),
                                           _node_rel(m.group("file"), base),
                                           m.group("line"), granularity),
                                sev, "tsc"))
                    continue
                g = _TSC_GLOBAL.match(s)
                if g:
                    sev = "HIGH" if g.group("kind") == "error" else "MEDIUM"
                    out.append((_mk_id_rel("tsc", g.group("code"), "?", 0,
                                           granularity), sev, "tsc"))
    except OSError:
        return out
    return out


def parse_clippy(path, granularity):
    """`cargo clippy --message-format=json` ? Cargo JSON Lines.

    Each nonblank line must be a UTF-8 JSON object with a string ``reason``.
    Cargo permits an empty output and non-diagnostic records (including
    ``build-finished``); compiler-message diagnostics may legitimately have no
    primary span for end-of-run summaries, so those remain clean noise. Unlike
    permissive text formats, malformed JSON or an invalid diagnostic shape is
    unambiguously bad structured evidence and must reject ingest before the
    ledger is mutated. Error -> HIGH, warning -> MEDIUM; code:null with a
    primary span is a real rustc compile error -> HIGH. Repeats across targets
    are deduped by finding ID."""
    out = []
    seen = set()
    try:
        fh = open(path, "r", encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        _invalid_static_report(path, "Clippy JSONL", exc)
    with fh:
        for line_no, raw in enumerate(fh, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except ValueError as exc:
                _invalid_static_report(path, "Clippy JSONL",
                                       f"line {line_no} is not valid JSON: {exc}")
            if not isinstance(obj, dict):
                _invalid_static_report(path, "Clippy JSONL",
                                       f"line {line_no} must be a JSON object")
            reason = obj.get("reason")
            if not isinstance(reason, str):
                _invalid_static_report(path, "Clippy JSONL",
                                       f"line {line_no} has no string reason")
            if reason != "compiler-message":
                continue

            msg = obj.get("message")
            where = f"compiler message at line {line_no}"
            if not isinstance(msg, dict):
                _invalid_static_report(path, "Clippy JSONL", f"{where} must be an object")
            if not isinstance(msg.get("message"), str):
                _invalid_static_report(path, "Clippy JSONL", f"{where} has invalid message")
            level = msg.get("level")
            if not isinstance(level, str):
                _invalid_static_report(path, "Clippy JSONL", f"{where} has invalid level")
            if "code" not in msg:
                _invalid_static_report(path, "Clippy JSONL", f"{where} is missing code")
            code_data = msg["code"]
            if code_data is not None:
                if not isinstance(code_data, dict) or not isinstance(code_data.get("code"), str):
                    _invalid_static_report(path, "Clippy JSONL", f"{where} has invalid code")
            spans = msg.get("spans")
            if not isinstance(spans, list):
                _invalid_static_report(path, "Clippy JSONL", f"{where} has invalid spans")
            for span_index, candidate in enumerate(spans):
                if not isinstance(candidate, dict):
                    _invalid_static_report(
                        path, "Clippy JSONL", f"{where} has non-object span {span_index}")
                if not isinstance(candidate.get("is_primary"), bool):
                    _invalid_static_report(
                        path, "Clippy JSONL", f"{where} has invalid is_primary in span {span_index}")

            if level not in ("error", "warning"):
                continue
            span = next((candidate for candidate in spans if candidate["is_primary"]), None)
            if span is None:
                continue  # span-less = summary diagnostic, not a finding
            fname = span.get("file_name")
            line = span.get("line_start")
            if not isinstance(fname, str) or not fname:
                _invalid_static_report(path, "Clippy JSONL", f"{where} has invalid primary file_name")
            if isinstance(line, bool) or not isinstance(line, int) or line < 1:
                _invalid_static_report(path, "Clippy JSONL", f"{where} has invalid primary line_start")
            if code_data is None:
                sev, rule = "HIGH", "compile-error"
            else:
                sev = "HIGH" if level == "error" else "MEDIUM"
                rule = code_data["code"]
            fid = _mk_id_rel("clippy", rule, fname, line, granularity)
            if fid in seen:
                continue
            seen.add(fid)
            out.append((fid, sev, "clippy"))
    return out

def _sarif_rel(uri, base):
    """SARIF uris arrive as file:///C:/repo/src/A.cs (Roslyn emits absolute,
    percent-encoded) — strip scheme, unquote, and relativize against the repo
    so finding IDs survive machine/worktree moves (same job as _node_rel)."""
    from urllib.parse import unquote
    p = unquote(uri).replace("file:///", "").replace("file://", "")
    if base:
        try:
            rp = os.path.relpath(p, base)
            if not rp.startswith(".."):
                p = rp
        except ValueError:
            pass  # different drive on Windows — keep as-is
    return p.replace("\\", "/")


def parse_sarif(path, granularity, tool="sarif", base=None):
    """SARIF (the universal static-analysis format — Roslyn analyzers via
    MSBuild /p:ErrorLog="...,version=2", and many other tools). results[].level:
    error -> HIGH, warning -> MEDIUM, note -> INFO (absent defaults to warning).
    Suppressed results (#pragma / [SuppressMessage] — 'suppressions' in v2,
    'suppressionStates' in v1) are skipped: a suppressed diagnostic must not
    phantom-gate a build that compiles clean. v1 location shape
    (resultFile/analysisTarget) supported as fallback — Roslyn's ErrorLog
    emits v1 unless ',version=2' is requested."""
    sev_map = {"error": "HIGH", "warning": "MEDIUM", "note": "INFO", "none": "INFO"}
    out = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        _invalid_static_report(path, "SARIF JSON", exc)
    if not isinstance(data, dict):
        _invalid_static_report(path, "SARIF JSON", "expected a JSON object")
    runs = data.get("runs")
    if not isinstance(runs, list):
        _invalid_static_report(path, "SARIF JSON", "expected runs to be an array")
    for run_index, run in enumerate(runs):
        if not isinstance(run, dict):
            _invalid_static_report(
                path, "SARIF JSON", f"run at index {run_index} must be an object")
        results = run.get("results", [])
        if not isinstance(results, list):
            _invalid_static_report(
                path, "SARIF JSON", f"run at index {run_index} has invalid results")
        for result_index, res in enumerate(results):
            where = f"result at {run_index}:{result_index}"
            if not isinstance(res, dict):
                _invalid_static_report(path, "SARIF JSON", f"{where} must be an object")
            for suppression_key in ("suppressions", "suppressionStates"):
                suppressions = res.get(suppression_key)
                if suppressions is not None and not isinstance(suppressions, list):
                    _invalid_static_report(
                        path, "SARIF JSON", f"{where} has invalid {suppression_key}")
            if res.get("suppressions") or res.get("suppressionStates"):
                continue
            level = res.get("level", "warning")
            if not isinstance(level, str):
                _invalid_static_report(path, "SARIF JSON", f"{where} has invalid level")
            rule = res.get("ruleId", "?")
            if rule is None:
                rule = "?"
            if not isinstance(rule, str):
                _invalid_static_report(path, "SARIF JSON", f"{where} has invalid ruleId")
            sev = sev_map.get(level.lower(), "MEDIUM")
            fname, line = "?", 0
            locs = res.get("locations", [])
            if not isinstance(locs, list):
                _invalid_static_report(path, "SARIF JSON", f"{where} has invalid locations")
            if locs:
                loc = locs[0]
                if not isinstance(loc, dict):
                    _invalid_static_report(
                        path, "SARIF JSON", f"{where} has a non-object location")
                phys = loc.get("physicalLocation", {})
                if not isinstance(phys, dict):
                    _invalid_static_report(
                        path, "SARIF JSON", f"{where} has invalid physicalLocation")
                art = phys.get("artifactLocation", {})
                region = phys.get("region", {})
                if not isinstance(art, dict) or not isinstance(region, dict):
                    _invalid_static_report(
                        path, "SARIF JSON", f"{where} has invalid physical location fields")
                uri = art.get("uri")
                if not uri:
                    v1 = loc.get("resultFile") or loc.get("analysisTarget") or {}
                    if not isinstance(v1, dict):
                        _invalid_static_report(
                            path, "SARIF JSON", f"{where} has invalid SARIF v1 location")
                    uri = v1.get("uri")
                    region = v1.get("region") or {}
                    if not isinstance(region, dict):
                        _invalid_static_report(
                            path, "SARIF JSON", f"{where} has invalid SARIF v1 region")
                if uri is not None and not isinstance(uri, str):
                    _invalid_static_report(path, "SARIF JSON", f"{where} has invalid uri")
                if uri:
                    fname = _sarif_rel(uri, base)
                line = region.get("startLine", 0)
                if isinstance(line, bool) or not isinstance(line, int):
                    _invalid_static_report(
                        path, "SARIF JSON", f"{where} has invalid startLine")
            out.append((_mk_id_rel(tool, rule, fname, line, granularity), sev, tool))
    return out

_CLANG_TIDY_LINE = re.compile(
    r"^(?P<file>(?:[A-Za-z]:)?[^:\n]+\.(?:c|cc|cpp|cxx|h|hh|hpp|hxx|tpp|ipp|inl|mm|cu)):"
    r"(?P<line>\d+):\d+:\s*(?P<kind>error|warning):\s*.*?"
    r"(?:\[(?P<checks>[\w.,-]+)\])?\s*$")


def parse_clang_tidy(path, granularity, base=None):
    """clang-tidy text output (`file:line:col: warning: msg [check-a,check-b]`):
    error -> HIGH, warning -> MEDIUM; security-flavored checks (cert-*, or any
    check containing 'security') floored to HIGH — same discipline as
    findsecbugs/eslint-security. Lines without a [check] tag (raw compiler
    diagnostics passed through) are kept as rule 'diagnostic'. clang-tidy
    prints ABSOLUTE paths — relativize against the repo so finding IDs
    survive machine/worktree moves (same job as tsc's _node_rel)."""
    out = []
    try:
        fh = open(path, "r", encoding="utf-8", errors="replace")
    except OSError:
        return out
    with fh:
        for raw in fh:
            m = _CLANG_TIDY_LINE.match(raw.strip())
            if not m:
                continue
            checks = m.group("checks") or "diagnostic"
            rule = checks.split(",")[0]
            sev = "HIGH" if m.group("kind") == "error" else "MEDIUM"
            if rule.startswith("cert-") or "security" in rule:
                sev = _bump(sev, "HIGH")
            out.append((_mk_id_rel("clang-tidy", rule,
                                   _node_rel(m.group("file"), base),
                                   m.group("line"), granularity),
                        sev, "clang-tidy"))
    return out


def _prev_finding_ids(node, tool):
    for s in reversed(node["iterations"]):
        if s.get("tool") == tool and s.get("finding_ids") is not None:
            return set(s["finding_ids"])
    return None


# --------------------------------------------------------------------------- #
# subcommands
# --------------------------------------------------------------------------- #
SUPPORTED_REPO_TYPES = {
    "maven", "flutter", "python", "node", "go", "rust", "dotnet", "cpp",
    "gradle", "swift", "ant",
}


def _has_text(value):
    return isinstance(value, str) and bool(value.strip())


# risk_profile (kit 1.45.0, ADR-001): a NAMED PRESET, not a fixed engine gate. It expands
# to knobs the config already understands; any explicit `defaults` key wins per-key; the
# origin is tracked for provenance. An overridable default, never an imposed opinion.
GOLDEN_REQUIRED_CEILING = 49  # ADR-002: no approved golden -> NOT READY (does not pass merge)
RISK_PROFILES = {
    "A": {"qa_tools_order": ["code-review"]},
    "B": {"qa_tools_order": ["code-review", "improve"]},
    "C": {"qa_tools_order": ["code-review", "judgment-day", "improve"]},
    "D": {"qa_tools_order": ["code-review", "judgment-day", "improve"],
          "coverage_threshold": 70, "golden_required": True},
    "E": {"qa_tools_order": ["code-review", "judgment-day", "improve"],
          "coverage_threshold": 80, "golden_required": True},
}


def _apply_risk_profile(defaults):
    """Expand defaults['risk_profile'] into concrete knobs UNDER any explicit value (explicit
    wins per key). Records the profile-provided keys in defaults['_risk_profile_keys'] so a cap
    can label its provenance. Mutates + returns defaults. Unknown profile -> SystemExit (a
    declared risk level is never inert -- INV-RISK-01)."""
    profile = defaults.get("risk_profile")
    if profile is None:
        return defaults
    if profile not in RISK_PROFILES:
        raise SystemExit("[qa_ledger] invalid config: risk_profile must be one of "
                         + ", ".join(sorted(RISK_PROFILES)))
    provided = []
    for key, value in RISK_PROFILES[profile].items():
        if key not in defaults:  # an explicit declaration always wins
            defaults[key] = list(value) if isinstance(value, list) else value
            provided.append(key)
    defaults["_risk_profile_keys"] = provided
    return defaults


def _validate_init_config(cfg):
    """Validate only the engine's core init contract before creating a ledger."""
    if not isinstance(cfg, dict):
        raise SystemExit("[qa_ledger] invalid config: root must be an object")
    defaults = cfg.get("defaults", {})
    if not isinstance(defaults, dict):
        raise SystemExit("[qa_ledger] invalid config: defaults must be an object")
    # expand a named risk profile into concrete knobs BEFORE validating them, so the merged
    # values (qa_tools_order, coverage_threshold, golden_required) flow through the checks
    # below. Explicit config wins per key; an unknown profile fails loud (INV-RISK-01).
    _apply_risk_profile(defaults)
    if "golden_required" in defaults and not isinstance(defaults["golden_required"], bool):
        raise SystemExit("[qa_ledger] invalid config: golden_required must be a boolean")

    repos = cfg.get("repos", [])
    if not isinstance(repos, list):
        raise SystemExit("[qa_ledger] invalid config: repos must be a list")
    names = set()
    for index, repo in enumerate(repos):
        if not isinstance(repo, dict):
            raise SystemExit(
                f"[qa_ledger] invalid config: repos[{index}] must be an object")
        name = repo.get("name")
        path = repo.get("path")
        repo_type = repo.get("type")
        if not _has_text(name):
            raise SystemExit(
                f"[qa_ledger] invalid config: repos[{index}].name must be nonempty")
        if name == "integration":
            raise SystemExit(
                "[qa_ledger] invalid config: repo name 'integration' is reserved")
        if name in names:
            raise SystemExit(
                f"[qa_ledger] invalid config: duplicate repo name '{name}'")
        names.add(name)
        if not _has_text(path):
            raise SystemExit(
                f"[qa_ledger] invalid config: repo '{name}' path must be nonempty")
        if repo_type not in SUPPORTED_REPO_TYPES:
            supported = ", ".join(sorted(SUPPORTED_REPO_TYPES))
            raise SystemExit(
                f"[qa_ledger] invalid config: repo '{name}' type must be one of {supported}")

    if "qa_tools_order" in defaults:
        order = defaults["qa_tools_order"]
        if (not isinstance(order, list) or not order
                or any(not _has_text(tool) for tool in order)
                or len(set(order)) != len(order)):
            raise SystemExit(
                "[qa_ledger] invalid config: qa_tools_order must contain unique nonempty strings")

    if "coverage_threshold" in defaults:
        value = defaults["coverage_threshold"]
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or value < 0 or value > 100):
            raise SystemExit(
                "[qa_ledger] invalid config: coverage_threshold must be between 0 and 100")
    for key in ("max_iterations", "tools_per_cycle"):
        if key in defaults:
            value = defaults[key]
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise SystemExit(
                    f"[qa_ledger] invalid config: {key} must be a positive integer")

    integration = cfg.get("integration", {})
    if not isinstance(integration, dict):
        raise SystemExit("[qa_ledger] invalid config: integration must be an object")
    if "enabled" in integration and not isinstance(integration["enabled"], bool):
        raise SystemExit("[qa_ledger] invalid config: integration.enabled must be boolean")

    if "severity_gate" in defaults:
        gate = defaults["severity_gate"]
        if (not isinstance(gate, list)
                or any(not isinstance(level, str) or level not in SEVERITY_ORDER
                       for level in gate)):
            raise SystemExit("[qa_ledger] invalid config: severity_gate must be a list of known severities")

    def finite_number(value):
        return (not isinstance(value, bool) and isinstance(value, (int, float))
                and math.isfinite(value))

    readiness_weights = defaults.get("readiness_weights", {})
    if not isinstance(readiness_weights, dict):
        raise SystemExit("[qa_ledger] invalid config: readiness_weights must be an object")
    unknown_weights = sorted(set(readiness_weights) - set(DEFAULT_WEIGHTS))
    if unknown_weights:
        raise SystemExit("[qa_ledger] invalid config: readiness_weights has unknown dimension(s): " + ", ".join(unknown_weights))
    for key, value in readiness_weights.items():
        if not finite_number(value) or value < 0:
            raise SystemExit(f"[qa_ledger] invalid config: readiness_weights.{key} must be a finite nonnegative number")

    readiness_caps = defaults.get("readiness_caps", {})
    if not isinstance(readiness_caps, dict):
        raise SystemExit("[qa_ledger] invalid config: readiness_caps must be an object")
    unknown_caps = sorted(set(readiness_caps) - set(DEFAULT_CAPS))
    if unknown_caps:
        raise SystemExit("[qa_ledger] invalid config: readiness_caps has unknown cap(s): " + ", ".join(unknown_caps))
    for key, value in readiness_caps.items():
        if not finite_number(value) or value < 0 or value > 100:
            raise SystemExit(f"[qa_ledger] invalid config: readiness_caps.{key} must be a finite percentage between 0 and 100")

    if "static_gate_zero_at" in defaults:
        value = defaults["static_gate_zero_at"]
        if not finite_number(value) or value <= 0:
            raise SystemExit("[qa_ledger] invalid config: static_gate_zero_at must be a positive finite number")

    effective_weights = {**DEFAULT_WEIGHTS, **readiness_weights}
    local_dimensions = ("coverage", "static_gate", "convergence")
    if repos and sum(effective_weights[key] for key in local_dimensions) <= 0:
        raise SystemExit("[qa_ledger] invalid config: effective readiness_weights must leave positive weight for per-repo readiness")

    global_dimensions = ["acceptance", "adr", "coverage", "static_gate", "convergence"]
    if integration.get("enabled", False):
        global_dimensions.append("integration")
    dimension_sets = [global_dimensions]
    if "readiness_weights" in defaults and "acceptance" not in readiness_weights:
        dimension_sets.append([key for key in global_dimensions if key != "acceptance"])
    if any(sum(effective_weights[key] for key in dimensions) <= 0 for dimensions in dimension_sets):
        raise SystemExit("[qa_ledger] invalid config: effective readiness_weights must sum to a positive value for every possible readiness dimension set")


def _validate_iteration(node, tool, iteration):
    if isinstance(iteration, bool) or not isinstance(iteration, int) or iteration < 1:
        raise SystemExit("[qa_ledger] iteration must be >= 1")
    latest = max(
        (record.get("iteration", 0) for record in node.get("iterations", [])
         if record.get("tool") == tool),
        default=0,
    )
    if iteration < latest:
        raise SystemExit(
            f"[qa_ledger] iteration {iteration} is older than latest iteration "
            f"{latest} for {tool}")


def _validate_log_step_counts(args):
    names = ("reported", "gated_reported", "fixed", "deferred",
             "suppressed", "files_changed")
    for name in names:
        value = getattr(args, name)
        if value < 0:
            raise SystemExit(f"[qa_ledger] {name.replace('_', '-')} must be nonnegative")
    if args.gated_reported > args.reported:
        raise SystemExit("[qa_ledger] gated-reported cannot exceed reported")


def cmd_init(args):
    cfg = _load(args.config)
    _validate_init_config(cfg)
    defaults = cfg.get("defaults", {})
    ledger = {
        "schema": "dev-loop/qa-ledger@1",
        "run_id": datetime.now().strftime("%Y%m%d-%H%M%S"),
        "started_at": _now(),
        "updated_at": _now(),
        "config": cfg,
        "step_counter": 0,
        "repos": {
            r["name"]: {"type": r["type"], "path": r["path"],
                        "snapshots": [], "iterations": []}
            for r in cfg.get("repos", [])
        },
        "integration": {"type": "maven", "snapshots": [], "iterations": []},
        "steps": [],
        "escalations": [],
        "production_findings": [],
        "spec_doubts": [],
        "spec_change_requests": [],
    }
    _save(args.out, ledger)
    print(f"[qa_ledger] initialized {args.out} "
          f"(run {ledger['run_id']}, {len(ledger['repos'])} repos, "
          f"coverage_threshold={defaults.get('coverage_threshold')})")


def _origin_label(origin):
    """Render an origin for humans. An unmeasurable tree state reads `unknown`, never
    `clean` -- the whole reason the field distinguishes False from None."""
    o = origin or {}
    sha = (o.get("commit") or "")[:8] or "no-commit"
    dirty = o.get("dirty")
    state = "unknown" if dirty is None else ("dirty" if dirty else "clean")
    return "%s/%s" % (sha, state)


def _scope_path(ledger, name):
    """Repo path for a scope, guarding the SYNTHETIC `integration` scope -- never present
    in config["repos"], where _repo_cfg exits on unknown names. This crash class shipped
    once (the clean-room gate, 1.63.0) and nearly shipped twice (spec-drift at pass close,
    caught by fresh review): two recurrences make it a helper, not a per-site pattern."""
    cfg = _repo_cfg(ledger, name) if name != "integration" else {"path": "."}
    return cfg.get("path", ".")


def _evidence_origin(repo_path):
    """WHERE the evidence came from: the commit it was measured at, and whether the tree
    was clean (ADR-007). The engine's freshness check compares file MTIMES, so until now a
    snapshot could say "tests green" without being able to say green AT WHAT -- provenance
    true of the tree, not of the commit that will merge.

    Absence is NAMED, never guessed: no git, no repo, unreadable -> both None. `dirty is
    None` must never read as clean; that distinction is the entire point of recording it.
    Advisory only -- nothing here scores or blocks.

    Untracked files COUNT as dirty (plain --porcelain): an untracked file the suite depends
    on is exactly the contamination this records, and treating untracked as invisible is a
    mistake this engine already paid for once (fast-path, 1.57.0)."""
    origin = {"commit": None, "dirty": None}

    def _git(*args):
        # OSError covers BOTH ways this used to take the whole snapshot down: git absent
        # from PATH (FileNotFoundError) and a repo_path that does not exist or is a file
        # (NotADirectoryError). Every sibling measurement in _snapshot already tolerates a
        # missing path; provenance must not be the one field that can crash the command it
        # only annotates. Same posture as _spike_branch. (Both found by fresh review, both
        # reproduced: an unconfigured or not-yet-cloned repo path is ordinary, not exotic.)
        try:
            return subprocess.run(["git"] + list(args), cwd=repo_path,
                                  capture_output=True, text=True, encoding="utf-8",
                                  errors="replace")
        except OSError:
            return None

    rev = _git("rev-parse", "HEAD")
    if rev is not None and rev.returncode == 0 and rev.stdout.strip():
        origin["commit"] = rev.stdout.strip()
    # `-- .` scopes the answer to repo_path. Without it, a repo entry pointing at a
    # SUBDIRECTORY of a larger working tree reports the whole outer repo's state, so an
    # unrelated edit elsewhere would mark this repo's evidence dirty -- and the ADR would
    # be claiming a per-path fact the code did not deliver.
    st = _git("status", "--porcelain", "--", ".")
    if st is not None and st.returncode == 0:
        origin["dirty"] = bool(st.stdout.strip())
    return origin


def _snapshot(ledger, name):
    node = _repo_node(ledger, name)
    cfg = _repo_cfg(ledger, name) if name != "integration" else {"path": ".", "type": "maven"}
    path = cfg["path"]
    rtype = cfg["type"]
    snap = {
        "at": _now(),
        "coverage": coverage(path, rtype),
        "tests": test_count(path, rtype),
        "loc": count_loc(path, rtype),
        "origin": _evidence_origin(path),
    }
    node["snapshots"].append(snap)
    return snap


def cmd_snapshot(args):
    ledger = _load(args.ledger)
    snap = _snapshot(ledger, args.repo)
    ledger["step_counter"] += 1
    ledger["steps"].append({"n": ledger["step_counter"], "at": _now(),
                            "kind": "snapshot", "repo": args.repo,
                            "phase": args.phase})
    _save(args.ledger, ledger)
    cov, tests, loc = snap["coverage"], snap["tests"], snap["loc"]
    freshness = tests.get("freshness", {})
    print(f"[qa_ledger] snapshot {args.repo} ({args.phase}): "
          f"coverage={cov['pct']}% (found={cov['report_found']}), "
          f"tests={tests['total']} (found={tests['report_found']}), "
          f"freshness={freshness.get('status', 'unknown')}, "
          f"origin={_origin_label(snap.get('origin'))}, "
          f"prod_loc={loc['prod_loc']}, test_loc={loc['test_loc']}")
    if freshness.get("status") == "stale":
        print(f"  test evidence stale: {freshness.get('reason')}")


def cmd_check_coverage(args):
    ledger = _load(args.ledger)
    cfg = _repo_cfg(ledger, args.repo)
    threshold = args.threshold
    if threshold is None:
        threshold = ledger["config"].get("defaults", {}).get("coverage_threshold", 60)
    cov = coverage(cfg["path"], cfg["type"])
    pct = cov["pct"]
    below = pct < threshold
    state = "BELOW" if below else "OK"
    if not cov["report_found"]:
        # No coverage report at all == treat as below threshold (needs char tests),
        # but flag loudly so the skill knows tests simply haven't been run yet.
        print(f"[qa_ledger] {args.repo}: NO coverage report found "
              f"(threshold {threshold}%) -> treat as BELOW. "
              f"Run the test command first if a report was expected.")
        sys.exit(1)
    print(f"[qa_ledger] {args.repo}: coverage {pct}% vs threshold {threshold}% -> {state}")
    sys.exit(1 if below else 0)


def _to_bool(s):
    return str(s).strip().lower() in {"1", "true", "yes", "y", "ok", "pass", "passed"}


def cmd_log_step(args):
    ledger = _load(args.ledger)
    node = _repo_node(ledger, args.repo)
    _validate_iteration(node, args.tool, args.iteration)
    _validate_log_step_counts(args)
    ledger["step_counter"] += 1
    fp = None
    ids = None
    if args.fingerprint:
        ids = sorted(x.strip() for x in args.fingerprint.split(",") if x.strip())
        fp = hashlib.sha1(("|".join(ids)).encode()).hexdigest()[:12] if ids else None
    record = {
        "n": ledger["step_counter"],
        "at": _now(),
        "iteration": args.iteration,
        "tool": args.tool,
        "category": "agent",
        "reported": args.reported,
        "gated_reported": args.gated_reported,
        "fixed": args.fixed,
        "deferred": args.deferred,
        "suppressed": args.suppressed,
        "tests_passed": _to_bool(args.tests_passed),
        "files_changed": args.files_changed,
        "fingerprint": fp,
        "finding_ids": ids,
        "note": args.note,
    }
    node["iterations"].append(record)
    ledger["steps"].append({"n": record["n"], "at": record["at"], "kind": "qa-step",
                            "repo": args.repo, "tool": args.tool,
                            "iteration": args.iteration})
    _save(args.ledger, ledger)
    print(f"[qa_ledger] step #{record['n']} logged: {args.repo}/{args.tool} "
          f"iter={args.iteration} reported={args.reported} "
          f"gated={args.gated_reported} fixed={args.fixed} "
          f"tests_passed={record['tests_passed']} files_changed={args.files_changed}")


def cmd_ingest_gate(args):
    """Parse Checkstyle/PMD/SpotBugs/FindSecBugs reports and log one static-gate
    step per linter. `fixed` is computed by diffing finding-IDs against the most
    recent prior run of the same linter, so it is real, not estimated."""
    ledger = _load(args.ledger)
    cfg = _repo_cfg(ledger, args.repo)
    if args.iteration < 1:
        raise SystemExit("[qa_ledger] iteration must be >= 1")
    base = cfg["path"]
    defaults = ledger["config"].get("defaults", {})
    gate = defaults.get("severity_gate", ["BLOCKER", "CRITICAL", "HIGH"])
    gran = args.id_granularity or defaults.get("id_granularity", "line")

    rtype = cfg.get("type", "maven")
    collected = []
    present = set()  # tools whose report file actually existed this run
    if rtype == "python":
        ruff_files = _find_all(base, [os.path.join("reports", "ruff.json"),
                                      "ruff.json"], args.ruff)
        for path in ruff_files:
            collected += parse_ruff(path, gran)
        if ruff_files:
            present.add("ruff")
        mypy_files = _find_all(base, [os.path.join("reports", "mypy.txt"),
                                      "mypy.txt"], args.mypy)
        for path in mypy_files:
            collected += parse_mypy(path, gran)
        if mypy_files:
            present.add("mypy")
    elif rtype == "node":
        es_files = _find_all(base, [os.path.join("reports", "eslint.json"),
                                    "eslint.json"], args.eslint)
        for path in es_files:
            collected += parse_eslint(path, gran, base)
        if es_files:
            present.add("eslint")
        tsc_files = _find_all(base, [os.path.join("reports", "tsc.txt"),
                                     "tsc.txt"], args.tsc)
        for path in tsc_files:
            collected += parse_tsc(path, gran, base)
        if tsc_files:
            present.add("tsc")
    elif rtype == "go":
        gl_files = _find_all(base, [os.path.join("reports", "golangci.xml"),
                                    "golangci.xml"], args.golangci)
        for path in gl_files:
            collected += parse_checkstyle(path, gran, tool="golangci", base=base)
        if gl_files:
            present.add("golangci")
    elif rtype == "rust":
        cl_files = _find_all(base, [os.path.join("reports", "clippy.json"),
                                    "clippy.json"], args.clippy)
        for path in cl_files:
            collected += parse_clippy(path, gran)
        if cl_files:
            present.add("clippy")
    elif rtype == "dotnet":
        sa_files = _find_all(base, [os.path.join("reports", "analysis.sarif"),
                                    "analysis.sarif"], args.sarif)
        for path in sa_files:
            collected += parse_sarif(path, gran, tool="roslyn", base=base)
        if sa_files:
            present.add("roslyn")
    elif rtype == "cpp":
        ct_files = _find_all(base, [os.path.join("reports", "clang-tidy.txt"),
                                    "clang-tidy.txt"], args.clang_tidy)
        for path in ct_files:
            collected += parse_clang_tidy(path, gran, base=base)
        if ct_files:
            present.add("clang-tidy")
    elif rtype == "gradle":
        dk_files = _find_all(base, ["**/build/reports/detekt/detekt.xml",
                                    os.path.join("reports", "detekt.xml"),
                                    "detekt.xml"], args.detekt)
        for path in dk_files:
            collected += parse_checkstyle(path, gran, tool="detekt", base=base)
        if dk_files:
            present.add("detekt")
    elif rtype == "swift":
        sl_files = _find_all(base, [os.path.join("reports", "swiftlint.xml"),
                                    "swiftlint.xml"], args.swiftlint)
        for path in sl_files:
            collected += parse_checkstyle(path, gran, tool="swiftlint", base=base)
        if sl_files:
            present.add("swiftlint")
    else:
        cs_files = _find_all(base, ["**/target/checkstyle-result.xml",
                                    "**/checkstyle-result.xml"], args.checkstyle)
        for path in cs_files:
            collected += parse_checkstyle(path, gran)
        if cs_files:
            present.add("checkstyle")
        pmd_files = _find_all(base, ["**/target/pmd.xml", "**/pmd.xml"], args.pmd)
        for path in pmd_files:
            collected += parse_pmd(path, gran)
        if pmd_files:
            present.add("pmd")
        sb_files = _find_all(base, ["**/target/spotbugsXml.xml",
                                    "**/spotbugsXml.xml"], args.spotbugs)
        for path in sb_files:
            collected += parse_spotbugs(path, gran)
        if sb_files:
            present.update({"spotbugs", "findsecbugs"})

    combined_name = {"python": "python-qa-gate",
                     "node": "node-qa-gate",
                     "go": "go-qa-gate",
                     "rust": "rust-qa-gate",
                     "dotnet": "dotnet-qa-gate",
                     "cpp": "cpp-qa-gate",
                     "gradle": "gradle-qa-gate",
                     "swift": "swift-qa-gate"}.get(rtype, "java-qa-gate")
    by_tool = {}
    for fid, sev, tool in collected:
        by_tool.setdefault(tool, []).append((fid, sev))
    if args.combined:
        merged = [item for items in by_tool.values() for item in items]
        by_tool = {combined_name: merged} if (merged or present) else {}
        seed = {combined_name} if present else set()
    else:
        seed = present

    node = _repo_node(ledger, args.repo)
    # A linter whose report EXISTS but is now clean still gets a zero step, so the
    # fix is credited and convergence sees the clean state. An ABSENT report is NOT
    # treated as clean (the gate simply didn't run) — its last state stands.
    for tool in seed:
        by_tool.setdefault(tool, [])

    results = []
    for tool in by_tool:
        _validate_iteration(node, tool, args.iteration)
    for tool, items in sorted(by_tool.items()):
        ids = sorted(set(fid for fid, _ in items))
        gated = sum(1 for _, sev in items if _at_or_above(sev, gate))
        below = len(items) - gated
        prev = _prev_finding_ids(node, tool)
        if prev is not None:
            resolved = len(prev - set(ids))
            new = len(set(ids) - prev)
        else:
            resolved = new = 0
        sev_counts = {}
        for _fid, sev in items:
            sev_counts[sev] = sev_counts.get(sev, 0) + 1
        ledger["step_counter"] += 1
        fp = hashlib.sha1(("|".join(ids)).encode()).hexdigest()[:12] if ids else None
        rec = {
            "n": ledger["step_counter"], "at": _now(), "iteration": args.iteration,
            "tool": tool, "category": "static-gate",
            "reported": len(items), "gated_reported": gated,
            "fixed": resolved, "deferred": below, "suppressed": 0,
            "new_regressions": new, "severity_counts": sev_counts,
            "tests_passed": None, "files_changed": 0,
            "fingerprint": fp, "finding_ids": ids, "note": args.note,
        }
        node["iterations"].append(rec)
        ledger["steps"].append({"n": rec["n"], "at": rec["at"], "kind": "static-gate",
                                "repo": args.repo, "tool": tool,
                                "iteration": args.iteration})
        results.append((tool, len(items), gated, resolved, new, below))
    _save(args.ledger, ledger)

    if not results:
        flags = {"python": "--ruff/--mypy", "node": "--eslint/--tsc",
                 "go": "--golangci", "rust": "--clippy", "dotnet": "--sarif",
                 "cpp": "--clang-tidy", "gradle": "--detekt",
                 "swift": "--swiftlint"}.get(rtype, "--checkstyle/--pmd/--spotbugs")
        print(f"[qa_ledger] ingest-gate {args.repo}: no linter reports found under "
              f"'{base}'. Run the linters first, or pass explicit {flags} paths.")
        return
    for tool, total, gated, resolved, new, below in results:
        print(f"[qa_ledger] {args.repo}/{tool}: reported={total} gated={gated} "
              f"fixed_since_prev={resolved} new={new} below_gate={below}")


def _latest_static_by_tool(node):
    latest = {}
    for s in node["iterations"]:
        if s.get("category") == "static-gate":
            latest[s["tool"]] = s  # iteration order preserved -> last wins
    return latest


def _gate_rollup(ledger):
    """Collapse the latest persisted gate record per (repo, tool) into a flat list
    for the single-verdict view (1.25.0, anti-ceremony). Reads FACTS already in the
    ledger — it never re-runs a gate nor recomputes the readiness score; a record is
    'blocking' iff its latest state gated at least one finding (gated_reported > 0).
    This is presentation over persisted facts: the score/caps are untouched, so the
    KPI stays exactly what it was before the rollup existed."""
    gates = []
    for rname, rnode in ledger["repos"].items():
        for tool, rec in _latest_static_by_tool(rnode).items():
            gates.append({"repo": rname, "tool": tool,
                          "blocking": rec.get("gated_reported", 0) > 0,
                          "gated": rec.get("gated_reported", 0),
                          "note": rec.get("note")})
    return sorted(gates, key=lambda g: (g["repo"], g["tool"]))


# --------------------------------------------------------------------------- #
# discovery intake (kit 1.36.0+): facts that reopen discovery instead of letting
# the agent silently code around reality. Production findings are real-world facts;
# spec-doubts are builder-raised doubts requiring human review; SPEC change requests
# are the human-signed bridge from a doubt/finding to an amended contract. All are
# persisted in the ledger and surfaced by readiness; none is hidden LLM narration.
# --------------------------------------------------------------------------- #
def _next_prefixed_id(rows, prefix):
    n = 0
    rx = re.compile(r"^%s-(\d+)$" % re.escape(prefix))
    for row in rows:
        m = rx.match(str(row.get("id", "")))
        if m:
            n = max(n, int(m.group(1)))
    return "%s-%03d" % (prefix, n + 1)


def _find_by_id(rows, rid, noun):
    for row in rows:
        if row.get("id") == rid:
            return row
    raise SystemExit("[qa_ledger] unknown %s id '%s'" % (noun, rid))


def _require_open_resolution(row, noun):
    status = row.get("status")
    if status is None:
        raise SystemExit(f"[qa_ledger] {noun} '{row.get('id')}' has no status; legacy rows are fail-closed and cannot be resolved")
    if status != "open":
        raise SystemExit(f"[qa_ledger] {noun} '{row.get('id')}' is not open (status '{status}'); only open records can be resolved")


def _touch_event(ledger, kind, rid, repo=None):
    ledger["step_counter"] = ledger.get("step_counter", 0) + 1
    ledger.setdefault("steps", []).append({"n": ledger["step_counter"],
                                           "at": _now(), "kind": kind,
                                           "id": rid, "repo": repo})


def _open_production_findings(ledger, repo=None, gate_only=False):
    gate = ledger.get("config", {}).get("defaults", {}).get(
        "severity_gate", ["BLOCKER", "CRITICAL", "HIGH"])
    out = []
    for row in ledger.get("production_findings", []):
        if row.get("resolved_at"):
            continue
        if repo is not None and row.get("repo") != repo:
            continue
        if gate_only and not _at_or_above(row.get("severity", "HIGH"), gate):
            continue
        out.append(row)
    return sorted(out, key=lambda r: r.get("id", ""))


def _open_spec_doubts(ledger, repo=None):
    out = []
    for row in ledger.get("spec_doubts", []):
        if row.get("resolved_at"):
            continue
        if repo is not None and row.get("repo") != repo:
            continue
        out.append(row)
    return sorted(out, key=lambda r: r.get("id", ""))


def _open_spec_change_requests(ledger, repo=None):
    out = []
    for row in ledger.get("spec_change_requests", []):
        if row.get("resolved_at"):
            continue
        if repo is not None and row.get("repo") != repo:
            continue
        out.append(row)
    return sorted(out, key=lambda r: r.get("id", ""))


def _discovery_intake(ledger, repo=None):
    return {"production_findings": _open_production_findings(ledger, repo),
            "spec_doubts": _open_spec_doubts(ledger, repo),
            "spec_change_requests": _open_spec_change_requests(ledger, repo)}


def cmd_production_finding(args):
    """Record or resolve a post-merge/production finding as discovery intake."""
    ledger = _load(args.ledger)
    rows = ledger.setdefault("production_findings", [])
    if args.resolve:
        if not args.id:
            raise SystemExit("[qa_ledger] --resolve requires --id PF-nnn")
        if not _has_text(args.note):
            raise SystemExit(
                "[qa_ledger] production-finding --resolve requires a nonempty --note")
        row = _find_by_id(rows, args.id, "production finding")
        _require_open_resolution(row, "production finding")
        row["status"] = "resolved"
        row["resolved_at"] = _now()
        row["resolution_note"] = args.note
        _touch_event(ledger, "production-finding:resolve", row["id"], row.get("repo"))
        _save(args.ledger, ledger)
        print("[qa_ledger] production-finding %s resolved -- %s" %
              (row["id"], args.note or "no note"))
        return
    if not args.repo or not args.title or not args.evidence:
        raise SystemExit("[qa_ledger] production-finding requires --repo, --title and --evidence")
    _repo_node(ledger, args.repo)  # validate repo
    sev = (args.severity or "HIGH").upper()
    if sev not in SEVERITY_ORDER:
        raise SystemExit("[qa_ledger] invalid severity '%s'" % args.severity)
    row = {"id": _next_prefixed_id(rows, "PF"), "at": _now(), "status": "open",
           "repo": args.repo, "severity": sev, "source": args.source,
           "title": args.title, "evidence": args.evidence,
           "note": args.note, "resolved_at": None}
    rows.append(row)
    _touch_event(ledger, "production-finding", row["id"], args.repo)
    _save(args.ledger, ledger)
    print("[qa_ledger] production-finding %s logged: %s/%s -- %s" %
          (row["id"], args.repo, sev, args.title))


def cmd_spec_doubt(args):
    """Record or resolve a SPEC doubt/SPEC-WRONG finding raised during build."""
    ledger = _load(args.ledger)
    rows = ledger.setdefault("spec_doubts", [])
    if args.resolve:
        if not args.id:
            raise SystemExit("[qa_ledger] --resolve requires --id SD-nnn")
        if not _has_text(args.decision):
            raise SystemExit(
                "[qa_ledger] spec-doubt --resolve requires a nonempty --decision")
        row = _find_by_id(rows, args.id, "spec-doubt")
        _require_open_resolution(row, "spec-doubt")
        row["status"] = "resolved"
        row["resolved_at"] = _now()
        row["decision"] = args.decision
        row["resolution_note"] = args.note
        _touch_event(ledger, "spec-doubt:resolve", row["id"], row.get("repo"))
        _save(args.ledger, ledger)
        print("[qa_ledger] spec-doubt %s resolved -- %s" %
              (row["id"], args.decision or args.note or "human reviewed"))
        return
    if not args.repo or not args.note:
        raise SystemExit("[qa_ledger] spec-doubt requires --repo and --note")
    _repo_node(ledger, args.repo)  # validate repo
    sev = (args.severity or "HIGH").upper()
    if sev not in SEVERITY_ORDER:
        raise SystemExit("[qa_ledger] invalid severity '%s'" % args.severity)
    row = {"id": _next_prefixed_id(rows, "SD"), "at": _now(), "status": "open",
           "repo": args.repo, "kind": args.kind, "severity": sev,
           "note": args.note, "evidence": args.evidence,
           "spec": args.spec, "resolved_at": None}
    rows.append(row)
    _touch_event(ledger, "spec-doubt", row["id"], args.repo)
    _save(args.ledger, ledger)
    print("[qa_ledger] spec-doubt %s logged: %s/%s/%s -- %s" %
          (row["id"], args.repo, args.kind, sev, args.note))


def cmd_spec_change_request(args):
    """Record or resolve a human contract bridge from evidence to SPEC/ADR change."""
    ledger = _load(args.ledger)
    rows = ledger.setdefault("spec_change_requests", [])
    if args.resolve:
        if not args.id:
            raise SystemExit("[qa_ledger] --resolve requires --id SCR-nnn")
        if args.decision not in {"accepted", "rejected", "superseded"}:
            raise SystemExit(
                "[qa_ledger] spec-change-request --resolve requires "
                "--decision accepted|rejected|superseded")
        if args.decision == "accepted" and not _has_text(args.amended):
            raise SystemExit(
                "[qa_ledger] accepted spec-change-request requires nonempty --amended")
        if (args.decision in {"rejected", "superseded"}
                and not (_has_text(args.note) or
                         (args.decision == "superseded" and _has_text(args.amended)))):
            raise SystemExit(
                f"[qa_ledger] {args.decision} spec-change-request requires "
                "a nonempty --note"
                + (" or --amended replacement reference"
                   if args.decision == "superseded" else ""))
        row = _find_by_id(rows, args.id, "spec-change-request")
        _require_open_resolution(row, "spec-change-request")
        row["status"] = "resolved"
        row["resolved_at"] = _now()
        row["decision"] = args.decision
        row["resolution_note"] = args.note
        row["amended"] = args.amended
        _touch_event(ledger, "spec-change-request:resolve", row["id"], row.get("repo"))
        _save(args.ledger, ledger)
        print("[qa_ledger] spec-change-request %s resolved -- %s" %
              (row["id"], args.decision or args.note or "human decided"))
        return
    if not args.repo or not args.source or not args.requested_change or not args.evidence:
        raise SystemExit("[qa_ledger] spec-change-request requires --repo, --source, --requested-change and --evidence")
    _repo_node(ledger, args.repo)  # validate repo
    source_match = re.fullmatch(r"(PF|SD)-(\d+)", args.source or "")
    if not source_match:
        raise SystemExit(
            "[qa_ledger] spec-change-request --source must be an existing PF-n or SD-n")
    source_rows = (ledger.get("production_findings", [])
                   if source_match.group(1) == "PF"
                   else ledger.get("spec_doubts", []))
    source_row = next((item for item in source_rows
                       if item.get("id") == args.source), None)
    if source_row is None:
        raise SystemExit(
            f"[qa_ledger] spec-change-request source '{args.source}' does not exist")
    if source_row.get("repo") != args.repo:
        raise SystemExit(
            f"[qa_ledger] spec-change-request source '{args.source}' belongs to "
            f"repo '{source_row.get('repo')}', not '{args.repo}'")
    row = {"id": _next_prefixed_id(rows, "SCR"), "at": _now(),
           "status": "open", "repo": args.repo, "source": args.source,
           "requested_change": args.requested_change, "evidence": args.evidence,
           "spec": args.spec, "adr": args.adr, "note": args.note,
           "decision": None, "amended": None, "resolved_at": None}
    rows.append(row)
    _touch_event(ledger, "spec-change-request", row["id"], args.repo)
    _save(args.ledger, ledger)
    print("[qa_ledger] spec-change-request %s logged: %s from %s -- %s" %
          (row["id"], args.repo, args.source, args.requested_change))


def _append_gate_record(ledger, node, repo, tool, iteration, failing, count, note):
    """Append a static-gate-shaped record for a FACT gate so the EXISTING plumbing
    sees it: _gate_open_and_sev feeds the BLOCKER/CRITICAL readiness cap (<=65) and
    _converged refuses while the latest record for the tool is failing. A later
    clean record for the same tool clears it (latest-per-tool wins)."""
    ledger["step_counter"] += 1
    n = max(1, count) if failing else 0
    rec = {
        "n": ledger["step_counter"], "at": _now(), "iteration": iteration,
        "tool": tool, "category": "static-gate",
        "reported": n, "gated_reported": n,
        "fixed": 0, "deferred": 0, "suppressed": 0,
        "severity_counts": {"BLOCKER": n} if failing else {},
        "tests_passed": None, "files_changed": 0,
        "fingerprint": None, "finding_ids": None, "note": note,
    }
    node["iterations"].append(rec)
    ledger["steps"].append({"n": rec["n"], "at": rec["at"], "kind": "static-gate",
                            "repo": repo, "tool": tool, "iteration": iteration})
    return rec


def cmd_log_gate(args):
    """Persist a FACT-gate verdict (golden-diff / gate-check / pit-check / simplicity / regression)
    into the ledger, so 'facts may block' is enforced by the engine, not by goodwill.
      fail    -> BLOCKER record: trips the <=65 readiness cap AND blocks convergence.
      pass    -> clean record for the same tool: credits the fix, convergence sees clean.
      not-run -> a steps event ONLY, never an iterations record: absence is not
                 evidence — it neither reads as clean nor fakes a red (last state stands).
    """
    # INV-ADVISORY-01 note (ADR-014): --kind is a CLOSED vocabulary (argparse choices), so
    # an advisory-class dimension (e.g. "semantic") cannot be registered as a gate through
    # this door at all -- the refusal is structural. The smoke suite measures that the
    # vocabulary stays closed; widening it to admit an advisory kind is a red build.
    ledger = _load(args.ledger)
    node = _repo_node(ledger, args.repo)
    tool = f"gate:{args.kind}"
    _validate_iteration(node, tool, args.iteration)
    if args.count < 0:
        raise SystemExit("[qa_ledger] count must be nonnegative")
    if args.verdict == "not-run":
        ledger["step_counter"] += 1
        ledger["steps"].append({"n": ledger["step_counter"], "at": _now(),
                                "kind": "gate-not-run", "repo": args.repo,
                                "tool": tool, "iteration": args.iteration})
        _save(args.ledger, ledger)
        print(f"[qa_ledger] {args.repo}/{tool}: NOT-RUN recorded "
              f"(no evidence — last logged state stands, absence is never green)")
        return
    failing = args.verdict == "fail"
    rec = _append_gate_record(ledger, node, args.repo, tool, args.iteration,
                              failing, args.count, args.note)
    _save(args.ledger, ledger)
    state = f"FAIL (BLOCKER x{rec['gated_reported']})" if failing else "PASS (clean)"
    print(f"[qa_ledger] {args.repo}/{tool}: {state} logged — "
          f"{'caps readiness <=65 and blocks convergence' if failing else 'clears the gate for convergence'}")


def cmd_flag_blocker(args):
    """Record (or resolve) a CONSTITUTION/invariant breach as a first-class BLOCKER.
    The record is static-gate-shaped, so it caps readiness <=65 and blocks convergence
    through the same plumbing as a linter BLOCKER — no parallel mechanism.
    --resolve writes a clean record for the same kind (latest-per-tool wins).
    Resolver EXIGE --escape-analysis (kit 1.16.0, Tip 94 'Find Bugs Once'): que
    gate/test debio atrapar esto y que accion se tomo (test nuevo, gate nuevo,
    busqueda de hermanos del bug) — cerrar un BLOCKER sin esa reflexion es
    garantia de encontrarlo dos veces."""
    ledger = _load(args.ledger)
    node = _repo_node(ledger, args.repo)
    tool = f"blocker:{args.kind}"
    _validate_iteration(node, tool, args.iteration)
    failing = not args.resolve
    if failing and not args.note:
        raise SystemExit("[qa_ledger] flag-blocker requires --note describing the breach.")
    if args.resolve and not args.escape_analysis:
        raise SystemExit(
            "[qa_ledger] resolving a BLOCKER requires --escape-analysis: which gate/test "
            "should have caught it, and what was done about it (new test / new gate / "
            "sibling hunt)? Finding each bug ONCE is the rule.")
    rec = _append_gate_record(ledger, node, args.repo, tool, args.iteration,
                              failing, 1, args.note)
    if args.resolve:
        rec["escape_analysis"] = args.escape_analysis
    _save(args.ledger, ledger)
    if failing:
        print(f"[qa_ledger] {args.repo}/{tool}: BLOCKER logged — {args.note} "
              f"(readiness capped <=65, convergence blocked until --resolve)")
    else:
        print(f"[qa_ledger] {args.repo}/{tool}: resolved — gate cleared "
              f"(step #{rec['n']}, escape analysis recorded)")


def _converged(node, k, qa_order=None):
    """Return (bool, reasons). Convergence = agent cycle clean AND latest
    static-gate run of every linter/fact-gate clean at the gate level.
    With qa_order (config defaults.qa_tools_order): the cycle is the LATEST agent
    step PER TOOL and every listed tool must have run — padding the window with
    clean throwaway steps can no longer push dirty findings out of sight.
    Measured tests beat narrated tests: a red last snapshot vetoes agent-reported
    green (maker != checker, enforced where the data allows it)."""
    agent = [s for s in node["iterations"] if s.get("category", "agent") == "agent"]
    reasons = []
    k = max(1, k)
    if qa_order:
        latest_agent = {}
        for s in agent:
            latest_agent[s["tool"]] = s   # iteration order preserved -> last wins
        missing = [t for t in qa_order if t not in latest_agent]
        if missing:
            reasons.append(f"agent tools never ran: {','.join(missing)}")
        cycle = [latest_agent[t] for t in qa_order if t in latest_agent]
        if not agent:
            return False, ["no agent steps measured"]
    else:
        if len(agent) < k:
            return False, [f"only {len(agent)} agent steps (need a full cycle of {k})"]
        cycle = agent[-k:]
    gated = sum((s.get("gated_reported") or 0) for s in cycle)
    changed = sum((s.get("files_changed") or 0) for s in cycle)
    tests_ok = all(s.get("tests_passed") for s in cycle) if cycle else False
    # measured beats narrated: the parsed snapshot vetoes the agent boolean
    if node.get("snapshots"):
        t = node["snapshots"][-1].get("tests", {})
        if (t.get("failures", 0) or 0) + (t.get("errors", 0) or 0) > 0:
            tests_ok = False
            reasons.append("snapshot shows failing tests (measured, overrides agent report)")
        freshness = t.get("freshness", {})
        if freshness.get("status") == "stale":
            tests_ok = False
            reasons.append(f"snapshot test evidence is stale: "
                           f"{freshness.get('reason', 'source/test changed after report')}")
    if gated:
        reasons.append(f"agent gated={gated}")
    if changed:
        reasons.append(f"files_changed={changed}")
    if not tests_ok and "snapshot shows failing tests (measured, overrides agent report)" not in reasons:
        reasons.append("tests not green")
    latest = _latest_static_by_tool(node)
    static_gated = sum((s.get("gated_reported") or 0) for s in latest.values())
    if static_gated:
        offenders = ",".join(f"{t}:{s.get('gated_reported')}"
                             for t, s in latest.items() if s.get("gated_reported"))
        reasons.append(f"static-gate gated={static_gated} ({offenders})")
    return (not reasons), reasons


# --------------------------------------------------------------------------- #
# phase  (M4: FSM DERIVADA del workflow — el estado se computa, no se declara)
# --------------------------------------------------------------------------- #
# Una FSM donde el agente DECLARA "entro a qa" es estado narrado — lo que todo
# el kit combate. Aca el estado ES los hechos del ledger; no existen
# transiciones ilegales que validar porque no hay nada que declarar.
# Reglas de derivacion (precedencia de arriba hacia abajo):
#   escalated — escalacion abierta sin resolver (acto humano pendiente)
#   pr-ready  — _converged() AND tests verdes AND 0 BLOCKER/CRITICAL
#   qa        — hay pasos de QA registrados (agent o static-gate)
#   build     — hay snapshots medidos pero ningun paso de QA
#   plan      — ledger virgen para el repo
PHASES = ["plan", "build", "qa", "escalated", "pr-ready"]


def _derive_phase(ledger, name, node, k, qa_order):
    """(estado, evidencia[]) — computado del ledger, jamas self-reported."""
    open_esc = [e for e in ledger.get("escalations", [])
                if e.get("repo") == name and not e.get("resolved_at")]
    if open_esc:
        return "escalated", [f"{len(open_esc)} escalacion(es) sin resolver "
                             f"(la resolucion es un acto humano registrado)"]
    spec_open = _open_spec_doubts(ledger, name)
    if spec_open:
        ids = ", ".join(s.get("id", "SD-?") for s in spec_open)
        return "escalated", [f"spec-doubt abierto ({ids}): la SPEC requiere "
                             f"revision humana antes de PR"]
    scr_open = _open_spec_change_requests(ledger, name)
    if scr_open:
        ids = ", ".join(r.get("id", "SCR-?") for r in scr_open)
        return "escalated", [f"spec-change-request abierto ({ids}): requiere "
                             f"decision humana y SPEC/ADR amended antes de PR"]
    prod_open = _open_production_findings(ledger, name, gate_only=True)
    if prod_open:
        ids = ", ".join(p.get("id", "PF-?") for p in prod_open)
        return "escalated", [f"production finding abierto ({ids}): feedback real "
                             f"debe entrar al proximo discovery"]
    conv, reasons = _converged(node, k, qa_order)
    tests_red = _tests_red(node)
    last_tests = (node["snapshots"][-1].get("tests", {})
                  if node.get("snapshots") else {})
    tests_measured_green = (
        bool(last_tests.get("report_found"))
        and last_tests.get("freshness", {}).get("status") != "stale"
        and (last_tests.get("executed", 0) or 0) > 0
        and (last_tests.get("failures", 0) or 0) == 0
        and (last_tests.get("errors", 0) or 0) == 0
    )
    if not last_tests.get("report_found"):
        reasons.append("falta evidencia medida de tests")
    elif (last_tests.get("executed", 0) or 0) <= 0 and not tests_red:
        reasons.append("la evidencia medida no contiene tests ejecutados")
    _go, sev = _gate_open_and_sev(node)
    blk = sev.get("BLOCKER", 0) + sev.get("CRITICAL", 0)
    # clean-room gate (ADR-008). OPT-IN: no clean_room block, or mode "off", and this does not
    # exist -- behavior identical to earlier releases. Declared "final": pr-ready additionally
    # requires clean-room evidence that is GREEN and pinned to the CURRENT HEAD. A new commit
    # makes the previous run stale for the gate, the same staleness posture the rest of the
    # engine takes: evidence certifies the thing it was measured against, nothing later.
    # curation gate (ADR-009, INV-CURATION-01). In use the moment discovery/ exists --
    # creating candidates IS the opt-in. Fail-closed both ways: an unjudged candidate blocks,
    # and a malformation blocks too, because "could not validate" must never read as judged.
    _cu_cfg = (_repo_cfg(ledger, name) if name != "integration"
               else {"path": "."})               # synthetic scope: never in config["repos"]
    _cu = _curation_state(_cu_cfg.get("path", "."))
    if _cu is not None:
        if _cu["malformed"] or _cu["ledger_errors"] or _cu["append_only"] == "violation":
            _bits = [m["candidate"] for m in _cu["malformed"][:3]]
            if _cu["ledger_errors"]:
                _bits.append(BEHAVIOR_LEDGER_FILE + " malformado")
            if _cu["append_only"] == "violation":
                _bits.append(BEHAVIOR_LEDGER_FILE + " editado (append-only)")
            reasons.append("curation invalida: " + "; ".join(_bits)
                           + " -- corregir antes de avanzar")
            conv = False
        elif _cu["unjudged"]:
            reasons.append("candidata(s) sin veredicto humano: "
                           + ", ".join(_cu["unjudged"][:3])
                           + (" (+%d)" % (len(_cu["unjudged"]) - 3)
                              if len(_cu["unjudged"]) > 3 else "")
                           + " -- INV-CURATION-01: sin juicio no hay promocion")
            conv = False
    # CANDIDATE-DELTA gate (ADR-013): same invariant, typed storage. Creating the delta IS
    # the opt-in; an uncurated OBS blocks exactly like an unjudged .md candidate did.
    _dl = _delta_state(ledger, name, _cu_cfg.get("path", "."))
    if _dl is not None:
        if _dl["malformed"]:
            reasons.append("CANDIDATE-DELTA invalido: " + "; ".join(_dl["malformed"][:3])
                           + " -- corregir antes de avanzar")
            conv = False
        elif _dl["uncurated"]:
            reasons.append("OBS sin veredicto humano: " + ", ".join(_dl["uncurated"][:3])
                           + (" (+%d)" % (len(_dl["uncurated"]) - 3)
                              if len(_dl["uncurated"]) > 3 else "")
                           + " -- INV-CURATION-01: sin juicio no hay promocion")
            conv = False
    _cr = _cr_cfg(ledger)
    if _cr and _cr.get("mode") == "final":
        _head = None
        _hr = None
        _crcfg = (_repo_cfg(ledger, name) if name != "integration"
                  else {"path": "."})          # synthetic scope: never in config["repos"]
        try:
            _hr = subprocess.run(["git", "rev-parse", "HEAD"],
                                 cwd=_crcfg.get("path", "."),
                                 capture_output=True, text=True, encoding="utf-8",
                                 errors="replace")
        except OSError:
            _hr = None
        if _hr is not None and _hr.returncode == 0:
            _head = _hr.stdout.strip()
        _run = _cr_latest(ledger, name, _head) if _head else None
        if not _head:
            reasons.append("clean-room declarado pero no se pudo resolver HEAD "
                           "(no se mide, no se aprueba)")
            conv = False
        elif not _run or not _run.get("ok"):
            reasons.append("falta clean-room verde para %s (evidencia del arbol no "
                           "certifica el commit)" % _head[:8])
            conv = False
    if conv and tests_measured_green and not tests_red and blk == 0:
        evidence = ["ciclo de agente limpio", "tests verdes (medidos)",
                    "0 BLOCKER/CRITICAL abiertos"]
        if _latest_static_by_tool(node):
            evidence.insert(1, "static gates registrados sin findings gateados")
        return "pr-ready", evidence
    if node["iterations"]:
        return "qa", reasons or ["pasos de QA registrados, aun sin converger"]
    if node.get("snapshots"):
        return "build", ["snapshots medidos, ningun paso de QA todavia"]
    return "plan", ["ledger virgen para el repo — nada medido aun"]


def _spike_branch(repo_path):
    """Rama actual si es spike/* (kit 1.19.0, Tip 21 'Prototype to Learn').
    symbolic-ref funciona incluso antes del primer commit; detached HEAD o
    directorio sin git = None (no hay rama spike que vetar)."""
    import subprocess
    try:
        r = subprocess.run(["git", "-C", repo_path, "symbolic-ref", "--short",
                            "-q", "HEAD"], capture_output=True, text=True)
        branch = (r.stdout or "").strip()
        return branch if branch.startswith("spike/") else None
    except Exception:  # noqa: BLE001 — sin git instalado no hay veto posible
        return None


def cmd_phase(args):
    ledger = _load(args.ledger)
    node = _repo_node(ledger, args.repo)
    qa_order = ledger["config"].get("defaults", {}).get("qa_tools_order")
    state, evidence = _derive_phase(ledger, args.repo, node,
                                    args.tools_per_cycle, qa_order)
    ok = args.require is None or state == args.require
    # M10: el codigo de spike es descartable POR CONTRATO — una rama spike/*
    # jamas pasa el gate de PR, aunque los hechos del ledger den pr-ready.
    # El output legitimo de un spike es un ADR con lecciones, no un merge.
    spike = None
    if args.require == "pr-ready" and args.repo != "integration":
        try:
            path = _repo_cfg(ledger, args.repo).get("path", ".")
        except SystemExit:
            path = None
        spike = _spike_branch(path) if path else None
        if spike:
            ok = False
    if args.json:
        print(json.dumps({"repo": args.repo, "phase": state,
                          "evidence": evidence, "required": args.require,
                          "spike_branch": spike, "satisfied": ok},
                         indent=2, ensure_ascii=False))
        sys.exit(0 if ok else 1)
    print(f"PHASE {args.repo}: {state}  (derived from the ledger — not declared)")
    for e in evidence:
        print(f"  · {e}")
    if spike:
        print(f"  ! branch '{spike}': SPIKE code, disposable by contract "
              f"(Tip 21) — its legitimate output is an ADR with the lessons, "
              f"never a PR. Write the ADR and start clean on a normal branch.")
    elif args.require and not ok:
        print(f"  ! '{args.require}' is required and the FACTS say '{state}' — "
              f"state is not negotiated, it is built")
    sys.exit(0 if ok else 1)


def cmd_converged(args):
    """
    ADVISORY. Convergence requires ALL of:
      - the last full cycle of AGENT tool passes has zero gated findings,
        zero files changed, and green tests; AND
      - the latest static-gate run of every linter has zero gated findings.
    """
    ledger = _load(args.ledger)
    node = _repo_node(ledger, args.repo)
    qa_order = ledger["config"].get("defaults", {}).get("qa_tools_order")
    ok, reasons = _converged(node, args.tools_per_cycle, qa_order)
    if ok:
        print(f"[qa_ledger] {args.repo}: CONVERGED")
    else:
        print(f"[qa_ledger] {args.repo}: NOT converged ({'; '.join(reasons)})")
    sys.exit(0 if ok else 1)


def cmd_oscillation(args):
    """
    ADVISORY. Oscillation = the finding set for a tool keeps coming back.
    Uses finding_ids when available (ingest-gate always records them; log-step
    records them when --fingerprint is passed): a Jaccard overlap >= 0.8 between
    the last set and the set 2 or 3 passes back counts as recurrence — a one-line
    churn that shifts a single finding-ID no longer hides the loop. Falls back to
    exact fingerprint equality (period 2) when only hashes exist.
    """
    ledger = _load(args.ledger)
    node = _repo_node(ledger, args.repo)
    runs = [(s.get("fingerprint"), set(s.get("finding_ids") or []))
            for s in node["iterations"]
            if s.get("tool") == args.tool
            and (s.get("fingerprint") or s.get("finding_ids"))]
    if not runs:
        print(f"[qa_ledger] {args.repo}/{args.tool}: no fingerprints/finding-ids logged "
              f"-> cannot judge oscillation (ingest-gate records them automatically; "
              f"pass --fingerprint to log-step)")
        sys.exit(2)
    osc = False
    detail = ""
    if len(runs) >= 3:
        last_fp, last_ids = runs[-1]
        for back in (3, 4):
            if len(runs) < back:
                continue
            prev_fp, prev_ids = runs[-back]
            if last_ids and prev_ids:
                j = len(last_ids & prev_ids) / len(last_ids | prev_ids)
                if j >= 0.8:
                    osc = True
                    detail = f" (Jaccard {j:.2f} vs pass N-{back - 1})"
                    break
            elif last_fp and last_fp == prev_fp:
                osc = True
                detail = f" (exact fingerprint repeat vs pass N-{back - 1})"
                break
    print(f"[qa_ledger] {args.repo}/{args.tool}: "
          f"{'OSCILLATING' + detail if osc else 'no oscillation detected'}")
    sys.exit(1 if osc else 0)


# --------------------------------------------------------------------------- #
# fastpath-eval  (ADR-003: fast-path entry by MEASURED signals, never opinion)
# --------------------------------------------------------------------------- #

def _fp_glob_re(g):
    """Translate a protected-path glob to a regex. `**` crosses directories, `*`/`?` do not.
    Case-insensitive on purpose: Windows and macOS filesystems are."""
    g = g.replace("\\", "/")
    out, i = [], 0
    while i < len(g):
        c = g[i]
        if c == "*":
            if g[i:i + 2] == "**":
                i += 2
                if i < len(g) and g[i] == "/":
                    # `**/` = any number of WHOLE directories (incl. zero) -- segment-anchored,
                    # so `**/migrations/**` does not match `db_migrations/` by substring.
                    out.append("(?:[^/]*/)*")
                    i += 1
                else:
                    out.append(".*")
                continue
            out.append("[^/]*")
        elif c == "?":
            out.append("[^/]")
        elif c in ".^$+{}[]|()":
            out.append("\\" + c)
        else:
            out.append(c)
        i += 1
    return re.compile("^(?:%s)$" % "".join(out), re.I)


def cmd_fastpath_eval(args):
    """Measured verdict for the fast-path (ADR-003). ALLOW only when every signal passes;
    ANY ambiguity -- no config, no git, unresolvable base -- is DENY with the reason named
    (fail-closed: "could not measure" never grants the shortcut). With --intent the verdict is
    recorded in the ledger as a first-class entry; without it this is a dry-run. A prior ALLOW
    followed by a DENY re-eval escalates through the EXISTING escalation machinery, so the
    derived phase flips to `escalated` and pr-ready is blocked until the human resolves."""
    ledger = _load(args.ledger)
    _repo_node(ledger, args.repo)
    fp = ledger["config"].get("defaults", {}).get("fast_path")
    intent = (args.intent or "").strip()
    signals, deny = [], []

    def sig(name, value, threshold, source, ok):
        signals.append({"name": name, "value": value, "threshold": threshold,
                        "source": source, "at": _now(), "ok": bool(ok)})
        if not ok:
            deny.append(name)

    if not isinstance(fp, dict) or fp.get("enabled") is False:
        sig("configured", False, "defaults.fast_path present and enabled",
            "config.defaults.fast_path", False)
    else:
        repo_path = _repo_cfg(ledger, args.repo).get("path", ".")
        base, base_src = args.base, "--base"
        if base:
            probe = subprocess.run(["git", "rev-parse", "--verify", base + "^{commit}"],
                                   cwd=repo_path, capture_output=True, text=True)
            if probe.returncode != 0:
                base = None
                base_src = "--base (unresolvable)"
        else:
            for cand in ("origin/main", "main"):
                r = subprocess.run(["git", "merge-base", "HEAD", cand], cwd=repo_path,
                                   capture_output=True, text=True)
                if r.returncode == 0 and r.stdout.strip():
                    base, base_src = r.stdout.strip(), "merge-base HEAD %s" % cand
                    break
        if not base:
            sig("base_ref", None, "a resolvable base commit",
                base_src if base_src != "--base" else "git merge-base HEAD origin/main|main",
                False)
        else:
            num = subprocess.run(["git", "diff", "--numstat", base], cwd=repo_path,
                                 capture_output=True, text=True, encoding="utf-8",
                                 errors="replace")
            if num.returncode != 0:
                sig("git_diff", None, "a readable diff",
                    "git diff --numstat %s" % base[:12], False)
            else:
                files, loc, binaries = [], 0, []
                for line in num.stdout.splitlines():
                    parts = line.split("\t")
                    if len(parts) != 3:
                        continue
                    a, d, path = parts
                    path = path.strip().replace("\\", "/")
                    # RENAMES arrive as one descriptor -- `old => new` or `pre{old => new}post`.
                    # Matching the raw descriptor against the globs let a rename INTO db/ walk
                    # straight past protected_paths (found by fresh review). Expand it and
                    # count BOTH sides: renaming a file out of a protected area is as
                    # gate-worthy as renaming one in.
                    if " => " in path:
                        m_ = re.match(r"^(.*)\{(.*) => (.*)\}(.*)$", path)
                        if m_:
                            pre, old_, new_, post = m_.groups()
                            files.append((pre + old_ + post).replace("//", "/"))
                            files.append((pre + new_ + post).replace("//", "/"))
                        else:
                            old_, new_ = path.split(" => ", 1)
                            files.append(old_)
                            files.append(new_)
                    else:
                        files.append(path)
                    if a == "-" or d == "-":
                        # binary diff: LOC is UNMEASURABLE, and an unmeasurable signal must
                        # deny, not silently count as zero (fail-closed).
                        binaries.append(path)
                    loc += (int(a) if a.isdigit() else 0) + (int(d) if d.isdigit() else 0)
                # UNTRACKED files are invisible to `git diff` -- and a small change is very
                # often a NEW file. Not counting them would under-measure exactly the case
                # this gate exists for, so they count as files + added lines (fail-closed).
                unt = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"],
                                     cwd=repo_path, capture_output=True, text=True,
                                     encoding="utf-8", errors="replace")
                for path in unt.stdout.splitlines():
                    path = path.strip()
                    if not path:
                        continue
                    files.append(path.replace("\\", "/"))
                    try:
                        with open(os.path.join(repo_path, path), "rb") as fh:
                            loc += fh.read().count(b"\n")
                    except OSError:
                        loc += 1  # an unreadable new file still counts as a change
                src = "git diff --numstat %s (+ untracked)" % base[:12]
                max_f = int(fp.get("max_files_changed", 3))
                max_l = int(fp.get("max_loc_delta", 80))
                sig("max_files_changed", len(files), max_f, src, len(files) <= max_f)
                sig("max_loc_delta", loc, max_l, src, loc <= max_l)
                if binaries:
                    sig("binary_files", binaries[:5], "none (LOC unmeasurable on binary)",
                        src, False)
                pats = fp.get("protected_paths",
                              ["**/migrations/**", "**/*.appro" + "ved", "db/**"])
                hits = []
                for f in files:
                    for g in pats:
                        if _fp_glob_re(g).match(f):
                            hits.append("%s (%s)" % (f, g))
                            break
                sig("protected_paths", hits if hits else 0,
                    "no touched file matches a protected glob", "config globs over " + src,
                    not hits)
                # ADR-006: the golden-touched veto. OPT-IN -- absent flag, no signal at all
                # and behavior identical to 1.57.0+. DECLARED -- fail-closed: a missing or
                # empty mapping DENIES, because "could not measure" never grants a shortcut.
                if fp.get("forbid_when_golden_touched"):
                    gcm = _load_golden_coverage(repo_path)   # malformed -> exit 2, never silent
                    gmap = (gcm or {}).get("goldens") or {}
                    # Enumerate the goldens that actually EXIST. A manifest knowing only SOME
                    # of them would otherwise assert "no touched file is covered by a golden"
                    # about goldens it has never measured -- an ALLOW built on ignorance, which
                    # is precisely the silent bypass this veto exists to prevent. Found by
                    # fresh review and reproduced: 2 goldens in the tree, 1 in the map, a diff
                    # touching the unmapped one's source -> ALLOW. Same glob shape cmd_golden_diff
                    # already uses to locate goldens; no new mechanism.
                    _sfx = ".appro" + "ved"
                    _hits = set(glob.glob(os.path.join(repo_path, "**", "*" + _sfx),
                                          recursive=True))
                    _hits |= set(glob.glob(os.path.join(repo_path, "**", "*" + _sfx + ".*"),
                                           recursive=True))
                    _tree = set()
                    for _p in _hits:
                        if os.path.isfile(_p):
                            _r = _gc_rel(os.path.abspath(_p), os.path.abspath(repo_path))
                            if _r:
                                _tree.add(_r)
                    _unmapped = sorted(_tree - set(gmap))
                    if _unmapped:
                        # covers the manifest-absent case too: with goldens present and no
                        # manifest, every one of them is unmapped.
                        sig("golden_touched", _unmapped[:5],
                            "every golden in the tree carries a measured map",
                            GOLDEN_COVERAGE_FILE + " (missing or incomplete -- run "
                            "golden-coverage for each golden)", False)
                    elif not _tree:
                        # No golden exists, so none can be touched. This is a MEASUREMENT
                        # ("nothing to cover"), not an absence of one -- denying forever a
                        # repo that has no goldens would be ceremony, not rigor.
                        sig("golden_touched", 0, "no golden in the tree to be covered",
                            "glob over " + repo_path, True)
                    else:
                        covered = {}
                        _commits, _tools = set(), set()
                        for _g, _e in gcm["goldens"].items():
                            for _f in _e.get("files", []):
                                covered.setdefault(_f, []).append(_g)
                            if _e.get("captured_at_commit"):
                                _commits.add(_e["captured_at_commit"][:8])
                            if _e.get("tool"):
                                _tools.add(_e["tool"])
                        ghits = ["%s (golden: %s)" % (f, ", ".join(covered[f]))
                                 for f in files if f in covered]
                        # provenance travels with the verdict (ADR-006: no freshness gate,
                        # but every verdict says which capture it trusted)
                        prov = "%s @ %s (%s)" % (
                            GOLDEN_COVERAGE_FILE,
                            ",".join(sorted(_commits)) if _commits else "no commit recorded",
                            ", ".join(sorted(_tools)) if _tools else "no tool recorded")
                        sig("golden_touched", ghits if ghits else 0,
                            "no touched file is covered by a golden", prov, not ghits)

    verdict = "ALLOW" if not deny else "DENY"
    # Escalation means "an ACTIVE fast-path run outgrew its thresholds" -- so it gates on the
    # LATEST entry for this repo being ALLOW, not on an ALLOW ever having existed. The first
    # version scanned all history, which misclassified every later unrelated DENY as ESCALATED
    # forever (found by fresh review, reproduced in ordinary sequential usage).
    _fp_prior = [e for e in ledger.get("fast_path", []) if e.get("repo") == args.repo]
    active_allow = bool(_fp_prior) and _fp_prior[-1].get("verdict") == "ALLOW"
    escalated = bool(intent and active_allow and verdict == "DENY"
                     and "configured" not in deny)
    if escalated:
        verdict = "ESCALATED"
    out = {"repo": args.repo, "mode": "fast_path", "verdict": verdict,
           "intent": intent or None, "dry_run": not bool(intent), "signals": signals}

    if intent:
        ledger.setdefault("fast_path", [])
        ledger["step_counter"] += 1
        entry = dict(out)
        entry.pop("dry_run", None)
        entry.update({"n": ledger["step_counter"], "at": _now()})
        ledger["fast_path"].append(entry)
        ledger["steps"].append({"n": ledger["step_counter"], "at": _now(),
                                "kind": "fastpath-eval", "repo": args.repo})
        if escalated:
            # reuse the EXISTING escalation machinery: derived phase flips to `escalated`,
            # pr-ready is blocked and readiness capped until the human resolve-escalation --
            # after producing ADR + ACCEPTANCE, per ADR-003 (not a full discovery).
            ledger["step_counter"] += 1
            ledger["escalations"].append({
                "n": ledger["step_counter"], "at": _now(), "repo": args.repo,
                "reason": "fast-path thresholds exceeded mid-run: " + ", ".join(deny)
                          + " -- produce ADR + ACCEPTANCE, then resolve-escalation"})
            ledger["steps"].append({"n": ledger["step_counter"], "at": _now(),
                                    "kind": "escalation", "repo": args.repo})
        _save(args.ledger, ledger)

    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print("FASTPATH %s: %s%s" % (args.repo, verdict,
              "" if intent else "  (dry-run: no --intent, nothing recorded)"))
        for s_ in signals:
            print("  %s %s: %s / %s  [%s]" % ("ok" if s_["ok"] else "!!",
                  s_["name"], s_["value"], s_["threshold"], s_["source"]))
        if escalated:
            print("  -> ESCALATED: pr-ready is blocked; produce ADR + ACCEPTANCE, "
                  "then resolve-escalation (a recorded human act)")
    sys.exit(0 if verdict == "ALLOW" else 1)


# --------------------------------------------------------------------------- #
# spec-drift  (ADR-005: mechanical drift detection, advisory -- NEVER a gate)
# --------------------------------------------------------------------------- #

def _sd_governs(path):
    """Parse the `governs:` glob list from a `---` frontmatter block at the top of a
    markdown file. Returns None when there is no frontmatter or no `governs:` key
    (UNMAPPED -- absence of a mapping is absence of measurement, not "no drift")."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return None
    if not lines or lines[0].strip() != "---":
        return None
    globs, in_governs, explicit_empty = None, False, False
    # scan runs to the CLOSING fence, not an arbitrary window -- a governs: key late in a
    # long frontmatter block must not silently read as UNMAPPED (fresh-review finding).
    for ln in lines[1:]:
        s = ln.strip()
        if s == "---":
            break
        if s.startswith("governs:"):
            rest = s[len("governs:"):].strip()
            if rest.startswith("[") and rest.endswith("]"):
                globs = [x.strip().strip("\x27\x22")
                         for x in rest[1:-1].split(",") if x.strip()]
                # only an INLINE [] is a declaration of "nothing to govern"
                explicit_empty = not globs
                in_governs = False
            elif rest:
                # bare scalar (`governs: src/**`) -- a plausible authoring shorthand;
                # dropping it silently would report a misleading "globs match nothing".
                globs, in_governs = [rest.strip("\x27\x22")], False
            else:
                globs, in_governs = [], True
            continue
        if in_governs:
            if s.startswith("- "):
                globs.append(s[2:].strip().strip("\x27\x22"))
            elif s and not ln.startswith((" ", "\t")):
                in_governs = False
    if globs == [] and not explicit_empty:
        # a `governs:` key with nothing usable under it (a placeholder, a comment, a typo) is
        # an UNFINISHED declaration, not a statement that this spec governs nothing. Report it
        # as UNMAPPED, which is what it is (fresh-review finding).
        return None
    return globs


def _sd_iso(ct):
    import datetime as _dt
    return _dt.datetime.fromtimestamp(ct, _dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sd_last_commit_ct(repo_path, paths):
    """Newest commit epoch touching any of `paths` (chunked: command lines have limits).
    None when no commit touches them (untracked)."""
    newest = None
    for i in range(0, len(paths), 200):
        r = subprocess.run(["git", "log", "-1", "--format=%ct", "--"] + paths[i:i + 200],
                           cwd=repo_path, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        out = r.stdout.strip().splitlines()
        if r.returncode == 0 and out and out[0].strip().isdigit():
            ct = int(out[0].strip())
            newest = ct if newest is None else max(newest, ct)
    return newest


def cmd_spec_drift(args):
    """Advisory drift report (ADR-005): last commit date of each spec doc vs. the newest
    commit touching the files its `governs:` globs map to. SPEC_STALE when governed code
    outran the spec by more than max_lag_days; UNMAPPED when there is no (effective)
    mapping; UNTRACKED when the spec has no commit date to compare. This command NEVER
    gates: a stale spec is a prompt for a human conversation, not a blocked pipeline.
    Exit code 0 always."""
    ledger = _load(args.ledger)
    _repo_node(ledger, args.repo)
    cfg = ledger["config"].get("defaults", {}).get("spec_drift") or {}
    lag_days = int(args.max_lag_days if args.max_lag_days is not None
                   else cfg.get("max_lag_days", 30))
    repo_path = _scope_path(ledger, args.repo)

    # The spec surface is fixed by ADR-005: the repo SPEC.md plus every ADR.
    spec_files = []
    if os.path.isfile(os.path.join(repo_path, "SPEC.md")):
        spec_files.append("SPEC.md")
    adr_dir = os.path.join(repo_path, "docs", "adr")
    if os.path.isdir(adr_dir):
        spec_files += sorted("docs/adr/" + f for f in os.listdir(adr_dir)
                             if f.lower().endswith(".md"))

    tracked = []
    ls = subprocess.run(["git", "ls-files"], cwd=repo_path, capture_output=True,
                        text=True, encoding="utf-8", errors="replace")
    if ls.returncode == 0:
        tracked = [l.strip().replace("\\", "/") for l in ls.stdout.splitlines() if l.strip()]

    results = []
    for spec in spec_files:
        governs = _sd_governs(os.path.join(repo_path, spec))
        row = {"file": spec, "governs": governs, "max_lag_days": lag_days}
        if governs is None:
            row.update({"verdict": "UNMAPPED", "reason": "no governs: frontmatter"})
            results.append(row)
            continue
        if not governs:
            # An EXPLICIT empty list is a declaration, not an omission: this decision governs
            # no code and never will. Negative ADRs ("we are NOT doing X, and why") are a
            # documented practice in this kit, and reporting them UNMAPPED forever turns a
            # correct state into permanent noise -- which is how an advisory gets ignored.
            # Found by running spec-drift on this repo's own ADR-004.
            row.update({"verdict": "NO-CODE",
                        "reason": "declares governs: [] -- a decision that governs no code"})
            results.append(row)
            continue
        matched = []
        pats = [_fp_glob_re(g) for g in governs]
        for f in tracked:
            if f == spec:
                continue  # a spec governing itself would always read fresh -- excluded
            if any(p.match(f) for p in pats):
                matched.append(f)
        if not matched:
            # A mapping that matches nothing measures nothing -- same absence, named.
            row.update({"verdict": "UNMAPPED", "reason": "globs match no tracked files"})
            results.append(row)
            continue
        spec_ct = _sd_last_commit_ct(repo_path, [spec])
        if spec_ct is None:
            row.update({"verdict": "UNTRACKED",
                        "reason": "spec has no commit date to compare"})
            results.append(row)
            continue
        newest = _sd_last_commit_ct(repo_path, matched)
        lag_s = lag_days * 86400
        row.update({"governed_files": len(matched),
                    "spec_committed_at": _sd_iso(spec_ct),
                    "newest_governed_at": _sd_iso(newest) if newest is not None else None})
        if newest is not None and newest - spec_ct > lag_s:
            import datetime as _dt
            cutoff = _dt.datetime.fromtimestamp(
                spec_ct + lag_s, _dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+0000")
            newer = set()
            for i in range(0, len(matched), 200):
                r = subprocess.run(["git", "log", "--since", cutoff, "--name-only",
                                    "--format=", "--"] + matched[i:i + 200],
                                   cwd=repo_path, capture_output=True, text=True,
                                   encoding="utf-8", errors="replace")
                if r.returncode == 0:
                    newer |= {l.strip().replace("\\", "/")
                              for l in r.stdout.splitlines() if l.strip()}
            newer &= set(matched)
            row.update({"verdict": "SPEC_STALE",
                        "lag_days_actual": round((newest - spec_ct) / 86400.0, 1),
                        "newer_files": sorted(newer)[:20],
                        "newer_files_total": len(newer)})
        else:
            row["verdict"] = "CLEAN"
        results.append(row)

    out = {"repo": args.repo, "max_lag_days": lag_days, "results": results,
           "advisory": True}

    # Latest-state record so the mirador can surface an advisory row. Advisory data,
    # not a step in the loop: no step_counter, no gate record, no readiness input.
    ledger["spec_drift"] = {"repo": args.repo, "at": _now(), "max_lag_days": lag_days,
                            "results": results}
    _save(args.ledger, ledger)

    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print("SPEC-DRIFT %s (advisory, lag > %dd):" % (args.repo, lag_days))
        if not results:
            print("  no spec documents found (SPEC.md / docs/adr/*.md)")
        mark = {"SPEC_STALE": "!!", "CLEAN": "ok", "UNMAPPED": "--", "UNTRACKED": "--",
                "NO-CODE": "ok"}
        for r_ in results:
            line = "  %s %s: %s" % (mark.get(r_["verdict"], "??"), r_["file"],
                                    r_["verdict"])
            if r_["verdict"] == "SPEC_STALE":
                line += " -- %d governed file(s) newer, e.g. %s" % (
                    r_["newer_files_total"], ", ".join(r_["newer_files"][:3]))
            elif "reason" in r_:
                line += " (%s)" % r_["reason"]
            print(line)
    sys.exit(0)



# --------------------------------------------------------------------------- #
# golden-coverage  (ADR-006: the golden<->source mapping, DERIVED BY MEASUREMENT)
# --------------------------------------------------------------------------- #

GOLDEN_COVERAGE_FILE = "golden.coverage.json"


def _load_golden_coverage(root):
    """Read the measured golden<->source manifest. Strict shape, mirroring
    _load_scrub_rules: a typo must NOT degrade into "no mapping" in silence, because
    under a declared veto that silence would GRANT the shortcut it exists to deny.
    Absent file -> None (the caller decides; with the veto declared, absent is DENY)."""
    path = os.path.join(root, GOLDEN_COVERAGE_FILE)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            spec = json.load(fh)
        if not isinstance(spec, dict) or not isinstance(spec.get("goldens"), dict):
            raise TypeError('expected {"goldens": {"<golden path>": {"files": [...]}}}')
        for g, entry in spec["goldens"].items():
            if not isinstance(entry, dict) or not isinstance(entry.get("files"), list):
                raise TypeError("golden %r has no files list" % g)
            for f in entry["files"]:
                if not isinstance(f, str):
                    raise TypeError("golden %r maps a non-string file" % g)
        return spec
    except (json.JSONDecodeError, TypeError, KeyError) as exc:
        print("[qa_ledger] %s invalid (%s) - the golden mapping is not skipped in "
              "silence: fix the file or delete it." % (path, exc), file=sys.stderr)
        sys.exit(2)


def _gc_rel(path, root):
    # realpath BOTH sides before comparing. On Windows a temp dir under a username longer
    # than 8 chars is reported in 8.3 short form (RUNNER~1) by one side and long form by the
    # other; relpath then yields "../.." and a file INSIDE the repo is filtered out as
    # outside it -- silently shrinking the map. Invisible on a machine whose username does
    # not mangle (which is why local Windows was green and Windows CI was not).
    try:
        rel = os.path.relpath(os.path.realpath(path), os.path.realpath(root))
    except ValueError:      # different drive on Windows -- outside the repo either way
        return None
    rel = rel.replace("\\", "/")
    return None if rel.startswith("../") else rel


def cmd_golden_coverage(args):
    """Record the MEASURED source files a golden's harness exercises (ADR-006).

    The harnesses drive their subject through subprocess, so instrumenting only the parent
    measures nothing: coverage is injected into EVERY python the harness spawns via a
    sitecustomize on PYTHONPATH plus COVERAGE_PROCESS_START -- the documented multiprocess
    technique, and the same PYTHONPATH-injection shape this repo's fault tests already use.

    coverage.py is an optional CAPTURE-time dependency (the engine stays stdlib-only at
    runtime). Absent, this writes NOTHING and exits 2: an empty map would read as
    "this golden covers nothing", which is the one lie that would let the veto pass."""
    try:
        import coverage
    except ImportError:
        print("[qa_ledger] coverage.py is not installed - refusing to write a map that was "
              "not measured (an empty map reads as 'covers nothing'). pip install coverage",
              file=sys.stderr)
        sys.exit(2)

    root = os.path.abspath(args.dir or ".")
    harness = os.path.abspath(args.harness)
    if not os.path.isfile(harness):
        print("[qa_ledger] harness not found: %s" % harness, file=sys.stderr)
        sys.exit(2)

    tmp = tempfile.mkdtemp(prefix="uscha-gc-")
    try:
        data_file = os.path.join(tmp, ".coverage")
        rc = os.path.join(tmp, "cov.rc")
        with open(rc, "w", encoding="utf-8") as fh:
            fh.write("[run]\nparallel = True\ndata_file = %s\n"
                     % data_file.replace("\\", "/"))
        with open(os.path.join(tmp, "sitecustomize.py"), "w", encoding="utf-8") as fh:
            fh.write("import coverage\ncoverage.process_startup()\n")

        env = dict(os.environ)
        env["COVERAGE_PROCESS_START"] = rc
        env["PYTHONPATH"] = tmp + os.pathsep + env.get("PYTHONPATH", "")
        env["PYTHONIOENCODING"] = "utf-8"
        r = subprocess.run([sys.executable, harness], cwd=root, env=env,
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        if r.returncode != 0:
            print("[qa_ledger] the harness failed (exit %d) - no map recorded from a run "
                  "that did not complete:\n%s" % (r.returncode, (r.stderr or "")[-1500:]),
                  file=sys.stderr)
            sys.exit(2)

        cov = coverage.Coverage(data_file=data_file)
        try:
            cov.combine()
            cov.save()
        except Exception as exc:
            # Never silent: a PARTIAL combine yields an incomplete-but-non-empty file list,
            # which slips past the empty-map guard below and records a map that under-reports
            # what the golden covers. The empty case still exits 2; this one is announced so a
            # human sees the map may be short (fresh-review finding).
            print("[qa_ledger] coverage combine reported: %s - the map below may be "
                  "incomplete; re-run before trusting it." % exc, file=sys.stderr)
        measured = sorted(cov.get_data().measured_files())
        harness_rel = _gc_rel(harness, root)
        files = []
        for m in measured:
            rel = _gc_rel(os.path.abspath(m), root)
            # the harness measures the SUBJECT, not itself; sitecustomize is our scaffolding
            if not rel or rel == harness_rel or rel.endswith("/sitecustomize.py"):
                continue
            files.append(rel)
        files = sorted(set(files))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if not files:
        print("[qa_ledger] the run measured no source file inside %s - refusing to record "
              "an empty map (it would read as 'covers nothing')." % root, file=sys.stderr)
        sys.exit(2)

    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root,
                          capture_output=True, text=True)
    commit = head.stdout.strip() if head.returncode == 0 else None
    golden_rel = _gc_rel(os.path.abspath(args.golden), root) or args.golden

    path = os.path.join(root, GOLDEN_COVERAGE_FILE)
    manifest = _load_golden_coverage(root) or {"goldens": {}}
    manifest["goldens"][golden_rel] = {
        "harness": harness_rel,
        "files": files,
        "captured_at": _now(),
        "captured_at_commit": commit,
        "tool": "coverage.py " + coverage.__version__,
    }
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False, sort_keys=True)
        fh.write("\n")

    if args.json:
        print(json.dumps(manifest["goldens"][golden_rel], indent=2, ensure_ascii=False))
    else:
        print("GOLDEN-COVERAGE %s: %d source file(s) measured -> %s"
              % (golden_rel, len(files), GOLDEN_COVERAGE_FILE))
        for f in files[:20]:
            print("  " + f)



# --------------------------------------------------------------------------- #
# cleanroom  (ADR-008: verify the COMMIT, not the tree -- opt-in, human-supplied command)
# --------------------------------------------------------------------------- #

CLEAN_ROOM_KEY = "clean_room"


def _cr_cfg(ledger):
    cfg = ledger["config"].get("defaults", {}).get(CLEAN_ROOM_KEY)
    return cfg if isinstance(cfg, dict) else None


def _cr_latest(ledger, repo, ref=None):
    """Latest clean-room record for a repo, optionally pinned to one ref."""
    runs = [e for e in ledger.get(CLEAN_ROOM_KEY, [])
            if e.get("repo") == repo and (ref is None or e.get("ref") == ref)]
    return runs[-1] if runs else None


def cmd_cleanroom(args):
    """Run a command against a CLEAN CHECKOUT of one commit, in a throwaway worktree.

    Evidence produced in the maker's tree is true of the TREE; this produces evidence true
    of the COMMIT. As a side effect maker != checker becomes physical: the worktree cannot
    see uncommitted state.

    The engine does NOT decide what to run. The command arrives explicitly via --run, the
    same contract golden-coverage uses for --harness: the engine owns what it can guarantee
    (isolation, the SHA binding, cleanup) and never guesses what a project's suite is.
    Reading test_command_* from config and executing it would make the engine an executor
    of config-supplied shell, which it is not (ADR-008)."""
    import time
    ledger = _load(args.ledger)
    _repo_node(ledger, args.repo)
    repo_path = _repo_cfg(ledger, args.repo).get("path", ".")

    def git(*a, **kw):
        cwd = kw.pop("cwd", repo_path)
        try:
            return subprocess.run(["git"] + list(a), cwd=cwd, capture_output=True,
                                  text=True, encoding="utf-8", errors="replace")
        except OSError:
            return None

    rev = git("rev-parse", "--verify", (args.ref or "HEAD") + "^{commit}")
    if rev is None or rev.returncode != 0 or not rev.stdout.strip():
        print("[qa_ledger] cannot resolve ref %r in %s - nothing to verify."
              % (args.ref or "HEAD", repo_path), file=sys.stderr)
        sys.exit(2)
    sha = rev.stdout.strip()

    wt = tempfile.mkdtemp(prefix="uscha-cleanroom-")
    target = os.path.join(wt, "tree")
    started = time.time()
    record = {"repo": args.repo, "ref": sha, "at": _now(), "ok": False,
              "status": None, "wall_ms": None, "worktree_sha": None}
    keep = bool((_cr_cfg(ledger) or {}).get("keep_worktree_on_failure"))
    try:
        add = git("worktree", "add", "--detach", target, sha)
        if add is None or add.returncode != 0:
            record["status"] = "WORKTREE_FAILED"
            print("[qa_ledger] git worktree add failed:\n%s"
                  % ((add.stderr if add else "git unavailable") or "")[-800:], file=sys.stderr)
        else:
            # a worktree of a commit must be clean by construction; if it is not, something
            # (a smudge filter, a hook, a stale index) intervened and the isolation claim is
            # already false. Say so rather than measure in it.
            st = git("status", "--porcelain", cwd=target)
            if st is None or st.returncode != 0 or st.stdout.strip():
                record["status"] = "WORKTREE_DIRTY"
            else:
                record["worktree_sha"] = sha
                if args.setup:
                    r = subprocess.run(args.setup, cwd=target, shell=True,
                                       capture_output=True, text=True,
                                       encoding="utf-8", errors="replace")
                    if r.returncode != 0:
                        record["status"] = "SETUP_FAILED"
                        print((r.stderr or "")[-800:], file=sys.stderr)
                if record["status"] is None:
                    r = subprocess.run(args.run, cwd=target, shell=True,
                                       capture_output=True, text=True,
                                       encoding="utf-8", errors="replace")
                    record["exit_code"] = r.returncode
                    record["status"] = "GREEN" if r.returncode == 0 else "RED"
                    record["ok"] = r.returncode == 0
                    if r.returncode != 0:
                        print((r.stdout or "")[-1500:], file=sys.stderr)
    finally:
        record["wall_ms"] = int((time.time() - started) * 1000)
        # Cleanup is unconditional unless the human asked to inspect a FAILURE: a zombie
        # worktree is a defect, and `git worktree remove` alone leaves the admin entry behind.
        if record["ok"] or not keep:
            git("worktree", "remove", "--force", target)
            git("worktree", "prune")
            shutil.rmtree(wt, ignore_errors=True)
            # VERIFY the removal instead of assuming it. rmtree(ignore_errors=True) and a
            # discarded git return code can both fail in silence -- typically on Windows,
            # where a handle the caller's command left open blocks removal.
            if os.path.exists(target):
                record["cleanup_failed"] = True
                record["worktree_kept_at"] = target
                print("[qa_ledger] WARNING: the clean-room worktree could not be removed and "
                      "is still at %s (a process may still hold a handle). Remove it with: "
                      "git worktree remove --force %s && git worktree prune"
                      % (target, target), file=sys.stderr)
        else:
            record["worktree_kept_at"] = target

    ledger.setdefault(CLEAN_ROOM_KEY, []).append(record)
    ledger["step_counter"] += 1
    ledger["steps"].append({"n": ledger["step_counter"], "at": _now(),
                            "kind": "cleanroom", "repo": args.repo})
    _save(args.ledger, ledger)

    if args.json:
        print(json.dumps(record, indent=2, ensure_ascii=False))
    else:
        print("CLEANROOM %s @ %s: %s (%.1fs)"
              % (args.repo, sha[:8], record["status"], (record["wall_ms"] or 0) / 1000.0))
        if record.get("worktree_kept_at"):
            print("  worktree kept for inspection: " + record["worktree_kept_at"])
    sys.exit(0 if record["ok"] else 1)



# --------------------------------------------------------------------------- #
# curation  (ADR-009/010: candidates in quarantine, verdicts in the behavior
# ledger, and a promotion gate the ENGINE measures -- INV-CURATION-01)
# --------------------------------------------------------------------------- #

BEHAVIOR_LEDGER_FILE = "BEHAVIOR-LEDGER.md"
CANDIDATE_DIR = "discovery"
_BL_VERDICTS = ("preserve", "fix", "undefined")


def _parse_candidate(path):
    """Parse one candidate's frontmatter. Returns (data, errors); a candidate with errors
    is INVALID and named -- never silently skipped, because a skipped candidate would walk
    past the promotion gate unjudged."""
    errors = []
    try:
        # utf-8-sig: a BOM-adding editor must not turn a well-formed candidate into a
        # false "no frontmatter" (fresh-review LOW)
        with open(path, encoding="utf-8-sig", errors="replace") as fh:
            lines = fh.read().splitlines()
    except OSError as exc:
        return None, ["unreadable: %s" % exc]
    if not lines or lines[0].strip() != "---":
        return None, ["no frontmatter (evidence/confidence are mandatory, ADR-009)"]
    fm, i = [], 1
    while i < len(lines) and lines[i].strip() != "---":
        fm.append(lines[i]); i += 1
    if i >= len(lines):
        return None, ["frontmatter never closes"]
    etype, refs, conf, in_refs, in_evidence = None, [], None, False, False
    for ln in fm:
        s = ln.strip()
        indented = ln.startswith((" ", "\t"))
        if s.startswith("evidence:") and not indented:
            in_evidence = True; in_refs = False
        elif s.startswith("type:"):
            # scope + duplicates are MALFORMATION, not last-value-wins: a stray top-level
            # type:/confidence: after the evidence block silently overrode the nested one
            # and walked straight past the inference->low invariant (fresh-review HIGH).
            if not (in_evidence and indented):
                errors.append("type: outside the evidence block")
            elif etype is not None:
                errors.append("duplicate type: declaration")
            else:
                etype = s[len("type:"):].strip().strip("\x27\x22")
            in_refs = False
        elif s.startswith("refs:"):
            if not (in_evidence and indented):
                errors.append("refs: outside the evidence block")
            in_refs = in_evidence and indented
        elif s.startswith("confidence:") and not indented:
            if conf is not None:
                errors.append("duplicate confidence: declaration")
            else:
                conf = s[len("confidence:"):].strip().strip("\x27\x22")
            in_refs = False; in_evidence = False
        elif in_refs and s.startswith("- "):
            refs.append(s[2:].strip().strip("\x27\x22"))
        elif s and not indented:
            in_refs = False; in_evidence = False
    if etype not in ("test", "code", "inference"):
        errors.append("evidence.type %r (expected test|code|inference)" % etype)
    if not refs:
        errors.append("evidence.refs is empty (a candidate without evidence is a guess)")
    if conf not in ("high", "medium", "low"):
        errors.append("confidence %r (expected high|medium|low)" % conf)
    if etype == "inference" and conf != "low":
        errors.append("inference is ALWAYS low confidence (ADR-009); %r declared" % conf)
    return {"type": etype, "refs": refs, "confidence": conf}, errors


def _resolve_ref(repo_path, ref):
    """A ref must point at something REAL: `path`, `path:N`, `path:N-M` or `path#name`.
    Returns None when it resolves, else the reason."""
    frag = None
    if "#" in ref:
        ref, frag = ref.split("#", 1)
    span = None
    m = re.match(r"^(.*?):(\d+)(?:-(\d+))?$", ref)
    if m:
        ref = m.group(1)
        span = (int(m.group(2)), int(m.group(3) or m.group(2)))
    full = os.path.join(repo_path, ref.replace("/", os.sep))
    if _gc_rel(full, repo_path) is None:
        # an absolute path makes os.path.join DISCARD repo_path entirely, and ../ walks
        # out -- either way the "evidence" would point outside the legacy tree it claims
        # to evidence (fresh-review HIGH). Confinement is part of resolution.
        return "ref escapes the repo tree: %s" % ref
    if not os.path.isfile(full):
        return "file not found: %s" % ref
    if span or frag:
        try:
            with open(full, encoding="utf-8", errors="replace") as fh:
                body = fh.read()
        except OSError as exc:
            return "unreadable: %s" % exc
        if span:
            n = body.count("\n") + 1
            if span[0] < 1 or span[1] > n or span[0] > span[1]:
                return "lines %d-%d out of range (file has %d)" % (span[0], span[1], n)
        if frag and frag not in body:
            return "fragment %r not found in %s" % (frag, ref)
    return None


def _load_behavior_ledger(path):
    """Strict parse of the verdict table. Returns (rows, errors). Malformed is an ERROR,
    never a degrade: under the promotion gate, a silent "no verdicts" would UNBLOCK exactly
    what the gate guards (same posture as golden.scrub.json)."""
    rows, errors = [], []
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
    except OSError as exc:
        return [], ["unreadable: %s" % exc]
    for n, ln in enumerate(lines, 1):
        s = ln.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if cells and all(c and set(c) <= set("-: ") for c in cells):
            continue                                    # separator row (empty cells are NOT)
        low = [c.lower() for c in cells]
        if "candidate" in low and "verdict" in low:
            continue                                    # header row
        if len(cells) != 6:
            errors.append("line %d: %d cells, expected 6 (# | candidate | evidence | "
                          "confidence | verdict | adr)" % (n, len(cells)))
            continue
        _, cand, _ev, _conf, verdict, adr = cells
        if verdict not in _BL_VERDICTS:
            errors.append("line %d: verdict %r is not one of %s -- a fourth state is "
                          "malformation, not an option" % (n, verdict, "/".join(_BL_VERDICTS)))
        if not re.match(r"^ADR-\S+$", adr):
            errors.append("line %d: adr ref %r -- no verdict without its why (ADR-010)"
                          % (n, adr))
        if not cand:
            errors.append("line %d: empty candidate" % n)
        rows.append({"candidate": cand, "verdict": verdict, "adr": adr, "line": n})
    return rows, errors


def _bl_append_only(repo_path, rel):
    """The rows in HEAD must be a byte-identical prefix of the working file. Deliberately
    blunt (ADR-010): an audit trail that tolerates rewriting is not an audit trail.
    Returns "ok" | "new" | "violation" | "unmeasured"."""
    try:
        # probe the repo FIRST: "git failed entirely" and "file not in HEAD yet" are
        # different answers, and conflating them turned no-git into a silent "new"
        # (caught by T120's AC-RD-05 -- unmeasured must never be mistaken for anything).
        probe = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_path,
                               capture_output=True)
        if probe.returncode != 0:
            return "unmeasured"
        r = subprocess.run(["git", "show", "HEAD:" + rel.replace(os.sep, "/")],
                           cwd=repo_path, capture_output=True)
    except OSError:
        return "unmeasured"
    if r.returncode != 0:
        return "new"                                   # not in HEAD yet
    try:
        with open(os.path.join(repo_path, rel), "rb") as fh:
            cur = fh.read()
    except OSError:
        return "violation"                             # in HEAD but gone from the tree
    # normalize line endings on BOTH sides: with core.autocrlf, git stores LF and checks out
    # CRLF, so a raw byte compare reads that translation as tampering on every Windows box
    # (found by the first probe). Git itself treats line endings as non-content; so do we.
    # A verdict edit still cannot hide in a CRLF flip.
    cur_n = cur.replace(b"\r\n", b"\n")
    head_n = r.stdout.replace(b"\r\n", b"\n")
    return "ok" if cur_n.startswith(head_n) else "violation"


def _curation_state(repo_path):
    """Everything the gate needs, from one scan. None = feature unused (no discovery/):
    behavior identical to a release where this code does not exist (AC-RD-07)."""
    disc = os.path.join(repo_path, CANDIDATE_DIR)
    if not os.path.isdir(disc):
        return None
    cands = sorted(f for f in os.listdir(disc) if f.lower().endswith(".md"))
    state = {"candidates": [], "malformed": [], "ledger_errors": [],
             "append_only": None, "unjudged": [], "promote_as_is": [],
             "promote_with_declared_divergence": [], "excluded": []}
    for f in cands:
        data, errs = _parse_candidate(os.path.join(disc, f))
        if data:
            for ref in data["refs"]:
                bad = _resolve_ref(repo_path, ref)
                if bad:
                    errs.append("ref %r: %s" % (ref, bad))
        if errs:
            state["malformed"].append({"candidate": f, "errors": errs})
        else:
            state["candidates"].append(f)
    lpath = os.path.join(repo_path, BEHAVIOR_LEDGER_FILE)
    verdicts = {}
    if os.path.isfile(lpath):
        rows, lerrs = _load_behavior_ledger(lpath)
        state["ledger_errors"] = lerrs
        state["append_only"] = _bl_append_only(repo_path, BEHAVIOR_LEDGER_FILE)
        for row in rows:
            verdicts[row["candidate"]] = row["verdict"]   # append-only: the LATEST row wins
    for f in state["candidates"]:
        v = verdicts.get(f)
        if v is None:
            state["unjudged"].append(f)
        elif v == "preserve":
            state["promote_as_is"].append(f)
        elif v == "fix":
            state["promote_with_declared_divergence"].append(f)
        else:
            state["excluded"].append(f)
    return state


_SPEC_MARKER_MAX_BYTES = 2 * 1024 * 1024   # a 2MB+ tracked file is not where a spec-id
                                           # marker lives; unbounded reads are the T112 lesson


def _scan_spec_markers(repo_path, tracked):
    """Every `uscha-spec: <id>` marker in the given tracked files, as (file, id) pairs.
    One scanner shared by roundtrip and fidelity (REUSE-FIRST)."""
    pat = re.compile(r"uscha-spec:\s*([\w.\-]+)")
    hits = []
    for f in tracked:
        full = os.path.join(repo_path, f.replace("/", os.sep))
        try:
            if os.path.getsize(full) > _SPEC_MARKER_MAX_BYTES:
                continue
            with open(full, encoding="utf-8", errors="replace") as fh:
                body = fh.read()
        except OSError:
            continue
        for m in pat.finditer(body):
            hits.append((f, m.group(1)))
    return hits


def cmd_roundtrip(args):
    """Advisory spec-id coverage (ADR-009 slice 2, v1): which PROMOTED candidates are
    traceable in the code via an embedded `uscha-spec: <candidate>` marker. Coverage by id,
    deliberately NOT semantic matching -- that stays out of scope until it can be measured
    (ADR-011). Advisory end to end: exit 0 always, a report, never a gate."""
    ledger = _load(args.ledger)
    _repo_node(ledger, args.repo)
    repo_path = _scope_path(ledger, args.repo)
    st = _curation_state(repo_path)
    if st is None:
        print("ROUNDTRIP %s: no %s/ directory -- feature unused, nothing to trace."
              % (args.repo, CANDIDATE_DIR))
        sys.exit(0)
    promoted = sorted(st["promote_as_is"] + st["promote_with_declared_divergence"])
    ls = subprocess.run(["git", "ls-files"], cwd=repo_path, capture_output=True,
                        text=True, encoding="utf-8", errors="replace")
    tracked = [l.strip() for l in ls.stdout.splitlines()
               if ls.returncode == 0 and l.strip()
               and not l.strip().startswith(CANDIDATE_DIR + "/")
               and os.path.basename(l.strip()) != BEHAVIOR_LEDGER_FILE]
    found = set()
    for _f, mid in _scan_spec_markers(repo_path, tracked):
        found.add(mid if mid.endswith(".md") else mid + ".md")
    covered = [c for c in promoted if c in found]
    missing = [c for c in promoted if c not in found]
    out = {"repo": args.repo, "promoted": len(promoted), "covered": len(covered),
           "missing": missing, "advisory": True,
           "coverage_pct": round(100.0 * len(covered) / len(promoted), 1) if promoted else None}
    # Latest-state record so the mirador/status can surface it without anyone re-running the
    # command (the spec_drift pattern). A report that evaporates on exit is invisible to
    # every read surface -- which defeats the point of an advisory (found by auditing which
    # features actually REACH the user). Advisory data: no step counter, no gate record.
    ledger["roundtrip"] = dict(out, at=_now())
    _save(args.ledger, ledger)
    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        if not promoted:
            print("ROUNDTRIP %s: no promoted candidates yet -- nothing to trace (advisory)."
                  % args.repo)
        else:
            print("ROUNDTRIP %s: %d/%d promoted candidate(s) traceable by uscha-spec id "
                  "(advisory)" % (args.repo, len(covered), len(promoted)))
            for mss in missing:
                print("  .. %s: no uscha-spec marker found in the code" % mss)
    sys.exit(0)



def cmd_curation_check(args):
    """The INV-CURATION-01 gate, measured. Exit 2: malformation or tampering (config-error
    class -- candidates that cannot be validated, a ledger that cannot be trusted). Exit 1:
    valid candidates awaiting a human verdict (the quarantine holding). Exit 0: every
    candidate judged, or the feature unused."""
    ledger = _load(args.ledger)
    _repo_node(ledger, args.repo)
    repo_path = _scope_path(ledger, args.repo)
    st = _curation_state(repo_path)
    if st is None:
        if args.json:
            print(json.dumps({"repo": args.repo, "in_use": False}))
        else:
            print("CURATION %s: no %s/ directory -- feature unused, nothing to gate."
                  % (args.repo, CANDIDATE_DIR))
        sys.exit(0)
    out = dict(st)
    out.update({"repo": args.repo, "in_use": True})
    hard = bool(st["malformed"] or st["ledger_errors"]
                or st["append_only"] == "violation")
    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print("CURATION %s: %d candidate(s), %d judged, %d awaiting verdict"
              % (args.repo, len(st["candidates"]) + len(st["malformed"]),
                 len(st["promote_as_is"]) + len(st["promote_with_declared_divergence"])
                 + len(st["excluded"]), len(st["unjudged"])))
        for m in st["malformed"]:
            print("  !! %s: %s" % (m["candidate"], "; ".join(m["errors"])))
        for e in st["ledger_errors"]:
            print("  !! %s: %s" % (BEHAVIOR_LEDGER_FILE, e))
        if st["append_only"] == "violation":
            print("  !! %s: existing rows were EDITED -- append-only violated; revert and "
                  "add a new row + ADR instead" % BEHAVIOR_LEDGER_FILE)
        elif st["append_only"] == "unmeasured":
            print("  -- append-only: UNMEASURED (no git) -- reported, never claimed as pass")
        for f in st["unjudged"]:
            print("  .. %s: awaiting human verdict (blocks forward)" % f)
    sys.exit(2 if hard else (1 if st["unjudged"] else 0))



# --------------------------------------------------------------------------- #
# CANDIDATE-DELTA  (Diamond M1: discovery emits typed observations, verdicts
# become ledger objects, fidelity is a vector. ADR-013 / ADR-014.)
# --------------------------------------------------------------------------- #

CANDIDATE_DELTA_FILE = "CANDIDATE-DELTA.json"    # under discovery/, machine-canonical
CANDIDATE_DELTA_TWIN = "CANDIDATE-DELTA.md"      # rendered view, regenerated, never a source
CANONICAL_FILE = "CANONICAL.json"                # under discovery/: the promoted package
ISSUES_DEFERRED_FILE = "ISSUES-DEFERRED.md"
OBS_TYPES = ("behavior", "invariant", "contract", "config", "dependency", "decision_trace")
EVIDENCE_CLASSES = ("measured", "static", "narrated")
# ADR-014 / INV-ADVISORY-01: dimensions an LLM judges can only advise. The QUARANTINE is an
# engine invariant: nothing here may ever be registered as a blocking gate.
FIDELITY_DIMENSIONS = {
    "traceability": "measured", "behavior": "measured", "contracts": "measured",
    "curation_closure": "measured", "unexplained_code": "measured",
    "semantic": "advisory",
}
_DELTA_BANNER = ("GENERATED by qa_ledger.py discover (ADR-013). Rendered view of "
                 + CANDIDATE_DELTA_FILE + " -- hand edits are overwritten on regeneration.")


def _delta_seal(observations, repo, path):
    """The seal covers everything semantically load-bearing that the content-addressed OBS
    ids do NOT: the full observation set, the repo, and the bound. `path` changes what the
    delta MEANS (a partial discovery), so it must be sealed -- a hand edit of any of these is
    a named malformation (fresh-review MEDIUM)."""
    return _integrity_hash({"observations": observations, "repo": repo, "path": path})


def _obs_id(otype, statement, primary_prov):
    """Content-addressed: OBS-sha256(type + LF + normalized statement + LF + primary
    provenance)[:12]. Normalization = lowercase + whitespace collapse. Re-running discovery
    over unchanged code MUST yield byte-identical ids (AC-DD-04) -- the id is the identity
    of the observation, not of the run."""
    norm = re.sub(r"\s+", " ", statement.strip().lower())
    blob = otype + "\n" + norm + "\n" + primary_prov
    return "OBS-" + hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


def _tracked_files(repo_path):
    r = subprocess.run(["git", "ls-files"], cwd=repo_path, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        return None                                # no git: caller decides what that means
    return [l.strip() for l in r.stdout.splitlines() if l.strip()]


_STATIC_PY_MAX_BYTES = 2 * 1024 * 1024             # the T112 lesson: never unbounded reads


def _extract_static_py(repo_path, tracked):
    """v0 static extractors, PYTHON ONLY (ADR-013): public signatures via ast, dependency
    manifests via requirements*.txt. Deterministic by construction -- if AST/manifest cannot
    establish it, it is not `static`. Every other stack is UNSUPPORTED: counted and named,
    never guessed at. Returns (observations, unsupported_count)."""
    obs, unsupported = [], 0
    code_exts = (".java", ".kt", ".js", ".ts", ".tsx", ".go", ".rs", ".cs",
                 ".cpp", ".c", ".swift", ".dart", ".rb", ".php")
    for rel in tracked:
        low = rel.lower()
        if low.endswith(code_exts):
            unsupported += 1
            continue
        if not low.endswith(".py"):
            continue
        full = os.path.join(repo_path, rel.replace("/", os.sep))
        try:
            if os.path.getsize(full) > _STATIC_PY_MAX_BYTES:
                continue
            with open(full, encoding="utf-8", errors="replace") as fh:
                tree = ast.parse(fh.read())
        except (OSError, SyntaxError):
            continue                               # unparseable code yields no static facts
        for nd in tree.body:                       # top-level only: the PUBLIC surface
            if isinstance(nd, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if nd.name.startswith("_"):
                    continue
                sig = ", ".join(a.arg for a in nd.args.args)
                stmt = "%s defines function %s(%s)" % (rel, nd.name, sig)
                prov = "%s:%d" % (rel, nd.lineno)
            elif isinstance(nd, ast.ClassDef):
                if nd.name.startswith("_"):
                    continue
                stmt = "%s defines class %s" % (rel, nd.name)
                prov = "%s:%d" % (rel, nd.lineno)
            else:
                continue
            obs.append({"id": _obs_id("contract", stmt, prov), "type": "contract",
                        "statement": stmt, "evidence_class": "static",
                        "provenance": {"files": [prov],
                                       "derivation": "AST scan (python ast, top-level defs)",
                                       "tool": "qa_ledger-static-py"}})
    for man in sorted(f for f in tracked
                      if re.match(r"^requirements[^/]*\.txt$", f)):
        try:
            with open(os.path.join(repo_path, man), encoding="utf-8",
                      errors="replace") as fh:
                lines = fh.read().splitlines()
        except OSError:
            continue
        for n, ln in enumerate(lines, 1):
            s = ln.strip()
            if not s or s.startswith("#"):
                continue
            stmt = "depends on %s (declared in %s)" % (s, man)
            prov = "%s:%d" % (man, n)
            obs.append({"id": _obs_id("dependency", stmt, prov), "type": "dependency",
                        "statement": stmt, "evidence_class": "static",
                        "provenance": {"files": [prov],
                                       "derivation": "dependency manifest",
                                       "tool": "qa_ledger-static-py"}})
    return obs, unsupported


def _under_bound(rel, bound):
    return bound is None or rel == bound or rel.startswith(bound + "/")


def _golden_backed_obs(ledger, repo, repo_path, bound=None):
    """Measured observations: one per approved golden fixture, backed by the LATEST ingested
    golden-diff gate record (AC-DD-03). Only source: real, ledger-ingested execution. No
    ingested run -> no measured OBS; a fixture on disk that nothing executed is not evidence."""
    node = ledger["repos"].get(repo) or {}
    latest = None
    for rec in node.get("iterations", []):
        if rec.get("tool") == "gate:golden-diff":
            latest = rec
    if latest is None or latest.get("gated_reported", 1) != 0:
        return []                                  # no clean ingested run: nothing measured
    obs = []
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules", ".uscha-worktrees")]
        for f in sorted(files):
            if ".approved." not in f:
                continue
            rel = os.path.relpath(os.path.join(root, f), repo_path).replace(os.sep, "/")
            if not _under_bound(rel, bound):
                continue
            stmt = "behavior frozen by golden fixture %s matches the approved baseline" % rel
            obs.append({"id": _obs_id("behavior", stmt, rel), "type": "behavior",
                        "statement": stmt, "evidence_class": "measured",
                        "provenance": {"files": [rel],
                                       "derivation": "golden-diff run ingested %s"
                                                     % latest.get("at"),
                                       "tool": "golden-suite"}})
    return obs


def _load_narrated(path, repo_path):
    """Strict shape for the skill-supplied narrated observations: a JSON list of
    {type, statement, files}. The CLASS is the engine's to assign -- an input that declares
    evidence_class (or an id) is malformation, not a suggestion (ADR-013: the skill
    narrates, the engine classifies). Returns (observations, errors)."""
    errors = []
    try:
        with open(path, encoding="utf-8-sig") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        return [], ["unreadable narrated input: %s" % exc]
    if not isinstance(data, list):
        return [], ["narrated input must be a JSON list"]
    obs = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            errors.append("item %d: not an object" % i)
            continue
        if "evidence_class" in item or "id" in item:
            errors.append("item %d: declares %s -- the class and id are the ENGINE's to "
                          "assign; a narrated input cannot self-classify (ADR-013)"
                          % (i, "/".join(k for k in ("evidence_class", "id") if k in item)))
            continue
        otype = item.get("type")
        stmt = item.get("statement")
        stmt = stmt.strip() if isinstance(stmt, str) else ""
        files = item.get("files") or []
        if otype not in OBS_TYPES:
            errors.append("item %d: type %r (expected %s)" % (i, otype, "|".join(OBS_TYPES)))
            continue
        if not stmt:
            errors.append("item %d: empty statement" % i)
            continue
        if not isinstance(files, list) or not all(isinstance(x, str) for x in files):
            # a non-string ref must be a NAMED refusal, never a TypeError traceback
            # (fresh-review MEDIUM, reproduced)
            errors.append("item %d: files must be a list of strings" % i)
            continue
        bad = None
        for ref in files:
            bad = _resolve_ref(repo_path, ref)
            if bad:
                errors.append("item %d: ref %r: %s" % (i, ref, bad))
                break
        if bad:
            continue
        prov = files[0] if files else "agent-inference"
        obs.append({"id": _obs_id(otype, stmt, prov), "type": otype,
                    "statement": stmt, "evidence_class": "narrated",
                    "provenance": {"files": files, "derivation": "agent inference",
                                   "tool": "skill"}})
    return obs, errors


def _canonical_ids(repo_path, acceptance_file):
    """The ids the canonical package answers to today: traceable AC-nn ids from the
    acceptance file. Match is by ID REFERENCE (ADR-013) -- fuzzy semantic matching is
    exactly what stays out of scope."""
    path = acceptance_file if os.path.isabs(acceptance_file) \
        else os.path.join(repo_path, acceptance_file)
    if not os.path.isfile(path):
        return {}
    ids = {}
    try:
        items, _legacy = _parse_acceptance_items(path)
    except Exception:
        return {}
    for it in items or []:
        if it.get("id"):                          # normalized "AC-<n>" (numeric ids only)
            ids[int(it["id"].split("-")[1])] = it["id"]
    return ids


def _match_canonical(statement, canon_ids):
    m = re.search(r"(?i)\bAC[-_]?0*(\d+)\b", statement)
    if m and int(m.group(1)) in canon_ids:
        return canon_ids[int(m.group(1))]
    return None


def _render_delta_md(delta, verdicts):
    lines = ["<!-- %s -->" % _DELTA_BANNER, "",
             "# CANDIDATE-DELTA (rendered view)", ""]
    if delta.get("path"):
        # the bound is the artifact the HUMAN curates from -- a partial discovery must not
        # read as a complete one, or the shrunk INV-CURATION-01 surface is undisclosed
        # (fresh-review HIGH). The JSON recorded it; the human-facing view must too.
        lines += ["> **BOUNDED discovery** — mechanical scans were restricted to "
                  "`%s`. Files outside this path were NOT scanned; this delta is PARTIAL "
                  "by construction." % delta["path"], ""]
    lines += ["| id | type | class | verdict | statement | provenance |",
              "|----|------|-------|---------|-----------|------------|"]
    for o in delta["observations"]:
        v = verdicts.get(o["id"], "(uncurated)")
        files = ", ".join(o["provenance"].get("files") or []) or "-"
        stmt = o["statement"].replace("|", "\\|")
        lines.append("| %s | %s | %s | %s | %s | %s |"
                     % (o["id"], o["type"], o["evidence_class"], v, stmt, files))
    lines.append("")
    return "\n".join(lines)


def _delta_path(repo_path):
    return os.path.join(repo_path, CANDIDATE_DIR, CANDIDATE_DELTA_FILE)


def _load_delta(repo_path):
    """Strict loader (ADR-013): malformation is exit-2 class, never a silent degrade. The
    id of every OBS is RECOMPUTED -- the delta is mechanically derived and never hand-edited,
    so an id that no longer matches its content is tampering, said as such. Returns
    (delta, errors); delta None when the file does not exist (feature unused)."""
    path = _delta_path(repo_path)
    if not os.path.isfile(path):
        return None, []
    errors = []
    try:
        with open(path, encoding="utf-8-sig") as fh:
            delta = json.load(fh)
    except (OSError, ValueError) as exc:
        return {}, ["unreadable: %s" % exc]
    obs = delta.get("observations")
    if not isinstance(obs, list):
        return {}, ["no observations list"]
    seen = set()
    for i, o in enumerate(obs):
        if not isinstance(o, dict):
            errors.append("observation %d: not an object" % i)
            continue
        oid = o.get("id")
        if o.get("type") not in OBS_TYPES:
            errors.append("%s: type %r" % (oid or i, o.get("type")))
        if o.get("evidence_class") not in EVIDENCE_CLASSES:
            errors.append("%s: evidence_class %r" % (oid or i, o.get("evidence_class")))
        stmt = o.get("statement")
        prov = o.get("provenance")
        files = prov.get("files") if isinstance(prov, dict) else None
        # SHAPE before use (fresh-review HIGH, reproduced): a provenance that is a list, a
        # non-string statement or a non-string ref must be a NAMED error, never a traceback
        # -- the crash would take down phase/dashboard, the read-only readouts.
        if (not isinstance(stmt, str) or not stmt.strip()
                or not isinstance(prov, dict) or not isinstance(files, list)
                or not all(isinstance(x, str) for x in files)):
            errors.append("%s: statement/provenance shape invalid -- the delta is "
                          "derived, never hand-edited" % (oid or i))
        elif o.get("type") in OBS_TYPES:
            primary = files[0] if files else "agent-inference"
            want = _obs_id(o["type"], stmt, primary)
            if oid != want:
                errors.append("%s: id does not match its content (recomputed %s) -- the "
                              "delta is derived, never hand-edited" % (oid, want))
        if oid in seen:
            errors.append("%s: duplicate id" % oid)
        seen.add(oid)
    # the ids cover type+statement+primary provenance; the SEAL covers everything else
    # (evidence_class, canonical_match, the full ref list) -- without it, one JSON edit
    # launders narrated inference into measured evidence (fresh-review MEDIUM, reproduced)
    if not errors:
        seal = delta.get("_integrity")
        want = _delta_seal(obs, delta.get("repo"), delta.get("path"))
        if seal != want:
            errors.append("integrity seal %s does not match the delta content -- observations, "
                          "repo or path was hand-edited (regenerate via `discover`)"
                          % ("missing" if seal is None else repr(seal)))
    return delta, errors


def _curation_verdicts(ledger, repo):
    """Latest verdict per OBS from the append-only ledger records (re-curation supersedes,
    never deletes -- every superseded record stays retrievable, AC-CU-05)."""
    verdicts = {}
    for rec in ledger.get("curation") or []:
        if rec.get("repo") == repo:
            verdicts[rec["obs_id"]] = rec["verdict"]
    return verdicts


def _delta_state(ledger, repo, repo_path):
    """Everything the gates/readouts need about the delta, or None when unused."""
    delta, errors = _load_delta(repo_path)
    if delta is None:
        return None
    verdicts = _curation_verdicts(ledger, repo)
    obs = delta.get("observations") or [] if not errors else []
    uncurated = [o["id"] for o in obs if o.get("id") not in verdicts]
    undefined = [o["id"] for o in obs
                 if verdicts.get(o.get("id")) == "undefined"]
    return {"total": len(obs), "curated": len(obs) - len(uncurated),
            "uncurated": uncurated, "undefined_open": undefined,
            "malformed": errors}


def cmd_discover(args):
    """Emit discovery/CANDIDATE-DELTA.json (ADR-013): typed, content-addressed observations
    from three strictly separated sources -- measured (ledger-ingested golden runs), static
    (deterministic extractors, Python-only v0), narrated (skill-supplied inference; the
    engine classifies and stores, it NEVER calls an LLM). Plus a rendered .md twin."""
    ledger = _load(args.ledger)
    _repo_node(ledger, args.repo)
    repo_path = _scope_path(ledger, args.repo)
    tracked = _tracked_files(repo_path)
    if tracked is None:
        print("[qa_ledger] discover: %s is not a git tree -- discovery derives provenance "
              "from tracked files and cannot proceed without it." % repo_path,
              file=sys.stderr)
        sys.exit(2)
    bound = None
    if args.path is not None:
        # the bound restricts the MECHANICAL scans (static, measured); narrated input stays
        # the skill's to scope. Field-found before the first run (AC-DD-07): "real, bounded"
        # is unimplementable without it.
        raw = args.path.replace("\\", "/").strip()
        if not raw:
            # an empty --path is the silent-degrade trap (a wrapper passing an unset var):
            # falsy would mean "no bound" and quietly scan the whole repo (fresh-review MED)
            print("[qa_ledger] discover: --path is empty -- omit --path to scan the whole "
                  "repo; an empty bound is not a bound.", file=sys.stderr)
            sys.exit(2)
        bound = posixpath.normpath(raw).strip("/")     # ./src, src/ , /src -> src
        if bound in (".", "") or bound == ".." or bound.startswith("../"):
            print("[qa_ledger] discover: --path %r does not name a subtree inside the repo."
                  % args.path, file=sys.stderr)
            sys.exit(2)
        if _gc_rel(os.path.join(repo_path, bound.replace("/", os.sep)), repo_path) is None:
            print("[qa_ledger] discover: --path %r escapes the repo tree." % args.path,
                  file=sys.stderr)
            sys.exit(2)
        tracked = [f for f in tracked if _under_bound(f, bound)]
        if not tracked:
            # a typo'd bound silently emitting an empty delta is the silent-degrade trap
            print("[qa_ledger] discover: --path %r matches no tracked file -- refusing to "
                  "emit an empty delta for a bound that points at nothing." % args.path,
                  file=sys.stderr)
            sys.exit(2)
    static_obs, unsupported = _extract_static_py(repo_path, tracked)
    measured_obs = _golden_backed_obs(ledger, args.repo, repo_path, bound)
    narrated_obs, nerrs = ([], [])
    if args.narrated:
        narrated_obs, nerrs = _load_narrated(args.narrated, repo_path)
    if nerrs:
        for e in nerrs:
            print("[qa_ledger] discover: %s" % e, file=sys.stderr)
        sys.exit(2)                                # malformed input: refuse, never degrade
    by_id = {}
    for o in measured_obs + static_obs + narrated_obs:
        by_id.setdefault(o["id"], o)               # identical content = the same observation
    acc = (args.acceptance
           or ledger.get("config", {}).get("defaults", {}).get("acceptance_file")
           or "ACCEPTANCE.md")
    canon = _canonical_ids(repo_path, acc)
    for o in by_id.values():
        o["canonical_match"] = _match_canonical(o["statement"], canon)
    observations = sorted(by_id.values(), key=lambda o: o["id"])
    delta = {"_generated_by": "qa_ledger.py discover (ADR-013) -- machine-canonical; "
                              "never hand-edit (ids are content-addressed; the seal "
                              "covers observations, repo and path)",
             "_integrity": _delta_seal(observations, args.repo, bound),
             "repo": args.repo,
             **({"path": bound} if bound else {}),
             "observations": observations,
             "static_unsupported": {"files": unsupported,
                                    "note": "static extractors are Python-only in v0 "
                                            "(ADR-013); other stacks report here, "
                                            "never guess"}}
    disc = os.path.join(repo_path, CANDIDATE_DIR)
    os.makedirs(disc, exist_ok=True)
    with open(_delta_path(repo_path), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(delta, indent=2, ensure_ascii=False) + "\n")
    twin_path = os.path.join(disc, CANDIDATE_DELTA_TWIN)
    twin = _render_delta_md(delta, _curation_verdicts(ledger, args.repo))
    prev = None
    if os.path.isfile(twin_path):
        try:
            with open(twin_path, encoding="utf-8-sig") as fh:
                prev = fh.read()
        except OSError:
            prev = None
    with open(twin_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(twin)
    if prev is not None and prev != twin:
        # stderr, not stdout: on this exact path --json must still emit parseable output
        # (fresh-review MEDIUM, reproduced)
        print("[qa_ledger] discover: %s differed from the regenerated render -- overwritten "
              "(the .md twin is a rendered view, never a source; edit verdicts via `curate`)"
              % CANDIDATE_DELTA_TWIN, file=sys.stderr)
    counts = {c: sum(1 for o in observations if o["evidence_class"] == c)
              for c in EVIDENCE_CLASSES}
    out = {"repo": args.repo, "observations": len(observations), "by_class": counts,
           "static_unsupported_files": unsupported,
           "delta": os.path.join(CANDIDATE_DIR, CANDIDATE_DELTA_FILE)}
    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print("DISCOVER %s: %d observation(s) (%d measured / %d static / %d narrated) -> %s"
              % (args.repo, len(observations), counts["measured"], counts["static"],
                 counts["narrated"], out["delta"]))
        if unsupported:
            print("  -- %d non-Python source file(s): static extraction UNSUPPORTED in v0 "
                  "(ADR-013) -- reported, not guessed" % unsupported)
    sys.exit(0)


def cmd_curate(args):
    """ONE human verdict for ONE observation, recorded as an append-only ledger object
    (ADR-013). No batch path exists -- and this refusal is the assertion of its absence:
    curation is the human's judgment applied per-item, never a bulk operation."""
    if re.search(r"[,\s*]", args.obs) or args.obs.lower() in ("all", "*"):
        print("[qa_ledger] curate: %r -- one OBS, one human verdict. A batch-accept path "
              "does not exist and will not (ADR-013, INV-CURATION-01)." % args.obs,
              file=sys.stderr)
        sys.exit(2)
    ledger = _load(args.ledger)
    _repo_node(ledger, args.repo)
    repo_path = _scope_path(ledger, args.repo)
    delta, errors = _load_delta(repo_path)
    if delta is None:
        print("[qa_ledger] curate: no %s -- run `discover` first."
              % os.path.join(CANDIDATE_DIR, CANDIDATE_DELTA_FILE), file=sys.stderr)
        sys.exit(2)
    if errors:
        for e in errors:
            print("[qa_ledger] curate: delta malformed: %s" % e, file=sys.stderr)
        sys.exit(2)
    known = {o["id"] for o in delta.get("observations") or []}
    if args.obs not in known:
        print("[qa_ledger] curate: %s is not in the current delta -- a verdict must judge "
              "a real observation." % args.obs, file=sys.stderr)
        sys.exit(2)
    prev = _curation_verdicts(ledger, args.repo).get(args.obs)
    human = args.human or os.environ.get("USERNAME") or os.environ.get("USER") or "unknown"
    rec = {"obs_id": args.obs, "verdict": args.verdict, "human": human,
           "at": _now(), "note": args.note, "repo": args.repo}
    ledger.setdefault("curation", []).append(rec)
    _save(args.ledger, ledger)
    if prev and prev != args.verdict:
        print("[qa_ledger] curate: %s = %s (supersedes %r -- the earlier record stays; "
              "append-only, never deleted)" % (args.obs, args.verdict, prev))
    else:
        print("[qa_ledger] curate: %s = %s (by %s)" % (args.obs, args.verdict, human))
    sys.exit(0)


def cmd_promote(args):
    """Move ONLY preserve-verdict observations into the canonical package, with
    `derived_from` lineage (ADR-013). fix -> a work item in ISSUES-DEFERRED.md, never
    canonical. undefined -> stays open in the readouts. ANY uncurated OBS -> hard refusal
    naming the ids; nothing moves (INV-CURATION-01, fail-closed)."""
    ledger = _load(args.ledger)
    _repo_node(ledger, args.repo)
    repo_path = _scope_path(ledger, args.repo)
    delta, errors = _load_delta(repo_path)
    if delta is None:
        print("[qa_ledger] promote: no %s -- run `discover` first."
              % os.path.join(CANDIDATE_DIR, CANDIDATE_DELTA_FILE), file=sys.stderr)
        sys.exit(2)
    if errors:
        for e in errors:
            print("[qa_ledger] promote: delta malformed: %s" % e, file=sys.stderr)
        sys.exit(2)
    obs = delta.get("observations") or []
    verdicts = _curation_verdicts(ledger, args.repo)
    uncurated = [o["id"] for o in obs if o["id"] not in verdicts]
    if uncurated:
        print("[qa_ledger] promote: REFUSED -- %d observation(s) without a human verdict: %s"
              % (len(uncurated), ", ".join(uncurated[:5])
                 + (" (+%d)" % (len(uncurated) - 5) if len(uncurated) > 5 else "")),
              file=sys.stderr)
        print("  INV-CURATION-01: nothing promotes unjudged. Curate each with "
              "`curate --obs <id> --verdict preserve|fix|undefined`.", file=sys.stderr)
        sys.exit(1)
    canon_path = os.path.join(repo_path, CANDIDATE_DIR, CANONICAL_FILE)
    canonical = {"_generated_by": "qa_ledger.py promote (ADR-013) -- items carry "
                                  "derived_from lineage to their OBS", "items": []}
    if os.path.isfile(canon_path):
        try:
            with open(canon_path, encoding="utf-8-sig") as fh:
                canonical = json.load(fh)
        except (OSError, ValueError) as exc:
            print("[qa_ledger] promote: %s unreadable: %s" % (CANONICAL_FILE, exc),
                  file=sys.stderr)
            sys.exit(2)
    have = {it.get("derived_from") for it in canonical.get("items") or []}
    promoted, fixes, undefined_open = [], [], []
    for o in obs:
        v = verdicts[o["id"]]
        if v == "preserve":
            if o["id"] not in have:
                canonical.setdefault("items", []).append(
                    {"statement": o["statement"], "type": o["type"],
                     "evidence_class": o["evidence_class"],
                     "provenance": o["provenance"], "derived_from": o["id"]})
                promoted.append(o["id"])
        elif v == "fix":
            fixes.append(o)
        else:
            undefined_open.append(o["id"])
    canonical["items"] = sorted(canonical.get("items") or [],
                                key=lambda it: it.get("derived_from") or "")
    with open(canon_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(canonical, indent=2, ensure_ascii=False) + "\n")
    new_fix = []
    if fixes:
        dpath = os.path.join(repo_path, ISSUES_DEFERRED_FILE)
        existing = ""
        if os.path.isfile(dpath):
            with open(dpath, encoding="utf-8-sig", errors="replace") as fh:
                existing = fh.read()
        add = [o for o in fixes if o["id"] not in existing]
        if add:
            with open(dpath, "a", encoding="utf-8", newline="\n") as fh:
                if existing and not existing.endswith("\n"):
                    fh.write("\n")
                for o in add:
                    fh.write("- [ ] %s (curated `fix`): %s -- observed behavior the human "
                             "ruled a defect; NEVER canonical (ADR-013)\n"
                             % (o["id"], o["statement"]))
            new_fix = [o["id"] for o in add]
    ledger["candidate_delta"] = {"repo": args.repo, "total": len(obs),
                                 "curated": len(obs),
                                 "undefined_open": undefined_open,
                                 "canonical_items": len(canonical["items"]),
                                 "at": _now()}
    _save(args.ledger, ledger)
    out = {"repo": args.repo, "promoted": promoted, "fix_deferred": new_fix,
           "undefined_open": undefined_open,
           "canonical": os.path.join(CANDIDATE_DIR, CANONICAL_FILE)}
    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print("PROMOTE %s: %d promoted, %d fix -> %s, %d undefined OPEN"
              % (args.repo, len(promoted), len(new_fix), ISSUES_DEFERRED_FILE,
                 len(undefined_open)))
        for oid in undefined_open:
            print("  .. %s: undefined -- stays open and visible until re-curated" % oid)
    sys.exit(0)


def _fid_dim(value, provenance, **extra):
    d = {"value": value, "provenance": provenance}
    d.update(extra)
    return d


def cmd_fidelity(args):
    """The fidelity VECTOR (ADR-014): five independently measured dimensions, each with its
    own provenance, plus the advisory quarantine. Deterministic: same inputs, same numbers,
    no LLM anywhere in the measured path. Advisory dimensions can NEVER gate -- attempting
    to configure one as blocking is an engine refusal, not a configuration
    (INV-ADVISORY-01)."""
    ledger = _load(args.ledger)
    node = _repo_node(ledger, args.repo)
    repo_path = _scope_path(ledger, args.repo)
    cfg = {}
    if os.path.isfile(args.config):
        try:
            with open(args.config, encoding="utf-8-sig") as fh:
                cfg = json.load(fh)
        except (OSError, ValueError) as exc:
            # a config that cannot be parsed cannot declare gates -- swallowing the error
            # would DISABLE the INV-ADVISORY-01 refusal on a syntax slip (fresh-review
            # HIGH, reproduced). Malformation is exit 2, never a silent degrade.
            print("[qa_ledger] fidelity: %s unreadable: %s -- refusing to guess what it "
                  "declares." % (args.config, exc), file=sys.stderr)
            sys.exit(2)
    declared = ((cfg.get("defaults") or {}).get("fidelity") or {}).get("gate") or []
    for dim in (ledger.get("config", {}).get("defaults", {}).get("fidelity")
                or {}).get("gate") or []:
        if dim not in declared:                    # both surfaces checked -- no silent path
            declared.append(dim)
    for dim in declared:
        cls = FIDELITY_DIMENSIONS.get(dim)
        if cls is None:
            print("[qa_ledger] fidelity: %r is not a dimension (%s)"
                  % (dim, ", ".join(sorted(FIDELITY_DIMENSIONS))), file=sys.stderr)
            sys.exit(2)
        if cls == "advisory":
            print("[qa_ledger] fidelity: REFUSED -- %r is an ADVISORY-class dimension and "
                  "can never be registered as blocking. This is an engine invariant "
                  "(INV-ADVISORY-01, ADR-014), not a configuration." % dim, file=sys.stderr)
            sys.exit(2)
        print("[qa_ledger] fidelity: gating on measured dimension %r is not implemented "
              "in v0 (ADR-014) -- declared but unenforceable is a silent lie; remove it "
              "or wait for the milestone that wires it." % dim, file=sys.stderr)
        sys.exit(2)
    delta, derrs = _load_delta(repo_path)
    if derrs:
        # same posture as curate/promote: a delta that EXISTS but cannot be validated is
        # exit 2, and "no delta" must never be the label for it (fresh-review MEDIUM)
        for e in derrs:
            print("[qa_ledger] fidelity: delta malformed: %s" % e, file=sys.stderr)
        sys.exit(2)
    obs = (delta.get("observations") or []) if delta else []
    verdicts = _curation_verdicts(ledger, args.repo)
    # fidelity respects the SAME bound that produced the delta (user decision, FR-001): a
    # bounded discovery is measured over its own subtree, so unexplained_code and the other
    # mechanical dimensions never mix the delta's scope with the whole repo's.
    bound = delta.get("path") if delta else None
    dims = {}
    # traceability: canonical items reachable in code via the uscha-spec id machinery
    canon_items = []
    canon_path = os.path.join(repo_path, CANDIDATE_DIR, CANONICAL_FILE)
    if os.path.isfile(canon_path):
        try:
            with open(canon_path, encoding="utf-8-sig") as fh:
                canon_items = json.load(fh).get("items") or []
        except (OSError, ValueError):
            canon_items = []
    tracked = [f for f in (_tracked_files(repo_path) or []) if _under_bound(f, bound)]
    _scope = " (bounded to %s)" % bound if bound else ""
    if bound:
        # scope the DENOMINATOR too, not just the file scan: promote MERGES into CANONICAL
        # repo-wide, so an earlier unbounded promote would otherwise count out-of-bound
        # items as "no longer derives" -- the exact scope-mixing this release kills, half-
        # done if only the numerator moves (fresh-review LOW). An item is under the bound
        # when its primary provenance file is.
        canon_items = [it for it in canon_items
                       if any(_under_bound(f.split(":")[0].split("#")[0], bound)
                              for f in (it.get("provenance") or {}).get("files") or [])]
    marked, marker_files = set(), set()
    for f, mid in _scan_spec_markers(repo_path, tracked):
        marked.add(mid)
        marker_files.add(f)
    if canon_items:
        traced = sum(1 for it in canon_items if (it.get("derived_from") or "") in marked)
        dims["traceability"] = _fid_dim(round(traced / len(canon_items), 4),
                                        "uscha-spec marker scan over %d git-tracked "
                                        "files%s vs %d canonical item(s)"
                                        % (len(tracked), _scope, len(canon_items)))
    else:
        dims["traceability"] = _fid_dim(None, "UNMEASURED: no canonical items promoted yet")
    # behavior: the latest ingested golden-diff gate verdict
    latest_g = None
    for rec in node.get("iterations", []):
        if rec.get("tool") == "gate:golden-diff":
            latest_g = rec
    if latest_g is not None:
        ok = latest_g.get("gated_reported", 1) == 0
        prov = "gate:golden-diff record ingested %s (iteration %s)" % (
            latest_g.get("at"), latest_g.get("iteration"))
        cr = _cr_latest(ledger, args.repo)
        if cr and cr.get("status") == "GREEN":
            prov += "; clean-room GREEN at %s" % (cr.get("ref") or "?")[:12]
        dims["behavior"] = _fid_dim(1.0 if ok else 0.0, prov)
    else:
        dims["behavior"] = _fid_dim(None, "UNMEASURED: no golden-diff run ingested "
                                          "(log-gate --kind golden-diff)")
    # contracts: canonical static items still derivable from the code RIGHT NOW
    static_canon = [it for it in canon_items if it.get("evidence_class") == "static"]
    if static_canon:
        cur_static, _u = _extract_static_py(repo_path, tracked)
        cur_ids = {o["id"] for o in cur_static}
        okc = sum(1 for it in static_canon if it.get("derived_from") in cur_ids)
        dims["contracts"] = _fid_dim(round(okc / len(static_canon), 4),
                                     "re-ran static extractors%s; %d/%d canonical static "
                                     "item(s) still derive from the code"
                                     % (_scope, okc, len(static_canon)))
    else:
        dims["contracts"] = _fid_dim(None, "UNMEASURED: no static-class canonical items")
    # curation_closure: curated OBS / total OBS in the active delta. With --ir (ADR-015) it is
    # answered as a path query over the graph -- OBS nodes reachable to a CURATION node via an
    # OBS->CURATION edge / OBS nodes. It reproduces v0 when the graph's OBS set equals the
    # delta's (the FIELD-RUN-001 case); a canonical carrying OBS beyond the active delta would
    # widen the denominator, which is the graph's honest answer, not v0's.
    if args.ir:
        graph = _extract_ir(repo_path, ledger)
        obs_nodes = [nd["id"] for nd in graph["nodes"] if nd["type"] == "OBS"]
        cured = {e["from"] for e in graph["edges"] if e["type"] == "OBS->CURATION"}
        if obs_nodes:
            hit = sum(1 for oid in obs_nodes if oid in cured)
            dims["curation_closure"] = _fid_dim(
                round(hit / len(obs_nodes), 4),
                "IR path query: %d/%d OBS node(s) reach a CURATION node (IR v%s)"
                % (hit, len(obs_nodes), IR_SCHEMA))
        else:
            dims["curation_closure"] = _fid_dim(
                None, "UNMEASURED: no OBS nodes in the IR graph")
    elif obs:
        cur = sum(1 for o in obs if o["id"] in verdicts)
        dims["curation_closure"] = _fid_dim(round(cur / len(obs), 4),
                                            "%d/%d OBS in %s carry a ledger verdict"
                                            % (cur, len(obs), CANDIDATE_DELTA_FILE))
    else:
        dims["curation_closure"] = _fid_dim(
            None, "UNMEASURED: no delta" if delta is None
            else "no observations in the delta")
    # unexplained_code: v0 deliberately crude -- unit = source FILE (ADR-014: crude and
    # honest beats fine-grained and narrated; over-fires on monoliths BY DESIGN)
    rtype = (_repo_cfg(ledger, args.repo).get("type")
             if args.repo != "integration" else None)
    src_exts = (".py", ".java", ".kt", ".js", ".ts", ".tsx", ".go", ".rs", ".cs",
                ".cpp", ".c", ".swift", ".dart", ".rb", ".php")
    prod = [f for f in tracked
            if f.lower().endswith(src_exts)
            and not f.startswith(CANDIDATE_DIR + "/")
            and not _is_test_path(f, rtype)]
    lineage = set(marker_files)                    # a file CARRYING a spec marker is explained
    for o in obs:
        if verdicts.get(o["id"]) == "preserve":
            for ref in o["provenance"].get("files") or []:
                lineage.add(ref.split(":")[0].split("#")[0])
    for it in canon_items:
        for ref in (it.get("provenance") or {}).get("files") or []:
            lineage.add(ref.split(":")[0].split("#")[0])
    if prod:
        unex = [f for f in prod if f not in lineage]
        dims["unexplained_code"] = _fid_dim(
            round(len(unex) / len(prod), 4),
            "%d/%d tracked prod source file(s)%s with no path to a canonical item or "
            "preserved OBS (v0 granularity: FILE)" % (len(unex), len(prod), _scope),
            files=unex[:10] + (["(+%d)" % (len(unex) - 10)] if len(unex) > 10 else []))
    else:
        dims["unexplained_code"] = _fid_dim(None, "UNMEASURED: no tracked prod source files")
    dims["semantic"] = _fid_dim(None, "not wired: an LLM-judged comparison enters as "
                                      "advisory only and can NEVER gate (INV-ADVISORY-01)")
    out = {"repo": args.repo,
           **({"path": bound} if bound else {}),
           "dimensions": {k: dict(dims[k], **{"class": FIDELITY_DIMENSIONS[k]})
                          for k in ("traceability", "behavior", "contracts",
                                    "curation_closure", "unexplained_code", "semantic")}}
    ledger["fidelity"] = dict(out, at=_now())
    _save(args.ledger, ledger)
    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print("FIDELITY %s%s (vector -- no blend; each number stands on its own evidence):"
              % (args.repo, " [bounded to %s]" % bound if bound else ""))
        for k, d in out["dimensions"].items():
            val = "UNMEASURED" if d["value"] is None else "%.2f" % d["value"]
            print("  %-17s %-10s [%s] %s" % (k, val, d["class"], d["provenance"]))
    sys.exit(0)


# --------------------------------------------------------------------------- #
# IR  (Diamond M2: the canonical package extracts into a typed graph. ADR-015.
# Markdown stays canonical; the IR is a derived index. What cannot be typed
# deterministically is UNTYPED -- visible, counted, never guessed.)
# --------------------------------------------------------------------------- #

IR_DIR = "ir"
IR_FILE = "IR.json"
IR_TWIN = "IR.md"
IR_SCHEMA = "0.1"
IR_NODE_TYPES = ("REQ", "INV", "AC", "CONTRACT", "DECISION", "NFR",
                 "GOLDEN", "OBS", "CURATION", "EVIDENCE")
IR_EDGE_TYPES = ("REQ->AC", "AC->EVIDENCE", "DECISION->INV", "OBS->CURATION",
                 "CURATION->canonical", "supersedes", "derived_from")
# broader than _AC_ID: the forward package uses sub-namespaced ids (AC-DD-07, AC-FV-06)
_IR_AC_LINE = re.compile(r"^\s*[-*]\s*\[[ xX]\]\s*(AC-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)\b\s*[-—:]*\s*(.*)$")
_IR_INV_LINE = re.compile(r"^\s*[-*]\s*\*\*(INV-[A-Za-z0-9-]+)\s*[—-]+\s*(.*?)\*\*")
_IR_ADR_REF = re.compile(r"\bADR-0*(\d+)\b")
_IR_INV_REF = re.compile(r"\bINV-[A-Za-z0-9-]+\b")
_IR_SUPERSEDE = re.compile(r"(?i)supersed\w*\s+(ADR-0*\d+)")
_IR_BANNER = ("GENERATED by qa_ledger.py ir-extract (ADR-015). Rendered view of "
              + IR_FILE + " -- hand edits are overwritten on regeneration.")


def _ir_node_id(ntype, text, source):
    """Content-address the ID-less (ADR-015 option B): nodes with a native human id keep it;
    only nodes with nothing human to anchor to get NODE-sha256(type+text+source)[:12]."""
    norm = re.sub(r"\s+", " ", (text or "").strip().lower())
    return "NODE-" + hashlib.sha256(
        (ntype + "\n" + norm + "\n" + source).encode("utf-8")).hexdigest()[:12]


def _ir_read_lines(path):
    try:
        with open(path, encoding="utf-8-sig", errors="replace") as fh:
            return fh.read().splitlines()
    except OSError:
        return None


def _extract_ir(repo_path, ledger):
    """Deterministic extraction of the forward canonical package into a typed graph. Every
    node/edge is derived from an EXISTING structural convention or reference -- nothing is
    inferred. A line that fills a structural slot but cannot be typed lands in `untyped`."""
    nodes, edges, untyped = [], [], []
    seen_ids = set()

    def add(node):
        if node["id"] not in seen_ids:
            seen_ids.add(node["id"])
            nodes.append(node)

    # AC nodes <- ACCEPTANCE.md checkboxes carrying an AC id; a checkbox WITHOUT an id is an
    # acceptance slot the conventions do not type -> untyped (never a guessed id).
    acc_lines = _ir_read_lines(os.path.join(repo_path, "ACCEPTANCE.md")) or []
    for n, ln in enumerate(acc_lines, 1):
        s = ln.strip()
        if s[:5].lower() not in ("- [x]", "- [ ]", "* [x]", "* [ ]"):
            continue
        m = _IR_AC_LINE.match(ln)
        src = {"file": "ACCEPTANCE.md", "line": n}
        if m:
            add({"id": m.group(1).upper(), "type": "AC",
                 "statement": m.group(2).strip(), "source": src})
        else:
            untyped.append({"text": s[5:].strip(), "source": src,
                            "reason": "acceptance checkbox without a traceable AC-id"})

    # INV nodes <- CONSTITUTION.md `- **INV-XXX-NN — Title.**` headings
    con_lines = _ir_read_lines(os.path.join(repo_path, "CONSTITUTION.md")) or []
    inv_ids = set()
    for n, ln in enumerate(con_lines, 1):
        m = _IR_INV_LINE.match(ln)
        if m:
            add({"id": m.group(1).upper(), "type": "INV",
                 "statement": m.group(2).strip().rstrip("."),
                 "source": {"file": "CONSTITUTION.md", "line": n}})
            inv_ids.add(m.group(1).upper())

    # DECISION nodes <- docs/adr/*.md (native ADR-NNN id, title, file); edges to the INVs the
    # ADR governs/states, and supersedes edges -- both from references already in the body.
    adr_dir = os.path.join(repo_path, "docs", "adr")
    ac_ids = {nd["id"] for nd in nodes if nd["type"] == "AC"}
    for row in _mirador_adrs(adr_dir):
        add({"id": row["id"], "type": "DECISION", "statement": row["t"],
             "source": {"file": os.path.relpath(row["file"], repo_path).replace(os.sep, "/"),
                        "line": 1}})
        body = _ir_read_lines(row["file"]) or []
        text = "\n".join(body)
        for inv in set(_IR_INV_REF.findall(text)):
            if inv.upper() in inv_ids:
                edges.append({"from": row["id"], "to": inv.upper(), "type": "DECISION->INV"})
        for sup in set(_IR_SUPERSEDE.findall(text)):
            edges.append({"from": row["id"],
                          "to": "ADR-%03d" % int(re.search(r"\d+", sup).group()),
                          "type": "supersedes"})
        # an ADR's Verification checklist references its ACs -> REQ->AC is absent here (no REQ
        # layer yet), but AC nodes referenced by an ADR are real edges DECISION mentions AC:
        for aid in {m.group(0)[1:-1].upper()
                    for m in re.finditer(r"\(AC-[A-Za-z0-9-]+\)", text)}:
            if aid in ac_ids:                       # set(): an AC cited twice is one edge
                edges.append({"from": row["id"], "to": aid, "type": "REQ->AC"})

    # GOLDEN nodes <- git-tracked approved fixtures (the path is a native, stable id)
    tracked = _tracked_files(repo_path) or []
    gold_marker = ".appro" + "ved."
    for f in tracked:
        if gold_marker in f:
            add({"id": f, "type": "GOLDEN", "statement": "approved golden fixture",
                 "source": {"file": f, "line": 1}})

    # OBS / CURATION <- the active delta's observations (all of them, so curation_closure is
    # a real path query over the graph) + the ledger's curation records. Absent in a repo
    # that never ran a field run -> simply no such nodes.
    delta, derrs = _load_delta(repo_path)
    if delta and not derrs:
        for o in delta.get("observations") or []:
            prov = (o.get("provenance") or {}).get("files") or []
            add({"id": o["id"], "type": "OBS", "statement": o.get("statement") or "",
                 "source": {"file": prov[0].split(":")[0] if prov else "delta", "line": 1}})
    canon_path = os.path.join(repo_path, CANDIDATE_DIR, CANONICAL_FILE)
    canon_items = []
    if os.path.isfile(canon_path):
        try:
            with open(canon_path, encoding="utf-8-sig") as fh:
                canon_items = json.load(fh).get("items") or []
        except (OSError, ValueError):
            canon_items = []
    for it in canon_items:
        oid = it.get("derived_from")
        if not oid:
            continue
        prov = (it.get("provenance") or {}).get("files") or []
        add({"id": oid, "type": "OBS", "statement": it.get("statement") or "",
             "source": {"file": prov[0].split(":")[0] if prov else "canonical", "line": 1}})
    for rec in ledger.get("curation") or []:
        oid = rec.get("obs_id")
        if not oid:
            continue
        cid = "CUR-" + hashlib.sha256(
            (oid + "\n" + (rec.get("at") or "")).encode("utf-8")).hexdigest()[:12]
        add({"id": cid, "type": "CURATION",
             "statement": "%s: %s" % (rec.get("verdict"), oid),
             "source": {"file": "QA-LEDGER.json", "line": 0}})
        if oid in seen_ids:
            edges.append({"from": oid, "to": cid, "type": "OBS->CURATION"})

    node_ids = {nd["id"] for nd in nodes}
    kept, dropped = [], 0
    for e in edges:
        if e["from"] in node_ids and e["to"] in node_ids:
            kept.append(e)
        elif e["type"] == "supersedes" and e["from"] in node_ids:
            kept.append(e)                          # a superseded ADR may be archived; keep it
        else:
            dropped += 1
    nodes.sort(key=lambda nd: (nd["type"], nd["id"]))
    kept.sort(key=lambda e: (e["type"], e["from"], e["to"]))
    untyped.sort(key=lambda u: (u["source"]["file"], u["source"]["line"]))
    counts = {t: sum(1 for nd in nodes if nd["type"] == t) for t in IR_NODE_TYPES}
    stats = {"nodes": len(nodes), "edges": len(kept),
             "edges_dropped": dropped, "untyped": len(untyped),
             "by_type": {t: c for t, c in counts.items() if c},
             "untyped_rate": round(len(untyped) / (len(nodes) + len(untyped)), 4)
             if (nodes or untyped) else 0.0}
    graph = {"schema_version": IR_SCHEMA,
             "_generated_by": "qa_ledger.py ir-extract (ADR-015) -- derived index of the "
                              "canonical package; never hand-edit",
             "nodes": nodes, "edges": kept, "untyped": untyped, "stats": stats}
    # the seal covers stats too (fresh-review MEDIUM): a doctored summary that ir-render
    # would faithfully print must trip the strict loader, not slip past it -- the
    # derived-but-unsealed lesson, applied a third time (path @1.70, evidence_class @1.69).
    graph["_integrity"] = _ir_seal(graph)
    return graph


def _ir_seal(graph):
    return _integrity_hash({k: graph.get(k) for k in
                            ("schema_version", "nodes", "edges", "untyped", "stats")})


def _load_ir(repo_path):
    """Strict loader: an unknown schema_version or a broken graph is exit-2 class, never
    mis-read (AC-IR-05). Returns (graph, errors); graph None when absent."""
    path = os.path.join(repo_path, IR_DIR, IR_FILE)
    if not os.path.isfile(path):
        return None, []
    try:
        with open(path, encoding="utf-8-sig") as fh:
            g = json.load(fh)
    except (OSError, ValueError) as exc:
        return {}, ["unreadable: %s" % exc]
    errors = []
    if g.get("schema_version") != IR_SCHEMA:
        errors.append("schema_version %r != %r (a version this engine does not know is not "
                      "read, it is refused)" % (g.get("schema_version"), IR_SCHEMA))
        return g, errors
    if not isinstance(g.get("nodes"), list) or not isinstance(g.get("edges"), list):
        return g, ["nodes/edges missing or not lists"]
    if g.get("_integrity") != _ir_seal(g):
        errors.append("integrity seal does not match the graph -- nodes, edges, untyped or "
                      "stats was hand-edited (regenerate via ir-extract)")
    return g, errors


def _render_ir_md(graph):
    st = graph.get("stats") or {}
    lines = ["<!-- %s -->" % _IR_BANNER, "", "# Uscha IR v%s (rendered view)" % IR_SCHEMA, "",
             "%d nodes · %d edges · %d UNTYPED (rate %.2f)"
             % (st.get("nodes", 0), st.get("edges", 0), st.get("untyped", 0),
                st.get("untyped_rate", 0.0)), "",
             "## Nodes", "", "| id | type | statement | source |",
             "|----|------|-----------|--------|"]
    for nd in graph.get("nodes") or []:
        src = "%s:%s" % (nd["source"]["file"], nd["source"]["line"])
        stmt = (nd.get("statement") or "").replace("|", "\\|")
        lines.append("| %s | %s | %s | %s |" % (nd["id"], nd["type"], stmt, src))
    lines += ["", "## Edges", "", "| from | type | to |", "|------|------|----|"]
    for e in graph.get("edges") or []:
        lines.append("| %s | %s | %s |" % (e["from"], e["type"], e["to"]))
    if graph.get("untyped"):
        lines += ["", "## UNTYPED (conventions the human layer is missing)", "",
                  "| text | source | reason |", "|------|--------|--------|"]
        for u in graph["untyped"]:
            src = "%s:%s" % (u["source"]["file"], u["source"]["line"])
            txt = (u.get("text") or "").replace("|", "\\|")[:80]
            lines.append("| %s | %s | %s |" % (txt, src, u.get("reason", "")))
    lines.append("")
    return "\n".join(lines)


def cmd_ir_extract(args):
    ledger = _load(args.ledger)
    _repo_node(ledger, args.repo)
    repo_path = _scope_path(ledger, args.repo)
    graph = _extract_ir(repo_path, ledger)
    ir_dir = os.path.join(repo_path, IR_DIR)
    os.makedirs(ir_dir, exist_ok=True)
    with open(os.path.join(ir_dir, IR_FILE), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(graph, indent=2, ensure_ascii=False) + "\n")
    twin_path = os.path.join(ir_dir, IR_TWIN)
    twin = _render_ir_md(graph)
    prev = None
    if os.path.isfile(twin_path):
        try:
            with open(twin_path, encoding="utf-8-sig") as fh:
                prev = fh.read()
        except OSError:
            prev = None
    with open(twin_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(twin)
    if prev is not None and prev != twin:
        print("[qa_ledger] ir-extract: %s regenerated (rendered view, never a source)"
              % IR_TWIN, file=sys.stderr)
    st = graph["stats"]
    if args.json:
        print(json.dumps(st, indent=2, ensure_ascii=False))
    else:
        print("IR-EXTRACT %s: %d nodes, %d edges -> %s"
              % (args.repo, st["nodes"], st["edges"],
                 os.path.join(IR_DIR, IR_FILE)))
        print("  by type: " + ", ".join("%s=%d" % (t, c)
                                        for t, c in st["by_type"].items()))
        print("  UNTYPED: %d (rate %.2f) -- the size of what the conventions cannot yet type"
              % (st["untyped"], st["untyped_rate"]))
        if st["edges_dropped"]:
            print("  %d edge(s) dropped (endpoint not a node) -- counted, never dangling"
                  % st["edges_dropped"])
    sys.exit(0)


def cmd_ir_render(args):
    ledger = _load(args.ledger)
    _repo_node(ledger, args.repo)
    repo_path = _scope_path(ledger, args.repo)
    graph, errors = _load_ir(repo_path)
    if graph is None:
        print("[qa_ledger] ir-render: no %s -- run ir-extract first."
              % os.path.join(IR_DIR, IR_FILE), file=sys.stderr)
        sys.exit(2)
    if errors:
        for e in errors:
            print("[qa_ledger] ir-render: %s" % e, file=sys.stderr)
        sys.exit(2)
    twin = _render_ir_md(graph)
    with open(os.path.join(repo_path, IR_DIR, IR_TWIN), "w", encoding="utf-8",
              newline="\n") as fh:
        fh.write(twin)
    print("IR-RENDER %s: %s regenerated from the graph"
          % (args.repo, os.path.join(IR_DIR, IR_TWIN)))
    sys.exit(0)


# --------------------------------------------------------------------------- #
# compiler contract  (Diamond M3: the LLM is a compiler with a validated output
# contract. The engine VALIDATES and INGESTS compilations; it NEVER compiles and
# never calls a model. Only mechanical violations gate; every statistic is
# advisory (INV-ADVISORY-01). ADR-016.)
# --------------------------------------------------------------------------- #
COMPILE_SCHEMA = "compile/0.1"
COMPILE_REQUIRED = ("schema_version", "canonical_ir", "target_stack", "source",
                    "tests", "trace_manifest", "unresolved_intent",
                    "compilation_report")
# The seal covers the load-bearing contract, NOT compilation_report: model, versions and
# timestamps legitimately vary and never change WHAT was compiled. A hand edit of the
# substance (source/tests/manifest/unresolved_intent) after production must trip the seal.
COMPILE_SEALED = ("schema_version", "canonical_ir", "target_stack",
                  "implementation_constraints", "source", "tests",
                  "trace_manifest", "unresolved_intent")
# Advisory degeneracy dial: a manifest of >=2 units where EVERY unit claims >= this share
# of ALL IR nodes is "everything traces to everything" -- no unit discriminates. ADVISORY
# ONLY: printed, never gates. The exact value is a reporting choice, not a contract,
# precisely because it can never block (a threshold on a smell would be a judgment).
_COMPILE_DEGENERATE_FANOUT = 0.8


def _compile_seal(c):
    return _integrity_hash({k: c.get(k) for k in COMPILE_SEALED})


def _sha256_file(path):
    try:
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    except OSError:
        return None


def _contained_unit(base, unit):
    """A compilation's units must be RELATIVE paths CONTAINED within the compilation
    directory: the manifest references what was compiled, and what was compiled lives with
    the compilation. An absolute path or a `..` escape lets a manifest name any file on the
    filesystem as a "source" unit and pass on that file's hash -- exactly the "manifest
    cannot lie about what was compiled" guarantee, defeated. Returns the resolved path, or
    None if the unit is absolute or escapes `base`. Both sides are `realpath`-normalized
    before comparison -- the Windows 8.3 short-path trap this repo already paid for once
    (a file INSIDE a tree judged outside it) applies to any containment check."""
    if os.path.isabs(unit):
        return None
    full = os.path.realpath(os.path.join(base, unit.replace("/", os.sep)))
    root = os.path.realpath(base)
    if full == root or full.startswith(root + os.sep):
        return full
    return None


def _load_ir_at(path):
    """Strict IR loader for an ARBITRARY IR.json. The repo's own ir/ is gitignored (a
    regenerable index), so the M3 reference IR is a committed fixture loaded here with the
    same posture as _load_ir: an unknown schema or a broken/hand-edited seal is refused,
    never mis-read. Returns (graph, errors); graph None when the file is absent."""
    if not os.path.isfile(path):
        return None, ["no reference IR at %s" % path]
    try:
        with open(path, encoding="utf-8-sig") as fh:
            g = json.load(fh)
    except (OSError, ValueError) as exc:
        return {}, ["unreadable: %s" % exc]
    if g.get("schema_version") != IR_SCHEMA:
        return g, ["schema_version %r != %r (an IR version this engine does not know is "
                   "refused, not read)" % (g.get("schema_version"), IR_SCHEMA)]
    if not isinstance(g.get("nodes"), list) or not isinstance(g.get("edges"), list):
        return g, ["nodes/edges missing or not lists"]
    if g.get("_integrity") != _ir_seal(g):
        return g, ["reference IR integrity seal does not match -- it was hand-edited "
                   "(regenerate via ir-extract)"]
    return g, []


def _validate_compilation(comp_path, ir_graph):
    """The deterministic checker (ADR-016). Returns (blocking_errors, advisory).

    BLOCKS only on FACTS: unknown schema, a missing/mistyped section, a broken seal, an
    ir_hash that does not match the reference IR, a trace_manifest id that is not an IR
    node, a unit whose file is absent or whose hash does not match the bytes on disk, a
    malformed unresolved_intent entry. Every STATISTIC (fan-out degeneracy, empty/generic
    unresolved_intent, coverage) is advisory and can NEVER change the outcome -- a
    threshold on a smell is a judgment, and no judgment gates (INV-ADVISORY-01)."""
    errors, advisory = [], {}
    base = os.path.dirname(os.path.abspath(comp_path))
    try:
        with open(comp_path, encoding="utf-8-sig") as fh:
            c = json.load(fh)
    except (OSError, ValueError) as exc:
        return ["unreadable compilation: %s" % exc], advisory
    if c.get("schema_version") != COMPILE_SCHEMA:
        return ["schema_version %r != %r (a contract version this engine does not know is "
                "refused, not read)" % (c.get("schema_version"), COMPILE_SCHEMA)], advisory
    for k in COMPILE_REQUIRED:
        if k not in c:
            errors.append("required section missing: %s" % k)
    if errors:
        return errors, advisory
    for k, typ in (("source", list), ("tests", list), ("trace_manifest", list),
                   ("unresolved_intent", list), ("canonical_ir", dict),
                   ("compilation_report", dict)):
        if not isinstance(c.get(k), typ):
            errors.append("%s must be a %s" % (k, typ.__name__))
    if errors:
        return errors, advisory
    # ELEMENT shapes, checked before any `.get` on them: an adversarial/buggy compiler that
    # emits a list of strings (or a non-list `implements`) is a mechanical violation -> exit
    # 2 with a named fault, NEVER an AttributeError traceback (exit 1). This is the trust
    # boundary the contract exists to defend; the loops below assume dict elements.
    for k in ("source", "tests"):
        for i, u in enumerate(c.get(k)):
            if not isinstance(u, dict):
                errors.append("%s[%d] must be an object with unit/sha256" % (k, i))
    for i, e in enumerate(c.get("trace_manifest")):
        if not isinstance(e, dict):
            errors.append("trace_manifest[%d] must be an object with unit/implements" % i)
        elif not isinstance(e.get("implements"), list):
            errors.append("trace_manifest[%d].implements must be a list of IR node ids" % i)
    for i, ui in enumerate(c.get("unresolved_intent")):
        if not isinstance(ui, dict):
            errors.append("unresolved_intent[%d] must be an object with ir_region/decision"
                          % i)
    if errors:
        return errors, advisory
    if c.get("_integrity") != _compile_seal(c):
        errors.append("compilation integrity seal does not match -- source/tests/manifest/"
                      "unresolved_intent was hand-edited after production")
    # the compilation NAMES which IR it compiled; a stale or foreign ir_hash is refused --
    # a compilation cannot be measured against a graph this repo does not reproduce.
    ir_seal = ir_graph.get("_integrity")
    named = (c.get("canonical_ir") or {}).get("ir_hash")
    if named != ir_seal:
        errors.append("canonical_ir.ir_hash %s.. does not match the reference IR seal %s.. "
                      "-- a stale or foreign IR is refused, never assumed"
                      % (str(named)[:12], str(ir_seal)[:12]))
    node_ids = {nd["id"] for nd in ir_graph.get("nodes") or []}
    # units resolve on disk and their hashes match the bytes: the manifest cannot lie about
    # what was compiled.
    units = {}
    for section in ("source", "tests"):
        for u in c.get(section) or []:
            unit, want = u.get("unit"), u.get("sha256")
            if not unit:
                errors.append("%s entry without a unit path" % section)
                continue
            # source classification is sticky: a unit listed in BOTH source and tests stays
            # source, so the degeneracy detector (over source units) cannot be dodged by also
            # listing a source file under tests. Advisory-only, but the detector stays honest.
            if units.get(unit) != "source":
                units[unit] = section
            full = _contained_unit(base, unit)
            if full is None:
                errors.append("%s unit escapes the compilation directory -- a relative, "
                              "contained path is required (the manifest references what was "
                              "compiled): %s" % (section, unit))
                continue
            got = _sha256_file(full)
            if got is None:
                errors.append("%s unit missing on disk: %s" % (section, unit))
            elif got != want:
                errors.append("%s unit hash mismatch (manifest lies about the bytes): %s"
                              % (section, unit))
    # every manifest id is an IR node (THE named mechanical violation); every manifest unit
    # is a real source/test unit.
    for entry in c.get("trace_manifest") or []:
        unit = entry.get("unit")
        if unit not in units:
            errors.append("trace_manifest unit is not a declared source/test unit: %s" % unit)
        for nid in entry.get("implements") or []:
            if nid not in node_ids:
                errors.append("trace_manifest implements an id that is not an IR node: %s"
                              % nid)
    # unresolved_intent SHAPE blocks; its richness (count, specificity) is advisory only.
    for ui in c.get("unresolved_intent") or []:
        if not ui.get("ir_region") or not ui.get("decision"):
            errors.append("unresolved_intent entry missing ir_region or decision")
    # ---- ADVISORY (computed always, gates never) ----
    manifest_units = {e.get("unit") for e in c.get("trace_manifest") or []}
    per_unit = [len(e.get("implements") or []) for e in c.get("trace_manifest") or []]
    total_nodes = len(node_ids) or 1
    mean_fanout = (sum(per_unit) / len(per_unit)) if per_unit else 0.0
    covered = {nid for e in c.get("trace_manifest") or []
               for nid in (e.get("implements") or []) if nid in node_ids}
    # Degeneracy is a property of the SOURCE units: >=2 source units that EACH claim >= the
    # threshold share of all nodes -> the manifest cannot tell you which code implements
    # which intent (everything traces to everything). Min-based, not mean-based, and over
    # source only: one comprehensive source file legitimately implements a whole tiny
    # package, and tests naturally exercise everything, so neither is a degeneracy signal.
    source_units = {u for u, s in units.items() if s == "source"}
    src_fanout = [len(e.get("implements") or []) for e in c.get("trace_manifest") or []
                  if e.get("unit") in source_units]
    advisory = {
        "trace_units": len(manifest_units),
        "mean_nodes_per_unit": round(mean_fanout, 3),
        "node_coverage": round(len(covered) / total_nodes, 3),
        "unexplained_units": sorted(u for u in units if u not in manifest_units),
        "unresolved_intent_count": len(c.get("unresolved_intent") or []),
        "degenerate": len(src_fanout) >= 2 and all(
            (pu / total_nodes) >= _COMPILE_DEGENERATE_FANOUT for pu in src_fanout),
        "empty_unresolved": len(c.get("unresolved_intent") or []) == 0,
    }
    return errors, advisory


def _print_compile_advisory(advisory):
    if not advisory:
        return
    print("  advisory (never gates): coverage %.2f, mean %.2f nodes/unit, %d unresolved_intent%s"
          % (advisory.get("node_coverage", 0.0), advisory.get("mean_nodes_per_unit", 0.0),
             advisory.get("unresolved_intent_count", 0),
             ", DEGENERATE manifest" if advisory.get("degenerate") else ""))
    if advisory.get("empty_unresolved"):
        print("  advisory: unresolved_intent is EMPTY -- suspicious (a compiler that made no "
              "choices is rare); reported, never blocked")
    for u in advisory.get("unexplained_units") or []:
        print("  advisory: %s has no trace_manifest entry -- unexplained by construction" % u)


def cmd_compile_validate(args):
    ir_graph, ir_errors = _load_ir_at(args.ir)
    if ir_graph is None or ir_errors:
        for e in ir_errors:
            print("[qa_ledger] compile-validate: reference IR: %s" % e, file=sys.stderr)
        sys.exit(2)
    errors, advisory = _validate_compilation(args.compilation, ir_graph)
    if args.json:
        print(json.dumps({"compilation": args.compilation, "ir": args.ir,
                          "valid": not errors, "errors": errors, "advisory": advisory},
                         indent=2, ensure_ascii=False))
    elif errors:
        # diagnostics to stderr (Unix convention, and consistent with compile-ingest); the
        # machine signal is the exit code. stdout stays clean for the VALID payload path.
        print("COMPILE-VALIDATE %s: REFUSED (%d mechanical violation(s))"
              % (args.compilation, len(errors)), file=sys.stderr)
        for e in errors:
            print("  x %s" % e, file=sys.stderr)
    else:
        print("COMPILE-VALIDATE %s: VALID (contract conformant)" % args.compilation)
        _print_compile_advisory(advisory)
    sys.exit(2 if errors else 0)


def cmd_compile_ingest(args):
    """Record a VALIDATED compilation into the ledger (ADR-016). Ingesting an invalid
    compilation is a refusal. unresolved_intent becomes append-only, content-addressed
    UINT objects + an ISSUES-DEFERRED.md mirror (the house convention `fix` uses); the
    by-construction unexplained_code is the set of units with no trace_manifest entry."""
    ledger = _load(args.ledger)
    _repo_node(ledger, args.repo)
    repo_path = _scope_path(ledger, args.repo)
    ir_graph, ir_errors = _load_ir_at(args.ir)
    if ir_graph is None or ir_errors:
        for e in ir_errors:
            print("[qa_ledger] compile-ingest: reference IR: %s" % e, file=sys.stderr)
        sys.exit(2)
    errors, advisory = _validate_compilation(args.compilation, ir_graph)
    if errors:
        print("[qa_ledger] compile-ingest: REFUSED -- ingesting an invalid compilation is a "
              "refusal (%d mechanical violation(s)); run compile-validate." % len(errors),
              file=sys.stderr)
        for e in errors:
            print("  x %s" % e, file=sys.stderr)
        sys.exit(2)
    with open(args.compilation, encoding="utf-8-sig") as fh:
        c = json.load(fh)
    comp_seal = c.get("_integrity")
    uints, seen_uint = [], set()
    for ui in c.get("unresolved_intent") or []:
        uid = "UINT-" + hashlib.sha256(
            (ui.get("ir_region", "") + "\n" + ui.get("decision", "")).encode("utf-8")
        ).hexdigest()[:12]
        # content-addressed: two entries that resolve to the same id ARE the same intent gap
        # (same ir_region + decision), deduped within this ingest just as across ingests --
        # otherwise ISSUES-DEFERRED and the ledger record carry the id twice.
        if uid in seen_uint:
            continue
        seen_uint.add(uid)
        uints.append({"id": uid, "ir_region": ui.get("ir_region"),
                      "decision": ui.get("decision"), "rationale": ui.get("rationale", "")})
    comp_rec = {"id": comp_seal[:12], "repo": args.repo,
                "ir_hash": (c.get("canonical_ir") or {}).get("ir_hash"),
                "model": (c.get("compilation_report") or {}).get("model"),
                "target_stack": c.get("target_stack"), "seal": comp_seal,
                "unexplained_units": advisory.get("unexplained_units") or [],
                "node_coverage": advisory.get("node_coverage"),
                "unresolved_intent": uints, "at": _now()}
    comps = ledger.setdefault("compilations", [])
    # re-ingest is idempotent PER REPO: the seal is the identity within a repo, and a
    # byte-identical compilation has nothing to supersede. The compilations list is flat and
    # cross-repo, so the supersede check MUST be scoped by repo -- otherwise two repos that
    # legitimately produce the same compilation (a shared/small canonical package -- exactly
    # this milestone's own fixtures) collide, and the second repo's first ingest is dropped
    # as a false "superseded". A CHANGED compilation reseals -> a new record. Never a dup.
    superseded = any(x.get("seal") == comp_seal and x.get("repo") == args.repo for x in comps)
    if not superseded:
        comps.append(comp_rec)
        _save(args.ledger, ledger)
    new_items = []
    if uints:
        dpath = os.path.join(repo_path, ISSUES_DEFERRED_FILE)
        existing = ""
        if os.path.isfile(dpath):
            with open(dpath, encoding="utf-8-sig", errors="replace") as fh:
                existing = fh.read()
        add = [u for u in uints if u["id"] not in existing]
        if add:
            with open(dpath, "a", encoding="utf-8", newline="\n") as fh:
                if existing and not existing.endswith("\n"):
                    fh.write("\n")
                for u in add:
                    fh.write("- [ ] %s (unresolved_intent): %s -- the compiler decided "
                             "'%s' on its own; a candidate canonical improvement (ADR-016)\n"
                             % (u["id"], u["ir_region"], u["decision"]))
            new_items = [u["id"] for u in add]
    out = {"repo": args.repo, "compilation": comp_rec["id"], "superseded": superseded,
           "unresolved_intent": [u["id"] for u in uints],
           "issues_deferred_new": new_items,
           "unexplained_units": comp_rec["unexplained_units"]}
    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print("COMPILE-INGEST %s: compilation %s%s"
              % (args.repo, comp_rec["id"],
                 " (byte-identical to a prior ingest -- nothing superseded)"
                 if superseded else ""))
        print("  %d unresolved_intent -> %d new %s item(s); %d unexplained unit(s)"
              % (len(uints), len(new_items), ISSUES_DEFERRED_FILE,
                 len(comp_rec["unexplained_units"])))
    sys.exit(0)


# --------------------------------------------------------------------------- #
# bootstrap  (Diamond M4: a bounded subsystem's identity is carried by its
# canonical package + a WITHHELD oracle, not by its implementation. The oracle
# runner is a measured fact and decides "same system"; variance is advisory
# evidence that the implementations genuinely differ. ADR-017.)
# --------------------------------------------------------------------------- #
_BOOTSTRAP_CASE_TIMEOUT = 15                        # a compiled hook must decide fast


def _run_oracle_case(impl_path, case):
    """Run ONE withheld oracle case against a compiled implementation: feed the case's stdin
    (raw_stdin verbatim if present, else json.dumps(payload)) to `python <impl>`, and check its
    result against whichever expectations the case declares. Deterministic execution -- the
    oracle is a `measured` fact, never an LLM judgment. Returns a per-case result dict.

    A case may assert any of: `expected_exit` (process exit code -- the M4 guard's contract),
    `expected_stdout` (the program's stdout, compared stripped -- for archetypes that COMPUTE an
    output, e.g. a parser or transformer), and `expected_json` (stdout parsed as JSON and
    compared structurally, so an output whose formatting is free but whose value is fixed is not
    penalised for whitespace or key order). The case passes iff EVERY declared expectation holds;
    a case that declares none proves nothing and fails."""
    if "raw_stdin" in case:
        stdin = case["raw_stdin"]
    else:
        stdin = json.dumps(case.get("payload"))
    try:
        r = subprocess.run([sys.executable, impl_path], input=stdin, capture_output=True,
                           text=True, encoding="utf-8", errors="replace",
                           timeout=_BOOTSTRAP_CASE_TIMEOUT)
        got, out, err = r.returncode, r.stdout, None
    except subprocess.TimeoutExpired:
        got, out, err = None, "", "timeout"
    except OSError as exc:
        got, out, err = None, "", "could not run impl: %s" % exc
    want = case.get("expected_exit")
    asserted = [k for k in ("expected_exit", "expected_stdout", "expected_json") if k in case]
    ok = err is None and bool(asserted)
    if ok and "expected_exit" in case:
        ok = got == want
    if ok and "expected_stdout" in case:
        ok = (out or "").strip() == str(case["expected_stdout"]).strip()
    if ok and "expected_json" in case:
        try:
            ok = json.loads(out) == case["expected_json"]
        except (ValueError, TypeError):
            ok = False
    return {"name": case.get("name"), "expected": want, "got": got, "ok": ok, "error": err}


def cmd_bootstrap_oracle(args):
    """Run a WITHHELD oracle suite (ADR-017) against a compiled implementation. The oracle
    predates and is physically separate from every compiler input; this runner is the
    maker!=checker wall made executable. Exit 0 iff every case matches its expected exit,
    else 1 -- a measured behavioural fact about whether this implementation is the same
    system. It runs the implementation as a subprocess and consults no model."""
    try:
        with open(args.oracle, encoding="utf-8-sig") as fh:
            oracle = json.load(fh)
    except (OSError, ValueError) as exc:
        print("[qa_ledger] bootstrap-oracle: unreadable oracle %s: %s" % (args.oracle, exc),
              file=sys.stderr)
        sys.exit(2)
    cases = oracle.get("cases")
    if not isinstance(cases, list) or not cases:
        print("[qa_ledger] bootstrap-oracle: oracle has no cases", file=sys.stderr)
        sys.exit(2)
    if not os.path.isfile(args.impl):
        print("[qa_ledger] bootstrap-oracle: no implementation at %s" % args.impl,
              file=sys.stderr)
        sys.exit(2)
    results = [_run_oracle_case(args.impl, c) for c in cases]
    passed = sum(1 for r in results if r["ok"])
    failed = [r for r in results if not r["ok"]]
    report = {"impl": args.impl, "oracle": args.oracle, "total": len(results),
              "passed": passed, "failed": len(failed),
              "oracle_green": not failed, "results": results}
    if args.ledger and args.repo:
        ledger = _load(args.ledger)
        _repo_node(ledger, args.repo)
        rec = {"impl": os.path.basename(args.impl), "oracle": os.path.basename(args.oracle),
               "total": len(results), "passed": passed, "failed": len(failed),
               "oracle_green": not failed,
               "failing": [r["name"] for r in failed], "at": _now()}
        ledger.setdefault("bootstrap_oracle", []).append(rec)
        _save(args.ledger, ledger)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print("BOOTSTRAP-ORACLE %s: %d/%d cases pass -- %s"
              % (os.path.basename(args.impl), passed, len(results),
                 "ORACLE GREEN (same system on this suite)" if not failed
                 else "ORACLE RED (%d divergence(s))" % len(failed)))
        for r in failed:
            print("  x %s: expected exit %s, got %s%s"
                  % (r["name"], r["expected"], r["got"],
                     " (%s)" % r["error"] if r["error"] else ""))
    sys.exit(0 if not failed else 1)


def _impl_metrics(path):
    """Structural fingerprint of one implementation: physical LOC, AST node count, function
    and class counts, and the set of imported top-level modules. Deterministic; no judgment."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            src = fh.read()
    except OSError as exc:
        return {"path": path, "error": "unreadable: %s" % exc}
    loc = sum(1 for ln in src.splitlines() if ln.strip())
    try:
        tree = ast.parse(src)
    except SyntaxError as exc:
        return {"path": path, "loc": loc, "error": "unparseable: %s" % exc}
    funcs = classes = nodes = 0
    imports = set()
    for nd in ast.walk(tree):
        nodes += 1
        if isinstance(nd, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs += 1
        elif isinstance(nd, ast.ClassDef):
            classes += 1
        elif isinstance(nd, ast.Import):
            for a in nd.names:
                imports.add(a.name.split(".")[0])
        elif isinstance(nd, ast.ImportFrom):
            if nd.module:
                imports.add(nd.module.split(".")[0])
    return {"path": path, "loc": loc, "ast_nodes": nodes, "functions": funcs,
            "classes": classes, "imports": sorted(imports),
            "sha256": hashlib.sha256(src.encode("utf-8")).hexdigest()}


def cmd_bootstrap_variance(args):
    """Prove independent compilations of the same canonical package genuinely DIFFER (ADR-017).
    Reports per-implementation structural metrics and pairwise divergence. ADVISORY: variance
    is evidence the implementations differ, never a certificate of 'same system' (only the
    oracle certifies that) and never a gate -- it cannot change an exit code."""
    metrics = [_impl_metrics(p) for p in args.impls]
    pairs = []
    good = [m for m in metrics if "error" not in m]
    for i in range(len(good)):
        for j in range(i + 1, len(good)):
            a, b = good[i], good[j]
            ia, ib = set(a["imports"]), set(b["imports"])
            jac = (len(ia & ib) / len(ia | ib)) if (ia or ib) else 1.0
            pairs.append({"a": os.path.basename(a["path"]), "b": os.path.basename(b["path"]),
                          "byte_identical": a["sha256"] == b["sha256"],
                          "loc_delta": abs(a["loc"] - b["loc"]),
                          "ast_node_delta": abs(a["ast_nodes"] - b["ast_nodes"]),
                          "function_delta": abs(a["functions"] - b["functions"]),
                          "import_jaccard": round(jac, 3)})
    all_distinct = all(not p["byte_identical"] for p in pairs) if pairs else None
    report = {"implementations": metrics, "pairs": pairs, "all_distinct": all_distinct,
              "advisory": True}
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        for m in metrics:
            if "error" in m:
                print("VARIANCE %s: %s" % (os.path.basename(m["path"]), m["error"]))
            else:
                print("VARIANCE %s: %d loc, %d ast-nodes, %d fn, %d cls, imports=%s"
                      % (os.path.basename(m["path"]), m["loc"], m["ast_nodes"],
                         m["functions"], m["classes"], ",".join(m["imports"]) or "-"))
        for p in pairs:
            print("  %s vs %s: %s | dloc=%d dnodes=%d import_jaccard=%.2f"
                  % (p["a"], p["b"], "IDENTICAL" if p["byte_identical"] else "distinct",
                     p["loc_delta"], p["ast_node_delta"], p["import_jaccard"]))
        if all_distinct is not None:
            print("  all implementations distinct: %s (advisory, never gates)"
                  % ("yes" if all_distinct else "NO -- convergence, a weak result"))
    sys.exit(0)


# --------------------------------------------------------------------------- #
# bench  (Diamond M5: the Diamond Bench aggregates the M3/M4 primitives over a
# set of bounded systems and emits a per-archetype verdict table. It measures
# REGENERATION FIDELITY of canonical representations, not "which model codes
# better" -- model identities are anonymized in the headline. Deterministic, no
# LLM. ADR-018.)
# --------------------------------------------------------------------------- #
# min oracle pass-rate for a non-green compilation to still count as PARTIAL (core identity).
_BENCH_PARTIAL_FLOOR = 0.8


def _bench_oracle_all(impl_path, cases):
    results = [_run_oracle_case(impl_path, c) for c in cases]
    passed = sum(1 for r in results if r["ok"])
    return {"passed": passed, "total": len(results), "green": passed == len(results),
            "failing": [r["name"] for r in results if not r["ok"]]}


def _bench_entry(entry_dir, name):
    """Run compile-validate + the withheld oracle + variance over ONE bench entry and compute
    its verdict. Reuses the M3/M4 organs unchanged; consults no model. A PASS is >=3 oracle-green
    compilations that genuinely differ; PARTIAL is core identity with the divergence isolated;
    FAIL is no green, convergence to near-identical code, or an oracle a degenerate stub can
    satisfy (non-discriminating); PENDING is an entry not yet fully compiled."""
    ir_graph, ir_errors = _load_ir_at(os.path.join(entry_dir, IR_FILE))
    try:
        with open(os.path.join(entry_dir, "oracle", "ORACLE.json"), encoding="utf-8-sig") as fh:
            cases = (json.load(fh) or {}).get("cases") or []
    except (OSError, ValueError):
        cases = []
    rec = {"archetype": name, "oracle_cases": len(cases), "compilations": [],
           "variance": None, "discrimination": None, "verdict": "PENDING", "reason": None}
    if ir_graph is None or ir_errors or not cases:
        rec["reason"] = "entry incomplete (missing/invalid IR or oracle)"
        return rec
    comp_dirs = sorted(d for d in os.listdir(entry_dir)
                       if d.startswith("c-") and
                       os.path.isfile(os.path.join(entry_dir, d, "COMPILATION.json")))
    for d in comp_dirs:
        cd = os.path.join(entry_dir, d)
        cj = os.path.join(cd, "COMPILATION.json")
        errors, _adv = _validate_compilation(cj, ir_graph)
        unit, model = None, None
        try:
            with open(cj, encoding="utf-8-sig") as fh:
                c = json.load(fh)
            src = c.get("source") or []
            unit = src[0].get("unit") if src else None
            model = (c.get("compilation_report") or {}).get("model")
        except (OSError, ValueError, AttributeError, IndexError):
            pass
        impl = os.path.join(cd, unit.replace("/", os.sep)) if unit else None
        ores = (_bench_oracle_all(impl, cases) if impl and os.path.isfile(impl)
                else {"passed": 0, "total": len(cases), "green": False, "failing": ["<no impl>"]})
        rec["compilations"].append({"dir": d, "model": model, "impl": impl,
                                    "compile_valid": not errors, "oracle": ores})
    impls = rec["compilations"]
    impl_paths = [i["impl"] for i in impls if i["impl"] and os.path.isfile(i["impl"])]
    if len(impl_paths) >= 2:
        metrics = [_impl_metrics(p) for p in impl_paths]
        shas = [m.get("sha256") for m in metrics if "error" not in m and m.get("sha256")]
        rec["variance"] = {"all_distinct": len(set(shas)) == len(shas) and len(shas) >= 2,
                           "metrics": metrics}
    stub_dir = os.path.join(entry_dir, "stub")
    stub_green = False
    if os.path.isdir(stub_dir):
        stubs = sorted(f for f in os.listdir(stub_dir) if f.endswith(".py"))
        if stubs:
            sres = _bench_oracle_all(os.path.join(stub_dir, stubs[0]), cases)
            stub_green = sres["green"]
            rec["discrimination"] = {"stub_passed": sres["passed"], "total": sres["total"],
                                     "stub_green": stub_green}
    n = len(impls)
    if n == 0:
        rec["reason"] = "no compilations yet"
        return rec                                  # PENDING
    all_valid = all(i["compile_valid"] for i in impls)
    greens = sum(1 for i in impls if i["oracle"]["green"])
    min_rate = min((i["oracle"]["passed"] / i["oracle"]["total"]) if i["oracle"]["total"]
                   else 0.0 for i in impls)
    # distinct is None when variance could not be computed (fewer than 2 resolvable impl files),
    # which is NOT the same as a byte-identical convergence -- keep the two reasons apart.
    distinct = rec["variance"]["all_distinct"] if rec["variance"] else None
    if stub_green:
        rec["verdict"], rec["reason"] = "FAIL", ("oracle satisfied by a degenerate stub -- not "
                                                 "discriminating; the entry proves nothing")
    elif not all_valid:
        rec["verdict"], rec["reason"] = "FAIL", "a compilation does not validate against the pinned IR"
    elif n < 3:
        rec["verdict"], rec["reason"] = "PENDING", "fewer than 3 compilations (have %d)" % n
    elif distinct is None:
        rec["verdict"], rec["reason"] = "FAIL", ("cannot assess distinctness -- fewer than 2 "
                                                 "resolvable implementation files on disk")
    elif not distinct:
        rec["verdict"], rec["reason"] = "FAIL", ("implementations converged to a byte-identical "
                                                 "pair -- a disguised implementation")
    elif greens == n:
        rec["verdict"], rec["reason"] = "PASS", ("all %d compilations oracle-green and genuinely "
                                                 "different -- the same system" % n)
    elif min_rate >= _BENCH_PARTIAL_FLOOR:
        rec["verdict"], rec["reason"] = "PARTIAL", ("core identity (min %.0f%% of cases); "
                                                    "divergence isolated" % (min_rate * 100))
    else:
        rec["verdict"], rec["reason"] = "FAIL", ("a compilation below the core-identity floor "
                                                 "(min %.0f%%)" % (min_rate * 100))
    return rec


def _render_bench_md(table, anon, recs):
    lines = ["<!-- GENERATED by qa_ledger.py bench (ADR-018) -- every number is a measured run; "
             "do not hand-edit. -->", "", "# DIAMOND-BENCH", "",
             "Regeneration fidelity of canonical representations across archetypes. Each row is a "
             "bounded system compiled blind by independent models through the M3 contract and "
             "judged by a WITHHELD oracle (M4). Model identities are anonymized here; the mapping "
             "is published below.", "",
             "| Archetype | Verdict | Compilers (oracle pass / total) | Distinct | Oracle cases |",
             "|-----------|---------|--------------------------------|----------|--------------|"]
    for t in table:
        dist = "—" if t["distinct"] is None else ("yes" if t["distinct"] else "NO")
        lines.append("| %s | %s | %s | %s | %d |" % (t["archetype"], t["verdict"],
                     t["compilers"], dist, t["oracle_cases"]))
    counts = {}
    for t in table:
        counts[t["verdict"]] = counts.get(t["verdict"], 0) + 1
    lines += ["", "**Coverage:** " + ", ".join("%d %s" % (v, k) for k, v in sorted(counts.items()))
              + " (of %d entries)." % len(table), "",
              "**Model map (published, not the headline):** "
              + (", ".join("%s = %s" % (a, m) for m, a in sorted(anon.items(), key=lambda x: x[1]))
                 or "none yet") + ".", "",
              "## Per-entry detail", ""]
    for r in recs:
        lines.append("### %s — %s" % (r["archetype"], r["verdict"]))
        lines.append("*%s*" % (r["reason"] or ""))
        if r["compilations"]:
            for i in r["compilations"]:
                lines.append("- `%s` (%s): oracle %d/%d%s%s" % (
                    i["dir"], anon.get(i["model"], i["model"] or "?"),
                    i["oracle"]["passed"], i["oracle"]["total"],
                    " GREEN" if i["oracle"]["green"] else "",
                    "" if i["compile_valid"] else " [does not compile-validate]"))
        if r["discrimination"]:
            dsc = r["discrimination"]
            lines.append("- discrimination stub: %d/%d (%s)" % (
                dsc["stub_passed"], dsc["total"],
                "NON-DISCRIMINATING" if dsc["stub_green"] else "oracle rejects the stub"))
        lines.append("")
    return "\n".join(lines)


def cmd_bench(args):
    if not os.path.isdir(args.dir):
        print("[qa_ledger] bench: no directory %s" % args.dir, file=sys.stderr)
        sys.exit(2)
    entries = sorted(d for d in os.listdir(args.dir)
                     if os.path.isfile(os.path.join(args.dir, d, IR_FILE)))
    if not entries:
        print("[qa_ledger] bench: no entries under %s (an entry is a subdir with %s)"
              % (args.dir, IR_FILE), file=sys.stderr)
        sys.exit(2)
    recs = [_bench_entry(os.path.join(args.dir, e), e) for e in entries]
    models = sorted({i["model"] for r in recs for i in r["compilations"] if i.get("model")})
    anon = {m: "M%d" % (k + 1) for k, m in enumerate(models)}
    table = []
    for r in recs:
        cols = ", ".join("%s %d/%d" % (anon.get(i["model"], "?"), i["oracle"]["passed"],
                                       i["oracle"]["total"]) for i in r["compilations"])
        table.append({"archetype": r["archetype"], "verdict": r["verdict"],
                      "compilers": cols or "(none yet)",
                      "distinct": (r["variance"] or {}).get("all_distinct"),
                      "oracle_cases": r["oracle_cases"], "reason": r["reason"]})
    md = _render_bench_md(table, anon, recs)
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(md)
    if args.json:
        print(json.dumps({"entries": len(recs), "model_map": anon, "table": table,
                          "raw": recs}, indent=2, ensure_ascii=False))
    else:
        print("BENCH: %d entries" % len(recs))
        for t in table:
            dist = "" if t["distinct"] is None else (" | distinct" if t["distinct"]
                                                     else " | CONVERGED")
            print("  %-14s %-8s | %s%s" % (t["archetype"], t["verdict"], t["compilers"], dist))
        if args.out:
            print("  -> %s" % args.out)
    sys.exit(0)


# --------------------------------------------------------------------------- #
# facts  (T0 / SYSTEM-FACTS: public claims become compiled artifacts of repo
# facts -- Diamond applied to Diamond. ADR-012.)
# --------------------------------------------------------------------------- #

FACTS_FILE = "SYSTEM-FACTS.json"


def _derive_facts():
    """Facts derived from the ARTIFACTS themselves, never from prose and never from greps
    over documentation: the subcommand list comes from introspecting the REAL parser, the
    skill list from the REAL kit tree, the version from the kit VERSION file. No timestamp
    on purpose: regeneration over an unchanged repo must be byte-identical (AC-SF-01)."""
    here = os.path.abspath(__file__)
    # kit root by MARKER, not by fixed depth: the canonical engine sits 4 levels deep
    # (.claude/skills/uscha-devloop/) and the Codex twin 3 (skills/uscha-devloop/). A fixed
    # dirname walk made the twin silently derive the OUTER repo root -- version None,
    # 0 skills, no error (fresh-review HIGH, reproduced by running both copies).
    kit, cur = None, os.path.dirname(here)
    for _ in range(6):
        if os.path.isfile(os.path.join(cur, "VERSION")):
            kit = cur
            break
        nxt = os.path.dirname(cur)
        if nxt == cur:
            break
        cur = nxt
    if kit is None:
        print("[qa_ledger] facts: no VERSION file found walking up from the engine -- "
              "facts that cannot locate their own kit are not facts.", file=sys.stderr)
        sys.exit(2)
    with open(os.path.join(kit, "VERSION"), encoding="utf-8") as fh:
        version = fh.read().split()[-1].strip()
    subs = []
    for action in build_parser()._subparsers._group_actions:
        subs = sorted(action.choices.keys())
    skills = []
    for sdir in (os.path.join(kit, ".claude", "skills"), os.path.join(kit, "skills")):
        # canonical tree first; the Codex install ships only skills/ -- same inventory
        if os.path.isdir(sdir):
            skills = sorted(d for d in os.listdir(sdir)
                            if os.path.isfile(os.path.join(sdir, d, "SKILL.md")))
            break
    return {
        "version": version,
        "subcommands": {"count": len(subs), "list": subs},
        "skills": {"count": len(skills), "list": skills},
        "_derivation": {
            "version": "uscha-kit/VERSION",
            "subcommands": "argparse introspection of build_parser()",
            "skills": "SKILL.md inventory under uscha-kit/.claude/skills/",
            "omitted": "stack matrix and REAL/VISION registry: no mechanical "
                       "source exists yet -- omitted, not guessed (ADR-012)",
        },
    }


_CLAIM_PATTERNS = (
    # (fact key path, regex over one line, needs-context substring or None)
    ("version", r"v(\d+\.\d+\.\d+)", "kit"),
    ("version", r"uscha-kit\s+v?(\d+\.\d+\.\d+)", None),
    ("subcommands.count", r"(\d+)\s+sub-?comm?ands", None),
    ("subcommands.count", r"(\d+)\s+subcomandos", None),
    ("skills.count", r"(\d+)\s+skills", None),
)


def _fact_value(facts, dotted):
    cur = facts
    for part in dotted.split("."):
        cur = cur[part]
    return str(cur)


def cmd_facts(args):
    """Generate SYSTEM-FACTS.json, or --check published claims against the derived facts.

    The founding fixture (recorded in ADR-012): the site claimed kit 1.65.0 with 32 engine
    subcommands while the repo was at 1.67.0 with 35 -- factual drift, live, in the project
    about factual drift. A claim that CI does not compare against a derived fact will
    drift; this makes the comparison mechanical and the drift a named red."""
    facts = _derive_facts()
    if args.check:
        problems = []
        # 1) the committed facts file must match a fresh derivation (stale facts are drift)
        if os.path.isfile(args.out):
            with open(args.out, encoding="utf-8") as fh:
                committed = fh.read()
            fresh = json.dumps(facts, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
            if committed.replace("\r\n", "\n") != fresh:
                problems.append((args.out, 0, "committed facts file",
                                 "stale vs regenerated", "run: qa_ledger.py facts"))
        else:
            problems.append((args.out, 0, "facts file", "absent",
                             "run: qa_ledger.py facts"))
        # 2) every recognizable claim in the given files must equal the derived fact
        for path in args.check:
            try:
                with open(path, encoding="utf-8", errors="replace") as fh:
                    lines = fh.read().splitlines()
            except OSError as exc:
                problems.append((path, 0, "file", "unreadable: %s" % exc, ""))
                continue
            for n, line in enumerate(lines, 1):
                # an HTML comment is not a published claim -- the first live run flagged a
                # section marker (a comment reading "2 Skills") as a drifted count
                line = re.sub(r"<!--.*?-->", "", line)
                low = line.lower()
                for key, pat, ctx in _CLAIM_PATTERNS:
                    if ctx and ctx not in low:
                        continue
                    for m in re.finditer(pat, line, re.I):
                        claimed = m.group(1)
                        actual = _fact_value(facts, key)
                        if claimed != actual:
                            problems.append((path, n, key, claimed, actual))
        if problems:
            print("FACTUAL DRIFT: %d claim(s) disagree with the derived facts"
                  % len(problems))
            for path, n, key, claimed, actual in problems:
                loc = "%s:%d" % (path, n) if n else path
                print("  !! %s: %s claims %r, the artifact says %r"
                      % (loc, key, claimed, actual))
            sys.exit(1)
        print("FACTS: %d file(s) checked, every claim matches the derived facts"
              % len(args.check))
        sys.exit(0)
    body = json.dumps(facts, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(body)
    print("FACTS -> %s: version %s · %d subcommands · %d skills"
          % (args.out, facts["version"], facts["subcommands"]["count"],
             facts["skills"]["count"]))



def cmd_escalate(args):
    ledger = _load(args.ledger)
    _repo_node(ledger, args.repo)
    ledger["step_counter"] += 1
    ledger["escalations"].append({"n": ledger["step_counter"], "at": _now(),
                                  "repo": args.repo, "reason": args.reason})
    ledger["steps"].append({"n": ledger["step_counter"], "at": _now(),
                            "kind": "escalation", "repo": args.repo})
    _save(args.ledger, ledger)
    print(f"[qa_ledger] ESCALATION logged for {args.repo}: {args.reason} "
          f"(caps readiness <=escalation until resolve-escalation)")


def cmd_resolve_escalation(args):
    """Close open escalations for a repo. Closing the human gate is a RECORDED
    event (resolved_at), not an implication — the readiness cap holds until then."""
    ledger = _load(args.ledger)
    open_esc = [e for e in ledger.get("escalations", [])
                if e.get("repo") == args.repo and not e.get("resolved_at")]
    if not open_esc:
        print(f"[qa_ledger] {args.repo}: no open escalations to resolve.")
        return
    for e in open_esc:
        e["resolved_at"] = _now()
        if args.note:
            e["resolution_note"] = args.note
    ledger["step_counter"] += 1
    ledger["steps"].append({"n": ledger["step_counter"], "at": _now(),
                            "kind": "escalation-resolved", "repo": args.repo})
    _save(args.ledger, ledger)
    print(f"[qa_ledger] {args.repo}: {len(open_esc)} escalation(s) resolved — "
          f"readiness cap lifted.")


def _tool_rollup(ledger):
    tools = {}
    scopes = list(ledger["repos"].items()) + [("integration", ledger["integration"])]
    for _name, node in scopes:
        for s in node["iterations"]:
            t = s["tool"]
            agg = tools.setdefault(t, {"reported": 0, "gated_reported": 0,
                                       "fixed": 0, "deferred": 0,
                                       "suppressed": 0, "passes": 0})
            agg["reported"] += s.get("reported") or 0
            agg["gated_reported"] += s.get("gated_reported") or 0
            agg["fixed"] += s.get("fixed") or 0
            agg["deferred"] += s.get("deferred") or 0
            agg["suppressed"] += s.get("suppressed") or 0
            agg["passes"] += 1
    for t, a in tools.items():
        a["fixed_pct"] = round(a["fixed"] / a["reported"] * 100, 1) if a["reported"] else None
    return tools


def _fty(ledger):
    """First-Time Yield (Lean, kit 1.27.0): fraction of repos that cleared QA on the
    FIRST cycle — no second pass, no new regressions, no escalation (resolved or not:
    a human intervention means it did NOT pass first-time). PASSIVE: derived from ledger
    facts already recorded, adds zero human step. Informational (retrospective) — never
    a gate, never a readiness dimension (it measures process, not the result's state)."""
    escalated = {e.get("repo") for e in ledger.get("escalations", [])}
    total, first_pass, detail = 0, 0, []
    for name, node in ledger["repos"].items():
        its = node.get("iterations", [])
        if not its:
            continue  # never entered QA — not part of the yield base
        total += 1
        max_cycle = _repo_loop_count(node)
        regr = sum((s.get("new_regressions") or 0) for s in its)
        yielded = (max_cycle <= 1 and regr == 0 and name not in escalated)
        first_pass += 1 if yielded else 0
        detail.append({"repo": name, "first_time": yielded, "max_cycle": max_cycle,
                       "regressions": regr, "escalated": name in escalated})
    return {"pct": round(100.0 * first_pass / total, 1) if total else None,
            "repos_first_time": first_pass, "repos_through_qa": total,
            "by_repo": detail}


def _intake_status_counts(rows):
    total = len(rows)
    resolved = sum(1 for r in rows if r.get("resolved_at"))
    return {"total": total, "open": total - resolved, "resolved": resolved}


def _post_merge_calibration(ledger):
    pf = ledger.get("production_findings", [])
    sd = ledger.get("spec_doubts", [])
    scr = ledger.get("spec_change_requests", [])
    scr_counts = _intake_status_counts(scr)
    for decision in ("accepted", "rejected", "superseded"):
        scr_counts[decision] = sum(1 for r in scr if r.get("decision") == decision)
    return {
        "production_findings": _intake_status_counts(pf),
        "spec_doubts": _intake_status_counts(sd),
        "spec_change_requests": scr_counts,
        "contract_reopen_signals": len(pf) + len(sd) + len(scr),
    }


def cmd_summary(args):
    ledger = _load(args.ledger)
    repos = {}
    agg_cov_c = agg_cov_m = agg_prod = agg_test_loc = agg_tests = 0
    for name, node in ledger["repos"].items():
        last = node["snapshots"][-1] if node["snapshots"] else None
        if last:
            cov, tc, loc = last["coverage"], last["tests"], last["loc"]
            repos[name] = {
                "coverage_pct": cov["pct"],
                "prod_loc": loc["prod_loc"], "test_loc": loc["test_loc"],
                "test_count": tc["total"],
                "test_per_kloc": round(tc["total"] / (loc["prod_loc"] / 1000), 1)
                if loc["prod_loc"] else None,
                "test_to_prod_loc_ratio": round(loc["test_loc"] / loc["prod_loc"], 2)
                if loc["prod_loc"] else None,
            }
            agg_cov_c += cov["covered"]
            agg_cov_m += cov["missed"]
            agg_prod += loc["prod_loc"]
            agg_test_loc += loc["test_loc"]
            agg_tests += tc["total"]
        else:
            repos[name] = {"note": "no snapshot taken"}
    total_cov = agg_cov_c + agg_cov_m
    summary = {
        "run_id": ledger["run_id"],
        "started_at": ledger["started_at"],
        "updated_at": ledger["updated_at"],
        "total_steps": ledger["step_counter"],
        "escalations": ledger["escalations"],
        "first_time_yield": _fty(ledger),
        "by_tool": _tool_rollup(ledger),
        "by_repo": repos,
        "post_merge_calibration": _post_merge_calibration(ledger),
        "aggregate": {
            "coverage_pct": round(agg_cov_c / total_cov * 100, 2) if total_cov else 0.0,
            "prod_loc": agg_prod,
            "test_loc": agg_test_loc,
            "test_count": agg_tests,
            "test_per_kloc": round(agg_tests / (agg_prod / 1000), 1) if agg_prod else None,
            "test_to_prod_loc_ratio": round(agg_test_loc / agg_prod, 2) if agg_prod else None,
        },
    }
    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return
    a = summary["aggregate"]
    print(f"=== dev-loop run {summary['run_id']} ===")
    print(f"total steps: {summary['total_steps']}   escalations: {len(summary['escalations'])}")
    fty = summary["first_time_yield"]
    if fty["repos_through_qa"]:
        print(f"first-time yield: {fty['pct']}% "
              f"({fty['repos_first_time']}/{fty['repos_through_qa']} repos limpios al 1er "
              f"ciclo, sin regresiones ni escalacion — Lean, informativo, no gatea)")
    print(f"aggregate coverage: {a['coverage_pct']}%   "
          f"prod LOC: {a['prod_loc']}   test LOC: {a['test_loc']}   "
          f"tests: {a['test_count']}   tests/kLOC: {a['test_per_kloc']}")
    cal = summary["post_merge_calibration"]
    if cal["contract_reopen_signals"]:
        print(f"post-merge calibration: {cal['contract_reopen_signals']} contract reopen signal(s) "
              f"(PF {cal['production_findings']['total']}, "
              f"SD {cal['spec_doubts']['total']}, "
              f"SCR {cal['spec_change_requests']['total']})")
    print("--- by tool (reported / fixed / %fixed / deferred / suppressed) ---")
    for t, x in summary["by_tool"].items():
        print(f"  {t:14s} {x['reported']:5d} / {x['fixed']:5d} / "
              f"{str(x['fixed_pct']) + '%':>6s} / {x['deferred']:4d} / {x['suppressed']:4d}")
    print("--- by repo (coverage / prod LOC / tests) ---")
    for r, x in summary["by_repo"].items():
        if "coverage_pct" in x:
            print(f"  {r:14s} {x['coverage_pct']:5.1f}%  {x['prod_loc']:7d}  {x['test_count']:5d}")
        else:
            print(f"  {r:14s} (no snapshot)")


# --------------------------------------------------------------------------- #
# readiness KPI
# --------------------------------------------------------------------------- #
# Defaults (overridable via config.defaults). Readiness measures STATE of the
# result, never effort spent. Cycles are churn, not readiness.
# acceptance (criterios AC-n cerrados por testcase MEDIDO) domina; el checkbox
# (adr) queda como progreso narrado y coverage baja de peso: verde alto no es
# evidencia de resolver el problema — cerrar criterios trazados SI (Tip 94 /
# anti-Goodhart: pulir la metrica sin acercarse a la solucion es el modo de
# falla tipico del agente).
DEFAULT_WEIGHTS = {"acceptance": 30, "adr": 15, "coverage": 15,
                   "static_gate": 20, "convergence": 10, "integration": 10}
DEFAULT_CAPS = {"tests_red": 35, "blocker_critical": 65, "escalation": 75}
DEFAULT_STATIC_ZERO_AT = 10  # gated-open count at which the static dimension hits 0
BANDS = [(95, "READY"), (80, "RELEASE CANDIDATE"), (50, "IN PROGRESS"), (0, "NOT READY")]


def _band(score):
    for floor, label in BANDS:
        if score >= floor:
            return label
    return "NOT READY"


_AC_ID = re.compile(r"(?i)^[*_`]*\s*AC[-_]?0*(\d+)\b[*_`]*[\s.:—–·-]*")


def _parse_acceptance_items(path, section=None):
    """Checkboxes markdown de ACCEPTANCE, con ID trazable opcional por criterio
    ('- [ ] AC-01 — cuando X entonces Y'). Los IDs se normalizan por numero
    (AC-01 == AC_1 == ac1 — los nombres de test de python/go no admiten '-').
    Devuelve (items, found); item = {'id': 'AC-n'|None, 'checked', 'text'}."""
    if not path or not os.path.exists(path):
        return [], False
    items = []
    in_scope = section is None
    sec_low = section.lower() if section else None
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                stripped = line.strip()
                if section is not None and stripped.startswith("#"):
                    in_scope = sec_low in stripped.lower()
                    continue
                if not in_scope:
                    continue
                s = stripped
                if s[:5].lower() in ("- [x]", "* [x]"):
                    checked = True
                elif s[:5] in ("- [ ]", "* [ ]"):
                    checked = False
                else:
                    continue
                body = s[5:].strip()
                m = _AC_ID.match(body)
                items.append({"id": f"AC-{int(m.group(1))}" if m else None,
                              "checked": checked,
                              "text": body[m.end():].strip() if m else body})
    except OSError:
        return [], False
    return items, True


def _parse_acceptance(path, section=None):
    """Count markdown checkboxes. Returns (done, total, found)."""
    items, found = _parse_acceptance_items(path, section)
    return sum(1 for i in items if i["checked"]), len(items), found


def _gate_open_and_sev(node):
    """From the latest static-gate run per linter: (gated_open, {sev: count})."""
    latest = _latest_static_by_tool(node)
    gated_open = sum((s.get("gated_reported") or 0) for s in latest.values())
    sev = {}
    for s in latest.values():
        for k, v in (s.get("severity_counts") or {}).items():
            sev[k] = sev.get(k, 0) + v
    return gated_open, sev


def _dropped_reports(node):
    """Test reports discovered but NOT usable, from the latest snapshot. Dropping evidence
    quietly would be silence buying a pass, so readiness names them (kit 1.44.0)."""
    if node.get("snapshots"):
        return node["snapshots"][-1].get("tests", {}).get("skipped_reports") or []
    return []


def _tests_red(node):
    """True if the system's tests are currently failing."""
    if node.get("snapshots"):
        t = node["snapshots"][-1].get("tests", {})
        if (t.get("failures", 0) or 0) + (t.get("errors", 0) or 0) > 0:
            return True
    agent = [s for s in node["iterations"]
             if s.get("category", "agent") == "agent" and s.get("tests_passed") is not None]
    if agent and agent[-1].get("tests_passed") is False:
        return True
    return False


def _apply_caps(score, caps_active):
    # tuplas (label, ceiling) o (label, ceiling, key) — tolerante a ambas
    capped = score
    reason = None
    for cap in caps_active:
        label, ceiling = cap[0], cap[1]
        if capped > ceiling:
            capped = ceiling
            reason = label
    return capped, reason


def _repo_readiness(ledger, name, node, weights, caps, zero_at, k):
    defaults = ledger["config"].get("defaults", {})
    threshold = defaults.get("coverage_threshold", 60)
    qa_order = defaults.get("qa_tools_order")
    cfg = next((r for r in ledger["config"].get("repos", []) if r["name"] == name), {})
    rtype = cfg.get("type", "maven")
    cov = coverage(cfg.get("path", "."), rtype)
    cov_dim = min(cov["pct"] / threshold, 1.0) if threshold else 0.0
    # silence is not success, part two (kit 1.44.0, mirrors static_unmeasured below):
    # NO coverage report at all is a different FACT from a report that says 0%. Both
    # score 0.0 -- redistributing the weight automatically would let any repo raise its
    # score by DELETING its instrumentation -- but only the first is a missing
    # measurement, so it is surfaced: the operator either instruments, or DECLARES the
    # exemption via defaults.readiness_weights.coverage = 0 (a config declaration is a
    # human requirement, and carries provenance).
    coverage_unmeasured = not cov.get("report_found", False)
    dropped_reports = _dropped_reports(node)
    gated_open, sev = _gate_open_and_sev(node)
    # silence is not success: for a lint-capable repo (every type the ingest
    # parsers support) with NO static-gate record ever logged, the dimension is
    # UNMEASURED (0.0), not a perfect 1.0. A tool that didn't run is never green.
    static_unmeasured = (rtype in ("maven", "python", "node", "go", "rust",
                                   "dotnet", "cpp", "gradle", "swift", "ant")
                         and not _latest_static_by_tool(node))
    if static_unmeasured:
        static_dim = 0.0
    else:
        static_dim = 1.0 if gated_open == 0 else max(0.0, 1 - min(gated_open, zero_at) / zero_at)
    converged, creasons = _converged(node, k, qa_order)
    conv_dim = 1.0 if converged else 0.0
    # per-repo score uses only the local dimensions, renormalized
    local = {"coverage": cov_dim, "static_gate": static_dim, "convergence": conv_dim}
    wsum = sum(weights[d] for d in local)
    raw = sum(weights[d] * v for d, v in local.items()) / wsum * 100 if wsum else 0.0

    caps_active = []
    tests_red = _tests_red(node)
    if tests_red:
        caps_active.append(("tests red", caps["tests_red"]))
    blk = sev.get("BLOCKER", 0) + sev.get("CRITICAL", 0)
    if blk:
        caps_active.append((f"{blk} BLOCKER/CRITICAL open", caps["blocker_critical"]))
    # the escalation cap holds until the human RESOLVES it (recorded event) —
    # independent of convergence, so a converged-but-unreviewed repo stays capped.
    esc = [e for e in ledger.get("escalations", [])
           if e.get("repo") == name and not e.get("resolved_at")]
    if esc:
        caps_active.append(("unresolved escalation", caps["escalation"]))
    # golden_required (kit 1.45.0, ADR-002): if declared and NO approved golden-diff gate was
    # ever logged for this repo, the frozen baseline is ABSENT -- a measured fact that caps
    # readiness. A present-but-FAILED golden is already handled by the BLOCKER path above, so
    # only the ABSENT case fires here (no double-cap).
    golden_rec = _latest_static_by_tool(node).get("gate:golden-diff")
    golden_missing = bool(defaults.get("golden_required")) and golden_rec is None
    if golden_missing:
        caps_active.append(("golden requerido: sin golden aprobado", GOLDEN_REQUIRED_CEILING))
    final, cap_reason = _apply_caps(raw, caps_active)
    return {
        "score": round(final, 1), "raw": round(raw, 1), "status": _band(final),
        "cap_reason": cap_reason,
        "dims": {"coverage": round(cov_dim, 3), "static_gate": round(static_dim, 3),
                 "convergence": round(conv_dim, 3)},
        "facts": {"coverage_pct": cov["pct"], "coverage_threshold": threshold,
                  "gated_open": gated_open, "severity": sev, "converged": converged,
                  "convergence_reasons": creasons, "tests_red": tests_red,
                  "static_unmeasured": static_unmeasured,
                  "coverage_unmeasured": coverage_unmeasured,
                  "dropped_reports": dropped_reports,
                  # only surfaced when golden_required is in play, so a config with neither
                  # risk_profile nor golden_required has byte-identical facts to before (1.45.0)
                  **({"golden_missing": golden_missing}
                     if defaults.get("golden_required") else {})},
    }


# plateau/stop-signal (kit 1.14.0, Topic 37 'Listen to Your Lizard Brain' +
# Topic 5 'Know When to Stop'). ADVISORY puro: recomienda, jamas gatea.
STALL_WINDOW = 3  # ciclos consecutivos sin progreso que disparan el aviso


def _stall_series(node, qa_order=None):
    """Findings gateados por CICLO de agente (suma sobre las tools del ciclo),
    en orden de ciclo — la serie sobre la que se mide el plateau. Con qa_order
    configurado solo cuentan ciclos COMPLETOS (todas las tools logueadas): un
    ciclo a medio correr suma parcial y puede enmascarar o inventar un stall."""
    by_cycle, tools_by_cycle = {}, {}
    for s in node["iterations"]:
        if s.get("category", "agent") != "agent":
            continue
        it = s.get("iteration") or 0
        by_cycle[it] = by_cycle.get(it, 0) + (s.get("gated_reported") or 0)
        tools_by_cycle.setdefault(it, set()).add(s.get("tool"))
    cycles = sorted(by_cycle)
    if qa_order:
        cycles = [c for c in cycles if tools_by_cycle[c] >= set(qa_order)]
    return [by_cycle[c] for c in cycles]


def _is_stalled(node, qa_order=None, window=STALL_WINDOW):
    """True si los ultimos `window` ciclos (completos) muestran findings
    gateados planos o SUBIENDO (y todavia hay findings): iterar mas no esta
    acercando la solucion — la senal tipica de que el problema es de
    diseño/SPEC, no de codigo."""
    tail = _stall_series(node, qa_order)[-window:]
    if len(tail) < window or tail[-1] <= 0:
        return False
    return all(tail[i] <= tail[i + 1] for i in range(len(tail) - 1))


# --------------------------------------------------------------------------- #
# mirador — bird's-eye status view (kit 1.32.0). Agrega SOLO hechos que el ledger
# ya tiene al contrato DATA del template. Read-only, determinista, cero narracion
# del LLM. Truth-pass: un campo sin fuente se emite null/[] (el template degrada),
# jamas inventado.
_MIRADOR_PHASES = [
    ("idea", "Idea", "00"), ("disc", "Discovery", "01"),
    ("spec", "SPEC", "02"), ("adr", "ADR . CONST", "03"),
    ("build", "Build", "04"), ("qa", "QA loop", "05"),
    ("verify", "Verify", "06"), ("prod", "Produccion", "07"),
]
_MIRADOR_TITLE = {
    "READY": "Listo para release",
    "RELEASE CANDIDATE": "Casi listo para release",
    "IN PROGRESS": "En construccion",
    # NOT READY has no fixed title: it is score-aware (see cmd_dashboard, kit 1.41.2).
}
# los 7 invariantes de la CONSTITUTION (lista fija: el engine NO lee CONSTITUTION.md
# por diseno). El status se infiere del gate persistido donde hay mapeo; los que no
# tienen gate (Seguridad, Dominio) quedan null — nunca se inventan.
_MIRADOR_INV = ["Seguridad", "Dominio", "Simplicidad", "Reuso", "Golden",
                "Tests efectivos", "Integridad del gate"]
_INV_GATE = {"Simplicidad": "simplicity", "Reuso": "waste", "Golden": "golden",
             "Tests efectivos": "pit-check", "Integridad del gate": "gate-check"}

# execution_policy (kit 1.35.0) is routing metadata for the orchestrator/operator:
# what the methodology is doing in each phase, and which model/effort tier should
# be used. It is deliberately NOT part of readiness scoring; facts still block,
# guesses still advise, and the engine remains model-agnostic.
_EXEC_DEFAULT_PHASES = {
    "idea": {"method": "Capture the intent and decide whether Uscha rigor is warranted",
             "tier": "human", "model": None, "effort": "none", "uncorrelated": False},
    "disc": {"method": "Shape the idea into discovery facts, scope, risks and invariants",
             "tier": "deep", "model": None, "effort": "high", "uncorrelated": False},
    "spec": {"method": "Turn scope into testable SPEC/ACCEPTANCE contracts",
             "tier": "deep", "model": None, "effort": "high", "uncorrelated": False},
    "adr": {"method": "Record consequential decisions and non-negotiable invariants",
            "tier": "deep", "model": None, "effort": "high", "uncorrelated": False},
    "build": {"method": "Implement the accepted plan with tests as guardrail",
              "tier": "standard", "model": None, "effort": "medium", "uncorrelated": False},
    "qa": {"method": "Run maker-not-checker QA passes and persist fact gates",
           "tier": "checker", "model": None, "effort": "high", "uncorrelated": True},
    "verify": {"method": "Re-run measured readiness, freshness and release gates",
               "tier": "standard", "model": None, "effort": "medium", "uncorrelated": False},
    "prod": {"method": "Stop at the human merge/deploy gate",
             "tier": "human", "model": None, "effort": "none", "uncorrelated": False},
}


def _execution_policy_raw(cfg):
    defaults = cfg.get("defaults", {}) if isinstance(cfg, dict) else {}
    ep = defaults.get("execution_policy", {})
    if not isinstance(ep, dict):
        ep = {}
    default = ep.get("default", {})
    if not isinstance(default, dict):
        default = {}
    phases = ep.get("phases", {})
    if not isinstance(phases, dict):
        phases = {}
    source = "config.defaults.execution_policy" if ep else "kit.default_execution_policy"
    return source, default, phases


def _phase_execution(cfg, key):
    source, default, phases = _execution_policy_raw(cfg)
    base = dict(_EXEC_DEFAULT_PHASES.get(key, {}))
    # A declared default is a project routing policy; it intentionally overrides
    # built-in tier/effort defaults, while the phase keeps its built-in method unless
    # the phase declares one. Phase entries then override everything.
    for field in ("tier", "model", "effort", "uncorrelated"):
        if field in default:
            base[field] = default.get(field)
    phase = phases.get(key, {})
    if not isinstance(phase, dict):
        phase = {}
    for field in ("method", "tier", "model", "effort", "uncorrelated"):
        if field in phase:
            base[field] = phase.get(field)
    return {
        "phase": key,
        "method": base.get("method") or _EXEC_DEFAULT_PHASES.get(key, {}).get("method"),
        "tier": base.get("tier"),
        "model": base.get("model"),
        "effort": base.get("effort"),
        "uncorrelated": bool(base.get("uncorrelated")),
        "source": source,
    }


def _execution_policy(cfg):
    source, default, _phases = _execution_policy_raw(cfg)
    default_out = {
        "tier": default.get("tier"),
        "model": default.get("model"),
        "effort": default.get("effort"),
    }
    return {
        "source": source,
        "default": default_out,
        "phases": {key: _phase_execution(cfg, key) for key, _label, _ph in _MIRADOR_PHASES},
    }


def _execution_line(ex):
    def val(x):
        return "default" if x is None or x == "" else str(x)
    suffix = " uncorrelated=true" if ex.get("uncorrelated") else ""
    return ("EXECUTION {phase}: {method} | tier={tier} model={model} "
            "effort={effort}{suffix}").format(
                phase=ex.get("phase"),
                method=ex.get("method") or "methodology phase",
                tier=val(ex.get("tier")),
                model=val(ex.get("model")),
                effort=val(ex.get("effort")),
                suffix=suffix)


def cmd_execution_policy(args):
    ledger = _load(args.ledger)
    cfg = ledger.get("config", {})
    policy = _execution_policy(cfg)
    valid = [key for key, _label, _ph in _MIRADOR_PHASES]
    phase = (args.phase or "").strip().lower()
    if phase:
        if phase not in policy["phases"]:
            raise SystemExit("[qa_ledger] unknown execution phase '%s' (valid: %s)"
                             % (phase, ",".join(valid)))
        ex = policy["phases"][phase]
        if getattr(args, "json", False):
            print(json.dumps(ex, indent=2, ensure_ascii=False))
        else:
            print(_execution_line(ex))
        return
    if getattr(args, "json", False):
        print(json.dumps(policy, indent=2, ensure_ascii=False))
        return
    for key in valid:
        print(_execution_line(policy["phases"][key]))


def _repo_loop_count(node):
    """Pasadas del QA loop de un repo = la iteracion mas alta registrada. UNA definicion:
    el badge del mirador, el churn del readiness y el odometro persistido leian lo mismo
    calculado en tres lugares distintos — un cambio en uno los desincronizaba en silencio
    (kit 1.48.1)."""
    return max((s.get("iteration", 0) or 0 for s in node.get("iterations", [])), default=0)


def _reached_index(score):
    """Proyecta un readiness MEDIDO sobre el sendero de 8 nodos (idea..prod) para el
    time-lapse. Transformacion determinista del score (como la band), NO un dato
    independiente de milestones — el engine no trackea completitud por fase."""
    if score is None:
        return 0
    for floor, idx in ((95, 7), (80, 6), (65, 5), (50, 4), (35, 3), (20, 2), (1, 1)):
        if score >= floor:
            return idx
    return 0



_ADR_STATUS_TO_PHASE = {
    "accepted": "done", "approved": "done", "done": "done", "final": "done",
    "experiment": "prog", "experimental": "prog",
    "proposed": "prog", "draft": "prog", "wip": "prog",
    "rejected": "todo", "superseded": "todo", "deprecated": "todo",
}

_ADR_EXPERIMENT_REQUIRED = {
    "hypothesis": {"hypothesis", "hipotesis"},
    "feedback_signal": {"feedback_signal", "feedback", "signal", "senal_de_feedback",
                        "senal_feedback", "criterio_de_feedback", "criterio_feedback"},
    "promote_criteria": {"promote_criteria", "promotion_criteria", "criterios_de_promocion",
                         "criterio_de_promocion", "promocion"},
    "rollback_supersede_criteria": {"rollback_supersede_criteria",
                                     "rollback_supersede",
                                     "rollback_criteria",
                                     "supersede_criteria",
                                     "criterios_de_rollback",
                                     "criterio_de_rollback"},
}


def _ascii_fold(s):
    normalized = unicodedata.normalize("NFKD", (s or "").lower())
    return "".join(c for c in normalized if not unicodedata.combining(c))

def _adr_key(s):
    s = _ascii_fold(s)
    s = re.sub(r"^[#\s]+", "", s).strip()
    s = re.split(r"[:=]", s, 1)[0]
    s = re.sub(r"[`*_]+", "", s)
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def _adr_headings(body):
    return {_adr_key(m.group(1)) for m in re.finditer(r"(?m)^\s{0,3}#{1,6}\s+(.+?)\s*$", body or "")}


def _adr_line_value(body, labels):
    names = "|".join(re.escape(x) for x in labels)
    m = re.search(r"(?im)^\s*(?:#{1,6}\s*)?(?:" + names + r")\s*[:=]\s*(.+?)\s*$", body or "")
    return m.group(1).strip() if m else None


def _adr_has_any(headings, aliases):
    return bool(set(headings) & set(aliases))


def _date_expired(value):
    if not value:
        return False
    m = re.search(r"\d{4}-\d{2}-\d{2}", value)
    if not m:
        return False
    try:
        return datetime.strptime(m.group(0), "%Y-%m-%d").date() < datetime.now(timezone.utc).date()
    except ValueError:
        return False


def _adr_experiment_fields(body):
    headings = _adr_headings(body)
    review_by = _adr_line_value(body, ["Review By", "review_by", "Revisar antes de", "Revision antes de"])
    review_trigger = _adr_line_value(body, ["Review Trigger", "review_trigger", "Trigger de revision"])
    feedback_signal = _adr_line_value(body, ["Feedback Signal", "feedback_signal", "Senal de feedback"])

    missing = []
    for key, aliases in _ADR_EXPERIMENT_REQUIRED.items():
        if key == "feedback_signal" and feedback_signal:
            continue
        if not _adr_has_any(headings, aliases):
            missing.append(key)
    if not (review_by or review_trigger or _adr_has_any(headings, {"review_by", "review_trigger"})):
        missing.append("review")

    expired = _date_expired(review_by)
    return {
        "experiment_valid": not missing,
        "experiment_missing": missing,
        "review_by": review_by,
        "review_trigger": review_trigger,
        "feedback_signal": feedback_signal,
        "expired": expired,
    }


def _adr_experiment_summary(adrs):
    exps = [a for a in adrs if a.get("adr_status") == "experiment"]
    return {
        "open": len(exps),
        "malformed": sum(1 for a in exps if not a.get("experiment_valid")),
        "expired": sum(1 for a in exps if a.get("expired")),
        "ids": [a.get("id") for a in exps],
    }


def _mirador_adrs(adr_dir):
    """Read-only glob of docs/adr/*.md for the mirador contract.

    The legacy field `status` remains the coarse UI bucket (done/prog/todo). The richer
    `adr_status` preserves the authored ADR status. `experiment` is advisory/visible:
    it does not alter readiness and is never a PR gate by itself.
    """
    out = []
    if not adr_dir or not os.path.isdir(adr_dir):
        return out
    for f in sorted(glob.glob(os.path.join(adr_dir, "*.md"))):
        base = os.path.basename(f)
        if base.lower() in ("readme.md", "template.md", "index.md", "_index.md"):
            continue
        try:
            body = open(f, encoding="utf-8").read()
        except OSError:
            continue
        mid = re.search(r"ADR[-_]?0*(\d+)", base) or re.search(r"ADR[-_]?0*(\d+)", body)
        aid = "ADR-%03d" % int(mid.group(1)) if mid else base[:-3]
        mt = re.search(r"(?m)^#\s+(.+)$", body)
        title = mt.group(1).strip() if mt else base[:-3]
        title = re.sub(r"(?i)^ADR[-_]?0*\d+[\s:.??????-]*", "", title).strip() or title
        ms = re.search(r"(?im)^\s*(?:#{1,6}\s*)?(?:[-*]\s*)?status\s*[:=]\s*([A-Za-z_-]+)", body)
        adr_status = ms.group(1).lower().replace("_", "-") if ms else None
        phase_status = _ADR_STATUS_TO_PHASE.get((adr_status or "").replace("-", "_"), "todo")
        # RECEIPT (kit 1.50.0): the source filename travels -- `f` was always in scope.
        row = {"id": aid, "t": title, "status": phase_status, "adr_status": adr_status,
               "file": f.replace("\\", "/")}
        if adr_status in ("experiment", "experimental"):
            row["adr_status"] = "experiment"
            row.update(_adr_experiment_fields(body))
        out.append(row)
    return out


def cmd_dashboard(args):
    """mirador — vista bird's-eye del estado. Agrega SOLO hechos que el ledger ya tiene
    al contrato DATA del template. Read-only, determinista, cero narracion. Campos sin
    fuente -> null/[] (el template degrada), jamas inventados. --json imprime el
    contrato; sin flags, un veredicto de una linea."""
    import contextlib
    import io as _io
    ledger = _load(args.ledger)
    cfg = ledger.get("config", {})
    exec_policy = _execution_policy(cfg)

    # readiness: se reusan los numeros de `readiness --json` VERBATIM (mismo KPI, sin
    # drift posible) capturando su salida. --record OFF: el dashboard NUNCA escribe.
    _r = argparse.Namespace(**vars(args))
    _r.json = True
    _r.verbose = False
    _r.record = False
    _buf = _io.StringIO()
    try:
        with contextlib.redirect_stdout(_buf):
            cmd_readiness(_r)
    except SystemExit:
        pass
    rd = json.loads(_buf.getvalue())

    score = rd.get("score")
    band = rd.get("status")
    cap = rd.get("cap_reason")
    # kit 1.41.2: NOT READY (band 0-49) is NOT "hasn't started". Above 0 the project HAS
    # started but lacks enough MEASURED evidence -- do not say "no arranca" at e.g. 22.
    if band == "NOT READY":
        _title = ("Todavia sin evidencia medida" if (score or 0) < 1
                  else "En construccion -- evidencia insuficiente")
    else:
        _title = _MIRADOR_TITLE.get(band)
    readiness = {"score": score, "band": band,
                 "title": _title,
                 "sub": (f"cap: {cap}" if cap else None)}

    # subscores: coverage es numerico real; los gates persistidos (simplicity/waste/
    # golden) guardan pass/fail + note, NO un score 0-100 -> val=null (truth-pass),
    # bd = el estado persistido. (golden se persiste como kind 'golden-diff'.)
    covp = rd.get("facts", {}).get("coverage_pct")
    subscores = [{"k": "coverage",
                  "val": round(covp) if isinstance(covp, (int, float)) else None,
                  "bd": (f"{round(covp)}%" if isinstance(covp, (int, float)) else None)}]
    gate_block, gate_note = {}, {}
    for g in rd.get("gates", []):
        kind = (g.get("tool") or "").replace("gate:", "")
        key = "golden" if kind.startswith("golden") else kind
        gate_block[key] = gate_block.get(key, False) or bool(g.get("blocking"))
        if g.get("note") and key not in gate_note:
            gate_note[key] = g.get("note")
    for key in ("simplicity", "waste", "golden"):
        if key in gate_block:
            subscores.append({"k": key, "val": None,
                              "bd": gate_note.get(key) or ("FAIL" if gate_block[key] else "OK")})

    # loops: iters + estado por repo (escalated > converged > active). max sin fuente.
    # El estado se deriva ENTERO con _derive_phase (kit 1.48.1) — la MISMA funcion que
    # alimenta el odometro del statusline. Antes esta vista mezclaba dos fuentes:
    # ledger["escalations"] a secas (se perdia spec-doubts, spec-change-requests y
    # production findings gateados) y _converged() a secas (que ACEPTA tests narrados por
    # el agente cuando no hay snapshot medido, mientras _derive_phase exige evidencia
    # medida para 'pr-ready'). Resultado: el mirador cantaba "convergido" sobre tests que
    # nadie midio, justo en la vista que decide un merge. Una sola derivacion, una verdad.
    # acceptance (kit 1.49.0): reemplaza al panel "specs" (que era [] hardcodeado — el
    # engine trackea AC-nn, no SPEC-nnn: mostrar la moneda real). Reusa VERBATIM el bloque
    # acceptance del readiness capturado; el status por criterio se computa ACA porque el
    # template pinta, no deriva: measured = cerrado por test verde; narrated = tildado a
    # mano SIN test verde; open = ni lo uno ni lo otro.
    _acc = rd.get("acceptance") or {}
    _mc = set(_acc.get("measured_closed") or [])
    _no = set(_acc.get("narrated_only") or [])
    acceptance = {
        "found": _acc.get("found"), "file": _acc.get("file"),
        "traceable": _acc.get("traceable"), "total": _acc.get("total"),
        "measured_done": len(_mc), "measured_pct": _acc.get("measured_pct"),
        # untagged travels too: `total` counts EVERY checkbox but `items` only the AC-nn
        # tagged ones -- without this the panel shows fewer rows than the header counts,
        # a silent gap with no reason given (the exact sin this panel exists to remove).
        "untagged": _acc.get("untagged"),
        "stale_reports": _acc.get("stale_reports"),
        "items": [{"id": it["id"], "text": it["text"],
                   "status": ("measured" if it["id"] in _mc
                              else "narrated" if it["id"] in _no else "open"),
                   # receipt (kit 1.50.0): the testcases backing the verdict travel too
                   "cases": it.get("cases") or []}
                  for it in (_acc.get("items") or [])],
    }

    qa_order_d = (cfg.get("defaults") or {}).get("qa_tools_order")
    k_d = getattr(args, "tools_per_cycle", 3)
    loops = []
    for name, rnode in ledger.get("repos", {}).items():
        phase_d, _ = _derive_phase(ledger, name, rnode, k_d, qa_order_d)
        state = ("escalated" if phase_d == "escalated"
                 else "converged" if phase_d == "pr-ready" else "active")
        # burn-down (kit 1.49.0): the loop's STORY, not just its count — findings
        # reported/gated/fixed/deferred per cycle, straight from the recorded steps.
        # AGENT steps only (same filter as _converged): static-gate ingests carry noisy
        # below-gate counts (a linter's 35 LOWs re-reported every refresh) that drown the
        # loop's trend, and the gates already speak through readiness's own gate line.
        _cycles = {}
        for s in rnode.get("iterations", []):
            if s.get("category", "agent") != "agent":
                continue
            c = s.get("iteration", 0) or 0
            row = _cycles.setdefault(c, {"cycle": c, "reported": 0, "gated": 0,
                                         "fixed": 0, "deferred": 0})
            row["reported"] += s.get("reported") or 0
            row["gated"] += s.get("gated_reported") or 0
            row["fixed"] += s.get("fixed") or 0
            row["deferred"] += s.get("deferred") or 0
        loops.append({"mod": name, "iters": _repo_loop_count(rnode),
                      "max": None, "state": state,
                      # the REAL derived phase (kit 1.49.0, closes deferred D-01): the
                      # 3-state badge stays, the FSM detail travels alongside it.
                      "phase": phase_d,
                      "series": [_cycles[c] for c in sorted(_cycles)]})

    # odometro del QA loop (kit 1.47.0): badge del nodo "qa" del sendero. Solo hechos ya
    # computados: pasadas (max iteration), escalaciones abiertas, plateau (advisory 1.14.0)
    # o convergencia. Sin pasadas -> null (el template no dibuja el badge).
    qa_count = None
    _mx = max((l["iters"] for l in loops), default=0)
    if _mx:
        bits = [f"{_mx} loop" + ("s" if _mx != 1 else "")]
        _esc = sum(1 for l in loops if l["state"] == "escalated")
        if _esc:
            bits.append(f"{_esc} escalado" + ("s" if _esc != 1 else ""))
        if rd.get("advice", {}).get("stalled_repos"):
            bits.append("plateau")
        elif loops and all(l["state"] == "converged" for l in loops):
            bits.append("convergido")
        qa_count = " · ".join(bits)

    # phases: esqueleto fijo de 8 nodos; status = proyeccion determinista del readiness
    # (nodos < alcanzado = done; el alcanzado = block si hay cap, si no prog; resto todo).
    # count = odometro medido para "qa"; el resto sin fuente -> null.
    ridx = _reached_index(score)
    phases = []
    for i, (key, label, ph) in enumerate(_MIRADOR_PHASES):
        st = "done" if i < ridx else ("todo" if i > ridx else ("block" if cap else "prog"))
        phases.append({"key": key, "label": label, "phase": ph,
                       "status": st, "count": qa_count if key == "qa" else None,
                       "risk": None,
                       "execution": exec_policy["phases"].get(key)})

    # inv: nombres fijos; status del gate persistido donde mapea, si no null.
    inv = []
    for name in _MIRADOR_INV:
        gk = _INV_GATE.get(name)
        if gk and gk in gate_block:
            inv.append({"name": name, "status": "miss" if gate_block[gk] else "ok"})
        else:
            inv.append({"name": name, "status": None})

    # snapshots: time-lapse del historial persistido por `readiness --record` (add-on
    # 1.32.0). Solo hacia adelante; [] hasta que se registre. reached = proyeccion.
    snapshots = [{"date": h.get("at"), "readiness": h.get("score"),
                  "reached": _reached_index(h.get("score"))}
                 for h in ledger.get("readiness_history", [])]

    names = [r.get("name") for r in cfg.get("repos", []) if r.get("name")]
    # nombre de proyecto: lo declara el humano en config (project/name); si no,
    # se deriva juntando los repos. Truth-pass: nombre puesto si existe, si no derivado.
    project = cfg.get("project") or cfg.get("name") or (" + ".join(names) if names else None)
    adrs = _mirador_adrs(getattr(args, "adr_dir", "docs/adr"))

    # evidence (kit 1.50.0): RECEIPTS. The template shipped a click-a-milestone drawer
    # since 1.32.0 and the engine fed it {} -- the machinery waited for data that never
    # came. Every receipt below quotes only facts the ledger/reports already hold (paths,
    # timestamps, counts); a phase with no recorded facts gets NO key and the template
    # says so honestly. <span class='g|r|a|m'> are the drawer's whitelisted tokens.
    def _fmtd(iso):
        return (iso or "")[:16].replace("T", " ")

    def _esc(s):
        # user-authored strings (testcase names, file paths, titles) must render as
        # TEXT: the drawer tokenizer treats a literal <span class='g'> as markup, so a
        # crafted testcase name could paint fake verdicts over the receipt. '&lt;'
        # round-trips back to a literal '<' on screen.
        return str(s or "").replace("<", "&lt;")

    ev = {}
    if acceptance.get("found"):
        _l = [f"archivo: {_esc(acceptance.get('file'))}",
              f"criterios: {acceptance.get('total')} "
              f"({len(acceptance.get('items') or [])} con ID AC-nn)",
              f"cerrados por test verde: <span class='g'>"
              f"{acceptance.get('measured_done')}</span>"]
        if acceptance.get("untagged"):
            _l.append(f"<span class='a'>{acceptance['untagged']} sin ID</span> "
                      f"— no pueden cerrarse medidos")
        ev["spec"] = {"ey": "acceptance · medido",
                      "title": "SPEC — criterios de aceptacion",
                      "desc": "La moneda del engine: un AC-nn cierra solo con un "
                              "testcase verde que lleva su nombre.",
                      "pre": "\n".join(_l)}
    if adrs:
        _l = [f"{_esc(a['id'])} — {_esc(a.get('adr_status') or a['status'])} — "
              f"{_esc(a.get('file', ''))}" for a in adrs[:8]]
        ev["adr"] = {"ey": "decisiones · docs/adr",
                     "title": f"{len(adrs)} ADR registrados",
                     "desc": "Cada decision con su archivo fuente.",
                     "pre": "\n".join(_l)}
    _l = []
    for name, rnode in ledger.get("repos", {}).items():
        snaps = rnode.get("snapshots") or []
        if not snaps:
            continue
        s = snaps[-1]
        t = s.get("tests") or {}
        c = s.get("coverage") or {}
        loc = s.get("loc") or {}
        _l.append(f"{_esc(name)} @ {_fmtd(s.get('at'))}")
        _l.append(f"  loc prod/test: {loc.get('prod_loc')}/{loc.get('test_loc')}")
        if t.get("report_found"):
            _ok = ((t.get("failures", 0) or 0) + (t.get("errors", 0) or 0)) == 0
            _tk = "g" if _ok else "r"
            _fr = (t.get("freshness") or {}).get("status", "?")
            _l.append(f"  tests: <span class='{_tk}'>{t.get('passed')}/"
                      f"{t.get('executed')}</span> · evidencia {_fr}")
            for r in (t.get("reports") or [])[:3]:
                _l.append(f"    {_esc(r.get('path'))} ({_fmtd(r.get('mtime'))})")
        if c.get("report_found"):
            _l.append(f"  coverage: {c.get('pct')}%")
            for rp in (c.get("reports") or [])[:3]:
                _l.append(f"    {_esc(rp)}")
    if _l:
        ev["build"] = {"ey": "snapshot · medido",
                       "title": "Build — ultimo snapshot por repo",
                       "desc": "Lo que el engine midio del arbol: tests, coverage y "
                               "tamano, con sus reportes y frescura.",
                       "pre": "\n".join(_l)}
    _l = []
    for l in loops:
        if not l.get("iters"):
            continue
        _l.append(f"{_esc(l['mod'])}: {l['iters']} ciclo(s) · fase {l.get('phase')} "
                  f"· {l['state']}")
        for c in (l.get("series") or [])[-4:]:
            _tk = "r" if c.get("gated") else "g"
            _l.append(f"  c{c['cycle']}: <span class='{_tk}'>gated {c['gated']}</span> "
                      f"· fixed {c['fixed']} · defer {c['deferred']}")
    _gates = rd.get("gates") or []
    if _gates:
        _l.append(f"gates persistidos: {len(_gates)} "
                  f"({', '.join(sorted({g.get('tool', '?') for g in _gates})[:6])})")
    if _l:
        ev["qa"] = {"ey": "loop · medido",
                    "title": "QA loop — pasadas y gates",
                    "desc": "El burn-down por ciclo sale de los pasos registrados; "
                            "los gates, de los reportes ingeridos.",
                    "pre": "\n".join(_l)}
    if snapshots:
        _last = snapshots[-1]
        _l = [f"ultimo registro: {_fmtd(_last.get('date'))} — "
              f"readiness {_last.get('readiness')}",
              f"ahora: <span class='{'g' if (score or 0) >= 80 else 'a'}'>"
              f"{score}</span> — {band}"]
        if cap:
            _l.append(f"<span class='r'>cap: {cap}</span>")
        _l.append(f"historial: {len(snapshots)} registro(s) de `readiness --record`")
        ev["verify"] = {"ey": "readiness · medido",
                        "title": "Verify — el numero y su historia",
                        "desc": "Cada registro es una corrida real de readiness; "
                                "el time-lapse los reproduce.",
                        "pre": "\n".join(_l)}
    ev["prod"] = {"ey": "gate humano · por diseno",
                  "title": "Produccion — sin evidencia, a proposito",
                  "desc": "El metodo se detiene en el PR: mergear y deployar son "
                          "actos humanos que el ledger no registra.",
                  "pre": "el agente propone, mide y frena;\n"
                         "<span class='m'>el humano decide</span>."}
    _di = rd.get("discovery_intake") or {}
    _din = sum(len(_di.get(k) or []) for k in
               ("production_findings", "spec_doubts", "spec_change_requests"))
    if _din:
        ev["disc"] = {"ey": "intake · abierto",
                      "title": "Discovery intake — feedback esperando",
                      "desc": "Hechos post-produccion que deben entrar al proximo "
                              "ciclo de discovery.",
                      "pre": "\n".join(
                          f"{k.replace('_', ' ')}: {len(_di.get(k) or [])}"
                          for k in ("production_findings", "spec_doubts",
                                    "spec_change_requests") if _di.get(k))}
    # per-criterion receipts: click an AC row -> which testcases back the verdict.
    # CASES-DRIVEN, never status-driven: a criterion with green AND red testcases must
    # show BOTH and name the veto -- a receipt that hides the vetoed green (or the
    # vetoing red) lies about the very evidence it exists to cite.
    for it in acceptance.get("items") or []:
        _st = it.get("status")
        _cases = it.get("cases") or []
        _l = [(f"<span class='{'g' if c.get('ok') else 'r'}'>{_esc(c.get('test'))}"
               f"</span>\n    {_esc(c.get('report'))}") for c in _cases]
        _reds = any(not c.get("ok") for c in _cases)
        if _st == "measured":
            _desc = "Cerrado MEDIDO: estos testcases verdes llevan su nombre."
            _pre = "\n".join(_l) or "cerrado por test verde"
        elif _reds:
            _desc = ("NO cierra: la evidencia roja veta (fail-closed) — un criterio "
                     "cierra con >=1 testcase verde y 0 rojos.")
            _pre = "<span class='r'>veto rojo</span>\n" + "\n".join(_l)
            if _st == "narrated":
                _pre += ("\n<span class='a'>ademas esta tildado a mano</span> — "
                         "el checkbox no anula un rojo.")
        elif _st == "narrated":
            _pre = (f"<span class='a'>tildado a mano</span> — ningun testcase "
                    f"'{_esc(it.get('id'))}_...' lo respalda.\n"
                    "El checkbox es relato; el test es hecho.")
            _desc = "Narrado: el humano lo marco, la evidencia no lo confirma."
        else:
            _pre = "sin test y sin tilde — criterio abierto."
            _desc = "Abierto: nada lo respalda todavia."
        ev[f"ac:{it['id']}"] = {"ey": f"criterio · {_st}",
                                "title": f"{it['id']} — {(it.get('text') or '')[:70]}",
                                "desc": _desc, "pre": _pre}
    out = {
        "project": project,
        "generated": _now(),
        "readiness": readiness,
        "subscores": subscores,
        "phases": phases,
        "execution_policy": exec_policy,
        "discovery_intake": rd.get("discovery_intake", {}),
        "adr_experiments": _adr_experiment_summary(adrs),
        "acceptance": acceptance,
        "adrs": adrs,
        "inv": inv,
        "capas": [],          # NO SOURCE: el engine no puntua las 6 capas de verdad
        "loops": loops,
        "snapshots": snapshots,
        "evidence": ev,       # receipts (kit 1.50.0): facts with paths + timestamps
    }
    # fast-path (ADR-003): latest verdict per repo, straight from the ledger. The key exists
    # ONLY when entries exist: an unconfigured/unused project keeps the exact prior schema
    # ("absent block = behavior identical" is a measured claim, and an unconditional key was
    # a schema change that contradicted it -- found by fresh review).
    if ledger.get("fast_path"):
        out["fast_path"] = {r: [e for e in ledger["fast_path"] if e.get("repo") == r][-1]
                            for r in {e.get("repo") for e in ledger["fast_path"]}}
    if ledger.get("spec_drift"):
        out["spec_drift"] = ledger["spec_drift"]
    # evidence_origin: the latest snapshot's origin per repo, and ONLY when one exists --
    # a ledger predating ADR-007 keeps the exact prior schema (same conditional-key rule
    # fast_path and spec_drift already follow).
    _org = {}
    for _rn, _rnode in ledger["repos"].items():
        _snaps = _rnode.get("snapshots") or []
        if _snaps and _snaps[-1].get("origin"):
            _org[_rn] = _snaps[-1]["origin"]
    if _org:
        out["evidence_origin"] = _org
    if ledger.get(CLEAN_ROOM_KEY):
        out["clean_room"] = {r: [e for e in ledger[CLEAN_ROOM_KEY] if e.get("repo") == r][-1]
                             for r in {e.get("repo") for e in ledger[CLEAN_ROOM_KEY]}}
    if ledger.get("roundtrip"):
        out["roundtrip"] = ledger["roundtrip"]
    # AC-CU-04: undefined verdicts stay OPEN and visible in the readouts -- derived live
    # from delta + curation records per repo (conditional key, the roundtrip pattern)
    _dl_all = {}
    for _rn in ledger["repos"]:
        try:
            _dls = _delta_state(ledger, _rn, _scope_path(ledger, _rn))
        except SystemExit:
            _dls = None
        if _dls is not None:
            _dl_all[_rn] = _dls
    if _dl_all:
        out["candidate_delta"] = _dl_all
    if ledger.get("fidelity"):
        out["fidelity"] = ledger["fidelity"]
    if getattr(args, "json", False):
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return
    head = (f"MIRADOR: readiness {score}/100 — {band}"
            if score is not None else "MIRADOR: sin readiness medido")
    if cap:
        head += f" (cap: {cap})"
    print(head)
    print(f"  {sum(1 for p in phases if p['status'] == 'done')}/8 fases . "
          f"{len(loops)} loop(s) . {len(out['adrs'])} ADR . "
          f"{len(snapshots)} snapshot(s) en el time-lapse")


def cmd_readiness(args):
    ledger = _load(args.ledger)
    defaults = ledger["config"].get("defaults", {})
    weights = {**DEFAULT_WEIGHTS, **defaults.get("readiness_weights", {})}
    caps = {**DEFAULT_CAPS, **defaults.get("readiness_caps", {})}
    zero_at = defaults.get("static_gate_zero_at", DEFAULT_STATIC_ZERO_AT)
    k = args.tools_per_cycle
    threshold = defaults.get("coverage_threshold", 60)
    severity_gate = defaults.get("severity_gate", ["BLOCKER", "CRITICAL", "HIGH"])
    discovery_intake = _discovery_intake(ledger)
    production_open = discovery_intake["production_findings"]
    production_gated = [p for p in production_open
                        if _at_or_above(p.get("severity", "HIGH"), severity_gate)]
    spec_doubts_open = discovery_intake["spec_doubts"]
    spec_change_requests_open = discovery_intake["spec_change_requests"]

    # ADR / acceptance completion (feature-level)
    acc_path = args.acceptance or defaults.get("acceptance_file")
    acc_items, acc_found = _parse_acceptance_items(acc_path, args.section)
    done = sum(1 for i in acc_items if i["checked"])
    total = len(acc_items)
    adr_dim = (done / total) if total else 0.0

    # acceptance TRAZADA — measured beats narrated a nivel CRITERIO: un AC-n
    # cierra solo con >=1 testcase verde taggeado en los reportes JUnit ya
    # ingeridos (y 0 rojos). El checkbox es RELATO; el testcase es HECHO.
    ac_ids = [i for i in acc_items if i["id"]]
    ac_tags = {}
    stale_reports = []
    for rcfg in ledger["config"].get("repos", []):
        rtags, rstale = _ac_tags(rcfg.get("path", "."),
                                 rcfg.get("type", "maven"))
        for cid, v in rtags.items():
            d = ac_tags.setdefault(cid, {"green": 0, "red": 0, "cases": []})
            d["green"] += v["green"]
            d["red"] += v["red"]
            d["cases"] = (d["cases"] + v.get("cases", []))[:8]
        stale_reports.extend(rstale)
    stale_reports = sorted(set(stale_reports))

    def _ac_closed(cid):
        d = ac_tags.get(cid)
        return bool(d and d["green"] >= 1 and d["red"] == 0)

    # IDs duplicados (ACCEPTANCE mal numerado) cuentan UNA sola vez — si no,
    # un solo test verde cierra "medido" tantos criterios como copias del ID.
    id_list = [i["id"] for i in ac_ids]
    dupe_ids = sorted({cid for cid in id_list if id_list.count(cid) > 1})
    unique_ids = sorted(set(id_list))
    measured_closed = [cid for cid in unique_ids if _ac_closed(cid)]
    narrated_only = sorted({i["id"] for i in ac_ids
                            if i["checked"] and not _ac_closed(i["id"])})
    measured_unchecked = sorted({i["id"] for i in ac_ids
                                 if not i["checked"] and _ac_closed(i["id"])})
    ac_untagged = total - len(ac_ids)
    acc_traceable = bool(ac_ids)
    if acc_traceable:
        # denominador = TODOS los criterios: uno sin ID no puede cerrar medido
        acc_meas_dim = len(measured_closed) / total if total else 0.0
    else:
        # legacy sin IDs: no hay trazado — cae al ratio de checkboxes (relato)
        # con warning; la adopcion es incremental, no una rotura retroactiva.
        acc_meas_dim = adr_dim

    # config pre-1.10.0 con readiness_weights EXPLICITOS que no conocian la
    # dimension acceptance: si ademas no hay AC-IDs (adopcion no arrancada),
    # inyectar el peso default duplicaria adr (mismo ratio de checkboxes,
    # doble peso) hasta que el usuario elija explicitamente o tagee criterios.
    legacy_weights_cfg = ("readiness_weights" in defaults
                          and "acceptance" not in defaults["readiness_weights"])
    if legacy_weights_cfg and not acc_traceable:
        weights["acceptance"] = 0

    # per-repo readiness
    repos = {n: _repo_readiness(ledger, n, node, weights, caps, zero_at, k)
             for n, node in ledger["repos"].items()}

    # aggregate quality dimensions (LOC-weighted coverage already aggregates in summary)
    agg_cov_c = agg_cov_m = 0
    for n, node in ledger["repos"].items():
        cfg = next((r for r in ledger["config"]["repos"] if r["name"] == n), {})
        c = coverage(cfg.get("path", "."), cfg.get("type", "maven"))
        agg_cov_c += c["covered"]
        agg_cov_m += c["missed"]
    agg_cov_pct = (agg_cov_c / (agg_cov_c + agg_cov_m) * 100) if (agg_cov_c + agg_cov_m) else 0.0
    cov_dim = min(agg_cov_pct / threshold, 1.0) if threshold else 0.0

    total_open = 0
    agg_sev = {}
    for node in ledger["repos"].values():
        go, sev = _gate_open_and_sev(node)
        total_open += go
        for kk, vv in sev.items():
            agg_sev[kk] = agg_sev.get(kk, 0) + vv
    # aggregate static dimension = mean of the per-repo dims, which already encode
    # UNMEASURED (0.0) for a lint-capable repo whose gate never ran — an aggregate
    # 1.0 can no longer be produced by silence.
    static_dims = [r["dims"]["static_gate"] for r in repos.values()]
    static_dim = (sum(static_dims) / len(static_dims)) if static_dims else 0.0
    unmeasured_repos = sorted(n for n, r in repos.items()
                              if r["facts"].get("static_unmeasured"))
    cov_unmeasured_repos = sorted(n for n, r in repos.items()
                                  if r["facts"].get("coverage_unmeasured"))
    dropped_report_repos = sorted(n for n, r in repos.items()
                                  if r["facts"].get("dropped_reports"))

    conv_flags = [r["facts"]["converged"] for r in repos.values()]
    conv_dim = (sum(1 for c in conv_flags if c) / len(conv_flags)) if conv_flags else 0.0

    # integration dimension (feature-level)
    integ_enabled = ledger["config"].get("integration", {}).get("enabled", False)
    integ_steps = [s for s in ledger["integration"]["iterations"]
                   if (s.get("tests_passed") is not None
                       or s.get("gated_reported", 0) > 0)]
    if integ_enabled:
        if integ_steps:
            # kit 1.41.1 (adversarial-review fix): do NOT trust the single last event.
            # A trailing green test-only step must not mask an earlier FAILING integration
            # gate. Green requires (a) 0 open gated findings across the LATEST record per
            # integration tool (so a re-run that clears a gate still counts), AND (b) the
            # latest test-carrying event passed.
            integ_all = ledger["integration"]["iterations"]
            integ_latest_by_tool = {}
            for s in integ_all:
                integ_latest_by_tool[s.get("tool")] = s
            integ_open = sum((v.get("gated_reported", 0) or 0)
                             for v in integ_latest_by_tool.values())
            integ_tests = [s for s in integ_all if s.get("tests_passed") is not None]
            integ_tests_ok = bool(integ_tests) and integ_tests[-1].get("tests_passed") is True
            integ_dim = 1.0 if (integ_open == 0 and integ_tests_ok) else 0.0
        else:
            integ_dim = 0.0  # required but never run
    else:
        integ_dim = None  # excluded, weight redistributed

    dims = {"acceptance": acc_meas_dim, "adr": adr_dim, "coverage": cov_dim,
            "static_gate": static_dim, "convergence": conv_dim}
    if integ_dim is not None:
        dims["integration"] = integ_dim
    wsum = sum(weights[d] for d in dims)
    raw = sum(weights[d] * v for d, v in dims.items()) / wsum * 100 if wsum else 0.0

    # aggregate hard caps = min across repos (any repo trips it -> whole release capped)
    # procedencia (kit 1.17.0, Tip 8 'Make Quality a Requirements Issue'): que el
    # cap EXISTA es principio (tests rojos != ready es definicion, no opinion);
    # el NUMERO es opinion del kit SALVO que el humano lo haya declarado en
    # config.defaults.readiness_caps — el config commiteado ES el acto de
    # declaracion. El output etiqueta cual de las dos cosas mordio.
    declared_caps = set(defaults.get("readiness_caps", {}))
    caps_active = []
    if any(r["facts"]["tests_red"] for r in repos.values()):
        caps_active.append(("tests red in a repo", caps["tests_red"], "tests_red"))
    blk = agg_sev.get("BLOCKER", 0) + agg_sev.get("CRITICAL", 0)
    if blk:
        caps_active.append((f"{blk} BLOCKER/CRITICAL open",
                            caps["blocker_critical"], "blocker_critical"))
    if any(not e.get("resolved_at") for e in ledger.get("escalations", [])):
        caps_active.append(("unresolved escalation", caps["escalation"], "escalation"))
    # AC-FP-06 (ADR-003): an active fast-path run still owes an asserting test. The latest
    # fast_path entry per repo being ALLOW, with NO measured test execution recorded at or
    # after it, caps readiness -- reusing the escalation cap value, per the existing cap
    # mechanics rather than inventing a new one.
    fp_cfg = ledger["config"].get("defaults", {}).get("fast_path")
    if isinstance(fp_cfg, dict) and fp_cfg.get("require_asserting_test", True):
        for _fp_repo in {e.get("repo") for e in ledger.get("fast_path", [])}:
            entries = [e for e in ledger["fast_path"] if e.get("repo") == _fp_repo]
            last = entries[-1] if entries else None
            if not last or last.get("verdict") != "ALLOW":
                continue
            node_fp = ledger["repos"].get(_fp_repo, {})
            tested = any((s.get("tests", {}).get("executed", 0) or 0) > 0
                         and s.get("at", "") >= last.get("at", "")
                         for s in node_fp.get("snapshots", []))
            if not tested:
                caps_active.append(("fast-path active in %s without a measured asserting test"
                                    % _fp_repo, caps["escalation"], "escalation"))
    if spec_doubts_open:
        caps_active.append((f"{len(spec_doubts_open)} spec-doubt open",
                            caps["escalation"], "escalation"))
    if spec_change_requests_open:
        caps_active.append((f"{len(spec_change_requests_open)} spec-change-request open",
                            caps["escalation"], "escalation"))
    if production_gated:
        caps_active.append((f"{len(production_gated)} production finding(s) open",
                            caps["blocker_critical"], "blocker_critical"))
    if not acc_found:
        caps_active.append(("acceptance file not found",
                            caps["blocker_critical"], "blocker_critical"))
    # golden_required (kit 1.45.0, ADR-002): any repo missing an approved golden caps the whole
    # release. A human declaration (via profile or direct config), applied to a measured fact.
    golden_missing_repos = sorted(n for n, r in repos.items()
                                  if r["facts"].get("golden_missing"))
    if golden_missing_repos:
        caps_active.append((f"golden requerido: sin golden aprobado en "
                            f"{', '.join(golden_missing_repos)}",
                            GOLDEN_REQUIRED_CEILING, "golden_required"))
    final, cap_reason = _apply_caps(raw, caps_active)
    cap_key = next((c[2] for c in caps_active if c[0] == cap_reason), None)
    cap_source = None
    if cap_reason:
        if cap_key == "golden_required":
            # provenance is three-way for the golden cap: profile-origin vs explicit config
            profile = defaults.get("risk_profile")
            from_profile = "golden_required" in (defaults.get("_risk_profile_keys") or [])
            cap_source = (f"requerimiento (perfil {profile})"
                          if (from_profile and profile) else "requerimiento (config)")
        else:
            cap_source = ("requerimiento (config)" if cap_key in declared_caps
                          else "default del kit")

    # plateau / stop-signal (ADVISORY: recomienda, jamas gatea)
    qa_order = defaults.get("qa_tools_order")
    stalled_repos = sorted(n for n, node in ledger["repos"].items()
                           if _is_stalled(node, qa_order))
    stop_signal = (bool(conv_flags) and all(conv_flags)
                   and not caps_active and total_open == 0)

    # churn (separate from readiness)
    tool_roll = _tool_rollup(ledger)
    cycles = max([_repo_loop_count(node) for node in ledger["repos"].values()] + [0])
    regressions = sum((s.get("new_regressions") or 0) for node in ledger["repos"].values()
                      for s in node["iterations"])

    # time-lapse (kit 1.32.0, opt-in): --record persiste el readiness del momento en un
    # historial top-level para el mirador. readiness sigue read-only por default; solo
    # hacia adelante (no backfillea). El dashboard lo consume, nunca escribe.
    if getattr(args, "record", False):
        now = _now()
        ledger.setdefault("readiness_history", []).append(
            {"at": now, "score": round(final, 1)})
        # kit 1.46.1: persist a compact MEASURED summary so the statusline (uscha_progress.py)
        # shows MEASURED acceptance -- the same truth this readiness computed -- instead of
        # counting checkboxes (narrated). Write-once/read-many: the fast Stop hook reads this
        # and never re-runs the engine, and can never contradict the ledger it summarizes.
        _closed = set(measured_closed)
        _next = next((i for i in ac_ids if i["id"] not in _closed), None)
        # kit 1.47.0: the loop odometer -- persist per repo the derived phase (FSM 1.18.0),
        # the loop-pass count and the plateau flag. All facts this readiness ALREADY computed;
        # the statusline shows WHERE the method is without re-deriving or running the engine.
        _stalled = set(stalled_repos)
        _odometer = {
            name: {"phase": _derive_phase(ledger, name, node, k, qa_order)[0],
                   "loops": _repo_loop_count(node),
                   "stalled": name in _stalled}
            for name, node in ledger["repos"].items()}
        ledger["measured"] = {
            "at": now, "score": round(final, 1), "band": _band(final),
            "acceptance_done": len(measured_closed), "acceptance_total": total,
            "next": ({"id": _next["id"], "text": _next.get("text", "")} if _next else None),
            "repos": _odometer,
        }
        _save(args.ledger, ledger)

    out = {
        "score": round(final, 1), "raw": round(raw, 1), "status": _band(final),
        "cap_reason": cap_reason, "cap_source": cap_source,
        "thresholds_declared": {
            "readiness_caps": sorted(declared_caps),
            "coverage_threshold": "coverage_threshold" in defaults,
        },
        "weights": {d: weights[d] for d in dims},
        "dimensions": {d: {"raw": round(v, 3),
                           "contribution": round(weights[d] * v / wsum * 100, 1)}
                       for d, v in dims.items()},
        "acceptance": {"done": done, "total": total, "found": acc_found,
                       "file": acc_path, "section": args.section,
                       "traceable": acc_traceable, "ids": len(ac_ids),
                       # kit 1.49.0: per-criterion detail so the mirador can show WHICH
                       # criteria are closed by a green test vs merely ticked. Additive.
                       # kit 1.50.0: each item carries its RECEIPT -- the testcases (name
                       # + report) that back the verdict, capped at 8 by _ac_tags.
                       "items": [{"id": i["id"], "text": i["text"],
                                  "checked": bool(i["checked"]),
                                  "cases": ac_tags.get(i["id"], {}).get("cases", [])}
                                 for i in ac_ids],
                       "untagged": ac_untagged, "duplicate_ids": dupe_ids,
                       "measured_closed": measured_closed,
                       "measured_pct": (round(100.0 * len(measured_closed) / total, 1)
                                        if (acc_traceable and total) else None),
                       "narrated_only": narrated_only,
                       "measured_unchecked": measured_unchecked,
                       "stale_reports": stale_reports},
        "facts": {"coverage_pct": round(agg_cov_pct, 2), "coverage_threshold": threshold,
                  "gated_open": total_open, "severity": agg_sev,
                  "repos_converged": f"{sum(conv_flags)}/{len(conv_flags)}",
                  "static_unmeasured_repos": unmeasured_repos,
                  "coverage_unmeasured_repos": cov_unmeasured_repos,
                  "dropped_report_repos": dropped_report_repos,
                  **({"golden_missing_repos": golden_missing_repos}
                     if golden_missing_repos else {}),
                  "production_findings_open": len(production_open),
                  "spec_doubts_open": len(spec_doubts_open),
                  "spec_change_requests_open": len(spec_change_requests_open)},
        "discovery_intake": discovery_intake,
        "churn": {"max_cycle": cycles, "new_regressions": regressions,
                  "by_tool_fixed_pct": {t: x["fixed_pct"] for t, x in tool_roll.items()}},
        "advice": {"stalled_repos": stalled_repos, "stop_signal": stop_signal},
        "gates": _gate_rollup(ledger),
        "by_repo": repos,
    }
    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return

    cap_str = (f"  (capped at {int(final)}: {cap_reason} — umbral {cap_source})"
               if cap_reason else "")
    print(f"READINESS: {out['score']}/100 — {out['status']}{cap_str}")
    # % TERMINADO que el kit puede firmar: criterios cerrados por test verde /
    # total (MEDIDO, no el ratio de checkboxes). Solo con trazabilidad AC-n;
    # sin ella no hay % honesto que mostrar. Informativo: jamas gatea (kit 1.28.0).
    if acc_traceable and total:
        print(f"  acceptance medido: {out['acceptance']['measured_pct']}% "
              f"({len(measured_closed)}/{total} criteria closed by a green test "
              f"— measured, does not gate)")
    if not acc_found:
        print(f"  ! acceptance file not found: {acc_path or '(unset)'} — ADR dimension = 0")
    if acc_found and not total:
        print(f"  ! acceptance found but 0 criteria in scope "
              f"(--section {args.section!r} matched nothing in the file?) — "
              f"adr/acceptance dimensions at 0")
    if acc_found and total and not acc_traceable:
        print("  ! acceptance has no traceable IDs ('- [ ] AC-01 — ...') — the "
              "acceptance dimension falls back to the checkbox ratio (NARRATED, not measured)")
    if dupe_ids:
        print(f"  ! duplicate IDs in acceptance (normalized): {', '.join(dupe_ids)} "
              f"— each ID counts ONCE in the acceptance dimension")
    if legacy_weights_cfg and not acc_traceable:
        print("  ! config carries explicit readiness_weights from kit <=1.9.0 without "
              "'acceptance' — dimension excluded (weight 0) until you add AC-IDs "
              "or the explicit weight in config.defaults.readiness_weights")
    if narrated_only:
        print(f"  ! narrated-only: {', '.join(narrated_only)} — checkbox ticked "
              f"WITHOUT a green 'AC-n' testcase in the reports (measured beats "
              f"narrated: does NOT close)")
    if measured_unchecked:
        print(f"  · measured but unticked: {', '.join(measured_unchecked)} — there is "
              f"a green testcase; tick the checkbox if the criterion is done")
    if acc_traceable and ac_untagged:
        print(f"  · {ac_untagged} criterion(s) without an AC-ID — cannot close "
              f"MEASURED (they count as open in the acceptance dimension)")
    if unmeasured_repos:
        print(f"  ! static gate NEVER ran in: {', '.join(unmeasured_repos)} — "
              f"dimension scored UNMEASURED (0.0), silence is not success")
    if dropped_report_repos:
        n_dropped = sum(len(repos[r]["facts"]["dropped_reports"]) for r in dropped_report_repos)
        print(f"  ! {n_dropped} test report(s) DROPPED in: {', '.join(dropped_report_repos)} — "
              f"discovered but not usable JUnit; their tests do NOT count. Fix or remove "
              f"them (see stderr for each path and reason)")
    if cov_unmeasured_repos:
        print(f"  ! NO coverage report found in: {', '.join(cov_unmeasured_repos)} — "
              f"coverage scored UNMEASURED (0.0); that is NOT the same fact as a "
              f"measured 0%. Instrument it, or DECLARE the exemption with "
              f"defaults.readiness_weights.coverage = 0 (config = requirement)")
    if stale_reports:
        print(f"  ! {len(stale_reports)} STALE JUnit report(s) discarded "
              f"(code newer than the evidence) — the ACs that relied only "
              f"on them go UNMEASURED; re-run the tests")
    if production_open:
        labels = ", ".join(f"{p.get('id')}({p.get('severity')})" for p in production_open[:3])
        more = "" if len(production_open) <= 3 else f" +{len(production_open)-3} more"
        print(f"  ! production findings open: {labels}{more} -- real field "
              f"feedback; reopen discovery/SPEC in the next cycle")
    if spec_doubts_open:
        labels = ", ".join(f"{s.get('id')}({s.get('kind')}/{s.get('severity')})"
                           for s in spec_doubts_open[:3])
        more = "" if len(spec_doubts_open) <= 3 else f" +{len(spec_doubts_open)-3} more"
        print(f"  ! spec-doubt open: {labels}{more} -- do not code around a "
              f"doubtful SPEC; this needs human review")
    if spec_change_requests_open:
        labels = ", ".join(f"{r.get('id')}({r.get('source')})"
                           for r in spec_change_requests_open[:3])
        more = "" if len(spec_change_requests_open) <= 3 else f" +{len(spec_change_requests_open)-3} more"
        print(f"  ! spec-change-request open: {labels}{more} -- the contract "
              f"needs a human decision and an amended SPEC/ADR")
    if stalled_repos:
        print(f"  ! stall: {', '.join(stalled_repos)} — gated findings flat or "
              f"rising for {STALL_WINDOW} cycles: iterating more is not getting "
              f"closer. Likely a design/SPEC problem — go back to the ADR / "
              f"re-plan with the human (advisory)")
    # rubrica (1.23.0): el ultimo grade por repo, siempre visible — guess
    # estructurado que aconseja; si esta gateado ya bloqueo por el ledger
    for rname, rnode in ledger["repos"].items():
        rub = _latest_static_by_tool(rnode).get("rubric:grade")
        if rub:
            m_ = "!" if rub.get("gated_reported") else "·"
            print(f"  {m_} rubric {rname}: {rub.get('note', 'n/a')}")
    if stop_signal:
        print("  · stop-signal: every repo converged and no blocking fact "
              "remains — what is left is measurable debt (coverage/"
              "acceptance), not findings: a candidate to stop and go to PR (advisory)")
    # veredicto unico (1.25.0, anti-ceremonia): los gates persistidos se colapsan a
    # UNA linea bajo el KPI. El detalle (dimensiones, acceptance, churn, by-repo) es
    # ruido de auditoria en el caso normal -> detras de --verbose. Las lineas de
    # arriba SI se quedan: son condicionales ("habla solo cuando importa").
    gate_roll = out["gates"]
    if gate_roll:
        blocking = [g for g in gate_roll if g["blocking"]]
        n_ok = len(gate_roll) - len(blocking)
        hint = "" if args.verbose else "   (readiness --verbose for the detail)"
        if blocking:
            names = ", ".join(f"{g['repo']}/{g['tool']}" for g in blocking)
            print(f"--- gates: {n_ok} ok · {len(blocking)} blocking ({names}){hint}")
        else:
            print(f"--- gates: {n_ok} ok, none blocking{hint}")
    if not args.verbose:
        return
    print("--- dimensions (weight | raw | contribution) ---")
    for d in dims:
        print(f"  {d:13s} {weights[d]:3d} | {dims[d]:.2f} | "
              f"{out['dimensions'][d]['contribution']:5.1f}")
    acc_str = (f"medida {len(measured_closed)}/{total}" if acc_traceable
               else "sin trazar")
    thr_src = ("declarado" if "coverage_threshold" in defaults else "default del kit")
    print(f"--- acceptance: {done}/{total} tasks ({acc_str})   "
          f"coverage: {round(agg_cov_pct,1)}% (thr {threshold}, {thr_src})   "
          f"gated open: {total_open}   converged: {sum(conv_flags)}/{len(conv_flags)}")
    print(f"--- churn (not readiness): max cycle {cycles}, "
          f"regressions {regressions}")
    print("--- by repo (score / status / cap) ---")
    for r, x in repos.items():
        print(f"  {r:13s} {x['score']:5.1f}  {x['status']:18s} "
              f"{('cap: ' + x['cap_reason']) if x['cap_reason'] else ''}")


# --------------------------------------------------------------------------- #
# rebuild test: completeness of the SPEC (not correctness of the build)
# --------------------------------------------------------------------------- #
# The rebuild test answers a DIFFERENT question than the ledger: not "did this
# build pass?" (correctness) but "is the SPEC complete enough to regenerate the
# system from scratch?" (completeness).
#
# This script cannot regenerate code — that is the dev-loop skill's job. It only
# MEASURES, PERSISTS and SCORES. The workflow:
#
#   1. On the ORIGINAL tree:
#        qa_ledger.py rebuild --mode baseline --config uscha.config.json
#      -> writes REBUILD-BASELINE.json: the signature the rebuilt system must match
#         (coverage, test totals/results, prod/test LOC, the test-file set to
#         preserve, acceptance done/total).
#   2. The agent regenerates PRODUCTION code from SPEC/ADR/ACCEPTANCE only (fresh
#      session / clean tree), PRESERVING the original test suite, then runs the
#      tests so the reports are written.
#   3. On the REBUILT tree:
#        qa_ledger.py rebuild --mode compare --baseline REBUILD-BASELINE.json
#      -> emits  REBUILD: NN/100 — COVERS|PARTIAL|DIVERGE  + the specific gaps.
#
# The dominant signal is the preserved suite: if regenerated production code fails
# tests the original passed, the SPEC left behavior implicit. Coverage and LOC
# deltas are secondary completeness hints, not a semantic diff.

DEFAULT_REBUILD_BASELINE = "REBUILD-BASELINE.json"
REBUILD_WEIGHTS = {"tests": 60, "acceptance": 20, "coverage": 15, "surface": 5}
REBUILD_BANDS = [(90, "COVERS"), (70, "PARTIAL"), (0, "DIVERGE")]
DEFAULT_COVERAGE_TOLERANCE = 5.0  # pct points the rebuilt coverage may drop

# --------------------------------------------------------------------------- #
# simplicity (the "Reduce" invariant): DETERMINISTIC proxies over a unified diff.
# This is NOT AST cyclomatic complexity — it is diff size, indentation depth and
# a declaration regex. Honest proxies for "would a senior say this is overbuilt?"
# --------------------------------------------------------------------------- #
# abstraction is INTENTIONALLY not weighted: the "new types" regex is a prose/AST proxy
# that false-positives on Java records/DTOs, so it must not gate the band. It stays as an
# advisory metric + flag only (distilled: hard caps gate, guessy proxies advise).
SIMPLICITY_WEIGHTS = {
    "diff_size": 35, "nesting": 30, "net_growth": 20, "fan_out": 8, "blob": 7,
}
SIMPLICITY_BANDS = [(85, "SIMPLE"), (65, "ACCEPTABLE"), (0, "OVERBUILT")]
SIMPLICITY_DEFAULTS = {
    "max_lines_added": 400,
    "max_net_lines": 300,
    "max_files_changed": 20,
    "max_nesting_depth": 4,
    "max_hunk_added": 120,
    "max_new_abstractions": 8,
    "max_abstraction_density": 3.0,   # new *types* per 100 added LOC
    "indent_width": 4,
}
# code files only — docs, config, resources and generated trees are noise for a
# code-simplicity gate. Broader than SOURCE_EXT (which is repo-typed for rebuild).
_SIMPLICITY_CODE_EXT = {
    ".java", ".kt", ".kts", ".dart", ".py", ".ts", ".tsx", ".js", ".jsx", ".mjs",
    ".go", ".rs", ".rb", ".cs", ".c", ".h", ".cpp", ".cc", ".hpp", ".m", ".mm",
    ".scala", ".swift", ".php", ".vue", ".svelte",
}
# "abstractions" = new types/layers (the speculative-generality smell), NOT funcs.
_ABSTRACTION_RE = re.compile(
    r"^(?:export\s+|default\s+|public\s+|private\s+|protected\s+|internal\s+|"
    r"static\s+|final\s+|abstract\s+|sealed\s+|open\s+|data\s+)*"
    r"(?:class|interface|trait|struct|enum|protocol|record|module|namespace)\b"
)
_FUNC_RE = re.compile(
    r"^(?:export\s+|default\s+|public\s+|private\s+|protected\s+|internal\s+|"
    r"static\s+|final\s+|abstract\s+|async\s+|suspend\s+|override\s+)*"
    r"(?:def|function|func|fun)\b"
)


def _simplicity_band(score):
    for floor, label in SIMPLICITY_BANDS:
        if score >= floor:
            return label
    return "OVERBUILT"


def _rebuild_band(score):
    for floor, label in REBUILD_BANDS:
        if score >= floor:
            return label
    return "DIVERGE"


def _test_file_set(repo_path, repo_type):
    """Relative paths of test files — the suite the rebuild must preserve."""
    exts = SOURCE_EXT.get(repo_type, SOURCE_EXT["generic"])
    files = []
    for dirpath, dirnames, filenames in os.walk(repo_path):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS
                    and not d.startswith("cmake-build-")]
        for fn in filenames:
            if os.path.splitext(fn)[1] not in exts:
                continue
            if _reserved_name(fn):
                continue
            rel = os.path.relpath(os.path.join(dirpath, fn), repo_path).replace("\\", "/")
            if _is_test_path(rel, repo_type):
                files.append(rel)
    return sorted(files)


def _repo_signature(cfg, acc_path, section):
    """Deterministic completeness signature of a repo's current tree."""
    path, rtype = cfg["path"], cfg["type"]
    cov = coverage(path, rtype)
    tc = test_count(path, rtype)
    loc = count_loc(path, rtype)
    done, total, found = _parse_acceptance(acc_path, section)
    return {
        "coverage_pct": cov["pct"], "coverage_report_found": cov["report_found"],
        "tests": {"total": tc["total"], "passed": tc["passed"],
                  "failures": tc.get("failures", 0), "errors": tc.get("errors", 0),
                  "report_found": tc["report_found"],
                  "approximate": tc.get("approximate", False)},
        "loc": {"prod": loc["prod_loc"], "test": loc["test_loc"],
                "prod_files": loc["prod_files"], "test_files": loc["test_files"]},
        "test_file_set": _test_file_set(path, rtype),
        "acceptance": {"done": done, "total": total, "found": found},
    }


def cmd_rebuild(args):
    if args.mode == "baseline":
        return _rebuild_baseline(args)
    return _rebuild_compare(args)


def _rebuild_baseline(args):
    cfg = _load(args.config)
    defaults = cfg.get("defaults", {})
    acc_default = args.acceptance or defaults.get("acceptance_file")
    tol = (args.coverage_tolerance if args.coverage_tolerance is not None
           else defaults.get("rebuild", {}).get("coverage_tolerance",
                                                DEFAULT_COVERAGE_TOLERANCE))
    base = {
        "schema": "dev-loop/rebuild-baseline@1",
        "created_at": _now(),
        "config_repos": cfg.get("repos", []),
        "coverage_tolerance": tol,
        "acceptance_file": acc_default,
        "section": args.section,
        "repos": {r["name"]: _repo_signature(r, acc_default, args.section)
                  for r in cfg.get("repos", [])},
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(base, fh, indent=2, ensure_ascii=False)
    print(f"[qa_ledger] rebuild baseline written to {args.out} "
          f"({len(base['repos'])} repos, coverage_tolerance={tol}).")
    print("[qa_ledger] next: in a CLEAN tree, regenerate PRODUCTION code from "
          "SPEC/ADR/ACCEPTANCE only (preserve the tests), run the suite, then "
          "`rebuild --mode compare`.")


def _rebuild_compare(args):
    base = _load(args.baseline)
    tol = base.get("coverage_tolerance", DEFAULT_COVERAGE_TOLERANCE)
    acc_path = args.acceptance or base.get("acceptance_file")
    section = args.section if args.section is not None else base.get("section")
    repos_cfg = {r["name"]: r for r in base.get("config_repos", [])}

    per_repo = {}
    gaps = []
    dim_scores = {"tests": [], "acceptance": [], "coverage": [], "surface": []}

    for name, sig0 in base["repos"].items():
        cfg = repos_cfg.get(name)
        if not cfg:
            continue
        sig1 = _repo_signature(cfg, acc_path, section)

        # tests (dominant): the preserved suite must still pass on regenerated code
        t0, t1 = sig0["tests"], sig1["tests"]
        if not t1["report_found"]:
            tests_dim = 0.0
            gaps.append(f"{name}: no test report after rebuild "
                        f"(suite not run, or tests not preserved)")
        elif (t1["failures"] + t1["errors"]) > 0:
            tests_dim = (t1["passed"] / t1["total"]) if t1["total"] else 0.0
            gaps.append(f"{name}: {t1['failures'] + t1['errors']} test(s) fail on "
                        f"regenerated code — behavior the SPEC left implicit")
        else:
            ratio = (t1["total"] / t0["total"]) if t0["total"] else 1.0
            tests_dim = min(1.0, ratio)
            if t0["total"] and ratio < 0.9:
                gaps.append(f"{name}: rebuilt suite has {t1['total']} tests vs "
                            f"{t0['total']} baseline — fewer behaviors exercised")

        # acceptance
        a0, a1 = sig0["acceptance"], sig1["acceptance"]
        if a1["found"] and a1["total"]:
            acc_dim = a1["done"] / a1["total"]
            if a1["done"] < a1["total"]:
                gaps.append(f"{name}: acceptance {a1['done']}/{a1['total']} after rebuild")
        else:
            acc_dim = 1.0 if not a0["found"] else 0.0

        # coverage (within tolerance)
        c0, c1 = sig0["coverage_pct"], sig1["coverage_pct"]
        if not sig1["coverage_report_found"]:
            cov_dim = 0.0
        elif c1 + tol >= c0:
            cov_dim = 1.0
        else:
            cov_dim = max(0.0, c1 / c0) if c0 else 1.0
            gaps.append(f"{name}: coverage {c1}% vs baseline {c0}% (tolerance {tol})")

        # surface: prod-LOC proportion — a coarse "same amount of system?" hint
        p0, p1 = sig0["loc"]["prod"], sig1["loc"]["prod"]
        surf_dim = max(0.0, 1 - abs(p1 - p0) / p0) if p0 else 1.0

        for k, v in (("tests", tests_dim), ("acceptance", acc_dim),
                     ("coverage", cov_dim), ("surface", surf_dim)):
            dim_scores[k].append(v)
        per_repo[name] = {
            "tests": round(tests_dim, 3), "acceptance": round(acc_dim, 3),
            "coverage": round(cov_dim, 3), "surface": round(surf_dim, 3),
            "baseline": sig0, "rebuilt": sig1,
        }

    def _avg(xs):
        return sum(xs) / len(xs) if xs else 0.0

    dims = {k: _avg(v) for k, v in dim_scores.items()}
    wsum = sum(REBUILD_WEIGHTS.values())
    score = (sum(REBUILD_WEIGHTS[k] * dims[k] for k in REBUILD_WEIGHTS) / wsum * 100
             if wsum else 0.0)
    score = round(score, 1)
    verdict = _rebuild_band(score)

    out = {
        "score": score, "verdict": verdict, "weights": REBUILD_WEIGHTS,
        "dimensions": {k: round(v, 3) for k, v in dims.items()},
        "coverage_tolerance": tol, "gaps": gaps, "by_repo": per_repo,
    }
    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
        sys.exit(0 if verdict == "COVERS" else 1)
    print(f"REBUILD: {score}/100 — {verdict}")
    print("--- dimensions (weight | score) ---")
    for k in REBUILD_WEIGHTS:
        print(f"  {k:11s} {REBUILD_WEIGHTS[k]:3d} | {dims[k]:.2f}")
    if gaps:
        print("--- gaps (the SPEC's implicit decisions) ---")
        for g in gaps:
            print(f"  ! {g}")
    else:
        print("  no gaps detected — the SPEC regenerates the system within tolerance")
    sys.exit(0 if verdict == "COVERS" else 1)


# --------------------------------------------------------------------------- #
# simplicity-check  (the "Reduce" gate)
# --------------------------------------------------------------------------- #
def _read_diff(args):
    """Unified-diff text from --diff, --from-git, or stdin."""
    if getattr(args, "diff", None):
        with open(args.diff, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    if getattr(args, "from_git", False):
        import subprocess
        base = args.base or "HEAD"
        try:
            return subprocess.run(
                ["git", "diff", "--unified=0", base],
                check=True, capture_output=True, text=True,
                encoding="utf-8", errors="replace").stdout
        except Exception as exc:  # noqa: BLE001
            print(f"[qa_ledger] git diff failed: {exc}", file=sys.stderr)
            sys.exit(2)
    data = sys.stdin.read()
    if not data.strip():
        print("[qa_ledger] no diff on stdin; use --diff PATH or --from-git.",
              file=sys.stderr)
        sys.exit(2)
    return data


def _indent_level(text, indent_width):
    cols = 0
    for ch in text:
        if ch == " ":
            cols += 1
        elif ch == "\t":
            cols += indent_width
        else:
            break
    return cols // max(1, indent_width)


# Narrower than SKIP_DIRS on purpose: only UNAMBIGUOUS build/VCS/generated output.
# `bin`/`out`/`dist`/`generated` are dropped — they are also legitimate package names
# (e.g. src/.../generated/Foo.java), and JVM/Dart build output (.class/.jar/.dex) never
# matches _SIMPLICITY_CODE_EXT. Known limit: a committed JS bundle under dist/ (.js IS in
# the allowlist) WOULD count — this gate targets JVM/Dart repos, not JS.
_SIMPLICITY_SKIP = {"target", "build", "node_modules", ".git", ".gradle",
                    ".idea", ".mvn", ".dart_tool", "generated-sources"}


def _is_simplicity_code_file(rel):
    """Only real source files count toward the budget — docs, config, resources
    and build/generated trees are noise for a code-simplicity gate."""
    p = rel.replace("\\", "/")
    if any(seg in _SIMPLICITY_SKIP for seg in p.split("/")):
        return False
    return os.path.splitext(p)[1].lower() in _SIMPLICITY_CODE_EXT


def _is_simplicity_test_file(rel):
    """Tests FUERA del presupuesto de simplicity (Topic 51: 'un buen proyecto
    puede tener MAS codigo de test que de produccion'): si el presupuesto los
    cuenta junto a produccion, el gate castiga escribir tests — incentivo
    perverso directo contra el corazon del kit. Se cuentan y REPORTAN aparte.

    Type-agnostico (el diff no trae repo_type): union de las convenciones de
    _is_test_path para los 9 stacks. Direccion de fallo benigna: un falso
    positivo solo EXIME del presupuesto (borrar tests lo bloquea gate-check,
    no este gate); CamelCase case-sensitive como dotnet/cpp para no tragar
    backtest.cpp/protest.cpp."""
    p = rel.replace("\\", "/")
    parts = p.split("/")
    fn = parts[-1]
    dirs = parts[:-1]
    if any(d in ("test", "tests", "__tests__", "Tests") or d.endswith(".Tests")
           for d in dirs):
        return True
    # gradle source sets custom: src/integrationTest/, src/functionalTest/...
    for i, d in enumerate(dirs):
        if d == "src" and i + 1 < len(dirs) and dirs[i + 1].endswith("Test"):
            return True
    base, _ = os.path.splitext(fn)
    low = base.lower()
    segs = fn.lower().split(".")
    return (low.startswith("test_") or low.endswith(("_test", "_tests"))
            or base.endswith(("Test", "Tests"))
            or (len(segs) >= 3 and segs[-2] in ("test", "spec")))  # foo.test.ts / a.b.spec.js


def _simplicity_metrics(diff_text, indent_width):
    # Expects GIT-format diffs (a `diff --git` line per file — as produced by `git diff`
    # and the --from-git path). A plain POSIX `diff -u`/`svn diff` WITHOUT those headers
    # miscounts files after the first (their `--- `/`+++ ` headers get read as hunk body).
    # Feed git diffs, not raw POSIX diffs. [judgment-day R2 / B1: documented limitation]
    files, test_files, skipped = set(), set(), set()
    added, removed = 0, 0
    test_added, test_removed = 0, 0
    max_nesting, new_types, new_funcs = 0, 0, 0
    hunk_added, max_hunk_added = 0, 0
    counting = None    # 'prod' gatea | 'test' se cuenta aparte | None fuera
    in_hunk = False    # inside a hunk body? file headers only appear before the first @@
    for raw in diff_text.splitlines():
        if raw.startswith("diff --git"):
            in_hunk = False
            counting = None
            continue
        if raw.startswith("@@"):
            in_hunk = True
            max_hunk_added = max(max_hunk_added, hunk_added)
            hunk_added = 0
            continue
        if not in_hunk:
            # file preamble — only the +++ header carries the path we gate on
            if raw.startswith("+++ "):
                path = raw[4:].strip().split("\t")[0]
                if path == "/dev/null":
                    counting = None
                else:
                    rel = path[2:] if path[:2] in ("a/", "b/") else path
                    if not _is_simplicity_code_file(rel):
                        counting = None
                        skipped.add(rel)
                    elif _is_simplicity_test_file(rel):
                        # tests fuera del presupuesto (Topic 51): contados y
                        # reportados, nunca gateados — el gate no debe castigar
                        # escribir tests (gate-check ya bloquea borrarlos).
                        counting = "test"
                        test_files.add(rel)
                    else:
                        counting = "prod"
                        files.add(rel)
            continue
        # inside a hunk body: +/- lines are content. A source line `++ x` shows up as
        # `+++ x` here but is correctly a body add (not a header) because in_hunk is True.
        if counting is None:
            continue
        if counting == "test":
            if raw.startswith("+"):
                test_added += 1
            elif raw.startswith("-"):
                test_removed += 1
            continue
        if raw.startswith("+"):
            added += 1
            hunk_added += 1
            body = raw[1:]
            stripped = body.strip()
            if stripped:
                max_nesting = max(max_nesting, _indent_level(body, indent_width))
                if _ABSTRACTION_RE.match(stripped):
                    new_types += 1
                elif _FUNC_RE.match(stripped):
                    new_funcs += 1
        elif raw.startswith("-"):
            removed += 1
    max_hunk_added = max(max_hunk_added, hunk_added)
    density = (new_types / (added / 100.0)) if added else 0.0
    return {
        "files_changed": len(files),
        "files_skipped": len(skipped),
        "lines_added": added,
        "lines_removed": removed,
        "net_lines": added - removed,
        "max_nesting": max_nesting,
        "new_abstractions": new_types,
        "new_functions": new_funcs,
        "max_hunk_added": max_hunk_added,
        "abstraction_density": round(density, 2),
        "test_files_changed": len(test_files),
        "test_lines_added": test_added,
        "test_lines_removed": test_removed,
    }


def _adherence(value, budget):
    """1.0 within budget; linear to 0.0 at 2x budget."""
    if budget <= 0:
        return 1.0
    if value <= budget:
        return 1.0
    return max(0.0, 1.0 - (value - budget) / budget)


def _simplicity_score(m, b):
    dims = {
        "diff_size": _adherence(m["lines_added"], b["max_lines_added"]),
        "net_growth": _adherence(max(0, m["net_lines"]), b["max_net_lines"]),
        "nesting": _adherence(m["max_nesting"], b["max_nesting_depth"]),
        "abstraction": min(
            _adherence(m["new_abstractions"], b["max_new_abstractions"]),
            _adherence(m["abstraction_density"], b["max_abstraction_density"]),
        ),
        "fan_out": _adherence(m["files_changed"], b["max_files_changed"]),
        "blob": _adherence(m["max_hunk_added"], b["max_hunk_added"]),
    }
    wsum = sum(SIMPLICITY_WEIGHTS.values())
    score = (sum(SIMPLICITY_WEIGHTS[k] * dims[k] for k in SIMPLICITY_WEIGHTS)
             / wsum * 100) if wsum else 0.0
    # hard cap: a single gross overbuild can't be masked by the rest
    crit = (
        m["lines_added"] > 2 * b["max_lines_added"]
        or m["net_lines"] > 2 * b["max_net_lines"]
        or m["files_changed"] > 2 * b["max_files_changed"]
        or m["max_hunk_added"] > 2 * b["max_hunk_added"]
        or m["max_nesting"] > b["max_nesting_depth"] + 3
    )
    if crit:
        score = min(score, 60.0)
    # min-floor for the HEAVY dims: a diff >1.5x over the size/growth budget must not
    # average into ACCEPTABLE just because the cheap structural dims are green.
    # (Same discipline the abstraction dim already applies via min().)
    if dims["diff_size"] < 0.5 or dims["net_growth"] < 0.5:
        score = min(score, 60.0)
    return round(score, 1), dims


def _simplicity_flags(m, b):
    f = []
    if m["max_nesting"] > b["max_nesting_depth"]:
        f.append(f"nesting {m['max_nesting']} > {b['max_nesting_depth']} — "
                 f"aplanar: guard clauses / extraer función (CWE-1124)")
    if m["new_abstractions"] > b["max_new_abstractions"]:
        f.append(f"{m['new_abstractions']} tipos/capas nuevos > "
                 f"{b['max_new_abstractions']} — ¿todos pedidos? "
                 f"(YAGNI / generalidad especulativa)")
    if m["abstraction_density"] > b["max_abstraction_density"]:
        f.append(f"densidad {m['abstraction_density']}/100 LOC > "
                 f"{b['max_abstraction_density']} — mucha abstracción por línea útil")
    if m["lines_added"] > b["max_lines_added"]:
        f.append(f"+{m['lines_added']} líneas > {b['max_lines_added']} — "
                 f"¿el cambio es más chico que esto?")
    if m["net_lines"] > b["max_net_lines"]:
        f.append(f"crecimiento neto +{m['net_lines']} > {b['max_net_lines']} — "
                 f"restar antes de sumar")
    if m["max_hunk_added"] > b["max_hunk_added"]:
        f.append(f"hunk de +{m['max_hunk_added']} > {b['max_hunk_added']} — "
                 f"un bloque gigante; partir en piezas legibles")
    if m["files_changed"] > b["max_files_changed"]:
        f.append(f"{m['files_changed']} archivos > {b['max_files_changed']} — "
                 f"cambio disperso; ¿una sola responsabilidad?")
    return f


def cmd_simplicity_check(args):
    b = dict(SIMPLICITY_DEFAULTS)
    declared = set()   # presupuestos declarados por el humano (config o CLI)
    if args.config and os.path.exists(args.config):
        cfg = _load(args.config).get("defaults", {}).get("simplicity", {})
        b.update({k: cfg[k] for k in b if k in cfg})
        declared |= {k for k in b if k in cfg and k != "indent_width"}
    for k in ("max_lines_added", "max_net_lines", "max_files_changed",
              "max_nesting_depth", "max_hunk_added", "max_new_abstractions",
              "indent_width"):
        v = getattr(args, k, None)
        if v is not None:
            b[k] = v
            if k != "indent_width":   # parametro de parseo, no un presupuesto
                declared.add(k)
    if args.max_abstraction_density is not None:
        b["max_abstraction_density"] = args.max_abstraction_density
        declared.add("max_abstraction_density")

    m = _simplicity_metrics(_read_diff(args), b["indent_width"])
    score, dims = _simplicity_score(m, b)
    verdict = _simplicity_band(score)
    flags = _simplicity_flags(m, b)

    out = {"score": score, "verdict": verdict, "weights": SIMPLICITY_WEIGHTS,
           "dimensions": {k: round(v, 3) for k, v in dims.items()},
           "metrics": m, "budgets": b, "budgets_declared": sorted(declared),
           "flags": flags}
    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
        sys.exit(0 if verdict != "OVERBUILT" else 1)

    print(f"SIMPLICITY: {score}/100 — {verdict}")
    print("--- metrics (value / budget · * = declared by the human) ---")
    rows = [
        ("lines_added", m["lines_added"], b["max_lines_added"], "max_lines_added"),
        ("net_lines", m["net_lines"], b["max_net_lines"], "max_net_lines"),
        ("files_changed", m["files_changed"], b["max_files_changed"], "max_files_changed"),
        ("max_nesting", m["max_nesting"], b["max_nesting_depth"], "max_nesting_depth"),
        ("new_abstractions", m["new_abstractions"], b["max_new_abstractions"], "max_new_abstractions"),
        ("abstraction/100", m["abstraction_density"], b["max_abstraction_density"], "max_abstraction_density"),
        ("max_hunk_added", m["max_hunk_added"], b["max_hunk_added"], "max_hunk_added"),
    ]
    for name, val, bud, key in rows:
        mark = "*" if key in declared else ""
        print(f"  {name:17s} {str(val):>7s} / {bud}{mark}")
    if not declared:
        print("  (every budget is a kit default — an opinion, not a "
              "requirement: declare yours in config.defaults.simplicity)")
    print(f"  (new_functions: {m['new_functions']} — informational, not gated)")
    if m.get("test_files_changed"):
        print(f"  (tests OUTSIDE the budget: +{m['test_lines_added']} lines "
              f"in {m['test_files_changed']} test file(s) — writing tests "
              f"never penalizes this gate)")
    if m.get("files_skipped"):
        print(f"  ({m['files_skipped']} non-code file(s) skipped: docs/config/resources)")
    if flags:
        print("--- flags (Reduce: what to cut) ---")
        for fl in flags:
            print(f"  ! {fl}")
    else:
        print("  within budget — nothing to cut")
    sys.exit(0 if verdict != "OVERBUILT" else 1)


# --------------------------------------------------------------------------- #
# pit-check  (mutation testing: test EFFECTIVENESS, because coverage lies)
# --------------------------------------------------------------------------- #
# Coverage says a line RAN; mutation testing says a test would CATCH it changing.
# Ingests a PIT (pitest) mutations.xml. stdlib only. exit 0 = PASS, 1 = below gate.
_PIT_KILLED = {"KILLED", "TIMED_OUT", "MEMORY_ERROR"}
# Excluded from the score entirely: NON_VIABLE (mutant did not compile — PIT itself
# drops it) and RUN_ERROR (infra failure, not a test-quality signal). Counting either
# as a survivor inflates the denominator and can flip the gate to a false BELOW-GATE.
_PIT_EXCLUDED = {"NON_VIABLE", "RUN_ERROR"}


def _find_pit_report(path_arg):
    """Explicit --report, else the newest target/pit-reports/*/mutations.xml."""
    if path_arg:
        return path_arg
    hits = glob.glob(os.path.join("target", "pit-reports", "*", "mutations.xml"))
    if not hits:
        hits = glob.glob(os.path.join("**", "pit-reports", "**", "mutations.xml"),
                         recursive=True)
    return max(hits, key=os.path.getmtime) if hits else None


def _pit_metrics(xml_path):
    root = _parse_xml(xml_path).getroot()
    total = killed = survived = no_cov = excluded = 0
    by_file = {}
    for mut in root.iter("mutation"):
        status = (mut.get("status") or "").upper()
        if status in _PIT_EXCLUDED:   # NON_VIABLE / RUN_ERROR: out of the denominator
            excluded += 1
            continue
        total += 1
        detected = (mut.get("detected") or "").lower() == "true"
        src = (mut.findtext("sourceFile") or "?").strip()
        if detected or status in _PIT_KILLED:
            killed += 1
            continue
        slot = by_file.setdefault(src, {"survived": 0, "no_coverage": 0})
        if status == "NO_COVERAGE":
            no_cov += 1
            slot["no_coverage"] += 1
        else:  # SURVIVED
            survived += 1
            slot["survived"] += 1
    covered = killed + survived
    return {
        "total": total, "killed": killed, "survived": survived, "no_coverage": no_cov,
        "excluded": excluded,
        # mutation_score = killed / total (the conventional PIT number, NON_VIABLE excluded)
        "mutation_score": round(100.0 * killed / total, 1) if total else 100.0,
        # test_strength = killed / covered — the honest "do the tests ASSERT?" signal
        "test_strength": round(100.0 * killed / covered, 1) if covered else 100.0,
        "by_file": by_file,
    }


# --------------------------------------------------------------------------- #
# waste-check (the "REUSE-FIRST" invariant, kit 1.26.0): DETERMINISTIC Type-1/Type-2
# clone detection over the diff vs the repo — the muda `simplicity-check` cannot see,
# because it scores the diff in ISOLATION and never looks at what already exists.
# --------------------------------------------------------------------------- #
# HONEST SCOPE: a Type-1/Type-2 proxy over NORMALIZED lines (strip + collapse
# whitespace, drop comment-only), NOT semantic clone detection (Type-3/4) nor AST.
# It reports a FACT (a byte-identical window of code exists elsewhere) but the VERDICT
# "wasteful" is a heuristic with known false positives (boilerplate, DTOs, embedded
# SQL/JSON). That is exactly why it is ADVISORY by default and gates ONLY when the
# human declares it (`defaults.waste.gate: true` or `--gate`) — a natural-language-ish
# gate that blocks on false positives gets disabled and dies (anti-ceremony rule 2).
WASTE_WEIGHTS = {"repo_reuse": 55, "internal_dup": 45}
WASTE_BANDS = [(85, "LEAN"), (65, "ACCEPTABLE"), (0, "WASTEFUL")]
WASTE_DEFAULTS = {
    "window_size": 5,               # GitClear def.: "5+ significant lines repeated"
    "max_dup_windows_vs_repo": 0,   # budget for the score/cap; 0 = any repo clone is noteworthy
    "max_dup_ratio": 0.10,          # dup_vs_repo / added_windows before the 2x hard cap bites
    "min_line_len": 8,              # a normalized line shorter than this is not "significant"
    "allow_paths": [],              # substrings to exclude (migrations/, generated/, *_pb2...)
    "gate": False,                  # advisory-first: WASTEFUL blocks ONLY when declared
}
_WASTE_COMMENT = ("//", "#", "*", "--", "/*", "*/", '"""', "'''", ";;", "<!--")


def _waste_band(score):
    for floor, label in WASTE_BANDS:
        if score >= floor:
            return label
    return "WASTEFUL"


def _path_allowed(rel, allow_paths):
    r = rel.replace("\\", "/")
    return any(sub and sub in r for sub in allow_paths)


def _waste_norm(body, min_line_len):
    """Normalize a source line to its Type-1/Type-2 form, or None if not significant.
    Same normalization is applied to BOTH the diff's added lines and the repo files,
    so a byte-identical block hashes identically on both sides."""
    s = " ".join(body.split())               # strip + collapse internal whitespace
    if len(s) < min_line_len:
        return None
    if s.startswith(_WASTE_COMMENT):
        return None
    if not re.search(r"[A-Za-z_]\w*", s):     # pure punctuation / lone braces do not count
        return None
    return s


def _waste_hashes(norm_lines, W):
    """(start_index, sha1) for each window of W consecutive normalized lines."""
    out = []
    for i in range(len(norm_lines) - W + 1):
        h = hashlib.sha1("\n".join(norm_lines[i:i + W]).encode("utf-8")).hexdigest()
        out.append((i, h))
    return out


def _waste_added_by_file(diff_text, min_line_len, allow_paths):
    """Added, normalized significant lines per PRODUCTION code file, plus the set of
    files the diff touches (so the repo scan can exclude them and not match a clone to
    itself). Tests and non-code files are excluded, as in simplicity-check."""
    by_file, touched = {}, set()
    counting, in_hunk = None, False
    for raw in diff_text.splitlines():
        if raw.startswith("diff --git"):
            in_hunk, counting = False, None
            continue
        if raw.startswith("@@"):
            in_hunk = True
            continue
        if not in_hunk:
            if raw.startswith("+++ "):
                path = raw[4:].strip().split("\t")[0]
                if path == "/dev/null":
                    counting = None
                else:
                    rel = path[2:] if path[:2] in ("a/", "b/") else path
                    touched.add(rel.replace("\\", "/"))
                    if (_is_simplicity_code_file(rel)
                            and not _is_simplicity_test_file(rel)
                            and not _path_allowed(rel, allow_paths)):
                        counting = rel.replace("\\", "/")
                        by_file.setdefault(counting, [])
                    else:
                        counting = None
            continue
        if counting is None:
            continue
        if raw.startswith("+"):
            norm = _waste_norm(raw[1:], min_line_len)
            if norm is not None:
                by_file[counting].append(norm)
    return by_file, touched


def _waste_repo_hashes(repo_root, touched, W, min_line_len, allow_paths):
    """hash -> 'rel:line' (first window seen) over every code file in the repo EXCEPT
    the touched files (self-match) and allow-listed paths."""
    seen = {}
    for dirpath, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = [d for d in dirnames
                       if d not in SKIP_DIRS and d not in _SIMPLICITY_SKIP]
        for fn in filenames:
            if _reserved_name(fn):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, repo_root).replace("\\", "/")
            if (rel in touched or not _is_simplicity_code_file(rel)
                    or _is_simplicity_test_file(rel)
                    or _path_allowed(rel, allow_paths)):
                continue
            try:
                with open(full, "r", encoding="utf-8", errors="replace") as fh:
                    raw_lines = fh.read().splitlines()
            except OSError:
                continue
            norm, mapping = [], []
            for lineno, rl in enumerate(raw_lines, 1):
                n = _waste_norm(rl, min_line_len)
                if n is not None:
                    norm.append(n)
                    mapping.append(lineno)
            for i, h in _waste_hashes(norm, W):
                seen.setdefault(h, f"{rel}:{mapping[i]}")
    return seen


def _waste_metrics(diff_text, repo_root, b):
    W, mll, allow = b["window_size"], b["min_line_len"], b["allow_paths"]
    by_file, touched = _waste_added_by_file(diff_text, mll, allow)
    added_windows, counts = [], {}
    sig_lines, call_lines = 0, 0
    for rel, lines in by_file.items():
        sig_lines += len(lines)
        for l in lines:
            if re.search(r"[A-Za-z_]\w*\s*\(", l):
                call_lines += 1
        for i, h in _waste_hashes(lines, W):
            added_windows.append((rel, i, h))
            counts[h] = counts.get(h, 0) + 1
    total = len(added_windows)
    dup_internal = sum(1 for _, _, h in added_windows if counts[h] > 1)
    repo_hashes = _waste_repo_hashes(repo_root, touched, W, mll, allow) if repo_root else {}
    vs_repo = [(rel, i, h) for (rel, i, h) in added_windows if h in repo_hashes]
    examples, seen_ex = [], set()
    for rel, _i, h in vs_repo:
        if h not in seen_ex:
            seen_ex.add(h)
            examples.append({"added_in": rel, "clone_of": repo_hashes[h]})
    return {
        "added_windows": total,
        "sig_lines_added": sig_lines,
        "dup_windows_internal": dup_internal,
        "dup_windows_vs_repo": len(vs_repo),
        "dup_ratio": round(len(vs_repo) / total, 3) if total else 0.0,
        "call_density": round(100.0 * call_lines / sig_lines, 1) if sig_lines else 0.0,
        "files_added_to": len(by_file),
        "examples_vs_repo": examples[:5],
    }


def _waste_score(m, b):
    total = m["added_windows"]
    reuse = 1.0 - min(1.0, m["dup_windows_vs_repo"] / total) if total else 1.0
    internal = 1.0 - min(1.0, m["dup_windows_internal"] / total) if total else 1.0
    dims = {"repo_reuse": reuse, "internal_dup": internal}
    wsum = sum(WASTE_WEIGHTS.values())
    score = (sum(WASTE_WEIGHTS[k] * dims[k] for k in WASTE_WEIGHTS) / wsum * 100
             if wsum else 0.0)
    # hard cap: a gross clone-vs-repo (over budget) or an internal-dup blowout can't be
    # averaged into ACCEPTABLE by a clean internal (or reuse) dimension.
    if (m["dup_windows_vs_repo"] > b["max_dup_windows_vs_repo"]
            or m["dup_ratio"] > 2 * b["max_dup_ratio"]):
        score = min(score, 60.0)
    return round(score, 1), dims


def _waste_flags(m, b):
    flags = []
    for ex in m["examples_vs_repo"]:
        flags.append(f"bloque de {b['window_size']}+ lineas ya existe en "
                     f"{ex['clone_of']} (agregado en {ex['added_in']}) — reusar, "
                     f"no reimplementar (DRY / CWE-1041)")
    if m["dup_windows_internal"]:
        flags.append(f"{m['dup_windows_internal']} ventana(s) de {b['window_size']}+ "
                     f"lineas duplicadas DENTRO del cambio — extraer un helper")
    return flags


def cmd_waste_check(args):
    b = dict(WASTE_DEFAULTS)
    declared = set()
    if args.config and os.path.exists(args.config):
        cfg = _load(args.config).get("defaults", {}).get("waste", {})
        for k in b:
            if k in cfg:
                b[k] = cfg[k]
                declared.add(k)
    if args.window_size is not None:
        b["window_size"] = args.window_size
        declared.add("window_size")
    if args.gate:
        b["gate"] = True
        declared.add("gate")
    gate = bool(b.get("gate"))
    repo_root = args.repo_root or "."
    m = _waste_metrics(_read_diff(args), repo_root, b)
    score, dims = _waste_score(m, b)
    verdict = _waste_band(score)
    flags = _waste_flags(m, b)
    exit_code = 1 if (verdict == "WASTEFUL" and gate) else 0

    out = {"score": score, "verdict": verdict, "gate": gate, "weights": WASTE_WEIGHTS,
           "dimensions": {k: round(v, 3) for k, v in dims.items()},
           "metrics": m, "budgets": b, "budgets_declared": sorted(declared),
           "flags": flags}
    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
        sys.exit(exit_code)

    mode = "declared gate" if gate else "advisory (declare defaults.waste.gate to make it block)"
    print(f"WASTE: {score}/100 — {verdict}  ({mode})")
    print(f"--- windows of {b['window_size']} normalized lines over {m['sig_lines_added']} "
          f"added lines ({m['added_windows']} window(s), {m['files_added_to']} file(s)) ---")
    print(f"  dup_vs_repo:      {m['dup_windows_vs_repo']} (budget {b['max_dup_windows_vs_repo']}"
          f"{'*' if 'max_dup_windows_vs_repo' in declared else ''})   "
          f"dup_internal: {m['dup_windows_internal']}   dup_ratio: {m['dup_ratio']}")
    print(f"  (call_density: {m['call_density']}/100 — informational, neither scored nor gated)")
    if not declared:
        print("  (every budget is a kit default — an opinion, not a "
              "requirement: declare yours in config.defaults.waste)")
    if flags:
        print("--- flags (REUSE-FIRST: what to reuse instead of cloning) ---")
        for fl in flags:
            print(f"  ! {fl}")
    print("--- honest: a Type-1/Type-2 proxy over normalized lines, NOT semantic "
          "clones (Type-3/4) nor AST-based CC ---")
    sys.exit(exit_code)


def cmd_pit_check(args):
    report = _find_pit_report(args.report)
    if not report or not os.path.exists(report):
        print("[qa_ledger] no PIT mutations.xml found. Run pitest first or pass "
              "--report PATH (Maven: mvn org.pitest:pitest-maven:mutationCoverage).",
              file=sys.stderr)
        sys.exit(2)
    try:
        m = _pit_metrics(report)
    except (ET.ParseError, OSError) as exc:
        print(f"[qa_ledger] cannot read PIT report {report}: {exc}", file=sys.stderr)
        sys.exit(2)

    passed = m["mutation_score"] >= args.min_score
    verdict = "PASS" if passed else "BELOW-GATE"
    hotspots = sorted(m["by_file"].items(),
                      key=lambda kv: kv[1]["survived"] + kv[1]["no_coverage"],
                      reverse=True)[:args.top]

    if args.json:
        out = {"verdict": verdict, "report": report, "min_score": args.min_score,
               "metrics": {k: v for k, v in m.items() if k != "by_file"},
               "hotspots": [{"file": f, **c} for f, c in hotspots]}
        print(json.dumps(out, indent=2, ensure_ascii=False))
        sys.exit(0 if passed else 1)

    print(f"MUTATION: {m['mutation_score']}/100 — {verdict} "
          f"(gate {args.min_score}, test-strength {m['test_strength']})")
    print("--- effectiveness (NOT coverage: it measures that the tests ASSERT) ---")
    print(f"  mutants {m['total']} · killed {m['killed']} · "
          f"survived {m['survived']} · uncovered {m['no_coverage']}")
    if m.get("excluded"):
        print(f"  ({m['excluded']} excluidos NON_VIABLE/RUN_ERROR — fuera del score, como PIT)")
    if hotspots:
        print("--- hotspots (more surviving mutants = weaker tests there) ---")
        for f, c in hotspots:
            print(f"  ! {f}: {c['survived']} sobreviven, {c['no_coverage']} sin cubrir")
    else:
        print("  no survivors — the tests catch the mutations")
    if m["no_coverage"]:
        print(f"  nota: {m['no_coverage']} mutante(s) sin NINGÚN test "
              f"(coverage-gap, distinto de assertion-gap)")
    sys.exit(0 if passed else 1)


# --------------------------------------------------------------------------- #
# gate-check  (gate integrity: a change must not WEAKEN the apparatus that measures it)
# --------------------------------------------------------------------------- #
# A maker-optimizer takes the cheapest path to green, and editing the gate is often
# cheapest. Flags a diff for: removed tests, disabled tests, lowered thresholds (BLOCKER,
# exit 1); added lint suppressions / removed assertions (soft — review, or gate with
# --strict). stdlib only; reads a GIT-format diff (same source as simplicity-check).
_GC_DISABLE = re.compile(
    r"@Disabled\b|@Ignore\b|enabled\s*=\s*false|\bxit\s*\(|\bxdescribe\s*\(|"
    r"\.skip\b|@(?:pytest\.mark\.)?skip\b", re.I)
# solo se evalua DENTRO de archivos ya clasificados test (_gc_is_test_file) —
# un falso positivo aca es inocuo. Cubre: JUnit/TestNG, C#/Java void, pytest,
# kotlin fun, Go func TestX, xunit [Fact]/[Theory], rust #[test], js it/test/describe.
_GC_TESTDEF = re.compile(
    r"@Test\b|\bvoid\s+test\w*|\bdef\s+test_\w+|\bfun\s+test\w*|"
    r"\bfunc\s+test\w+|\[(?:Fact|Theory)\]|#\[\s*(?:tokio::)?test\s*\]|"
    r"\b(?:it|test|describe)\s*\(", re.I)
_GC_SUPPRESS = re.compile(
    r"@SuppressWarnings|@SuppressFBWarnings|//\s*NOPMD|//\s*NOSONAR|checkstyle:off|"
    r"eslint-disable|#\s*noqa|#\s*type:\s*ignore|#\s*pylint:\s*disable", re.I)
_GC_ASSERT = re.compile(r"\bassert\w*|\bverify\s*\(|\bexpect\s*\(", re.I)
_GC_CONFIG = re.compile(
    r"pom\.xml$|\.gradle$|\.eslintrc|checkstyle|pmd|ruleset|jacoco|sonar-project|"
    r"dev-loop\.config\.json$", re.I)
# secret-scan (kit 1.12.0, Topic 43 'Stay Safe Out There'): patrones de ALTA
# precision bloquean como hecho (un PEM privado o una AKIA agregada no tiene
# lectura inocente); los literales genericos (password = "...") y los JWT son
# advisory — en fixtures de test abundan placeholders y bloquearlos seria
# castigar escribir tests. Solo se escanean lineas AGREGADAS: sacar un secreto
# del codigo es bueno y no debe frenar el diff que lo saca.
_GC_SECRETS_HARD = [
    ("clave privada PEM", re.compile(
        r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY")),
    ("AWS access key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(
        r"\bgh[pousr]_[A-Za-z0-9]{36}\b|\bgithub_pat_[A-Za-z0-9_]{22,}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
]
_GC_SECRET_SOFT = re.compile(
    r"(?i)\b(?:password|passwd|pwd|secret|api[_-]?key|token|credential)\s*[:=]\s*"
    r"[\"'][^\"']{8,}[\"']|\beyJ[A-Za-z0-9_\-]{20,}\.eyJ")
# contenedores de material de clave: AGREGARLOS al repo es un hecho bloqueante
# (borrarlos no — el lado b/ del diff es /dev/null y no matchea).
_GC_KEYFILE = re.compile(r"\.(?:p12|pfx|jks|keystore|key)$", re.I)
_GC_THRESH = re.compile(
    r"coverage|threshold|min[-_]?score|minimum|mutation|line-rate|branch-rate", re.I)
_GC_NUM = re.compile(r"\d+(?:\.\d+)?")


def _gc_is_test_file(path):
    # UNION fail-closed (kit 1.11.0): el clasificador compartido de los 9 stacks
    # (foo_test.go, *.Tests/ de dotnet, __tests__, spec.tsx, source sets gradle)
    # MAS los sufijos legacy case-insensitive — solo se AMPLIA que cuenta como
    # test para el veto de borrado; ningun path antes protegido se desprotege.
    if _is_simplicity_test_file(path):
        return True
    p = path.lower()
    if "/test/" in p or "/tests/" in p or p.startswith(("test/", "tests/")):
        return True
    base = p.rsplit("/", 1)[-1]
    return (base.startswith("test_")
            or base.endswith(("test.java", "tests.java", "test.kt", "test.dart",
                              "_test.py", ".test.js", ".test.ts", ".spec.js", ".spec.ts")))


# dependencias nuevas (supply-chain, kit 1.30.0): la CONSTITUTION dice "0 dependencias
# nuevas sin aprobacion" — hoy es prosa; esto la hace VISIBLE. Senal BLANDA (avisa;
# gatea con --strict), no BLOCKER: agregar una dep suele ser legitimo, solo necesita
# que un humano la vea/apruebe. Heuristica por manifest; un falso positivo (bump de
# version, key no-dep) es benigno porque es advisory. Cubre los 9 stacks del kit.
_GC_DEP_MANIFEST = {
    "package.json":   re.compile(r'"[\w@./-]+"\s*:\s*"[~^<>=v]?\d'),   # "pkg": "^1.2.3"
    "pyproject.toml": re.compile(r'^\s*[\w.-]+\s*=\s*[">{\d~^]'),
    "cargo.toml":     re.compile(r'^\s*[\w.-]+\s*=\s*[">{\d~^]'),
    "go.mod":         re.compile(r'^\s*[\w.][\w./-]+\s+v\d'),
    "pom.xml":        re.compile(r'<artifactId>'),
    "gemfile":        re.compile(r'^\s*gem\s+["\']'),
    "podfile":        re.compile(r'^\s*pod\s+["\']'),
}
_GC_REQ = re.compile(r'^\s*[A-Za-z][\w.-]*\s*(?:[=<>~!]=|~=|>=|<=|@|\[)')
_GC_GRADLE = re.compile(r'\b(?:implementation|api|testImplementation|runtimeOnly|compile|classpath)\s*[("\']')


def _gc_new_dep(path, body):
    """True if an ADDED line introduces a dependency in a known manifest (advisory
    heuristic — a false positive is benign because this is a soft finding)."""
    base = path.rsplit("/", 1)[-1].lower()
    if base.endswith((".csproj", ".vbproj", ".fsproj")):
        return "<PackageReference" in body
    if base.startswith("build.gradle"):
        return bool(_GC_GRADLE.search(body))
    if base.startswith("requirements") and base.endswith(".txt"):
        return bool(_GC_REQ.search(body))
    rx = _GC_DEP_MANIFEST.get(base)
    return bool(rx.search(body)) if rx else False


def cmd_gate_check(args):
    diff = _read_diff(args)
    removed_tests, disabled_tests, suppressions, thresholds = [], [], [], []
    secrets, secret_literals, scrub_edits, new_deps = [], [], [], []
    assertions_removed = 0
    path = None
    minus_path = None
    in_hunk = False
    # cross-hunk threshold bookkeeping: config file -> threshold-bearing line bodies.
    # Matched by KEYWORD across ALL hunks of the file, so splitting a config edit
    # into separate hunks (or reformatting it) no longer hides a lowered gate.
    thresh_removed = {}
    thresh_added = {}
    for raw in diff.splitlines():
        if raw.startswith("diff --git"):
            in_hunk = False; path = None; minus_path = None
            continue
        if raw.startswith("@@"):
            in_hunk = True
            continue
        if not in_hunk:
            if raw.startswith("--- "):
                p = raw[4:].strip().split("\t")[0]
                minus_path = None if p == "/dev/null" else (p[2:] if p[:2] in ("a/", "b/") else p)
            elif raw.startswith("+++ "):
                p = raw[4:].strip().split("\t")[0]
                if p == "/dev/null":
                    # whole-file DELETION: keep gating against the removed file's
                    # identity — deleting a test file wholesale is not invisible.
                    path = minus_path
                else:
                    path = p[2:] if p[:2] in ("a/", "b/") else p
                    if _GC_KEYFILE.search(path):
                        secrets.append(f"{path}: contenedor de claves agregado/modificado")
            elif raw.startswith("Binary files "):
                # los .p12/.jks binarios no traen +++ — el lado b/ vive en esta linea
                m = re.search(r" and b/(.+) differ$", raw)
                if m and _GC_KEYFILE.search(m.group(1)):
                    secrets.append(f"{m.group(1)}: contenedor de claves agregado/modificado (binario)")
            continue
        if not path:
            continue
        if raw.startswith("+"):
            body = raw[1:]
            if _GC_DISABLE.search(body) and (_gc_is_test_file(path) or "test" in path.lower()):
                disabled_tests.append(path)
            if _GC_SUPPRESS.search(body):
                suppressions.append(path)
            for label, rx in _GC_SECRETS_HARD:
                if rx.search(body):
                    secrets.append(f"{path}: {label}")
            if _GC_SECRET_SOFT.search(body):
                secret_literals.append(path)
            if _gc_new_dep(path, body):
                new_deps.append(f"{path}: {body.strip()[:70]}")
            # reglas de scrub del golden (kit 1.15.0): editarlas puede enmascarar
            # divergencia real — señal blanda SIEMPRE visible, el humano decide.
            if path.rsplit("/", 1)[-1] == "golden.scrub.json":
                scrub_edits.append(path)
            if _GC_CONFIG.search(path) and _GC_THRESH.search(body) and _GC_NUM.search(body):
                thresh_added.setdefault(path, []).append(body)
        elif raw.startswith("-"):
            body = raw[1:]
            if _gc_is_test_file(path):
                if _GC_TESTDEF.search(body):
                    removed_tests.append(path)
                if _GC_ASSERT.search(body):
                    assertions_removed += 1
            # borrar/recortar reglas de scrub tambien es editarlas (los goldens
            # pueden volver perma-rojos, o el recorte esconder un ensanche previo)
            if path.rsplit("/", 1)[-1] == "golden.scrub.json":
                scrub_edits.append(path)
            if _GC_CONFIG.search(path) and _GC_THRESH.search(body) and _GC_NUM.search(body):
                thresh_removed.setdefault(path, []).append(body)

    # threshold analysis, keyword-matched per file across all hunks:
    #   lowered  -> BLOCKER;  removed with no re-add -> BLOCKER (the gate vanished)
    for cpath, removed in thresh_removed.items():
        added = thresh_added.get(cpath, [])
        for rbody in removed:
            rkey = _GC_THRESH.search(rbody).group(0).lower()
            rnums = _GC_NUM.findall(rbody)
            if not rnums:
                continue
            candidates = [a for a in added
                          if _GC_THRESH.search(a).group(0).lower() == rkey]
            if not candidates:
                thresholds.append(f"{cpath}: '{rkey}' {rnums[0]} removed with no replacement")
                continue
            for a in candidates:
                anums = _GC_NUM.findall(a)
                if anums and float(anums[0]) < float(rnums[0]):
                    thresholds.append(f"{cpath}: {rkey} {rnums[0]} -> {anums[0]}")
                    break

    # optional MEASURED cross-check (heuristic-independent): with --repo, compare the
    # last two snapshots' executed-test totals — a drop is a fact no regex can miss.
    test_count_drop = None
    if getattr(args, "repo", None):
        try:
            ledger = _load(args.ledger)
            node = _repo_node(ledger, args.repo)
            snaps = node.get("snapshots", [])
            if len(snaps) >= 2:
                prev_t = (snaps[-2].get("tests") or {}).get("total") or 0
                last_t = (snaps[-1].get("tests") or {}).get("total") or 0
                if last_t < prev_t:
                    test_count_drop = f"{prev_t} -> {last_t}"
        except SystemExit:
            raise
        except Exception:
            pass  # the ledger cross-check is optional; its absence must not break the diff gate

    hard = (len(removed_tests) + len(disabled_tests) + len(thresholds)
            + len(secrets))
    soft = (len(suppressions) + (1 if assertions_removed else 0)
            + (1 if test_count_drop else 0) + len(secret_literals)
            + len(scrub_edits) + len(new_deps))
    blocker = hard > 0 or (args.strict and soft > 0)
    verdict = "BLOCKER" if blocker else ("REVIEW" if soft else "CLEAN")

    if args.json:
        print(json.dumps({
            "verdict": verdict,
            "removed_tests": sorted(set(removed_tests)),
            "disabled_tests": sorted(set(disabled_tests)),
            "thresholds_lowered": thresholds,
            "secrets_added": sorted(set(secrets)),
            "secret_literals": sorted(set(secret_literals)),
            "scrub_rules_touched": sorted(set(scrub_edits)),
            "suppressions_added": sorted(set(suppressions)),
            "new_dependencies": sorted(set(new_deps)),
            "assertions_removed": assertions_removed,
            "test_count_drop": test_count_drop,
        }, indent=2, ensure_ascii=False))
        sys.exit(1 if blocker else 0)

    print(f"GATE-INTEGRITY: {verdict}")

    def _show(label, items):
        if items:
            uniq = sorted(set(items))
            tail = " ..." if len(uniq) > 5 else ""
            print(f"  ! {label}: {len(items)} in {', '.join(uniq[:5])}{tail}")

    _show("tests deleted (BLOCKER)", removed_tests)
    _show("tests disabled (BLOCKER)", disabled_tests)
    if thresholds:
        print(f"  ! thresholds lowered/removed (BLOCKER): {'; '.join(thresholds)}")
    if secrets:
        print(f"  ! secrets added (BLOCKER): {'; '.join(sorted(set(secrets)))}")
    _show("password/token-shaped literals added (review)", secret_literals)
    _show("golden scrub rules edited (review: they can mask divergence)", scrub_edits)
    _show("lint suppressions added (review)", suppressions)
    _show("new dependencies (review: 0 new deps without approval)", new_deps)
    if assertions_removed:
        print(f"  ~ asserts removed from tests: {assertions_removed} (review)")
    if test_count_drop:
        print(f"  ~ executed-test count dropped: {test_count_drop} (measured in snapshots — review)")
    if verdict == "CLEAN":
        print("  the change does not weaken the measuring apparatus")
    elif not blocker:
        print("  soft signals: they require justification (--strict to gate)")
    sys.exit(1 if blocker else 0)


# --------------------------------------------------------------------------- #
# regression-check  (M1, Tip 94 'Find Bugs Once' + Tip 31 'Failing Test First')
# --------------------------------------------------------------------------- #
def cmd_regression_check(args):
    """Cierre de findings SIN test que lo reproduzca = RELATO (aconseja),
    jamas hecho. La evidencia es a nivel DIFF y es mecanica: el diff que
    arregla tiene que AGREGAR/modificar lineas NO VACIAS en el arbol de test
    (clasificador compartido de los 9 stacks). LIMITE DISCLOSED: es un tripwire,
    no un juez — una linea de comentario en un test file cuenta (juzgar
    contenido entre 9 lenguajes seria adivinanza); las señales
    has_test_definition/has_assertion se exponen como hechos y su ausencia se
    marca como evidencia debil. La CALIDAD de los tests la juzga pit-check.
    Que test reproduce QUE finding seria adivinanza sin una convencion de
    naming — diferido consciente; este gate mide lo que se puede medir sin
    inventar. Verdicts: N/A (nada cerrado) · MEASURED
    (cierre con tests tocados) · NARRATED (cierre sin evidencia — exit 1 solo
    con --strict; persistir con log-gate --kind regression si el equipo decide
    gatearlo)."""
    diff = _read_diff(args)
    fixed = args.fixed
    if fixed is None:
        # default: suma de 'fixed' de la iteracion MAS RECIENTE del repo
        ledger = _load(args.ledger)
        node = _repo_node(ledger, args.repo)
        last_it = _repo_loop_count(node)
        fixed = sum((s.get("fixed") or 0) for s in node["iterations"]
                    if (s.get("iteration") or 0) == last_it)
    test_files = set()
    test_added = 0          # solo lineas NO vacias: un '\n' suelto no es evidencia
    has_testdef = False     # ¿alguna linea agregada define un test?
    has_assert = False      # ¿alguna trae un assert/verify/expect?
    in_hunk = False
    counting = False
    for raw in diff.splitlines():
        if raw.startswith("diff --git"):
            in_hunk = False
            counting = False
            continue
        if raw.startswith("@@"):
            in_hunk = True
            continue
        if not in_hunk:
            if raw.startswith("+++ "):
                p = raw[4:].strip().split("\t")[0]
                if p != "/dev/null":
                    rel = p[2:] if p[:2] in ("a/", "b/") else p
                    counting = _is_simplicity_test_file(rel)
                    if counting:
                        test_files.add(rel)
            continue
        if counting and raw.startswith("+"):
            body = raw[1:]
            if body.strip():
                test_added += 1
                if _GC_TESTDEF.search(body):
                    has_testdef = True
                if _GC_ASSERT.search(body):
                    has_assert = True

    if fixed == 0:
        verdict = "N/A"
    elif test_added > 0:
        verdict = "MEASURED"
    else:
        verdict = "NARRATED"
    fail = verdict == "NARRATED" and args.strict

    if args.json:
        print(json.dumps({"verdict": verdict, "fixed": fixed,
                          "test_files_touched": sorted(test_files),
                          "test_lines_added": test_added,
                          "has_test_definition": has_testdef,
                          "has_assertion": has_assert},
                         indent=2, ensure_ascii=False))
        sys.exit(1 if fail else 0)
    print(f"REGRESSION-CAPTURE: {verdict}  ({fixed} finding(s) closed · "
          f"+{test_added} test lines in {len(test_files)} file(s))")
    if verdict == "NARRATED":
        print("  ! NARRATED close: findings vanished without touching a single test — "
              "which test reproduces the bug you say you fixed? (Tip 31: the "
              "failing test comes BEFORE the fix; Tip 94: each bug is found ONCE)")
    elif verdict == "MEASURED":
        print("  close with evidence: the fixing diff brings tests")
        if not (has_testdef or has_assert):
            print("  · WEAK evidence: the added test lines carry neither a test "
                  "definition nor an assert — this tripwire does not judge quality "
                  "(that is pit-check), but it deserves a human eye")
    else:
        print("  nothing closed in the last iteration — nothing to demand")
    sys.exit(1 if fail else 0)


# --------------------------------------------------------------------------- #
# spec-check  (spec-quality gate: lint the SPEC/ACCEPTANCE BEFORE generation)
# --------------------------------------------------------------------------- #
# The kit gates code; this gates the SPEC — its deterministic twin. It does the
# COMPUTATIONAL checks (structure, testability proxies, EARS shape, stack naming);
# it does NOT fake CONSISTENCY (contradictory clauses = a semantic/inferential check
# for the non-correlated checker, per the Böckeler computational-vs-inferential rule).
# Split verdicts, per the kit's own rule (fact-reading gates block, prose-guessers
# advise): the STRUCTURAL checks (out-of-scope section absent / acceptance criteria
# absent-or-empty) are FACTS — a section exists or it does not — and exit 1.
# The PROSE heuristics (vague terms, EARS shape, stack naming) stay advisory;
# --strict makes them gate too.
_SC_VAGUE = re.compile(
    r"\b(fast|quick|efficient|robust|scalable|user[- ]?friendly|intuitive|simple|easy|"
    r"appropriate|adequate|reasonable|properly|seamless|flexible|optimal|as needed|"
    r"as appropriate|as expected|works? as expected|handled correctly|etc\.?|and so on|should work|"
    r"r[áa]pid[oa]|eficiente|robust[oa]|amigable|adecuad[oa]|apropiad[oa]|flexible|[óo]ptim[oa]|"
    r"sencill[oa]|f[áa]cil|intuitiv[oa]|escalable|usable|comprensible|clar[oa]|correct[oa]|"
    r"seg[úu]n sea necesario|etc[eé]tera)\b", re.I)
# measurable = a comparator, a number+unit, or an explicit bounded-quantity phrase.
# (A bare digit is NOT measurable — "see section 3" must not exempt a vague criterion.)
_SC_MEASURABLE = re.compile(
    r"[<>]=?|\b\d+(?:\.\d+)?\s?(?:ms|s|sec|seconds?|min|minutes?|hours?|[kmg]b|%|percent|"
    r"requests?|rps|qps|x)\b|"
    r"\b(less than|more than|at most|at least|within|exactly|no more than|no less than|"
    r"menos de|m[áa]s de|a lo sumo|al menos|dentro de|exactamente|byte[- ]?equivalent)\b", re.I)
_SC_EARS = re.compile(
    r"\b(when|if|while|where|given|cuando|si|mientras|dado)\b.*\b(shall|must|will|should|"
    r"debe|deber[áa]|tiene que)\b", re.I)
# only UNAMBIGUOUS stack tokens (dropped react/express/angular/vue/flask/spring-alone/node/.net
# which collide with ordinary words); scanned only within acceptance criteria, not whole doc.
_SC_STACK = re.compile(
    r"\b(spring boot|hibernate|postgres(?:ql)?|mysql|mssql|sql server|mongodb|redis|kafka|"
    r"docker|kubernetes|k8s|jdbc|graphql|django|nginx|tomcat|maven|gradle|quartz|cxf|"
    r"bouncycastle)\b", re.I)
_SC_OUTSCOPE = re.compile(
    r"out[- ]?of[- ]?scope|exclusions?|non[- ]?goals?|no[- ]?goals?|fuera de alcance|"
    r"exclusi[oó]n|no[- ]?objetivos?", re.I)
# acceptance section only — NOT bare "criteria"/"criterios" (which also matches success/exit/design)
_SC_ACCEPT = re.compile(r"\bacceptance\b|criterios?\s+de\s+aceptaci[oó]n|\baceptaci[oó]n\b", re.I)
_SC_HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
_SC_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*\S)\s*$")
_SC_SETEXT = re.compile(r"^(=+|-{2,})\s*$")
_SC_CHECKBOX = re.compile(r"^\[[ xX]\]\s*")


def _spec_check_text(text):
    lines = text.split("\n")
    n = len(lines)
    has_outscope = False
    accept_section = False
    in_accept = False
    in_fence = False       # inside a ``` / ~~~ fenced block — skip its content
    criteria = []          # acceptance-criterion bodies
    stack_hits = []        # (lineno, term) — scanned only within acceptance criteria
    i = 0
    while i < n:
        raw = lines[i]
        st = raw.strip()
        if st.startswith("```") or st.startswith("~~~"):
            in_fence = not in_fence
            i += 1
            continue
        if in_fence:
            i += 1
            continue
        title = None
        h = _SC_HEADING.match(raw)
        if h:
            title = h.group(2)
        elif st and not _SC_ITEM.match(raw) and i + 1 < n and _SC_SETEXT.match(lines[i + 1].strip()):
            title = st          # setext heading: text underlined by === or ---
            i += 1              # consume the underline line
        if title is not None:
            if _SC_OUTSCOPE.search(title):
                has_outscope = True
            in_accept = bool(_SC_ACCEPT.search(title))
            if in_accept:
                accept_section = True
            i += 1
            continue
        it = _SC_ITEM.match(raw)
        if it and in_accept:
            body = _SC_CHECKBOX.sub("", it.group(1).strip()).strip()
            if body:            # skip empty checkbox-only items ("- [ ]")
                criteria.append(body)
                m = _SC_STACK.search(body)
                if m:
                    stack_hits.append((i + 1, m.group(0)))
        i += 1

    untestable = [c for c in criteria if _SC_VAGUE.search(c) and not _SC_MEASURABLE.search(c)]
    non_ears = [c for c in criteria if not _SC_EARS.search(c)]
    blockers = []
    if not has_outscope:
        blockers.append("falta sección de alcance/exclusiones (out-of-scope) — sin ella no hay oráculo para 'scoped-but-absent'")
    if not accept_section or not criteria:
        blockers.append("sin criterios de aceptación testables (falta sección Acceptance/Criterios o está vacía)")
    return {
        "has_outscope": has_outscope,
        "n_criteria": len(criteria),
        "untestable": untestable,
        "non_ears": len(non_ears),
        "stack_hits": stack_hits,
        "blockers": blockers,
    }


def _acceptance_traceability(path):
    """Trazabilidad del ACCEPTANCE (kit 1.10.0): estructura = FACT.
    Bloquea: archivo ausente, cero criterios, CERO criterios con AC-ID, IDs
    duplicados (tras normalizar: AC-01 == AC-1). Aconseja: criterios sueltos
    sin ID (no podran cerrar MEDIDO)."""
    blockers, advisory = [], []
    items, found = _parse_acceptance_items(path)
    if not found:
        blockers.append(f"acceptance no encontrado: {path}")
        return blockers, advisory
    if not items:
        blockers.append("acceptance sin criterios (cero checkboxes)")
        return blockers, advisory
    ids = [i["id"] for i in items if i["id"]]
    if not ids:
        blockers.append("cero criterios trazables — cada criterio lleva ID "
                        "estable: '- [ ] AC-01 — cuando X entonces Y'")
        return blockers, advisory
    dupes = sorted({x for x in ids if ids.count(x) > 1})
    if dupes:
        blockers.append(f"IDs duplicados (normalizados): {', '.join(dupes)}")
    untagged = sum(1 for i in items if not i["id"])
    if untagged:
        advisory.append(f"{untagged} criterio(s) sin AC-ID — no podran "
                        f"cerrar MEDIDO en el readiness")
    return blockers, advisory


# --------------------------------------------------------------------------- #
# rubric  (kit 1.23.0: el ACCEPTANCE de lo NO-testeable — criterio cualitativo
# versionado. El engine NO corre ningun grader: valida la estructura de
# RUBRIC.md como HECHO e ingesta el JSON del contrato — quien lo emitio
# (Claude Code, Codex, Gemini CLI, un curl, un humano) es irrelevante.
# Advisory por default; gatea SOLO por declaracion humana (--gate o
# defaults.rubric.gate en config — procedencia 1.17.0).
# --------------------------------------------------------------------------- #
_RB_ID = re.compile(r"(?i)^(RB(-NEG)?[-_]?0*(\d+))\b")
_RB_WEIGHT = re.compile(r"\(peso\s+(\d+)\)")
_RB_THRESHOLD = re.compile(r"(?im)^threshold:\s*([0-9.]+)\s*$")


def _parse_rubric(path):
    """(items, threshold, found). item = {'id': 'RB-n'|'RB-NEG-n', 'weight',
    'negative', 'text'} — IDs normalizados por numero. Los anchors son prosa
    para el grader: el engine no los parsea."""
    if not path or not os.path.exists(path):
        return [], None, False
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return [], None, False
    m = _RB_THRESHOLD.search(text)
    try:
        threshold = float(m.group(1)) if m else None
    except ValueError:   # 'threshold: 0.8.0' — malformado = ausente, no traceback
        threshold = None
    items = []
    for line in text.splitlines():
        s = line.strip()
        if s[:5].lower() not in ("- [ ]", "- [x]", "* [ ]", "* [x]"):
            continue
        body = s[5:].strip()
        mid = _RB_ID.match(body)
        if not mid:
            continue
        negative = bool(mid.group(2))
        num = int(mid.group(3))
        mw = _RB_WEIGHT.search(body)
        items.append({"id": f"RB-NEG-{num}" if negative else f"RB-{num}",
                      "weight": int(mw.group(1)) if mw else 1,
                      "negative": negative,
                      "text": body[mid.end():].strip()})
    return items, threshold, True


def _rubric_structure(path):
    """Estructura de la rubrica = HECHO. Bloquea: archivo ausente, cero
    criterios positivos, IDs duplicados (normalizados), threshold ausente o
    fuera de (0, 1]."""
    blockers = []
    items, threshold, found = _parse_rubric(path)
    if not found:
        return [f"rubrica no encontrada: {path}"]
    positives = [i for i in items if not i["negative"]]
    if not positives:
        blockers.append("rubrica sin criterios positivos ('- [ ] RB-01 (peso N) — ...')")
    ids = [i["id"] for i in items]
    dupes = sorted({x for x in ids if ids.count(x) > 1})
    if dupes:
        blockers.append(f"IDs duplicados (normalizados): {', '.join(dupes)}")
    if threshold is None:
        blockers.append("threshold ausente (linea 'threshold: 0.NN')")
    elif not 0 < threshold <= 1:
        blockers.append(f"threshold {threshold} fuera de (0, 1]")
    return blockers


def cmd_rubric_ingest(args):
    ledger = _load(args.ledger)
    node = _repo_node(ledger, args.repo)
    _validate_iteration(node, "rubric:grade", args.iteration)
    defaults = ledger["config"].get("defaults", {})
    rub_cfg = defaults.get("rubric", {}) if isinstance(defaults.get("rubric"), dict) else {}
    rubric_path = args.rubric or rub_cfg.get("file", "RUBRIC.md")
    blockers = _rubric_structure(rubric_path)
    if blockers:
        for b in blockers:
            print(f"[qa_ledger] invalid rubric: {b}", file=sys.stderr)
        sys.exit(2)
    items, threshold, _found = _parse_rubric(rubric_path)
    by_id = {i["id"]: i for i in items}

    try:
        with open(args.report, "r", encoding="utf-8") as fh:
            report = json.load(fh)
        criteria = report["criteria"]
        assert isinstance(criteria, list)
        assert all(isinstance(c, dict) for c in criteria)  # entradas no-dict = contrato roto
    except (OSError, json.JSONDecodeError, KeyError, TypeError, AssertionError) as exc:
        raise SystemExit(f"[qa_ledger] reporte del grader invalido ({args.report}): {exc} "
                         f'— contrato: {{"criteria": [{{"id","verdict","evidence","note"}}]}}')

    def _rb_norm(raw):
        # mismo normalizado que la rubrica: RB-01 == RB_1 == rb1 (por numero)
        m = _RB_ID.match(str(raw or "").strip())
        if not m:
            return None
        return f"RB-NEG-{int(m.group(3))}" if m.group(2) else f"RB-{int(m.group(3))}"

    unknown = [str(c.get("id")) for c in criteria
               if _rb_norm(c.get("id")) not in by_id]
    if unknown:
        raise SystemExit(f"[qa_ledger] IDs del reporte que no existen en la rubrica: "
                         f"{', '.join(unknown)} — el grader no inventa criterios.")
    norm_ids = [_rb_norm(c["id"]) for c in criteria]
    rep_dupes = sorted({x for x in norm_ids if norm_ids.count(x) > 1})
    if rep_dupes:
        # dos veredictos para el mismo criterio = contrato roto (si no, el
        # ultimo pisa al primero en silencio — vector de gaming del grader)
        raise SystemExit(f"[qa_ledger] IDs duplicados en el reporte (normalizados): "
                         f"{', '.join(rep_dupes)} — un veredicto por criterio.")

    verdicts = {_rb_norm(c["id"]): c for c in criteria}
    unsupported = []   # veredictos que afectan el score SIN evidencia -> no puntuan
    earned = 0.0
    failed_pos = []
    n_pos = sum(1 for i in items if not i["negative"])
    for it in items:
        c = verdicts.get(it["id"])
        if it["negative"]:
            # fail = la practica prohibida APARECE -> resta peso (con evidencia)
            if c and c.get("verdict") == "fail":
                if str(c.get("evidence") or "").strip():
                    earned -= it["weight"]
                else:
                    unsupported.append(it["id"])
            continue
        if c and c.get("verdict") == "pass":
            if str(c.get("evidence") or "").strip():
                earned += it["weight"]
            else:
                unsupported.append(it["id"])
                failed_pos.append(it["id"])
        else:
            # fail explicito o NO evaluado: no evaluado no es aprobado
            failed_pos.append(it["id"])
    total = sum(i["weight"] for i in items if not i["negative"])
    score = max(0.0, earned) / total if total else 0.0
    passed = score >= threshold
    gated = bool(args.gate or rub_cfg.get("gate") is True)

    note = (f"score {score:.2f} vs threshold {threshold:.2f} "
            f"({n_pos - len(failed_pos)}/{n_pos} positivos con evidencia)"
            + (" [GATE declarado]" if gated else " [advisory]"))
    failing = (not passed) and gated
    _append_gate_record(ledger, node, args.repo, "rubric:grade", args.iteration,
                        failing, len(failed_pos), note)
    _save(args.ledger, ledger)

    if args.json:
        print(json.dumps({"verdict": "PASS" if passed else "BELOW",
                          "score": round(score, 3), "threshold": threshold,
                          "gated": gated, "failed": sorted(failed_pos),
                          "unsupported": sorted(unsupported)},
                         indent=2, ensure_ascii=False))
        sys.exit(1 if failing else 0)
    print(f"RUBRIC: {'PASS' if passed else 'BELOW'}  {note}")
    if failed_pos:
        print(f"  ! criteria not closed: {', '.join(sorted(failed_pos))}")
    if unsupported:
        print(f"  ! verdicts WITHOUT evidence (they do not score): {', '.join(sorted(unsupported))} "
              f"— evidence-or-nothing, a judgement without a citation does not count")
    if failing:
        print("  the gate is DECLARED (config/--gate): it blocks convergence and "
              "caps readiness <=65 until a clean grade")
    elif not passed:
        print("  advisory: it does not gate — declare it in defaults.rubric.gate to make it block")
    sys.exit(1 if failing else 0)


def cmd_spec_check(args):
    acc_block, acc_adv = ([], [])
    if args.acceptance:
        acc_block, acc_adv = _acceptance_traceability(args.acceptance)
    if getattr(args, "rubric", None):
        acc_block = acc_block + _rubric_structure(args.rubric)
    if args.spec:
        text = ""
        for p in args.spec:
            try:
                with open(p, "r", encoding="utf-8", errors="replace") as fh:
                    text += fh.read() + "\n"
            except OSError as exc:
                print(f"[qa_ledger] cannot read spec {p}: {exc}", file=sys.stderr)
                sys.exit(2)
    elif (args.acceptance or getattr(args, "rubric", None)) and sys.stdin.isatty():
        text = ""  # modo solo-acceptance/rubrica interactivo: no bloquear leyendo stdin
    else:
        # sin --spec: leer stdin SIEMPRE que venga pipeado/redirigido (incluso
        # con --acceptance) — un `cat SPEC.md | ... --acceptance X` no debe
        # descartar en silencio el SPEC pipeado.
        text = sys.stdin.read()
    if not text.strip() and not args.acceptance and not getattr(args, "rubric", None):
        print("[qa_ledger] no spec content; use --spec PATH or pipe on stdin.", file=sys.stderr)
        sys.exit(2)

    m = (_spec_check_text(text) if text.strip()
         else {"blockers": [], "untestable": [], "stack_hits": [],
               "non_ears": 0, "n_criteria": 0})
    structural = len(m["blockers"]) + len(acc_block)  # estructura = FACT -> bloquea
    soft_find = len(m["untestable"]) + len(m["stack_hits"]) + len(acc_adv)
    fail = structural > 0 or (args.strict and soft_find > 0)
    verdict = "BLOCKED" if structural else ("ADVISORY" if soft_find else "OK")

    if args.json:
        print(json.dumps({"verdict": verdict, "advisory": structural == 0,
                          "acceptance_blockers": acc_block,
                          "acceptance_advisory": acc_adv, **m},
                         indent=2, ensure_ascii=False))
        sys.exit(1 if fail else 0)

    label = "" if structural else " (advisory)"
    print(f"SPEC-QUALITY: {verdict}{label}  ({m['n_criteria']} criterios de aceptación)")
    for b in m["blockers"]:
        print(f"  ! estructura (FACT — bloquea): {b}")
    for b in acc_block:
        print(f"  ! trazabilidad (FACT — bloquea): {b}")
    for a in acc_adv:
        print(f"  · trazabilidad (advisory): {a}")
    if m["untestable"]:
        print(f"  ~ testabilidad ({len(m['untestable'])}): criterios vagos sin métrica —")
        for c in m["untestable"][:5]:
            print(f"      · {c[:80]}")
    if m["stack_hits"]:
        terms = sorted({t for _, t in m["stack_hits"]})
        print(f"  ~ stack named in criteria ({len(m['stack_hits'])}): {', '.join(terms[:6])} — the 'how' belongs in the ADR, not the SPEC")
    if m["non_ears"] and m["n_criteria"]:
        print(f"  · advisory: {m['non_ears']}/{m['n_criteria']} criteria do not follow the EARS pattern (When/If/While … shall)")
    print("  i consistency: INFERENTIAL (an uncorrelated checker), not this lint · "
          "structure = FACT (blocks) · prose = advisory (--strict to gate)")
    if verdict == "OK":
        print("  structure complete and criteria testable")
    sys.exit(1 if fail else 0)


# --------------------------------------------------------------------------- #
# golden-diff  (approval/golden testing gate: byte-compare .received vs .approved)
# --------------------------------------------------------------------------- #
# The ONLY artifact the agent must not author. Captured mechanically from the ORIGINAL
# code; the gate is a byte-comparison (a FACT, not a judgment). Never writes .approved.
# A .received with no matching (unapproved) .approved = diverged = BLOCKER (exit 1).
def _golden_approved_path(rec):
    """Derive the .approved sibling — replacing the marker ONLY in the BASENAME (never a
    parent dir), at its LAST occurrence. None if the basename carries no marker."""
    d, base = os.path.split(rec)
    if ".received." in base:
        head, _, tail = base.rpartition(".received.")
        app_base = head + ".approved." + tail
    elif base.endswith(".received"):
        app_base = base[:-len(".received")] + ".approved"
    else:
        return None
    return os.path.join(d, app_base)


GOLDEN_SCRUB_FILE = "golden.scrub.json"
GOLDEN_DIVERGENCES_FILE = "golden.divergences.json"


def _load_golden_divergences(root):
    """Expected divergences for `fix` verdicts (ADR-009 slice 2): a golden that MUST differ
    because its ADR says the behavior was corrected. Shape:
    {"divergences": {"<fixture basename>": {"adr": "ADR-RD-NNN", "reason": "..."}}}.
    Strict like the scrub rules: a typo must not degrade into "no declarations" -- that
    silence would turn every expected divergence back into a blocker, or worse, hide a
    declared one behind a malformed file. Absent file -> {} (nothing declared)."""
    path = os.path.join(root, GOLDEN_DIVERGENCES_FILE)
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            spec = json.load(fh)
        if not isinstance(spec, dict) or not isinstance(spec.get("divergences"), dict):
            raise TypeError('expected {"divergences": {"<fixture>": {"adr":..., "reason":...}}}')
        for k, v in spec["divergences"].items():
            if (not isinstance(v, dict) or not re.match(r"^ADR-\S+$", str(v.get("adr", "")))
                    or not str(v.get("reason", "")).strip()):
                raise TypeError("divergence %r needs adr (ADR-...) and a reason" % k)
        return spec["divergences"]
    except (json.JSONDecodeError, TypeError, KeyError) as exc:
        print("[qa_ledger] %s invalid (%s) - declared divergences are not skipped in "
              "silence: fix the file or delete it." % (path, exc), file=sys.stderr)
        sys.exit(2)



def _load_scrub_rules(root):
    """Reglas de scrub del golden master (kit 1.15.0, Topic 41: no apoyar tests
    en cosas no confiables — timestamps, ids, posiciones). Formato:
    {"rules": [{"pattern": "<regex>", "replace": "<placeholder>"}]}. Las reglas
    se declaran en characterize y el HUMANO las aprueba junto con los .approved
    (gate-check flaggea sus ediciones). Archivo ausente = sin scrub, byte puro.
    Archivo invalido = exit 2 (error de config, explicito — nunca se saltea el
    scrub en silencio). Devuelve [(compiled, replace, pattern)]."""
    path = os.path.join(root, GOLDEN_SCRUB_FILE)
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            spec = json.load(fh)
        # shape estricta: un typo ('reglas', lista a secas) NO puede degradar
        # a 'cero reglas' en silencio — eso saltearia el scrub sin avisar.
        if not isinstance(spec, dict) or not isinstance(spec.get("rules"), list):
            raise TypeError('se espera {"rules": [{"pattern": ..., "replace": ...}]}')
        rules = []
        for r in spec["rules"]:
            rules.append((re.compile(r["pattern"]), r["replace"], r["pattern"]))
        return rules
    except (json.JSONDecodeError, re.error, KeyError, TypeError) as exc:
        print(f"[qa_ledger] {path} invalid ({exc}) — the scrub is not skipped in "
              f"silence: fix the file or delete it.", file=sys.stderr)
        sys.exit(2)


def _scrub(blob, rules, counts):
    """Aplica las reglas a contenido de TEXTO; el binario no se scrubbea
    (vuelve intacto y el compare sigue siendo byte a byte)."""
    try:
        text = blob.decode("utf-8")
    except UnicodeDecodeError:
        return blob
    for rx, repl, pat in rules:
        text, n = rx.subn(repl, text)
        if n:
            counts[pat] = counts.get(pat, 0) + n
    return text.encode("utf-8")


GOLDEN_LABEL_CLASSES = {"intended", "observed-accidental", "unknown"}


def _norm_golden_path(path):
    return os.path.normpath(str(path)).replace(os.sep, "/")


def _load_golden_labels(path):
    if not path:
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[qa_ledger] invalid golden labels ({exc})", file=sys.stderr)
        sys.exit(2)
    fixtures = raw.get("fixtures", raw) if isinstance(raw, dict) else None
    if not isinstance(fixtures, dict):
        print('[qa_ledger] golden labels invalidos: se espera {"fixtures": {...}}',
              file=sys.stderr)
        sys.exit(2)
    out = {}
    for key, val in fixtures.items():
        if isinstance(val, str):
            classification, note = val, None
        elif isinstance(val, dict):
            classification, note = val.get("classification", "unknown"), val.get("note")
        else:
            classification, note = "unknown", None
        classification = str(classification or "unknown").replace("_", "-")
        if classification not in GOLDEN_LABEL_CLASSES:
            classification = "unknown"
        out[_norm_golden_path(key)] = {"classification": classification, "note": note}
    return out


def _golden_label(labels, root, rec, app):
    if not app:
        return {"classification": "unknown", "note": None, "key": None}
    candidates = [_norm_golden_path(app), _norm_golden_path(rec)]
    try:
        candidates.append(_norm_golden_path(os.path.relpath(app, root)))
        candidates.append(_norm_golden_path(os.path.relpath(rec, root)))
    except ValueError:
        pass
    # Also try paths without a leading ./ because glob from root='.' returns ./foo.
    candidates.extend(c[2:] for c in list(candidates) if c.startswith("./"))
    for c in candidates:
        if c in labels:
            v = labels[c].copy()
            v["key"] = c
            return v
    return {"classification": "unknown", "note": None, "key": None}


def _golden_label_counts(fixtures):
    counts = {"intended": 0, "observed_accidental": 0, "unknown": 0, "total": len(fixtures)}
    for f in fixtures:
        cls = f.get("classification", "unknown")
        key = "observed_accidental" if cls == "observed-accidental" else cls
        if key not in counts:
            key = "unknown"
        counts[key] += 1
    return counts


def cmd_golden_diff(args):
    root = args.dir or "."
    hits = set(glob.glob(os.path.join(root, "**", "*.received.*"), recursive=True))
    hits |= set(glob.glob(os.path.join(root, "**", "*.received"), recursive=True))
    received = [p for p in sorted(hits) if os.path.isfile(p)]   # skip dirs matched by glob
    rules = _load_scrub_rules(root)
    labels = _load_golden_labels(getattr(args, "labels", None))
    divergences = _load_golden_divergences(root)
    expected_diverged = 0
    consumed_declarations = set()
    scrub_counts = {}
    diverged = []   # (received_path, reason)
    fixtures = []
    matched = 0
    matched_scrubbed = 0
    for rec in received:
        app = _golden_approved_path(rec)
        if app is None:
            continue
        label = _golden_label(labels, root, rec, app)
        fixture = {"received": rec, "approved": app,
                   "classification": label["classification"],
                   "label_note": label["note"], "label_key": label["key"],
                   "result": None}
        fixtures.append(fixture)
        if not os.path.exists(app):
            fixture["result"] = "missing_approved"
            diverged.append((rec, "sin .approved ? fixture nuevo, requiere aprobaci?n humana"))
            continue
        try:
            with open(rec, "rb") as fr:
                rb = fr.read()
            with open(app, "rb") as fa:
                ab = fa.read()
        except OSError as exc:
            fixture["result"] = "read_error"
            diverged.append((rec, f"could not read: {exc}"))
            continue
        decl, decl_key = None, None
        for cand_key in (os.path.relpath(app, root).replace(os.sep, "/"),
                         os.path.relpath(rec, root).replace(os.sep, "/"),
                         os.path.basename(app), os.path.basename(rec)):
            # relpath first (the _golden_label pattern: nested suites share basenames and a
            # declaration must not launder an unrelated module\x27s divergence -- fresh-review
            # finding); basename stays as the flat-layout convenience.
            if cand_key in divergences:
                decl, decl_key = divergences[cand_key], cand_key
                break
        if decl:
            consumed_declarations.add(decl_key)   # only what MATCHED: an unexercised twin
                                                  # key must still show as unconsumed
        if rb == ab:
            if decl:
                # a `fix` verdict DECLARED this golden must differ -- identical bytes mean
                # the corrected behavior never landed. An expected divergence that is not
                # observed is a red finding, not a quiet pass (ADR-010: fix cases must
                # diverge exactly as their ADR describes; identical is not that).
                fixture["result"] = "declared_divergence_not_observed"
                diverged.append((rec, "declared divergent (%s) but IDENTICAL -- the fix "
                                      "this declaration describes is not in the output"
                                      % decl["adr"]))
                continue
            fixture["result"] = "matched"
            matched += 1
        # el conteo reportado es del lado RECEIVED (la captura fresca) — sumar
        # ambos lados duplicaria cada volatil enmascarado en el reporte.
        elif rules and (_scrub(rb, rules, scrub_counts)
                        == _scrub(ab, rules, {})):
            if decl:
                # scrub-equal IS "not observed": once declared volatiles are masked the
                # outputs are behaviorally identical, so the fix this declaration
                # describes is absent -- and letting the scrub branch swallow it hid the
                # case from every signal (fresh-review HIGH: untested interaction).
                fixture["result"] = "declared_divergence_not_observed"
                diverged.append((rec, "declared divergent (%s) but scrub-equal -- "
                                      "identical once volatiles are masked; the declared "
                                      "fix is not in the output" % decl["adr"]))
                continue
            # matchea SOLO tras enmascarar volatiles declarados — cuenta como
            # pass pero se reporta APARTE: el masking jamas es invisible.
            fixture["result"] = "matched_scrubbed"
            matched_scrubbed += 1
        elif decl:
            # diverges AND a fix verdict declared it would: expected, named, never silent.
            fixture["result"] = "expected_divergence"
            fixture["divergence_adr"] = decl["adr"]
            expected_diverged += 1
        else:
            fixture["result"] = "diverged"
            diverged.append((rec, "diff NO aprobado contra .approved"))

    unconsumed = sorted(k for k in divergences if k not in consumed_declarations)
    passed = len(diverged) == 0
    # zero fixtures is NOT-RUN, never CLEAN: a comparison that had nothing to
    # compare is absent evidence — log it as not-run (absence advises, a present
    # divergence blocks). Exit 2 so callers can tell not-run from pass/fail.
    if not received:
        if args.json:
            print(json.dumps({"verdict": "NOT-RUN", "matched": 0, "diverged": [],
                              "note": "no .received fixtures found — run the capture first"},
                             indent=2, ensure_ascii=False))
        else:
            print("GOLDEN-DIFF: NOT-RUN — no .received fixtures, nothing to compare "
                  "(run the capture first; absence is NOT green)")
        sys.exit(2)
    verdict = "CLEAN" if passed else "DIVERGE"
    if args.json:
        print(json.dumps({
            "verdict": verdict, "matched": matched,
            "matched_scrubbed": matched_scrubbed,
            "scrub_rules": len(rules),
            "scrub_substitutions": scrub_counts,
            "golden_labels": _golden_label_counts(fixtures),
            "expected_diverged": expected_diverged,
            "unconsumed_declarations": unconsumed,
            "fixtures": fixtures,
            "diverged": [{"file": f, "reason": r} for f, r in diverged],
        }, indent=2, ensure_ascii=False))
        sys.exit(0 if passed else 1)
    scrub_str = f" · {matched_scrubbed} via scrub" if matched_scrubbed else ""
    print(f"GOLDEN-DIFF: {verdict}  ({matched} match{scrub_str} · {len(diverged)} diverge)")
    if rules:
        subs = sum(scrub_counts.values())
        print(f"  · scrub active: {len(rules)} rule(s) from {GOLDEN_SCRUB_FILE}, "
              f"{subs} substitution(s) — the masking is visible, not magic")
    for f, r in diverged[:12]:
        print(f"  ! {f}: {r}")
    if len(diverged) > 12:
        print(f"  ... and {len(diverged) - 12} more")
    if passed:
        print("  behaviour matches the approved golden byte for byte"
              + (" (volatiles declarados enmascarados)" if matched_scrubbed else ""))
    else:
        print("  the .approved is field truth: if the diff is right a HUMAN approves it — the agent never touches it")
    sys.exit(0 if passed else 1)


# --------------------------------------------------------------------------- #
# doctor  (diagnostico de la instalacion, espiritu flutter doctor)
# --------------------------------------------------------------------------- #
# El engine verifica su PROPIA instalacion: las skills viven al lado de
# qa_ledger.py (sea ~/.claude/skills global o .claude/skills del proyecto), asi
# que doctor inspecciona a sus hermanos. Output ASCII puro: es la herramienta
# de primer contacto en maquinas virgenes - no puede depender del encoding de
# la consola. Exit 1 SOLO con errores; los avisos no fallan (un toolchain
# ausente en la maquina puede vivir en CI).
USCHA_SKILLS = ["uscha-discovery", "uscha-adr-refine",
                   "uscha-reverse-discovery", "uscha-characterize",
                   "uscha-devloop", "uscha-sysdoc", "uscha-rubric",
                   "uscha-mirador", "uscha-status"]
# herramienta primaria por type - su ausencia es AVISO, no error
DOCTOR_TOOLS = {"maven": "mvn", "flutter": "flutter", "python": "pytest",
                "node": "npm", "go": "go", "rust": "cargo", "dotnet": "dotnet",
                "cpp": "ctest", "gradle": "gradle", "swift": "swift"}
# como instalar cada toolchain faltante (el doctor no solo diagnostica: cura)
DOCTOR_FIX = {
    "mvn": "https://maven.apache.org/install.html",
    "flutter": "https://docs.flutter.dev/get-started/install",
    "pytest": "pip install pytest  (https://docs.pytest.org)",
    "npm": "https://nodejs.org/en/download",
    "go": "https://go.dev/dl/",
    "cargo": "https://rustup.rs",
    "dotnet": "https://dotnet.microsoft.com/download",
    "ctest": "https://cmake.org/download/  (ctest ships with CMake)",
    "gradle": "https://gradle.org/install/  (or use the repo gradlew)",
    "swift": "https://www.swift.org/install/",
}
# Two valid hooks: the installer wires the portable .py; the plugin flow ships the .ps1.
# The doctor must recognize EITHER -- checking only the .ps1 (as it did < 1.50.x) reported a
# healthy .py install as broken on every OS, worst on mac/Linux where it ALSO false-warned
# about a powershell the .py never needs. .py is listed first: it is the canonical one.
HOOK_NAMES = ("block-approved-writes.py", "block-approved-writes.ps1")


def _doctor_hook_registered(settings_path):
    """The registered hook basename (.py or .ps1) if the golden-write guard appears under
    PreToolUse, else None. Match by filename substring within the PreToolUse branch -
    disclosed limit: another command that MENTIONS the filename would false-positive
    (contrived, and the failure direction is only an extra [OK] on an advisory)."""
    try:
        with open(settings_path, "r", encoding="utf-8") as fh:
            cfg = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None
    blob = json.dumps(cfg.get("hooks", {}).get("PreToolUse", []))
    return next((n for n in HOOK_NAMES if n in blob), None)


def cmd_doctor(args):
    checks = []   # (nivel 'ok'|'warn'|'error', titulo, detalle)

    def ok(t, d=""):
        checks.append(("ok", t, d))

    def warn(t, d=""):
        checks.append(("warn", t, d))

    def err(t, d=""):
        checks.append(("error", t, d))

    # --- core -------------------------------------------------------------
    py = sys.version_info
    if py >= (3, 8):
        ok(f"Python {py.major}.{py.minor}.{py.micro} (>= 3.8)")
    else:
        err(f"Python {py.major}.{py.minor} - the kit requires 3.8+",
            "install: https://www.python.org/downloads/")
    if shutil.which("git"):
        ok("git on PATH")
    else:
        err("git is not on PATH - gate-check/simplicity/regression use it (--from-git)",
            "install: https://git-scm.com/downloads")

    engine_dir = os.path.dirname(os.path.abspath(__file__))
    home_skills = os.path.join(os.path.expanduser("~"), ".claude", "skills")
    home_plugins = os.path.join(os.path.expanduser("~"), ".claude", "plugins")

    # separador final + normcase: sin ellos '~/.claude/skills-evil' clasificaria
    # como global, y en Windows el case del drive puede diferir
    def _under(child, parent):
        return os.path.normcase(os.path.abspath(child)).startswith(
            os.path.normcase(os.path.abspath(parent)) + os.sep)

    is_plugin = _under(engine_dir, home_plugins)
    is_global = (not is_plugin) and _under(engine_dir, home_skills)
    mode = ("instalacion como PLUGIN (~/.claude/plugins, 1.24.0)" if is_plugin
            else "instalacion global (~/.claude/skills)" if is_global
            else "per-project installation")
    ok(f"engine: {os.path.abspath(__file__)}", mode)

    # --- skills: hermanas del engine ---------------------------------------
    skills_root = os.path.dirname(engine_dir)
    missing, mismatched = [], []
    for s in USCHA_SKILLS:
        smd = os.path.join(skills_root, s, "SKILL.md")
        if not os.path.isfile(smd):
            missing.append(s)
            continue
        try:
            with open(smd, "r", encoding="utf-8") as fh:
                head = fh.read(2048)
            if f"name: {s}" not in head:
                mismatched.append(s)
        except OSError:
            missing.append(s)
    if not missing and not mismatched:
        ok(f"skills {len(USCHA_SKILLS)}/{len(USCHA_SKILLS)} next to the engine",
           ", ".join(USCHA_SKILLS))
    else:
        if missing:
            err(f"skills faltantes en {skills_root}: {', '.join(missing)}",
                "install: copy uscha-kit/.claude/skills/* to ~/.claude/skills/ "
                "(kit README > Installation, option B) - from the uscha-kit-X.Y.Z zip "
                "or from your checkout of the uscha repo")
        if mismatched:
            err(f"SKILL.md con frontmatter name distinto al directorio: {', '.join(mismatched)}")

    # --- hook INV-GOLDEN-01 -------------------------------------------------
    kit_root = os.path.abspath(os.path.join(engine_dir, "..", "..", ".."))
    hook_dirs = [os.path.join(os.path.expanduser("~"), ".claude", "hooks"),
                 os.path.join(kit_root, "hooks")]
    hook_file = next((os.path.join(d, n) for d in hook_dirs for n in HOOK_NAMES
                      if os.path.isfile(os.path.join(d, n))), None)
    settings_paths = [os.path.join(os.path.expanduser("~"), ".claude", "settings.json"),
                      os.path.join(".claude", "settings.json"),
                      os.path.join(".claude", "settings.local.json")]
    registered = next((r for p in settings_paths if os.path.isfile(p)
                       for r in [_doctor_hook_registered(p)] if r), None)
    if is_plugin and os.path.isfile(os.path.join(kit_root, "hooks", "hooks.json")):
        # los hooks del plugin se auto-registran via hooks/hooks.json (1.24.0); desde 1.50.2
        # apunta al .py portable (el .ps1 fue borrado -- PowerShell no existe en mac/Linux)
        registered = registered or "block-approved-writes.py"
    # interpretabilidad atada al hook REAL: el .py corre con el mismo Python que este engine
    # (siempre disponible aca); solo el .ps1 necesita powershell/pwsh. Exigirlo para el .py
    # era el bug -- un install .py sano se reportaba roto, peor en mac/Linux sin pwsh.
    needs_ps = bool(registered and registered.endswith(".ps1"))
    ps_ok = (not needs_ps) or bool(shutil.which("powershell") or shutil.which("pwsh"))
    if hook_file and registered and ps_ok:
        ok("hook INV-GOLDEN-01: present, registered (PreToolUse) and interpretable",
           f"{hook_file} ({registered})")
    elif not hook_file:
        warn("INV-GOLDEN-01 hook not found (neither ~/.claude/hooks nor <kit>/hooks)",
             f"install: `uscha install` copies {HOOK_NAMES[0]} to ~/.claude/hooks/ and "
             f"registers it in settings.json - without it the agent CAN write a .approved "
             f"(mandatory for migrations, profile E)")
    elif not registered:
        warn("hook present but NOT registered in settings.json (PreToolUse)",
             "re-run `uscha install` to write the PreToolUse snippet")
    else:
        warn(f"hook .ps1 registered but no powershell/pwsh on PATH",
             "instala pwsh, o usa el hook .py (portable) via `uscha install`: "
             "https://learn.microsoft.com/powershell/scripting/install/installing-powershell")

    # --- proyecto (si hay config aca) ---------------------------------------
    qa_order = ["code-review", "judgment-day", "improve"]   # default del kit
    cfg_path = args.config or "uscha.config.json"
    if os.path.isfile(cfg_path):
        try:
            cfg = _load(cfg_path)
            defaults = cfg.get("defaults", {})
            repos = cfg.get("repos", [])
            ok(f"project: {cfg_path} v{cfg.get('version', '?')} ({len(repos)} repo(s))")
            acc = defaults.get("acceptance_file")
            if acc and os.path.isfile(acc):
                items, _found = _parse_acceptance_items(acc)
                ids = sum(1 for i in items if i["id"])
                if items and ids:
                    ok(f"ACCEPTANCE: {len(items)} criterion(s), {ids} with a traceable AC-ID")
                elif items:
                    warn(f"ACCEPTANCE without traceable AC-IDs ({len(items)} criterion(s))",
                         "generate it with /uscha-discovery or /uscha-adr-refine "
                         "(format '- [ ] AC-01 - ...') - without IDs the dominant readiness "
                         "dimension falls back to the checkbox ratio")
                else:
                    warn(f"ACCEPTANCE {acc} has no criteria (zero checkboxes)")
            elif acc:
                warn(f"acceptance_file declared but missing: {acc}")
            qa_order = defaults.get("qa_tools_order", qa_order)
            for r in repos:
                tool = DOCTOR_TOOLS.get(r.get("type", ""))
                if not tool:
                    continue
                if r.get("type") == "gradle" and (
                        os.path.isfile(os.path.join(r.get("path", "."), "gradlew"))
                        or os.path.isfile(os.path.join(r.get("path", "."), "gradlew.bat"))):
                    ok(f"toolchain {r['name']} (gradle): gradlew del repo")
                elif shutil.which(tool):
                    ok(f"toolchain {r['name']} ({r.get('type')}): {tool} on PATH")
                else:
                    warn(f"toolchain {r['name']} ({r.get('type')}): {tool} NO esta on PATH",
                         f"install: {DOCTOR_FIX.get(tool, 'see the toolchain docs')} "
                         f"(or it may live only in CI)")
            rub_cfg = defaults.get("rubric", {}) if isinstance(defaults.get("rubric"), dict) else {}
            if rub_cfg.get("file"):
                if os.path.isfile(rub_cfg["file"]):
                    rb_block = _rubric_structure(rub_cfg["file"])
                    if rb_block:
                        warn(f"rubrica {rub_cfg['file']} con estructura invalida",
                             "; ".join(rb_block) + " - ver templates/RUBRIC.md")
                    else:
                        ok(f"rubrica declarada: {rub_cfg['file']}"
                           + (" (GATE declared)" if rub_cfg.get("gate") is True else " (advisory)"))
                else:
                    warn(f"rubrica declarada pero ausente: {rub_cfg['file']}",
                         "install: create it from templates/RUBRIC.md (weighted RB-nn "
                         "criteria + threshold)")
            ledger_path = args.ledger
            if os.path.isfile(ledger_path):
                try:
                    _load(ledger_path)
                    ok(f"ledger {ledger_path}: loads, integrity OK")
                except SystemExit as exc:
                    err(f"ledger {ledger_path} corrupt or mutated", str(exc))
        except SystemExit as exc:
            err(f"{cfg_path} invalid", str(exc))
    else:
        warn(f"no {cfg_path} in this directory",
             "install: copy the kit uscha.config.json to the repo root and declare "
             "your repos/types and your quality bar - only needed to RUN the loop here")

    # --- skills de QA del loop (externas al kit, se orquestan sin traerlas) --
    # sin ellas la fase 3 (QA loop) no corre; chequeables con o sin config.
    missing_qa = [t for t in qa_order
                  if not os.path.isdir(os.path.join(".claude", "skills", t))
                  and not os.path.isdir(os.path.join(home_skills, t))]
    if not missing_qa:
        ok(f"skills de QA del loop instaladas: {', '.join(qa_order)}")
    else:
        warn(f"skills de QA no encontradas como archivo: {', '.join(missing_qa)}",
             "install your QA skills in ~/.claude/skills/ or declare others in "
             "config.defaults.qa_tools_order; if it is a harness built-in "
             "(e.g. code-review), ignore this notice")

    # --- veredicto ----------------------------------------------------------
    n_ok = sum(1 for lv, _, _ in checks if lv == "ok")
    n_warn = sum(1 for lv, _, _ in checks if lv == "warn")
    n_err = sum(1 for lv, _, _ in checks if lv == "error")
    if args.json:
        # ensure_ascii=True a proposito: doctor promete bytes ASCII siempre
        print(json.dumps({"verdict": "ERROR" if n_err else ("WARN" if n_warn else "OK"),
                          "ok": n_ok, "warnings": n_warn, "errors": n_err,
                          "global_install": is_global, "plugin_install": is_plugin,
                          "checks": [{"level": lv, "title": t, "detail": d}
                                     for lv, t, d in checks]},
                         indent=2, ensure_ascii=True))
        sys.exit(1 if n_err else 0)
    print("USCHA DOCTOR - installation diagnosis")
    mark = {"ok": "[OK]", "warn": "[ !]", "error": "[ X]"}
    for lv, t, d in checks:
        print(f"  {mark[lv]} {t}")
        if d:
            print(f"       {d}")
    print(f"RESULT: {n_ok} ok - {n_warn} warning(s) - {n_err} error(s)"
          + ("  -> installation healthy" if not n_err else "  -> errors to fix"))
    sys.exit(1 if n_err else 0)


# --------------------------------------------------------------------------- #
# cli
# --------------------------------------------------------------------------- #
def build_parser():
    p = argparse.ArgumentParser(description="dev-loop QA ledger / measurement engine")
    sub = p.add_subparsers(dest="cmd", required=True)

    pdoc = sub.add_parser(
        "doctor",
        help="diagnose the uscha installation (flutter-doctor spirit): "
             "python/git, skills, hook, project config, per-repo toolchains")
    pdoc.add_argument("--config", default=None,
                      help="project config to inspect (default: ./uscha.config.json)")
    pdoc.add_argument("--ledger", default=DEFAULT_LEDGER)
    pdoc.add_argument("--json", action="store_true")
    pdoc.set_defaults(func=cmd_doctor)

    pri = sub.add_parser(
        "rubric-ingest",
        help="ingest a rubric grader's JSON verdict (vendor-neutral contract; "
             "advisory by default, --gate or defaults.rubric.gate blocks)")
    pri.add_argument("--ledger", default=DEFAULT_LEDGER)
    pri.add_argument("--repo", required=True)
    pri.add_argument("--report", required=True,
                     help='grader JSON: {"criteria":[{"id","verdict","evidence","note"}]}')
    pri.add_argument("--rubric", default=None,
                     help="RUBRIC.md path (default: defaults.rubric.file or ./RUBRIC.md)")
    pri.add_argument("--iteration", type=int, default=1)
    pri.add_argument("--gate", action="store_true",
                     help="a below-threshold score writes a GATED record: blocks "
                          "convergence and caps readiness <=65")
    pri.add_argument("--json", action="store_true")
    pri.set_defaults(func=cmd_rubric_ingest)

    pi = sub.add_parser("init", help="create the ledger from a config file")
    pi.add_argument("--config", required=True)
    pi.add_argument("--out", default=DEFAULT_LEDGER)
    pi.set_defaults(func=cmd_init)

    def add_ledger(sp):
        sp.add_argument("--ledger", default=DEFAULT_LEDGER)

    ps = sub.add_parser("snapshot", help="measure coverage/tests/LOC for a repo")
    add_ledger(ps)
    ps.add_argument("--repo", required=True)
    ps.add_argument("--phase", default="post", choices=["pre", "post"])
    ps.set_defaults(func=cmd_snapshot)

    pc = sub.add_parser("check-coverage", help="exit 0 if >= threshold, 1 if below")
    add_ledger(pc)
    pc.add_argument("--repo", required=True)
    pc.add_argument("--threshold", type=float, default=None)
    pc.set_defaults(func=cmd_check_coverage)

    pl = sub.add_parser("log-step", help="record one QA tool pass")
    add_ledger(pl)
    pl.add_argument("--repo", required=True)
    pl.add_argument("--tool", required=True)
    pl.add_argument("--iteration", type=int, required=True)
    pl.add_argument("--reported", type=int, default=0)
    pl.add_argument("--gated-reported", type=int, default=0)
    pl.add_argument("--fixed", type=int, default=0)
    pl.add_argument("--deferred", type=int, default=0)
    pl.add_argument("--suppressed", type=int, default=0)
    pl.add_argument("--tests-passed", default="true")
    pl.add_argument("--files-changed", type=int, default=0)
    pl.add_argument("--fingerprint", default=None,
                    help="comma-separated stable finding IDs for oscillation detection")
    pl.add_argument("--note", default=None)
    pl.set_defaults(func=cmd_log_step)

    pg = sub.add_parser("ingest-gate",
                        help="parse Checkstyle/PMD/SpotBugs/FindSecBugs reports and "
                             "log static-gate steps automatically")
    add_ledger(pg)
    pg.add_argument("--repo", required=True)
    pg.add_argument("--iteration", type=int, required=True)
    pg.add_argument("--checkstyle", default=None, help="explicit checkstyle-result.xml path")
    pg.add_argument("--pmd", default=None, help="explicit pmd.xml path")
    pg.add_argument("--spotbugs", default=None, help="explicit spotbugsXml.xml path")
    pg.add_argument("--ruff", default=None,
                    help="(type: python) explicit ruff JSON report path")
    pg.add_argument("--mypy", default=None,
                    help="(type: python) explicit mypy text report path")
    pg.add_argument("--eslint", default=None,
                    help="(type: node) explicit eslint JSON report path")
    pg.add_argument("--tsc", default=None,
                    help="(type: node) explicit tsc text report path")
    pg.add_argument("--golangci", default=None,
                    help="(type: go) explicit golangci-lint checkstyle XML path")
    pg.add_argument("--clippy", default=None,
                    help="(type: rust) explicit cargo-clippy JSON-lines report path")
    pg.add_argument("--sarif", default=None,
                    help="(type: dotnet) explicit SARIF report path (Roslyn ErrorLog)")
    pg.add_argument("--clang-tidy", dest="clang_tidy", default=None,
                    help="(type: cpp) explicit clang-tidy text report path")
    pg.add_argument("--detekt", default=None,
                    help="(type: gradle) explicit detekt checkstyle XML path")
    pg.add_argument("--swiftlint", default=None,
                    help="(type: swift) explicit swiftlint checkstyle XML path")
    pg.add_argument("--combined", action="store_true",
                    help="log one combined '<type>-qa-gate' step "
                         "(java-qa-gate for maven) instead of one per linter")
    pg.add_argument("--id-granularity", default=None, choices=["line", "file"],
                    help="finding-ID granularity for fixed/oscillation diffing")
    pg.add_argument("--note", default=None)
    pg.set_defaults(func=cmd_ingest_gate)

    pph = sub.add_parser(
        "phase",
        help="derived workflow state (plan/build/qa/escalated/pr-ready) — "
             "computed from ledger FACTS, never self-declared; --require gates")
    add_ledger(pph)
    pph.add_argument("--repo", required=True)
    pph.add_argument("--require", default=None, choices=PHASES,
                     help="exit 1 unless the DERIVED state equals this "
                          "(merge gate: --require pr-ready)")
    pph.add_argument("--tools-per-cycle", type=int, default=3)
    pph.add_argument("--json", action="store_true")
    pph.set_defaults(func=cmd_phase)

    pv = sub.add_parser("converged", help="advisory convergence check")
    add_ledger(pv)
    pv.add_argument("--repo", required=True)
    pv.add_argument("--tools-per-cycle", type=int, default=3)
    pv.set_defaults(func=cmd_converged)

    po = sub.add_parser("oscillation", help="advisory oscillation check")
    add_ledger(po)
    po.add_argument("--repo", required=True)
    po.add_argument("--tool", required=True)
    po.set_defaults(func=cmd_oscillation)

    pe = sub.add_parser("escalate", help="record a human-escalation event")
    add_ledger(pe)
    pe.add_argument("--repo", required=True)
    pe.add_argument("--reason", required=True)
    pe.set_defaults(func=cmd_escalate)

    pfp = sub.add_parser("fastpath-eval",
                         help="measured fast-path verdict (ADR-003): ALLOW/DENY from the real diff; --intent records it")
    pfp.add_argument("--ledger", default="QA-LEDGER.json")
    pfp.add_argument("--repo", required=True)
    pfp.add_argument("--base", help="base commit/ref; default merge-base HEAD origin/main (fallback main)")
    pfp.add_argument("--intent", help="one sentence, what and why; without it the call is a dry-run")
    pfp.add_argument("--json", action="store_true")
    pfp.set_defaults(func=cmd_fastpath_eval)

    pcu = sub.add_parser("curation-check",
                         help="the INV-CURATION-01 gate: candidates, verdicts, append-only ledger (ADR-009/010)")
    pcu.add_argument("--ledger", default="QA-LEDGER.json")
    pcu.add_argument("--repo", required=True)
    pcu.add_argument("--json", action="store_true")
    pcu.set_defaults(func=cmd_curation_check)

    pfa = sub.add_parser("facts",
                         help="SYSTEM-FACTS: derive repo facts from the artifacts, or --check published claims against them (ADR-012)")
    pfa.add_argument("--out", default="SYSTEM-FACTS.json")
    pfa.add_argument("--check", nargs="*", default=None,
                     help="files whose claims must match the derived facts; exit 1 on drift")
    pfa.set_defaults(func=cmd_facts)

    prt = sub.add_parser("roundtrip",
                         help="advisory: which promoted candidates are traceable in code via uscha-spec ids (ADR-009 slice 2)")
    prt.add_argument("--ledger", default="QA-LEDGER.json")
    prt.add_argument("--repo", required=True)
    prt.add_argument("--json", action="store_true")
    prt.set_defaults(func=cmd_roundtrip)

    pdd = sub.add_parser(
        "discover",
        help="emit discovery/CANDIDATE-DELTA.json: typed observations with content-addressed "
             "OBS ids -- measured/static/narrated, strictly classified (ADR-013)")
    pdd.add_argument("--ledger", default="QA-LEDGER.json")
    pdd.add_argument("--repo", required=True)
    pdd.add_argument("--narrated", default=None,
                     help="JSON list of skill-supplied observations {type, statement, files}; "
                          "the engine classifies them narrated -- it never calls an LLM")
    pdd.add_argument("--path", default=None,
                     help="bound the mechanical scans to one subtree/file (repo-relative); "
                          "a bound matching nothing is a refusal, and it is recorded in "
                          "the delta")
    pdd.add_argument("--acceptance", default=None,
                     help="acceptance file for canonical_match (default: config "
                          "defaults.acceptance_file, else ACCEPTANCE.md)")
    pdd.add_argument("--json", action="store_true")
    pdd.set_defaults(func=cmd_discover)

    pcv = sub.add_parser(
        "curate",
        help="record ONE human verdict (preserve|fix|undefined) for ONE observation as an "
             "append-only ledger object; no batch path exists (ADR-013)")
    pcv.add_argument("--ledger", default="QA-LEDGER.json")
    pcv.add_argument("--repo", required=True)
    pcv.add_argument("--obs", required=True, help="a single OBS id from the delta")
    pcv.add_argument("--verdict", required=True, choices=("preserve", "fix", "undefined"))
    pcv.add_argument("--note", default=None)
    pcv.add_argument("--human", default=None,
                     help="who judged (default: the OS user)")
    pcv.set_defaults(func=cmd_curate)

    ppr = sub.add_parser(
        "promote",
        help="move preserve-verdict observations into discovery/CANONICAL.json with "
             "derived_from lineage; refuses over ANY uncurated OBS (INV-CURATION-01)")
    ppr.add_argument("--ledger", default="QA-LEDGER.json")
    ppr.add_argument("--repo", required=True)
    ppr.add_argument("--json", action="store_true")
    ppr.set_defaults(func=cmd_promote)

    pfv = sub.add_parser(
        "fidelity",
        help="the fidelity vector: 5 measured dimensions + advisory quarantine; an advisory "
             "dimension can NEVER gate (ADR-014, INV-ADVISORY-01)")
    pfv.add_argument("--ledger", default="QA-LEDGER.json")
    pfv.add_argument("--repo", required=True)
    pfv.add_argument("--config", default="uscha.config.json",
                     help="checked for defaults.fidelity.gate -- advisory there is a refusal")
    pfv.add_argument("--ir", action="store_true",
                     help="answer curation_closure as a path query over the IR graph "
                          "(ADR-015); reproduces v0 from the derived index")
    pfv.add_argument("--json", action="store_true")
    pfv.set_defaults(func=cmd_fidelity)

    pie = sub.add_parser(
        "ir-extract",
        help="extract the canonical package into a typed graph (ir/IR.json); what cannot be "
             "typed deterministically is UNTYPED, counted, never guessed (ADR-015)")
    pie.add_argument("--ledger", default="QA-LEDGER.json")
    pie.add_argument("--repo", required=True)
    pie.add_argument("--json", action="store_true")
    pie.set_defaults(func=cmd_ir_extract)

    pir = sub.add_parser(
        "ir-render",
        help="regenerate the human view (ir/IR.md) from the graph; round-trip content-stable "
             "for the structured parts (ADR-015)")
    pir.add_argument("--ledger", default="QA-LEDGER.json")
    pir.add_argument("--repo", required=True)
    pir.set_defaults(func=cmd_ir_render)

    pcmv = sub.add_parser(
        "compile-validate",
        help="validate a COMPILATION.json against a reference IR (ADR-016); only mechanical "
             "violations gate, degeneracy stats are advisory and NEVER block")
    pcmv.add_argument("--ir", required=True,
                      help="the reference IR.json the compilation targets")
    pcmv.add_argument("--compilation", required=True, help="path to COMPILATION.json")
    pcmv.add_argument("--json", action="store_true")
    pcmv.set_defaults(func=cmd_compile_validate)

    pcmi = sub.add_parser(
        "compile-ingest",
        help="record a VALIDATED compilation into the ledger (ADR-016): by-construction "
             "unexplained_code + unresolved_intent as append-only UINT objects + backlog")
    pcmi.add_argument("--ledger", default="QA-LEDGER.json")
    pcmi.add_argument("--repo", required=True)
    pcmi.add_argument("--ir", required=True,
                      help="the reference IR.json the compilation targets")
    pcmi.add_argument("--compilation", required=True, help="path to COMPILATION.json")
    pcmi.add_argument("--json", action="store_true")
    pcmi.set_defaults(func=cmd_compile_ingest)

    pbo = sub.add_parser(
        "bootstrap-oracle",
        help="run a WITHHELD oracle suite against a compiled implementation (ADR-017); exit 0 "
             "iff every case matches its expected exit -- the maker!=checker wall, executable")
    pbo.add_argument("--impl", required=True, help="the compiled implementation to run")
    pbo.add_argument("--oracle", required=True, help="the withheld ORACLE.json case suite")
    pbo.add_argument("--ledger", default=None, help="optional: persist the measured result")
    pbo.add_argument("--repo", default=None, help="repo scope when --ledger is given")
    pbo.add_argument("--json", action="store_true")
    pbo.set_defaults(func=cmd_bootstrap_oracle)

    pbv = sub.add_parser(
        "bootstrap-variance",
        help="structural metrics + pairwise divergence proving independent compilations "
             "genuinely differ (ADR-017); ADVISORY evidence, never a gate")
    pbv.add_argument("--impls", required=True, nargs="+",
                     help="two or more compiled implementations to compare")
    pbv.add_argument("--json", action="store_true")
    pbv.set_defaults(func=cmd_bootstrap_variance)

    pbn = sub.add_parser(
        "bench",
        help="the Diamond Bench (ADR-018): per-archetype verdict table over a set of bounded "
             "systems, aggregating compile-validate + bootstrap-oracle + bootstrap-variance; "
             "model identities anonymized in the headline; deterministic, no LLM")
    pbn.add_argument("--dir", required=True,
                     help="the bench directory; each subdir with an IR.json is an entry")
    pbn.add_argument("--out", default=None, help="write DIAMOND-BENCH.md here")
    pbn.add_argument("--json", action="store_true")
    pbn.set_defaults(func=cmd_bench)

    pcr = sub.add_parser("cleanroom",
                         help="run a command against a CLEAN checkout of one commit in a throwaway worktree (ADR-008)")
    pcr.add_argument("--ledger", default="QA-LEDGER.json")
    pcr.add_argument("--repo", required=True)
    pcr.add_argument("--ref", default=None, help="commit to verify; default HEAD")
    pcr.add_argument("--run", required=True,
                     help="the command to run inside the worktree; the engine never guesses it")
    pcr.add_argument("--setup", default=None, help="optional bootstrap before --run (e.g. npm ci)")
    pcr.add_argument("--json", action="store_true")
    pcr.set_defaults(func=cmd_cleanroom)

    pgc = sub.add_parser("golden-coverage",
                         help="record the MEASURED source files a golden's harness exercises (ADR-006)")
    pgc.add_argument("--harness", required=True, help="script that drives the subject")
    pgc.add_argument("--golden", required=True, help="the golden this map belongs to")
    pgc.add_argument("--dir", default=".", help="repo root holding " + GOLDEN_COVERAGE_FILE)
    pgc.add_argument("--json", action="store_true")
    pgc.set_defaults(func=cmd_golden_coverage)

    psd = sub.add_parser("spec-drift",
                         help="advisory spec-vs-code drift from git commit dates (ADR-005); never gates, exit 0 always")
    psd.add_argument("--ledger", default="QA-LEDGER.json")
    psd.add_argument("--repo", required=True)
    psd.add_argument("--max-lag-days", type=int, default=None,
                     help="override defaults.spec_drift.max_lag_days (default 30)")
    psd.add_argument("--json", action="store_true")
    psd.set_defaults(func=cmd_spec_drift)
    pre = sub.add_parser("resolve-escalation",
                         help="close open escalations for a repo (recorded event; "
                              "lifts the readiness cap)")
    add_ledger(pre)
    pre.add_argument("--repo", required=True)
    pre.add_argument("--note", default=None)
    pre.set_defaults(func=cmd_resolve_escalation)

    plg = sub.add_parser(
        "log-gate",
        help="persist a FACT-gate verdict (golden-diff/gate-check/pit-check/simplicity/regression) "
             "so converged and readiness actually see it")
    add_ledger(plg)
    plg.add_argument("--repo", required=True)
    plg.add_argument("--iteration", type=int, required=True)
    plg.add_argument("--kind", required=True,
                     choices=["golden-diff", "gate-check", "pit-check", "simplicity",
                              "regression", "rubric", "waste"])
    plg.add_argument("--verdict", required=True, choices=["pass", "fail", "not-run"])
    plg.add_argument("--count", type=int, default=1,
                     help="failing finding count (fail only; default 1)")
    plg.add_argument("--note", default=None)
    plg.set_defaults(func=cmd_log_gate)

    pfb = sub.add_parser(
        "flag-blocker",
        help="record (or --resolve) a CONSTITUTION/invariant breach as a BLOCKER "
             "(caps readiness <=65, blocks convergence)")
    add_ledger(pfb)
    pfb.add_argument("--repo", required=True)
    pfb.add_argument("--kind", default="constitution",
                     help="free-text breach kind (default: constitution)")
    pfb.add_argument("--iteration", type=int, default=1)
    pfb.add_argument("--note", default=None,
                     help="what was breached (required unless --resolve)")
    pfb.add_argument("--resolve", action="store_true",
                     help="clear the blocker (writes a clean record for the same kind)")
    pfb.add_argument("--escape-analysis", default=None,
                     help="REQUIRED with --resolve: which gate/test should have "
                          "caught this and what was done (new test / new gate / "
                          "sibling-bug sweep) — find every bug ONCE")
    pfb.set_defaults(func=cmd_flag_blocker)

    ppf = sub.add_parser(
        "production-finding",
        help="record/resolve post-merge production feedback as discovery intake")
    add_ledger(ppf)
    ppf.add_argument("--id", default=None, help="PF-nnn to resolve")
    ppf.add_argument("--repo", default=None)
    ppf.add_argument("--severity", default="HIGH", choices=SEVERITY_ORDER)
    ppf.add_argument("--source", default="production",
                     help="where the finding came from (sentry, user, support, prod-log, ...)")
    ppf.add_argument("--title", default=None)
    ppf.add_argument("--evidence", default=None,
                     help="short evidence pointer; do not paste secrets or PII")
    ppf.add_argument("--note", default=None)
    ppf.add_argument("--resolve", action="store_true")
    ppf.set_defaults(func=cmd_production_finding)

    psd = sub.add_parser(
        "spec-doubt",
        help="record/resolve a SPEC doubt/SPEC-WRONG finding that requires human review")
    add_ledger(psd)
    psd.add_argument("--id", default=None, help="SD-nnn to resolve")
    psd.add_argument("--repo", default=None)
    psd.add_argument("--kind", default="spec-doubt",
                     choices=["spec-doubt", "spec-wrong", "ambiguous", "missing-acceptance"])
    psd.add_argument("--severity", default="HIGH", choices=SEVERITY_ORDER)
    psd.add_argument("--spec", default=None, help="SPEC/AC/ADR pointer involved")
    psd.add_argument("--note", default=None)
    psd.add_argument("--evidence", default=None)
    psd.add_argument("--decision", default=None,
                     help="human decision when resolving (SPEC amended, accepted-as-is, ...)")
    psd.add_argument("--resolve", action="store_true")
    psd.set_defaults(func=cmd_spec_doubt)

    pscr = sub.add_parser(
        "spec-change-request",
        help="record/resolve a human SPEC/ADR change request backed by evidence")
    add_ledger(pscr)
    pscr.add_argument("--id", default=None, help="SCR-nnn to resolve")
    pscr.add_argument("--repo", default=None)
    pscr.add_argument("--source", default=None, help="finding/doubt/evidence id that triggered it")
    pscr.add_argument("--requested-change", default=None)
    pscr.add_argument("--evidence", default=None)
    pscr.add_argument("--spec", default=None, help="SPEC/AC pointer to amend")
    pscr.add_argument("--adr", default=None, help="ADR pointer to amend")
    pscr.add_argument("--note", default=None)
    pscr.add_argument("--resolve", action="store_true")
    pscr.add_argument("--decision", default=None, choices=["accepted", "rejected", "superseded"],
                      help="human decision when resolving")
    pscr.add_argument("--amended", default=None, help="amended SPEC/ADR path or pointer")
    pscr.set_defaults(func=cmd_spec_change_request)

    prc = sub.add_parser(
        "regression-check",
        help="Find Bugs Once: closing findings without touching tests is "
             "NARRATED, never measured (advisory; --strict gates)")
    add_ledger(prc)
    prc.add_argument("--repo", required=True)
    prc.add_argument("--fixed", type=int, default=None,
                     help="findings closed by the fixing diff (default: sum of "
                          "'fixed' across the repo's most recent iteration)")
    prc.add_argument("--diff", help="path to the FIXING unified diff (else --from-git or stdin)")
    prc.add_argument("--from-git", action="store_true",
                     help="run `git diff --unified=0 <base>` for the diff")
    prc.add_argument("--base", default=None, help="git base ref (default HEAD)")
    prc.add_argument("--strict", action="store_true",
                     help="exit 1 on NARRATED closure (no test evidence)")
    prc.add_argument("--json", action="store_true")
    prc.set_defaults(func=cmd_regression_check)

    pm = sub.add_parser("summary", help="emit the final retrospective metrics")
    add_ledger(pm)
    pm.add_argument("--json", action="store_true")
    pm.set_defaults(func=cmd_summary)

    pr = sub.add_parser("readiness", help="project readiness KPI (state, with hard caps)")
    add_ledger(pr)
    pr.add_argument("--acceptance", default=None,
                    help="path to the acceptance task list (markdown checkboxes); "
                         "overrides config.defaults.acceptance_file")
    pr.add_argument("--section", default=None,
                    help="only count checkboxes under headings matching this text")
    pr.add_argument("--tools-per-cycle", type=int, default=3)
    pr.add_argument("--json", action="store_true")
    pr.add_argument("--record", action="store_true",
                    help="append the current readiness score to the ledger's "
                         "readiness_history (opt-in; feeds the mirador time-lapse). "
                         "Default is read-only.")
    pr.add_argument("--verbose", action="store_true",
                    help="expand the collapsed sub-scores (dimensions table, "
                         "acceptance/coverage summary, churn, per-repo breakdown); "
                         "default is the single-verdict view (anti-ceremony)")
    pr.set_defaults(func=cmd_readiness)

    pep = sub.add_parser("execution-policy",
                         help="print model/effort routing metadata for Uscha phases "
                              "(read-only; not part of readiness)")
    add_ledger(pep)
    pep.add_argument("--phase", default=None,
                     help="phase key to print (idea|disc|spec|adr|build|qa|verify|prod). "
                          "If omitted, prints all phases.")
    pep.add_argument("--json", action="store_true")
    pep.set_defaults(func=cmd_execution_policy)

    pdash = sub.add_parser("dashboard",
                           help="mirador: bird's-eye status as the template DATA "
                                "contract (read-only, deterministic)")
    add_ledger(pdash)
    pdash.add_argument("--acceptance", default=None,
                       help="acceptance task list (markdown); overrides config default")
    pdash.add_argument("--section", default=None)
    pdash.add_argument("--tools-per-cycle", type=int, default=3)
    pdash.add_argument("--adr-dir", default="docs/adr",
                       help="directory globbed for ADR markdown (mirador ADR panel)")
    pdash.add_argument("--json", action="store_true")
    pdash.set_defaults(func=cmd_dashboard)

    pb = sub.add_parser("rebuild",
                        help="rebuild test: is the SPEC complete enough to "
                             "regenerate the system? (completeness, not correctness)")
    pb.add_argument("--mode", required=True, choices=["baseline", "compare"])
    pb.add_argument("--config", default="uscha.config.json",
                    help="(baseline) config file listing repos")
    pb.add_argument("--baseline", default=DEFAULT_REBUILD_BASELINE,
                    help="(compare) signature file written by --mode baseline")
    pb.add_argument("--out", default=DEFAULT_REBUILD_BASELINE,
                    help="(baseline) where to write the signature")
    pb.add_argument("--acceptance", default=None,
                    help="acceptance task list; overrides config.defaults.acceptance_file")
    pb.add_argument("--section", default=None,
                    help="only count acceptance checkboxes under headings matching this text")
    pb.add_argument("--coverage-tolerance", type=float, default=None,
                    help="(baseline) pct points the rebuilt coverage may drop (default 5)")
    pb.add_argument("--json", action="store_true")
    pb.set_defaults(func=cmd_rebuild)

    ps2 = sub.add_parser(
        "simplicity-check",
        help="Reduce gate: score diff minimality/complexity over a unified diff")
    ps2.add_argument("--diff", help="path to a unified diff (else --from-git or stdin)")
    ps2.add_argument("--from-git", action="store_true",
                     help="run `git diff --unified=0 <base>` for the diff")
    ps2.add_argument("--base", default=None, help="git base ref (default HEAD)")
    ps2.add_argument("--config", default="uscha.config.json",
                     help="read defaults.simplicity budgets from here if present")
    ps2.add_argument("--max-lines-added", dest="max_lines_added", type=int)
    ps2.add_argument("--max-net-lines", dest="max_net_lines", type=int)
    ps2.add_argument("--max-files-changed", dest="max_files_changed", type=int)
    ps2.add_argument("--max-nesting-depth", dest="max_nesting_depth", type=int)
    ps2.add_argument("--max-hunk-added", dest="max_hunk_added", type=int)
    ps2.add_argument("--max-new-abstractions", dest="max_new_abstractions", type=int)
    ps2.add_argument("--max-abstraction-density", dest="max_abstraction_density",
                     type=float, default=None)
    ps2.add_argument("--indent-width", dest="indent_width", type=int)
    ps2.add_argument("--json", action="store_true")
    ps2.set_defaults(func=cmd_simplicity_check)

    pw = sub.add_parser(
        "waste-check",
        help="REUSE-FIRST gate: deterministic Type-1/2 clone detection of the diff "
             "vs the repo (the duplication simplicity-check cannot see). Advisory by "
             "default; gates only with --gate or defaults.waste.gate")
    pw.add_argument("--diff", help="path to a unified diff (else --from-git or stdin)")
    pw.add_argument("--from-git", action="store_true",
                    help="run `git diff --unified=0 <base>` for the diff")
    pw.add_argument("--base", default=None, help="git base ref (default HEAD)")
    pw.add_argument("--repo-root", dest="repo_root", default=".",
                    help="repo root to scan for clones-vs-existing (default .)")
    pw.add_argument("--config", default="uscha.config.json",
                    help="read defaults.waste budgets from here if present")
    pw.add_argument("--window-size", dest="window_size", type=int, default=None,
                    help="normalized significant lines per window (default 5)")
    pw.add_argument("--gate", action="store_true",
                    help="make a WASTEFUL verdict exit 1 (default: advisory exit 0)")
    pw.add_argument("--json", action="store_true")
    pw.set_defaults(func=cmd_waste_check)

    pp = sub.add_parser(
        "pit-check",
        help="mutation gate: test EFFECTIVENESS from a PIT mutations.xml (coverage lies)")
    pp.add_argument("--report", default=None,
                    help="path to PIT mutations.xml (default: newest target/pit-reports/*)")
    pp.add_argument("--min-score", dest="min_score", type=float, default=60.0,
                    help="min mutation score to pass (default 60)")
    pp.add_argument("--top", type=int, default=8, help="how many hotspots to list")
    pp.add_argument("--json", action="store_true")
    pp.set_defaults(func=cmd_pit_check)

    pgc = sub.add_parser(
        "gate-check",
        help="gate integrity: flag a diff that WEAKENS the test/lint/coverage apparatus "
             "or ADDS secrets (private keys / cloud tokens / key containers block as facts)")
    pgc.add_argument("--diff", help="path to a unified diff (else --from-git or stdin)")
    pgc.add_argument("--from-git", action="store_true",
                     help="run `git diff --unified=0 <base>` for the diff")
    pgc.add_argument("--base", default=None, help="git base ref (default HEAD)")
    pgc.add_argument("--strict", action="store_true",
                     help="also fail (exit 1) on soft flags: suppressions / removed "
                          "assertions / generic password-token literals")
    pgc.add_argument("--ledger", default=DEFAULT_LEDGER,
                     help="(with --repo) ledger for the measured test-count cross-check")
    pgc.add_argument("--repo", default=None,
                     help="optional: compare the last two snapshots' executed-test totals "
                          "(a measured drop flags REVIEW — no regex can miss it)")
    pgc.add_argument("--json", action="store_true")
    pgc.set_defaults(func=cmd_gate_check)

    psc = sub.add_parser(
        "spec-check",
        help="spec-quality gate: lint a SPEC/ACCEPTANCE for structure/testability BEFORE generation")
    psc.add_argument("--spec", action="append",
                     help="path to a SPEC/ACCEPTANCE markdown (repeatable; else stdin)")
    psc.add_argument("--rubric", default=None,
                     help="validate RUBRIC.md structure as FACTS: missing file / zero "
                          "positive criteria / duplicate RB-nn IDs / bad threshold block")
    psc.add_argument("--acceptance", default=None,
                     help="validate ACCEPTANCE traceability (AC-n IDs): missing "
                          "file / zero criteria / zero traceable / duplicate "
                          "IDs block as structural FACTS")
    psc.add_argument("--strict", action="store_true",
                     help="also fail (exit 1) on soft findings: untestable criteria / stack named")
    psc.add_argument("--json", action="store_true")
    psc.set_defaults(func=cmd_spec_check)

    pgd = sub.add_parser(
        "golden-diff",
        help="golden/approval gate: byte-compare *.received.* vs *.approved.* (fact, not judgment)")
    pgd.add_argument("--dir", default=None, help="root to scan for .received/.approved (default cwd)")
    pgd.add_argument("--labels", default=None,
                     help="optional golden-labels.json classifying approved fixtures as intended or observed-accidental")
    pgd.add_argument("--json", action="store_true")
    pgd.set_defaults(func=cmd_golden_diff)

    return p


def main(argv=None):
    # Windows console defaults to a legacy codepage (cp1252); force UTF-8 so the
    # ledger's own output (accents, em-dashes) prints cleanly instead of mojibake.
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:
            pass
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except BrokenPipeError:
        # downstream pipe (head/grep) closed early; not an error
        try:
            sys.stdout.close()
        except Exception:
            pass
        os._exit(0)


if __name__ == "__main__":
    main()
