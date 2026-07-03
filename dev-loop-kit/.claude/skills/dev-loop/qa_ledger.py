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
  qa_ledger.py init        --config dev-loop.config.json [--out QA-LEDGER.json]
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
  qa_ledger.py ingest-gate --repo backend-api --iteration 1 [--combined]
  qa_ledger.py ingest-gate --repo data-lib --iteration 1 \
                           [--ruff reports/ruff.json --mypy reports/mypy.txt]
  qa_ledger.py log-gate    --repo backend-api --iteration 1 --kind golden-diff \
                           --verdict pass|fail|not-run [--count N] [--note "..."]
  qa_ledger.py flag-blocker --repo backend-api --kind constitution --note "INV-XX breached" \
                           [--resolve]
  qa_ledger.py rebuild --mode baseline --config dev-loop.config.json [--out REBUILD-BASELINE.json]
  qa_ledger.py rebuild --mode compare  --baseline REBUILD-BASELINE.json [--json]
  qa_ledger.py simplicity-check --diff changes.diff [--config dev-loop.config.json] [--json]
  qa_ledger.py simplicity-check --from-git --base main
  qa_ledger.py pit-check --report target/pit-reports/*/mutations.xml [--min-score 60] [--json]
  qa_ledger.py gate-check --from-git --base main [--strict] [--json]
  qa_ledger.py spec-check --spec SPEC.md [--spec ACCEPTANCE.md] [--strict] [--json]
  qa_ledger.py golden-diff [--dir .] [--json]
"""

import argparse
import glob
import hashlib
import json
import os
import re
import sys
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
        root = ET.parse(xml_path).getroot()
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
            "report_found": bool(files)}


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
            "report_found": bool(lcov)}


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
        root = ET.parse(path).getroot()
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
            "report_found": True}


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
            "report_found": True}


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
            "report_found": bool(files)}


def coverage(repo_path, repo_type):
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
def _perclass_xml_count(patterns):
    """Sum per-class JUnit XML files (surefire/failsafe/gradle test-results):
    each file's root is a <testsuite> carrying the counters."""
    tests = failures = errors = skipped = 0
    seen = set()
    for pat in patterns:
        for f in glob.glob(pat, recursive=True):
            if f in seen:
                continue
            seen.add(f)
            try:
                root = ET.parse(f).getroot()
            except ET.ParseError:
                continue
            tests += int(root.get("tests", 0))
            failures += int(root.get("failures", 0))
            errors += int(root.get("errors", 0))
            skipped += int(root.get("skipped", 0))
    executed = tests - skipped
    return {"total": tests, "executed": executed, "failures": failures,
            "errors": errors, "skipped": skipped, "passed": executed - failures - errors,
            "report_found": bool(seen)}


def maven_test_count(repo_path):
    return _perclass_xml_count([
        os.path.join(repo_path, "**", "target", "surefire-reports", "TEST-*.xml"),
        os.path.join(repo_path, "**", "target", "failsafe-reports", "TEST-*.xml"),
    ])


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


# tolerante a los limites de naming de cada lenguaje: test_ac1_x (python/go,
# sin '-'), testAC01X (java camelCase), "AC-01: ..." (nombres libres).
# OJO: \b no sirve — '_' es word character y test_ac1 quedaria invisible;
# boundaries explicitos: separador no-alfanumerico, o salto camelCase a 'AC'.
_AC_TAG = re.compile(
    r"(?:(?<![A-Za-z0-9])[Aa][Cc]|(?<=[a-z])AC)[-_]?0*(\d+)(?!\d)")


def _ac_tags(repo_path, repo_type):
    """Tags AC-n leidos de los NOMBRES de testcase en los reportes JUnit que el
    engine ya ingiere. Devuelve {'AC-n': {'green': x, 'red': y}}. Un criterio
    cierra MEDIDO solo con >=1 testcase verde y 0 rojos (evidencia roja veta:
    fail-closed). Testcases skipped no cuentan para ningun lado.

    LIMITE CONOCIDO (heredado de junit_test_count, ahora con blast radius mayor
    porque vetea/cierra un AC en vez de aproximar un conteo): maven/gradle
    globbean TEST-*.xml recursivo sin chequeo de freshness — un reporte stale
    de un test renombrado/borrado (surefire no lo limpia sin `mvn clean`) puede
    vetear un AC para siempre (rojo stale) o mantenerlo cerrado sin evidencia
    vigente (verde stale). Mitigacion real (mtime + correlacion con el arbol de
    fuentes) queda diferida — no hay forma barata de distinguir "stale" de
    "vigente" sin esa correlacion."""
    tags = {}
    for f in _junit_files_for(repo_path, repo_type):
        try:
            root = ET.parse(f).getroot()
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
                d = tags.setdefault(f"AC-{int(num)}", {"green": 0, "red": 0})
                d[status] += 1
    return tags


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
        try:
            root = ET.parse(f).getroot()
        except (ET.ParseError, OSError):
            continue
        if _local(root.tag) == "testsuite":
            suites = [root]
        else:
            suites = list(_iter_local(root, "testsuite"))
        t = fl = er = sk = 0
        for s in suites:
            t += int(s.get("tests", 0))
            fl += int(s.get("failures", 0))
            er += int(s.get("errors", 0))
            sk += int(s.get("skipped", 0))
        if _local(root.tag) == "testsuites":
            # gotestsum puts `errors` ONLY on the <testsuites> root (a package
            # that fails to BUILD has root errors>0 and no suite) — take the max
            # of root attrs vs child sums so a broken build never reads green.
            t = max(t, int(root.get("tests", 0)))
            fl = max(fl, int(root.get("failures", 0)))
            er = max(er, int(root.get("errors", 0)))
            sk = max(sk, int(root.get("skipped", 0)))
        tests += t
        failures += fl
        errors += er
        skipped += sk
    executed = tests - skipped
    return {"total": tests, "executed": executed, "failures": failures,
            "errors": errors, "skipped": skipped,
            "passed": executed - failures - errors, "report_found": bool(files)}


def test_count(repo_path, repo_type):
    if repo_type == "maven":
        return maven_test_count(repo_path)
    if repo_type == "gradle":
        return gradle_test_count(repo_path)
    if repo_type == "swift":
        # SwiftPM writes Swift Testing results to a SEPARATE file next to the
        # XCTest one — both must count or a Swift-6 package reads tests=0.
        return junit_test_count(repo_path, extra_files=[
            os.path.join(repo_path, "reports", "junit-swift-testing.xml"),
            os.path.join(repo_path, "junit-swift-testing.xml")])
    if repo_type in ("python", "node", "go", "rust", "dotnet", "cpp"):
        # go: gotestsum · rust: cargo-nextest · dotnet: JUnit logger ·
        # cpp: ctest --output-junit / gtest
        return junit_test_count(repo_path)
    return flutter_test_count(repo_path)


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
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return out
    for f in _iter_local(root, "file"):
        fname = f.get("name", "?")
        for e in _iter_local(f, "error"):
            sev = CHECKSTYLE_SEVERITY.get((e.get("severity") or "warning").lower(), "MEDIUM")
            rule = (e.get("source") or "?").split(".")[-1]
            if tool != "checkstyle":
                fid = _mk_id_rel(tool, rule, _node_rel(fname, base),
                                 e.get("line", "0"), granularity)
            else:
                fid = _mk_id(tool, rule, fname, e.get("line", "0"), granularity)
            out.append((fid, sev, tool))
    return out


def parse_pmd(path, granularity):
    out = []
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return out
    for f in _iter_local(root, "file"):
        fname = f.get("name", "?")
        for v in _iter_local(f, "violation"):
            try:
                pr = int(v.get("priority", "3"))
            except ValueError:
                pr = 3
            sev = PMD_PRIORITY.get(pr, "MEDIUM")
            rule = v.get("rule", "?")
            out.append((_mk_id("pmd", rule, fname, v.get("beginline", "0"), granularity),
                        sev, "pmd"))
    return out


def parse_spotbugs(path, granularity):
    """SpotBugs report. FindSecBugs findings (category SECURITY) are split out
    under tool 'findsecbugs' and floored to HIGH severity."""
    out = []
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return out
    for b in _iter_local(root, "BugInstance"):
        try:
            pr = int(b.get("priority", "2"))
        except ValueError:
            pr = 2
        sev = SPOTBUGS_PRIORITY.get(pr, "MEDIUM")
        cat = (b.get("category") or "").upper()
        btype = b.get("type", "?")
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


def parse_ruff(path, granularity):
    """`ruff check --output-format=json` — a JSON array of finding objects."""
    out = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return out
    if not isinstance(data, list):
        return out
    for item in data:
        if not isinstance(item, dict):
            continue
        code = item.get("code")
        fname = item.get("filename") or "?"
        line = (item.get("location") or {}).get("row", 0)
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
    """`eslint --format json` — array of {filePath, messages:[{ruleId, severity,
    line, fatal}]}. fatal:true (parse error) -> HIGH always. ruleId null WITHOUT
    fatal (e.g. unused eslint-disable directives in ESLint 9) follows the message
    severity — never a false blocker. severity 2 -> HIGH, 1 -> MEDIUM; rules from
    security plugins ('security/...') floored to HIGH."""
    out = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return out
    if not isinstance(data, list):
        return out
    for entry in data:
        if not isinstance(entry, dict):
            continue
        fname = _node_rel(entry.get("filePath"), base)
        for msg in entry.get("messages") or []:
            if not isinstance(msg, dict):
                continue
            rule = msg.get("ruleId")
            if msg.get("fatal"):
                sev, rule = "HIGH", "syntax-error"
            elif rule is None:
                sev = "HIGH" if msg.get("severity") == 2 else "MEDIUM"
                rule = "unused-directive"
            else:
                sev = "HIGH" if msg.get("severity") == 2 else "MEDIUM"
                if rule.startswith("security/"):
                    sev = _bump(sev, "HIGH")
            out.append((_mk_id_rel("eslint", rule, fname, msg.get("line", 0),
                                   granularity), sev, "eslint"))
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
    """`cargo clippy --message-format=json` — JSON Lines; each compiler-message
    carries message.level (error/warning), message.code.code (e.g. 'clippy::x';
    null for plain rustc compile errors — real breakage, HIGH always) and spans.
    error -> HIGH, warning -> MEDIUM; note/help lines are skipped.
    Diagnostics WITHOUT a primary span are rustc's end-of-run summaries
    ('N warnings emitted', 'aborting due to ...') — real compile errors always
    carry a span, so span-less lines are skipped BEFORE the code-null check
    (else every warning run grows a phantom HIGH 'compile-error' and the gate
    can never converge). Repeats across compilation targets (lib/bin/test)
    are deduped by finding ID."""
    out = []
    seen = set()
    try:
        fh = open(path, "r", encoding="utf-8", errors="replace")
    except OSError:
        return out
    with fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except ValueError:
                continue
            if not isinstance(obj, dict) or obj.get("reason") != "compiler-message":
                continue
            msg = obj.get("message") or {}
            level = msg.get("level")
            if level not in ("error", "warning"):
                continue
            span = next((s for s in (msg.get("spans") or [])
                         if isinstance(s, dict) and s.get("is_primary")), None)
            if span is None:
                continue  # span-less = summary diagnostic, not a finding
            code = (msg.get("code") or {}).get("code") if msg.get("code") else None
            if code is None:
                sev, rule = "HIGH", "compile-error"
            else:
                sev = "HIGH" if level == "error" else "MEDIUM"
                rule = code
            fname = span.get("file_name") or "?"
            line = span.get("line_start", 0)
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
    except (OSError, ValueError):
        return out
    if not isinstance(data, dict):
        return out
    for run in data.get("runs") or []:
        if not isinstance(run, dict):
            continue
        for res in run.get("results") or []:
            if not isinstance(res, dict):
                continue
            if res.get("suppressions") or res.get("suppressionStates"):
                continue
            sev = sev_map.get((res.get("level") or "warning").lower(), "MEDIUM")
            rule = res.get("ruleId") or "?"
            fname, line = "?", 0
            locs = res.get("locations") or []
            if locs and isinstance(locs[0], dict):
                loc = locs[0]
                phys = loc.get("physicalLocation") or {}
                art = phys.get("artifactLocation") or {}
                uri = art.get("uri")
                region = phys.get("region") or {}
                if not uri:  # SARIF v1 fallback
                    v1 = loc.get("resultFile") or loc.get("analysisTarget") or {}
                    uri = v1.get("uri")
                    region = v1.get("region") or {}
                if uri:
                    fname = _sarif_rel(uri, base)
                line = region.get("startLine", 0)
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
def cmd_init(args):
    cfg = _load(args.config)
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
    }
    _save(args.out, ledger)
    print(f"[qa_ledger] initialized {args.out} "
          f"(run {ledger['run_id']}, {len(ledger['repos'])} repos, "
          f"coverage_threshold={defaults.get('coverage_threshold')})")


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
    print(f"[qa_ledger] snapshot {args.repo} ({args.phase}): "
          f"coverage={cov['pct']}% (found={cov['report_found']}), "
          f"tests={tests['total']} (found={tests['report_found']}), "
          f"prod_loc={loc['prod_loc']}, test_loc={loc['test_loc']}")


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
    """Persist a FACT-gate verdict (golden-diff / gate-check / pit-check / simplicity)
    into the ledger, so 'facts may block' is enforced by the engine, not by goodwill.
      fail    -> BLOCKER record: trips the <=65 readiness cap AND blocks convergence.
      pass    -> clean record for the same tool: credits the fix, convergence sees clean.
      not-run -> a steps event ONLY, never an iterations record: absence is not
                 evidence — it neither reads as clean nor fakes a red (last state stands).
    """
    ledger = _load(args.ledger)
    node = _repo_node(ledger, args.repo)
    tool = f"gate:{args.kind}"
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
    --resolve writes a clean record for the same kind (latest-per-tool wins)."""
    ledger = _load(args.ledger)
    node = _repo_node(ledger, args.repo)
    tool = f"blocker:{args.kind}"
    failing = not args.resolve
    if failing and not args.note:
        raise SystemExit("[qa_ledger] flag-blocker requires --note describing the breach.")
    rec = _append_gate_record(ledger, node, args.repo, tool, args.iteration,
                              failing, 1, args.note)
    _save(args.ledger, ledger)
    if failing:
        print(f"[qa_ledger] {args.repo}/{tool}: BLOCKER logged — {args.note} "
              f"(readiness capped <=65, convergence blocked until --resolve)")
    else:
        print(f"[qa_ledger] {args.repo}/{tool}: resolved — gate cleared "
              f"(step #{rec['n']})")


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


def cmd_escalate(args):
    ledger = _load(args.ledger)
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
        "by_tool": _tool_rollup(ledger),
        "by_repo": repos,
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
    print(f"aggregate coverage: {a['coverage_pct']}%   "
          f"prod LOC: {a['prod_loc']}   test LOC: {a['test_loc']}   "
          f"tests: {a['test_count']}   tests/kLOC: {a['test_per_kloc']}")
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
    capped = score
    reason = None
    for label, ceiling in caps_active:
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
    gated_open, sev = _gate_open_and_sev(node)
    # silence is not success: for a lint-capable repo (every type the ingest
    # parsers support) with NO static-gate record ever logged, the dimension is
    # UNMEASURED (0.0), not a perfect 1.0. A tool that didn't run is never green.
    static_unmeasured = (rtype in ("maven", "python", "node", "go", "rust",
                                   "dotnet", "cpp", "gradle", "swift")
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
    final, cap_reason = _apply_caps(raw, caps_active)
    return {
        "score": round(final, 1), "raw": round(raw, 1), "status": _band(final),
        "cap_reason": cap_reason,
        "dims": {"coverage": round(cov_dim, 3), "static_gate": round(static_dim, 3),
                 "convergence": round(conv_dim, 3)},
        "facts": {"coverage_pct": cov["pct"], "coverage_threshold": threshold,
                  "gated_open": gated_open, "severity": sev, "converged": converged,
                  "convergence_reasons": creasons, "tests_red": tests_red,
                  "static_unmeasured": static_unmeasured},
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


def cmd_readiness(args):
    ledger = _load(args.ledger)
    defaults = ledger["config"].get("defaults", {})
    weights = {**DEFAULT_WEIGHTS, **defaults.get("readiness_weights", {})}
    caps = {**DEFAULT_CAPS, **defaults.get("readiness_caps", {})}
    zero_at = defaults.get("static_gate_zero_at", DEFAULT_STATIC_ZERO_AT)
    k = args.tools_per_cycle
    threshold = defaults.get("coverage_threshold", 60)

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
    for rcfg in ledger["config"].get("repos", []):
        for cid, v in _ac_tags(rcfg.get("path", "."),
                               rcfg.get("type", "maven")).items():
            d = ac_tags.setdefault(cid, {"green": 0, "red": 0})
            d["green"] += v["green"]
            d["red"] += v["red"]

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

    conv_flags = [r["facts"]["converged"] for r in repos.values()]
    conv_dim = (sum(1 for c in conv_flags if c) / len(conv_flags)) if conv_flags else 0.0

    # integration dimension (feature-level)
    integ_enabled = ledger["config"].get("integration", {}).get("enabled", False)
    integ_steps = [s for s in ledger["integration"]["iterations"]]
    if integ_enabled:
        if integ_steps:
            last = integ_steps[-1]
            integ_dim = 1.0 if (last.get("gated_reported", 0) == 0
                                and last.get("tests_passed") is not False) else 0.0
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
    caps_active = []
    if any(r["facts"]["tests_red"] for r in repos.values()):
        caps_active.append(("tests red in a repo", caps["tests_red"]))
    blk = agg_sev.get("BLOCKER", 0) + agg_sev.get("CRITICAL", 0)
    if blk:
        caps_active.append((f"{blk} BLOCKER/CRITICAL open", caps["blocker_critical"]))
    if any(not e.get("resolved_at") for e in ledger.get("escalations", [])):
        caps_active.append(("unresolved escalation", caps["escalation"]))
    if not acc_found:
        caps_active.append(("acceptance file not found", caps["blocker_critical"]))
    final, cap_reason = _apply_caps(raw, caps_active)

    # plateau / stop-signal (ADVISORY: recomienda, jamas gatea)
    qa_order = defaults.get("qa_tools_order")
    stalled_repos = sorted(n for n, node in ledger["repos"].items()
                           if _is_stalled(node, qa_order))
    stop_signal = (bool(conv_flags) and all(conv_flags)
                   and not caps_active and total_open == 0)

    # churn (separate from readiness)
    tool_roll = _tool_rollup(ledger)
    cycles = max([s.get("iteration", 0) for node in ledger["repos"].values()
                  for s in node["iterations"]] + [0])
    regressions = sum((s.get("new_regressions") or 0) for node in ledger["repos"].values()
                      for s in node["iterations"])

    out = {
        "score": round(final, 1), "raw": round(raw, 1), "status": _band(final),
        "cap_reason": cap_reason,
        "weights": {d: weights[d] for d in dims},
        "dimensions": {d: {"raw": round(v, 3),
                           "contribution": round(weights[d] * v / wsum * 100, 1)}
                       for d, v in dims.items()},
        "acceptance": {"done": done, "total": total, "found": acc_found,
                       "file": acc_path, "section": args.section,
                       "traceable": acc_traceable, "ids": len(ac_ids),
                       "untagged": ac_untagged, "duplicate_ids": dupe_ids,
                       "measured_closed": measured_closed,
                       "narrated_only": narrated_only,
                       "measured_unchecked": measured_unchecked},
        "facts": {"coverage_pct": round(agg_cov_pct, 2), "coverage_threshold": threshold,
                  "gated_open": total_open, "severity": agg_sev,
                  "repos_converged": f"{sum(conv_flags)}/{len(conv_flags)}",
                  "static_unmeasured_repos": unmeasured_repos},
        "churn": {"max_cycle": cycles, "new_regressions": regressions,
                  "by_tool_fixed_pct": {t: x["fixed_pct"] for t, x in tool_roll.items()}},
        "advice": {"stalled_repos": stalled_repos, "stop_signal": stop_signal},
        "by_repo": repos,
    }
    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return

    cap_str = f"  (capped at {int(final)}: {cap_reason})" if cap_reason else ""
    print(f"READINESS: {out['score']}/100 — {out['status']}{cap_str}")
    if not acc_found:
        print(f"  ! acceptance file not found: {acc_path or '(unset)'} — ADR dimension = 0")
    if acc_found and not total:
        print(f"  ! acceptance encontrado pero 0 criterios en scope "
              f"(--section {args.section!r} sin match en el archivo?) — "
              f"dimensiones adr/acceptance en 0")
    if acc_found and total and not acc_traceable:
        print("  ! acceptance sin IDs trazables ('- [ ] AC-01 — ...') — la "
              "dimension acceptance cae al ratio de checkboxes (RELATO, no medido)")
    if dupe_ids:
        print(f"  ! IDs duplicados en acceptance (normalizados): {', '.join(dupe_ids)} "
              f"— cada ID cuenta UNA sola vez en la dimension acceptance")
    if legacy_weights_cfg and not acc_traceable:
        print("  ! config con readiness_weights explicitos de kit <=1.9.0 sin "
              "'acceptance' — dimension excluida (peso 0) hasta agregar AC-IDs "
              "o el peso explicito en config.defaults.readiness_weights")
    if narrated_only:
        print(f"  ! narrated-only: {', '.join(narrated_only)} — checkbox marcado "
              f"SIN testcase verde 'AC-n' en los reportes (measured beats "
              f"narrated: NO cierra)")
    if measured_unchecked:
        print(f"  · medido sin marcar: {', '.join(measured_unchecked)} — hay "
              f"testcase verde; marca el checkbox si el criterio esta completo")
    if acc_traceable and ac_untagged:
        print(f"  · {ac_untagged} criterio(s) sin AC-ID — no pueden cerrar "
              f"MEDIDO (cuentan como abiertos en la dimension acceptance)")
    if unmeasured_repos:
        print(f"  ! static gate NEVER ran in: {', '.join(unmeasured_repos)} — "
              f"dimension scored UNMEASURED (0.0), silence is not success")
    if stalled_repos:
        print(f"  ! stall: {', '.join(stalled_repos)} — findings gateados planos o "
              f"subiendo {STALL_WINDOW} ciclos: iterar mas no esta acercando la "
              f"solucion. Probable problema de diseño/SPEC — volver a ADR / "
              f"re-planear con el humano (advisory)")
    if stop_signal:
        print("  · stop-signal: todos los repos convergieron y no queda ningun "
              "fact bloqueante — lo que falta es deuda medible (coverage/"
              "acceptance), no findings: candidato a cortar e ir a PR (advisory)")
    print("--- dimensions (weight | raw | contribution) ---")
    for d in dims:
        print(f"  {d:13s} {weights[d]:3d} | {dims[d]:.2f} | "
              f"{out['dimensions'][d]['contribution']:5.1f}")
    acc_str = (f"medida {len(measured_closed)}/{total}" if acc_traceable
               else "sin trazar")
    print(f"--- acceptance: {done}/{total} tasks ({acc_str})   "
          f"coverage: {round(agg_cov_pct,1)}% (thr {threshold})   "
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
#        qa_ledger.py rebuild --mode baseline --config dev-loop.config.json
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
    if args.config and os.path.exists(args.config):
        cfg = _load(args.config).get("defaults", {}).get("simplicity", {})
        b.update({k: cfg[k] for k in b if k in cfg})
    for k in ("max_lines_added", "max_net_lines", "max_files_changed",
              "max_nesting_depth", "max_hunk_added", "max_new_abstractions",
              "indent_width"):
        v = getattr(args, k, None)
        if v is not None:
            b[k] = v
    if args.max_abstraction_density is not None:
        b["max_abstraction_density"] = args.max_abstraction_density

    m = _simplicity_metrics(_read_diff(args), b["indent_width"])
    score, dims = _simplicity_score(m, b)
    verdict = _simplicity_band(score)
    flags = _simplicity_flags(m, b)

    out = {"score": score, "verdict": verdict, "weights": SIMPLICITY_WEIGHTS,
           "dimensions": {k: round(v, 3) for k, v in dims.items()},
           "metrics": m, "budgets": b, "flags": flags}
    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
        sys.exit(0 if verdict != "OVERBUILT" else 1)

    print(f"SIMPLICITY: {score}/100 — {verdict}")
    print("--- métricas (valor / presupuesto) ---")
    rows = [
        ("lines_added", m["lines_added"], b["max_lines_added"]),
        ("net_lines", m["net_lines"], b["max_net_lines"]),
        ("files_changed", m["files_changed"], b["max_files_changed"]),
        ("max_nesting", m["max_nesting"], b["max_nesting_depth"]),
        ("new_abstractions", m["new_abstractions"], b["max_new_abstractions"]),
        ("abstraction/100", m["abstraction_density"], b["max_abstraction_density"]),
        ("max_hunk_added", m["max_hunk_added"], b["max_hunk_added"]),
    ]
    for name, val, bud in rows:
        print(f"  {name:17s} {str(val):>7s} / {bud}")
    print(f"  (new_functions: {m['new_functions']} — informativo, no gateado)")
    if m.get("test_files_changed"):
        print(f"  (tests FUERA del presupuesto: +{m['test_lines_added']} lineas "
              f"en {m['test_files_changed']} archivo(s) de test — escribir tests "
              f"nunca penaliza este gate)")
    if m.get("files_skipped"):
        print(f"  ({m['files_skipped']} archivo(s) no-código salteados: docs/config/resources)")
    if flags:
        print("--- flags (Reduce: qué recortar) ---")
        for fl in flags:
            print(f"  ! {fl}")
    else:
        print("  dentro de presupuesto — nada que recortar")
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
    root = ET.parse(xml_path).getroot()
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
    print("--- efectividad (NO es coverage: mide que los tests ASERTEN) ---")
    print(f"  mutantes {m['total']} · matados {m['killed']} · "
          f"sobreviven {m['survived']} · sin cobertura {m['no_coverage']}")
    if m.get("excluded"):
        print(f"  ({m['excluded']} excluidos NON_VIABLE/RUN_ERROR — fuera del score, como PIT)")
    if hotspots:
        print("--- hotspots (más mutantes vivos = tests débiles ahí) ---")
        for f, c in hotspots:
            print(f"  ! {f}: {c['survived']} sobreviven, {c['no_coverage']} sin cubrir")
    else:
        print("  sin sobrevivientes — los tests atrapan las mutaciones")
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


def cmd_gate_check(args):
    diff = _read_diff(args)
    removed_tests, disabled_tests, suppressions, thresholds = [], [], [], []
    secrets, secret_literals, scrub_edits = [], [], []
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
            + len(scrub_edits))
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
            "assertions_removed": assertions_removed,
            "test_count_drop": test_count_drop,
        }, indent=2, ensure_ascii=False))
        sys.exit(1 if blocker else 0)

    print(f"GATE-INTEGRITY: {verdict}")

    def _show(label, items):
        if items:
            uniq = sorted(set(items))
            tail = " ..." if len(uniq) > 5 else ""
            print(f"  ! {label}: {len(items)} en {', '.join(uniq[:5])}{tail}")

    _show("tests borrados (BLOCKER)", removed_tests)
    _show("tests deshabilitados (BLOCKER)", disabled_tests)
    if thresholds:
        print(f"  ! thresholds bajados/borrados (BLOCKER): {'; '.join(thresholds)}")
    if secrets:
        print(f"  ! secretos agregados (BLOCKER): {'; '.join(sorted(set(secrets)))}")
    _show("literales tipo password/token agregados (revisar)", secret_literals)
    _show("reglas de scrub del golden editadas (revisar: pueden enmascarar divergencia)", scrub_edits)
    _show("supresiones de lint agregadas (revisar)", suppressions)
    if assertions_removed:
        print(f"  ~ asserts removidos en tests: {assertions_removed} (revisar)")
    if test_count_drop:
        print(f"  ~ conteo de tests ejecutados cayó: {test_count_drop} (medido en snapshots — revisar)")
    if verdict == "CLEAN":
        print("  el cambio no debilita el aparato de medición")
    elif not blocker:
        print("  señales blandas: requieren justificación (--strict para gatear)")
    sys.exit(1 if blocker else 0)


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


def cmd_spec_check(args):
    acc_block, acc_adv = ([], [])
    if args.acceptance:
        acc_block, acc_adv = _acceptance_traceability(args.acceptance)
    if args.spec:
        text = ""
        for p in args.spec:
            try:
                with open(p, "r", encoding="utf-8", errors="replace") as fh:
                    text += fh.read() + "\n"
            except OSError as exc:
                print(f"[qa_ledger] cannot read spec {p}: {exc}", file=sys.stderr)
                sys.exit(2)
    elif args.acceptance and sys.stdin.isatty():
        text = ""  # modo solo-acceptance interactivo: nada pipeado, no bloquear leyendo stdin
    else:
        # sin --spec: leer stdin SIEMPRE que venga pipeado/redirigido (incluso
        # con --acceptance) — un `cat SPEC.md | ... --acceptance X` no debe
        # descartar en silencio el SPEC pipeado.
        text = sys.stdin.read()
    if not text.strip() and not args.acceptance:
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
        print(f"  ~ stack nombrado en criterios ({len(m['stack_hits'])}): {', '.join(terms[:6])} — el 'cómo' va al ADR, no al SPEC")
    if m["non_ears"] and m["n_criteria"]:
        print(f"  · advisory: {m['non_ears']}/{m['n_criteria']} criterios no siguen patrón EARS (When/If/While … shall)")
    print("  i consistencia: INFERENCIAL (checker no-correlacionado), no este lint · "
          "estructura = FACT (bloquea) · prosa = advisory (--strict para gatear)")
    if verdict == "OK":
        print("  estructura completa y criterios testables")
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
        print(f"[qa_ledger] {path} invalido ({exc}) — el scrub no se saltea en "
              f"silencio: arregla el archivo o borralo.", file=sys.stderr)
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


def cmd_golden_diff(args):
    root = args.dir or "."
    hits = set(glob.glob(os.path.join(root, "**", "*.received.*"), recursive=True))
    hits |= set(glob.glob(os.path.join(root, "**", "*.received"), recursive=True))
    received = [p for p in sorted(hits) if os.path.isfile(p)]   # skip dirs matched by glob
    rules = _load_scrub_rules(root)
    scrub_counts = {}
    diverged = []   # (received_path, reason)
    matched = 0
    matched_scrubbed = 0
    for rec in received:
        app = _golden_approved_path(rec)
        if app is None:
            continue
        if not os.path.exists(app):
            diverged.append((rec, "sin .approved — fixture nuevo, requiere aprobación humana"))
            continue
        try:
            with open(rec, "rb") as fr:
                rb = fr.read()
            with open(app, "rb") as fa:
                ab = fa.read()
        except OSError as exc:
            diverged.append((rec, f"no se pudo leer: {exc}"))
            continue
        if rb == ab:
            matched += 1
        # el conteo reportado es del lado RECEIVED (la captura fresca) — sumar
        # ambos lados duplicaria cada volatil enmascarado en el reporte.
        elif rules and (_scrub(rb, rules, scrub_counts)
                        == _scrub(ab, rules, {})):
            # matchea SOLO tras enmascarar volatiles declarados — cuenta como
            # pass pero se reporta APARTE: el masking jamas es invisible.
            matched_scrubbed += 1
        else:
            diverged.append((rec, "diff NO aprobado contra .approved"))

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
            print("GOLDEN-DIFF: NOT-RUN — sin fixtures .received, nada que comparar "
                  "(corré la captura primero; ausencia NO es verde)")
        sys.exit(2)
    verdict = "CLEAN" if passed else "DIVERGE"
    if args.json:
        print(json.dumps({
            "verdict": verdict, "matched": matched,
            "matched_scrubbed": matched_scrubbed,
            "scrub_rules": len(rules),
            "scrub_substitutions": scrub_counts,
            "diverged": [{"file": f, "reason": r} for f, r in diverged],
        }, indent=2, ensure_ascii=False))
        sys.exit(0 if passed else 1)
    scrub_str = f" · {matched_scrubbed} via scrub" if matched_scrubbed else ""
    print(f"GOLDEN-DIFF: {verdict}  ({matched} matchean{scrub_str} · {len(diverged)} divergen)")
    if rules:
        subs = sum(scrub_counts.values())
        print(f"  · scrub activo: {len(rules)} regla(s) de {GOLDEN_SCRUB_FILE}, "
              f"{subs} sustitucion(es) — el masking es visible, no magia")
    for f, r in diverged[:12]:
        print(f"  ! {f}: {r}")
    if len(diverged) > 12:
        print(f"  ... y {len(diverged) - 12} más")
    if passed:
        print("  el comportamiento matchea el golden aprobado byte a byte"
              + (" (volatiles declarados enmascarados)" if matched_scrubbed else ""))
    else:
        print("  el .approved es verdad de campo: si el diff es correcto, lo aprueba un HUMANO — el agente no lo toca")
    sys.exit(0 if passed else 1)


# --------------------------------------------------------------------------- #
# cli
# --------------------------------------------------------------------------- #
def build_parser():
    p = argparse.ArgumentParser(description="dev-loop QA ledger / measurement engine")
    sub = p.add_subparsers(dest="cmd", required=True)

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

    pre = sub.add_parser("resolve-escalation",
                         help="close open escalations for a repo (recorded event; "
                              "lifts the readiness cap)")
    add_ledger(pre)
    pre.add_argument("--repo", required=True)
    pre.add_argument("--note", default=None)
    pre.set_defaults(func=cmd_resolve_escalation)

    plg = sub.add_parser(
        "log-gate",
        help="persist a FACT-gate verdict (golden-diff/gate-check/pit-check/simplicity) "
             "so converged and readiness actually see it")
    add_ledger(plg)
    plg.add_argument("--repo", required=True)
    plg.add_argument("--iteration", type=int, required=True)
    plg.add_argument("--kind", required=True,
                     choices=["golden-diff", "gate-check", "pit-check", "simplicity"])
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
    pfb.add_argument("--iteration", type=int, default=0)
    pfb.add_argument("--note", default=None,
                     help="what was breached (required unless --resolve)")
    pfb.add_argument("--resolve", action="store_true",
                     help="clear the blocker (writes a clean record for the same kind)")
    pfb.set_defaults(func=cmd_flag_blocker)

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
    pr.set_defaults(func=cmd_readiness)

    pb = sub.add_parser("rebuild",
                        help="rebuild test: is the SPEC complete enough to "
                             "regenerate the system? (completeness, not correctness)")
    pb.add_argument("--mode", required=True, choices=["baseline", "compare"])
    pb.add_argument("--config", default="dev-loop.config.json",
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
    ps2.add_argument("--config", default="dev-loop.config.json",
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
