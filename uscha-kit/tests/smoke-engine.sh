#!/usr/bin/env bash
# smoke-engine.sh — suite de smoke del motor qa_ledger.py contra un ledger SINTÉTICO.
# Valida el cableado de los fact gates (v1.3.0): log-gate, flag-blocker,
# resolve-escalation, UNMEASURED, convergencia per-tool, gate-check, golden-diff,
# spec-check estructural, simplicity floor, oscillation — el adapter python
# (v1.4.0): coverage Cobertura, junit envuelto, LOC, ruff/mypy, UNMEASURED python —
# el adapter node (v1.5.0): lcov, jest-junit, LOC ts, eslint/tsc, UNMEASURED node —
# el adapter go (v1.6.0): cover profile, gotestsum, LOC _test.go, golangci —
# los adapters rust/dotnet (v1.7.0): Cobertura reusada, clippy JSONL, SARIF —
# el adapter cpp (v1.8.0): gcovr Cobertura, ctest junit plano, clang-tidy —
# y los adapters gradle/swift (v1.9.0): JaCoCo/lcov/junit/checkstyle reusados
# en paths nuevos (detekt, swiftlint) + fixes de los reviews 1.7.0/1.8.0 —
# y acceptance trazable (v1.10.0): AC-n cierra por testcase medido, spec-check
# --acceptance como FACT estructural —
# y tests fuera del presupuesto de simplicity (v1.11.0): escribir tests no
# penaliza el gate (Topic 51) + edges 1.10.0 (falsos positivos, flaky) —
# y secret-scan en gate-check (v1.12.0): secretos agregados bloquean como hecho —
# y ledger atomico (v1.13.0): checksum de integridad + carga blindada —
# y plateau/stop-signal (v1.14.0): stall y candidato-a-PR como advisories —
# y golden scrub (v1.15.0): volatiles declarados enmascaran con masking visible —
# y regression-capture (v1.16.0): cierre sin test = narrado; escape-analysis
# obligatoria al resolver blockers — y procedencia de umbrales (v1.17.0):
# requerimiento (config) vs default del kit, etiquetado en cada gate —
# y phase (v1.18.0): FSM derivada del ledger, el estado se computa —
# y spikes (v1.19.0): rama spike/* jamas pasa el gate de PR —
# y doctor (v1.22.0): diagnostico de la instalacion, ledger corrupto = error —
# y rubric layer (v1.23.0): criterio cualitativo versionado, agnostico (T43 a mano).
#
# Uso:   bash tests/smoke-engine.sh        (desde la raíz del kit)
# Exit:  0 = todos los checks verdes · 1 = algún check falló
#
# Nota INV-GOLDEN-01: el path CLEAN de golden-diff NO se auto-testea — crear un
# fixture aprobado es un acto HUMANO incluso en tests. Se cubren NOT-RUN y DIVERGE.

set -u
# stdin SIEMPRE cerrado: spec-check (y cualquier subcomando futuro) lee stdin
# cuando viene redirigido — con un pipe abierto sin EOF la suite se cuelga
# infinito (paso en la vida real: exit 124 por timeout con commit encadenado).
exec < /dev/null
KIT="$(cd "$(dirname "$0")/.." && pwd)"
ROOT="$(cd "$KIT/.." && pwd)"
QL="$KIT/.claude/skills/uscha-devloop/qa_ledger.py"
# probe FUNCIONAL: en Windows 'python3' puede ser un stub de Store que está en
# PATH pero no ejecuta — hay que probar --version, no solo command -v.
PY="${PYTHON:-}"
if [ -z "$PY" ]; then
  for cand in python3 python py; do
    if "$cand" --version >/dev/null 2>&1; then PY="$cand"; break; fi
  done
fi
[ -n "$PY" ] || { echo "FAIL: no hay Python funcional en PATH"; exit 1; }
if [ "${USCHA_INSTALLER_P0_D_ONLY:-0}" = "1" ]; then
  "$PY" - "$KIT/install-uscha.py" <<'PY'
import json
import os
import pathlib
import subprocess
import sys
import tempfile

installer = pathlib.Path(sys.argv[1])


def run(*args):
    return subprocess.run(
        [sys.executable, str(installer), *map(str, args)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")


with tempfile.TemporaryDirectory(prefix="uscha-installer-p0-d-") as tmp:
    root = pathlib.Path(tmp)
    repo = root / "repo-symlink"
    outside = root / "outside-sentinel.json"
    repo.mkdir()
    outside.write_bytes(b"outside-sentinel\n")
    (repo / "uscha.config.json").symlink_to(outside)
    before = outside.read_bytes()

    result = run("init", "--repo", repo, "--force", "--json")

    assert result.returncode != 0, (result.returncode, result.stdout, result.stderr)
    assert "traceback" not in result.stderr.lower(), result.stderr
    assert outside.read_bytes() == before, "managed-target symlink modified outside sentinel"
    assert (repo / "uscha.config.json").is_symlink(), "managed-target symlink was replaced"
    for name in ("CLAUDE.md", "CONSTITUTION.md", ".gitattributes"):
        assert not (repo / name).exists(), (name, "init wrote after symlink hazard")
    broken_repo = root / "repo-broken-symlink"
    broken_repo.mkdir()
    missing_outside = root / "missing-outside-sentinel.json"
    broken_target = broken_repo / "uscha.config.json"
    broken_target.symlink_to(missing_outside)
    result = run("init", "--repo", broken_repo, "--force", "--json")
    assert result.returncode != 0, (result.returncode, result.stdout, result.stderr)
    assert broken_target.is_symlink(), "broken managed-target symlink was replaced"
    assert not missing_outside.exists(), "broken symlink target was created outside repo"
    for name in ("CLAUDE.md", "CONSTITUTION.md", ".gitattributes"):
        assert not (broken_repo / name).exists(), (name, "init wrote after broken symlink hazard")
    print("P0-D RED/GREEN 1: init rejects existing and broken managed-target symlinks without writes")

    repo = root / "repo-late-conflict"
    repo.mkdir()
    conflict = repo / ".gitattributes"
    conflict.write_bytes(b"late-conflict-sentinel\n")
    before = conflict.read_bytes()

    result = run("init", "--repo", repo, "--json")

    assert result.returncode != 0, (result.returncode, result.stdout, result.stderr)
    assert conflict.read_bytes() == before, "late conflict was modified"
    for name in ("uscha.config.json", "CLAUDE.md", "CONSTITUTION.md"):
        assert not (repo / name).exists(), (name, "written before late conflict discovery")
    dry_repo = root / "repo-init-dry-run"
    result = run("init", "--repo", dry_repo, "--dry-run", "--json")
    assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)
    assert not dry_repo.exists(), "init dry-run wrote the repository"
    print("P0-D RED/GREEN 2: late init conflict prevents all earlier writes; dry-run stays write-free")

    fault = root / "codex-marker-fault"
    fault.mkdir()
    (fault / "sitecustomize.py").write_text(r"""
import os

_replace = os.replace
_failed = False


def fail_at_codex_marker(source, target):
    global _failed
    normalized = os.path.normcase(os.path.normpath(os.fspath(target)))
    suffix = os.path.normcase(os.path.normpath(os.path.join("plugins", "uscha", "uscha-install.json")))
    if not _failed and normalized.endswith(suffix):
        _failed = True
        with open(os.environ["USCHA_FAULT_WITNESS"], "w", encoding="utf-8", newline="\n") as handle:
            handle.write("late\n")
        raise OSError("deterministic late Codex marker failure")
    return _replace(source, target)


os.replace = fail_at_codex_marker
""", encoding="utf-8", newline="\n")

    marketplace_bytes = (b'{\n  "name": "personal", "interface": {"displayName": "Mine"},\n'
                         b'  "plugins": [{"name":"other","source":{"source":"local","path":"./plugins/other"},'
                         b'"policy":{"installation":"AVAILABLE","authentication":"ON_INSTALL"},"category":"Productivity"}]\n}\n')

    for prior_marketplace in (marketplace_bytes, None):
        label = "existing" if prior_marketplace is not None else "absent"
        home = root / ("home-codex-rollback-" + label)
        plugin = home / "plugins" / "uscha"
        market = home / ".agents" / "plugins" / "marketplace.json"
        plugin.mkdir(parents=True)
        (plugin / "sentinel.bin").write_bytes(b"prior-plugin-tree\x00\xff")
        if prior_marketplace is not None:
            market.parent.mkdir(parents=True)
            market.write_bytes(prior_marketplace)
        before_plugin = sorted((p.relative_to(plugin).as_posix(), p.read_bytes())
                               for p in plugin.rglob("*") if p.is_file())
        witness = fault / ("witness-" + label + ".txt")
        env = os.environ.copy()
        env["PYTHONPATH"] = str(fault)
        env["USCHA_FAULT_WITNESS"] = str(witness)

        result = subprocess.run(
            [sys.executable, str(installer), "install", "--target", "codex",
             "--home", str(home), "--json"], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding="utf-8", env=env)

        assert result.returncode != 0, (label, result.returncode, result.stdout, result.stderr)
        assert witness.read_text(encoding="utf-8") == "late\n", (label, "fault not reached")
        after_plugin = sorted((p.relative_to(plugin).as_posix(), p.read_bytes())
                              for p in plugin.rglob("*") if p.is_file())
        assert after_plugin == before_plugin, (label, "prior plugin tree not restored")
        if prior_marketplace is None:
            assert not market.exists(), "new marketplace remained after rollback"
            assert not (home / ".agents").exists(), "new marketplace directories remained after rollback"
        else:
            assert market.read_bytes() == prior_marketplace, "marketplace bytes not restored"
        assert not list((home / "plugins").glob(".uscha.*-*")), (label, "Codex transaction residue")
    print("P0-D RED/GREEN 3: late Codex marker failure restores plugin and marketplace states")

    home = root / "home-claude-narrow-matcher"
    result = run("install", "--target", "claude", "--home", home, "--json")
    assert result.returncode == 0, (result.stdout, result.stderr)
    settings_path = home / ".claude" / "settings.json"
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    canonical = settings["hooks"]["PreToolUse"][-1]
    canonical["matcher"] = "Write"
    settings["theme"] = "sentinel"
    settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8", newline="\n")

    result = run("doctor", "--target", "claude", "--home", home, "--json")
    assert result.returncode != 0, "doctor accepted exact command under a narrow matcher"

    result = run("install", "--target", "claude", "--home", home, "--json")
    assert result.returncode == 0, (result.stdout, result.stderr)
    result = run("install", "--target", "claude", "--home", home, "--json")
    assert result.returncode == 0, (result.stdout, result.stderr)
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    groups = settings["hooks"]["PreToolUse"]
    commands = [item.get("command") for group in groups if group.get("matcher") == "*"
                for item in group.get("hooks", []) if item.get("type") == "command"
                and "block-approved-writes.py" in item.get("command", "")]
    assert len(commands) == 1, (groups, "canonical matcher registration count")
    assert settings["theme"] == "sentinel", "unrelated Claude settings were not preserved"
    assert any(group.get("matcher") == "Write" for group in groups), "narrow registration was removed"
    result = run("doctor", "--target", "claude", "--home", home, "--json")
    assert result.returncode == 0, (result.stdout, result.stderr)
    print("P0-D RED/GREEN 4: narrow hook matcher requires one canonical registration")

    malformed_settings = [
        ("root-list", []),
        ("hooks-scalar", {"hooks": 7}),
        ("pretool-scalar", {"hooks": {"PreToolUse": 7}}),
        ("group-list", {"hooks": {"PreToolUse": [[]]}}),
        ("group-hooks-scalar", {"hooks": {"PreToolUse": [{"matcher": "*", "hooks": 7}]}}),
        ("item-list", {"hooks": {"PreToolUse": [{"matcher": "*", "hooks": [[]]}]}}),
    ]
    for label, payload in malformed_settings:
        home = root / ("home-malformed-" + label)
        claude = home / ".claude"
        settings_path = claude / "settings.json"
        claude.mkdir(parents=True)
        original = (json.dumps(payload, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
        settings_path.write_bytes(original)
        before_paths = sorted(p.relative_to(home).as_posix() for p in home.rglob("*"))

        result = run("install", "--target", "claude", "--home", home, "--json")

        assert result.returncode != 0, (label, result.stdout, result.stderr)
        assert "traceback" not in result.stderr.lower(), (label, result.stderr)
        assert settings_path.read_bytes() == original, (label, "settings bytes changed")
        after_paths = sorted(p.relative_to(home).as_posix() for p in home.rglob("*"))
        assert after_paths == before_paths, (label, before_paths, after_paths)
    print("P0-D RED/GREEN 5: malformed settings shapes fail cleanly without writes")
PY
  exit $?
fi
SB="$(mktemp -d 2>/dev/null || echo "${TMP:-/tmp}/smoke-$$")"; mkdir -p "$SB/repo-a" "$SB/repo-b" "$SB/repo-c" "$SB/repo-d" "$SB/repo-e" "$SB/repo-f" "$SB/repo-g" "$SB/repo-h" "$SB/repo-i" "$SB/repo-j"
cd "$SB"

PASS=0; FAIL=0
chk() { # $1 = descripción, $2 = exit esperado, $3.. = comando
  local desc="$1" want="$2"; shift 2
  "$@" >/dev/null 2>&1; local got=$?
  if [ "$got" -eq "$want" ]; then PASS=$((PASS+1)); echo "  ok   $desc"
  else FAIL=$((FAIL+1)); echo "  FAIL $desc (exit $got, esperado $want)"; fi
}
# Coverage of the engine is OPT-IN (USCHA_COVERAGE=1). The engine is exercised through
# ~370 subprocess calls, so measuring it means wrapping the ONE choke point they all pass
# through -- not instrumenting the suite. Off by default: the normal smoke stays fast and
# dependency-free (coverage.py is not required to run the suite).
if [ "${USCHA_COVERAGE:-0}" = "1" ]; then
  COV_DATA="$ROOT/.coverage-data/.coverage"
  mkdir -p "$(dirname "$COV_DATA")"
  export COVERAGE_FILE="$COV_DATA"
  # ONE absolute --source path, deliberately. Two reasons, both learned the hard way:
  # (1) git-bash/MSYS rewrites only the FIRST POSIX path embedded in an argument, so a
  #     comma-joined list arrives at Windows Python as C:/... , /c/... , /c/... -- the tail
  #     entries are unresolvable and coverage warns once per call;
  # (2) coverage.py does not report never-imported files under a --source directory anyway,
  #     so extra roots buy nothing.
  # What gets measured is what the suite EXECUTES through this seam: the engine. The twin
  # tree (uscha-kit/skills) is absent from the report because the suite never runs it --
  # $QL points at .claude/skills -- not because a flag excluded it.
  COV_SRC="$KIT/.claude/skills/uscha-devloop"
  run() { PYTHONIOENCODING=utf-8 "$PY" -m coverage run --parallel-mode \
            --source="$COV_SRC" "$QL" "$@"; }
else
  run() { PYTHONIOENCODING=utf-8 "$PY" "$QL" "$@"; }
fi

cat > uscha.config.json <<'EOF'
{ "version": "1.3.0",
  "defaults": { "coverage_threshold": 60, "tools_per_cycle": 3,
    "severity_gate": ["BLOCKER","CRITICAL","HIGH"],
    "qa_tools_order": ["code-review","judgment-day","improve"],
    "acceptance_file": "ACCEPTANCE.md" },
  "repos": [ {"name":"repo-a","path":"repo-a","type":"maven"},
             {"name":"repo-b","path":"repo-b","type":"flutter"},
             {"name":"repo-c","path":"repo-c","type":"python"},
             {"name":"repo-d","path":"repo-d","type":"node"},
             {"name":"repo-e","path":"repo-e","type":"go"},
             {"name":"repo-f","path":"repo-f","type":"rust"},
             {"name":"repo-g","path":"repo-g","type":"dotnet"},
             {"name":"repo-h","path":"repo-h","type":"cpp"},
             {"name":"repo-i","path":"repo-i","type":"gradle"},
             {"name":"repo-j","path":"repo-j","type":"swift"} ],
  "integration": {"enabled": false} }
EOF
printf -- "# ACCEPTANCE\n\n- [x] criterio uno\n- [ ] criterio dos\n" > ACCEPTANCE.md
run init --config uscha.config.json >/dev/null || { echo "FAIL init"; exit 1; }

echo "== T1 readiness virgen: static UNMEASURED, no 1.0 por silencio =="
run readiness 2>/dev/null | grep -q "UNMEASURED" && { PASS=$((PASS+1)); echo "  ok   warning UNMEASURED presente"; } || { FAIL=$((FAIL+1)); echo "  FAIL sin warning UNMEASURED"; }

echo "== T2 converged exige TODAS las tools de qa_tools_order =="
run log-step --repo repo-a --tool code-review --iteration 1 --tests-passed true >/dev/null
run log-step --repo repo-a --tool judgment-day --iteration 1 --tests-passed true >/dev/null
chk "falta 'improve' -> NOT converged" 1 run converged --repo repo-a

echo "== T3 log-gate fail bloquea convergencia; pass la limpia =="
run log-step --repo repo-a --tool improve --iteration 1 --tests-passed true >/dev/null
chk "ciclo completo limpio -> CONVERGED" 0 run converged --repo repo-a
run log-gate --repo repo-a --iteration 1 --kind golden-diff --verdict fail --note smoke >/dev/null
chk "fact gate rojo -> NOT converged" 1 run converged --repo repo-a
run log-gate --repo repo-a --iteration 2 --kind golden-diff --verdict pass >/dev/null
chk "fact gate pass -> CONVERGED de nuevo" 0 run converged --repo repo-a

echo "== T4 flag-blocker (constitution) bloquea hasta --resolve =="
run flag-blocker --repo repo-a --kind constitution --note "INV-X breached" >/dev/null
chk "blocker abierto -> NOT converged" 1 run converged --repo repo-a
chk "resolver SIN escape-analysis -> rechazado (Find Bugs Once)" 1 \
  run flag-blocker --repo repo-a --kind constitution --resolve
run flag-blocker --repo repo-a --kind constitution --resolve \
  --escape-analysis "hook nuevo + test que cubre INV-X" >/dev/null
chk "blocker resuelto (con escape analysis) -> CONVERGED" 0 run converged --repo repo-a

echo "== T5 escalate/resolve-escalation registrados =="
# el cap_reason solo se muestra cuando el cap MUERDE (score > techo); con score bajo
# lo observable es el REGISTRO: la escalación existe sin resolved_at y luego con él.
run escalate --repo repo-a --reason "smoke" >/dev/null
"$PY" -c "import json,sys; e=json.load(open('QA-LEDGER.json'))['escalations']; sys.exit(0 if any(not x.get('resolved_at') for x in e) else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   escalación abierta registrada"; } || { FAIL=$((FAIL+1)); echo "  FAIL escalación no registrada"; }
run resolve-escalation --repo repo-a >/dev/null
"$PY" -c "import json,sys; e=json.load(open('QA-LEDGER.json'))['escalations']; sys.exit(0 if all(x.get('resolved_at') for x in e) else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   resolved_at registrado al resolver"; } || { FAIL=$((FAIL+1)); echo "  FAIL resolved_at ausente"; }

echo "== T6 gate-check: borrado de archivo de test entero =="
printf -- "diff --git a/src/test/java/FooTest.java b/src/test/java/FooTest.java\n--- a/src/test/java/FooTest.java\n+++ /dev/null\n@@ -1,3 +0,0 @@\n-import org.junit.jupiter.api.Test;\n-@Test\n-void testX() { assertEquals(1,1); }\n" > del.diff
chk "delete de test file -> BLOCKER" 1 run gate-check --diff del.diff

echo "== T7 gate-check: threshold bajado cross-hunk + borrado sin re-add =="
printf -- "diff --git a/pom.xml b/pom.xml\n--- a/pom.xml\n+++ b/pom.xml\n@@ -10,1 +10,0 @@\n-  <coverage-minimum>0.80</coverage-minimum>\n@@ -90,0 +90,1 @@\n+  <coverage-minimum>0.50</coverage-minimum>\n" > thr.diff
chk "lowered cross-hunk -> BLOCKER" 1 run gate-check --diff thr.diff
printf -- "diff --git a/pom.xml b/pom.xml\n--- a/pom.xml\n+++ b/pom.xml\n@@ -10,1 +10,0 @@\n-  <coverage-minimum>0.80</coverage-minimum>\n@@ -55,0 +55,1 @@\n+  <coverage-minimum>0.80</coverage-minimum>\n" > move.diff
chk "mover threshold igual -> CLEAN" 0 run gate-check --diff move.diff

echo "== T7b gate-check: dependencia nueva = senal BLANDA (kit 1.30.0) =="
# la CONSTITUTION dice '0 deps nuevas sin aprobacion'; gate-check la hace visible.
printf -- 'diff --git a/package.json b/package.json\n--- a/package.json\n+++ b/package.json\n@@ -10,3 +10,4 @@\n   "dependencies": {\n+    "sketchy-lib": "^2.1.0",\n     "react": "^18.0.0"\n' > dep.diff
run gate-check --diff dep.diff --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
ok = (d['verdict'] == 'REVIEW' and len(d['new_dependencies']) == 1
      and 'sketchy-lib' in d['new_dependencies'][0])
sys.exit(0 if ok else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   dep nueva -> REVIEW + listada en new_dependencies"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL dep nueva no detectada"; }
chk "dep nueva SIN --strict -> exit 0 (advisory)" 0 run gate-check --diff dep.diff
chk "dep nueva CON --strict -> exit 1 (gatea la senal blanda)" 1 run gate-check --diff dep.diff --strict
# un diff de codigo normal NO debe flaguear dep (sin falsos positivos)
printf -- 'diff --git a/src/mod.py b/src/mod.py\n--- a/src/mod.py\n+++ b/src/mod.py\n@@ -1,2 +1,3 @@\n def f(x):\n+    return x + 1\n' > nodep.diff
run gate-check --diff nodep.diff --json 2>/dev/null | "$PY" -c "
import json, sys
sys.exit(0 if json.load(sys.stdin)['new_dependencies'] == [] else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   diff de codigo normal no flaguea dep (sin falso positivo)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL falso positivo de dep en codigo normal"; }

echo "== T8 golden-diff: NOT-RUN y DIVERGE =="
mkdir -p g && ( cd g && chk "cero fixtures -> NOT-RUN exit 2" 2 run golden-diff )
( cd g && printf "x" > f.received.txt && chk "fixture sin aprobar -> DIVERGE exit 1" 1 run golden-diff )

echo "== T9 spec-check: estructural bloquea, completo OK =="
printf -- "# SPEC\n\n## Acceptance\n\n- [ ] when a then shall b exactly 80.00\n" > s1.md
chk "sin out-of-scope -> exit 1" 1 run spec-check --spec s1.md
printf -- "# SPEC\n\n## Out of scope\n\n- x\n\n## Acceptance\n\n- [ ] when a then shall b exactly 80.00\n" > s2.md
chk "spec completa -> exit 0" 0 run spec-check --spec s2.md

echo "== T10 simplicity: floor de dims pesadas (1.9x -> OVERBUILT) =="
{ printf -- "diff --git a/src/A.java b/src/A.java\n--- a/src/A.java\n+++ b/src/A.java\n@@ -1,0 +1,190 @@\n"; for i in $(seq 1 190); do printf -- "+int x%d = %d;\n" "$i" "$i"; done; } > big.diff
chk "diff 1.9x budget -> OVERBUILT exit 1" 1 run simplicity-check --diff big.diff --max-lines-added 100 --max-net-lines 999 --max-files-changed 20 --max-hunk-added 999

echo "== T11 oscillation Jaccard (a,b -> c -> a,b) =="
run log-step --repo repo-b --tool code-review --iteration 1 --fingerprint "a,b" >/dev/null
run log-step --repo repo-b --tool code-review --iteration 2 --fingerprint "c" >/dev/null
run log-step --repo repo-b --tool code-review --iteration 3 --fingerprint "a,b" >/dev/null
chk "set repetido -> OSCILLATING exit 1" 1 run oscillation --repo repo-b --tool code-review

echo "== T12 converged: snapshot rojo MEDIDO veta verde narrado =="
mkdir -p repo-a/target/surefire-reports
printf '<testsuite name="F" tests="6" failures="2" errors="0" skipped="0"/>\n' > repo-a/target/surefire-reports/TEST-F.xml
run snapshot --repo repo-a >/dev/null
chk "snapshot rojo -> NOT converged" 1 run converged --repo repo-a

echo "== T13 adapter python: coverage Cobertura + junit ENVUELTO + LOC =="
mkdir -p repo-c/src/pkg repo-c/tests repo-c/reports
printf 'def f():\n    return 1\nX = 2\n' > repo-c/src/pkg/mod.py
printf 'from src.pkg import mod\ndef test_f(): assert mod.f() == 1\n' > repo-c/tests/test_mod.py
cat > repo-c/coverage.xml <<'EOF'
<?xml version="1.0"?>
<coverage lines-valid="10" lines-covered="8" line-rate="0.8" version="7.4"></coverage>
EOF
cat > repo-c/reports/junit.xml <<'EOF'
<?xml version="1.0"?>
<testsuites><testsuite name="pytest" tests="5" failures="0" errors="0" skipped="1"/></testsuites>
EOF
SNAP=$(run snapshot --repo repo-c 2>&1)
echo "$SNAP" | grep -q "coverage=80.0%" && { PASS=$((PASS+1)); echo "  ok   coverage Cobertura 8/10 -> 80.0%"; } || { FAIL=$((FAIL+1)); echo "  FAIL coverage python ($SNAP)"; }
echo "$SNAP" | grep -q "tests=5" && { PASS=$((PASS+1)); echo "  ok   junit ENVUELTO (testsuites>testsuite) -> 5 tests"; } || { FAIL=$((FAIL+1)); echo "  FAIL test count python ($SNAP)"; }
echo "$SNAP" | grep -q "prod_loc=3, test_loc=2" && { PASS=$((PASS+1)); echo "  ok   LOC prod=3 / test=2 bien clasificado"; } || { FAIL=$((FAIL+1)); echo "  FAIL LOC python ($SNAP)"; }

echo "== T14 python UNMEASURED pre-ingest / medido post-ingest =="
run readiness 2>/dev/null | grep "NEVER ran" | grep -q "repo-c" \
  && { PASS=$((PASS+1)); echo "  ok   repo-c UNMEASURED antes del ingest"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL repo-c no aparece como UNMEASURED"; }
cat > repo-c/reports/ruff.json <<'EOF'
[{"code":"S101","filename":"src/pkg/mod.py","location":{"row":3}},
 {"code":"E501","filename":"src/pkg/mod.py","location":{"row":1}},
 {"code":null,"filename":"src/pkg/mod.py","location":{"row":9}}]
EOF
printf 'src/pkg/mod.py:2: error: Incompatible return value type (got "int", expected "str")  [return-value]\n' > repo-c/reports/mypy.txt
ING=$(run ingest-gate --repo repo-c --iteration 1 2>&1)
echo "$ING" | grep -q "repo-c/ruff: reported=3 gated=2" && { PASS=$((PASS+1)); echo "  ok   ruff: 3 findings, 2 gateados (S101 + code:null syntax = HIGH; E501 = LOW)"; } || { FAIL=$((FAIL+1)); echo "  FAIL ruff ($ING)"; }
echo "$ING" | grep -q "repo-c/mypy: reported=1 gated=1" && { PASS=$((PASS+1)); echo "  ok   mypy: error -> HIGH gateado"; } || { FAIL=$((FAIL+1)); echo "  FAIL mypy ($ING)"; }
run readiness 2>/dev/null | grep "NEVER ran" | grep -q "repo-c" \
  && { FAIL=$((FAIL+1)); echo "  FAIL repo-c sigue UNMEASURED tras ingest"; } \
  || { PASS=$((PASS+1)); echo "  ok   repo-c ya no es UNMEASURED tras ingest"; }

echo "== T15 adapter node: lcov + junit envuelto + LOC ts =="
mkdir -p repo-d/src repo-d/reports repo-d/coverage
printf 'export function f(): number {\n  return 1;\n}\nexport const X = 2;\n' > repo-d/src/app.ts
printf 'import { f } from "./app";\ntest("f", () => expect(f()).toBe(1));\n' > repo-d/src/app.test.ts
printf 'SF:src/app.ts\nLF:10\nLH:9\nend_of_record\n' > repo-d/coverage/lcov.info
cat > repo-d/reports/junit.xml <<'EOF'
<?xml version="1.0"?>
<testsuites><testsuite name="jest" tests="7" failures="0" errors="0" skipped="0"/></testsuites>
EOF
SNAPD=$(run snapshot --repo repo-d 2>&1)
echo "$SNAPD" | grep -q "coverage=90.0%" && { PASS=$((PASS+1)); echo "  ok   coverage lcov 9/10 -> 90.0%"; } || { FAIL=$((FAIL+1)); echo "  FAIL coverage node ($SNAPD)"; }
echo "$SNAPD" | grep -q "tests=7" && { PASS=$((PASS+1)); echo "  ok   junit envuelto (jest-junit) -> 7 tests"; } || { FAIL=$((FAIL+1)); echo "  FAIL test count node ($SNAPD)"; }
echo "$SNAPD" | grep -q "prod_loc=4, test_loc=2" && { PASS=$((PASS+1)); echo "  ok   LOC prod=4 (.ts) / test=2 (.test.ts) bien clasificado"; } || { FAIL=$((FAIL+1)); echo "  FAIL LOC node ($SNAPD)"; }

echo "== T16 node UNMEASURED pre-ingest / eslint+tsc post-ingest =="
run readiness 2>/dev/null | grep "NEVER ran" | grep -q "repo-d" \
  && { PASS=$((PASS+1)); echo "  ok   repo-d UNMEASURED antes del ingest"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL repo-d no aparece como UNMEASURED"; }
cat > repo-d/reports/eslint.json <<'EOF'
[{"filePath":"src/app.ts","messages":[
  {"ruleId":"security/detect-eval-with-expression","severity":1,"line":2},
  {"ruleId":"prefer-const","severity":1,"line":4},
  {"ruleId":null,"severity":1,"line":5},
  {"ruleId":null,"severity":2,"line":9,"fatal":true}]}]
EOF
printf 'src/app.ts(2,3): error TS2322: Type mismatch.\nerror TS18003: No inputs were found in config file.\n' > repo-d/reports/tsc.txt
INGD=$(run ingest-gate --repo repo-d --iteration 1 2>&1)
echo "$INGD" | grep -q "repo-d/eslint: reported=4 gated=2" && { PASS=$((PASS+1)); echo "  ok   eslint: security floor + fatal = HIGH; null NO-fatal (ESLint 9) = MEDIUM, no bloquea"; } || { FAIL=$((FAIL+1)); echo "  FAIL eslint ($INGD)"; }
echo "$INGD" | grep -q "repo-d/tsc: reported=2 gated=2" && { PASS=$((PASS+1)); echo "  ok   tsc: error con archivo + error GLOBAL sin archivo (tsconfig roto) = HIGH"; } || { FAIL=$((FAIL+1)); echo "  FAIL tsc ($INGD)"; }
run readiness 2>/dev/null | grep "NEVER ran" | grep -q "repo-d" \
  && { FAIL=$((FAIL+1)); echo "  FAIL repo-d sigue UNMEASURED tras ingest"; } \
  || { PASS=$((PASS+1)); echo "  ok   repo-d ya no es UNMEASURED tras ingest"; }

echo "== T17 adapter go: cover profile nativo + gotestsum junit + LOC _test.go =="
mkdir -p repo-e/pkg repo-e/reports
printf 'package pkg\nfunc F() int {\nreturn 1\n}\n' > repo-e/pkg/mod.go
printf 'package pkg\nfunc TestF(t *T) {}\n' > repo-e/pkg/mod_test.go
cat > repo-e/coverage.out <<'EOF'
mode: set
example.com/m/pkg/mod.go:2.15,4.2 3 1
example.com/m/pkg/mod.go:6.2,8.3 2 0
EOF
cat > repo-e/reports/junit.xml <<'EOF'
<?xml version="1.0"?>
<testsuites><testsuite name="gotestsum" tests="4" failures="0" errors="0" skipped="0"/></testsuites>
EOF
SNAPE=$(run snapshot --repo repo-e 2>&1)
echo "$SNAPE" | grep -q "coverage=60.0%" && { PASS=$((PASS+1)); echo "  ok   cover profile 3/5 stmts -> 60.0%"; } || { FAIL=$((FAIL+1)); echo "  FAIL coverage go ($SNAPE)"; }
echo "$SNAPE" | grep -q "tests=4" && { PASS=$((PASS+1)); echo "  ok   gotestsum junit envuelto -> 4 tests"; } || { FAIL=$((FAIL+1)); echo "  FAIL test count go ($SNAPE)"; }
echo "$SNAPE" | grep -q "prod_loc=4, test_loc=2" && { PASS=$((PASS+1)); echo "  ok   LOC prod=4 (mod.go) / test=2 (_test.go junto al codigo)"; } || { FAIL=$((FAIL+1)); echo "  FAIL LOC go ($SNAPE)"; }

echo "== T18 go UNMEASURED pre-ingest / golangci (checkstyle reusado) post-ingest =="
run readiness 2>/dev/null | grep "NEVER ran" | grep -q "repo-e" \
  && { PASS=$((PASS+1)); echo "  ok   repo-e UNMEASURED antes del ingest"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL repo-e no aparece como UNMEASURED"; }
cat > repo-e/reports/golangci.xml <<'EOF'
<?xml version="1.0"?>
<checkstyle version="5.0">
  <file name="pkg/mod.go">
    <error line="3" severity="error" message="G104: unhandled error" source="gosec"/>
    <error line="7" severity="warning" message="var x is unused" source="unused"/>
  </file>
</checkstyle>
EOF
INGE=$(run ingest-gate --repo repo-e --iteration 1 2>&1)
echo "$INGE" | grep -q "repo-e/golangci: reported=2 gated=1" && { PASS=$((PASS+1)); echo "  ok   golangci via parse_checkstyle: error=HIGH gateado, warning=MEDIUM"; } || { FAIL=$((FAIL+1)); echo "  FAIL golangci ($INGE)"; }
run readiness 2>/dev/null | grep "NEVER ran" | grep -q "repo-e" \
  && { FAIL=$((FAIL+1)); echo "  FAIL repo-e sigue UNMEASURED tras ingest"; } \
  || { PASS=$((PASS+1)); echo "  ok   repo-e ya no es UNMEASURED tras ingest"; }

echo "== T19 adapter rust: Cobertura (cargo llvm-cov) + nextest junit + LOC tests/ =="
mkdir -p repo-f/src repo-f/tests repo-f/reports
printf 'pub fn f() -> i32 {\n    1\n}\n' > repo-f/src/lib.rs
printf 'use core_lib::f;\n#[test] fn it_works() { assert_eq!(f(), 1); }\n' > repo-f/tests/it_test.rs
cat > repo-f/reports/coverage.xml <<'EOF'
<?xml version="1.0"?>
<coverage lines-valid="10" lines-covered="7" line-rate="0.7"></coverage>
EOF
cat > repo-f/reports/junit.xml <<'EOF'
<?xml version="1.0"?>
<testsuites><testsuite name="nextest" tests="3" failures="0" errors="0" skipped="0"/></testsuites>
EOF
SNAPF=$(run snapshot --repo repo-f 2>&1)
echo "$SNAPF" | grep -q "coverage=70.0%" && { PASS=$((PASS+1)); echo "  ok   Cobertura reusada (cargo llvm-cov) 7/10 -> 70.0%"; } || { FAIL=$((FAIL+1)); echo "  FAIL coverage rust ($SNAPF)"; }
echo "$SNAPF" | grep -q "tests=3" && { PASS=$((PASS+1)); echo "  ok   nextest junit -> 3 tests"; } || { FAIL=$((FAIL+1)); echo "  FAIL test count rust ($SNAPF)"; }
echo "$SNAPF" | grep -q "prod_loc=3, test_loc=2" && { PASS=$((PASS+1)); echo "  ok   LOC prod=3 (src/) / test=2 (tests/)"; } || { FAIL=$((FAIL+1)); echo "  FAIL LOC rust ($SNAPF)"; }

echo "== T20 rust: clippy JSONL (error/warning/compile-error/summary/dup) =="
# el '1 warning emitted' de rustc es un diagnostico REAL (level warning, code
# null, spans []) — sin el skip por span, cada corrida con warnings crece un
# HIGH fantasma y el gate no converge jamas. El duplicado (lib + test target)
# debe dedupearse por finding ID.
cat > repo-f/reports/clippy.json <<'EOF'
{"reason":"compiler-message","message":{"message":"unwrap used","level":"error","code":{"code":"clippy::unwrap_used"},"spans":[{"file_name":"src/lib.rs","line_start":2,"is_primary":true}]}}
{"reason":"compiler-message","message":{"message":"needless return","level":"warning","code":{"code":"clippy::needless_return"},"spans":[{"file_name":"src/lib.rs","line_start":3,"is_primary":true}]}}
{"reason":"compiler-message","message":{"message":"needless return","level":"warning","code":{"code":"clippy::needless_return"},"spans":[{"file_name":"src/lib.rs","line_start":3,"is_primary":true}]}}
{"reason":"compiler-message","message":{"message":"compile error","level":"error","code":null,"spans":[{"file_name":"src/lib.rs","line_start":1,"is_primary":true}]}}
{"reason":"compiler-message","message":{"message":"1 warning emitted","level":"warning","code":null,"spans":[]}}
{"reason":"compiler-message","message":{"message":"aborting due to 1 previous error","level":"error","code":null,"spans":[]}}
{"reason":"build-finished","success":false}
EOF
INGF=$(run ingest-gate --repo repo-f --iteration 1 2>&1)
echo "$INGF" | grep -q "repo-f/clippy: reported=3 gated=2" && { PASS=$((PASS+1)); echo "  ok   clippy: 3 reales (summaries sin span NO cuentan, dup dedupeado)"; } || { FAIL=$((FAIL+1)); echo "  FAIL clippy ($INGF)"; }

echo "== T21 adapter dotnet: Cobertura (coverlet) + junit logger + LOC .Tests =="
mkdir -p repo-g/src repo-g/Svc.Tests repo-g/reports
printf 'namespace Svc;\npublic class Api {\npublic int F() => 1;\n}\n' > repo-g/src/Api.cs
printf 'namespace Svc.Tests;\npublic class ApiTests { }\n' > repo-g/Svc.Tests/ApiTests.cs
cat > repo-g/reports/coverage.xml <<'EOF'
<?xml version="1.0"?>
<coverage lines-valid="12" lines-covered="9" line-rate="0.75"></coverage>
EOF
cat > repo-g/reports/junit.xml <<'EOF'
<?xml version="1.0"?>
<testsuites><testsuite name="dotnet" tests="6" failures="0" errors="0" skipped="0"/></testsuites>
EOF
SNAPG=$(run snapshot --repo repo-g 2>&1)
echo "$SNAPG" | grep -q "coverage=75.0%" && { PASS=$((PASS+1)); echo "  ok   Cobertura reusada (coverlet) 9/12 -> 75.0%"; } || { FAIL=$((FAIL+1)); echo "  FAIL coverage dotnet ($SNAPG)"; }
echo "$SNAPG" | grep -q "tests=6" && { PASS=$((PASS+1)); echo "  ok   junit logger -> 6 tests"; } || { FAIL=$((FAIL+1)); echo "  FAIL test count dotnet ($SNAPG)"; }
echo "$SNAPG" | grep -q "prod_loc=4, test_loc=2" && { PASS=$((PASS+1)); echo "  ok   LOC prod=4 (src/) / test=2 (Svc.Tests/)"; } || { FAIL=$((FAIL+1)); echo "  FAIL LOC dotnet ($SNAPG)"; }

echo "== T22 dotnet: SARIF (Roslyn ErrorLog) error/warning/note =="
cat > repo-g/reports/analysis.sarif <<'EOF'
{"version":"2.1.0","runs":[{"tool":{"driver":{"name":"Roslyn"}},"results":[
 {"ruleId":"CA2100","level":"error","locations":[{"physicalLocation":{"artifactLocation":{"uri":"src/Api.cs"},"region":{"startLine":3}}}]},
 {"ruleId":"CA1822","level":"warning","locations":[{"physicalLocation":{"artifactLocation":{"uri":"src/Api.cs"},"region":{"startLine":2}}}]},
 {"ruleId":"IDE0005","level":"note","locations":[{"physicalLocation":{"artifactLocation":{"uri":"src/Api.cs"},"region":{"startLine":1}}}]}]}]}
EOF
INGG=$(run ingest-gate --repo repo-g --iteration 1 2>&1)
echo "$INGG" | grep -q "repo-g/roslyn: reported=3 gated=1" && { PASS=$((PASS+1)); echo "  ok   SARIF: error=HIGH gateado; warning=MEDIUM; note=INFO"; } || { FAIL=$((FAIL+1)); echo "  FAIL sarif ($INGG)"; }

echo "== T23 adapter cpp: gcovr Cobertura + ctest junit (root PLANO) + LOC tests/ =="
mkdir -p repo-h/src repo-h/tests repo-h/reports
printf '#include "core.h"\nint f() {\nreturn 1;\n}\n' > repo-h/src/core.cpp
printf '#include "core.h"\nTEST(Core, F) { EXPECT_EQ(f(), 1); }\n' > repo-h/tests/core_test.cpp
cat > repo-h/reports/coverage.xml <<'EOF'
<?xml version="1.0"?>
<coverage lines-valid="8" lines-covered="6" line-rate="0.75"></coverage>
EOF
cat > repo-h/reports/junit.xml <<'EOF'
<?xml version="1.0"?>
<testsuite name="ctest" tests="5" failures="0" errors="0" skipped="0"/>
EOF
SNAPH=$(run snapshot --repo repo-h 2>&1)
echo "$SNAPH" | grep -q "coverage=75.0%" && { PASS=$((PASS+1)); echo "  ok   gcovr Cobertura 6/8 -> 75.0%"; } || { FAIL=$((FAIL+1)); echo "  FAIL coverage cpp ($SNAPH)"; }
echo "$SNAPH" | grep -q "tests=5" && { PASS=$((PASS+1)); echo "  ok   ctest junit root PLANO (testsuite) -> 5 tests"; } || { FAIL=$((FAIL+1)); echo "  FAIL test count cpp ($SNAPH)"; }
echo "$SNAPH" | grep -q "prod_loc=4, test_loc=2" && { PASS=$((PASS+1)); echo "  ok   LOC prod=4 (src/) / test=2 (tests/ + _test.cpp)"; } || { FAIL=$((FAIL+1)); echo "  FAIL LOC cpp ($SNAPH)"; }

echo "== T24 cpp: clang-tidy (error/warning/cert floor/.tpp) =="
cat > repo-h/reports/clang-tidy.txt <<'EOF'
src/core.cpp:3:1: error: use of undeclared identifier 'x' [clang-diagnostic-error]
src/core.cpp:2:5: warning: function 'f' should be marked const [readability-make-member-function-const]
src/core.cpp:3:8: warning: calling 'system' uses a command processor [cert-env33-c]
src/impl.tpp:4:2: warning: repeated branch body [bugprone-branch-clone]
2 warnings generated.
EOF
INGH=$(run ingest-gate --repo repo-h --iteration 1 2>&1)
echo "$INGH" | grep -q "repo-h/clang-tidy: reported=4 gated=2" && { PASS=$((PASS+1)); echo "  ok   clang-tidy: error+cert floor=HIGH; readability+.tpp=MEDIUM; ruido stderr ignorado"; } || { FAIL=$((FAIL+1)); echo "  FAIL clang-tidy ($INGH)"; }

echo "== T25 fixes 1.7.0: junit root-max (gotestsum) + go dedupe + backtest.cpp prod =="
# (a) gotestsum reporta errors solo en el ROOT <testsuites> — el max(root, hijos)
# tiene que leer los atributos del root, no solo sumar hijos.
cat > repo-e/reports/junit.xml <<'EOF'
<?xml version="1.0"?>
<testsuites tests="9" failures="0" errors="1" skipped="0"><testsuite name="gotestsum" tests="4" failures="0" errors="0" skipped="0"/></testsuites>
EOF
SNAPE2=$(run snapshot --repo repo-e 2>&1)
echo "$SNAPE2" | grep -q "tests=9" && { PASS=$((PASS+1)); echo "  ok   junit root-attrs mandan: tests=9 (hijos sumaban 4)"; } || { FAIL=$((FAIL+1)); echo "  FAIL junit root-max ($SNAPE2)"; }
# (b) -coverpkg repite bloques entre targets: dedupe por bloque con max(hits).
# El bloque de 2 stmts (0 hits) reaparece con 1 hit -> 5/5 stmts = 100%.
printf 'example.com/m/pkg/mod.go:6.2,8.3 2 1\n' >> repo-e/coverage.out
SNAPE3=$(run snapshot --repo repo-e 2>&1)
echo "$SNAPE3" | grep -q "coverage=100.0%" && { PASS=$((PASS+1)); echo "  ok   cover profile dedupeado por bloque con max(hits) -> 100.0%"; } || { FAIL=$((FAIL+1)); echo "  FAIL go dedupe ($SNAPE3)"; }
# (c) sufijo bare 'test.cpp' NO debe tragar backtest.cpp como test LOC.
printf 'int backtest() {\nreturn 2;\n}\n' > repo-h/src/backtest.cpp
SNAPH2=$(run snapshot --repo repo-h 2>&1)
echo "$SNAPH2" | grep -q "prod_loc=7, test_loc=2" && { PASS=$((PASS+1)); echo "  ok   backtest.cpp cuenta como PROD (CamelCase Test.cpp es el patron de test)"; } || { FAIL=$((FAIL+1)); echo "  FAIL backtest.cpp ($SNAPH2)"; }

echo "== T26 adapter gradle: JaCoCo en paths gradle + test-results + LOC source sets =="
mkdir -p repo-i/src/main/kotlin repo-i/src/test/kotlin repo-i/src/integrationTest/kotlin repo-i/build/reports/jacoco/test repo-i/build/test-results/test repo-i/build/reports/detekt
printf 'package app\nfun f(): Int {\nreturn 1\n}\n' > repo-i/src/main/kotlin/App.kt
printf 'package app\nclass AppTest { }\n' > repo-i/src/test/kotlin/AppTest.kt
printf 'package app\nclass AppIT { }\n' > repo-i/src/integrationTest/kotlin/AppIT.kt
cat > repo-i/build/reports/jacoco/test/jacocoTestReport.xml <<'EOF'
<?xml version="1.0"?>
<report name="jvm-service"><counter type="LINE" missed="3" covered="9"/></report>
EOF
cat > repo-i/build/test-results/test/TEST-app.AppTest.xml <<'EOF'
<?xml version="1.0"?>
<testsuite name="app.AppTest" tests="8" failures="0" errors="0" skipped="0"/>
EOF
SNAPI=$(run snapshot --repo repo-i 2>&1)
echo "$SNAPI" | grep -q "coverage=75.0%" && { PASS=$((PASS+1)); echo "  ok   JaCoCo en build/reports/jacoco 9/12 -> 75.0%"; } || { FAIL=$((FAIL+1)); echo "  FAIL coverage gradle ($SNAPI)"; }
echo "$SNAPI" | grep -q "tests=8" && { PASS=$((PASS+1)); echo "  ok   build/test-results TEST-*.xml -> 8 tests"; } || { FAIL=$((FAIL+1)); echo "  FAIL test count gradle ($SNAPI)"; }
echo "$SNAPI" | grep -q "prod_loc=4, test_loc=4" && { PASS=$((PASS+1)); echo "  ok   LOC src/main=4 prod / src/test + src/integrationTest=4 test (source sets custom)"; } || { FAIL=$((FAIL+1)); echo "  FAIL LOC gradle ($SNAPI)"; }

echo "== T27 gradle: detekt (checkstyle reusado, paths ABSOLUTOS como el default real) =="
ABSI="$("$PY" -c "import os;print(os.path.abspath('repo-i/src/main/kotlin/App.kt'))")"
cat > repo-i/build/reports/detekt/detekt.xml <<EOF
<?xml version="1.0"?>
<checkstyle version="4.3">
  <file name="$ABSI">
    <error line="2" severity="error" message="ForbiddenCall" source="detekt.ForbiddenCall"/>
    <error line="3" severity="warning" message="MagicNumber" source="detekt.MagicNumber"/>
  </file>
</checkstyle>
EOF
INGI=$(run ingest-gate --repo repo-i --iteration 1 2>&1)
echo "$INGI" | grep -q "repo-i/detekt: reported=2 gated=1" && { PASS=$((PASS+1)); echo "  ok   detekt via parse_checkstyle: error=HIGH gateado, warning=MEDIUM"; } || { FAIL=$((FAIL+1)); echo "  FAIL detekt ($INGI)"; }
"$PY" -c "
import json, sys
node = json.load(open('QA-LEDGER.json'))['repos']['repo-i']
ids = [i for s in node['iterations'] if s.get('finding_ids') for i in s['finding_ids']]
ok = any(x.startswith('detekt:') and 'src/main/kotlin/App.kt' in x.replace(chr(92), '/') and not x.replace(chr(92), '/').count(':/') for x in ids)
sys.exit(0 if ok else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   IDs detekt repo-relativos (path absoluto relativizado)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL IDs detekt no relativizados"; }
run readiness 2>/dev/null | grep "NEVER ran" | grep -q "repo-i" \
  && { FAIL=$((FAIL+1)); echo "  FAIL repo-i sigue UNMEASURED tras ingest"; } \
  || { PASS=$((PASS+1)); echo "  ok   repo-i ya no es UNMEASURED tras ingest"; }

echo "== T28 adapter swift: lcov + xunit + LOC Sources/Tests + swiftlint =="
mkdir -p repo-j/Sources/Kit repo-j/Tests/KitTests repo-j/coverage repo-j/reports
printf 'public func f() -> Int {\nreturn 1\n}\n' > repo-j/Sources/Kit/Kit.swift
printf 'import XCTest\nfinal class KitTests: XCTestCase { }\n' > repo-j/Tests/KitTests/KitTests.swift
printf 'SF:Sources/Kit/Kit.swift\nLF:16\nLH:12\nend_of_record\n' > repo-j/coverage/lcov.info
cat > repo-j/reports/junit.xml <<'EOF'
<?xml version="1.0"?>
<testsuites><testsuite name="KitTests" tests="7" failures="0" errors="0" skipped="0"/></testsuites>
EOF
# Swift 6 / Swift Testing: --xunit-output escribe un SEGUNDO archivo con los
# resultados de Swift Testing — el engine debe SUMAR ambos (sets disjuntos);
# si lo ignorara, este failure real seria invisible (fail-open).
cat > repo-j/reports/junit-swift-testing.xml <<'EOF'
<?xml version="1.0"?>
<testsuites><testsuite name="SwiftTesting" tests="2" failures="1" errors="0" skipped="0"/></testsuites>
EOF
SNAPJ=$(run snapshot --repo repo-j 2>&1)
echo "$SNAPJ" | grep -q "coverage=75.0%" && { PASS=$((PASS+1)); echo "  ok   lcov reusado (llvm-cov export) 12/16 -> 75.0%"; } || { FAIL=$((FAIL+1)); echo "  FAIL coverage swift ($SNAPJ)"; }
echo "$SNAPJ" | grep -q "tests=9" && { PASS=$((PASS+1)); echo "  ok   XCTest (7) + Swift Testing (2) SUMADOS -> 9 tests (failure real visible)"; } || { FAIL=$((FAIL+1)); echo "  FAIL test count swift dual-file ($SNAPJ)"; }
echo "$SNAPJ" | grep -q "prod_loc=3, test_loc=2" && { PASS=$((PASS+1)); echo "  ok   LOC Sources/=3 / Tests/=2 (convencion SwiftPM)"; } || { FAIL=$((FAIL+1)); echo "  FAIL LOC swift ($SNAPJ)"; }
ABSJ="$("$PY" -c "import os;print(os.path.abspath('repo-j/Sources/Kit/Kit.swift'))")"
cat > repo-j/reports/swiftlint.xml <<EOF
<?xml version="1.0"?>
<checkstyle version="4.3">
  <file name="$ABSJ">
    <error line="1" severity="error" message="Force Cast Violation" source="swiftlint.force_cast"/>
    <error line="2" severity="warning" message="Line Length Violation" source="swiftlint.line_length"/>
  </file>
</checkstyle>
EOF
INGJ=$(run ingest-gate --repo repo-j --iteration 1 2>&1)
echo "$INGJ" | grep -q "repo-j/swiftlint: reported=2 gated=1" && { PASS=$((PASS+1)); echo "  ok   swiftlint via parse_checkstyle: error=HIGH gateado, warning=MEDIUM"; } || { FAIL=$((FAIL+1)); echo "  FAIL swiftlint ($INGJ)"; }
"$PY" -c "
import json, sys
node = json.load(open('QA-LEDGER.json'))['repos']['repo-j']
ids = [i for s in node['iterations'] if s.get('finding_ids') for i in s['finding_ids']]
ok = any(x.startswith('swiftlint:') and 'Sources/Kit/Kit.swift' in x.replace(chr(92), '/') and not x.replace(chr(92), '/').count(':/') for x in ids)
sys.exit(0 if ok else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   IDs swiftlint repo-relativos (sin colision por basename)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL IDs swiftlint no relativizados"; }

echo "== T29 acceptance trazable: AC-n cierra por testcase MEDIDO, no por checkbox =="
# AC-1: checkbox [x] + testcase verde 'test_ac1_*' -> cierra MEDIDO.
# AC-2: checkbox [x] pero su testcase FALLA -> narrated-only, NO cierra.
# AC-3: sin marcar y sin test -> abierta. Dimension acceptance = 1/3.
printf -- "# ACCEPTANCE\n\n- [x] AC-01 alta de cliente valida\n- [x] AC-02 rechazo de duplicado\n- [ ] AC-03 baja logica\n" > ACCEPTANCE.md
cat > repo-c/reports/junit.xml <<'EOF'
<?xml version="1.0"?>
<testsuites><testsuite name="pytest" tests="3" failures="1" errors="0" skipped="0">
<testcase classname="tests.test_flow" name="test_ac1_alta_ok"/>
<testcase classname="tests.test_flow" name="test_ac_02_rechazo_duplicado"><failure message="boom"/></testcase>
<testcase classname="tests.test_misc" name="test_sin_criterio"/>
</testsuite></testsuites>
EOF
RDY=$(run readiness --json 2>/dev/null)
echo "$RDY" | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
a = d['acceptance']
ok = (a['traceable'] is True and a['measured_closed'] == ['AC-1']
      and a['narrated_only'] == ['AC-2']
      and abs(d['dimensions']['acceptance']['raw'] - 0.333) < 0.01)
sys.exit(0 if ok else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   AC-1 cierra medido; AC-2 narrated-only (test rojo veta); dim=1/3"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL acceptance trazable ($(echo "$RDY" | "$PY" -c 'import json,sys;print(json.load(sys.stdin)["acceptance"])' 2>/dev/null))"; }
run readiness 2>/dev/null | grep -q "narrated-only: AC-2" \
  && { PASS=$((PASS+1)); echo "  ok   warning narrated-only visible (measured beats narrated)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL sin warning narrated-only"; }
# % TERMINADO medido (1.28.0): 1 de 3 AC cerrado por test verde = 33.3%, informativo
run readiness --json 2>/dev/null | "$PY" -c "import json,sys; sys.exit(0 if json.load(sys.stdin)['acceptance']['measured_pct']==33.3 else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   acceptance.measured_pct = 33.3% en --json (1 de 3 medido)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL measured_pct mal computado"; }
run readiness 2>/dev/null | grep -q "acceptance medido: 33.3%" \
  && { PASS=$((PASS+1)); echo "  ok   '% terminado' medido visible en la vista default"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL linea de acceptance medido ausente"; }
# sin trazabilidad AC-n NO hay % honesto: la linea no debe aparecer
printf -- "# ACCEPTANCE\n\n- [x] criterio uno\n- [ ] criterio dos\n" > ACCEPTANCE.md
run readiness 2>/dev/null | grep -q "acceptance medido:" \
  && { FAIL=$((FAIL+1)); echo "  FAIL muestra % medido sin AC-IDs (deshonesto)"; } \
  || { PASS=$((PASS+1)); echo "  ok   sin AC-IDs no muestra % medido (honesto)"; }
printf -- "# ACCEPTANCE\n\n- [x] AC-01 alta de cliente valida\n- [x] AC-02 rechazo de duplicado\n- [ ] AC-03 baja logica\n" > ACCEPTANCE.md

echo "== T30 spec-check --acceptance: trazabilidad como FACT =="
chk "acceptance con AC-IDs -> exit 0" 0 run spec-check --acceptance ACCEPTANCE.md
printf -- "- [ ] criterio sin id\n" > acc-untraced.md
chk "cero criterios trazables -> BLOCKED exit 1" 1 run spec-check --acceptance acc-untraced.md
printf -- "- [ ] AC-01 a\n- [x] AC-1 b\n" > acc-dup.md
chk "IDs duplicados (AC-01 == AC-1 normalizado) -> exit 1" 1 run spec-check --acceptance acc-dup.md

echo "== T31 edges 1.10.0: regex sin falsos positivos + flaky de surefire =="
# HVAC2/mac1/track12 NO son tags AC; classname jamas taggea (solo el NOMBRE);
# flaky que paso tras retry (solo <flakyFailure>) = verde; fallo definitivo
# (<failure> + <rerunFailure>) = rojo y veta.
"$PY" -c "
import sys, os, tempfile
sys.path.insert(0, os.path.dirname(sys.argv[1]))
import qa_ledger as q
for name in ('testHVAC2Compressor', 'test_mac1_address', 'testMac1Parse', 'test_track12'):
    assert q._AC_TAG.findall(name) == [], name
for name, want in (('test_ac1_alta', ['1']), ('testAC01X', ['1']), ('AC-01: alta', ['1'])):
    assert q._AC_TAG.findall(name) == want, name
xml_ = '''<testsuites><testsuite name=\"s\">
<testcase classname=\"tests.test_ac9_flow\" name=\"test_sin_tag\"/>
<testcase classname=\"C\" name=\"test_ac1_flaky\"><flakyFailure message=\"retry\"/></testcase>
<testcase classname=\"C\" name=\"test_ac2_fallo\"><failure message=\"x\"/><rerunFailure message=\"r\"/></testcase>
</testsuite></testsuites>'''
d = tempfile.mkdtemp(); os.makedirs(os.path.join(d, 'reports'))
open(os.path.join(d, 'reports', 'junit.xml'), 'w').write(xml_)
t, _stale = q._ac_tags(d, 'python')
assert 'AC-9' not in t, 'classname no taggea'
# kit 1.50.0: tags also carry 'cases' (the receipt) -- assert counts by key, not dict shape
assert (t['AC-1']['green'], t['AC-1']['red']) == (1, 0), 'flaky-que-paso = verde'
assert (t['AC-2']['green'], t['AC-2']['red']) == (0, 1), 'fallo-tras-reruns = rojo'
assert all('test' in c and 'report' in c for c in t['AC-1']['cases']), 'cases con recibo'
sys.exit(0)" "$QL" \
  && { PASS=$((PASS+1)); echo "  ok   sin falsos positivos (HVAC2/mac1/track12); classname no taggea; flaky ok"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL edges regex/flaky 1.10.0"; }

echo "== T32 simplicity: tests FUERA del presupuesto (M9, Topic 51) =="
# Diff con 6 lineas de prod y 300 de test: el presupuesto solo ve las 6.
"$PY" -c "
import io, os, sys
sys.path.insert(0, os.path.dirname(sys.argv[1]))
import qa_ledger as q
prod = ''.join(f'+line {i}\n' for i in range(6))
test = ''.join(f'+assert {i}\n' for i in range(300))
diff = (
    'diff --git a/src/main/java/App.java b/src/main/java/App.java\n'
    '--- a/src/main/java/App.java\n+++ b/src/main/java/App.java\n@@ -0,0 +1,6 @@\n' + prod +
    'diff --git a/src/test/java/AppTest.java b/src/test/java/AppTest.java\n'
    '--- /dev/null\n+++ b/src/test/java/AppTest.java\n@@ -0,0 +1,300 @@\n' + test +
    'diff --git a/tests/test_flow.py b/tests/test_flow.py\n'
    '--- /dev/null\n+++ b/tests/test_flow.py\n@@ -0,0 +1,2 @@\n+x = 1\n+y = 2\n'
)
m = q._simplicity_metrics(diff, 4)
assert m['lines_added'] == 6, m
assert m['files_changed'] == 1, m
assert m['test_lines_added'] == 302, m
assert m['test_files_changed'] == 2, m
# clasificador: convenciones de los 9 stacks, sin tragar backtest.cpp
tf = q._is_simplicity_test_file
assert tf('src/test/java/AppTest.java') and tf('tests/test_flow.py')
assert tf('src/integrationTest/kotlin/FlowTest.kt') and tf('lib/foo.spec.ts')
assert tf('Api.Tests/FooTests.cs') and tf('pkg/foo_test.go')
assert not tf('src/main/java/App.java') and not tf('src/backtest.cpp')
assert not tf('src/protest.cc') and not tf('Sources/Core/Engine.swift')
sys.exit(0)" "$QL" \
  && { PASS=$((PASS+1)); echo "  ok   presupuesto solo prod (6 lineas, 1 archivo); tests contados aparte (+302 en 2)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL tests dentro del presupuesto de simplicity"; }

echo "== T33 gate-check: borrado de tests go/dotnet/js tambien bloquea (clasificador unificado) =="
# gate-check reusa el clasificador de los 9 stacks + TESTDEF ampliado: la promesa
# 'borrar tests lo bloquea gate-check' vale para TODAS las convenciones, no solo JVM.
printf -- "diff --git a/pkg/foo_test.go b/pkg/foo_test.go\n--- a/pkg/foo_test.go\n+++ /dev/null\n@@ -1,2 +0,0 @@\n-func TestFoo(t *testing.T) {\n-\tassertEqual(t, 1, 1)\n" > del-go.diff
chk "delete de foo_test.go (Go) -> BLOCKER" 1 run gate-check --diff del-go.diff
printf -- "diff --git a/Api.Tests/CalcTests.cs b/Api.Tests/CalcTests.cs\n--- a/Api.Tests/CalcTests.cs\n+++ /dev/null\n@@ -1,2 +0,0 @@\n-[Fact]\n-public void Suma_Valida() { Assert.Equal(2, Calc.Suma(1,1)); }\n" > del-cs.diff
chk "delete de Api.Tests/*.cs (xunit [Fact]) -> BLOCKER" 1 run gate-check --diff del-cs.diff
printf -- "diff --git a/__tests__/flow.test.ts b/__tests__/flow.test.ts\n--- a/__tests__/flow.test.ts\n+++ /dev/null\n@@ -1,2 +0,0 @@\n-it('valida el flujo', () => {\n-  expect(flow()).toBe(true);\n" > del-ts.diff
chk "delete de __tests__/*.test.ts (it/expect) -> BLOCKER" 1 run gate-check --diff del-ts.diff

echo "== T34 gate-check: secret-scan (Topic 43) — secretos agregados bloquean como hecho =="
printf -- "diff --git a/src/cfg.py b/src/cfg.py\n--- a/src/cfg.py\n+++ b/src/cfg.py\n@@ -0,0 +1,1 @@\n+AWS_KEY = \"AKIAIOSFODNN7EXAMPLE\"\n" > sec-akia.diff
chk "AWS access key agregada -> BLOCKER" 1 run gate-check --diff sec-akia.diff
printf -- "diff --git a/deploy/id_rsa b/deploy/id_rsa\n--- /dev/null\n+++ b/deploy/id_rsa\n@@ -0,0 +1,1 @@\n+-----BEGIN PRIVATE KEY-----\n" > sec-pem.diff
chk "clave privada PEM agregada -> BLOCKER" 1 run gate-check --diff sec-pem.diff
printf -- "diff --git a/certs/client.p12 b/certs/client.p12\nindex 0000000..1111111 100644\nBinary files a/certs/client.p12 and b/certs/client.p12 differ\n" > sec-p12.diff
chk "contenedor .p12 binario agregado -> BLOCKER" 1 run gate-check --diff sec-p12.diff
printf -- "diff --git a/certs/old.p12 b/certs/old.p12\ndeleted file mode 100644\nindex 1111111..0000000\nBinary files a/certs/old.p12 and /dev/null differ\n" > sec-del.diff
chk "BORRAR un .p12 no bloquea (sacar secretos es bueno)" 0 run gate-check --diff sec-del.diff
printf -- "diff --git a/src/cfg.py b/src/cfg.py\n--- a/src/cfg.py\n+++ b/src/cfg.py\n@@ -0,0 +1,1 @@\n+password = \"hunter2secreto\"\n" > sec-lit.diff
chk "literal password generico -> REVIEW exit 0 (advisory)" 0 run gate-check --diff sec-lit.diff
chk "literal password generico + --strict -> exit 1" 1 run gate-check --diff sec-lit.diff --strict

echo "== T35 ledger atomico: checksum de integridad + carga blindada =="
# el ledger recien escrito trae integrity y carga verificado
chk "ledger con integrity carga OK" 0 run summary
# mutacion EXTERNA (JSON valido, contenido cambiado, hash viejo) -> bloquea
"$PY" -c "
import json, sys
d = json.load(open('QA-LEDGER.json', encoding='utf-8'))
assert 'integrity' in d and d['integrity']['sha256'], 'falta integrity en ledger nuevo'
d['config']['defaults']['coverage_threshold'] = 1
json.dump(d, open('QA-LEDGER.json', 'w', encoding='utf-8'))"
chk "mutacion externa (checksum roto) -> bloquea exit 1" 1 run summary
run summary 2>&1 | grep -qi "checksum" \
  && { PASS=$((PASS+1)); echo "  ok   mensaje de checksum presente (no traceback)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL sin mensaje de checksum"; }
# aceptacion humana explicita: borrar 'integrity' -> legacy, carga sin verificar
"$PY" -c "
import json
d = json.load(open('QA-LEDGER.json', encoding='utf-8'))
del d['integrity']
json.dump(d, open('QA-LEDGER.json', 'w', encoding='utf-8'))"
chk "legacy sin integrity -> carga OK (adopcion incremental)" 0 run summary
# JSON corrupto (escritura parcial) -> mensaje de recuperacion, no traceback
"$PY" -c "open('QA-LEDGER.json','a',encoding='utf-8').write('{trunc')"
chk "JSON corrupto -> exit 1 con mensaje" 1 run summary
run summary 2>&1 | grep -q "Traceback" \
  && { FAIL=$((FAIL+1)); echo "  FAIL traceback crudo en ledger corrupto"; } \
  || { PASS=$((PASS+1)); echo "  ok   sin traceback: mensaje de recuperacion"; }
# restaurar el ledger para lo que venga despues (re-init limpio)
run init --config uscha.config.json >/dev/null 2>&1

echo "== T36 plateau/stop-signal: advisory sobre el historico (Know When to Stop) =="
# (a) stall: findings gateados SUBIENDO 3 ciclos COMPLETOS en repo-a -> re-planear.
# Con qa_tools_order configurado solo cuentan ciclos con TODAS las tools logueadas.
for i in 1 2 3; do
  run log-step --repo repo-a --tool code-review --iteration $i \
    --reported $((i+3)) --gated-reported $((i+3)) --tests-passed true >/dev/null 2>&1
  for t in judgment-day improve; do
    run log-step --repo repo-a --tool $t --iteration $i \
      --gated-reported 0 --tests-passed true >/dev/null 2>&1
  done
done
run readiness 2>/dev/null | grep -q "stall: repo-a" \
  && { PASS=$((PASS+1)); echo "  ok   stall detectado (findings 4->5->6, iterar no acerca)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL sin aviso de stall"; }
# (b) mismo patron pero con el ULTIMO ciclo INCOMPLETO (1 de 3 tools) -> no cuenta,
# la serie completa queda corta y el stall NO dispara (sin contaminacion parcial)
run log-step --repo repo-a --tool code-review --iteration 4 \
  --gated-reported 9 --tests-passed true >/dev/null 2>&1
run readiness 2>/dev/null | grep -q "stall: repo-a" \
  && { PASS=$((PASS+1)); echo "  ok   ciclo 4 parcial no rompe la serie (stall sigue por ciclos 1-3)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL ciclo parcial altero la deteccion"; }
# (c) serie BAJANDO no es stall (hay progreso)
run init --config uscha.config.json >/dev/null 2>&1
for i in 1 2 3; do
  run log-step --repo repo-a --tool code-review --iteration $i \
    --reported $((7-i*2)) --gated-reported $((7-i*2)) --tests-passed true >/dev/null 2>&1
  for t in judgment-day improve; do
    run log-step --repo repo-a --tool $t --iteration $i \
      --gated-reported 0 --tests-passed true >/dev/null 2>&1
  done
done
run readiness 2>/dev/null | grep -q "stall: repo-a" \
  && { FAIL=$((FAIL+1)); echo "  FAIL stall con serie bajando (5->3->1 es progreso)"; } \
  || { PASS=$((PASS+1)); echo "  ok   serie bajando (5->3->1) no dispara stall"; }
# (c) stop-signal: repo unico convergido, cero facts bloqueantes -> candidato a PR
printf '{ "defaults": { "acceptance_file": "ACCEPTANCE.md", "qa_tools_order": ["code-review","judgment-day","improve"] },\n  "repos": [ {"name":"solo","path":"repo-c","type":"python"} ], "integration": {"enabled": false} }\n' > c-solo.json
run init --config c-solo.json --out L-solo.json >/dev/null 2>&1
for t in code-review judgment-day improve; do
  run log-step --ledger L-solo.json --repo solo --tool $t --iteration 1 \
    --gated-reported 0 --files-changed 0 --tests-passed true >/dev/null 2>&1
done
RDY=$(run readiness --ledger L-solo.json --json 2>/dev/null)
echo "$RDY" | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
a = d['advice']
sys.exit(0 if a['stop_signal'] is True and a['stalled_repos'] == [] else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   stop-signal: convergido + cero facts bloqueantes -> candidato a PR"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL stop-signal no emitido ($(echo "$RDY" | "$PY" -c 'import json,sys;print(json.load(sys.stdin).get("advice"))' 2>/dev/null))"; }

echo "== T37 golden scrub: volatiles declarados enmascaran, el masking es VISIBLE =="
# Nota INV-GOLDEN-01: crear un .approved es un acto HUMANO incluso en tests —
# igual que el path CLEAN byte-a-byte, el path CLEAN-via-scrub NO se auto-testea.
# La mecanica de scrub se prueba a nivel FUNCION (sin fixtures aprobados).
"$PY" -c "
import sys, os, re
sys.path.insert(0, os.path.dirname(sys.argv[1]))
import qa_ledger as q
rules = [(re.compile(r'\d{4}-\d{2}-\d{2}T[0-9:Z.+-]+'), '<TS>', 'ts')]
counts = {}
a = q._scrub(b'ok at 2026-07-03T10:00:00Z\nvalor=42\n', rules, counts)
b = q._scrub(b'ok at 2026-07-01T09:30:00Z\nvalor=42\n', rules, counts)
assert a == b == b'ok at <TS>\nvalor=42\n', (a, b)
assert counts['ts'] == 2, counts        # el masking se CUENTA, no es magia
# divergencia real (mas alla del volatil) NO se enmascara
c = q._scrub(b'ok at 2026-07-03T10:00:00Z\nvalor=99\n', rules, counts)
assert c != a
# binario: intacto, sigue byte a byte
raw = bytes([0xff, 0xfe, 0x00, 0x42])
assert q._scrub(raw, rules, counts) == raw
sys.exit(0)" "$QL" \
  && { PASS=$((PASS+1)); echo "  ok   scrub enmascara volatiles, cuenta sustituciones, binario intacto"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL mecanica de scrub"; }
mkdir -p gsc
printf "ok at 2026-07-03T10:00:00Z\n" > gsc/out.received.txt
printf '{ "rules": [ {"pattern": "\\\\d{4}-\\\\d{2}-\\\\d{2}T[0-9:Z.+-]+", "replace": "<TS>"} ] }\n' > gsc/golden.scrub.json
# el scrub NO fabrica aprobacion: .received sin .approved sigue DIVERGE
chk "scrub activo sin .approved -> sigue DIVERGE exit 1" 1 run golden-diff --dir gsc
# scrub invalido = error de config explicito, jamas se saltea en silencio
printf '{ "rules": [ {"pattern": "([", "replace": "x"} ] }\n' > gsc/golden.scrub.json
chk "scrub invalido (regex rota) -> exit 2 (config error)" 2 run golden-diff --dir gsc
printf '[ {"pattern": "x", "replace": "y"} ]\n' > gsc/golden.scrub.json
chk "scrub con shape invalida (lista a secas) -> exit 2, no traceback" 2 run golden-diff --dir gsc
printf '{}\n' > gsc/golden.scrub.json
chk "scrub sin key rules (typo) -> exit 2, no degrada a cero reglas" 2 run golden-diff --dir gsc
# gate-check: editar el scrub es señal blanda visible
printf -- "diff --git a/fixtures/golden.scrub.json b/fixtures/golden.scrub.json\n--- a/fixtures/golden.scrub.json\n+++ b/fixtures/golden.scrub.json\n@@ -0,0 +1,1 @@\n+{ \"rules\": [ {\"pattern\": \".*\", \"replace\": \"\"} ] }\n" > scrub-edit.diff
run gate-check --diff scrub-edit.diff 2>/dev/null | grep -q "scrub" \
  && { PASS=$((PASS+1)); echo "  ok   gate-check flaggea edicion de reglas de scrub (REVIEW)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL edicion de scrub invisible para gate-check"; }
chk "edicion de scrub + --strict -> exit 1" 1 run gate-check --diff scrub-edit.diff --strict
printf -- "diff --git a/fixtures/golden.scrub.json b/fixtures/golden.scrub.json\n--- a/fixtures/golden.scrub.json\n+++ /dev/null\n@@ -1,1 +0,0 @@\n-{ \"rules\": [ {\"pattern\": \"x\", \"replace\": \"y\"} ] }\n" > scrub-del.diff
run gate-check --diff scrub-del.diff 2>/dev/null | grep -q "scrub" \
  && { PASS=$((PASS+1)); echo "  ok   BORRAR el scrub tambien se flaggea (borrar reglas es editarlas)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL borrado de scrub invisible"; }

echo "== T38 regression-check: cierre sin test = NARRADO, jamas medido (Find Bugs Once) =="
# fix SIN tocar tests: solo produccion cambiada
printf -- "diff --git a/src/main/java/App.java b/src/main/java/App.java\n--- a/src/main/java/App.java\n+++ b/src/main/java/App.java\n@@ -0,0 +1,1 @@\n+if (x != null) { return x.trim(); }\n" > fix-sin-test.diff
chk "cierre sin test -> NARRATED, advisory exit 0" 0 run regression-check --repo repo-a --fixed 2 --diff fix-sin-test.diff
run regression-check --repo repo-a --fixed 2 --diff fix-sin-test.diff 2>/dev/null | grep -q "NARRATED" \
  && { PASS=$((PASS+1)); echo "  ok   verdict NARRATED visible (cierre narrado, no medido)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL sin verdict NARRATED"; }
chk "cierre sin test + --strict -> exit 1" 1 run regression-check --repo repo-a --fixed 2 --diff fix-sin-test.diff --strict
# fix CON test que reproduce: MEASURED
printf -- "diff --git a/src/main/java/App.java b/src/main/java/App.java\n--- a/src/main/java/App.java\n+++ b/src/main/java/App.java\n@@ -0,0 +1,1 @@\n+if (x != null) { return x.trim(); }\ndiff --git a/src/test/java/AppTest.java b/src/test/java/AppTest.java\n--- a/src/test/java/AppTest.java\n+++ b/src/test/java/AppTest.java\n@@ -0,0 +1,2 @@\n+@Test\n+void testNullInputRegression() { assertNull(app.run(null)); }\n" > fix-con-test.diff
chk "cierre con test nuevo -> MEASURED exit 0 (aun con --strict)" 0 run regression-check --repo repo-a --fixed 2 --diff fix-con-test.diff --strict
# nada cerrado -> N/A, nada que exigir
chk "fixed 0 -> N/A exit 0 (aun con --strict)" 0 run regression-check --repo repo-a --fixed 0 --diff fix-sin-test.diff --strict
# gaming barato: UNA linea EN BLANCO en un test file NO es evidencia
printf -- "diff --git a/src/test/java/AppTest.java b/src/test/java/AppTest.java\n--- a/src/test/java/AppTest.java\n+++ b/src/test/java/AppTest.java\n@@ -0,0 +1,1 @@\n+\n" > fix-blank.diff
chk "linea en blanco en test file NO es evidencia -> NARRATED --strict exit 1" 1 \
  run regression-check --repo repo-a --fixed 2 --diff fix-blank.diff --strict
# evidencia debil (linea de test sin testdef ni assert) -> MEASURED pero avisa
printf -- "diff --git a/src/test/java/AppTest.java b/src/test/java/AppTest.java\n--- a/src/test/java/AppTest.java\n+++ b/src/test/java/AppTest.java\n@@ -0,0 +1,1 @@\n+// nota\n" > fix-weak.diff
run regression-check --repo repo-a --fixed 2 --diff fix-weak.diff 2>/dev/null | grep -q "DEBIL" \
  && { PASS=$((PASS+1)); echo "  ok   evidencia debil (sin testdef/assert) marcada para el ojo humano"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL evidencia debil invisible"; }

echo "== T39 procedencia de umbrales: requerimiento (config) vs default del kit =="
# cap DECLARADO en config (tests_red: 1 — siempre muerde con el junit rojo de repo-c)
printf '{ "defaults": { "acceptance_file": "ACCEPTANCE.md", "readiness_caps": {"tests_red": 1} },\n  "repos": [ {"name":"solo","path":"repo-c","type":"python"} ], "integration": {"enabled": false} }\n' > c-caps.json
run init --config c-caps.json --out L-caps.json >/dev/null 2>&1
run snapshot --ledger L-caps.json --repo solo >/dev/null 2>&1
RDY=$(run readiness --ledger L-caps.json --json 2>/dev/null)
echo "$RDY" | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
td = d['thresholds_declared']
ok = (d['cap_source'] == 'requerimiento (config)'
      and td['readiness_caps'] == ['tests_red']
      and td['coverage_threshold'] is False)
sys.exit(0 if ok else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   cap declarado en config etiquetado 'requerimiento (config)'"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL procedencia en readiness ($(echo "$RDY" | "$PY" -c 'import json,sys;d=json.load(sys.stdin);print(d.get("cap_source"),d.get("thresholds_declared"))' 2>/dev/null))"; }
run readiness --ledger L-caps.json 2>/dev/null | grep -q "requerimiento (config)" \
  && { PASS=$((PASS+1)); echo "  ok   etiqueta de procedencia visible en el texto del cap"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL etiqueta de procedencia ausente en texto"; }
# el sandbox principal no declara caps: la lista de declarados queda vacia
run readiness --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
sys.exit(0 if d['thresholds_declared']['readiness_caps'] == [] else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   sin caps declarados -> lista vacia (defaults = opinion del kit)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL thresholds_declared del sandbox principal"; }
# simplicity: sin config -> todos default (aviso); con presupuesto CLI -> declarado
printf -- "diff --git a/src/A.java b/src/A.java\n--- a/src/A.java\n+++ b/src/A.java\n@@ -0,0 +1,1 @@\n+int x = 1;\n" > simp-tiny.diff
run simplicity-check --diff simp-tiny.diff 2>/dev/null | grep -q "defaults del kit" \
  && { PASS=$((PASS+1)); echo "  ok   simplicity avisa: presupuestos = opinion del kit"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL sin aviso de presupuestos default"; }
run simplicity-check --diff simp-tiny.diff --max-lines-added 100 --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
sys.exit(0 if d['budgets_declared'] == ['max_lines_added'] else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   presupuesto declarado por CLI listado en budgets_declared"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL budgets_declared no refleja el CLI"; }

echo "== T40 phase: FSM DERIVADA del ledger — el estado se computa, no se declara =="
mkdir -p repo-x/reports
cat > repo-x/reports/junit.xml <<'EOF'
<testsuite tests="1" failures="0" errors="0" skipped="0"/>
EOF
printf '{ "defaults": { "acceptance_file": "ACCEPTANCE.md", "qa_tools_order": ["code-review","judgment-day","improve"] },\n  "repos": [ {"name":"fsm","path":"repo-x","type":"go"} ], "integration": {"enabled": false} }\n' > c-fsm.json
run init --config c-fsm.json --out L-fsm.json >/dev/null 2>&1
chk "ledger virgen -> plan" 0 run phase --ledger L-fsm.json --repo fsm --require plan
run snapshot --ledger L-fsm.json --repo fsm >/dev/null 2>&1
chk "snapshot medido sin QA -> build" 0 run phase --ledger L-fsm.json --repo fsm --require build
run log-step --ledger L-fsm.json --repo fsm --tool code-review --iteration 1 \
  --reported 2 --gated-reported 2 --tests-passed true >/dev/null 2>&1
chk "pasos de QA sin converger -> qa" 0 run phase --ledger L-fsm.json --repo fsm --require qa
chk "pedir pr-ready con findings abiertos -> exit 1 (los hechos mandan)" 1 \
  run phase --ledger L-fsm.json --repo fsm --require pr-ready
run escalate --ledger L-fsm.json --repo fsm --reason "duda de diseño" >/dev/null 2>&1
chk "escalacion abierta -> escalated (pisa todo)" 0 run phase --ledger L-fsm.json --repo fsm --require escalated
run resolve-escalation --ledger L-fsm.json --repo fsm --note ok >/dev/null 2>&1
for t in code-review judgment-day improve; do
  run log-step --ledger L-fsm.json --repo fsm --tool $t --iteration 2 \
    --gated-reported 0 --files-changed 0 --tests-passed true >/dev/null 2>&1
done
chk "convergido + limpio -> pr-ready" 0 run phase --ledger L-fsm.json --repo fsm --require pr-ready

echo "== T41 spike/*: codigo descartable por contrato — jamas pasa el gate de PR =="
# repo-x convergido (pr-ready por hechos, de T40) pero en rama spike/* -> DENEGADO
git init -q repo-x 2>/dev/null
git -C repo-x symbolic-ref HEAD refs/heads/spike/idea-loca
chk "pr-ready por hechos PERO rama spike/* -> exit 1" 1 \
  run phase --ledger L-fsm.json --repo fsm --require pr-ready
run phase --ledger L-fsm.json --repo fsm --require pr-ready 2>/dev/null | grep -q "ADR con las lecciones" \
  && { PASS=$((PASS+1)); echo "  ok   mensaje del contrato de spike visible (ADR, no PR)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL sin mensaje de contrato de spike"; }
# misma rama consultada SIN --require: informa, no bloquea
chk "phase sin --require en rama spike -> exit 0 (informa, no gatea)" 0 \
  run phase --ledger L-fsm.json --repo fsm
git -C repo-x symbolic-ref HEAD refs/heads/main
chk "rama normal -> pr-ready OK de nuevo" 0 \
  run phase --ledger L-fsm.json --repo fsm --require pr-ready
# default sin --fixed: lee la suma de 'fixed' de la ultima iteracion del ledger
run init --config uscha.config.json >/dev/null 2>&1
run log-step --repo repo-a --tool code-review --iteration 1 --fixed 3 --tests-passed true >/dev/null 2>&1
run regression-check --repo repo-a --diff fix-sin-test.diff --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
sys.exit(0 if d['fixed'] == 3 and d['verdict'] == 'NARRATED' else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   sin --fixed lee la ultima iteracion del ledger (fixed=3)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL lookup de fixed en el ledger"; }

echo "== T42 doctor: diagnostico de la instalacion (flutter-doctor spirit) =="
chk "doctor en sandbox con config -> exit 0 (avisos no fallan)" 0 run doctor
run doctor --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
sk = next(c for c in d['checks'] if c['title'].startswith('skills'))
ok = (d['errors'] == 0 and d['global_install'] is False
      and sk['level'] == 'ok'
      and any(c['title'].startswith('proyecto:') for c in d['checks'])
      and any(c['title'].startswith('ACCEPTANCE') and c['level'] == 'ok'
              for c in d['checks']))
sys.exit(0 if ok else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   doctor: full skill roster, install por proyecto, config y ACCEPTANCE leidos"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL doctor json"; }
# ledger corrupto = ERROR (no aviso): el doctor debe salir 1
"$PY" -c "open('QA-LEDGER.json','a',encoding='utf-8').write('{trunc')"
chk "doctor con ledger corrupto -> exit 1" 1 run doctor
run init --config uscha.config.json >/dev/null 2>&1

echo "== T43 rubric layer: agnostico — el grader.json se llena A MANO, sin LLM =="
cat > RUBRIC.md <<'EOF'
# RUBRIC — smoke
threshold: 0.80
## Criterios
- [ ] RB-01 (peso 3) — errores sanos
- [ ] RB-02 (peso 1) — convenciones del repo
## Criterios negativos
- [ ] RB-NEG-01 (peso 2) — comentarios que narran el cambio
EOF
chk "spec-check --rubric valida -> exit 0" 0 run spec-check --rubric RUBRIC.md
printf -- "# RUBRIC\n- [ ] RB-01 a\n- [ ] RB-1 b\n" > rub-dup.md
chk "IDs duplicados (RB-01 == RB-1) -> exit 1" 1 run spec-check --rubric rub-dup.md
printf -- "# RUBRIC\n- [ ] RB-01 a\n" > rub-nothr.md
chk "sin threshold -> exit 1" 1 run spec-check --rubric rub-nothr.md
# grade a mano: RB-01 pass con evidencia (3), RB-02 pass SIN evidencia (no puntua),
# negativo no aparece -> score 3/4 = 0.75 < 0.80 -> BELOW
cat > grader.json <<'EOF'
{ "criteria": [
  {"id": "RB-01", "verdict": "pass", "evidence": "src/x.py:42 — timeout+retry", "note": "ok"},
  {"id": "RB-02", "verdict": "pass", "evidence": "", "note": "sin cita"},
  {"id": "RB-NEG-01", "verdict": "pass", "evidence": "", "note": "no aparece"} ] }
EOF
chk "BELOW threshold sin gate declarado -> advisory exit 0" 0 \
  run rubric-ingest --repo repo-a --report grader.json --rubric RUBRIC.md
run rubric-ingest --repo repo-a --report grader.json --rubric RUBRIC.md --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
ok = (d['verdict'] == 'BELOW' and abs(d['score'] - 0.75) < 0.001
      and d['unsupported'] == ['RB-2'] and d['gated'] is False)
sys.exit(0 if ok else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   evidence-or-nothing: pass sin cita no puntua (0.75 < 0.80)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL contrato del grader"; }
run readiness 2>/dev/null | grep -q "rubrica repo-a" \
  && { PASS=$((PASS+1)); echo "  ok   readiness muestra el grade como advisory (no dimension)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL rubrica invisible en readiness"; }
# gate DECLARADO: below-threshold bloquea convergencia via ledger.
# Primero repo-a CONVERGE (ciclo limpio) — sin esto el check seria VACUO
# (converged ya sale 1 en un ledger virgen por 'no agent steps').
for t in code-review judgment-day improve; do
  run log-step --repo repo-a --tool $t --iteration 9 \
    --gated-reported 0 --files-changed 0 --tests-passed true >/dev/null 2>&1
done
chk "repo-a converge ANTES del gate (sanidad del fixture)" 0 run converged --repo repo-a
chk "BELOW con --gate -> exit 1" 1 \
  run rubric-ingest --repo repo-a --report grader.json --rubric RUBRIC.md --gate
chk "convergencia bloqueada por rubric:grade gateado" 1 run converged --repo repo-a
# threshold malformado ('0.8.0') = ausente, no traceback
printf -- "# RUBRIC\nthreshold: 0.8.0\n- [ ] RB-01 x\n" > rub-badthr.md
chk "threshold malformado -> exit 1 sin traceback" 1 run spec-check --rubric rub-badthr.md
# dos veredictos para el mismo criterio (RB-01 y RB-1) = contrato roto
printf -- '{ "criteria": [ {"id": "RB-01", "verdict": "pass", "evidence": "x:1", "note": ""}, {"id": "RB-1", "verdict": "fail", "evidence": "", "note": ""} ] }\n' > grader-dup.json
chk "IDs duplicados en el reporte -> exit 1 (un veredicto por criterio)" 1 \
  run rubric-ingest --repo repo-a --report grader-dup.json --rubric RUBRIC.md
# grade limpio (todo con evidencia, negativo sin matchear) -> PASS y limpia el gate
cat > grader-ok.json <<'EOF'
{ "criteria": [
  {"id": "RB-01", "verdict": "pass", "evidence": "src/x.py:42 — ok", "note": "ok"},
  {"id": "RB-02", "verdict": "pass", "evidence": "src/y.py:7 — snake_case", "note": "ok"},
  {"id": "RB-NEG-01", "verdict": "pass", "evidence": "", "note": "no aparece"} ] }
EOF
chk "grade limpio con --gate -> exit 0 (PASS)" 0 \
  run rubric-ingest --repo repo-a --report grader-ok.json --rubric RUBRIC.md --gate
chk "gate limpio libera la convergencia (latest-wins)" 0 run converged --repo repo-a
# ID inexistente = error de contrato
printf -- '{ "criteria": [ {"id": "RB-99", "verdict": "pass", "evidence": "x:1", "note": ""} ] }\n' > grader-bad.json
chk "ID inexistente en la rubrica -> exit 1" 1 \
  run rubric-ingest --repo repo-a --report grader-bad.json --rubric RUBRIC.md
# negativo CON evidencia resta peso: 4/4 - 2 = 2/4 = 0.5
cat > grader-neg.json <<'EOF'
{ "criteria": [
  {"id": "RB-01", "verdict": "pass", "evidence": "src/x.py:42 — ok", "note": "ok"},
  {"id": "RB-02", "verdict": "pass", "evidence": "src/y.py:7 — ok", "note": "ok"},
  {"id": "RB-NEG-01", "verdict": "fail", "evidence": "src/z.py:9 — 'now correctly...'", "note": "narra"} ] }
EOF
run rubric-ingest --repo repo-a --report grader-neg.json --rubric RUBRIC.md --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
sys.exit(0 if d['verdict'] == 'BELOW' and abs(d['score'] - 0.5) < 0.001 else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   negativo con evidencia resta peso (4-2)/4 = 0.50"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL semantica de negativos"; }

echo "== T45 anti-ceremonia (1.25.0): readiness = veredicto unico; --verbose expande; gates colapsados =="
printf '{ "defaults": { "acceptance_file": "ACCEPTANCE.md" },\n  "repos": [ {"name":"solo","path":"repo-c","type":"python"} ], "integration": {"enabled": false} }\n' > ac-cfg.json
run init --config ac-cfg.json --out L-ac.json >/dev/null
# default = 1 veredicto, SIN la tabla de rutina (dimensiones/by-repo son ceremonia)
run readiness --ledger L-ac.json 2>/dev/null | grep -q "^READINESS:" \
  && { PASS=$((PASS+1)); echo "  ok   default emite el veredicto (READINESS:)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL default no emite el veredicto"; }
run readiness --ledger L-ac.json 2>/dev/null | grep -q -- "--- dimensions" \
  && { FAIL=$((FAIL+1)); echo "  FAIL default filtra la tabla de dimensiones (ceremonia)"; } \
  || { PASS=$((PASS+1)); echo "  ok   default colapsa las dimensiones"; }
run readiness --ledger L-ac.json 2>/dev/null | grep -q -- "--- by repo" \
  && { FAIL=$((FAIL+1)); echo "  FAIL default filtra el by-repo (ceremonia)"; } \
  || { PASS=$((PASS+1)); echo "  ok   default colapsa el by-repo"; }
# --verbose expande el detalle
run readiness --ledger L-ac.json --verbose 2>/dev/null | grep -q -- "--- dimensions" \
  && { PASS=$((PASS+1)); echo "  ok   --verbose expande las dimensiones"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL --verbose no expande las dimensiones"; }
run readiness --ledger L-ac.json --verbose 2>/dev/null | grep -q -- "--- by repo" \
  && { PASS=$((PASS+1)); echo "  ok   --verbose expande el by-repo"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL --verbose no expande el by-repo"; }
# un gate BLOQUEANTE persistido aparece nombrado en la linea colapsada
run log-gate --repo solo --iteration 1 --kind simplicity --verdict fail --count 3 --ledger L-ac.json >/dev/null 2>&1
run readiness --ledger L-ac.json 2>/dev/null | grep -- "--- gates:" | grep -q "solo/gate:simplicity" \
  && { PASS=$((PASS+1)); echo "  ok   gate bloqueante colapsado y nombrado"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL gate bloqueante no nombrado en la linea de gates"; }
# gate limpio (latest-wins) -> la linea reporta ninguno bloqueando
run log-gate --repo solo --iteration 2 --kind simplicity --verdict pass --ledger L-ac.json >/dev/null 2>&1
run readiness --ledger L-ac.json 2>/dev/null | grep -- "--- gates:" | grep -q "ninguno bloqueando" \
  && { PASS=$((PASS+1)); echo "  ok   gate limpio libera la linea de gates (latest-wins)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL gate limpio no libera la linea de gates"; }
# --json expone gates[] (aditivo: presentacion sobre hechos, no recomputa el KPI)
run readiness --ledger L-ac.json --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
g = d.get('gates')
ok = (isinstance(g, list) and len(g) == 1 and g[0]['tool'] == 'gate:simplicity'
      and g[0]['blocking'] is False)
sys.exit(0 if ok else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   --json expone gates[] aditivo (latest limpio, blocking False)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL contrato gates[] en --json"; }

echo "== T46 REUSE-FIRST (1.26.0): waste-check Type-1/2 clon-vs-repo, advisory-first, determinista =="
mkdir -p wrepo/util
cat > wrepo/util/money.py <<'EOF'
def compute_total(items, rate):
    subtotal = sum(x.price for x in items)
    taxed = subtotal * (1 + rate)
    shipping = 5 if taxed < 100 else 0
    grand = round(taxed + shipping, 2)
    return grand
EOF
# LEAN: archivo nuevo, codigo unico (no clona nada del repo)
cat > lean.diff <<'EOF'
diff --git a/service/report.py b/service/report.py
new file mode 100644
--- /dev/null
+++ b/service/report.py
@@ -0,0 +1,6 @@
+def build_report(rows, header):
+    lines = [header.upper(), "----------"]
+    for entry in rows:
+        lines.append(entry.render_line())
+    joined = "\n".join(lines)
+    return joined
EOF
# CLON VS REPO: archivo nuevo que reimplementa wrepo/util/money.py exacto
cat > clone.diff <<'EOF'
diff --git a/service/checkout.py b/service/checkout.py
new file mode 100644
--- /dev/null
+++ b/service/checkout.py
@@ -0,0 +1,6 @@
+def compute_total(items, rate):
+    subtotal = sum(x.price for x in items)
+    taxed = subtotal * (1 + rate)
+    shipping = 5 if taxed < 100 else 0
+    grand = round(taxed + shipping, 2)
+    return grand
EOF
# CLON INTERNO: el mismo bloque repetido dentro del propio diff (no en el repo)
cat > internal.diff <<'EOF'
diff --git a/service/dup.py b/service/dup.py
new file mode 100644
--- /dev/null
+++ b/service/dup.py
@@ -0,0 +1,12 @@
+def parse_alpha(text, mode):
+    tokens = text.split(mode)
+    cleaned = [t.strip() for t in tokens]
+    filtered = [t for t in cleaned if t]
+    counted = len(filtered)
+    return counted, filtered
+def parse_beta(text, mode):
+    tokens = text.split(mode)
+    cleaned = [t.strip() for t in tokens]
+    filtered = [t for t in cleaned if t]
+    counted = len(filtered)
+    return counted, filtered
EOF
# CLON EN TEST: excluido (como simplicity) -> no cuenta
cat > clone-test.diff <<'EOF'
diff --git a/tests/test_checkout.py b/tests/test_checkout.py
new file mode 100644
--- /dev/null
+++ b/tests/test_checkout.py
@@ -0,0 +1,6 @@
+def compute_total(items, rate):
+    subtotal = sum(x.price for x in items)
+    taxed = subtotal * (1 + rate)
+    shipping = 5 if taxed < 100 else 0
+    grand = round(taxed + shipping, 2)
+    return grand
EOF
chk "lean.diff -> exit 0 (advisory)" 0 run waste-check --diff lean.diff --repo-root wrepo
run waste-check --diff lean.diff --repo-root wrepo --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
sys.exit(0 if d['verdict'] == 'LEAN' and d['metrics']['dup_windows_vs_repo'] == 0 else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   codigo unico -> LEAN, 0 clones vs repo"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL lean mal clasificado"; }
chk "clon vs repo -> exit 0 SIN gate (advisory-first)" 0 run waste-check --diff clone.diff --repo-root wrepo
run waste-check --diff clone.diff --repo-root wrepo --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
ok = (d['verdict'] == 'WASTEFUL' and d['metrics']['dup_windows_vs_repo'] >= 1
      and d['gate'] is False and any('money.py' in f for f in d['flags']))
sys.exit(0 if ok else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   clon vs repo -> WASTEFUL + flag nombra el original (money.py)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL clon vs repo no detectado"; }
chk "clon vs repo con --gate -> exit 1 (BLOCKER declarado)" 1 run waste-check --diff clone.diff --repo-root wrepo --gate
run waste-check --diff internal.diff --repo-root wrepo --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
sys.exit(0 if d['metrics']['dup_windows_internal'] >= 1 else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   clon interno detectado (dup_windows_internal >= 1)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL clon interno no detectado"; }
run waste-check --diff clone-test.diff --repo-root wrepo --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
sys.exit(0 if d['verdict'] == 'LEAN' and d['metrics']['dup_windows_vs_repo'] == 0 else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   clon en archivo de test EXCLUIDO (como simplicity)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL test no excluido del waste-check"; }
# SELF-MATCH: un diff que TOCA util/money.py y le agrega una copia de su PROPIO bloque
# no debe matchearse contra si mismo (el archivo tocado se excluye del escaneo del repo)
cat > selfmod.diff <<'EOF'
diff --git a/util/money.py b/util/money.py
--- a/util/money.py
+++ b/util/money.py
@@ -6,0 +7,6 @@
+def compute_total(items, rate):
+    subtotal = sum(x.price for x in items)
+    taxed = subtotal * (1 + rate)
+    shipping = 5 if taxed < 100 else 0
+    grand = round(taxed + shipping, 2)
+    return grand
EOF
run waste-check --diff selfmod.diff --repo-root wrepo --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
sys.exit(0 if d['metrics']['dup_windows_vs_repo'] == 0 else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   archivo tocado excluido del escaneo (no auto-match)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL self-match: el archivo tocado se comparo consigo mismo"; }
# determinismo: misma entrada -> mismo score (sin azar, sin red, sin LLM)
W1=$(run waste-check --diff clone.diff --repo-root wrepo --json 2>/dev/null | "$PY" -c "import json,sys;print(json.load(sys.stdin)['score'])")
W2=$(run waste-check --diff clone.diff --repo-root wrepo --json 2>/dev/null | "$PY" -c "import json,sys;print(json.load(sys.stdin)['score'])")
[ "$W1" = "$W2" ] && [ -n "$W1" ] \
  && { PASS=$((PASS+1)); echo "  ok   determinista (score $W1 estable)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL no determinista ($W1 vs $W2)"; }
# log-gate --kind waste persiste y entra al rollup de readiness (1.25.0)
run log-gate --repo solo --iteration 3 --kind waste --verdict fail --count 2 --ledger L-ac.json >/dev/null 2>&1
run readiness --ledger L-ac.json 2>/dev/null | grep -- "--- gates:" | grep -q "gate:waste" \
  && { PASS=$((PASS+1)); echo "  ok   gate:waste persistido aparece en el veredicto unico"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL gate:waste no entra al rollup de readiness"; }

echo "== T47 FTY (1.27.0): first-time yield pasivo en summary, informativo, no gatea =="
printf '{ "defaults": {"qa_tools_order":["code-review"]},\n  "repos": [ {"name":"fa","path":"repo-c","type":"python"},{"name":"fb","path":"repo-d","type":"python"} ], "integration": {"enabled": false} }\n' > fty-cfg.json
run init --config fty-cfg.json --out L-fty.json >/dev/null
# fa: limpio al ciclo 1 (first-time). fb: necesito 2 ciclos (no first-time).
run log-step --repo fa --tool code-review --iteration 1 --gated-reported 0 --tests-passed true --ledger L-fty.json >/dev/null 2>&1
run log-step --repo fb --tool code-review --iteration 1 --gated-reported 3 --tests-passed true --ledger L-fty.json >/dev/null 2>&1
run log-step --repo fb --tool code-review --iteration 2 --gated-reported 0 --tests-passed true --ledger L-fty.json >/dev/null 2>&1
run summary --ledger L-fty.json --json 2>/dev/null | "$PY" -c "
import json, sys
f = json.load(sys.stdin)['first_time_yield']
ok = (f['repos_through_qa'] == 2 and f['repos_first_time'] == 1 and f['pct'] == 50.0)
sys.exit(0 if ok else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   FTY 50% (fa limpio al 1er ciclo, fb necesito 2)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL FTY mal computado"; }
run summary --ledger L-fty.json 2>/dev/null | grep -q "first-time yield: 50.0%" \
  && { PASS=$((PASS+1)); echo "  ok   FTY visible en el texto del summary"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL FTY no aparece en summary"; }
# una escalacion (aunque el repo converja) lo saca del first-time yield
run escalate --repo fa --reason "design doubt" --ledger L-fty.json >/dev/null 2>&1
run summary --ledger L-fty.json --json 2>/dev/null | "$PY" -c "
import json, sys
f = json.load(sys.stdin)['first_time_yield']
sys.exit(0 if f['repos_first_time'] == 0 and f['pct'] == 0.0 else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   escalacion saca al repo del first-time yield"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL escalacion no afecta FTY"; }

echo "== T48 pit-check: mutation gate desde un mutations.xml (efectividad, no coverage) =="
cat > mutations.xml <<'EOF'
<mutations>
<mutation detected="true"  status="KILLED"><sourceFile>a.py</sourceFile></mutation>
<mutation detected="true"  status="KILLED"><sourceFile>a.py</sourceFile></mutation>
<mutation detected="true"  status="KILLED"><sourceFile>a.py</sourceFile></mutation>
<mutation detected="true"  status="SURVIVED"><sourceFile>a.py</sourceFile></mutation>
<mutation detected="false" status="SURVIVED"><sourceFile>b.py</sourceFile></mutation>
<mutation detected="false" status="NO_COVERAGE"><sourceFile>b.py</sourceFile></mutation>
<mutation detected="false" status="NON_VIABLE"><sourceFile>c.py</sourceFile></mutation>
<mutation detected="false" status="RUN_ERROR"><sourceFile>c.py</sourceFile></mutation>
</mutations>
EOF
# total = killed(4: 3 KILLED + 1 detected-override) + survived(1) + no_cov(1) = 6
# NON_VIABLE + RUN_ERROR excluidos del denominador -> excluded=2
# mutation_score = 100*4/6 = 66.7 ; test_strength = 100*4/(4+1) = 80.0
chk "score 66.7 >= min-score 60 -> PASS exit 0" 0 run pit-check --report mutations.xml --min-score 60
chk "score 66.7 < min-score 70 -> BELOW-GATE exit 1" 1 run pit-check --report mutations.xml --min-score 70
run pit-check --report mutations.xml --min-score 60 --json 2>/dev/null | "$PY" -c "
import json, sys
m = json.load(sys.stdin)['metrics']
ok = (m['total'] == 6 and m['killed'] == 4 and m['survived'] == 1
      and m['no_coverage'] == 1 and m['excluded'] == 2
      and abs(m['mutation_score'] - 66.7) < 0.05
      and abs(m['test_strength'] - 80.0) < 0.05)
sys.exit(0 if ok else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   NON_VIABLE/RUN_ERROR fuera del denominador; detected=true cuenta como killed"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL metricas del mutation report mal computadas"; }
chk "report inexistente -> exit 2 (no evidencia)" 2 run pit-check --report no-such.xml --min-score 60

echo "== T49 check-coverage: gate de umbral (OK / BELOW / sin report = fail-closed) =="
printf '{ "defaults": { "acceptance_file": "ACCEPTANCE.md" },\n  "repos": [ {"name":"cov","path":"covrepo","type":"python"}, {"name":"nocov","path":"nocovrepo","type":"python"} ], "integration": {"enabled": false} }\n' > cc-cfg.json
mkdir -p covrepo nocovrepo
# Cobertura: line-rate 0.85 -> 85% (lines-valid/lines-covered coherentes con line-rate)
cat > covrepo/coverage.xml <<'EOF'
<?xml version="1.0"?>
<coverage lines-valid="20" lines-covered="17" line-rate="0.85" version="7.4"></coverage>
EOF
run init --config cc-cfg.json --out L-cc.json >/dev/null
chk "coverage 85% >= threshold 60 -> OK exit 0" 0 run check-coverage --repo cov --threshold 60 --ledger L-cc.json
chk "coverage 85% < threshold 90 -> BELOW exit 1" 1 run check-coverage --repo cov --threshold 90 --ledger L-cc.json
chk "sin report de coverage -> fail-closed exit 1" 1 run check-coverage --repo nocov --threshold 60 --ledger L-cc.json

echo "== T50 rebuild: baseline escribe la firma; compare puntua COVERS / DIVERGE =="
mkdir -p rbrepo/src rbrepo/reports
cat > rbrepo/src/mod.py <<'EOF'
def add(a, b):
    return a + b
def mul(a, b):
    return a * b
EOF
cat > rbrepo/coverage.xml <<'EOF'
<?xml version="1.0"?>
<coverage lines-valid="10" lines-covered="8" line-rate="0.8" version="7.4"></coverage>
EOF
cat > rbrepo/reports/junit.xml <<'EOF'
<testsuites><testsuite name="S" tests="5" failures="0" errors="0" skipped="0"/></testsuites>
EOF
printf -- "# ACCEPTANCE\n\n- [x] uno\n- [x] dos\n" > ACCEPTANCE-rb.md
printf '{ "defaults": { "acceptance_file": "ACCEPTANCE-rb.md" },\n  "repos": [ {"name":"rb","path":"rbrepo","type":"python"} ], "integration": {"enabled": false} }\n' > rb-cfg.json
# baseline: escribe la firma
chk "baseline escribe REBUILD-BASELINE -> exit 0" 0 run rebuild --mode baseline --config rb-cfg.json --out RB.json
"$PY" -c "import json,sys; d=json.load(open('RB.json',encoding='utf-8')); sys.exit(0 if 'rb' in d['repos'] and d['repos']['rb']['tests']['total']==5 else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   la firma baseline capturo el repo (tests total=5)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL baseline no capturo la firma esperada"; }
# compare sobre el MISMO arbol -> todas las dimensiones 1.0 -> COVERS
chk "compare mismo arbol -> COVERS exit 0" 0 run rebuild --mode compare --baseline RB.json --json
run rebuild --mode compare --baseline RB.json --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
sys.exit(0 if d['verdict'] == 'COVERS' and d['dimensions']['tests'] == 1.0 else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   arbol sin cambios -> COVERS (tests dim 1.0)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL compare del mismo arbol no da COVERS"; }
# el arbol 'regenerado' rompe tests -> la dimension dominante cae -> NO COVERS + gap
cat > rbrepo/reports/junit.xml <<'EOF'
<testsuites><testsuite name="S" tests="5" failures="4" errors="0" skipped="0"/></testsuites>
EOF
chk "compare con tests que fallan -> exit 1 (no COVERS)" 1 run rebuild --mode compare --baseline RB.json --json
run rebuild --mode compare --baseline RB.json --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
ok = (d['verdict'] != 'COVERS' and d['dimensions']['tests'] < 0.5
      and any('fail' in g for g in d['gaps']))
sys.exit(0 if ok else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   tests rotos al regenerar -> DIVERGE/PARTIAL + gap reportado"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL compare no detecto la divergencia de tests"; }

echo "== T44 sync seis fuentes de version + changelog: VERSION/config/Claude/marketplace/package/Codex =="
"$PY" -c "
import json, sys, os, io
kit = os.path.dirname(os.path.dirname(os.path.dirname(sys.argv[1])))  # <kit>/.claude/skills/x -> <kit>
repo = os.path.dirname(kit)
v_file = io.open(os.path.join(kit, 'VERSION'), encoding='utf-8').read().split()[-1]
v_cfg = json.load(io.open(os.path.join(kit, 'uscha.config.json'), encoding='utf-8'))['version']
v_claude = json.load(io.open(os.path.join(kit, '.claude-plugin', 'plugin.json'), encoding='utf-8'))['version']
v_codex = json.load(io.open(os.path.join(kit, '.codex-plugin', 'plugin.json'), encoding='utf-8'))['version']
v_pkg = json.load(io.open(os.path.join(repo, 'package.json'), encoding='utf-8'))['version']
mk = json.load(io.open(os.path.join(repo, '.claude-plugin', 'marketplace.json'), encoding='utf-8'))
v_mkt = mk['plugins'][0]['version']
versions = [v_file, v_cfg, v_claude, v_mkt, v_pkg, v_codex]
changelog = os.path.join(kit, 'CHANGELOG-1.50.1.md')
print('  versiones:', *versions)
sys.exit(0 if len(set(versions)) == 1 and os.path.isfile(changelog) else 1)" "$(dirname "$QL")" \
  && { PASS=$((PASS+1)); echo "  ok   las seis fuentes coinciden y existe CHANGELOG-1.50.1.md"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL drift de version o falta CHANGELOG-1.50.1.md"; }
echo "== T51 freshness (1.31.0): reporte JUnit mas viejo que el codigo = STALE -> AC UNMEASURED =="
mkdir -p repo-fresh/reports
printf 'def alta():\n    return True\n' > repo-fresh/alta.py
cat > repo-fresh/reports/junit.xml <<'EOF'
<?xml version="1.0"?>
<testsuites><testsuite name="pytest" tests="1" failures="0" errors="0" skipped="0">
<testcase classname="tests.test_flow" name="test_ac1_alta_ok"/>
</testsuite></testsuites>
EOF
printf -- "# ACCEPTANCE\n\n- [x] AC-01 alta\n" > acc-fresh.md
printf '{ "defaults": { "acceptance_file": "acc-fresh.md" },\n  "repos": [ {"name":"fresh","path":"repo-fresh","type":"python"} ], "integration": {"enabled": false} }\n' > fresh.json
run init --config fresh.json --out L-fresh.json >/dev/null 2>&1
# FRESCO: reporte mas nuevo que la fuente -> AC-1 cierra medido, sin stale
touch -t 202601010800 repo-fresh/alta.py
touch -t 202601010900 repo-fresh/reports/junit.xml
run readiness --ledger L-fresh.json --json 2>/dev/null | "$PY" -c "
import json, sys
a = json.load(sys.stdin)['acceptance']
sys.exit(0 if a['measured_closed'] == ['AC-1'] and a['stale_reports'] == [] else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   reporte fresco: AC-1 cierra medido, stale_reports vacio"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL fresco no cierra o reporta stale de mas (falso positivo)"; }
# STALE: la fuente pasa a ser mas nueva que el reporte -> reporte descartado
touch -t 202601011200 repo-fresh/alta.py
run readiness --ledger L-fresh.json --json 2>/dev/null | "$PY" -c "
import json, sys
a = json.load(sys.stdin)['acceptance']
sys.exit(0 if a['measured_closed'] == [] and len(a['stale_reports']) == 1 else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   codigo mas nuevo: reporte STALE descartado, AC-1 UNMEASURED"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL stale no descartado (falso-verde por evidencia vieja)"; }
run readiness --ledger L-fresh.json 2>/dev/null | grep -q "STALE descartados" \
  && { PASS=$((PASS+1)); echo "  ok   advisory de reportes STALE visible en la vista default"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL sin advisory de STALE"; }

echo "== T52 gate de doc-version (1.31.0): READMEs (marcador uscha:version) = VERSION =="
"$PY" -c "
import sys, os, io, re
skdir = sys.argv[1]                                   # <kit>/.claude/skills/uscha-devloop
kit = os.path.dirname(os.path.dirname(os.path.dirname(skdir)))
repo = os.path.dirname(kit)
ver = io.open(os.path.join(kit, 'VERSION'), encoding='utf-8').read().split()[-1]
docs = [os.path.join(repo, 'README.md'), os.path.join(kit, 'README.md')]
rx = re.compile(r'v?(\d+\.\d+\.\d+)')
bad = []
for d in docs:
    marked = [l for l in io.open(d, encoding='utf-8') if 'uscha:version' in l]
    if not marked:
        bad.append(d + ': SIN marcador uscha:version'); continue
    m = rx.search(marked[0])
    got = m.group(1) if m else None
    if got != ver:
        bad.append(d + ': marcador dice ' + str(got) + ' != VERSION ' + ver)
print('  VERSION:', ver, '· READMEs marcados y en sync:', len(docs) - len(bad))
for b in bad: print('   ', b)
sys.exit(1 if bad else 0)" "$(dirname "$QL")" \
  && { PASS=$((PASS+1)); echo "  ok   los READMEs declaran la version actual (doc drift bloqueado)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL doc-version drift: un README no coincide con VERSION"; }

echo "== T53 dashboard (1.32.0): contrato mirador desde el ledger, truth-pass (null sin fuente) =="
mkdir -p repo-mir/reports docs/adr-mir
printf 'def a():\n    return 1\n' > repo-mir/x.py
printf -- "# ADR-001 Append-only\n\nStatus: accepted\n" > docs/adr-mir/ADR-001.md
printf -- "# ADR-002 Rollback\n\nStatus: proposed\n" > docs/adr-mir/ADR-002.md
printf -- "# ACCEPTANCE\n\n- [x] AC-01 alta\n" > acc-mir.md
printf '{ "defaults": { "acceptance_file": "acc-mir.md" },\n  "repos": [ {"name":"backend-api","path":"repo-mir","type":"python"} ], "integration": {"enabled": false} }\n' > mir.json
run init --config mir.json --out L-mir.json >/dev/null 2>&1
run dashboard --ledger L-mir.json --adr-dir docs/adr-mir --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
keys = ['project','generated','readiness','subscores','phases','acceptance','adrs','inv','capas','loops','snapshots','evidence']
assert all(k in d for k in keys), 'faltan claves: ' + str([k for k in keys if k not in d])
assert 'specs' not in d, 'specs (hardcodeado sin fuente) fue reemplazado por acceptance en 1.49.0'
assert isinstance(d['readiness']['score'], (int, float)), 'readiness.score'
assert isinstance(d['acceptance'].get('items'), list), 'acceptance.items lista'
assert d['capas'] == [], 'capas debe ser [] (truth-pass, sin fuente)'
assert len(d['adrs']) == 2 and d['adrs'][0]['status'] == 'done' and d['adrs'][1]['status'] == 'prog', 'adrs glob'
assert d['snapshots'] == [], 'snapshots vacio antes de --record'
assert len(d['phases']) == 8 and len(d['inv']) == 7, 'esqueleto phases(8)/inv(7)'
sys.exit(0)" \
  && { PASS=$((PASS+1)); echo "  ok   contrato completo; acceptance con items; capas []; adrs del glob; snapshots vacio pre-record"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL contrato dashboard mal formado"; }
DS=$(run dashboard --ledger L-mir.json --adr-dir docs/adr-mir --json 2>/dev/null | "$PY" -c "import json,sys;print(json.load(sys.stdin)['readiness']['score'])")
RS=$(run readiness --ledger L-mir.json --json 2>/dev/null | "$PY" -c "import json,sys;print(json.load(sys.stdin)['score'])")
[ "$DS" = "$RS" ] \
  && { PASS=$((PASS+1)); echo "  ok   readiness del dashboard == readiness --json ($DS, reuso verbatim sin drift)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL drift readiness dashboard($DS) vs readiness($RS)"; }
run readiness --ledger L-mir.json --record >/dev/null 2>&1
run dashboard --ledger L-mir.json --adr-dir docs/adr-mir --json 2>/dev/null | "$PY" -c "
import json, sys
s = json.load(sys.stdin)['snapshots']
sys.exit(0 if len(s) == 1 and isinstance(s[0]['readiness'], (int, float)) and 'date' in s[0] else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   readiness --record puebla el time-lapse (add-on prospectivo)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL time-lapse no se poblo tras --record"; }
# inv mapea el gate persistido por su kind REAL (pit-check, no 'pit'): sin este check
# un typo de kind deja el invariante en null en silencio (regresion muda).
run log-gate --ledger L-mir.json --repo backend-api --iteration 1 --kind pit-check --verdict fail --count 2 >/dev/null 2>&1
run log-gate --ledger L-mir.json --repo backend-api --iteration 1 --kind simplicity --verdict pass >/dev/null 2>&1
run dashboard --ledger L-mir.json --adr-dir docs/adr-mir --json 2>/dev/null | "$PY" -c "
import json, sys
inv = {i['name']: i['status'] for i in json.load(sys.stdin)['inv']}
sys.exit(0 if inv.get('Tests efectivos') == 'miss' and inv.get('Simplicidad') == 'ok' else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   inv mapea el gate por su kind real (pit-check->Tests efectivos miss, simplicity->ok)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL inv no mapea el gate persistido (kind mal escrito?)"; }

echo "== T54 telemetry-extract (1.33.0): transcript CC -> sidecar (vendor adapter, FUERA del engine) =="
EXTRACT="$(dirname "$(dirname "$QL")")/uscha-mirador/telemetry-extract.py"
mkdir -p tele
cat > tele/t.jsonl <<'EOF'
{"type":"assistant","timestamp":"2026-07-05T20:00:00Z","message":{"model":"claude-opus-4-8","usage":{"input_tokens":10000,"cache_read_input_tokens":40000,"output_tokens":3000}}}
{"type":"assistant","timestamp":"2026-07-05T20:10:00Z","message":{"model":"claude-haiku-4-5","usage":{"input_tokens":4000,"output_tokens":1500}}}
{bad json se saltea}
EOF
"$PY" "$EXTRACT" tele/t.jsonl --sidecar tele/telemetry.jsonl >/dev/null 2>&1
"$PY" -c "
import json, sys
d = json.loads(open('tele/telemetry.jsonl', encoding='utf-8').readline())
ok = (d['tokens_in'] == 54000 and d['tokens_out'] == 4500 and d['ms'] == 600000
      and len(d['by_model']) == 2
      and {m['model'] for m in d['by_model']} == {'claude-opus-4-8', 'claude-haiku-4-5'})
sys.exit(0 if ok else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   suma tokens (input+cache) + wall time + by_model desde el transcript"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL extractor no resume bien el transcript CC"; }
# upsert idempotente (1.34.0): re-correr con la misma sesion NO duplica la linea
"$PY" "$EXTRACT" tele/t.jsonl --sidecar tele/telemetry.jsonl >/dev/null 2>&1
"$PY" -c "
import sys
n = sum(1 for l in open('tele/telemetry.jsonl', encoding='utf-8') if l.strip())
sys.exit(0 if n == 1 else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   re-correr el extractor hace UPSERT (1 linea, no infla el total en watch)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL el extractor duplico la linea de sesion (watch-mode inflaria)"; }

echo "== T55 dashboard project (1.34.0): config.project gana; sin el, join de repos =="
printf '{ "project": "My Project", "defaults": { "acceptance_file": "acc-mir.md" },\n  "repos": [ {"name":"backend-api","path":"repo-mir","type":"python"} ], "integration": {"enabled": false} }\n' > mirp.json
run init --config mirp.json --out L-mirp.json >/dev/null 2>&1
run dashboard --ledger L-mirp.json --json 2>/dev/null | "$PY" -c "import json,sys; sys.exit(0 if json.load(sys.stdin)['project']=='My Project' else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   config.project -> dashboard.project"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL no toma project del config"; }
run dashboard --ledger L-mir.json --json 2>/dev/null | "$PY" -c "import json,sys; sys.exit(0 if json.load(sys.stdin)['project']=='backend-api' else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   sin project en config -> fallback al nombre del repo (truth-pass)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL fallback de project mal"; }

echo "== T56 mirador-render (1.34.0): dashboard + telemetria mergeada + inject + meta-refresh =="
RENDER="$(dirname "$(dirname "$QL")")/uscha-mirador/mirador-render.py"
TPL="$(dirname "$(dirname "$QL")")/uscha-mirador/mirador.template.html"
"$PY" "$RENDER" --engine "$QL" --ledger L-mirp.json --template "$TPL" --out mir-out.html --sidecar tele/telemetry.jsonl --refresh 30 --no-open >/dev/null 2>&1
"$PY" -c "
import re, json, sys
h = open('mir-out.html', encoding='utf-8').read()
m = re.search(r'const DATA = (\{.*\});\n/\*MIRADOR_DATA_END', h, re.S)
d = json.loads(m.group(1))
ok = (d['project'] == 'My Project' and 'telemetry' in d
      and d['telemetry']['tokens_in'] == 54000
      and 'http-equiv=\"refresh\" content=\"30\"' in h)
sys.exit(0 if ok else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   render standalone: project + telemetria + meta-refresh en mirador.html"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL mirador-render no produjo el HTML esperado"; }

echo "== T57 skill-count no-drift (1.34.0): USCHA_SKILLS del doctor == dirs uscha-* en disco =="
SKILLS_DIR="$(dirname "$(dirname "$QL")")"
"$PY" -c "
import sys, os
sys.path.insert(0, os.path.dirname(sys.argv[1]))
import qa_ledger as q
listed = set(q.USCHA_SKILLS)
ondisk = {d for d in os.listdir(sys.argv[2])
          if d.startswith('uscha-') and os.path.isdir(os.path.join(sys.argv[2], d))}
sys.exit(0 if listed == ondisk else 1)" "$QL" "$SKILLS_DIR" \
  && { PASS=$((PASS+1)); echo "  ok   el doctor lista exactamente las skills uscha-* en disco (sin drift)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL USCHA_SKILLS != dirs uscha-* en disco (skill nueva sin registrar en el doctor?)"; }

echo "== T58 execution-policy (1.35.0): routing por fase sin contaminar readiness =="
cat > ep.json <<'EOF'
{ "version": "1.35.0",
  "defaults": {
    "execution_policy": {
      "default": { "tier": "standard", "effort": "medium" },
      "phases": {
        "qa": { "method": "checker fresco", "tier": "checker", "model": "gpt-5.5", "effort": "high", "uncorrelated": true },
        "build": { "method": "implementar plan", "tier": "standard", "effort": "medium" }
      }
    }
  },
  "repos": [ {"name":"repo-c","path":"repo-c","type":"python"} ],
  "integration": {"enabled": false} }
EOF
run init --config ep.json --out L-ep.json >/dev/null 2>&1
run execution-policy --ledger L-ep.json --phase qa --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
ok = (d['phase'] == 'qa' and d['method'] == 'checker fresco'
      and d['tier'] == 'checker' and d['model'] == 'gpt-5.5'
      and d['effort'] == 'high' and d['uncorrelated'] is True)
sys.exit(0 if ok else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   CLI JSON devuelve metodologia/model/effort declarados para qa"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL execution-policy --json no respeta config.defaults.execution_policy"; }
run execution-policy --ledger L-ep.json --phase qa 2>/dev/null | grep -q "EXECUTION qa: checker fresco | tier=checker model=gpt-5.5 effort=high" \
  && { PASS=$((PASS+1)); echo "  ok   CLI humano emite una linea operable por fase"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL execution-policy no imprime la linea de fase esperada"; }
run dashboard --ledger L-ep.json --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
ph = {p['key']: p['execution'] for p in d['phases']}
ok = ('execution_policy' in d
      and d['execution_policy']['source'] == 'config.defaults.execution_policy'
      and ph['qa']['model'] == 'gpt-5.5' and ph['qa']['effort'] == 'high'
      and ph['build']['method'] == 'implementar plan'
      and isinstance(d['readiness']['score'], (int, float)))
sys.exit(0 if ok else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   dashboard expone execution_policy y anota phases sin ser score"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL dashboard no expone execution_policy por fase"; }

echo "== T59 mirador-render (1.35.0): bird's-eye muestra policy model/effort =="
"$PY" "$RENDER" --engine "$QL" --ledger L-ep.json --template "$TPL" --out ep-mir.html --no-open >/dev/null 2>&1
"$PY" -c "
import re, json, sys
h = open('ep-mir.html', encoding='utf-8').read()
m = re.search(r'const DATA = (\{.*\});\n/\*MIRADOR_DATA_END', h, re.S)
d = json.loads(m.group(1))
ok = ('id=\"exec\"' in h and 'Execution policy' in h
      and d['execution_policy']['phases']['qa']['model'] == 'gpt-5.5'
      and d['execution_policy']['phases']['qa']['effort'] == 'high')
sys.exit(0 if ok else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   mirador renderiza el panel y preserva model/effort en DATA"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL mirador no muestra execution_policy"; }

echo "== T60 discovery-intake (1.36.0): production finding reabre discovery =="
printf -- "# ACCEPTANCE\n\n- [ ] AC-01 checkout total correcto\n" > acc-intake.md
printf '{ "version": "1.36.0", "defaults": { "acceptance_file": "acc-intake.md" },\n  "repos": [ {"name":"repo-c","path":"repo-c","type":"python"} ], "integration": {"enabled": false} }\n' > intake.json
run init --config intake.json --out L-intake.json >/dev/null 2>&1
run production-finding --ledger L-intake.json --repo repo-c --severity HIGH --source sentry --title "checkout total wrong" --evidence "Sentry INC-1" 2>/dev/null | grep -q "PF-001" \
  && { PASS=$((PASS+1)); echo "  ok   production-finding crea PF-001 con evidencia de produccion"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL production-finding no crea PF-001"; }
run readiness --ledger L-intake.json --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
pf = d['discovery_intake']['production_findings']
ok = (len(pf) == 1 and pf[0]['id'] == 'PF-001' and pf[0]['severity'] == 'HIGH'
      and d['facts']['production_findings_open'] == 1)
sys.exit(0 if ok else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   readiness expone production findings como discovery_intake"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL readiness no expone production findings"; }
run readiness --ledger L-intake.json 2>/dev/null | grep -q "production findings open" \
  && { PASS=$((PASS+1)); echo "  ok   readiness default avisa que discovery debe reabrirse"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL readiness default no avisa production finding"; }
run production-finding --ledger L-intake.json --id PF-001 --resolve --note "fed into SPEC next cycle" >/dev/null 2>&1
run readiness --ledger L-intake.json --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
sys.exit(0 if d['discovery_intake']['production_findings'] == [] and d['facts']['production_findings_open'] == 0 else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   resolver PF-001 limpia el intake abierto"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL resolver PF-001 no limpia discovery_intake"; }

echo "== T61 spec-doubt (1.36.0): SPEC-WRONG bloquea atajos y exige humano =="
run spec-doubt --ledger L-intake.json --repo repo-c --kind spec-wrong --severity HIGH --note "AC dice sin impuesto, codigo real lo incluye" --evidence "demo con usuario" 2>/dev/null | grep -q "SD-001" \
  && { PASS=$((PASS+1)); echo "  ok   spec-doubt crea SD-001 como duda de SPEC"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL spec-doubt no crea SD-001"; }
run readiness --ledger L-intake.json --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
sd = d['discovery_intake']['spec_doubts']
ok = (len(sd) == 1 and sd[0]['id'] == 'SD-001' and sd[0]['kind'] == 'spec-wrong'
      and d['facts']['spec_doubts_open'] == 1)
sys.exit(0 if ok else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   readiness expone spec-doubt como discovery_intake"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL readiness no expone spec-doubt"; }
run phase --ledger L-intake.json --repo repo-c --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
sys.exit(0 if d['phase'] == 'escalated' and any('spec-doubt' in e for e in d['evidence']) else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   phase deriva escalated si hay spec-doubt abierto"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL phase ignora spec-doubt abierto"; }
run spec-doubt --ledger L-intake.json --id SD-001 --resolve --decision "SPEC amended" --note "acceptance updated" >/dev/null 2>&1
run readiness --ledger L-intake.json --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
sys.exit(0 if d['discovery_intake']['spec_doubts'] == [] and d['facts']['spec_doubts_open'] == 0 else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   resolver SD-001 limpia el intake abierto"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL resolver SD-001 no limpia discovery_intake"; }

echo "== T62 ADR experiments (1.37.0): hipotesis visible, advisory, no score =="
mkdir -p docs/adr
cat > docs/adr/ADR-001-checkout-path.md <<'EOF'
# ADR-001: Checkout path
## Status: Experiment
## Context
Tenemos dos caminos viables y la respuesta depende de feedback real.
## Decision
Probar el nuevo checkout para aprender con bajo blast radius.
## HIPÓTESIS
El checkout nuevo reduce abandonos sin subir errores.
## SEÑAL DE FEEDBACK
Conversion rate y errores de pago en produccion.
## Review By: 2099-01-01
## CRITERIOS DE PROMOCIÓN
Conversion estable o mejor y cero incidentes HIGH/BLOCKER.
## Rollback / Supersede Criteria
Suben errores de pago o aparece production-finding gateado.
## Implementation Plan
- Affected paths: checkout/*
## Verification
- [ ] Revisar senales de feedback.
EOF
cat > docs/adr/ADR-002-bad-experiment.md <<'EOF'
# ADR-002: Bad experiment
## Status: Experiment
## Context
Esto declara experimento pero no dice como se mide ni como se cierra.
## Hypothesis
Tal vez mejora.
## Review By: 2000-01-01
EOF
run dashboard --ledger L-intake.json --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
adrs = {a['id']: a for a in d['adrs']}
good = adrs['ADR-001']
bad = adrs['ADR-002']
summary = d['adr_experiments']
ok = (
  good['status'] == 'prog'
  and good['adr_status'] == 'experiment'
  and good['experiment_valid'] is True
  and good['review_by'] == '2099-01-01'
  and good['expired'] is False
  and bad['experiment_valid'] is False
  and bad['expired'] is True
  and 'feedback_signal' in bad['experiment_missing']
  and summary['open'] == 2
  and summary['malformed'] == 1
  and summary['expired'] == 1
  and isinstance(d['readiness']['score'], (int, float))
)
sys.exit(0 if ok else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   dashboard expone experiment ADR valido/malformado como advisory"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL dashboard no modela ADR experiment correctamente"; }
"$PY" "$RENDER" --engine "$QL" --ledger L-intake.json --template "$TPL" --out exp-mir.html >/dev/null 2>&1
"$PY" -c "
import re, json, sys
h = open('exp-mir.html', encoding='utf-8').read()
m = re.search(r'const DATA = (\{.*\});\n/\*MIRADOR_DATA_END', h, re.S)
d = json.loads(m.group(1))
ok = ('experiment' in h and 'ADR-001' in h
      and d['adr_experiments']['open'] == 2
      and d['adrs'][0]['adr_status'] == 'experiment')
sys.exit(0 if ok else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   mirador renderiza ADR experiment sin cambiar readiness"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL mirador no muestra ADR experiment"; }

echo "== T63 spec-change-request (1.38.0): evidence -> human-signed contract change =="
run spec-change-request --ledger L-intake.json --repo repo-c --source SD-001 --requested-change "AC-01 debe incluir impuesto" --evidence "demo + SD-001" --spec ACCEPTANCE.md 2>/dev/null | grep -q "SCR-001" \
  && { PASS=$((PASS+1)); echo "  ok   spec-change-request crea SCR-001 desde evidencia"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL spec-change-request no crea SCR-001"; }
run readiness --ledger L-intake.json --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
scr = d['discovery_intake']['spec_change_requests']
ok = (len(scr) == 1 and scr[0]['id'] == 'SCR-001' and scr[0]['source'] == 'SD-001'
      and d['facts']['spec_change_requests_open'] == 1)
sys.exit(0 if ok else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   readiness expone SCR abierto como puente contractual"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL readiness no expone SCR abierto"; }
run phase --ledger L-intake.json --repo repo-c --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
sys.exit(0 if d['phase'] == 'escalated' and any('SCR-001' in e for e in d['evidence']) else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   phase deriva escalated si hay SCR humano pendiente"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL phase ignora SCR abierto"; }
run spec-change-request --ledger L-intake.json --id SCR-001 --resolve --decision accepted --note "ACCEPTANCE amended" --amended ACCEPTANCE.md >/dev/null 2>&1
run readiness --ledger L-intake.json --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
sys.exit(0 if d['discovery_intake']['spec_change_requests'] == [] and d['facts']['spec_change_requests_open'] == 0 else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   resolver SCR-001 limpia el puente contractual abierto"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL resolver SCR-001 no limpia discovery_intake"; }

echo "== T64 golden labels (1.38.0): intended vs observed-accidental visible =="
mkdir -p gold
printf 'legacy bug preserved\n' > gold/qr.received.txt
cp gold/qr.received.txt gold/qr.approved.txt
cat > golden-labels.json <<'EOF'
{
  "fixtures": {
    "gold/qr.approved.txt": {
      "classification": "observed-accidental",
      "note": "legacy QR bug preserved for migration only"
    }
  }
}
EOF
run golden-diff --dir gold --labels golden-labels.json --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
labels = d['golden_labels']
ok = (d['verdict'] == 'CLEAN'
      and labels['observed_accidental'] == 1
      and labels['intended'] == 0
      and labels['unknown'] == 0
      and d['fixtures'][0]['classification'] == 'observed-accidental')
sys.exit(0 if ok else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   golden-diff clasifica golden observado-accidental sin debilitar el byte compare"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL golden-diff no expone labels intended/accidental"; }
run golden-diff --dir gold --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
sys.exit(0 if d['golden_labels']['unknown'] == 1 else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   golden sin labels queda unknown, no inventa intencion"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL golden-diff sin labels no queda unknown"; }

echo "== T65 calibration summary (1.38.0): post-merge facts calibran la retro =="
run summary --ledger L-intake.json --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
cal = d['post_merge_calibration']
ok = (cal['production_findings']['total'] == 1
      and cal['production_findings']['resolved'] == 1
      and cal['spec_doubts']['total'] == 1
      and cal['spec_doubts']['resolved'] == 1
      and cal['spec_change_requests']['total'] == 1
      and cal['spec_change_requests']['accepted'] == 1
      and cal['contract_reopen_signals'] == 3)
sys.exit(0 if ok else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   summary expone calibracion post-merge desde PF/SD/SCR"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL summary no expone calibracion post-merge"; }

echo "== T66 universal installer (1.41.0): Codex plugin + Claude adapter, dry-run safe =="
INST_HOME="$SB/home-installer"
mkdir -p "$INST_HOME"
"$PY" "$KIT/install-uscha.py" version --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
ok = (d['source_version'] == '1.50.1' and 'codex' in d['targets'] and 'claude' in d['targets'])
sys.exit(0 if ok else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   install-uscha version expone version fuente y targets"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL install-uscha version no expone targets/version"; }
"$PY" "$KIT/install-uscha.py" install --target both --home "$INST_HOME" --dry-run --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
ops = '\n'.join(o['path'].replace(chr(92), '/') for o in d['operations'])
ok = (d['dry_run'] is True and 'plugins/uscha' in ops and '.agents/plugins/marketplace.json' in ops and '.claude/skills/uscha-devloop' in ops)
sys.exit(0 if ok else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   dry-run planifica Codex plugin y Claude skills sin escribir"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL dry-run no muestra plan universal"; }
[ ! -e "$INST_HOME/.agents/plugins/uscha" ] && [ ! -e "$INST_HOME/.claude/skills/uscha-devloop" ] \
  && { PASS=$((PASS+1)); echo "  ok   dry-run no crea instalacion"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL dry-run escribio archivos"; }
"$PY" "$KIT/install-uscha.py" install --target codex --home "$INST_HOME" --json >/dev/null 2>&1
INST_HOME="$INST_HOME" "$PY" -c "
import json, os, pathlib, sys
h = pathlib.Path(os.environ['INST_HOME'])
manifest = h/'plugins/uscha/.codex-plugin/plugin.json'
market = h/'.agents/plugins/marketplace.json'
engine = h/'plugins/uscha/skills/uscha-devloop/qa_ledger.py'
marker = h/'plugins/uscha/uscha-install.json'
ok = (manifest.exists() and market.exists() and engine.exists() and
      json.load(open(manifest, encoding='utf-8'))['version'] == '1.50.1' and
      json.load(open(marker, encoding='utf-8'))['target'] == 'codex')
sys.exit(0 if ok else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   install codex crea plugin personal, marketplace y marker"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL install codex incompleto"; }
"$PY" "$KIT/install-uscha.py" doctor --target codex --home "$INST_HOME" --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
ok = (d['source_version'] == '1.50.1' and d['targets']['codex']['installed'] is True and d['targets']['codex']['version_match'] is True)
sys.exit(0 if ok else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   doctor detecta Codex instalado y version match"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL doctor no detecta install Codex"; }
diff -qr "$KIT/.claude/skills" "$KIT/skills" -x __pycache__ >/dev/null 2>&1 \
  && { PASS=$((PASS+1)); echo "  ok   Codex plugin skills mirror stays synced with canonical skills"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL uscha-kit/skills drifted from .claude/skills"; }


echo "== T67 npm router (1.41.0): npx package delegates to canonical installer =="
if command -v node >/dev/null 2>&1; then
  node "$ROOT/bin/uscha.js" version --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
ok = (d['source_version'] == '1.50.1' and 'codex' in d['targets'] and 'claude' in d['targets'])
sys.exit(0 if ok else 1)" \
    && { PASS=$((PASS+1)); echo "  ok   npm router expone version/targets desde install-uscha.py"; } \
    || { FAIL=$((FAIL+1)); echo "  FAIL npm router no delega correctamente al installer"; }
else
  FAIL=$((FAIL+1)); echo "  FAIL node no esta disponible para probar el router npm"
fi
if command -v npm >/dev/null 2>&1; then
  (cd "$ROOT" && npm_config_cache="$SB/npm-cache" npm pack --dry-run --json 2>/dev/null) | "$PY" -c "
import json, sys
d = json.load(sys.stdin)[0]
files = {f['path'] for f in d['files']}
ok = (d['name'] == '@andresmassello/uscha' and d['version'] == '1.50.1'
      and 'bin/uscha.js' in files and 'uscha-kit/install-uscha.py' in files
      and '.atl/skill-registry.md' not in files and 'handoff.md' not in files and 'mirador.html' not in files
      and not any('__pycache__' in f or f.endswith(('.pyc', '.pyo')) for f in files))
sys.exit(0 if ok else 1)" \
    && { PASS=$((PASS+1)); echo "  ok   npm pack dry-run incluye router/kit y excluye artefactos locales"; } \
    || { FAIL=$((FAIL+1)); echo "  FAIL npm pack dry-run no tiene el contenido esperado"; }
else
  FAIL=$((FAIL+1)); echo "  FAIL npm no esta disponible para probar package dry-run"
fi

echo "== T68 pr-ready exige evidencia de tests medida y verde =="
mkdir -p repo-pr-evidence
printf '{ "defaults": {"qa_tools_order":["code-review","judgment-day","improve"]},\n  "repos": [ {"name":"pr-evidence","path":"repo-pr-evidence","type":"python"} ], "integration": {"enabled": false} }\n' > c-pr-evidence.json
run init --config c-pr-evidence.json --out L-pr-evidence.json >/dev/null 2>&1
for t in code-review judgment-day improve; do
  run log-step --ledger L-pr-evidence.json --repo pr-evidence --tool "$t" \
    --iteration 1 --gated-reported 0 --files-changed 0 >/dev/null 2>&1
done
chk "QA narrada sin snapshot/reporte medido NO queda pr-ready" 1 \
  run phase --ledger L-pr-evidence.json --repo pr-evidence --require pr-ready
run phase --ledger L-pr-evidence.json --repo pr-evidence 2>/dev/null \
  | grep -q "falta evidencia medida de tests" \
  && { PASS=$((PASS+1)); echo "  ok   phase explains missing measured test evidence"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL phase does not explain missing measured test evidence"; }

echo "== T69 reportes malformados fallan cerrados =="
mkdir -p repo-pr-evidence/reports
cat > repo-pr-evidence/reports/ruff.json <<'EOF'
[{"code":"S101","filename":"app.py","location":{"row":1}}]
EOF
run ingest-gate --ledger L-pr-evidence.json --repo pr-evidence --iteration 2 \
  --ruff repo-pr-evidence/reports/ruff.json >/dev/null 2>&1
cp L-pr-evidence.json L-pr-evidence-before-invalid.json
printf '{malformed\n' > repo-pr-evidence/reports/ruff.json
chk "Ruff JSON malformado -> evidencia invalida exit 2" 2 \
  run ingest-gate --ledger L-pr-evidence.json --repo pr-evidence --iteration 3 \
    --ruff repo-pr-evidence/reports/ruff.json
cmp -s L-pr-evidence-before-invalid.json L-pr-evidence.json \
  && { PASS=$((PASS+1)); echo "  ok   Ruff invalido no reemplaza findings previos con estado limpio"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL invalid Ruff changed the ledger"; }
cp L-pr-evidence.json L-pr-evidence-before-schema-invalid.json
printf '[42]\n' > repo-pr-evidence/reports/ruff.json
chk "Ruff JSON schema-invalid -> invalid evidence exit 2" 2 \
  run ingest-gate --ledger L-pr-evidence.json --repo pr-evidence --iteration 4 \
    --ruff repo-pr-evidence/reports/ruff.json
cmp -s L-pr-evidence-before-schema-invalid.json L-pr-evidence.json \
  && { PASS=$((PASS+1)); echo "  ok   Ruff schema-invalid leaves ledger unchanged"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL Ruff schema-invalid changed the ledger"; }
cat > repo-pr-evidence/reports/ruff.json <<'EOF'
[{"code":"S101","filename":"app.py","location":"oops"}]
EOF
cp L-pr-evidence.json L-pr-evidence-before-nested-schema-invalid.json
chk "Ruff nested schema-invalid -> invalid evidence exit 2" 2 \
  run ingest-gate --ledger L-pr-evidence.json --repo pr-evidence --iteration 5 \
    --ruff repo-pr-evidence/reports/ruff.json
cmp -s L-pr-evidence-before-nested-schema-invalid.json L-pr-evidence.json \
  && { PASS=$((PASS+1)); echo "  ok   Ruff nested schema-invalid leaves ledger unchanged"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL Ruff nested schema-invalid changed the ledger"; }
for bad_ruff in \
  '[{"code":42,"filename":"app.py","location":{"row":1}}]' \
  '[{"code":"S101","filename":[],"location":{"row":1}}]' \
  '[{"code":"S101","filename":"app.py","location":{"row":"one"}}]'
do
  printf '%s\n' "$bad_ruff" > repo-pr-evidence/reports/ruff.json
  cp L-pr-evidence.json L-pr-evidence-before-invalid-ruff-field.json
  chk "Ruff invalid field type -> invalid evidence exit 2" 2 \
    run ingest-gate --ledger L-pr-evidence.json --repo pr-evidence --iteration 6 \
      --ruff repo-pr-evidence/reports/ruff.json
  cmp -s L-pr-evidence-before-invalid-ruff-field.json L-pr-evidence.json \
    && { PASS=$((PASS+1)); echo "  ok   Ruff invalid field leaves ledger unchanged"; } \
    || { FAIL=$((FAIL+1)); echo "  FAIL Ruff invalid field changed the ledger"; }
done
printf '<testsuite tests="1"' > repo-pr-evidence/reports/junit.xml
cp L-pr-evidence.json L-pr-evidence-before-invalid-junit.json
chk "JUnit XML malformado -> evidencia invalida exit 2" 2 \
  run snapshot --ledger L-pr-evidence.json --repo pr-evidence
cmp -s L-pr-evidence-before-invalid-junit.json L-pr-evidence.json \
  && { PASS=$((PASS+1)); echo "  ok   JUnit invalido no persiste snapshot falsamente limpio"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL invalid JUnit changed the ledger"; }
printf '<testsuites><foo/></testsuites>\n' > repo-pr-evidence/reports/junit.xml
cp L-pr-evidence.json L-pr-evidence-before-invalid-junit-structure.json
chk "JUnit structure-invalid -> invalid evidence exit 2" 2 \
  run snapshot --ledger L-pr-evidence.json --repo pr-evidence
cmp -s L-pr-evidence-before-invalid-junit-structure.json L-pr-evidence.json \
  && { PASS=$((PASS+1)); echo "  ok   JUnit structure-invalid leaves ledger unchanged"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL JUnit structure-invalid changed the ledger"; }

printf '<testsuite tests="1" failures="0" errors="0" skipped="-1"/>\n' \
  > repo-pr-evidence/reports/junit.xml
cp L-pr-evidence.json L-pr-evidence-before-invalid-junit-counters.json
chk "JUnit negative counters -> invalid evidence exit 2" 2 \
  run snapshot --ledger L-pr-evidence.json --repo pr-evidence
cmp -s L-pr-evidence-before-invalid-junit-counters.json L-pr-evidence.json \
  && { PASS=$((PASS+1)); echo "  ok   JUnit invalid counters leave ledger unchanged"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL JUnit invalid counters changed the ledger"; }

for bad_junit in \
  '<testsuite tests="1" failures="-1" errors="0" skipped="0"/>' \
  '<testsuite tests="1" failures="0" errors="-1" skipped="0"/>'
do
  printf '%s\n' "$bad_junit" > repo-pr-evidence/reports/junit.xml
  cp L-pr-evidence.json L-pr-evidence-before-negative-outcome.json
  chk "JUnit negative failure/error -> invalid evidence exit 2" 2 \
    run snapshot --ledger L-pr-evidence.json --repo pr-evidence
  cmp -s L-pr-evidence-before-negative-outcome.json L-pr-evidence.json \
    && { PASS=$((PASS+1)); echo "  ok   JUnit negative outcome leaves ledger unchanged"; } \
    || { FAIL=$((FAIL+1)); echo "  FAIL JUnit negative outcome changed the ledger"; }
done
printf '<testsuite tests="1" failures="0" errors="0" skipped="2"/>\n' \
  > repo-pr-evidence/reports/junit.xml
cp L-pr-evidence.json L-pr-evidence-before-excess-skipped.json
chk "JUnit skipped exceeds tests -> invalid evidence exit 2" 2 \
  run snapshot --ledger L-pr-evidence.json --repo pr-evidence
cmp -s L-pr-evidence-before-excess-skipped.json L-pr-evidence.json \
  && { PASS=$((PASS+1)); echo "  ok   JUnit excess skipped leaves ledger unchanged"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL JUnit excess skipped changed the ledger"; }

printf '<testsuite tests="2" failures="1" errors="1" skipped="1"/>\n' \
  > repo-pr-evidence/reports/junit.xml
cp L-pr-evidence.json L-pr-evidence-before-impossible-outcomes.json
chk "JUnit outcomes exceed executed tests -> invalid evidence exit 2" 2 \
  run snapshot --ledger L-pr-evidence.json --repo pr-evidence
cmp -s L-pr-evidence-before-impossible-outcomes.json L-pr-evidence.json \
  && { PASS=$((PASS+1)); echo "  ok   JUnit impossible outcomes leave ledger unchanged"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL JUnit impossible outcomes changed the ledger"; }

printf '<testsuites tests="1" failures="1"><testsuite tests="1" errors="1"/></testsuites>\n' > repo-pr-evidence/reports/junit.xml
cp L-pr-evidence.json L-pr-evidence-before-inconsistent-root.json
chk "JUnit root/child counters inconsistent -> invalid evidence exit 2" 2 run snapshot --ledger L-pr-evidence.json --repo pr-evidence
cmp -s L-pr-evidence-before-inconsistent-root.json L-pr-evidence.json \
  && { PASS=$((PASS+1)); echo "  ok   JUnit inconsistent root leaves ledger unchanged"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL JUnit inconsistent root changed the ledger"; }
chk "invalid JUnit cannot lead to pr-ready" 1 run phase --ledger L-pr-evidence.json --repo pr-evidence --require pr-ready

echo "== T69b (1.41.1): well-formed JUnit that LIES (failures=0 attr + real <failure>) reads RED =="
"$PY" -c "
import sys, os, tempfile
sys.path.insert(0, os.path.dirname(sys.argv[1]))
import qa_ledger as q
def cnt(xml):
    d = tempfile.mkdtemp(); os.makedirs(os.path.join(d, 'reports'))
    open(os.path.join(d, 'reports', 'junit.xml'), 'w').write(xml)
    return q.junit_test_count(d)
lie = cnt('<testsuite tests=\"2\" failures=\"0\" errors=\"0\" skipped=\"0\"><testcase name=\"t1\"/><testcase name=\"t2\"><failure message=\"x\"/></testcase></testsuite>')
err = cnt('<testsuite tests=\"1\" failures=\"0\" errors=\"0\" skipped=\"0\"><testcase name=\"t\"><error message=\"x\"/></testcase></testsuite>')
adapter = cnt('<testsuites><testsuite name=\"pytest\" tests=\"5\" failures=\"0\" errors=\"0\" skipped=\"1\"/></testsuites>')
legit = cnt('<testsuites><testsuite name=\"pytest\" tests=\"3\" failures=\"1\" errors=\"0\" skipped=\"0\"><testcase name=\"a\"/><testcase name=\"b\"><failure/></testcase><testcase name=\"c\"/></testsuite></testsuites>')
ok = (lie['failures'] == 1 and err['errors'] == 1
      and adapter['total'] == 5 and adapter['failures'] == 0
      and legit['failures'] == 1)
sys.exit(0 if ok else 1)" "$QL" \
  && { PASS=$((PASS+1)); echo "  ok   <failure>/<error> elements override a lying summary attribute; adapter/legit reports intact"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL lying JUnit still reads green (element reconciliation broken)"; }

echo "== T69c (1.41.1): integration readiness does NOT trust the last event (green test cannot mask a failing gate) =="
mkdir -p ri/reports
printf '{ "defaults": { "acceptance_file": "acc-ri.md" }, "repos": [ {"name":"backend-api","path":"ri","type":"python"} ], "integration": {"enabled": true, "contract_tests_command": "x"} }\n' > ri.json
printf -- "# A\n\n- [x] AC-01 x\n" > acc-ri.md
run init --config ri.json --out L-ri.json >/dev/null 2>&1
run log-step --ledger L-ri.json --repo integration --tool e2e-gate --iteration 1 --reported 3 --gated-reported 3 --tests-passed false >/dev/null 2>&1
run log-step --ledger L-ri.json --repo integration --tool e2e-tests --iteration 2 --reported 0 --gated-reported 0 --tests-passed true >/dev/null 2>&1
run readiness --ledger L-ri.json --json 2>/dev/null | "$PY" -c "import json,sys; sys.exit(0 if json.load(sys.stdin)['dimensions'].get('integration',{}).get('raw')==0.0 else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   a failing integration gate is not masked by a trailing green test (dim=0.0)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL integration still trusts the last event (masking not closed)"; }
run log-step --ledger L-ri.json --repo integration --tool e2e-gate --iteration 3 --reported 3 --gated-reported 0 >/dev/null 2>&1
run readiness --ledger L-ri.json --json 2>/dev/null | "$PY" -c "import json,sys; sys.exit(0 if json.load(sys.stdin)['dimensions'].get('integration',{}).get('raw')==1.0 else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   clearing the same-tool gate restores integration to green (no false negative)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL a fixed integration gate is not seen"; }

echo "== T70 static-gate silence does not invent clean evidence =="
PHASE_NO_STATIC=$(run phase --ledger L-fsm.json --repo fsm --require pr-ready 2>&1)
PHASE_NO_STATIC_RC=$?
if [ "$PHASE_NO_STATIC_RC" -eq 0 ]; then
  PASS=$((PASS+1)); echo "  ok   measured green tests can reach pr-ready without static reports"
else
  FAIL=$((FAIL+1)); echo "  FAIL phase did not reach pr-ready without static reports ($PHASE_NO_STATIC)"
fi
if echo "$PHASE_NO_STATIC" | grep -q "static gates"; then
  FAIL=$((FAIL+1)); echo "  FAIL phase invented a clean static-gate claim"
else
  PASS=$((PASS+1)); echo "  ok   qa_tools_order covers agents; static silence is not evidence"
fi

echo "== T71 pr-ready requires at least one executed test =="
mkdir -p repo-zero-tests/reports
cat > repo-zero-tests/reports/junit.xml <<'EOF'
<testsuite tests="0" failures="0" errors="0" skipped="0"/>
EOF
printf '{ "defaults": {"qa_tools_order":["code-review"]},\n  "repos": [ {"name":"zero-tests","path":"repo-zero-tests","type":"python"} ], "integration": {"enabled": false} }\n' > c-zero-tests.json
run init --config c-zero-tests.json --out L-zero-tests.json >/dev/null 2>&1
run snapshot --ledger L-zero-tests.json --repo zero-tests >/dev/null 2>&1
run log-step --ledger L-zero-tests.json --repo zero-tests --tool code-review \
  --iteration 1 --gated-reported 0 --files-changed 0 >/dev/null 2>&1
chk "zero executed tests cannot satisfy pr-ready" 1 \
  run phase --ledger L-zero-tests.json --repo zero-tests --require pr-ready

echo "== T72 installer safety =="
SAFE_HOME="$SB/home-installer-safe"; SAFE_REPO="$SB/repo-installer-safe"
mkdir -p "$SAFE_HOME" "$SAFE_REPO"
printf 'keep-existing\n' > "$SAFE_REPO/CLAUDE.md"
chk "init conflict exits nonzero" 1 "$PY" "$KIT/install-uscha.py" init --repo "$SAFE_REPO" --json
grep -q '^keep-existing$' "$SAFE_REPO/CLAUDE.md" && { PASS=$((PASS+1)); echo "  ok   init preserves conflict"; } || { FAIL=$((FAIL+1)); echo "  FAIL init replaced conflict"; }
chk "init dry-run detects conflict" 1 "$PY" "$KIT/install-uscha.py" init --repo "$SAFE_REPO" --dry-run --json
chk "init --force replaces conflict" 0 "$PY" "$KIT/install-uscha.py" init --repo "$SAFE_REPO" --force --json
mkdir -p "$SAFE_HOME/plugins/uscha" "$SAFE_HOME/.agents/plugins"
printf 'preserve-plugin\n' > "$SAFE_HOME/plugins/uscha/sentinel.txt"
printf '{ malformed\n' > "$SAFE_HOME/.agents/plugins/marketplace.json"
chk "dry-run rejects malformed marketplace" 1 "$PY" "$KIT/install-uscha.py" install --target codex --home "$SAFE_HOME" --dry-run --json
test -f "$SAFE_HOME/plugins/uscha/sentinel.txt" && { PASS=$((PASS+1)); echo "  ok   malformed preflight preserves plugin"; } || { FAIL=$((FAIL+1)); echo "  FAIL malformed preflight changed plugin"; }
cat > "$SAFE_HOME/.agents/plugins/marketplace.json" <<'EOF'
{"name":"personal","interface":{"displayName":"Personal"},"plugins":[{"name":"other"}]}
EOF
chk "install rejects structurally invalid marketplace" 1 "$PY" "$KIT/install-uscha.py" install --target codex --home "$SAFE_HOME" --json
test -f "$SAFE_HOME/plugins/uscha/sentinel.txt" && { PASS=$((PASS+1)); echo "  ok   structural preflight preserves plugin"; } || { FAIL=$((FAIL+1)); echo "  FAIL structural preflight changed plugin"; }
rm -f "$SAFE_HOME/.agents/plugins/marketplace.json"
chk "healthy Codex install" 0 "$PY" "$KIT/install-uscha.py" install --target codex --home "$SAFE_HOME" --json
chk "healthy Codex doctor" 0 "$PY" "$KIT/install-uscha.py" doctor --target codex --home "$SAFE_HOME" --json
EMPTY_HOME="$SB/home-installer-unhealthy"; mkdir -p "$EMPTY_HOME"
chk "unhealthy doctor text exits 1" 1 "$PY" "$KIT/install-uscha.py" doctor --target codex --home "$EMPTY_HOME"
chk "unhealthy doctor JSON exits 1" 1 "$PY" "$KIT/install-uscha.py" doctor --target codex --home "$EMPTY_HOME" --json
CLAUDE_HOME="$SB/home-installer-claude"; mkdir -p "$CLAUDE_HOME/.claude"
printf '{"theme":"dark","hooks":{"PostToolUse":[{"matcher":"*","hooks":[]}]}}\n' > "$CLAUDE_HOME/.claude/settings.json"
chk "Claude install activates hook" 0 "$PY" "$KIT/install-uscha.py" install --target claude --home "$CLAUDE_HOME" --json
chk "Claude reinstall is idempotent" 0 "$PY" "$KIT/install-uscha.py" install --target claude --home "$CLAUDE_HOME" --json
CLAUDE_HOME="$CLAUDE_HOME" "$PY" -c "import json,os,pathlib,sys; d=json.load(open(pathlib.Path(os.environ['CLAUDE_HOME'])/'.claude/settings.json',encoding='utf-8')); p=d.get('hooks',{}).get('PreToolUse',[]); c=[h.get('command','') for r in p for h in r.get('hooks',[])]; sys.exit(0 if d.get('theme')=='dark' and 'PostToolUse' in d.get('hooks',{}) and sum('block-approved-writes.py' in x for x in c)==1 else 1)" && { PASS=$((PASS+1)); echo "  ok   settings preserved; hook registered once"; } || { FAIL=$((FAIL+1)); echo "  FAIL Claude hook merge"; }
chk "healthy Claude doctor" 0 "$PY" "$KIT/install-uscha.py" doctor --target claude --home "$CLAUDE_HOME" --json
echo "== T73 mutation-safe input validation =="
mkdir -p repo-valid repo-other repo-valid/reports
printf '<testsuite tests="1" failures="0" errors="0" skipped="0"/>\n' > repo-valid/reports/junit.xml
cat > c-validation.json <<'EOF'
{"defaults":{"coverage_threshold":60,"max_iterations":5,"tools_per_cycle":3,"qa_tools_order":["code-review"]},"repos":[{"name":"valid","path":"repo-valid","type":"python"},{"name":"other","path":"repo-other","type":"node"}],"integration":{"enabled":false}}
EOF
run init --config c-validation.json --out L-validation.json >/dev/null 2>&1

reject_unchanged() {
  local desc="$1" ledger="$2"; shift 2
  cp "$ledger" "$ledger.before"
  "$@" >/dev/null 2>&1; local got=$?
  if [ "$got" -ne 0 ] && cmp -s "$ledger.before" "$ledger"; then
    PASS=$((PASS+1)); echo "  ok   $desc"
  else
    FAIL=$((FAIL+1)); echo "  FAIL $desc (exit=$got or ledger changed)"
  fi
}

reject_unchanged "escalate rejects unknown repo and preserves bytes" L-validation.json \
  run escalate --ledger L-validation.json --repo missing --reason "invalid target"
run production-finding --ledger L-validation.json --repo valid --title "prod" --evidence "log:1" >/dev/null
reject_unchanged "PF resolve requires nonempty note and preserves bytes" L-validation.json \
  run production-finding --ledger L-validation.json --id PF-001 --resolve --note "   "
chk "PF resolve accepts disposition note" 0 run production-finding --ledger L-validation.json --id PF-001 --resolve --note "triaged into fix"

run spec-doubt --ledger L-validation.json --repo valid --note "contract mismatch" >/dev/null
reject_unchanged "SD resolve requires nonempty decision and preserves bytes" L-validation.json \
  run spec-doubt --ledger L-validation.json --id SD-001 --resolve --decision "   "
chk "SD resolve accepts decision" 0 run spec-doubt --ledger L-validation.json --id SD-001 --resolve --decision "SPEC amended"

run production-finding --ledger L-validation.json --repo valid --title "source" --evidence "log:2" >/dev/null
run spec-doubt --ledger L-validation.json --repo other --note "other repo doubt" >/dev/null
reject_unchanged "SCR rejects arbitrary source ID and preserves bytes" L-validation.json \
  run spec-change-request --ledger L-validation.json --repo valid --source BUG-9 --requested-change "change" --evidence "log:3"
reject_unchanged "SCR rejects missing PF source and preserves bytes" L-validation.json \
  run spec-change-request --ledger L-validation.json --repo valid --source PF-999 --requested-change "change" --evidence "log:3"
reject_unchanged "SCR rejects cross-repo SD source and preserves bytes" L-validation.json \
  run spec-change-request --ledger L-validation.json --repo valid --source SD-002 --requested-change "change" --evidence "log:3"
chk "SCR accepts same-repo PF source" 0 run spec-change-request --ledger L-validation.json --repo valid --source PF-002 --requested-change "change" --evidence "log:3"
for bad_args in "--decision accepted" "--decision rejected" "--decision superseded" "--decision rejected --note '   '"; do
  cp L-validation.json L-validation-before-scr.json
  eval "run spec-change-request --ledger L-validation.json --id SCR-001 --resolve $bad_args" >/dev/null 2>&1; rc=$?
  if [ "$rc" -ne 0 ] && cmp -s L-validation-before-scr.json L-validation.json; then
    PASS=$((PASS+1)); echo "  ok   invalid SCR closure rejected without mutation: $bad_args"
  else
    FAIL=$((FAIL+1)); echo "  FAIL invalid SCR closure mutated ledger: $bad_args"
  fi
done
reject_unchanged "SCR resolve requires decision and preserves bytes" L-validation.json \
  run spec-change-request --ledger L-validation.json --id SCR-001 --resolve
chk "SCR accepted requires amended artifact" 0 run spec-change-request --ledger L-validation.json --id SCR-001 --resolve --decision accepted --amended SPEC.md

run spec-change-request --ledger L-validation.json --repo valid --source PF-002 --requested-change "reject" --evidence "log:4" >/dev/null
chk "SCR rejected accepts rationale" 0 run spec-change-request --ledger L-validation.json --id SCR-002 --resolve --decision rejected --note "not aligned"
run spec-change-request --ledger L-validation.json --repo valid --source PF-002 --requested-change "replace" --evidence "log:5" >/dev/null
chk "SCR superseded accepts replacement reference" 0 run spec-change-request --ledger L-validation.json --id SCR-003 --resolve --decision superseded --amended SPEC-v2.md

echo "== T73b P1 ledger integrity: readiness config and one-shot closures =="
"$PY" "$KIT/tests/ledger-integrity-regressions.py" "$QL" >/dev/null 2>&1 \
  && { PASS=$((PASS+1)); echo "  ok   P1 ledger integrity regressions"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL P1 ledger integrity regressions"; }

check_bad_config() {
  local desc="$1" json="$2"
  printf '%s\n' "$json" > c-bad-validation.json
  rm -f L-bad-validation.json
  run init --config c-bad-validation.json --out L-bad-validation.json >/dev/null 2>&1; local got=$?
  if [ "$got" -ne 0 ] && [ ! -e L-bad-validation.json ]; then
    PASS=$((PASS+1)); echo "  ok   $desc"
  else
    FAIL=$((FAIL+1)); echo "  FAIL $desc (exit=$got or output created)"
  fi
}
check_bad_config "repos must be a list" '{"repos":{}}'
check_bad_config "repo entries must be objects" '{"repos":["x"]}'
check_bad_config "repo names must be nonempty" '{"repos":[{"name":" ","path":"x","type":"python"}]}'
check_bad_config "repo names must be unique" '{"repos":[{"name":"x","path":"a","type":"python"},{"name":"x","path":"b","type":"node"}]}'
check_bad_config "integration is a reserved repo name" '{"repos":[{"name":"integration","path":"x","type":"python"}]}'
check_bad_config "repo paths must be nonempty" '{"repos":[{"name":"x","path":" ","type":"python"}]}'
check_bad_config "repo types must be supported" '{"repos":[{"name":"x","path":"x","type":"ruby"}]}'
check_bad_config "qa_tools_order must be nonempty" '{"defaults":{"qa_tools_order":[]},"repos":[]}'
check_bad_config "qa_tools_order entries must be strings" '{"defaults":{"qa_tools_order":[1]},"repos":[]}'
check_bad_config "qa_tools_order entries must be unique and nonempty" '{"defaults":{"qa_tools_order":["x","x"]},"repos":[]}'
check_bad_config "qa_tools_order entries cannot be blank" '{"defaults":{"qa_tools_order":[" "]},"repos":[]}'
for supported_type in maven flutter python node go rust dotnet cpp gradle swift; do
  printf '{"repos":[{"name":"x","path":"x","type":"%s"}]}\n' "$supported_type" > c-supported.json
  chk "supported repo type: $supported_type" 0 run init --config c-supported.json --out L-supported.json
done
check_bad_config "coverage threshold cannot be negative" '{"defaults":{"coverage_threshold":-1},"repos":[]}'
check_bad_config "coverage threshold cannot exceed 100" '{"defaults":{"coverage_threshold":101},"repos":[]}'
check_bad_config "max_iterations must be positive" '{"defaults":{"max_iterations":0},"repos":[]}'
check_bad_config "tools_per_cycle must be positive" '{"defaults":{"tools_per_cycle":0},"repos":[]}'

for cmd in \
  "log-step --repo valid --tool code-review --iteration 0" \
  "ingest-gate --repo valid --iteration 0 --ruff repo-valid/reports/ruff.json" \
  "log-gate --repo valid --iteration 0 --kind regression --verdict pass" \
  "flag-blocker --repo valid --iteration 0 --note breach" \
  "rubric-ingest --repo valid --iteration 0 --report missing.json"
do
  cp L-validation.json L-validation-before-iteration.json
  eval "run $cmd --ledger L-validation.json" >/dev/null 2>&1; rc=$?
  if [ "$rc" -ne 0 ] && cmp -s L-validation-before-iteration.json L-validation.json; then
    PASS=$((PASS+1)); echo "  ok   iteration <1 rejected without mutation: $cmd"
  else
    FAIL=$((FAIL+1)); echo "  FAIL iteration <1 changed ledger: $cmd"
  fi
done

printf '[{"code":"E501","filename":"x.py","location":{"row":1}}]\n' > repo-valid/reports/ruff.json
chk "newer ingest-gate state accepted" 0 run ingest-gate --ledger L-validation.json --repo valid --iteration 3 --ruff repo-valid/reports/ruff.json
reject_unchanged "older ingest-gate iteration cannot supersede newer state" L-validation.json \
  run ingest-gate --ledger L-validation.json --repo valid --iteration 2 --ruff repo-valid/reports/ruff.json
chk "newer blocker state accepted" 0 run flag-blocker --ledger L-validation.json --repo valid --kind t73 --iteration 3 --note breach
reject_unchanged "older blocker iteration cannot supersede newer state" L-validation.json \
  run flag-blocker --ledger L-validation.json --repo valid --kind t73 --iteration 2 --note older
cat > T73-RUBRIC.md <<'EOF'
# T73 rubric
threshold: 0.50
- [ ] RB-01 (peso 1) - evidence
EOF
cat > t73-grader.json <<'EOF'
{"criteria":[{"id":"RB-01","verdict":"pass","evidence":"x.py:1","note":"ok"}]}
EOF
chk "newer rubric state accepted" 0 run rubric-ingest --ledger L-validation.json --repo valid --iteration 3 --rubric T73-RUBRIC.md --report t73-grader.json
reject_unchanged "older rubric iteration cannot supersede newer state" L-validation.json \
  run rubric-ingest --ledger L-validation.json --repo valid --iteration 2 --rubric T73-RUBRIC.md --report t73-grader.json

for bad_counts in "--reported -1" "--gated-reported -1" "--fixed -1" "--deferred -1" \
  "--suppressed -1" "--files-changed -1" "--reported 1 --gated-reported 2"
do
  cp L-validation.json L-validation-before-counts.json
  eval "run log-step --ledger L-validation.json --repo valid --tool code-review --iteration 1 $bad_counts" >/dev/null 2>&1; rc=$?
  if [ "$rc" -ne 0 ] && cmp -s L-validation-before-counts.json L-validation.json; then
    PASS=$((PASS+1)); echo "  ok   invalid log-step counters rejected: $bad_counts"
  else
    FAIL=$((FAIL+1)); echo "  FAIL invalid log-step counters changed ledger: $bad_counts"
  fi
done
reject_unchanged "negative FACT-gate count rejected without mutation" L-validation.json \
  run log-gate --ledger L-validation.json --repo valid --iteration 1 --kind regression --verdict fail --count -1
chk "log-step allows fixed above reported" 0 run log-step --ledger L-validation.json --repo valid --tool code-review --iteration 2 --reported 1 --fixed 2
reject_unchanged "older log-step iteration cannot supersede newer state" L-validation.json \
  run log-step --ledger L-validation.json --repo valid --tool code-review --iteration 1
chk "same-cycle retry remains valid" 0 run log-step --ledger L-validation.json --repo valid --tool code-review --iteration 2
chk "newer FACT-gate state accepted" 0 run log-gate --ledger L-validation.json --repo valid --iteration 3 --kind regression --verdict fail --count 1
reject_unchanged "older FACT-gate iteration cannot supersede newer state" L-validation.json \
  run log-gate --ledger L-validation.json --repo valid --iteration 2 --kind regression --verdict pass
cat > c-integration-readiness.json <<'EOF'
{"defaults":{"qa_tools_order":["code-review"]},"repos":[],"integration":{"enabled":true}}
EOF
run init --config c-integration-readiness.json --out L-integration-readiness.json >/dev/null
run log-step --ledger L-integration-readiness.json --repo integration --tool integration-tests \
  --iteration 1 --tests-passed false >/dev/null
run log-gate --ledger L-integration-readiness.json --repo integration --iteration 1 \
  --kind gate-check --verdict pass >/dev/null
run readiness --ledger L-integration-readiness.json --json | "$PY" -c \
  "import json,sys; sys.exit(0 if json.load(sys.stdin)['dimensions']['integration']['raw'] == 0 else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   integration failure survives later non-test event"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL integration failure hidden by later non-test event"; }
run log-step --ledger L-integration-readiness.json --repo integration --tool integration-tests \
  --iteration 2 --tests-passed true >/dev/null
run readiness --ledger L-integration-readiness.json --json | "$PY" -c \
  "import json,sys; sys.exit(0 if json.load(sys.stdin)['dimensions']['integration']['raw'] == 1 else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   newer measured integration success recovers readiness"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL newer measured integration success did not recover readiness"; }
echo "== T74 npm router: probes Python before one installer invocation =="
if command -v node >/dev/null 2>&1; then
  ROUTER_BIN="$SB/router-bin"; ROUTER_LOG="$SB/router.log"
  ROUTER_FIXTURE_READY=1
  mkdir -p "$ROUTER_BIN"
  if [ "$(node -p 'process.platform')" = "win32" ]; then
    cat > "$ROUTER_BIN/fake-python.cs" <<'EOF'
using System;
using System.Diagnostics;
using System.IO;
class FakePython {
  static int Main(string[] args) {
    string role = Path.GetFileNameWithoutExtension(Process.GetCurrentProcess().MainModule.FileName).ToLowerInvariant();
    File.AppendAllText(Environment.GetEnvironmentVariable("USCHA_TEST_LOG"), role + " " + string.Join(" ", args) + "\r\n");
    if (Array.IndexOf(args, "--version") >= 0) {
      if (role == "python") return 1;
      Console.WriteLine("Python 3.8.0");
      return 0;
    }
    return role == "python" ? 9 : 0;
  }
}
EOF
    CSHARP_ROOT="${WINDIR:-C:/Windows}"
    command -v cygpath >/dev/null 2>&1 || ROUTER_FIXTURE_READY=0
    if [ "$ROUTER_FIXTURE_READY" -eq 1 ] && printf '%s' "$CSHARP_ROOT" | grep -Eq '^[A-Za-z]:'; then CSHARP_ROOT="$(cygpath -u "$CSHARP_ROOT")"; fi
    CSHARP_COMPILER="$CSHARP_ROOT/Microsoft.NET/Framework64/v4.0.30319/csc.exe"
    [ -x "$CSHARP_COMPILER" ] || CSHARP_COMPILER="$CSHARP_ROOT/Microsoft.NET/Framework/v4.0.30319/csc.exe"
    [ -x "$CSHARP_COMPILER" ] || ROUTER_FIXTURE_READY=0
    if [ "$ROUTER_FIXTURE_READY" -eq 1 ]; then
      CSHARP_OUTPUT="$(cygpath -w "$ROUTER_BIN/python.exe")"
      CSHARP_SOURCE="$(cygpath -w "$ROUTER_BIN/fake-python.cs")"
      MSYS_NO_PATHCONV=1 "$CSHARP_COMPILER" /nologo "/out:$CSHARP_OUTPUT" "$CSHARP_SOURCE" >/dev/null 2>&1 \
        && cp "$ROUTER_BIN/python.exe" "$ROUTER_BIN/py.exe" \
        || ROUTER_FIXTURE_READY=0
    fi
    ROUTER_PRIMARY="python"; ROUTER_FALLBACK="py -3"
  else
    cat > "$ROUTER_BIN/python3" <<'EOF'
#!/usr/bin/env sh
printf 'python3 %s\n' "$*" >> "$USCHA_TEST_LOG"
[ "$1" = "--version" ] && exit 1
exit 9
EOF
    cat > "$ROUTER_BIN/python" <<'EOF'
#!/usr/bin/env sh
printf 'python %s\n' "$*" >> "$USCHA_TEST_LOG"
if [ "$1" = "--version" ]; then echo "Python 3.8.0"; exit 0; fi
exit 0
EOF
    chmod +x "$ROUTER_BIN/python3" "$ROUTER_BIN/python"
    ROUTER_PRIMARY="python3"; ROUTER_FALLBACK="python"
  fi
  if [ "$ROUTER_FIXTURE_READY" -eq 1 ]; then
    PATH="$ROUTER_BIN:$PATH" USCHA_TEST_LOG="$ROUTER_LOG" node "$ROOT/bin/uscha.js" version >/dev/null 2>&1; ROUTER_RC=$?
  else
    ROUTER_RC=99
  fi
  if [ "$ROUTER_FIXTURE_READY" -eq 1 ] && [ "$ROUTER_RC" -eq 0 ] && grep -Fxq "$ROUTER_PRIMARY --version" "$ROUTER_LOG" \
    && grep -Fxq "$ROUTER_FALLBACK --version" "$ROUTER_LOG" \
    && [ "$(grep -F "$ROUTER_FALLBACK " "$ROUTER_LOG" | grep -c 'install-uscha.py version')" -eq 1 ] \
    && [ "$(grep -F "$ROUTER_PRIMARY " "$ROUTER_LOG" | grep -c 'install-uscha.py version')" -eq 0 ] \
    && [ "$(grep -c 'install-uscha.py version' "$ROUTER_LOG")" -eq 1 ]; then
    PASS=$((PASS+1)); echo "  ok   unusable first Python falls through to verified fallback once"
  else
    FAIL=$((FAIL+1)); echo "  FAIL router did not probe/fallback exactly once"
  fi
else
  FAIL=$((FAIL+1)); echo "  FAIL node no esta disponible para probar fallback del router npm"
fi
echo "== T75 npm router: installer failure is not retried =="
if command -v node >/dev/null 2>&1; then
  ROUTER_BIN="$SB/router-failure-bin"; ROUTER_LOG="$SB/router-failure.log"
  ROUTER_FIXTURE_READY=1
  mkdir -p "$ROUTER_BIN"
  if [ "$(node -p 'process.platform')" = "win32" ]; then
    cat > "$ROUTER_BIN/fake-python.cs" <<'EOF'
using System;
using System.Diagnostics;
using System.IO;
class FakePython {
  static int Main(string[] args) {
    string role = Path.GetFileNameWithoutExtension(Process.GetCurrentProcess().MainModule.FileName).ToLowerInvariant();
    File.AppendAllText(Environment.GetEnvironmentVariable("USCHA_TEST_LOG"), role + " " + string.Join(" ", args) + "\r\n");
    if (Array.IndexOf(args, "--version") >= 0) { Console.WriteLine("Python 3.8.0"); return 0; }
    return role == "python" ? 23 : 0;
  }
}
EOF
    CSHARP_ROOT="${WINDIR:-C:/Windows}"
    command -v cygpath >/dev/null 2>&1 || ROUTER_FIXTURE_READY=0
    if [ "$ROUTER_FIXTURE_READY" -eq 1 ] && printf '%s' "$CSHARP_ROOT" | grep -Eq '^[A-Za-z]:'; then CSHARP_ROOT="$(cygpath -u "$CSHARP_ROOT")"; fi
    CSHARP_COMPILER="$CSHARP_ROOT/Microsoft.NET/Framework64/v4.0.30319/csc.exe"
    [ -x "$CSHARP_COMPILER" ] || CSHARP_COMPILER="$CSHARP_ROOT/Microsoft.NET/Framework/v4.0.30319/csc.exe"
    [ -x "$CSHARP_COMPILER" ] || ROUTER_FIXTURE_READY=0
    if [ "$ROUTER_FIXTURE_READY" -eq 1 ]; then
      CSHARP_OUTPUT="$(cygpath -w "$ROUTER_BIN/python.exe")"
      CSHARP_SOURCE="$(cygpath -w "$ROUTER_BIN/fake-python.cs")"
      MSYS_NO_PATHCONV=1 "$CSHARP_COMPILER" /nologo "/out:$CSHARP_OUTPUT" "$CSHARP_SOURCE" >/dev/null 2>&1 \
        && cp "$ROUTER_BIN/python.exe" "$ROUTER_BIN/py.exe" \
        || ROUTER_FIXTURE_READY=0
    fi
    ROUTER_PRIMARY="python"; ROUTER_FALLBACK="py -3"
  else
    cat > "$ROUTER_BIN/python3" <<'EOF'
#!/usr/bin/env sh
printf 'python3 %s\n' "$*" >> "$USCHA_TEST_LOG"
if [ "$1" = "--version" ]; then echo "Python 3.8.0"; exit 0; fi
exit 23
EOF
    cat > "$ROUTER_BIN/python" <<'EOF'
#!/usr/bin/env sh
printf 'python %s\n' "$*" >> "$USCHA_TEST_LOG"
if [ "$1" = "--version" ]; then echo "Python 3.8.0"; exit 0; fi
exit 0
EOF
    chmod +x "$ROUTER_BIN/python3" "$ROUTER_BIN/python"
    ROUTER_PRIMARY="python3"; ROUTER_FALLBACK="python"
  fi
  if [ "$ROUTER_FIXTURE_READY" -eq 1 ]; then
    PATH="$ROUTER_BIN:$PATH" USCHA_TEST_LOG="$ROUTER_LOG" node "$ROOT/bin/uscha.js" version >/dev/null 2>&1; ROUTER_RC=$?
  else
    ROUTER_RC=99
  fi
  # "without another interpreter" = the installer ran EXACTLY ONCE, by the primary, and no
  # fallback retried it. Counting total install invocations captures that intent directly and
  # is platform-robust; the old `! grep -Fq "$ROUTER_FALLBACK"` matched a substring and broke
  # on POSIX, where the fallback "python" is a prefix of the primary "python3" (found by CI).
  if [ "$ROUTER_FIXTURE_READY" -eq 1 ] && [ "$ROUTER_RC" -eq 23 ] && grep -Fxq "$ROUTER_PRIMARY --version" "$ROUTER_LOG" \
    && [ "$(grep -F "$ROUTER_PRIMARY " "$ROUTER_LOG" | grep -c 'install-uscha.py version')" -eq 1 ] \
    && [ "$(grep -c 'install-uscha.py version' "$ROUTER_LOG")" -eq 1 ]; then
    PASS=$((PASS+1)); echo "  ok   installer exit 23 is preserved without another interpreter"
  else
    FAIL=$((FAIL+1)); echo "  FAIL router retried or changed installer failure status"
  fi
else
  FAIL=$((FAIL+1)); echo "  FAIL node no esta disponible para probar failure del router npm"
fi
echo "== T76 workbench doctor: usable Python fallback and source skill roster =="
DOCTOR_BIN="$SB/doctor-bin"; DOCTOR_HOME="$SB/doctor-home"
mkdir -p "$DOCTOR_BIN" "$DOCTOR_HOME/.claude/skills"
cat > "$DOCTOR_BIN/python3" <<'EOF'
#!/usr/bin/env sh
echo "Python 2.7.18"
EOF
if case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) true;; *) false;; esac; then
  cat > "$DOCTOR_BIN/python" <<'EOF'
#!/usr/bin/env sh
echo "Python 2.7.18"
EOF
  cat > "$DOCTOR_BIN/py" <<'EOF'
#!/usr/bin/env sh
if [ "$#" -eq 2 ] && [ "$1" = "-3" ] && [ "$2" = "--version" ]; then
  echo "Python 3.11.9"
  exit 0
fi
exit 1
EOF
  chmod +x "$DOCTOR_BIN/python" "$DOCTOR_BIN/py"
else
  cat > "$DOCTOR_BIN/python" <<'EOF'
#!/usr/bin/env sh
echo "Python 3.11.9"
EOF
  chmod +x "$DOCTOR_BIN/python"
fi
chmod +x "$DOCTOR_BIN/python3"
DOCTOR_SKILL_COUNT=0
for source_skill in "$KIT/.claude/skills"/uscha-*; do
  [ -d "$source_skill" ] || continue
  skill_name="$(basename "$source_skill")"
  mkdir -p "$DOCTOR_HOME/.claude/skills/$skill_name"
  : > "$DOCTOR_HOME/.claude/skills/$skill_name/SKILL.md"
  DOCTOR_SKILL_COUNT=$((DOCTOR_SKILL_COUNT+1))
done
DOCTOR_OUT="$(HOME="$DOCTOR_HOME" PATH="$DOCTOR_BIN:$PATH" bash "$KIT/workbench-doctor.sh")"
DOCTOR_SKILLS_OK=1
for source_skill in "$KIT/.claude/skills"/uscha-*; do
  [ -d "$source_skill" ] || continue
  skill_name="$(basename "$source_skill")"
  printf '%s\n' "$DOCTOR_OUT" | grep -Fq "$skill_name" || DOCTOR_SKILLS_OK=0
done
if [ "$DOCTOR_SKILL_COUNT" -gt 0 ] && [ "$DOCTOR_SKILLS_OK" -eq 1 ] \
  && printf '%s\n' "$DOCTOR_OUT" | grep -Fq "Python 3.8+" \
  && printf '%s\n' "$DOCTOR_OUT" | grep -Fq "Python 3.11.9" \
  && ! printf '%s\n' "$DOCTOR_OUT" | grep -Fq "Python 2.7.18"; then
  PASS=$((PASS+1)); echo "  ok   doctor uses Python >=3.8 fallback and current uscha-* skill roster"
else
  FAIL=$((FAIL+1)); echo "  FAIL doctor did not use source roster or usable Python fallback"
fi

echo "== T77 Claude install rolls back the complete managed target on a late failure =="
ROLLBACK_HOME="$SB/home-installer-claude-rollback"
ROLLBACK_ROOT="$ROLLBACK_HOME/.claude"
ROLLBACK_FAULT="$SB/claude-rollback-fault"
mkdir -p "$ROLLBACK_ROOT/skills/unrelated-skill" "$ROLLBACK_ROOT/hooks" "$ROLLBACK_FAULT"
for source_skill in "$KIT/.claude/skills"/uscha-*; do
  [ -d "$source_skill" ] || continue
  skill_name="$(basename "$source_skill")"
  mkdir -p "$ROLLBACK_ROOT/skills/$skill_name"
  printf 'previous-%s\n' "$skill_name" > "$ROLLBACK_ROOT/skills/$skill_name/sentinel.bin"
done
printf 'unrelated-skill\n' > "$ROLLBACK_ROOT/skills/unrelated-skill/sentinel.bin"
printf 'previous-hook\n' > "$ROLLBACK_ROOT/hooks/block-approved-writes.py"
printf 'unrelated-file\n' > "$ROLLBACK_ROOT/unrelated.bin"
printf '{"theme":"sentinel","permissions":{"allow":["Read"]},"hooks":{"PostToolUse":[{"matcher":"*","hooks":[]}]}}\n' > "$ROLLBACK_ROOT/settings.json"
printf 'previous-marker\n' > "$ROLLBACK_ROOT/uscha-install.json"
cat > "$ROLLBACK_FAULT/sitecustomize.py" <<'PY'
import os

_replace = os.replace
_failed = False


def fail_at_claude_marker(source, target):
    global _failed
    normalized = os.path.normcase(os.path.normpath(os.fspath(target)))
    marker_suffix = os.path.normcase(os.path.normpath(os.path.join(".claude", "uscha-install.json")))
    if not _failed and normalized.endswith(marker_suffix):
        _failed = True
        root = os.path.dirname(normalized)
        replaced = os.path.isfile(os.path.join(root, "skills", "uscha-discovery", "SKILL.md"))
        old_gone = not os.path.exists(os.path.join(root, "skills", "uscha-discovery", "sentinel.bin"))
        with open(os.environ["USCHA_FAULT_WITNESS"], "w", encoding="utf-8", newline="\n") as handle:
            handle.write("late\n" if replaced and old_gone else "too-early\n")
        raise OSError("deterministic late Claude marker failure")
    return _replace(source, target)


os.replace = fail_at_claude_marker
PY
cat > "$ROLLBACK_FAULT/snapshot.py" <<'PY'
import base64
import json
import os
import pathlib
import stat
import sys

root = pathlib.Path(sys.argv[1])
snapshot = []
for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
    relative = path.relative_to(root).as_posix()
    info = path.lstat()
    if path.is_symlink():
        snapshot.append([relative, "symlink", os.readlink(path)])
    elif path.is_dir():
        snapshot.append([relative, "dir", stat.S_IMODE(info.st_mode)])
    else:
        snapshot.append([relative, "file", stat.S_IMODE(info.st_mode),
                         base64.b64encode(path.read_bytes()).decode("ascii")])
json.dump(snapshot, sys.stdout, separators=(",", ":"))
sys.stdout.write("\n")
PY
"$PY" "$ROLLBACK_FAULT/snapshot.py" "$ROLLBACK_HOME" > "$ROLLBACK_FAULT/before.json"
PYTHONPATH="$ROLLBACK_FAULT" USCHA_FAULT_WITNESS="$ROLLBACK_FAULT/witness.txt" \
  "$PY" "$KIT/install-uscha.py" install --target claude --home "$ROLLBACK_HOME" --json \
  > "$ROLLBACK_FAULT/stdout.txt" 2> "$ROLLBACK_FAULT/stderr.txt"
ROLLBACK_RC=$?
"$PY" "$ROLLBACK_FAULT/snapshot.py" "$ROLLBACK_HOME" > "$ROLLBACK_FAULT/after.json"
if [ "$ROLLBACK_RC" -ne 0 ] \
  && grep -Fxq 'late' "$ROLLBACK_FAULT/witness.txt" \
  && cmp -s "$ROLLBACK_FAULT/before.json" "$ROLLBACK_FAULT/after.json"; then
  PASS=$((PASS+1)); echo "  ok   late Claude failure restores the full managed tree and unrelated state"
else
  FAIL=$((FAIL+1)); echo "  FAIL late Claude failure left a partial install or changed unrelated state"
fi

rm -f "$ROLLBACK_ROOT/uscha-install.json" "$ROLLBACK_FAULT/witness.txt"
"$PY" "$ROLLBACK_FAULT/snapshot.py" "$ROLLBACK_HOME" > "$ROLLBACK_FAULT/before-no-marker.json"
PYTHONPATH="$ROLLBACK_FAULT" USCHA_FAULT_WITNESS="$ROLLBACK_FAULT/witness.txt" \
  "$PY" "$KIT/install-uscha.py" install --target claude --home "$ROLLBACK_HOME" --json \
  > "$ROLLBACK_FAULT/stdout-no-marker.txt" 2> "$ROLLBACK_FAULT/stderr-no-marker.txt"
ROLLBACK_NO_MARKER_RC=$?
"$PY" "$ROLLBACK_FAULT/snapshot.py" "$ROLLBACK_HOME" > "$ROLLBACK_FAULT/after-no-marker.json"
if [ "$ROLLBACK_NO_MARKER_RC" -ne 0 ] \
  && grep -Fxq 'late' "$ROLLBACK_FAULT/witness.txt" \
  && [ ! -e "$ROLLBACK_ROOT/uscha-install.json" ] \
  && cmp -s "$ROLLBACK_FAULT/before-no-marker.json" "$ROLLBACK_FAULT/after-no-marker.json"; then
  PASS=$((PASS+1)); echo "  ok   late Claude failure does not leave a newly created marker"
else
  FAIL=$((FAIL+1)); echo "  FAIL late Claude failure left a marker that did not exist before"
fi

echo "== T77b (1.41.1): Codex install rollback restores the pre-existing plugin (data-loss fix) =="
"$PY" - "$KIT/install-uscha.py" <<'PY'
import importlib.util, os, sys, shutil, tempfile, pathlib
spec = importlib.util.spec_from_file_location("iu", sys.argv[1])
iu = importlib.util.module_from_spec(spec); spec.loader.exec_module(iu)
home = pathlib.Path(tempfile.mkdtemp())
try:
    plugin = home / "plugins" / iu.PLUGIN_NAME
    plugin.mkdir(parents=True)
    (plugin / "SENTINEL.txt").write_text("ORIGINAL")
    real = os.replace
    def failing(src, dst, *a, **k):
        # only the stage->plugin swap fails (e.g. a Windows AV lock on the fresh stage
        # tree); the backup->plugin restore must still succeed
        if pathlib.Path(dst) == plugin and "staging" in str(src):
            raise PermissionError("simulated stage-swap failure")
        return real(src, dst, *a, **k)
    iu.os.replace = failing
    raised = False
    try:
        iu.install_codex(home, "copy", False, [])
    except BaseException:
        raised = True
    finally:
        iu.os.replace = real
    s = plugin / "SENTINEL.txt"
    ok = (raised and s.exists() and s.read_text() == "ORIGINAL"
          and not list((home / "plugins").glob(".*backup*")))
    sys.exit(0 if ok else 1)
finally:
    shutil.rmtree(home, ignore_errors=True)
PY
if [ $? -eq 0 ]; then PASS=$((PASS+1)); echo "  ok   a failed Codex swap restores the user's pre-existing plugin (no data loss)"; \
else FAIL=$((FAIL+1)); echo "  FAIL Codex rollback lost or stranded the pre-existing plugin"; fi

echo "== T78 (1.41.2): NOT READY title is score-aware -- never says 'no arranca' once started =="
# isolated subdir: dashboard scans the CWD for ADRs/specs, so run away from the shared sandbox
mkdir -p title-sb && ( cd title-sb
  printf -- "# ACCEPTANCE\n\n- [ ] uno\n- [ ] dos\n" > title-acc.md
  printf '{ "defaults": { "acceptance_file": "title-acc.md" },\n  "repos": [ {"name":"solo","path":"r","type":"python"} ], "integration": {"enabled": false} }\n' > title-cfg.json
  run init --config title-cfg.json --out L-title-a.json >/dev/null 2>&1
  # A: virgin ledger -> score 0 -> "sin evidencia medida", NOT "no arranca"
  run dashboard --ledger L-title-a.json --json 2>/dev/null | "$PY" -c "
import json, sys
r = json.load(sys.stdin)['readiness']
t = r['title'] or ''
sys.exit(0 if (r['band'] == 'NOT READY' and (r['score'] or 0) == 0
               and 'arranca' not in t and 'sin evidencia' in t) else 1)" \
    && { PASS=$((PASS+1)); echo "  ok   score 0 -> 'sin evidencia medida' (no 'no arranca')"; } \
    || { FAIL=$((FAIL+1)); echo "  FAIL titulo virgen incorrecto"; }
  # B: one passing gate -> score >0 but still NOT READY -> "en construccion", never "no arranca"
  cp L-title-a.json L-title-b.json
  run log-gate --repo solo --iteration 1 --kind simplicity --verdict pass --ledger L-title-b.json >/dev/null 2>&1
  run dashboard --ledger L-title-b.json --json 2>/dev/null | "$PY" -c "
import json, sys
r = json.load(sys.stdin)['readiness']
t = r['title'] or ''
sys.exit(0 if (r['band'] == 'NOT READY' and 0 < (r['score'] or 0) < 50
               and 'arranca' not in t and 'construccion' in t) else 1)" \
    && { PASS=$((PASS+1)); echo "  ok   score >0 NOT READY -> 'en construccion' (no 'no arranca')"; } \
    || { FAIL=$((FAIL+1)); echo "  FAIL titulo iniciado incorrecto"; }
  echo "$PASS $FAIL" > title-counts.txt )
read PASS FAIL < title-sb/title-counts.txt

echo "== T79 (1.41.3): --refresh (live) never auto-opens -- one open tab self-reloads, no tab spam =="
"$PY" - "$KIT/.claude/skills/uscha-mirador/mirador-render.py" "$KIT/.claude/skills/uscha-mirador/mirador.template.html" <<'PY'
import importlib.util, os, pathlib, shutil, sys, tempfile
render_path, tpl = sys.argv[1], sys.argv[2]
spec = importlib.util.spec_from_file_location("mr", render_path)
mr = importlib.util.module_from_spec(spec); spec.loader.exec_module(mr)
tmp = pathlib.Path(tempfile.mkdtemp())
eng = tmp / "eng.py"
eng.write_text('import sys; sys.stdout.write(\'{"readiness":{"score":22,"band":"NOT READY","title":"x"}}\')\n', encoding="utf-8")
opens = {"n": 0}
mr._open_best_effort = lambda p: opens.__setitem__("n", opens["n"] + 1)  # count instead of launching a browser
def run(extra):
    sys.argv = ["mirador-render.py", "--engine", str(eng), "--ledger", str(tmp / "L.json"),
                "--template", tpl, "--out", str(tmp / "m.html"), "--sidecar", str(tmp / "none.jsonl")] + extra
    return mr.main()
b = opens["n"]; run(["--refresh", "30"]); live = opens["n"] - b        # live view -> 0 (page self-reloads)
b = opens["n"]; run([]); oneshot = opens["n"] - b                       # one-shot -> 1 (open once)
b = opens["n"]; run(["--no-open"]); noopen = opens["n"] - b             # explicit suppress -> 0
shutil.rmtree(tmp, ignore_errors=True)
sys.exit(0 if (live == 0 and oneshot == 1 and noopen == 0) else 1)
PY
if [ $? -eq 0 ]; then PASS=$((PASS+1)); echo "  ok   live=0 opens, one-shot=1, --no-open=0 (no browser-tab spam under watch)"; \
else FAIL=$((FAIL+1)); echo "  FAIL auto-open policy wrong -- a live/watch render would spam browser tabs"; fi

echo "== T80 (1.42.0): mirador status story (como viene/que lo traba/que sigue) present + fed by the ledger =="
printf '{ "defaults": { "acceptance_file": "ACCEPTANCE.md" }, "repos": [ {"name":"solo","path":"repo-c","type":"python"} ], "integration": {"enabled": false} }\n' > status-cfg.json
run init --config status-cfg.json --out L-status.json >/dev/null 2>&1
run log-gate --repo solo --iteration 1 --kind simplicity --verdict fail --count 3 --ledger L-status.json >/dev/null 2>&1
"$PY" "$KIT/.claude/skills/uscha-mirador/mirador-render.py" --engine "$QL" --ledger L-status.json \
  --template "$KIT/.claude/skills/uscha-mirador/mirador.template.html" --out status-mir.html --no-open >/dev/null 2>&1
"$PY" - status-mir.html <<'PYIN'
import json, re, sys
html = open(sys.argv[1], encoding="utf-8").read()
scaffold = all(x in html for x in ('id="status"', 'id="s-how"', 'id="s-block"', 'id="s-next"',
                                   'function renderStatus', 'renderStatus();', 'id="card-heat"'))
data = json.loads(re.search(r"const DATA = (\{.*?\});\n/\*MIRADOR_DATA_END", html, re.S).group(1))
subs = data.get("subscores") or []
fed = any("FAIL" in str(s.get("bd") or "").upper() for s in subs)   # a measured blocker feeds "que lo traba"
sys.exit(0 if (scaffold and fed) else 1)
PYIN
if [ $? -eq 0 ]; then PASS=$((PASS+1)); echo "  ok   status scaffold present and 'que lo traba' fed by a measured sub-score"; \
else FAIL=$((FAIL+1)); echo "  FAIL status story missing or not fed by the ledger"; fi

echo "== T81 (1.43.0): 'uscha mirador' verb renders the dashboard from the ledger (no python/paths for the user) =="
"$PY" "$KIT/install-uscha.py" mirador --ledger L-status.json --out uscha-mir.html --no-open >/dev/null 2>&1
if [ $? -eq 0 ] && [ -f uscha-mir.html ] && grep -q 'id="status"' uscha-mir.html; then
  PASS=$((PASS+1)); echo "  ok   uscha mirador renders mirador.html with the status story"; \
else FAIL=$((FAIL+1)); echo "  FAIL uscha mirador did not render the dashboard"; fi
"$PY" "$KIT/install-uscha.py" mirador --ledger NOPE-missing.json --no-open >/dev/null 2>&1
if [ $? -ne 0 ]; then PASS=$((PASS+1)); echo "  ok   uscha mirador fails clearly when the ledger is missing"; \
else FAIL=$((FAIL+1)); echo "  FAIL uscha mirador did not fail on a missing ledger"; fi

echo "== T82 (1.44.0): coverage sin reporte es UNMEASURED, distinto de un 0% medido =="
mkdir -p t82-sin t82-con/target/site/jacoco
printf '<?xml version="1.0" encoding="UTF-8"?>\n<report name="r"><counter type="LINE" missed="10" covered="0"/></report>\n' > t82-con/target/site/jacoco/jacoco.xml
printf '{ "defaults": { "acceptance_file": "ACCEPTANCE.md" },\n  "repos": [ {"name":"t82sin","path":"t82-sin","type":"maven"}, {"name":"t82con","path":"t82-con","type":"maven"} ], "integration": {"enabled": false} }\n' > t82-cfg.json
run init --config t82-cfg.json --out L-t82.json >/dev/null 2>&1
run readiness --ledger L-t82.json --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin); by = d['by_repo']
# el repo SIN reporte y el repo CON reporte que dice 0% puntuan igual (0.0) pero son
# HECHOS distintos: solo el primero es una medicion faltante
sys.exit(0 if (by['t82sin']['facts']['coverage_unmeasured'] is True
               and by['t82con']['facts']['coverage_unmeasured'] is False
               and by['t82con']['facts']['coverage_pct'] == 0.0
               and d['facts'].get('coverage_unmeasured_repos') == ['t82sin']) else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   'sin reporte' y '0% medido' son hechos distintos"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL coverage no distingue no-instrumentado de cero medido"; }
run readiness --ledger L-t82.json 2>/dev/null | grep -q "NO coverage report found in: t82sin" \
  && { PASS=$((PASS+1)); echo "  ok   el aviso nombra el repo y el remedio (no hay que leer el motor)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL sin aviso visible de coverage UNMEASURED"; }
# exencion DECLARADA por el humano: redistribuye el peso (procedencia config), no es silencio.
# Con el resto de las dimensiones en verde, el repo legacy sin instrumentar queda clavado
# en 66.7 (2 de 3 dimensiones) -- el techo real reportado en campo -- y solo la DECLARACION
# humana lo libera. El silencio, por si solo, nunca sube el numero.
t82_setup() { # $1 = config, $2 = ledger
  run init --config "$1" --out "$2" >/dev/null 2>&1
  for t in code-review judgment-day improve; do
    run log-step --repo t82sin --tool "$t" --iteration 1 --tests-passed true --ledger "$2" >/dev/null 2>&1
  done
  run ingest-gate --repo t82sin --tool code-review --iteration 1 --json-report /dev/null --ledger "$2" >/dev/null 2>&1
  run log-gate --repo t82sin --iteration 1 --kind simplicity --verdict pass --ledger "$2" >/dev/null 2>&1
}
printf '{ "defaults": { "acceptance_file": "ACCEPTANCE.md" },\n  "repos": [ {"name":"t82sin","path":"t82-sin","type":"maven"} ], "integration": {"enabled": false} }\n' > t82-base.json
printf '{ "defaults": { "acceptance_file": "ACCEPTANCE.md", "readiness_weights": {"coverage": 0} },\n  "repos": [ {"name":"t82sin","path":"t82-sin","type":"maven"} ], "integration": {"enabled": false} }\n' > t82-decl.json
t82_setup t82-base.json L-t82b.json
t82_setup t82-decl.json L-t82d.json
T82_BASE=$(run readiness --ledger L-t82b.json --json 2>/dev/null | "$PY" -c "import json,sys; print(json.load(sys.stdin)['by_repo']['t82sin']['score'])")
T82_DECL=$(run readiness --ledger L-t82d.json --json 2>/dev/null | "$PY" -c "import json,sys; print(json.load(sys.stdin)['by_repo']['t82sin']['score'])")
if [ "$T82_BASE" = "66.7" ] && [ "$T82_DECL" = "100.0" ]; then
  PASS=$((PASS+1)); echo "  ok   sin declarar 66.7 (techo real) -> declarando coverage=0 sube a 100.0"; \
else FAIL=$((FAIL+1)); echo "  FAIL exencion declarada: base=$T82_BASE decl=$T82_DECL (esperado 66.7/100.0)"; fi

echo "== T83 (1.44.0): tipo 'ant' + reportes JUnit fuera de la convencion maven =="
mkdir -p t83-ant/reports/junit t83-ant/coverage
printf '<?xml version="1.0" encoding="UTF-8"?>\n<testsuite name="AppTest" tests="2" failures="0" errors="0" skipped="0">\n  <testcase classname="AppTest" name="testAC01_x"/>\n  <testcase classname="AppTest" name="testAC02_y"/>\n</testsuite>\n' > t83-ant/reports/junit/TEST-AppTest.xml
printf '<?xml version="1.0" encoding="UTF-8"?>\n<report name="a"><counter type="LINE" missed="30" covered="70"/></report>\n' > t83-ant/coverage/jacoco.xml
# Dos trampas reales de un arbol legacy, que ejercitan los DOS mecanismos:
#  (a) third-party: sus reportes nunca son nuestros -> PODADO
#  (b) un XML que se llama TEST-*.xml pero NO es JUnit, en el arbol propio (un fixture) ->
#      TOLERADO con aviso. Sin esto, un archivo suelto abortaba la corrida con SystemExit 2.
# Nota: build/ y coverage/ NO se podan aca a proposito -- los reportes VIVEN ahi.
mkdir -p t83-ant/node_modules/dep t83-ant/src/test/resources
printf '<?xml version="1.0" encoding="UTF-8"?>\n<report name="vendored"><counter type="LINE" missed="900" covered="100"/></report>\n' > t83-ant/node_modules/dep/jacoco.xml
printf '<?xml version="1.0" encoding="UTF-8"?>\n<project name="tampoco"/>\n' > t83-ant/node_modules/dep/TEST-Dep.xml
printf '<?xml version="1.0" encoding="UTF-8"?>\n<fixture name="no-soy-junit"/>\n' > t83-ant/src/test/resources/TEST-Fixture.xml
#  (c) raiz <testsuite> VALIDA pero contadores imposibles (corrida truncada): la validacion
#      de contadores TAMBIEN salia por SystemExit(2), fuera del bloque tolerante.
printf '<?xml version="1.0" encoding="UTF-8"?>\n<testsuite name="Trunc" tests="1" failures="5" errors="0" skipped="0"/>\n' > t83-ant/reports/junit/TEST-Truncado.xml
printf '{ "defaults": { "acceptance_file": "ACCEPTANCE.md", "coverage_threshold": 60 },\n  "repos": [ {"name":"t83ant","path":"t83-ant","type":"ant"} ], "integration": {"enabled": false} }\n' > t83-cfg.json
run init --config t83-cfg.json --out L-t83.json >/dev/null 2>&1
"$PY" - "$QL" <<'PYIN'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("q", sys.argv[1])
q = importlib.util.module_from_spec(spec); spec.loader.exec_module(q)
tc = q.test_count("t83-ant", "ant")          # Ant escribe TEST-*.xml donde diga el build
cov = q.coverage("t83-ant", "ant")           # y jacoco.xml fuera de target/site/
files = q._junit_files_for("t83-ant", "ant")  # trazabilidad AC-n sobre los mismos reportes
# los dos reportes inservibles se descartan SIN abortar, y quedan REGISTRADOS en el
# resultado (stderr no alcanza: dashboard --json captura stdout, no stderr)
reasons = {d["reason"] for d in tc["skipped_reports"]}
sys.exit(0 if (tc["total"] == 2 and tc["report_found"] is True
               and cov["pct"] == 70.0 and cov["report_found"] is True
               and not any("node_modules" in f for f in files)
               and len(tc["skipped_reports"]) == 2
               and "malformed JUnit counters" in reasons) else 1)
PYIN
if [ $? -eq 0 ]; then PASS=$((PASS+1)); echo "  ok   ant: descubre, poda third-party, y DESCARTA-REGISTRANDO lo inservible sin abortar"; \
else FAIL=$((FAIL+1)); echo "  FAIL ant: no descubre, no poda third-party, o aborta con un XML ajeno"; fi

echo "== T84 (1.44.0): nombres reservados de Windows no tumban el recorrido =="
"$PY" - "$QL" <<'PYIN'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("q", sys.argv[1])
q = importlib.util.module_from_spec(spec); spec.loader.exec_module(q)
# Windows toma lo anterior al PRIMER punto: 'nul.tar.gz' es tan reservado como 'nul.txt'
reserved = all(q._reserved_name(n) for n in ("nul", "NUL.txt", "con", "aux", "com3", "lpt9",
                                             "nul.tar.gz", "con.spec.ts", "aux.d.ts"))
sane = not any(q._reserved_name(n) for n in ("normal.java", "nullable.py", "console.ts",
                                             "com1x.go", "auxiliary.md"))
sys.exit(0 if (reserved and sane) else 1)
PYIN
if [ $? -eq 0 ]; then PASS=$((PASS+1)); echo "  ok   nul/con/aux/com3/lpt9 se saltan y no hay falsos positivos"; \
else FAIL=$((FAIL+1)); echo "  FAIL el filtro de nombres reservados es incorrecto"; fi

echo "== T86 (1.45.0): risk_profile is a named preset -- expands, explicit wins, unknown fails =="
printf -- "# ACCEPTANCE\n\n- [ ] uno\n" > t86-acc.md
# perfil E expande qa_tools_order + coverage_threshold + golden_required en el config del ledger
printf '{ "defaults": { "acceptance_file": "t86-acc.md", "risk_profile": "E" },\n  "repos": [ {"name":"solo","path":"repo-c","type":"python"} ], "integration": {"enabled": false} }\n' > t86-E.json
run init --config t86-E.json --out L-t86E.json >/dev/null 2>&1
"$PY" -c "
import json, sys
d = json.load(open('L-t86E.json', encoding='utf-8'))['config']['defaults']
sys.exit(0 if (d.get('qa_tools_order') == ['code-review','judgment-day','improve']
               and d.get('golden_required') is True and d.get('coverage_threshold') == 80
               and 'golden_required' in (d.get('_risk_profile_keys') or [])) else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   perfil E expande qa_tools_order/coverage/golden_required con marcador de procedencia"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL el perfil no expandio los knobs"; }
# lo explicito gana sobre el perfil (perfil A pero qa_tools_order declarado a mano)
printf '{ "defaults": { "acceptance_file": "t86-acc.md", "risk_profile": "A", "qa_tools_order": ["code-review","improve"] },\n  "repos": [ {"name":"solo","path":"repo-c","type":"python"} ], "integration": {"enabled": false} }\n' > t86-ov.json
run init --config t86-ov.json --out L-t86o.json >/dev/null 2>&1
"$PY" -c "
import json, sys
d = json.load(open('L-t86o.json', encoding='utf-8'))['config']['defaults']
sys.exit(0 if (d.get('qa_tools_order') == ['code-review','improve']
               and 'qa_tools_order' not in (d.get('_risk_profile_keys') or [])) else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   qa_tools_order explicito gana sobre el del perfil"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL el explicito no gano al perfil"; }
# perfil desconocido -> error duro (una declaracion de riesgo nunca es inerte)
printf '{ "defaults": { "acceptance_file": "t86-acc.md", "risk_profile": "Z" },\n  "repos": [ {"name":"solo","path":"repo-c","type":"python"} ], "integration": {"enabled": false} }\n' > t86-Z.json
run init --config t86-Z.json --out L-t86z.json >/dev/null 2>&1
if [ $? -ne 0 ]; then PASS=$((PASS+1)); echo "  ok   risk_profile desconocido falla duro (nunca inerte)"; \
else FAIL=$((FAIL+1)); echo "  FAIL perfil desconocido no fallo"; fi
# byte-identico sin perfil: un config sin risk_profile/golden_required NO gana campos nuevos
printf '{ "defaults": { "acceptance_file": "t86-acc.md" },\n  "repos": [ {"name":"solo","path":"repo-c","type":"python"} ], "integration": {"enabled": false} }\n' > t86-bare.json
run init --config t86-bare.json --out L-t86b.json >/dev/null 2>&1
run readiness --ledger L-t86b.json --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
# sin golden_required en juego, ni el repo ni el agregado ganan el campo golden_missing
sys.exit(0 if ('golden_missing' not in d['by_repo']['solo']['facts']
               and 'golden_missing_repos' not in d['facts']) else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   sin perfil: readiness no gana campos golden (byte-identico)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL sin perfil aparecieron campos golden (rompe byte-identico)"; }

echo "== T87 (1.45.0): golden_required caps readiness to 49 when the approved golden is ABSENT =="
# pesos aislados en static+convergence (=1.0) -> base agregada 100, para ver morder el cap
t87() { # $1 = extra defaults ; $2 = 'golden' para loguear golden aprobado ; imprime score|source
  printf '{ "defaults": { "acceptance_file": "t86-acc.md", "readiness_weights": {"acceptance":0,"adr":0,"coverage":0,"static_gate":50,"convergence":50} %s },\n  "repos": [ {"name":"solo","path":"repo-c","type":"python"} ], "integration": {"enabled": false} }\n' "$1" > t87.json
  run init --config t87.json --out L-t87.json >/dev/null 2>&1
  for tl in code-review judgment-day improve; do run log-step --repo solo --tool "$tl" --iteration 1 --tests-passed true --ledger L-t87.json >/dev/null 2>&1; done
  run ingest-gate --repo solo --tool code-review --iteration 1 --json-report /dev/null --ledger L-t87.json >/dev/null 2>&1
  run log-gate --repo solo --iteration 1 --kind simplicity --verdict pass --ledger L-t87.json >/dev/null 2>&1
  [ "${2:-}" = golden ] && run log-gate --repo solo --iteration 1 --kind golden-diff --verdict pass --ledger L-t87.json >/dev/null 2>&1
  run readiness --ledger L-t87.json --json 2>/dev/null | "$PY" -c "import json,sys;d=json.load(sys.stdin);print('%s|%s'%(d['score'], d.get('cap_source')))"
}
R_E=$(t87 ', "risk_profile": "E"')                              # perfil E, sin golden
R_G=$(t87 ', "risk_profile": "E"' golden)                       # perfil E, con golden aprobado
R_C=$(t87 ', "golden_required": true')                          # declarado directo, sin golden
R_O=$(t87 ', "risk_profile": "E", "golden_required": false')    # override explicito
if [ "$R_E" = "49|requerimiento (perfil E)" ] && [ "${R_G%%|*}" = "100.0" ] \
   && [ "$R_C" = "49|requerimiento (config)" ] && [ "${R_O%%|*}" = "100.0" ]; then
  PASS=$((PASS+1)); echo "  ok   sin golden -> cap 49 (perfil E / config); con golden o override -> no capea"; \
else FAIL=$((FAIL+1)); echo "  FAIL golden cap: E=$R_E G=$R_G C=$R_C O=$R_O"; fi

echo "== T88 (1.46.0): statusline scripts are generic (config-driven) and degrade to empty =="
T88="$(mktemp -d)"
mkdir -p "$T88/.claude" "$T88/src"
cat > "$T88/uscha.config.json" <<'JSON'
{ "defaults": { "acceptance_file": "ACCEPTANCE.md" },
  "repos": [ { "name": "myproj", "path": ".", "type": "python", "label": "MY PROJECT",
    "roadmap": [ {"name":"01 Core","path":"src/core.py"}, {"name":"02 API","path":"src/api.py"} ],
    "build_priority": ["02 API","01 Core"] } ] }
JSON
printf -- "# ACCEPTANCE\n\n- [X] **AC-01** hecho\n- [ ] ac-02 — build the API\n" > "$T88/ACCEPTANCE.md"  # [X] mayus + ac minus: ejercita el IGNORECASE (debe seguir contando 1/2)
"$PY" -c "print('x'*300)" > "$T88/src/core.py"   # >200 bytes -> built ; src/api.py absent -> not built
echo '{"repos":{"myproj":{"snapshots":[{"tests":{"report_found":true,"passed":7},"coverage":{"report_found":true,"pct":55.0}}]}}}' > "$T88/QA-LEDGER.json"
CLAUDE_PROJECT_DIR="$T88" "$PY" "$KIT/templates/scripts/uscha_progress.py"
T88_RENDER=$(echo '{}' | CLAUDE_PROJECT_DIR="$T88" "$PY" "$KIT/templates/scripts/uscha_statusline.py" | sed 's/\x1b\[[0-9;]*m//g')
T88_HOME="$T88" "$PY" -c "
import json, os, sys
s = json.load(open(os.path.join(os.environ['T88_HOME'], '.claude', 'uscha-progress.json'), encoding='utf-8'))
# label + AC + roadmap all come from the config/files, nothing hardcoded, no ANTI-FARO
ok = (s['label'] == 'MY PROJECT' and s['pct'] == 50 and s['done'] == 1 and s['total'] == 2
      and s['tests'] == 7 and s['roadmap_done'] == 1 and s['roadmap_total'] == 2
      and s['roadmap_next'] == '02 API')
sys.exit(0 if ok else 1)"
T88_JSON=$?
# degradation: remove the progress file -> statusline prints an EMPTY (hidden) line
rm -f "$T88/.claude/uscha-progress.json"
T88_EMPTY=$(echo '{}' | CLAUDE_PROJECT_DIR="$T88" "$PY" "$KIT/templates/scripts/uscha_statusline.py")
rm -rf "$T88"
if [ "$T88_JSON" -eq 0 ] && echo "$T88_RENDER" | grep -q "MY PROJECT" \
   && ! echo "$T88_RENDER" | grep -qi "ANTI" && [ -z "$T88_EMPTY" ]; then
  PASS=$((PASS+1)); echo "  ok   config-driven progress + render, zero hardcoded project, hidden when no data"; \
else FAIL=$((FAIL+1)); echo "  FAIL statusline not generic or did not degrade (json=$T88_JSON empty=[$T88_EMPTY])"; fi

echo "== T89 (1.46.0): uscha init wires the statusline into settings.json (merge, no clobber) =="
T89="$(mktemp -d)"
T89_RC=0
"$PY" "$KIT/install-uscha.py" init --repo "$T89" >/dev/null 2>&1 || T89_RC=$?
T89_HOME="$T89" "$PY" -c "
import json, os, sys
h = os.environ['T89_HOME']
s = json.load(open(os.path.join(h, '.claude', 'settings.json'), encoding='utf-8'))
# the interpreter is OS-resolved (kit 1.51.0): python3 on POSIX, python on Windows
py = 'python' if os.name == 'nt' else 'python3'
sl_ok = s.get('statusLine', {}).get('command') == py + ' .claude/scripts/uscha_statusline.py'
stop = s.get('hooks', {}).get('Stop', [])
stop_ok = any(hh.get('command') == py + ' .claude/scripts/uscha_progress.py'
              for g in stop for hh in (g.get('hooks') or []))
scripts_ok = (os.path.isfile(os.path.join(h, '.claude', 'scripts', 'uscha_statusline.py'))
              and os.path.isfile(os.path.join(h, '.claude', 'scripts', 'uscha_progress.py')))
sys.exit(0 if (sl_ok and stop_ok and scripts_ok) else 1)" && T89_WIRED=0 || T89_WIRED=$?
# a foreign statusLine is a CONFLICT, never overwritten
T89_HOME="$T89" "$PY" -c "
import json, os
h = os.environ['T89_HOME']; p = os.path.join(h, '.claude', 'settings.json')
d = json.load(open(p, encoding='utf-8')); d['statusLine'] = {'type': 'command', 'command': 'mine'}
json.dump(d, open(p, 'w', encoding='utf-8'))"
"$PY" "$KIT/install-uscha.py" init --repo "$T89" >/dev/null 2>&1 || true
T89_HOME="$T89" "$PY" -c "
import json, os, sys
d = json.load(open(os.path.join(os.environ['T89_HOME'], '.claude', 'settings.json'), encoding='utf-8'))
sys.exit(0 if d['statusLine']['command'] == 'mine' else 1)" && T89_KEEP=0 || T89_KEEP=$?
rm -rf "$T89"
if [ "$T89_RC" -eq 0 ] && [ "$T89_WIRED" -eq 0 ] && [ "$T89_KEEP" -eq 0 ]; then
  PASS=$((PASS+1)); echo "  ok   init wires statusLine + Stop hook + scripts, and never clobbers a foreign statusLine"; \
else FAIL=$((FAIL+1)); echo "  FAIL init statusline wiring (rc=$T89_RC wired=$T89_WIRED keep=$T89_KEEP)"; fi

echo "== T90 (1.46.1): statusline shows MEASURED acceptance, never narrated (measured beats narrated) =="
# isolated subdir: the engine resolves acceptance_file relative to CWD, so it must run inside it
T90="$(mktemp -d)"
( cd "$T90" && mkdir -p .claude reports/junit
  # AC-01 and AC-02 both UNCHECKED, but AC-01 has a green testcase -> checkbox 0/2, MEASURED 1/2
  printf -- "# ACCEPTANCE\n\n- [ ] AC-01 — first\n- [ ] AC-02 — second\n" > ACCEPTANCE.md
  printf '<?xml version="1.0" encoding="UTF-8"?>\n<testsuite name="acc" tests="1" failures="0" errors="0" skipped="0">\n  <testcase classname="acc" name="AC-01_first"/>\n</testsuite>\n' > reports/junit/TEST.xml
  printf '{ "defaults": { "acceptance_file": "ACCEPTANCE.md" }, "repos": [ {"name":"p","path":".","type":"python","label":"DEMO"} ], "integration": {"enabled": false} }\n' > uscha.config.json
  run init --config uscha.config.json --out QA-LEDGER.json >/dev/null 2>&1
  run snapshot --ledger QA-LEDGER.json --repo p >/dev/null 2>&1
  # BEFORE record: no measured summary -> falls back to checkbox (0/2)
  CLAUDE_PROJECT_DIR="$(pwd)" "$PY" "$KIT/templates/scripts/uscha_progress.py"
  before=$("$PY" -c "import json;s=json.load(open('.claude/uscha-progress.json'));print('%s/%s'%(s['done'],s['total']))")
  run readiness --ledger QA-LEDGER.json --record >/dev/null 2>&1   # persist ledger['measured']
  CLAUDE_PROJECT_DIR="$(pwd)" "$PY" "$KIT/templates/scripts/uscha_progress.py"
  after=$("$PY" -c "import json;s=json.load(open('.claude/uscha-progress.json'));print('%s/%s'%(s['done'],s['total']))")
  echo "$before $after" > result.txt )
read T90_BEFORE T90_AFTER < "$T90/result.txt"
rm -rf "$T90"
# checkboxes say 0/2 (narrated); once the engine records, the statusline shows the MEASURED 1/2
if [ "$T90_BEFORE" = "0/2" ] && [ "$T90_AFTER" = "1/2" ]; then
  PASS=$((PASS+1)); echo "  ok   checkbox fallback 0/2 -> after readiness --record shows MEASURED 1/2 (agrees with the ledger)"; \
else FAIL=$((FAIL+1)); echo "  FAIL statusline not sourced from measured (before=$T90_BEFORE after=$T90_AFTER)"; fi

echo "== T91 (1.47.0): the trail feeds itself -- loop odometer in measured, mirador QA badge, statusline phase token =="
# isolated subdir (same reason as T90: acceptance_file resolves relative to CWD)
T91="$(mktemp -d)"
( cd "$T91" && mkdir -p .claude reports/junit
  printf -- "# ACCEPTANCE\n\n- [ ] AC-01 — first\n" > ACCEPTANCE.md
  printf '<?xml version="1.0" encoding="UTF-8"?>\n<testsuite name="acc" tests="1" failures="0" errors="0" skipped="0">\n  <testcase classname="acc" name="AC-01_first"/>\n</testsuite>\n' > reports/junit/TEST.xml
  printf '{ "defaults": { "acceptance_file": "ACCEPTANCE.md" }, "repos": [ {"name":"p","path":".","type":"python","label":"DEMO"} ], "integration": {"enabled": false} }\n' > uscha.config.json
  run init --config uscha.config.json --out QA-LEDGER.json >/dev/null 2>&1
  run snapshot --ledger QA-LEDGER.json --repo p >/dev/null 2>&1
  # two QA loop passes -> phase "qa", loops 2
  run log-step --ledger QA-LEDGER.json --repo p --tool code-review --iteration 1 --reported 3 --gated-reported 2 --fixed 2 >/dev/null 2>&1
  run log-step --ledger QA-LEDGER.json --repo p --tool code-review --iteration 2 --reported 1 --gated-reported 1 --fixed 1 >/dev/null 2>&1
  run readiness --ledger QA-LEDGER.json --record >/dev/null 2>&1
  # 1) measured carries the odometer: derived phase + loop count + plateau flag per repo
  odo=$("$PY" -c "import json;r=json.load(open('QA-LEDGER.json'))['measured']['repos']['p'];print('%s/%s/%s'%(r['phase'],r['loops'],r['stalled']))")
  # 2) mirador trail: the 'qa' node badge shows the measured pass count
  badge=$(run dashboard --ledger QA-LEDGER.json --json 2>/dev/null | "$PY" -c "import json,sys;d=json.load(sys.stdin);print(next(p['count'] for p in d['phases'] if p['key']=='qa'))")
  # 3) statusline: the phase token comes from measured, rendered as 'qa×2'
  CLAUDE_PROJECT_DIR="$(pwd)" "$PY" "$KIT/templates/scripts/uscha_progress.py"
  tok=$("$PY" -c "import json;s=json.load(open('.claude/uscha-progress.json'));print('%s/%s'%(s['phase'],s['loops']))")
  line=$(CLAUDE_PROJECT_DIR="$(pwd)" "$PY" "$KIT/templates/scripts/uscha_statusline.py" < /dev/null)
  echo "$odo|$badge|$tok|$line" > result.txt )
T91_RES="$(cat "$T91/result.txt")"
rm -rf "$T91"
T91_ODO="${T91_RES%%|*}"; T91_REST="${T91_RES#*|}"
T91_BADGE="${T91_REST%%|*}"; T91_REST="${T91_REST#*|}"
T91_TOK="${T91_REST%%|*}"; T91_LINE="${T91_REST#*|}"
if [ "$T91_ODO" = "qa/2/False" ] && [ "$T91_BADGE" = "2 loops" ] && [ "$T91_TOK" = "qa/2" ] \
   && printf '%s' "$T91_LINE" | grep -q "qa×2"; then
  PASS=$((PASS+1)); echo "  ok   measured.repos.p={qa,2,not stalled} · mirador qa badge '2 loops' · statusline token 'qa×2'"; \
else FAIL=$((FAIL+1)); echo "  FAIL odometer broken (odo=$T91_ODO badge=$T91_BADGE tok=$T91_TOK line=$T91_LINE)"; fi

echo "== T92 (1.48.0): installer skill roster == dirs on disk, and uscha-status has a valid frontmatter =="
# same no-drift spirit as T57 (doctor roster): a new skill dir without registering it in
# install-uscha.py SKILLS would silently not install. The installer list must match disk.
"$PY" - "$KIT" <<'PY'
import os, re, sys
kit = sys.argv[1]
src = open(os.path.join(kit, "install-uscha.py"), encoding="utf-8").read()
m = re.search(r"SKILLS = \[(.*?)\]", src, re.DOTALL)
listed = set(re.findall(r'"(uscha-[a-z-]+)"', m.group(1)))
ondisk = {d for d in os.listdir(os.path.join(kit, ".claude", "skills"))
          if d.startswith("uscha-")}
front = open(os.path.join(kit, ".claude", "skills", "uscha-status", "SKILL.md"),
             encoding="utf-8").read()
ok = (listed == ondisk
      and re.search(r"^name: uscha-status$", front, re.MULTILINE)
      and "read-only" in front.lower())
sys.exit(0 if ok else 1)
PY
if [ $? -eq 0 ]; then
  PASS=$((PASS+1)); echo "  ok   install-uscha.py SKILLS matches skill dirs; uscha-status frontmatter valid and read-only by contract"; \
else FAIL=$((FAIL+1)); echo "  FAIL installer roster drifted or uscha-status SKILL.md malformed"; fi

echo "== T93 (1.48.1): one derivation -- narrated is LABELED, and an open spec-doubt escalates BOTH views =="
# QA-loop findings: (a) the statusline dressed narrated checkboxes exactly like measured
# acceptance; (b) the mirador derived 'escalated' from ledger["escalations"] alone, so an
# open spec-doubt showed escalated in the statusline and NOT in the mirador badge.
T93="$(mktemp -d)"
( cd "$T93" && mkdir -p .claude reports/junit
  printf -- "# ACCEPTANCE\n\n- [x] AC-01 — ticked by a human, closed by NO test\n" > ACCEPTANCE.md
  printf '{ "defaults": { "acceptance_file": "ACCEPTANCE.md" }, "repos": [ {"name":"p","path":".","type":"python","label":"DEMO"} ], "integration": {"enabled": false} }\n' > uscha.config.json
  run init --config uscha.config.json --out QA-LEDGER.json >/dev/null 2>&1
  run snapshot --ledger QA-LEDGER.json --repo p >/dev/null 2>&1
  # (a) no measurement recorded -> the checkbox fallback must be MARKED as narrated
  CLAUDE_PROJECT_DIR="$(pwd)" "$PY" "$KIT/templates/scripts/uscha_progress.py"
  src=$("$PY" -c "import json;print(json.load(open('.claude/uscha-progress.json'))['acceptance_source'])")
  line=$(CLAUDE_PROJECT_DIR="$(pwd)" "$PY" "$KIT/templates/scripts/uscha_statusline.py" < /dev/null)
  # (b) NARRATED tests (agent-reported, no measured snapshot) must NEVER read as
  # 'converged' on the mirador while the odometer withholds readiness: same ledger,
  # same derivation. This is the view a human reads before deciding a merge.
  for t in code-review judgment-day improve; do
    run log-step --ledger QA-LEDGER.json --repo p --tool $t --iteration 1 \
      --tests-passed true --files-changed 0 >/dev/null 2>&1
  done
  narr=$(run dashboard --ledger QA-LEDGER.json --json 2>/dev/null | "$PY" -c "import json,sys;d=json.load(sys.stdin);print(next(l['state'] for l in d['loops'] if l['mod']=='p'))")
  # (c) an open spec-doubt is an escalation: the mirador badge must say so too
  run spec-doubt --ledger QA-LEDGER.json --repo p --kind ambiguous --note "SPEC unclear" >/dev/null 2>&1
  badge=$(run dashboard --ledger QA-LEDGER.json --json 2>/dev/null | "$PY" -c "import json,sys;d=json.load(sys.stdin);print(next(l['state'] for l in d['loops'] if l['mod']=='p'))")
  # and the persisted odometer (what the statusline reads) must agree with it
  run readiness --ledger QA-LEDGER.json --record >/dev/null 2>&1
  odo=$("$PY" -c "import json;print(json.load(open('QA-LEDGER.json'))['measured']['repos']['p']['phase'])")
  echo "$src|$badge|$odo|$narr|$line" > result.txt )
T93_RES="$(cat "$T93/result.txt")"
rm -rf "$T93"
T93_SRC="${T93_RES%%|*}"; T93_R="${T93_RES#*|}"
T93_BADGE="${T93_R%%|*}"; T93_R="${T93_R#*|}"
T93_ODO="${T93_R%%|*}"; T93_R="${T93_R#*|}"
T93_NARR="${T93_R%%|*}"; T93_LINE="${T93_R#*|}"
if [ "$T93_SRC" = "narrated" ] && printf '%s' "$T93_LINE" | grep -q "narrado" \
   && [ "$T93_NARR" != "converged" ] \
   && [ "$T93_BADGE" = "escalated" ] && [ "$T93_ODO" = "escalated" ]; then
  PASS=$((PASS+1)); echo "  ok   checkbox fallback labeled 'narrado' · narrated tests never read 'convergido' · spec-doubt escalates mirador AND odometer"; \
else FAIL=$((FAIL+1)); echo "  FAIL src=$T93_SRC badge=$T93_BADGE odo=$T93_ODO narrated_state=$T93_NARR line=$T93_LINE"; fi

echo "== T94 (1.48.2): the coverage seam is OPT-IN and the engine ingests what it emits =="
# The suite must NOT require coverage.py to run: instrumentation is opt-in via USCHA_COVERAGE.
# And the report it produces must be the shape the engine actually reads (Cobertura at
# reports/coverage.xml) -- emitting a report nothing ingests would be ceremony.
T94="$(mktemp -d)"
# BEHAVIOURAL opt-in check, not a string match: grepping the suite for its own guard would
# match the grep's own line and pass even if the feature were deleted. Instead -- when the
# switch is OFF, an engine call must leave NO coverage data behind.
T94_OPTIN=0
if [ "${USCHA_COVERAGE:-0}" = "1" ]; then
  T94_OPTIN=1   # instrumented on purpose this run; the off-path is not observable here
else
  mkdir -p "$T94/nocov"
  COVERAGE_FILE="$T94/nocov/.coverage" run --help >/dev/null 2>&1
  [ -z "$(find "$T94/nocov" -name '.coverage*' 2>/dev/null)" ] && T94_OPTIN=1
fi
( cd "$T94" && mkdir -p reports
  printf '{ "defaults": {"acceptance_file":"ACCEPTANCE.md"}, "repos": [ {"name":"p","path":".","type":"python"} ], "integration": {"enabled": false} }\n' > uscha.config.json
  printf -- "# ACCEPTANCE\n\n- [ ] AC-01 — x\n" > ACCEPTANCE.md
  # a minimal Cobertura report, exactly the shape coverage.py emits
  printf '<?xml version="1.0" ?>\n<coverage lines-valid="100" lines-covered="84" line-rate="0.84"><packages/></coverage>\n' > reports/coverage.xml
  run init --config uscha.config.json --out L.json >/dev/null 2>&1
  run snapshot --ledger L.json --repo p >/dev/null 2>&1
  "$PY" -c "
import json
s=json.load(open('L.json'))['repos']['p']['snapshots'][-1]['coverage']
print('%s|%s' % (s.get('report_found'), round(s.get('pct') or 0)))" > result.txt )
T94_COV="$(cat "$T94/result.txt")"
rm -rf "$T94"
if [ "$T94_OPTIN" -eq 1 ] && [ "$T94_COV" = "True|84" ]; then
  PASS=$((PASS+1)); echo "  ok   coverage is opt-in (suite runs without coverage.py) and reports/coverage.xml is ingested as MEASURED 84%"; \
else FAIL=$((FAIL+1)); echo "  FAIL optin=$T94_OPTIN ingest=$T94_COV"; fi

echo "== T95 (1.49.0): the mirador tells what the ledger knows -- acceptance panel + agent-only burn-down =="
# (a) dashboard emits per-AC status (measured/narrated/open) replacing the sourceless
# 'specs' panel; (b) loops carry the REAL derived phase + a per-cycle series built from
# AGENT steps only -- a static-gate ingest with below-gate noise must NOT pollute it.
T95="$(mktemp -d)"
( cd "$T95" && mkdir -p reports/junit
  printf -- "# ACCEPTANCE\n\n- [ ] AC-01 — closed by green test\n- [x] AC-02 — ticked, no test\n- [ ] AC-03 — untouched\n" > ACCEPTANCE.md
  printf '<?xml version="1.0" encoding="UTF-8"?>\n<testsuite name="acc" tests="1" failures="0" errors="0" skipped="0">\n  <testcase classname="acc" name="AC-01_green"/>\n</testsuite>\n' > reports/junit/TEST.xml
  printf '{ "defaults": { "acceptance_file": "ACCEPTANCE.md" }, "repos": [ {"name":"p","path":".","type":"python","label":"DEMO"} ], "integration": {"enabled": false} }\n' > uscha.config.json
  run init --config uscha.config.json --out L.json >/dev/null 2>&1
  run snapshot --ledger L.json --repo p >/dev/null 2>&1
  run log-step --ledger L.json --repo p --tool code-review --iteration 1 --reported 3 --gated-reported 2 --fixed 1 >/dev/null 2>&1
  run log-step --ledger L.json --repo p --tool code-review --iteration 2 --reported 1 --gated-reported 1 --fixed 1 >/dev/null 2>&1
  # a static-gate ingest in cycle 2 with a below-gate LOW: must NOT enter the series
  printf '[{"code":"E702","filename":"a.py","location":{"row":1}}]\n' > ruff.json
  run ingest-gate --ledger L.json --repo p --iteration 2 --ruff ruff.json >/dev/null 2>&1
  run dashboard --ledger L.json --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
a = d['acceptance']
st = {i['id']: i['status'] for i in a['items']}
l = d['loops'][0]
ok = (a['measured_done'] == 1 and a['total'] == 3
      and st.get('AC-1') == 'measured' and st.get('AC-2') == 'narrated'
      and st.get('AC-3') == 'open'
      and 'specs' not in d
      and l['phase'] == 'qa'
      and l['series'] == [
          {'cycle': 1, 'reported': 3, 'gated': 2, 'fixed': 1, 'deferred': 0},
          {'cycle': 2, 'reported': 1, 'gated': 1, 'fixed': 1, 'deferred': 0}])
print('OK' if ok else 'BAD %s %s %s' % (a['measured_done'], st, l))" > result.txt )
T95_RES="$(cat "$T95/result.txt")"
rm -rf "$T95"
if [ "$T95_RES" = "OK" ]; then
  PASS=$((PASS+1)); echo "  ok   acceptance items measured/narrated/open · specs gone · loops carry phase + agent-only series"; \
else FAIL=$((FAIL+1)); echo "  FAIL $T95_RES"; fi

echo "== T96 (1.50.0): receipts -- every number cites its evidence (report, file, when) =="
# The drawer machinery shipped in 1.32.0 fed by a hardcoded {}. Now: per-AC receipts cite
# the testcase + report; build cites snapshot reports + coverage path; a phase with no
# recorded facts gets NO key (the template says so honestly, never a silent no-op).
T96="$(mktemp -d)"
( cd "$T96" && mkdir -p reports/junit docs/adr
  printf -- "# ACCEPTANCE\n\n- [ ] AC-01 — closed by green test\n- [x] AC-02 — ticked, no test\n- [ ] AC-03 — mixed: one green AND one red\n" > ACCEPTANCE.md
  printf '<?xml version="1.0" encoding="UTF-8"?>\n<testsuite name="acc" tests="3" failures="1" errors="0" skipped="0">\n  <testcase classname="acc" name="AC-01_green_case"/>\n  <testcase classname="acc" name="AC-03_green_but_vetoed"/>\n  <testcase classname="acc" name="AC-03_red_case"><failure message="boom"/></testcase>\n</testsuite>\n' > reports/junit/TEST.xml
  printf '<?xml version="1.0" ?>\n<coverage lines-valid="100" lines-covered="70" line-rate="0.70"><packages/></coverage>\n' > reports/coverage.xml
  printf -- "# ADR-001 First decision\n\nStatus: accepted\n" > docs/adr/ADR-001.md
  printf '{ "defaults": { "acceptance_file": "ACCEPTANCE.md" }, "repos": [ {"name":"p","path":".","type":"python","label":"DEMO"} ], "integration": {"enabled": false} }\n' > uscha.config.json
  run init --config uscha.config.json --out L.json >/dev/null 2>&1
  run snapshot --ledger L.json --repo p >/dev/null 2>&1
  run dashboard --ledger L.json --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
ev = d['evidence']
it = {i['id']: i for i in d['acceptance']['items']}
cov = None
# the snapshot's coverage dict must now carry the report path it read
snapcov = None
ok = ('spec' in ev and 'build' in ev and 'prod' in ev
      and 'idea' not in ev                                   # no facts -> no key (honest)
      and 'AC-01_green_case' in ev['ac:AC-1']['pre']         # receipt cites the testcase
      and 'reports/junit/TEST.xml' in ev['ac:AC-1']['pre']   # ...and its report
      and 'tildado a mano' in ev['ac:AC-2']['pre']           # narrated says so
      and 'reports/coverage.xml' in ev['build']['pre']       # coverage cites its file
      and it['AC-1']['cases'] and it['AC-1']['cases'][0]['test'] == 'AC-01_green_case'
      # mixed green+red: fail-closed veto, and the receipt shows BOTH cases + names it
      and it['AC-3']['status'] != 'measured'
      and 'veto rojo' in ev['ac:AC-3']['pre']
      and 'AC-03_green_but_vetoed' in ev['ac:AC-3']['pre']
      and 'AC-03_red_case' in ev['ac:AC-3']['pre']
      and d['adrs'] and d['adrs'][0].get('file', '').endswith('ADR-001.md'))
print('OK' if ok else 'BAD keys=%s ac1=%s' % (sorted(ev.keys()), ev.get('ac:AC-1')))" > result.txt )
T96_RES="$(cat "$T96/result.txt")"
rm -rf "$T96"
if [ "$T96_RES" = "OK" ]; then
  PASS=$((PASS+1)); echo "  ok   AC receipt cites testcase+report · narrated says so · build cites coverage path · ADR carries file · no-facts phase has no key"; \
else FAIL=$((FAIL+1)); echo "  FAIL $T96_RES"; fi

echo "== T97 (1.50.x): doctor reads a .py-registered INV-GOLDEN hook as OK, no powershell needed =="
# The doctor used to check ONLY for block-approved-writes.ps1 and require powershell/pwsh, so
# a healthy .py install (what `uscha install` actually wires) read as broken on every OS --
# worst on mac/Linux, where it ALSO false-warned about a missing pwsh the .py never uses. On
# the CI Linux/macOS runners (no powershell present) a green here PROVES the .py path needs
# none: the runner IS the negative control.
T97="$(mktemp -d)"
( cd "$T97" && mkdir -p .claude/hooks
  cp "$KIT/hooks/block-approved-writes.py" .claude/hooks/
  printf '{ "hooks": { "PreToolUse": [ { "matcher": "*", "hooks": [ { "type": "command", "command": "python .claude/hooks/block-approved-writes.py" } ] } ] } }\n' > .claude/settings.json
  # isolate expanduser('~') on BOTH platforms: POSIX honors HOME, Windows honors USERPROFILE.
  HOME="$T97" USERPROFILE="$T97" run doctor --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
hk = [c for c in d['checks'] if 'INV-GOLDEN' in c['title']]
# exactly one hook check, level ok, and it names the .py variant (not the .ps1)
ok = (len(hk) == 1 and hk[0]['level'] == 'ok'
      and 'block-approved-writes.py' in hk[0].get('detail', ''))
print('OK' if ok else 'BAD ' + json.dumps(hk))" > result.txt )
T97_RES="$(cat "$T97/result.txt")"
rm -rf "$T97"
if [ "$T97_RES" = "OK" ]; then
  PASS=$((PASS+1)); echo "  ok   .py hook registered -> INV-GOLDEN reads OK without powershell (portable doctor)"; \
else FAIL=$((FAIL+1)); echo "  FAIL $T97_RES"; fi

echo "== T98 (1.50.2): the INV-GOLDEN hook is clean bytes AND runs DIRECTLY (BOM/CRLF regression) =="
# A UTF-8 BOM before the shebang makes the kernel hand the file to /bin/sh, which syntax-errors
# and exits 2 -- the exact PreToolUse BLOCK code -- so a corrupt hook LOOKS strict while it
# blocks EVERY tool call. Testing the hook only THROUGH an interpreter (as every other check
# does) masks it; only DIRECT execution reveals it. Field-measured on Linux, missed by the
# static audit.
HOOK="$KIT/hooks/block-approved-writes.py"
# 1) byte hygiene, on every OS: no BOM, no CRLF (the root cause). Pure bash -- passing an
#    MSYS path (/c/...) to Windows Python does not resolve; od/grep handle it natively.
T98_BOM="$(head -c3 "$HOOK" | od -An -tx1 | tr -d ' \n')"
# grep -c prints its count even on zero (and exits 1 then) -- capture the count, don't chain
# `|| echo 0` (that would emit a second line and break the integer test). Empty -> 0.
T98_CR="$(grep -c "$(printf '\r')" "$HOOK" 2>/dev/null)"; : "${T98_CR:=0}"
if [ "$T98_BOM" != "efbbbf" ] && [ "$T98_CR" -eq 0 ]; then T98_BYTES=ok; else T98_BYTES="bom=$T98_BOM cr=$T98_CR"; fi
# 2) behavioral proof via DIRECT execution (POSIX only: Windows git-bash does not honor a
#    script shebang for direct exec, and there the hook runs through a python command anyway)
T98_EXEC="skipped"
case "$(uname -s 2>/dev/null)" in
  MINGW*|MSYS*|CYGWIN*) : ;;   # Windows shell -> shebang direct-exec not meaningful
  *)
    chmod +x "$HOOK" 2>/dev/null
    printf '{"tool_name":"Write","tool_input":{"file_path":"src/app.py"}}' | "$HOOK" >/dev/null 2>&1; ALLOW=$?
    printf '{"tool_name":"Write","tool_input":{"file_path":"tests/x.approved"}}' | "$HOOK" >/dev/null 2>&1; BLOCK=$?
    [ "$ALLOW" -eq 0 ] && [ "$BLOCK" -eq 2 ] && T98_EXEC="ok" || T98_EXEC="allow=$ALLOW block=$BLOCK"
    ;;
esac
if [ "$T98_BYTES" = "ok" ] && { [ "$T98_EXEC" = "ok" ] || [ "$T98_EXEC" = "skipped" ]; }; then
  PASS=$((PASS+1)); echo "  ok   hook is BOM/CRLF-free; direct exec allow=0 block=2 (POSIX) [$T98_EXEC]"; \
else FAIL=$((FAIL+1)); echo "  FAIL bytes=$T98_BYTES exec=$T98_EXEC"; fi

echo "== T99 (1.50.2): reinstall self-heals a stale hook entry (N-1: prune by suffix, keep foreign) =="
# The hook command carries an ABSOLUTE sys.executable; an interpreter move would leave a dead
# PreToolUse entry that fails on every tool call. prepared_settings must prune ANY prior uscha
# hook (matched by the script basename, not the exact command) before adding the current one,
# and must NOT touch a user's own foreign hook. Field-found by simulation (N-1 / AC-P7).
T99=$("$PY" - "$KIT/install-uscha.py" <<'PY'
import importlib.util, json, os, sys, tempfile, pathlib
spec = importlib.util.spec_from_file_location("iu", sys.argv[1])
iu = importlib.util.module_from_spec(spec); spec.loader.exec_module(iu)
d = tempfile.mkdtemp(); p = pathlib.Path(d) / "settings.json"
p.write_text(json.dumps({"hooks": {"PreToolUse": [
    {"matcher": "*", "hooks": [{"type": "command",
     "command": "/old/py3.11 /home/u/.claude/hooks/block-approved-writes.py"}]},
    {"matcher": "*", "hooks": [{"type": "command", "command": "my-own-linter"}]},
]}}))
cur = "/new/py3 /home/u/.claude/hooks/block-approved-writes.py"
g = iu.prepared_settings(p, cur)["hooks"]["PreToolUse"]
ours = [h["command"] for grp in g for h in grp["hooks"] if "block-approved-writes.py" in h["command"]]
foreign = [h["command"] for grp in g for h in grp["hooks"] if "block-approved-writes.py" not in h["command"]]
# reinstall must be idempotent too: run it again on its own output
p.write_text(json.dumps({"hooks": {"PreToolUse": g}}))
g2 = iu.prepared_settings(p, cur)["hooks"]["PreToolUse"]
ours2 = [h["command"] for grp in g2 for h in grp["hooks"] if "block-approved-writes.py" in h["command"]]
import shutil; shutil.rmtree(d)
print("OK" if ours == [cur] and "my-own-linter" in foreign and ours2 == [cur] else
      "BAD ours=%s foreign=%s ours2=%s" % (ours, foreign, ours2))
PY
)
if [ "$T99" = "OK" ]; then
  PASS=$((PASS+1)); echo "  ok   stale entry pruned, current kept once, foreign preserved, idempotent"; \
else FAIL=$((FAIL+1)); echo "  FAIL $T99"; fi

echo "== T100 (1.50.2): the plugin hook is portable -- hooks.json invokes the .py, no PowerShell =="
# The plugin-marketplace flow reads the static hooks.json; a powershell-only command left
# INV-GOLDEN-01 dead on macOS/Linux. It now invokes the portable .py directly (runs via its
# shebang+exec bit on POSIX, the .py association on Windows -- enabled by P0-4). The .ps1 is gone.
T100=$("$PY" - "$KIT" <<'PY'
import json, os, sys
kit = sys.argv[1]
hj = json.load(open(os.path.join(kit, "hooks", "hooks.json"), encoding="utf-8"))
cmds = [h.get("command", "") for g in hj["hooks"]["PreToolUse"] for h in g["hooks"]]
c = " ".join(cmds)
ps1_gone = not os.path.isfile(os.path.join(kit, "hooks", "block-approved-writes.ps1"))
py_present = os.path.isfile(os.path.join(kit, "hooks", "block-approved-writes.py"))
ok = ("block-approved-writes.py" in c and "powershell" not in c.lower()
      and ".ps1" not in c and ps1_gone and py_present)
print("OK" if ok else "BAD cmd=%r ps1_gone=%s py=%s" % (c, ps1_gone, py_present))
PY
)
if [ "$T100" = "OK" ]; then
  PASS=$((PASS+1)); echo "  ok   hooks.json invokes the portable .py; the PowerShell .ps1 is removed"; \
else FAIL=$((FAIL+1)); echo "  FAIL $T100"; fi

echo ""
echo "RESULTADO BASE: $PASS ok · $FAIL fail"
cd / && rm -rf "$SB"
[ "$FAIL" -eq 0 ]
SMOKE_STATUS=$?
# P0-B-START: targeted fail-closed static-analysis evidence regression.
if [ "${USCHA_P0_B_SKIP:-0}" != "1" ]; then
  P0_B_ROOT="${P0_ROOT:-${ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}}"
  P0_B_QL="$P0_B_ROOT/uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py"
  P0_B_PY="${PYTHON:-${PY:-python}}"
  "$P0_B_PY" - "$P0_B_QL" <<'PY'
import json
import pathlib
import subprocess
import sys
import tempfile

engine = pathlib.Path(sys.argv[1])


def run(*args):
    return subprocess.run(
        [sys.executable, str(engine), *map(str, args)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")


cases = [
    ("checkstyle", "maven", "--checkstyle", "checkstyle.xml",
     '<checkstyle><file name="src/A.java"><error line="1" severity="error" source="Rule"/></file></checkstyle>',
     '<checkstyle/>', '<pmd/>', '<checkstyle>',
     '<checkstyle><file name="src/A"><error line="oops" severity="error" source="Rule"/></file></checkstyle>'),
    ("golangci", "go", "--golangci", "golangci.xml",
     '<checkstyle><file name="pkg/a.go"><error line="1" severity="error" source="Rule"/></file></checkstyle>',
     '<checkstyle/>', '<pmd/>', '<checkstyle>',
     '<checkstyle><file name="src/A"><error line="oops" severity="error" source="Rule"/></file></checkstyle>'),
    ("detekt", "gradle", "--detekt", "detekt.xml",
     '<checkstyle><file name="src/A.kt"><error line="1" severity="error" source="Rule"/></file></checkstyle>',
     '<checkstyle/>', '<pmd/>', '<checkstyle>',
     '<checkstyle><file name="src/A"><error line="oops" severity="error" source="Rule"/></file></checkstyle>'),
    ("swiftlint", "swift", "--swiftlint", "swiftlint.xml",
     '<checkstyle><file name="Sources/A.swift"><error line="1" severity="error" source="Rule"/></file></checkstyle>',
     '<checkstyle/>', '<pmd/>', '<checkstyle>',
     '<checkstyle><file name="src/A"><error line="oops" severity="error" source="Rule"/></file></checkstyle>'),
    ("pmd", "maven", "--pmd", "pmd.xml",
     '<pmd><file name="src/A.java"><violation beginline="1" priority="1" rule="Rule"/></file></pmd>',
     '<pmd/>', '<checkstyle/>', '<pmd>',
     '<pmd><file name="src/A.java"><violation beginline="1" priority="oops" rule="Rule"/></file></pmd>'),
    ("spotbugs", "maven", "--spotbugs", "spotbugs.xml",
     '<BugCollection><BugInstance type="BUG" priority="1" category="CORRECTNESS"><SourceLine sourcepath="A.java" start="1"/></BugInstance></BugCollection>',
     '<BugCollection/>', '<checkstyle/>', '<BugCollection>',
     '<BugCollection><BugInstance type="BUG" priority="oops" category="CORRECTNESS"/></BugCollection>'),
    ("eslint", "node", "--eslint", "eslint.json",
     '[{"filePath":"src/a.js","messages":[{"ruleId":"rule","severity":2,"line":1}]}]',
     '[]', '{}', '{', '[{"filePath":"src/a.js","messages":{}}]'),
    ("sarif", "dotnet", "--sarif", "analysis.sarif",
     '{"version":"2.1.0","runs":[{"results":[{"ruleId":"CA1","level":"error"}]}]}',
     '{"version":"2.1.0","runs":[]}', '[]', '{',
     '{"version":"2.1.0","runs":[{"results":{}}]}'),
    ("clippy", "rust", "--clippy", "clippy.json",
     '{"reason":"compiler-message","message":{"message":"needless return","level":"warning","code":{"code":"clippy::needless_return"},"spans":[{"file_name":"src/lib.rs","line_start":1,"is_primary":true}]}}',
     '', '[]', '{',
     '{"reason":"compiler-message","message":{"message":"bad spans","level":"warning","code":null,"spans":"not-an-array"}}'),

]

with tempfile.TemporaryDirectory(prefix="uscha-p0-b-") as tmp:
    root = pathlib.Path(tmp)
    for family, repo_type, flag, report_name, finding, empty, wrong, malformed, nested in cases:
        repo = root / family
        repo.mkdir()
        report = repo / report_name
        config = root / f"{family}.config.json"
        ledger = root / f"{family}.ledger.json"
        config.write_text(json.dumps({
            "defaults": {"severity_gate": ["BLOCKER", "CRITICAL", "HIGH"]},
            "repos": [{"name": family, "path": str(repo), "type": repo_type}],
            "integration": {"enabled": False},
        }), encoding="utf-8")
        result = run("init", "--config", config, "--out", ledger)
        assert result.returncode == 0, (family, "init", result.stderr)
        report.write_text(finding, encoding="utf-8")
        result = run("ingest-gate", "--ledger", ledger, "--repo", family,
                     "--iteration", "1", flag, report)
        assert result.returncode == 0, (family, "seed red", result.stdout, result.stderr)
        before = ledger.read_bytes()
        invalid_cases = [("malformed", malformed), ("wrong shape", wrong),
                         ("invalid fields", nested)]
        if family == "clippy":
            invalid_cases.extend([
                ("missing diagnostic code", '{"reason":"compiler-message","message":{"message":"bad code","level":"warning","spans":[]}}'),
                ("invalid primary span", '{"reason":"compiler-message","message":{"message":"bad location","level":"warning","code":null,"spans":[{"file_name":"src/lib.rs","line_start":false,"is_primary":true}]}}'),
            ])
        for label, invalid in invalid_cases:
            report.write_text(invalid, encoding="utf-8")
            result = run("ingest-gate", "--ledger", ledger, "--repo", family,
                         "--iteration", "2", flag, report)
            assert result.returncode == 2, (family, label, result.returncode,
                                            result.stdout, result.stderr)
            assert "invalid" in result.stderr.lower(), (family, label, result.stderr)
            assert ledger.read_bytes() == before, (family, label, "ledger mutated")
        valid_clean = [("valid empty", empty)]
        if family == "clippy":
            valid_clean.extend([
                ("valid no-span summary", '{"reason":"compiler-message","message":{"message":"1 warning emitted","level":"warning","code":null,"spans":[]}}'),
                ("valid Cargo summary", '{"reason":"build-finished","success":true}'),
            ])
        for label, clean in valid_clean:
            report.write_text(clean, encoding="utf-8")
            result = run("ingest-gate", "--ledger", ledger, "--repo", family,
                         "--iteration", "2", flag, report)
            assert result.returncode == 0, (family, label, result.stdout, result.stderr)
        print(f"P0-B ok: {family} malformed/wrong-shape/invalid-field fail closed; valid empty/noise accepted")
PY
  P0_B_STATUS=$?
  if [ "$P0_B_STATUS" -ne 0 ]; then SMOKE_STATUS="$P0_B_STATUS"; fi
fi
# P0-B-END
# P0-C-START: targeted stale-JUnit pr-ready regression.
if [ "${USCHA_P0_C_SKIP:-0}" != "1" ]; then
  P0_C_ROOT="${P0_ROOT:-${ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}}"
  P0_C_QL="$P0_C_ROOT/uscha-kit/.claude/skills/uscha-devloop/qa_ledger.py"
  P0_C_PY="${PYTHON:-${PY:-python}}"
  "$P0_C_PY" - "$P0_C_QL" <<'PY'
import json
import os
import pathlib
import subprocess
import sys
import tempfile

engine = pathlib.Path(sys.argv[1])


def run(*args):
    return subprocess.run(
        [sys.executable, str(engine), *map(str, args)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")


def check_layout(root, name, repo_type, source_rel, report_rel):
    repo = root / name
    source = repo / source_rel
    report = repo / report_rel
    source.parent.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("source\n", encoding="utf-8")
    report.write_text(
        '<testsuite tests="1" failures="0" errors="0" skipped="0"/>\n',
        encoding="utf-8")
    base_ns = 1_700_000_000_000_000_000
    os.utime(source, ns=(base_ns, base_ns))
    os.utime(report, ns=(base_ns + 5_000_000_000,
                         base_ns + 5_000_000_000))

    config = root / f"{name}.config.json"
    ledger = root / f"{name}.ledger.json"
    config.write_text(json.dumps({
        "defaults": {"qa_tools_order": ["code-review"]},
        "repos": [{"name": name, "path": str(repo), "type": repo_type}],
        "integration": {"enabled": False},
    }), encoding="utf-8")

    result = run("init", "--config", config, "--out", ledger)
    assert result.returncode == 0, (name, "init", result.stdout, result.stderr)
    result = run("snapshot", "--ledger", ledger, "--repo", name)
    assert result.returncode == 0, (name, "fresh snapshot", result.stdout, result.stderr)
    result = run("log-step", "--ledger", ledger, "--repo", name,
                 "--tool", "code-review", "--iteration", "1",
                 "--gated-reported", "0", "--files-changed", "0")
    assert result.returncode == 0, (name, "log-step", result.stdout, result.stderr)
    result = run("phase", "--ledger", ledger, "--repo", name,
                 "--require", "pr-ready")
    assert result.returncode == 0, (name, "fresh pr-ready", result.stdout, result.stderr)

    os.utime(source, ns=(base_ns + 10_000_000_000,
                         base_ns + 10_000_000_000))
    result = run("snapshot", "--ledger", ledger, "--repo", name)
    assert result.returncode == 0, (name, "stale snapshot", result.stdout, result.stderr)
    assert "stale" in result.stdout.lower(), (name, "stale snapshot diagnostic", result.stdout)
    latest = json.loads(ledger.read_text(encoding="utf-8"))["repos"][name]["snapshots"][-1]["tests"]
    assert latest["report_found"] is True and latest["freshness"]["status"] == "stale", latest
    assert latest["reports"] and latest["reports"][0]["path"], latest
    result = run("phase", "--ledger", ledger, "--repo", name,
                 "--require", "pr-ready")
    assert result.returncode == 1, (name, "stale pr-ready veto", result.stdout, result.stderr)
    assert "stale" in (result.stdout + result.stderr).lower(), (name, "stale phase diagnostic", result.stdout, result.stderr)

    os.utime(report, ns=(base_ns + 15_000_000_000,
                         base_ns + 15_000_000_000))
    result = run("snapshot", "--ledger", ledger, "--repo", name)
    assert result.returncode == 0, (name, "recovered snapshot", result.stdout, result.stderr)
    result = run("phase", "--ledger", ledger, "--repo", name,
                 "--require", "pr-ready")
    assert result.returncode == 0, (name, "recovered pr-ready", result.stdout, result.stderr)
    print(f"P0-C ok: {repo_type} fresh -> stale veto -> regenerated recovery")


def check_report_only_compatibility(root):
    name = "report-only"
    repo = root / name
    report = repo / "reports" / "junit.xml"
    ignored = repo / "vendor" / "ignored.py"
    report.parent.mkdir(parents=True)
    ignored.parent.mkdir(parents=True)
    report.write_text(
        '<testsuite tests="1" failures="0" errors="0" skipped="0"/>\n',
        encoding="utf-8")
    ignored.write_text("generated dependency\n", encoding="utf-8")
    config = root / f"{name}.config.json"
    ledger = root / f"{name}.ledger.json"
    config.write_text(json.dumps({
        "defaults": {"qa_tools_order": ["code-review"]},
        "repos": [{"name": name, "path": str(repo), "type": "python"}],
        "integration": {"enabled": False},
    }), encoding="utf-8")
    for args in (
        ("init", "--config", config, "--out", ledger),
        ("snapshot", "--ledger", ledger, "--repo", name),
        ("log-step", "--ledger", ledger, "--repo", name, "--tool", "code-review",
         "--iteration", "1", "--gated-reported", "0", "--files-changed", "0"),
    ):
        result = run(*args)
        assert result.returncode == 0, (name, args[0], result.stdout, result.stderr)
    latest = json.loads(ledger.read_text(encoding="utf-8"))["repos"][name]["snapshots"][-1]["tests"]
    assert latest["freshness"]["status"] == "unknown-no-sources", latest
    result = run("phase", "--ledger", ledger, "--repo", name,
                 "--require", "pr-ready")
    assert result.returncode == 0, (name, "compatibility", result.stdout, result.stderr)
    print("P0-C ok: report-only repo stays usable with explicit unknown-no-sources provenance")


with tempfile.TemporaryDirectory(prefix="uscha-p0-c-") as tmp:
    root = pathlib.Path(tmp)
    check_layout(root, "python-layout", "python", "src/app.py", "reports/junit.xml")
    check_layout(root, "maven-layout", "maven", "src/test/java/AppTest.java",
                 "target/surefire-reports/TEST-AppTest.xml")
    check_report_only_compatibility(root)
PY
  P0_C_STATUS=$?
  if [ "$P0_C_STATUS" -ne 0 ]; then SMOKE_STATUS="$P0_C_STATUS"; fi
fi
# P0-C-END
# P0-A-START: targeted Mirador script/DOM injection regression.
if [ "${USCHA_P0_A_SKIP:-0}" != "1" ]; then
  set -eu
  P0_PREVIOUS_STATUS="${SMOKE_STATUS:-0}"
  P0_ROOT="${P0_ROOT:-${ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}}"
  P0_KIT="$P0_ROOT/uscha-kit"
  P0_TMP="$(mktemp -d)"
  trap 'rm -rf "$P0_TMP"' EXIT
  P0_PY="${PYTHON:-${PY:-python}}"
  cat > "$P0_TMP/dashboard-engine.py" <<'PY'
#!/usr/bin/env python3
import json
import sys
sys.stdout.reconfigure(encoding="utf-8")
attack = '</script><script>globalThis.MIRADOR_PWNED=1</script><b>&"\'\u2028\u2029'
data = {
 "project": attack, "generated": attack,
 "readiness": {"score": 7, "band": "NOT READY", "title": attack, "sub": attack},
 "phases": [{"key": attack, "phase": attack, "label": attack, "status": "todo", "risk": 0, "count": attack,
             "execution": {"model": attack, "tier": attack, "effort": attack, "method": attack, "uncorrelated": True}}],
 "specs": [{"id": attack, "t": attack, "status": "todo", "acc": attack}],
 "adrs": [{"id": attack, "t": attack, "status": "todo", "adr_status": attack}],
 "inv": [{"name": attack, "status": "todo"}], "capas": [{"name": attack, "v": attack, "status": "warn"}],
 "loops": [{"mod": attack, "state": attack, "max": 1, "iters": 1}],
 "subscores": [{"k": attack, "val": None, "bd": attack}],
 "execution_policy": {"source": attack, "phases": {}},
 "evidence": {attack: {"ey": attack, "title": attack, "desc": attack, "pre": attack}},
 "snapshots": [{"date": attack, "readiness": 7, "reached": 0}],
}
print(json.dumps(data, ensure_ascii=False))
PY
  cat > "$P0_TMP/telemetry.jsonl" <<'JSON'
{"tokens_in":1,"tokens_out":2,"ms":3,"effort":"</script><script>telemetry()</script><i>&\"\u2028\u2029","by_model":[{"model":"<img src=x onerror=telemetry()> & \" model","tokens_in":1,"tokens_out":2}]}
JSON
  "$P0_PY" "$P0_KIT/.claude/skills/uscha-mirador/mirador-render.py" \
    --engine "$P0_TMP/dashboard-engine.py" --ledger "$P0_TMP/ledger.json" \
    --template "$P0_KIT/.claude/skills/uscha-mirador/mirador.template.html" \
    --out "$P0_TMP/mirador.html" --sidecar "$P0_TMP/telemetry.jsonl" --no-open >/dev/null
  "$P0_PY" - "$P0_TMP/mirador.html" "$P0_KIT/.claude/skills/uscha-mirador/mirador.template.html" <<'PY'
import json, pathlib, re, sys
attack = '</script><script>globalThis.MIRADOR_PWNED=1</script><b>&"\'\u2028\u2029'
html = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
template = pathlib.Path(sys.argv[2]).read_text(encoding="utf-8")
match = re.search(r"const DATA = (\{.*?\});\n/\*MIRADOR_DATA_END", html, re.S)
assert match, "rendered DATA payload missing"
payload = match.group(1)
decoded = json.loads(payload)
assert decoded["project"] == attack and decoded["readiness"]["title"] == attack
assert decoded["telemetry"]["effort"].startswith("</script><script>telemetry()")
for raw in ("<", ">", "&", "\u2028", "\u2029"):
    assert raw not in payload, f"raw script-context delimiter leaked: {raw!r}"
for escaped in (r"\u003c", r"\u003e", r"\u0026", r"\u2028", r"\u2029"):
    assert escaped in payload, f"missing HTML-safe JSON escape: {escaped}"
assert "globalThis.MIRADOR_PWNED" not in html.replace(payload, "")
assert ".innerHTML" not in template, "data-bearing innerHTML sink remains"
assert "insertAdjacentHTML" not in template and "document.write" not in template
print("P0-A ok: script-context JSON escaped and dynamic DOM rendering has no HTML sinks")
PY
  P0_A_STATUS=0
fi
# P0-A-END

if [ "${USCHA_P0_B_SKIP:-0}" != "1" ]; then
  if [ "${P0_B_STATUS:-1}" -eq 0 ]; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); fi
fi
if [ "${USCHA_P0_C_SKIP:-0}" != "1" ]; then
  if [ "${P0_C_STATUS:-1}" -eq 0 ]; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); fi
fi
if [ "${USCHA_P0_A_SKIP:-0}" != "1" ]; then
  if [ "${P0_A_STATUS:-1}" -eq 0 ]; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); fi
fi

# ---------------------------------------------------------------------------- #
# ACCEPTANCE EMISSION (kit 1.44.0) — uscha applied to itself.
# Runs the repo's own ACCEPTANCE.md criteria and writes the JUnit report the engine
# ingests. The evidence is captured BY EXECUTION here: nothing is hand-written, and a
# failing criterion is emitted as a <failure>, never quietly omitted. Additive only —
# it never changes the suite's PASS/FAIL or its exit code.
# ---------------------------------------------------------------------------- #
USCHA_ACC_OUT="$ROOT/reports/junit"   # raiz: NO entra al paquete npm (files: uscha-kit/)
mkdir -p "$USCHA_ACC_OUT"
ROOT="$ROOT" KIT="$KIT" ACC_OUT="$USCHA_ACC_OUT" SMOKE_FAIL="$FAIL" "$PY" <<'PYACC' || true
import filecmp, json, os, re, sys
root, kit, out = os.environ["ROOT"], os.environ["KIT"], os.environ["ACC_OUT"]
results = []  # (id, name, failure_message_or_None)


SKIP = object()   # criterion could not be measured (no source configured)


def check(ac, name, fn):
    try:
        msg = fn()
    except Exception as exc:                      # a broken check is a RED criterion,
        msg = f"check raised {type(exc).__name__}: {exc}"   # never a silent pass
    results.append((ac, name, msg))


def twins():
    a, b = os.path.join(kit, ".claude", "skills"), os.path.join(kit, "skills")
    def tree(base):
        found = {}
        for dp, dns, fns in os.walk(base):
            dns[:] = [d for d in dns if d != "__pycache__"]
            for fn in fns:
                p = os.path.join(dp, fn)
                found[os.path.relpath(p, base).replace("\\", "/")] = p
        return found
    ta, tb = tree(a), tree(b)
    only = sorted(set(ta) ^ set(tb))
    if only:
        return "files present in only one tree: " + ", ".join(only[:5])
    diff = [r for r in sorted(ta) if not filecmp.cmp(ta[r], tb[r], shallow=False)]
    return ("byte differences in: " + ", ".join(diff[:5])) if diff else None


def versions():
    v = [open(os.path.join(kit, "VERSION"), encoding="utf-8").read().split()[-1]]
    for rel in (("uscha.config.json",), (".claude-plugin", "plugin.json"),
                (".codex-plugin", "plugin.json")):
        v.append(json.load(open(os.path.join(kit, *rel), encoding="utf-8"))["version"])
    v.append(json.load(open(os.path.join(root, "package.json"), encoding="utf-8"))["version"])
    mk = json.load(open(os.path.join(root, ".claude-plugin", "marketplace.json"), encoding="utf-8"))
    v.append(mk["plugins"][0]["version"])
    if len(set(v)) != 1:
        return "version surfaces disagree: " + ", ".join(sorted(set(v)))
    if not os.path.isfile(os.path.join(kit, f"CHANGELOG-{v[0]}.md")):
        return f"missing CHANGELOG-{v[0]}.md"
    return None


def anonymous():
    # The names to hunt for are PRIVATE: hardcoding them here would publish, in a public
    # repo and inside the npm tarball, the very list this criterion exists to keep out.
    # They live in an untracked file instead (one name or regex per line, '#' comments).
    # No list -> the criterion is UNMEASURED, never a silent pass: absence is not success.
    names_file = os.path.join(root, ".uscha-private-names")
    names = []
    try:
        with open(names_file, encoding="utf-8") as fh:
            names = [ln.strip() for ln in fh
                     if ln.strip() and not ln.lstrip().startswith("#")]
    except OSError:
        pass
    if not names:
        return SKIP  # sentinel: emitted as <skipped/>, closes nothing
    pat = re.compile("|".join(names), re.I)
    # The list file is itself the one place the names legitimately live.
    self_file = os.path.abspath(__file__) if "__file__" in dir() else ""
    skip_files = {".uscha-private-names", os.path.basename(self_file)}
    hits = []
    for base in (kit, os.path.join(root, "README.md")):
        walk = [(os.path.dirname(base), [], [os.path.basename(base)])] if os.path.isfile(base) \
            else os.walk(base)
        for dp, dns, fns in walk:
            dns[:] = [d for d in dns if d not in ("__pycache__", ".git", "node_modules")]
            for fn in fns:
                if not fn.endswith((".md", ".py", ".sh", ".json", ".html", ".ps1")):
                    continue
                if fn in skip_files:
                    continue
                p = os.path.join(dp, fn)
                try:
                    if pat.search(open(p, encoding="utf-8", errors="ignore").read()):
                        hits.append(os.path.relpath(p, root).replace("\\", "/"))
                except OSError:
                    continue
    return ("client/private references in: " + ", ".join(sorted(hits)[:5])) if hits else None


def model_agnostic():
    src = open(os.path.join(kit, ".claude", "skills", "uscha-devloop", "qa_ledger.py"),
               encoding="utf-8").read()
    bad = [t for t in ("tokens_in", "tokens_out", "anthropic", "openai") if t in src]
    return ("engine reads vendor/token data: " + ", ".join(bad)) if bad else None


def doc_twins():
    d = os.path.join(root, "docs")
    html = [f for f in os.listdir(d) if f.endswith(".html")]
    missing = [f[:-5] + "-EN.html" for f in html
               if not f.endswith("-EN.html") and (f[:-5] + "-EN.html") not in html]
    return ("missing EN twin: " + ", ".join(sorted(missing))) if missing else None


def smoke_green():
    n = int(os.environ.get("SMOKE_FAIL", "1") or 0)
    return None if n == 0 else f"{n} smoke check(s) failed"


check("AC-01", "twins_byte_identical", twins)
check("AC-02", "version_surfaces_agree", versions)
check("AC-03", "no_client_references", anonymous)
check("AC-04", "engine_model_agnostic", model_agnostic)
check("AC-05", "doc_es_en_twins", doc_twins)
check("AC-06", "smoke_suite_green", smoke_green)

failed = sum(1 for _, _, m in results if m and m is not SKIP)
skipped = sum(1 for _, _, m in results if m is SKIP)
def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))
lines = ['<?xml version="1.0" encoding="UTF-8"?>',
         f'<testsuite name="uscha-acceptance" tests="{len(results)}" '
         f'failures="{failed}" errors="0" skipped="{skipped}">']
for ac, name, msg in results:
    lines.append(f'  <testcase classname="uscha.acceptance" name="{ac}_{name}">')
    if msg is SKIP:
        # UNMEASURED, on purpose: the engine counts a skipped testcase for neither
        # side, so the criterion stays open instead of turning green by default.
        lines.append('    <skipped message="no source configured for this criterion"/>')
    elif msg:
        lines.append(f'    <failure message="{esc(msg)}"/>')
    lines.append("  </testcase>")
lines.append("</testsuite>")
with open(os.path.join(out, "uscha-acceptance.xml"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")
print(f"ACCEPTANCE: {len(results) - failed - skipped}/{len(results)} criterios medidos en verde"
      + ("" if not skipped else " · SIN MEDIR: "
         + ", ".join(ac for ac, _, m in results if m is SKIP))
      + ("" if not failed else " · ROJO: "
         + ", ".join(ac for ac, _, m in results if m and m is not SKIP)))
PYACC

echo "== T85 (1.44.1): 'uscha init' is per-file, not all-or-nothing =="
T85=$(mktemp -d)
printf '# my own CLAUDE.md\n' > "$T85/CLAUDE.md"
# init exits 1 on a pending conflict BY DESIGN; guard so `set -e` (left on by the P0
# blocks above) does not abort the suite here.
T85_RC=0
"$PY" "$KIT/install-uscha.py" init --repo "$T85" --json >"$T85/out.json" 2>&1 || T85_RC=$?
T85_CHECK=0
T85_HOME="$T85" "$PY" -c "
import json, os, sys
h = os.environ['T85_HOME']
d = json.load(open(os.path.join(h, 'out.json'), encoding='utf-8'))
wrote = {os.path.basename(p) for p in d.get('wrote', [])}
conflicts = {os.path.basename(c['path']) for c in d['conflicts']}
# the non-conflicting files were written despite the CLAUDE.md conflict: config, the two
# other templates, the two statusline scripts, and the wired settings.json (kit 1.46.0)...
ok = (d['status'] == 'partial'
      and {'uscha.config.json', 'CONSTITUTION.md', '.gitattributes',
           'uscha_statusline.py', 'uscha_progress.py', 'settings.json'} <= wrote
      and conflicts == {'CLAUDE.md'}
      and os.path.isfile(os.path.join(h, 'CONSTITUTION.md'))
      and os.path.isfile(os.path.join(h, '.claude', 'scripts', 'uscha_statusline.py'))
      # ...and the user's own CLAUDE.md was left untouched
      and open(os.path.join(h, 'CLAUDE.md'), encoding='utf-8').read().strip() == '# my own CLAUDE.md')
sys.exit(0 if ok else 1)" || T85_CHECK=$?
rm -rf "$T85"
if [ "$T85_RC" -eq 1 ] && [ "$T85_CHECK" -eq 0 ]; then
  PASS=$((PASS+1)); echo "  ok   init writes the clean files, leaves the conflicting CLAUDE.md intact, exits 1"; \
else FAIL=$((FAIL+1)); echo "  FAIL init still all-or-nothing (rc=$T85_RC check=$T85_CHECK)"; fi

echo ""
printf 'RESULTADO: %s ok · %s fail\n' "$PASS" "$FAIL"
exit "${SMOKE_STATUS:-0}"
