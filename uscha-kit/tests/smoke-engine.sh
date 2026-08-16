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
# The version the suite asserts against is READ, never hardcoded (1.52.1). Pinning literals
# made every release edit six places in this file -- pure toll, zero safety: the real drift
# gate is T44 (the six surfaces must agree AND ship a CHANGELOG for that version), and it stays.
# Deriving does not weaken the version assertions either: install-uscha.py's source_version()
# reads this same file, so a literal was never proving the number -- only that someone
# remembered to retype it.
KIT_VERSION="$(awk 'NR==1{print $NF}' "$KIT/VERSION")"
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
  # Second choke point (D-03, 1.82.0): the statusline scripts and the mirador renderer
  # are invoked directly as "$PY" "$SCRIPT" ... (not through $QL), so run()'s --source
  # never sees them and coverage.py reports them as absent, not scored 0. runpy() mirrors
  # run() but takes the script path as its first argument and derives --source from that
  # SAME script's own directory (dirname), one absolute path per call -- not a fixed
  # multi-root constant. Two things ruled that out: coverage.py's --source is NOT
  # additive across repeated flags (the SECOND flag silently wins, dropping the first --
  # measured empirically, not assumed), and a comma-joined list has the same git-bash/MSYS
  # hazard as $COV_SRC above (only the FIRST embedded POSIX path gets rewritten). Deriving
  # the root from the script itself sidesteps both: every call is single-source.
  runpy() { local script="$1"; shift
            PYTHONIOENCODING=utf-8 "$PY" -m coverage run --parallel-mode \
              --source="$(dirname "$script")" "$script" "$@"; }
else
  run() { PYTHONIOENCODING=utf-8 "$PY" "$QL" "$@"; }
  runpy() { local script="$1"; shift; PYTHONIOENCODING=utf-8 "$PY" "$script" "$@"; }
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
run regression-check --repo repo-a --fixed 2 --diff fix-weak.diff 2>/dev/null | grep -q "WEAK evidence" \
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
run simplicity-check --diff simp-tiny.diff 2>/dev/null | grep -q "kit default" \
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
run phase --ledger L-fsm.json --repo fsm --require pr-ready 2>/dev/null | grep -q "ADR with the lessons" \
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
      and any(c['title'].startswith('project:') for c in d['checks'])
      and any(c['title'].startswith('ACCEPTANCE') and c['level'] == 'ok'
              for c in d['checks']))
sys.exit(0 if ok else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   doctor: full skill roster, per-project install, config and ACCEPTANCE read"; } \
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
run readiness 2>/dev/null | grep -q "rubric repo-a" \
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
run readiness --ledger L-ac.json 2>/dev/null | grep -- "--- gates:" | grep -q "none blocking" \
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
changelog = os.path.join(kit, 'CHANGELOG-%s.md' % v_file)   # derived from VERSION, never pinned
print('  versiones:', *versions)
sys.exit(0 if len(set(versions)) == 1 and os.path.isfile(changelog) else 1)" "$(dirname "$QL")" \
  && { PASS=$((PASS+1)); echo "  ok   las seis fuentes coinciden y existe CHANGELOG-$KIT_VERSION.md"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL drift de version o falta CHANGELOG-$KIT_VERSION.md"; }
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
run readiness --ledger L-fresh.json 2>/dev/null | grep -q "STALE JUnit report" \
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
"$PY" "$RENDER" --engine "$QL" --ledger L-intake.json --template "$TPL" --out exp-mir.html --no-open >/dev/null 2>&1
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
ok = (d['source_version'] == '$KIT_VERSION' and 'codex' in d['targets'] and 'claude' in d['targets'])
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
      json.load(open(manifest, encoding='utf-8'))['version'] == '$KIT_VERSION' and
      json.load(open(marker, encoding='utf-8'))['target'] == 'codex')
sys.exit(0 if ok else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   install codex crea plugin personal, marketplace y marker"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL install codex incompleto"; }
"$PY" "$KIT/install-uscha.py" doctor --target codex --home "$INST_HOME" --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
ok = (d['source_version'] == '$KIT_VERSION' and d['targets']['codex']['installed'] is True and d['targets']['codex']['version_match'] is True)
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
ok = (d['source_version'] == '$KIT_VERSION' and 'codex' in d['targets'] and 'claude' in d['targets'])
sys.exit(0 if ok else 1)" \
    && { PASS=$((PASS+1)); echo "  ok   npm router expone version/targets desde install-uscha.py"; } \
    || { FAIL=$((FAIL+1)); echo "  FAIL npm router no delega correctamente al installer"; }
else
  FAIL=$((FAIL+1)); echo "  FAIL node no esta disponible para probar el router npm"
fi
if command -v npm >/dev/null 2>&1; then
  (cd "$ROOT" && npm_config_cache="$SB/npm-cache" npm pack --dry-run --json 2>/dev/null) | "$PY" -c "
import json, sys
# npm's --json shape is not a stable contract across majors: a list under npm 11, and
# something else under npm@latest in the publish job (which upgrades npm because trusted
# publishing requires >= 11.5.1). Accept both, and NAME an unknown shape instead of dying
# with a KeyError that says nothing -- npm also emits an error OBJECT here on failure.
raw = json.load(sys.stdin)
if isinstance(raw, list) and raw:
    d = raw[0]
elif isinstance(raw, dict) and 'files' in raw:
    d = raw
elif isinstance(raw, dict) and len(raw) == 1 and isinstance(list(raw.values())[0], dict):
    d = list(raw.values())[0]   # npm 12: an object KEYED BY PACKAGE NAME
else:
    keys = sorted(raw)[:6] if isinstance(raw, dict) else type(raw).__name__
    print('npm pack --json returned an unexpected shape: %s' % (keys,), file=sys.stderr)
    sys.exit(1)
files = {f['path'] for f in d['files']}
ok = (d['name'] == '@andresmassello/uscha' and d['version'] == '$KIT_VERSION'
      and 'bin/uscha.js' in files and 'uscha-kit/install-uscha.py' in files
      and '.atl/skill-registry.md' not in files and 'handoff.md' not in files and 'mirador.html' not in files
      and not any('__pycache__' in f or f.endswith(('.pyc', '.pyo')) for f in files)
      # 1.51.3: the 70 historical per-release changelogs are repo archive, not payload --
      # they were 55% of the tarball's FILES and nothing in an install reads them.
      # anchored to the same shape the package.json glob excludes, so a future file that merely
      # CONTAINS the substring elsewhere in the kit cannot false-fail this check
      and not any(f.startswith('uscha-kit/CHANGELOG-') for f in files)
      # positive controls, so trimming can never quietly gut the actual payload: the skills
      # (what the agent reads) and the templates (what 'uscha init' emits) must still ship.
      # NOTE: no backticks in this block -- it lives inside a double-quoted shell string,
      # where a backtick would run command substitution and silently truncate the code.
      and 'uscha-kit/.claude/skills/uscha-devloop/SKILL.md' in files
      and 'uscha-kit/skills/uscha-devloop/SKILL.md' in files
      and 'uscha-kit/templates/CONSTITUTION.md' in files
      and 'uscha-kit/README.md' in files)
sys.exit(0 if ok else 1)" \
    && { PASS=$((PASS+1)); echo "  ok   npm pack: router/kit/skills/templates si, changelogs y artefactos locales no"; } \
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

echo "== T79 (1.51.2): auto-open fires on FIRST materialization only -- re-renders reuse one self-refreshing tab =="
T79_RES="$("$PY" - "$KIT/.claude/skills/uscha-mirador/mirador-render.py" "$KIT/.claude/skills/uscha-mirador/mirador.template.html" <<'PY'
import importlib.util, os, pathlib, shutil, sys, tempfile
render_path, tpl = sys.argv[1], sys.argv[2]
spec = importlib.util.spec_from_file_location("mr", render_path)
mr = importlib.util.module_from_spec(spec); spec.loader.exec_module(mr)
tmp = pathlib.Path(tempfile.mkdtemp())
eng = tmp / "eng.py"
eng.write_text('import sys; sys.stdout.write(\'{"readiness":{"score":22,"band":"NOT READY","title":"x"}}\')\n', encoding="utf-8")
opens = {"n": 0}
mr._open_best_effort = lambda p: opens.__setitem__("n", opens["n"] + 1)
_real_stdout = sys.stdout           # silence the renderer's chatter so only the verdict is captured
sys.stdout = open(os.devnull, "w")
def run(out, extra):
    sys.argv = ["mirador-render.py", "--engine", str(eng), "--ledger", str(tmp / "L.json"),
                "--template", tpl, "--out", str(out), "--sidecar", str(tmp / "none.jsonl")] + extra
    return mr.main()
m1 = tmp / "m1.html"
b = opens["n"]; run(m1, []); first = opens["n"] - b               # fresh file -> materialize -> open once
b = opens["n"]; run(m1, []); again = opens["n"] - b               # exists -> re-render, NO reopen (anti-spam)
b = opens["n"]; run(m1, ["--open"]); forced = opens["n"] - b      # --open forces a reopen (tab was closed)
b = opens["n"]; run(m1, ["--no-open", "--open"]); wins = opens["n"] - b  # --no-open beats --open
# --no-open must suppress on a GENUINELY FRESH file too -- on an existing one `pre_existed`
# alone would suppress, so that assertion could pass with the no_open check deleted.
m4 = tmp / "m4.html"
b = opens["n"]; run(m4, ["--no-open"]); noopen_fresh = opens["n"] - b
m2 = tmp / "m2.html"
b = opens["n"]; run(m2, ["--refresh", "30"]); liverefresh = opens["n"] - b  # open gated by EXISTENCE, not --refresh
default_refresh = 'http-equiv="refresh" content="10"' in m1.read_text(encoding="utf-8")
m3 = tmp / "m3.html"; run(m3, ["--refresh", "0", "--no-open"]); frozen = 'http-equiv="refresh"' not in m3.read_text(encoding="utf-8")
shutil.rmtree(tmp, ignore_errors=True)
sys.stdout = _real_stdout
print("OK" if (first == 1 and again == 0 and forced == 1 and wins == 0 and noopen_fresh == 0
               and liverefresh == 1 and default_refresh and frozen) else
      "BAD first=%s again=%s forced=%s wins=%s noopen_fresh=%s liverefresh=%s default_refresh=%s frozen=%s"
      % (first, again, forced, wins, noopen_fresh, liverefresh, default_refresh, frozen))
PY
)"
if [ "$T79_RES" = "OK" ]; then PASS=$((PASS+1)); echo "  ok   first=1 open, re-render=0 (one self-refreshing tab), --open forces, --no-open wins (fresh too), --refresh 0 frozen"; \
else FAIL=$((FAIL+1)); echo "  FAIL $T79_RES"; fi

echo "== T80 (1.42.0): mirador status story (como viene/que lo traba/que sigue) present + fed by the ledger =="
printf '{ "defaults": { "acceptance_file": "ACCEPTANCE.md" }, "repos": [ {"name":"solo","path":"repo-c","type":"python"} ], "integration": {"enabled": false} }\n' > status-cfg.json
run init --config status-cfg.json --out L-status.json >/dev/null 2>&1
run log-gate --repo solo --iteration 1 --kind simplicity --verdict fail --count 3 --ledger L-status.json >/dev/null 2>&1
runpy "$KIT/.claude/skills/uscha-mirador/mirador-render.py" --engine "$QL" --ledger L-status.json \
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
CLAUDE_PROJECT_DIR="$T88" runpy "$KIT/templates/scripts/uscha_progress.py"
T88_RENDER=$(echo '{}' | CLAUDE_PROJECT_DIR="$T88" runpy "$KIT/templates/scripts/uscha_statusline.py" | sed 's/\x1b\[[0-9;]*m//g')
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
T88_EMPTY=$(echo '{}' | CLAUDE_PROJECT_DIR="$T88" runpy "$KIT/templates/scripts/uscha_statusline.py")
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
  CLAUDE_PROJECT_DIR="$(pwd)" runpy "$KIT/templates/scripts/uscha_progress.py"
  before=$("$PY" -c "import json;s=json.load(open('.claude/uscha-progress.json'));print('%s/%s'%(s['done'],s['total']))")
  run readiness --ledger QA-LEDGER.json --record >/dev/null 2>&1   # persist ledger['measured']
  CLAUDE_PROJECT_DIR="$(pwd)" runpy "$KIT/templates/scripts/uscha_progress.py"
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
  CLAUDE_PROJECT_DIR="$(pwd)" runpy "$KIT/templates/scripts/uscha_progress.py"
  tok=$("$PY" -c "import json;s=json.load(open('.claude/uscha-progress.json'));print('%s/%s'%(s['phase'],s['loops']))")
  line=$(CLAUDE_PROJECT_DIR="$(pwd)" runpy "$KIT/templates/scripts/uscha_statusline.py" < /dev/null)
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
  CLAUDE_PROJECT_DIR="$(pwd)" runpy "$KIT/templates/scripts/uscha_progress.py"
  src=$("$PY" -c "import json;print(json.load(open('.claude/uscha-progress.json'))['acceptance_source'])")
  line=$(CLAUDE_PROJECT_DIR="$(pwd)" runpy "$KIT/templates/scripts/uscha_statusline.py" < /dev/null)
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
    # a QUOTED path (list2cmdline/shlex wrap a profile dir with a space) -- the prune must
    # still catch it despite the trailing quote (the substring, not suffix, match)
    {"matcher": "*", "hooks": [{"type": "command",
     "command": "\"C:/Users/John Doe/.claude/hooks/block-approved-writes.py\""}]},
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

echo "== T101 (1.51.0): the pi target installs skills to ~/.agents/skills, doctor measures it =="
# pi (Earendil) is a third install target: the 9 skills land flat under ~/.agents/skills (the
# harness-neutral sibling of codex's ~/.agents/plugins), with a marker so doctor can measure
# presence/version. `--target all` covers all three; `both` stays the legacy codex+claude alias.
T101H="$(mktemp -d)"
python "$KIT/install-uscha.py" install --target pi --home "$T101H" >/dev/null 2>&1
T101=$("$PY" - "$KIT" "$T101H" <<'PY'
import importlib.util, json, os, subprocess, sys
kit, home = sys.argv[1], sys.argv[2]
sk = os.path.join(home, ".agents", "skills")
present = sum(1 for d in os.listdir(sk) if d.startswith("uscha-")
              and os.path.isfile(os.path.join(sk, d, "SKILL.md"))) if os.path.isdir(sk) else 0
marker = os.path.isfile(os.path.join(sk, "uscha-install.json"))
def doc(h):
    r = subprocess.run([sys.executable, os.path.join(kit, "install-uscha.py"),
                        "doctor", "--target", "pi", "--home", h, "--json"],
                       stdout=subprocess.PIPE, text=True)
    return json.loads(r.stdout)["targets"]["pi"]
pi_status = doc(home)
healthy = pi_status["healthy"]
# golden_guard: pi is ADVISORY (the tool_call extension ships but its block is not measured here)
pi_guard = pi_status.get("golden_guard")
empty = os.path.join(home, "empty"); os.makedirs(empty, exist_ok=True)
unhealthy = doc(empty)["healthy"]        # a home with no install must read unhealthy
# a Claude install reports golden_guard ENFORCED (the PreToolUse hook is registered)
ch = os.path.join(home, "claudehome"); os.makedirs(ch, exist_ok=True)
subprocess.run([sys.executable, os.path.join(kit, "install-uscha.py"),
                "install", "--target", "claude", "--home", ch], stdout=subprocess.DEVNULL)
r = subprocess.run([sys.executable, os.path.join(kit, "install-uscha.py"),
                    "doctor", "--target", "claude", "--home", ch, "--json"],
                   stdout=subprocess.PIPE, text=True)
cl_guard = json.loads(r.stdout)["targets"]["claude"]["golden_guard"]
ext = os.path.isfile(os.path.join(kit, "pi", "golden-guard.js"))  # the extension artifact ships
# `all` lists pi; `both` does not (legacy)
spec = importlib.util.spec_from_file_location("iu", os.path.join(kit, "install-uscha.py"))
iu = importlib.util.module_from_spec(spec); spec.loader.exec_module(iu)
ok = (present == 9 and marker and healthy is True and unhealthy is False
      and pi_guard == "advisory" and cl_guard == "enforced" and ext
      # scoped to pi: `all` must INCLUDE it, `both` must not. Pinning the whole list here made
      # this test break every time a target was added -- that roster is T107's subject (1.53.0).
      and "pi" in iu.selected_targets("all")
      and iu.selected_targets("both") == ["codex", "claude"])
print("OK" if ok else "BAD present=%s marker=%s healthy=%s unhealthy=%s pi_guard=%s cl_guard=%s ext=%s"
      % (present, marker, healthy, unhealthy, pi_guard, cl_guard, ext))
PY
)
rm -rf "$T101H"
if [ "$T101" = "OK" ]; then
  PASS=$((PASS+1)); echo "  ok   pi: 9 skills + marker; doctor healthy/unhealthy; golden_guard pi=advisory claude=enforced; all vs both"; \
else FAIL=$((FAIL+1)); echo "  FAIL $T101"; fi

echo "== T102 (1.51.x): no case-only filename collisions (macOS/Windows case-insensitive vs Linux) =="
# The ONE difference between the Linux and macOS CI cells: Linux is case-sensitive, macOS
# (and Windows) are not. Two tracked files whose paths differ ONLY by case both exist on
# Linux but clobber each other on a macOS/Windows checkout -- a green Linux repo that breaks
# elsewhere. Lowercasing every repo path and looking for duplicates catches it on all three.
T102_DUPS="$(find "$ROOT" -type f \
  -not -path '*/.git/*' -not -path '*/.npm-cache/*' -not -path '*/node_modules/*' \
  -not -path '*/__pycache__/*' -not -path '*/.coverage-data/*' \
  | tr 'A-Z' 'a-z' | sort | uniq -d | head -5)"
if [ -z "$T102_DUPS" ]; then
  PASS=$((PASS+1)); echo "  ok   zero case-only path collisions across the tree (safe on case-insensitive filesystems)"; \
else FAIL=$((FAIL+1)); echo "  FAIL case-only collisions: $T102_DUPS"; fi

echo "== T113 (1.57.0): fastpath-eval -- measured ALLOW/DENY, escalation, fail-closed (ADR-003) =="
# Each sub-case maps 1:1 to an AC-FP criterion in ACCEPTANCE.md. Results land in a sidecar the
# acceptance block reads, so every criterion closes on its OWN named testcase instead of one
# opaque aggregate. The golden (AC-FP-08) compares the CURRENT engine against the anchor
# captured BEFORE this feature existed; without a human-approved anchor it reports null ->
# emitted as skipped, never as a silent pass.
rm -f "$KIT/reports/junit/.fastpath-cases.json"   # a stale green sidecar must never survive a crashed T113
rm -f "$KIT/reports/junit/.specdrift-cases.json"  # same rule for T114
rm -f "$KIT/reports/junit/.goldencov-cases.json"  # same rule for T117
rm -f "$KIT/reports/junit/.origin-cases.json"     # same rule for T118
rm -f "$KIT/reports/junit/.cleanroom-cases.json"  # same rule for T119
rm -f "$KIT/reports/junit/.curation-cases.json"   # same rule for T120
rm -f "$KIT/reports/junit/.oracle-cases.json"     # same rule for T121
rm -f "$KIT/reports/junit/.facts-cases.json"      # same rule for T122
rm -f "$KIT/reports/junit/.delta-cases.json"      # same rule for T123
rm -f "$KIT/reports/junit/.fidelity-cases.json"   # same rule for T124
rm -f "$KIT/reports/junit/.ir-cases.json"         # same rule for T125
rm -f "$KIT/reports/junit/.compile-cases.json"    # same rule for T126
rm -f "$KIT/reports/junit/.bootstrap-cases.json"  # same rule for T127
rm -f "$KIT/reports/junit/.bench-cases.json"      # same rule for T128
rm -f "$KIT/reports/junit/.lang-cases.json"       # same rule for T129
rm -f "$KIT/reports/junit/.bench-curate-cases.json"  # same rule for T130
rm -f "$KIT/reports/junit/.lang3-cases.json"      # same rule for T131
rm -f "$KIT/reports/junit/.sched-cases.json"      # same rule for T132
rm -f "$KIT/reports/junit/.r2-cases.json"         # same rule for T133
T113=$("$PY" - "$KIT" "$ROOT" <<'PY'
import io, json, os, subprocess, sys, tempfile
kit, root = sys.argv[1], sys.argv[2]
ENG = os.path.join(kit, ".claude", "skills", "uscha-devloop", "qa_ledger.py")
res = {}
w = tempfile.mkdtemp(); repo = os.path.join(w, "r"); os.makedirs(repo)
def sh(*a, cwd=repo):
    return subprocess.run(list(a), cwd=cwd, capture_output=True, text=True)
sh("git", "init", "-b", "main"); sh("git", "config", "user.email", "t@t"); sh("git", "config", "user.name", "t")
io.open(os.path.join(repo, "a.py"), "w").write("x=1\n")
sh("git", "add", "-A"); sh("git", "commit", "-m", "base")
sh("git", "checkout", "-b", "feat")
io.open(os.path.join(repo, "a.py"), "w").write("x=1\ny=2\n")
cfg = {"defaults": {"acceptance_file": "ACCEPTANCE.md", "fast_path": {"enabled": True}},
       "repos": [{"name": "r", "path": "r", "type": "python"}], "integration": {"enabled": False}}
io.open(os.path.join(w, "c.json"), "w").write(json.dumps(cfg))
def eng(*a):
    return subprocess.run([sys.executable, ENG] + list(a), cwd=w, capture_output=True, text=True)
eng("init", "--config", "c.json", "--out", "L.json")

r = eng("fastpath-eval", "--ledger", "L.json", "--repo", "r", "--json"); d = json.loads(r.stdout)
res["AC-FP-01"] = d["verdict"] == "ALLOW" and r.returncode == 0
L = json.load(open(os.path.join(w, "L.json")))
res["AC-FP-11"] = bool(d.get("dry_run")) and not L.get("fast_path")

r = eng("fastpath-eval", "--ledger", "L.json", "--repo", "r", "--intent", "fix: y", "--json")
d = json.loads(r.stdout)
L = json.load(open(os.path.join(w, "L.json"))); e = L["fast_path"][-1]
res["AC-FP-07"] = (d["verdict"] == "ALLOW" and e["mode"] == "fast_path" and e["intent"] == "fix: y"
                   and all(k in s for s in e["signals"] for k in ("value", "threshold", "source", "at")))
r = eng("readiness", "--ledger", "L.json", "--json"); dd = json.loads(r.stdout)
res["AC-FP-06"] = (dd.get("score", 100) or 0) <= 75

io.open(os.path.join(repo, "big.py"), "w").write("\n".join("l%d=%d" % (i, i) for i in range(100)) + "\n")
r = eng("fastpath-eval", "--ledger", "L.json", "--repo", "r", "--intent", "same", "--json")
d = json.loads(r.stdout)
L = json.load(open(os.path.join(w, "L.json")))
pr = eng("phase", "--ledger", "L.json", "--repo", "r", "--require", "pr-ready")
res["AC-FP-05"] = (d["verdict"] == "ESCALATED" and len(L["fast_path"]) == 2
                   and any(not x.get("resolved_at") for x in L["escalations"])
                   and pr.returncode == 1)
os.remove(os.path.join(repo, "big.py")); sh("git", "checkout", "--", ".")

sh("git", "checkout", "main"); sh("git", "checkout", "-b", "f81")
io.open(os.path.join(repo, "c81.py"), "w").write("\n".join("v%d=%d" % (i, i) for i in range(81)) + "\n")
r = eng("fastpath-eval", "--ledger", "L.json", "--repo", "r", "--json"); d = json.loads(r.stdout)
bad = [s["name"] for s in d["signals"] if not s["ok"]]
res["AC-FP-02"] = d["verdict"] == "DENY" and "max_loc_delta" in bad
os.remove(os.path.join(repo, "c81.py"))

os.makedirs(os.path.join(repo, "db"), exist_ok=True)
io.open(os.path.join(repo, "db", "m.sql"), "w").write("select 1;\n")
r = eng("fastpath-eval", "--ledger", "L.json", "--repo", "r", "--json"); d = json.loads(r.stdout)
bad = [s["name"] for s in d["signals"] if not s["ok"]]
res["AC-FP-03"] = d["verdict"] == "DENY" and "protected_paths" in bad
import shutil; shutil.rmtree(os.path.join(repo, "db"))

r = eng("fastpath-eval", "--ledger", "L.json", "--repo", "r", "--force-allow")
res["AC-FP-09"] = r.returncode == 2

w2 = tempfile.mkdtemp(); os.makedirs(os.path.join(w2, "r"))
io.open(os.path.join(w2, "c.json"), "w").write(json.dumps(cfg))
def eng2(*a):
    return subprocess.run([sys.executable, ENG] + list(a), cwd=w2, capture_output=True, text=True)
eng2("init", "--config", "c.json", "--out", "L.json")
r = eng2("fastpath-eval", "--ledger", "L.json", "--repo", "r", "--json"); d = json.loads(r.stdout)
res["AC-FP-10"] = d["verdict"] == "DENY" and d["signals"][0]["name"] == "base_ref"

# AC-FP-08: current engine vs the pre-feature anchor. Needs the human-approved golden.
gold_dir = os.path.join(root, "tests", "golden")
approved = os.path.join(gold_dir, "devloop-entry.appro" + "ved.json")
harness = os.path.join(gold_dir, "harness-devloop-entry.py")
if os.path.isfile(approved) and os.path.isfile(harness):
    subprocess.run([sys.executable, harness], capture_output=True, text=True)
    received = io.open(os.path.join(gold_dir, "devloop-entry.received.json"), encoding="utf-8").read()
    res["AC-FP-08"] = received == io.open(approved, encoding="utf-8").read()
else:
    res["AC-FP-08"] = None   # UNMEASURED until a human approves the anchor

side = os.path.join(kit, "reports", "junit")
os.makedirs(side, exist_ok=True)
io.open(os.path.join(side, ".fastpath-cases.json"), "w", encoding="utf-8").write(json.dumps(res))
bad = [k for k, v in res.items() if v is False]
unm = [k for k, v in res.items() if v is None]
print("OK %d cases%s" % (sum(1 for v in res.values() if v),
      (" (unmeasured: " + ",".join(unm) + ")") if unm else "")
      if not bad else "BAD " + ",".join(bad))
PY
)
case "$T113" in
  OK*) PASS=$((PASS+1)); echo "  ok   fastpath-eval: $T113";;
  *)   FAIL=$((FAIL+1)); echo "  FAIL $T113";;
esac

echo "== T114 (1.58.0): spec-drift -- advisory drift from commit dates, never a gate (ADR-005) =="
# Each sub-case maps 1:1 to an AC-SD criterion. Fixture commit dates are pinned via
# GIT_AUTHOR_DATE/GIT_COMMITTER_DATE so the lag math is deterministic on every runner.
T114=$("$PY" - "$KIT" <<'PY'
import io, json, os, subprocess, sys, tempfile
kit = sys.argv[1]
ENG = os.path.join(kit, ".claude", "skills", "uscha-devloop", "qa_ledger.py")
res = {}
w = tempfile.mkdtemp(); repo = os.path.join(w, "r")
os.makedirs(os.path.join(repo, "src")); os.makedirs(os.path.join(repo, "docs", "adr"))

def sh(args, when=None, cwd=repo):
    env = dict(os.environ)
    if when:
        env["GIT_AUTHOR_DATE"] = when; env["GIT_COMMITTER_DATE"] = when
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, env=env)

sh(["git", "init", "-b", "main"]); sh(["git", "config", "user.email", "t@t"])
sh(["git", "config", "user.name", "t"])
io.open(os.path.join(repo, "SPEC.md"), "w").write("---\ngoverns:\n  - src/**\n---\n# spec\n")
io.open(os.path.join(repo, "docs", "adr", "ADR-001-a.md"), "w").write("no frontmatter\n")
io.open(os.path.join(repo, "docs", "adr", "ADR-002-b.md"), "w").write(
    "---\ngoverns: []\n---\n# a negative decision\n")
io.open(os.path.join(repo, "src", "a.py"), "w").write("x=1\n")
sh(["git", "add", "-A"]); sh(["git", "commit", "-m", "one"], when="2026-01-01T00:00:00Z")
io.open(os.path.join(repo, "src", "a.py"), "w").write("x=2\n")
sh(["git", "add", "-A"]); sh(["git", "commit", "-m", "two"], when="2026-03-01T00:00:00Z")

cfg = {"defaults": {"acceptance_file": "ACCEPTANCE.md"},
       "repos": [{"name": "r", "path": "r", "type": "python"}], "integration": {"enabled": False}}
io.open(os.path.join(w, "c.json"), "w").write(json.dumps(cfg))
def eng(*a):
    return subprocess.run([sys.executable, ENG] + list(a), cwd=w, capture_output=True, text=True)
eng("init", "--config", "c.json", "--out", "L.json")

# readiness BEFORE any drift run -- AC-SD-04 compares numerically after.
r = eng("readiness", "--ledger", "L.json", "--json"); before = json.loads(r.stdout).get("score")

# AC-SD-01: src/a.py moved 59 days after the spec, default lag 30 -> SPEC_STALE, file listed,
# and the command still exits 0 (advisory NEVER gates).
r = eng("spec-drift", "--ledger", "L.json", "--repo", "r", "--json"); d = json.loads(r.stdout)
rows = {x["file"]: x for x in d["results"]}
spec = rows.get("SPEC.md", {})
res["AC-SD-01"] = (r.returncode == 0 and spec.get("verdict") == "SPEC_STALE"
                   and "src/a.py" in spec.get("newer_files", []))

# AC-SD-03: the ADR without frontmatter is UNMAPPED -- visibly distinct from clean.
adr = rows.get("docs/adr/ADR-001-a.md", {})
res["AC-SD-03"] = adr.get("verdict") == "UNMAPPED" and adr.get("verdict") != "CLEAN"

# AC-SD-05: an EXPLICIT empty governs list is a declaration, not an omission. A negative ADR
# governs no code and never will; reporting it UNMAPPED forever is how an advisory becomes
# noise and gets ignored. Must be distinct from BOTH other verdicts.
neg = rows.get("docs/adr/ADR-002-b.md", {})
res["AC-SD-05"] = (neg.get("verdict") == "NO-CODE"
                   and neg.get("verdict") != adr.get("verdict")
                   and neg.get("verdict") != "CLEAN")

# AC-SD-02: commit the spec AFTER the governed change -> no advisory.
io.open(os.path.join(repo, "SPEC.md"), "a").write("updated\n")
sh(["git", "add", "-A"]); sh(["git", "commit", "-m", "spec refresh"], when="2026-04-01T00:00:00Z")
r = eng("spec-drift", "--ledger", "L.json", "--repo", "r", "--json"); d = json.loads(r.stdout)
rows = {x["file"]: x for x in d["results"]}
res["AC-SD-02"] = r.returncode == 0 and rows.get("SPEC.md", {}).get("verdict") == "CLEAN"

# AC-SD-04: the advisory is in the ledger AND the readiness score is numerically unchanged.
L = json.load(open(os.path.join(w, "L.json")))
r = eng("readiness", "--ledger", "L.json", "--json"); after = json.loads(r.stdout).get("score")
res["AC-SD-04"] = bool(L.get("spec_drift")) and before == after

# dashboard passthrough: key present now, absent on a virgin ledger (schema stability).
r = eng("dashboard", "--ledger", "L.json", "--json"); has = "spec_drift" in json.loads(r.stdout)
eng("init", "--config", "c.json", "--out", "L2.json")
r = eng("dashboard", "--ledger", "L2.json", "--json"); virgin = "spec_drift" in json.loads(r.stdout)
dash_ok = has and not virgin

side = os.path.join(kit, "reports", "junit")
os.makedirs(side, exist_ok=True)
io.open(os.path.join(side, ".specdrift-cases.json"), "w", encoding="utf-8").write(json.dumps(res))
bad = [k for k, v in res.items() if not v] + ([] if dash_ok else ["dashboard-passthrough"])
print("OK %d cases" % len(res) if not bad else "BAD " + ",".join(bad))
PY
)
case "$T114" in
  OK*) PASS=$((PASS+1)); echo "  ok   spec-drift: $T114";;
  *)   FAIL=$((FAIL+1)); echo "  FAIL $T114";;
esac

echo "== T115 (1.59.0): mirador template draws the modes card (fast-path + spec-drift) =="
# Structural regression guard: the card, its renderer, the init call, the conditional
# hidden state and the advisory label must all survive template edits. Behavior was
# verified in a real browser at authoring time; CI has no DOM, so structure is the
# honest cheap proxy (a missing piece here IS a dropped panel).
T115=$("$PY" - "$KIT/.claude/skills/uscha-mirador/mirador.template.html" <<'PY'
import io, sys
t = io.open(sys.argv[1], encoding="utf-8").read()
bad = []
if "id=\x22card-modes\x22 hidden" not in t: bad.append("card-modes markup (hidden by default)")
if "function renderModes()" not in t: bad.append("renderModes definition")
if "renderModes();" not in t.split("/* ==== init ==== */")[-1]: bad.append("renderModes init call")
if "if(!fp&&!sd&&!cr){card.hidden=true;return;}" not in t: bad.append("conditional degradation")
# extract the renderModes body FIRST; no quotes may sit inside bracket expressions here
# (the documented bash 3.2 heredoc-in-substitution trap), hence chr() and two-step slicing.
start = t.index("function renderModes()")
js = t[start:]
cut = js.find(chr(10) + chr(125))
js = js[:cut] if cut > 0 else js
# verdict map checked INSIDE the renderer body, so a whole-file match cannot false-pass it
for v in ("SPEC_STALE", "UNMAPPED", "UNTRACKED", "ESCALATED", "clean-room"):
    if v not in js: bad.append("verdict class map: " + v)
if "ADVISORY (ADR-005)" not in js: bad.append("advisory label")
if "innerHTML" in js or "insertAdjacentHTML" in js: bad.append("HTML sink in renderModes")
print("OK modes card wired" if not bad else "BAD " + "; ".join(bad))
PY
)
case "$T115" in
  OK*) PASS=$((PASS+1)); echo "  ok   mirador modes card: $T115";;
  *)   FAIL=$((FAIL+1)); echo "  FAIL $T115";;
esac

echo "== T116 (repo infra): the publish workflow stays tokenless, pinned and gated =="
# This is the most dangerous file in the repo: it can push bytes to everyone who installs
# the package. Trusted publishing removes the token, but nothing stops a later edit from
# adding one back, unpinning an action, or moving the publish step ABOVE the test step.
# Structure is checkable, so it gets checked.
T116=$("$PY" - "$ROOT/.github/workflows/publish.yml" <<'PY'
import io, os, re, sys
p = sys.argv[1]
if not os.path.isfile(p):
    print("BAD publish workflow missing")
    raise SystemExit
t = io.open(p, encoding="utf-8").read()
bad = []
# Check the EXECUTABLE content, never the prose: this workflow explains in comments what it
# refuses to do (NODE_AUTH_TOKEN, the old npm publish by hand), and a raw-text scan reads
# those explanations as the thing itself. First version of this test did exactly that and
# failed a correct file -- the same false-match class a fresh review caught in T115.
lines = []
for ln in t.splitlines():
    if ln.lstrip().startswith("#"):
        continue
    lines.append(ln.split(" #")[0].rstrip() if " #" in ln else ln)
code = "\n".join(lines)
# a token would defeat the entire point -- and would be a real credential in a public repo
# chr(36) instead of a literal: an unescaped ${ inside a heredoc-in-$() makes bash 3.2 (macOS)
# start a parameter expansion while hunting for the closing paren, lose track of where the
# heredoc ends, and parse the next Python line as a command. Caught by the macOS CI cell --
# bash 4/5 (Linux, git-bash) parse it fine, so it is invisible locally. Same family as the
# quote-in-character-class trap CLAUDE.md already records.
if chr(36) + "{{ secrets." in code: bad.append("references a secret (trusted publishing needs none)")
if "NODE_AUTH_TOKEN" in code: bad.append("sets NODE_AUTH_TOKEN")
# OIDC needs id-token: write; anything more is privilege this job has no use for
if "id-token: write" not in code: bad.append("no id-token: write (OIDC cannot mint)")
if re.search(r"contents:\s*write", code): bad.append("contents: write (only read is needed)")
# a moving tag can be repointed at new code by whoever controls the action
for ref in re.findall(r"uses:\s*(\S+)", code):
    if not re.search(r"@[0-9a-f]{40}$", ref): bad.append("unpinned action: " + ref)
# fail-closed: an undeclared or disagreeing version must never publish
if "REFUSING TO PUBLISH" not in code: bad.append("no tag-vs-version guard")
# and the bytes must be measured BEFORE they leave, not after
i_smoke, i_pub = code.find("smoke-engine.sh"), code.find("npm publish")
if i_smoke < 0: bad.append("does not run the smoke suite")
elif i_pub < 0: bad.append("no publish step")
elif i_smoke > i_pub: bad.append("publishes BEFORE running the suite")
print("OK publish workflow tokenless + pinned + gated" if not bad else "BAD " + "; ".join(bad))
PY
)
case "$T116" in
  OK*) PASS=$((PASS+1)); echo "  ok   publish workflow: $T116";;
  *)   FAIL=$((FAIL+1)); echo "  FAIL $T116";;
esac

echo "== T117 (1.60.0): golden-coverage -- measured mapping + the opt-in veto (ADR-006) =="
# Consumption (the veto signal) needs only a manifest, so most criteria run everywhere with a
# hand-written one -- which is also the strict loader's real input. PRODUCTION needs a real
# coverage.py; without it AC-GM-08 reports null and is emitted as skipped, never as a pass.
T117=$("$PY" - "$KIT" <<'PY'
import io, json, os, subprocess, sys, tempfile
kit = sys.argv[1]
ENG = os.path.join(kit, ".claude", "skills", "uscha-devloop", "qa_ledger.py")
res = {}
w = tempfile.mkdtemp(); repo = os.path.join(w, "r"); os.makedirs(repo)

def sh(args, cwd=repo, env=None):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, env=env)

sh(["git", "init", "-b", "main"]); sh(["git", "config", "user.email", "t@t"])
sh(["git", "config", "user.name", "t"])
io.open(os.path.join(repo, "lib.py"), "w").write("VALUE = 1\nprint(VALUE)\n")
io.open(os.path.join(repo, "other.py"), "w").write("UNTOUCHED = 2\n")
# the harness drives its subject through a SUBPROCESS -- the boundary a parent-only
# instrumentation cannot see, which is the whole reason the sitecustomize injection exists
io.open(os.path.join(repo, "h.py"), "w").write(
    "import os, subprocess, sys\n"
    "here = os.path.dirname(os.path.abspath(__file__))\n"
    "subprocess.run([sys.executable, os.path.join(here, 'lib.py')], check=True)\n")
GOLD = "g.appro" + "ved.json"
GOLD2 = "g2.appro" + "ved.json"
# the goldens must EXIST: the veto enumerates the tree, so a manifest that knows only some
# of them must deny rather than assert "nothing is covered" about one it never measured
io.open(os.path.join(repo, GOLD), "w").write("{}")
io.open(os.path.join(repo, GOLD2), "w").write("{}")
sh(["git", "add", "-A"]); sh(["git", "commit", "-m", "base"])
sh(["git", "checkout", "-b", "feat"])
def cfg(veto):
    fp = {"enabled": True}
    if veto:
        fp["forbid_when_golden_touched"] = True
    return {"defaults": {"acceptance_file": "ACCEPTANCE.md", "fast_path": fp},
            "repos": [{"name": "r", "path": "r", "type": "python"}],
            "integration": {"enabled": False}}

def eng(*a):
    return subprocess.run([sys.executable, ENG] + list(a), cwd=w,
                          capture_output=True, text=True)

def evaluate(veto, ledger):
    io.open(os.path.join(w, "c.json"), "w").write(json.dumps(cfg(veto)))
    eng("init", "--config", "c.json", "--out", ledger)
    r = eng("fastpath-eval", "--ledger", ledger, "--repo", "r", "--json")
    return json.loads(r.stdout), r.returncode

def manifest(files, commit="abc12345deadbeef", tool="coverage.py 7.9.9",
             only_first=False):
    entry = {"harness": "h.py", "files": files, "captured_at": "2026-08-02T00:00:00Z",
             "captured_at_commit": commit, "tool": tool}
    goldens = {GOLD: entry}
    if not only_first:
        goldens[GOLD2] = {"harness": "h.py", "files": [], "captured_at": entry["captured_at"],
                          "captured_at_commit": commit, "tool": tool}
    io.open(os.path.join(repo, "golden.coverage.json"), "w").write(
        json.dumps({"goldens": goldens}))

def drop_manifest():
    p = os.path.join(repo, "golden.coverage.json")
    if os.path.isfile(p):
        os.remove(p)

def names(d):
    return [s["name"] for s in d["signals"]]

def vals(s):
    # a PASSING signal carries 0, a denying one a list. Assertions must read both without
    # exploding: a crash here loses the sidecar, and a criterion that vanishes into
    # UNMEASURED diagnoses far worse than one that goes cleanly red.
    v = s.get("value")
    return v if isinstance(v, list) else []

# --- AC-GM-01: veto undeclared -> no signal at all, and the verdict is unchanged
io.open(os.path.join(repo, "lib.py"), "w").write("VALUE = 2\nprint(VALUE)\n")
manifest(["lib.py"])                       # present but must be ignored: nobody declared it
d_off, rc_off = evaluate(False, "L1.json")
res["AC-GM-01"] = "golden_touched" not in names(d_off) and d_off["verdict"] == "ALLOW"

# --- AC-GM-03: veto declared + the diff touches a MAPPED file -> DENY naming golden and file
d_on, rc_on = evaluate(True, "L2.json")
gt = [s for s in d_on["signals"] if s["name"] == "golden_touched"]
res["AC-GM-03"] = (d_on["verdict"] == "DENY" and rc_on == 1 and gt
                   and gt[0]["ok"] is False
                   and any("lib.py" in v and GOLD in v for v in vals(gt[0])))

# --- AC-GM-05: provenance -- the capture commit and tool version travel in the signal source
res["AC-GM-05"] = bool(gt) and "abc12345" in gt[0]["source"] and "7.9.9" in gt[0]["source"]

# --- AC-GM-04: veto declared + only UNMAPPED files touched -> the signal passes
sh(["git", "checkout", "--", "lib.py"])
io.open(os.path.join(repo, "other.py"), "w").write("UNTOUCHED = 3\n")
d4, _ = evaluate(True, "L3.json")
gt4 = [s for s in d4["signals"] if s["name"] == "golden_touched"]
res["AC-GM-04"] = bool(gt4) and gt4[0]["ok"] is True and d4["verdict"] == "ALLOW"

# --- AC-GM-02: "could not measure" -> DENY, in BOTH its shapes. The incomplete half was
# missing here while the engine silently ALLOWed it: a manifest knowing only some goldens
# asserted "nothing is covered" about one it had never measured (fresh-review CRITICAL).
drop_manifest()
d2, rc2 = evaluate(True, "L4.json")
gt2 = [s for s in d2["signals"] if s["name"] == "golden_touched"]
absent_denies = (d2["verdict"] == "DENY" and rc2 == 1 and gt2 and gt2[0]["ok"] is False
                 and GOLD in " ".join(vals(gt2[0])))
manifest(["lib.py"], only_first=True)          # GOLD2 exists in the tree, absent from the map
d2b, rc2b = evaluate(True, "L4b.json")
gt2b = [s for s in d2b["signals"] if s["name"] == "golden_touched"]
partial_denies = (d2b["verdict"] == "DENY" and rc2b == 1 and gt2b
                  and gt2b[0]["ok"] is False and GOLD2 in " ".join(vals(gt2b[0])))
res["AC-GM-02"] = bool(absent_denies and partial_denies)

# --- AC-GM-06: malformed manifest -> exit 2 config error, never a silent "no mapping"
io.open(os.path.join(repo, "golden.coverage.json"), "w").write('{"goldenz": []}')
io.open(os.path.join(w, "c.json"), "w").write(json.dumps(cfg(True)))
eng("init", "--config", "c.json", "--out", "L5.json")
r6 = eng("fastpath-eval", "--ledger", "L5.json", "--repo", "r", "--json")
res["AC-GM-06"] = r6.returncode == 2 and "invalid" in (r6.stderr or "").lower()
drop_manifest()
sh(["git", "checkout", "--", "."])

# --- AC-GM-07: capture with coverage.py unavailable -> nothing written, exit 2
stub = tempfile.mkdtemp()
io.open(os.path.join(stub, "coverage.py"), "w").write(
    "raise ImportError('no coverage in this environment')\n")
env = dict(os.environ)
env["PYTHONPATH"] = stub + os.pathsep + env.get("PYTHONPATH", "")
r7 = subprocess.run([sys.executable, ENG, "golden-coverage", "--harness", "h.py",
                     "--golden", GOLD, "--dir", "."], cwd=repo, env=env,
                    capture_output=True, text=True)
res["AC-GM-07"] = (r7.returncode == 2
                   and not os.path.isfile(os.path.join(repo, "golden.coverage.json")))

# --- AC-GM-08: PRODUCTION under a real coverage.py measures ACROSS the subprocess boundary
try:
    import coverage as _cov_probe            # noqa: F401
    have_cov = True
except ImportError:
    have_cov = False
if have_cov:
    r8 = subprocess.run([sys.executable, ENG, "golden-coverage", "--harness", "h.py",
                         "--golden", GOLD, "--dir", "."], cwd=repo,
                        capture_output=True, text=True)
    m = {}
    p8 = os.path.join(repo, "golden.coverage.json")
    if os.path.isfile(p8):
        m = json.load(io.open(p8, encoding="utf-8"))
    entry = (m.get("goldens") or {}).get(GOLD) or {}
    res["AC-GM-08"] = (r8.returncode == 0 and "lib.py" in entry.get("files", [])
                       and "other.py" not in entry.get("files", [])
                       and bool(entry.get("captured_at_commit"))
                       and entry.get("tool", "").startswith("coverage.py"))
else:
    res["AC-GM-08"] = None       # UNMEASURED without the capture-time dependency

side = os.path.join(kit, "reports", "junit")
os.makedirs(side, exist_ok=True)
io.open(os.path.join(side, ".goldencov-cases.json"), "w", encoding="utf-8").write(
    json.dumps(res))
bad = [k for k, v in res.items() if v is False]
unm = [k for k, v in res.items() if v is None]
print("OK %d cases%s" % (sum(1 for v in res.values() if v),
      (" (unmeasured: " + ",".join(unm) + ")") if unm else "")
      if not bad else "BAD " + ",".join(bad))
PY
)
case "$T117" in
  OK*) PASS=$((PASS+1)); echo "  ok   golden-coverage: $T117";;
  *)   FAIL=$((FAIL+1)); echo "  FAIL $T117";;
esac

echo "== T118 (1.61.0): evidence origin -- the commit and tree state it was measured at (ADR-007) =="
# Provenance only: these criteria assert what is RECORDED, plus that the readiness score does
# not move. The case that matters most is AC-EP-03: without git, dirty must be null and never
# false, because a tree state nobody could measure must not read as clean.
T118=$("$PY" - "$KIT" <<'PY'
import io, json, os, subprocess, sys, tempfile
kit = sys.argv[1]
ENG = os.path.join(kit, ".claude", "skills", "uscha-devloop", "qa_ledger.py")
res = {}

def eng(w, *a):
    return subprocess.run([sys.executable, ENG] + list(a), cwd=w, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")

def setup(git=True):
    w = tempfile.mkdtemp(); repo = os.path.join(w, "r"); os.makedirs(repo)
    io.open(os.path.join(repo, "a.py"), "w").write("A = 1\n")
    if git:
        for a in (["git", "init", "-b", "main"], ["git", "config", "user.email", "t@t"],
                  ["git", "config", "user.name", "t"], ["git", "add", "-A"],
                  ["git", "commit", "-m", "base"]):
            subprocess.run(a, cwd=repo, capture_output=True, text=True)
    io.open(os.path.join(w, "c.json"), "w").write(json.dumps(
        {"defaults": {"acceptance_file": "ACCEPTANCE.md"},
         "repos": [{"name": "r", "path": "r", "type": "python"}],
         "integration": {"enabled": False}}))
    eng(w, "init", "--config", "c.json", "--out", "L.json")
    return w, repo

def origin(w):
    d = json.load(io.open(os.path.join(w, "L.json"), encoding="utf-8"))
    snaps = d["repos"]["r"]["snapshots"]
    return (snaps[-1].get("origin") or {}) if snaps else {}

def head(repo):
    r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True)
    return r.stdout.strip()

# --- AC-EP-01: clean repo -> the real HEAD, dirty false
w, repo = setup()
score_before = json.loads(eng(w, "readiness", "--ledger", "L.json", "--json").stdout).get("score")
eng(w, "snapshot", "--ledger", "L.json", "--repo", "r", "--phase", "pre")
o1 = origin(w)
res["AC-EP-01"] = o1.get("commit") == head(repo) and o1.get("dirty") is False

# --- AC-EP-02: a modified tracked file -> same commit, dirty true
io.open(os.path.join(repo, "a.py"), "w").write("A = 2\n")
eng(w, "snapshot", "--ledger", "L.json", "--repo", "r", "--phase", "post")
o2 = origin(w)
res["AC-EP-02"] = o2.get("commit") == head(repo) and o2.get("dirty") is True

# an UNTRACKED file must read dirty too -- treating it as invisible is the 1.57.0 mistake
subprocess.run(["git", "checkout", "--", "."], cwd=repo, capture_output=True)
io.open(os.path.join(repo, "new.py"), "w").write("N = 1\n")
eng(w, "snapshot", "--ledger", "L.json", "--repo", "r", "--phase", "post")
res["AC-EP-02"] = bool(res["AC-EP-02"] and origin(w).get("dirty") is True)

# --- AC-EP-03: "could not measure" -> null, NO CRASH, in all THREE of its shapes. The first
# version tested only a plain directory (where both git calls return cleanly non-zero) and so
# never touched the two that actually raised: a repo path that does not exist, and git absent
# from PATH. That gap is exactly why a fresh review found the crash and the suite did not.
def origin_null_no_crash(w2):
    r = eng(w2, "snapshot", "--ledger", "L.json", "--repo", "r", "--phase", "pre")
    o = origin(w2)
    return (r.returncode == 0 and "Traceback" not in (r.stderr or "")
            and o.get("commit") is None and o.get("dirty") is None
            and o.get("dirty") is not False)

w2, _ = setup(git=False)                       # a real directory that is not a git repo
plain_ok = origin_null_no_crash(w2)

w3, repo3 = setup(git=False)                   # the configured repo path does not exist
import shutil as _sh
_sh.rmtree(repo3)
missing_ok = origin_null_no_crash(w3)

w4, _ = setup(git=False)                       # git itself unreachable
_env = dict(os.environ); _env["PATH"] = tempfile.mkdtemp()
r4 = subprocess.run([sys.executable, ENG, "snapshot", "--ledger", "L.json",
                     "--repo", "r", "--phase", "pre"], cwd=w4, env=_env,
                    capture_output=True, text=True, encoding="utf-8", errors="replace")
o4 = origin(w4)
nogit_ok = (r4.returncode == 0 and "Traceback" not in (r4.stderr or "")
            and o4.get("commit") is None and o4.get("dirty") is None)

res["AC-EP-03"] = bool(plain_ok and missing_ok and nogit_ok)

# --- AC-EP-05: the answer is scoped to the repo path. A repo entry pointing at a
# SUBDIRECTORY of a larger working tree must not inherit the outer repo's dirtiness.
w5 = tempfile.mkdtemp(); sub = os.path.join(w5, "r"); os.makedirs(sub)
io.open(os.path.join(sub, "a.py"), "w").write("A = 1\n")
io.open(os.path.join(w5, "outside.py"), "w").write("B = 1\n")
for a in (["git", "init", "-b", "main"], ["git", "config", "user.email", "t@t"],
          ["git", "config", "user.name", "t"], ["git", "add", "-A"],
          ["git", "commit", "-m", "base"]):
    subprocess.run(a, cwd=w5, capture_output=True, text=True)
io.open(os.path.join(w5, "outside.py"), "w").write("B = 2\n")   # OUTSIDE the repo path only
io.open(os.path.join(w5, "c.json"), "w").write(json.dumps(
    {"defaults": {"acceptance_file": "ACCEPTANCE.md"},
     "repos": [{"name": "r", "path": "r", "type": "python"}],
     "integration": {"enabled": False}}))
eng(w5, "init", "--config", "c.json", "--out", "L.json")
eng(w5, "snapshot", "--ledger", "L.json", "--repo", "r", "--phase", "pre")
o5 = origin(w5)
res["AC-EP-05"] = o5.get("dirty") is False and o5.get("commit") is not None

# --- AC-EP-04: the score does not move because provenance appeared
score_after = json.loads(eng(w, "readiness", "--ledger", "L.json", "--json").stdout).get("score")
res["AC-EP-04"] = score_before == score_after

# dashboard passthrough: present once a snapshot has an origin, absent on a virgin ledger
d1 = json.loads(eng(w, "dashboard", "--ledger", "L.json", "--json").stdout)
eng(w, "init", "--config", "c.json", "--out", "L2.json")
d2 = json.loads(eng(w, "dashboard", "--ledger", "L2.json", "--json").stdout)
dash_ok = ("evidence_origin" in d1) and ("evidence_origin" not in d2)

side = os.path.join(kit, "reports", "junit")
os.makedirs(side, exist_ok=True)
io.open(os.path.join(side, ".origin-cases.json"), "w", encoding="utf-8").write(json.dumps(res))
bad = [k for k, v in res.items() if not v] + ([] if dash_ok else ["dashboard-passthrough"])
print("OK %d cases" % len(res) if not bad else "BAD " + ",".join(bad))
PY
)
case "$T118" in
  OK*) PASS=$((PASS+1)); echo "  ok   evidence origin: $T118";;
  *)   FAIL=$((FAIL+1)); echo "  FAIL $T118";;
esac

echo "== T119 (1.63.0): cleanroom -- verify the COMMIT, not the tree (ADR-008) =="
# The gate assertion is ATTRIBUTABLE by construction: the same ledger is asked for pr-ready
# twice, once with the clean-room off and once declared. If it only ever returned 1 we would
# be measuring "something blocks", not "THIS blocks".
T119=$("$PY" - "$KIT" <<'PY'
import io, json, os, subprocess, sys, tempfile
kit = sys.argv[1]
ENG = os.path.join(kit, ".claude", "skills", "uscha-devloop", "qa_ledger.py")
res = {}
w = tempfile.mkdtemp(); repo = os.path.join(w, "r"); os.makedirs(os.path.join(repo, "reports"))

def sh(*a, **kw):
    return subprocess.run(list(a), cwd=kw.get("cwd", repo), capture_output=True, text=True)

def eng(*a):
    return subprocess.run([sys.executable, ENG] + list(a), cwd=w, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")

def cfg(mode):
    d = {"defaults": {"acceptance_file": "ACCEPTANCE.md",
                      "qa_tools_order": ["code-review", "judgment-day", "improve"]},
         "repos": [{"name": "r", "path": "r", "type": "go"}],
         "integration": {"enabled": False}}
    if mode is not None:
        d["defaults"]["clean_room"] = {"mode": mode}
    io.open(os.path.join(w, "c.json"), "w").write(json.dumps(d))

sh("git", "init", "-b", "main"); sh("git", "config", "user.email", "t@t")
sh("git", "config", "user.name", "t")
io.open(os.path.join(repo, "helper.go"), "w").write("package main\n")
io.open(os.path.join(repo, "check.py"), "w").write(
    "import os, sys\nsys.exit(0 if os.path.isfile('helper.go') else 1)\n")
sh("git", "add", "-A"); sh("git", "commit", "-m", "base")
io.open(os.path.join(repo, "reports", "junit.xml"), "w").write(
    '<testsuite tests="1" failures="0" errors="0" skipped="0"/>')

RUN = '"%s" check.py' % sys.executable

def make_ledger(name, mode):
    cfg(mode)
    eng("init", "--config", "c.json", "--out", name)
    eng("snapshot", "--ledger", name, "--repo", "r")
    for it, tool in ((1, "code-review"), (1, "judgment-day"), (1, "improve")):
        eng("log-step", "--ledger", name, "--repo", "r", "--tool", tool,
            "--iteration", str(it), "--gated-reported", "0", "--files-changed", "0",
            "--tests-passed", "true")
    return name

def pr_ready(name):
    return eng("phase", "--ledger", name, "--repo", "r", "--require", "pr-ready").returncode

# --- AC-CR-06: block absent -> identical behavior, and the fixture DOES reach pr-ready
make_ledger("L-off.json", None)
off_rc = pr_ready("L-off.json")
# --- the gate is attributable: same facts, clean-room declared -> blocked
make_ledger("L-on.json", "final")
on_rc = pr_ready("L-on.json")
res["AC-CR-06"] = (off_rc == 0 and on_rc == 1)

# --- AC-CR-02 + AC-CR-04: a green run records ref, worktree_sha and wall clock
head = sh("git", "rev-parse", "HEAD").stdout.strip()
r = eng("cleanroom", "--ledger", "L-on.json", "--repo", "r", "--run", RUN, "--json")
rec = json.loads(r.stdout) if r.stdout.strip().startswith("{") else {}
res["AC-CR-02"] = (r.returncode == 0 and rec.get("ok") is True
                   and rec.get("status") == "GREEN" and isinstance(rec.get("wall_ms"), int))
res["AC-CR-04"] = rec.get("worktree_sha") == head and rec.get("ref") == head
# and with green clean-room evidence for HEAD, the gate opens
res["AC-CR-06"] = bool(res["AC-CR-06"] and pr_ready("L-on.json") == 0)

# --- AC-CR-05: no leftover worktree
wl = sh("git", "worktree", "list").stdout
res["AC-CR-05"] = "uscha-cleanroom" not in wl

# --- AC-CR-03: a NEW commit makes the previous clean-room evidence stale for the gate
io.open(os.path.join(repo, "other.go"), "w").write("package main\n")
sh("git", "add", "-A"); sh("git", "commit", "-m", "second")
res["AC-CR-03"] = pr_ready("L-on.json") == 1

# --- AC-CR-01: green in the maker's tree, RED against the commit alone
sh("git", "rm", "-q", "--cached", "helper.go")
sh("git", "commit", "-q", "-m", "drop helper")
local = subprocess.run([sys.executable, "check.py"], cwd=repo, capture_output=True)
r = eng("cleanroom", "--ledger", "L-on.json", "--repo", "r", "--run", RUN, "--json")
rec = json.loads(r.stdout) if r.stdout.strip().startswith("{") else {}
res["AC-CR-01"] = (local.returncode == 0 and r.returncode == 1
                   and rec.get("status") == "RED" and pr_ready("L-on.json") == 1)

# --- AC-CR-07: a failing setup is SETUP_FAILED, distinct from a red suite
r = eng("cleanroom", "--ledger", "L-on.json", "--repo", "r", "--run", RUN,
        "--setup", '"%s" -c "import sys; sys.exit(3)"' % sys.executable, "--json")
rec = json.loads(r.stdout) if r.stdout.strip().startswith("{") else {}
res["AC-CR-07"] = rec.get("status") == "SETUP_FAILED" and rec.get("ok") is False

# --- AC-CR-08: `integration` is a SYNTHETIC scope, never present in config["repos"], and
# _repo_cfg exits on an unknown name. The gate resolved the repo path without the guard every
# other call site uses, so declaring the clean-room turned the integration merge gate into a
# config-error crash instead of a phase verdict. It must degrade like any other repo.
_ip = eng("phase", "--ledger", "L-on.json", "--repo", "integration", "--require", "pr-ready")
res["AC-CR-08"] = (_ip.returncode == 1
                   and "no config entry" not in (_ip.stdout + _ip.stderr)
                   and "PHASE integration" in _ip.stdout)

side = os.path.join(kit, "reports", "junit")
os.makedirs(side, exist_ok=True)
io.open(os.path.join(side, ".cleanroom-cases.json"), "w", encoding="utf-8").write(json.dumps(res))
bad = [k for k, v in res.items() if not v]
print("OK %d cases" % len(res) if not bad else "BAD " + ",".join(sorted(bad)))
PY
)
case "$T119" in
  OK*) PASS=$((PASS+1)); echo "  ok   cleanroom: $T119";;
  *)   FAIL=$((FAIL+1)); echo "  FAIL $T119";;
esac

echo "== T120 (1.64.0): curation -- candidates in quarantine, verdicts in the ledger (ADR-009/010) =="
# The promotion-gate assertion is ATTRIBUTABLE by construction (the AC-CR-06 lesson): the
# same ledger reaches pr-ready with no discovery/, is blocked by one unjudged candidate,
# and opens again the moment the verdict lands.
T120=$("$PY" - "$KIT" <<'PY'
import io, json, os, subprocess, sys, tempfile
kit = sys.argv[1]
ENG = os.path.join(kit, ".claude", "skills", "uscha-devloop", "qa_ledger.py")
res = {}
w = tempfile.mkdtemp(); repo = os.path.join(w, "r")
os.makedirs(os.path.join(repo, "reports")); os.makedirs(os.path.join(repo, "src"))

def sh(*a):
    return subprocess.run(list(a), cwd=repo, capture_output=True, text=True)

def eng(*a):
    return subprocess.run([sys.executable, ENG] + list(a), cwd=w, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")

sh("git", "init", "-b", "main"); sh("git", "config", "user.email", "t@t")
sh("git", "config", "user.name", "t")
io.open(os.path.join(repo, "src", "calc.go"), "w").write("package main\nfunc Iva() {}\n")
sh("git", "add", "-A"); sh("git", "commit", "-m", "base")
io.open(os.path.join(repo, "reports", "junit.xml"), "w").write(
    '<testsuite tests="1" failures="0" errors="0" skipped="0"/>')

io.open(os.path.join(w, "c.json"), "w").write(json.dumps({
    "defaults": {"acceptance_file": "ACCEPTANCE.md",
                 "qa_tools_order": ["code-review", "judgment-day", "improve"]},
    "repos": [{"name": "r", "path": "r", "type": "go"}],
    "integration": {"enabled": False}}))
eng("init", "--config", "c.json", "--out", "L.json")
eng("snapshot", "--ledger", "L.json", "--repo", "r")
for tool in ("code-review", "judgment-day", "improve"):
    eng("log-step", "--ledger", "L.json", "--repo", "r", "--tool", tool,
        "--iteration", "1", "--gated-reported", "0", "--files-changed", "0",
        "--tests-passed", "true")

def pr_ready():
    return eng("phase", "--ledger", "L.json", "--repo", "r", "--require", "pr-ready")

def cc(*extra):
    return eng("curation-check", "--ledger", "L.json", "--repo", "r", *extra)

def write_cand(name, body):
    os.makedirs(os.path.join(repo, "discovery"), exist_ok=True)
    io.open(os.path.join(repo, "discovery", name), "w").write(body)

def write_ledger(body, commit=False):
    io.open(os.path.join(repo, "BEHAVIOR-LEDGER.md"), "w").write(body)
    if commit:
        sh("git", "add", "-A"); sh("git", "commit", "-m", "ledger")

VALID = ("---\nevidence:\n  type: code\n  refs:\n    - \x22src/calc.go:1-2\x22\n"
         "confidence: high\n---\n# iva behavior\n")
HDR = ("# Behavior Ledger\n\n"
       "| # | candidate | evidence | confidence | verdict | adr |\n"
       "|---|-----------|----------|------------|---------|-----|\n")

# --- AC-RD-07 first half: no discovery/ -> feature unused, pr-ready reachable
before = pr_ready().returncode
unused = cc()
res["AC-RD-07"] = before == 0 and unused.returncode == 0

# --- AC-RD-01: valid candidate accepted (exit 1: awaiting verdict); malformed fm -> exit 2
write_cand("001-iva.md", VALID)
r = cc("--json"); d = json.loads(r.stdout)
valid_ok = r.returncode == 1 and d["candidates"] == ["001-iva.md"] and d["unjudged"] == ["001-iva.md"]
write_cand("002-bad.md", "---\nevidence:\n  type: guesswork\n  refs:\n    - \x22src/calc.go\x22\nconfidence: high\n---\n# bad\n")
r = cc("--json"); d = json.loads(r.stdout)
mal_ok = (r.returncode == 2 and d["malformed"]
          and d["malformed"][0]["candidate"] == "002-bad.md")
res["AC-RD-01"] = bool(valid_ok and mal_ok)
os.remove(os.path.join(repo, "discovery", "002-bad.md"))

# --- AC-RD-02: unresolvable evidence ref -> invalid, NAMED
write_cand("003-ghost.md", "---\nevidence:\n  type: code\n  refs:\n    - \x22src/nope.go:9\x22\nconfidence: low\n---\n# ghost\n")
r = cc("--json"); d = json.loads(r.stdout)
gm = [m for m in d["malformed"] if m["candidate"] == "003-ghost.md"]
res["AC-RD-02"] = (r.returncode == 2 and gm
                   and any("src/nope.go" in e for e in gm[0]["errors"]))
os.remove(os.path.join(repo, "discovery", "003-ghost.md"))

# --- AC-RD-03: unjudged candidate blocks pr-ready, reason NAMES it (attributable)
blocked = pr_ready()
res["AC-RD-03"] = (blocked.returncode == 1 and "001-iva.md" in blocked.stdout
                   and before == 0)

# --- AC-RD-06: the three verdicts land in three distinct buckets
write_cand("004-keep.md", VALID.replace("# iva behavior", "# keep me"))
write_cand("005-drop.md", VALID.replace("# iva behavior", "# drop me"))
write_ledger(HDR
             + "| 1 | 001-iva.md | code | high | fix | ADR-RD-001 |\n"
             + "| 2 | 004-keep.md | code | high | preserve | ADR-RD-002 |\n"
             + "| 3 | 005-drop.md | code | high | undefined | ADR-RD-003 |\n",
             commit=True)
r = cc("--json"); d = json.loads(r.stdout)
res["AC-RD-06"] = (r.returncode == 0
                   and d["promote_as_is"] == ["004-keep.md"]
                   and d["promote_with_declared_divergence"] == ["001-iva.md"]
                   and d["excluded"] == ["005-drop.md"])
# and the gate OPENS now that every candidate is judged -- closes the attributable arc
res["AC-RD-03"] = bool(res["AC-RD-03"] and pr_ready().returncode == 0)

# --- AC-RD-04: malformed ledger (fourth verdict state) -> exit 2, named
write_ledger(HDR + "| 1 | 001-iva.md | code | high | maybe | ADR-RD-001 |\n")
r = cc("--json"); d = json.loads(r.stdout)
# malformation must block via the PHASE gate too, and be attributed there (fresh review:
# the gate blocked with a generic message and only curation-check was tested)
pm = pr_ready()
res["AC-RD-04"] = (r.returncode == 2 and any("maybe" in e for e in d["ledger_errors"])
                   and pm.returncode == 1 and "BEHAVIOR-LEDGER.md" in pm.stdout)

# --- AC-RD-05: EDIT an existing committed row -> violation; and no git -> UNMEASURED
write_ledger(HDR
             + "| 1 | 001-iva.md | code | high | preserve | ADR-RD-001 |\n"
             + "| 2 | 004-keep.md | code | high | preserve | ADR-RD-002 |\n"
             + "| 3 | 005-drop.md | code | high | undefined | ADR-RD-003 |\n")
r = cc("--json"); d = json.loads(r.stdout)
tamper_ok = r.returncode == 2 and d["append_only"] == "violation"
# no-git shape: same tree copied outside any repo
import shutil as _sh
w2 = tempfile.mkdtemp(); _sh.copytree(repo, os.path.join(w2, "r"),
                                      ignore=_sh.ignore_patterns(".git"))
io.open(os.path.join(w2, "c.json"), "w").write(json.dumps({
    "defaults": {"acceptance_file": "ACCEPTANCE.md"},
    "repos": [{"name": "r", "path": "r", "type": "go"}],
    "integration": {"enabled": False}}))
def eng2(*a):
    env2 = dict(os.environ)
    env2["GIT_CEILING_DIRECTORIES"] = w2   # a .git ABOVE the tempdir must not un-break no-git
    return subprocess.run([sys.executable, ENG] + list(a), cwd=w2, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", env=env2)
eng2("init", "--config", "c.json", "--out", "L.json")
r2 = eng2("curation-check", "--ledger", "L.json", "--repo", "r", "--json")
d2 = json.loads(r2.stdout)
res["AC-RD-05"] = bool(tamper_ok and d2["append_only"] == "unmeasured"
                       and d2["append_only"] != "ok")

# --- AC-RD-13: the SYNTHETIC integration scope must get a verdict, never a config crash
# (second recurrence of the 1.63.0 class -- the devloop now auto-runs spec-drift per pass)
ok13 = True
for cmdname in ("spec-drift", "curation-check", "roundtrip"):
    ri = eng(cmdname, "--ledger", "L.json", "--repo", "integration")
    if ri.returncode not in (0, 1) or "no config entry" in (ri.stdout + ri.stderr):
        ok13 = False
res["AC-RD-13"] = ok13

side = os.path.join(kit, "reports", "junit")
os.makedirs(side, exist_ok=True)
io.open(os.path.join(side, ".curation-cases.json"), "w", encoding="utf-8").write(json.dumps(res))
bad = [k for k, v in res.items() if not v]
print("OK %d cases" % len(res) if not bad else "BAD " + ",".join(sorted(bad)))
PY
)
case "$T120" in
  OK*) PASS=$((PASS+1)); echo "  ok   curation: $T120";;
  *)   FAIL=$((FAIL+1)); echo "  FAIL $T120";;
esac

echo "== T121 (1.65.0): oracle -- declared divergences + roundtrip by spec-id (slice 2) =="
T121=$("$PY" - "$KIT" <<'PY'
import io, json, os, subprocess, sys, tempfile
kit = sys.argv[1]
ENG = os.path.join(kit, ".claude", "skills", "uscha-devloop", "qa_ledger.py")
res = {}
w = tempfile.mkdtemp(); os.makedirs(os.path.join(w, "golden"))
SUF = ".appro" + "ved.json"

def eng(*a, cwd=w):
    return subprocess.run([sys.executable, ENG] + list(a), cwd=cwd, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")

def wr(rel, body):
    io.open(os.path.join(w, rel), "w").write(body)

wr("golden/keep.received.json", "AAA"); wr("golden/keep" + SUF, "AAA")
wr("golden/fixed.received.json", "NEW"); wr("golden/fixed" + SUF, "OLD")

# --- AC-RD-08: undeclared divergence blocks; declared -> CLEAN with the pair NAMED
r = eng("golden-diff", "--dir", ".", "--json"); d = json.loads(r.stdout)
undeclared_blocks = d["verdict"] == "DIVERGE" and r.returncode == 1
wr("golden.divergences.json", json.dumps({"divergences": {
    "fixed" + SUF: {"adr": "ADR-RD-003", "reason": "behavior corrected per verdict"}}}))
r = eng("golden-diff", "--dir", ".", "--json"); d = json.loads(r.stdout)
fx = {os.path.basename(f["received"]): f for f in d["fixtures"]}
res["AC-RD-08"] = (undeclared_blocks and d["verdict"] == "CLEAN" and r.returncode == 0
                   and d["expected_diverged"] == 1
                   and fx["fixed.received.json"]["result"] == "expected_divergence"
                   and fx["fixed.received.json"].get("divergence_adr") == "ADR-RD-003"
                   and fx["keep.received.json"]["result"] == "matched")

# --- AC-RD-09: declared but IDENTICAL -> red, the reason names the ADR -- in BOTH shapes:
# raw-identical, and SCRUB-EQUAL (identical once masked volatiles are removed; the first
# build let the scrub branch swallow that case silently -- fresh-review HIGH)
wr("golden/fixed.received.json", "OLD")
r = eng("golden-diff", "--dir", ".", "--json"); d = json.loads(r.stdout)
raw_red = (d["verdict"] == "DIVERGE" and r.returncode == 1
           and any("ADR-RD-003" in x["reason"] for x in d["diverged"]))
wr("golden/fixed.received.json", "OLD ts=111")
wr("golden/fixed" + SUF, "OLD ts=999")
wr("golden.scrub.json", json.dumps({"rules": [{"pattern": "ts=[0-9]+", "replace": "ts=X"}]}))
r = eng("golden-diff", "--dir", ".", "--json"); d = json.loads(r.stdout)
scrub_red = (d["verdict"] == "DIVERGE" and r.returncode == 1
             and any("scrub-equal" in x["reason"] for x in d["diverged"]))
os.remove(os.path.join(w, "golden.scrub.json"))
res["AC-RD-09"] = bool(raw_red and scrub_red)
wr("golden/fixed.received.json", "NEW")
wr("golden/fixed" + SUF, "OLD")

# --- AC-RD-10: malformed declaration file -> exit 2, never silent
wr("golden.divergences.json", "{\x22divergences\x22: {\x22x\x22: {\x22adr\x22: \x22nope\x22}}}")
r = eng("golden-diff", "--dir", ".", "--json")
res["AC-RD-10"] = r.returncode == 2 and "invalid" in (r.stderr or "").lower()
os.remove(os.path.join(w, "golden.divergences.json"))

# --- AC-RD-11: roundtrip coverage by embedded id, advisory (exit 0 even with misses)
repo = os.path.join(w, "r")
os.makedirs(os.path.join(repo, "discovery")); os.makedirs(os.path.join(repo, "src"))
def sh(*a):
    return subprocess.run(list(a), cwd=repo, capture_output=True, text=True)
sh("git", "init", "-b", "main"); sh("git", "config", "user.email", "t@t")
sh("git", "config", "user.name", "t")
CAND = ("---\nevidence:\n  type: code\n  refs:\n    - \x22src/a.go\x22\n"
        "confidence: high\n---\n# c\n")
io.open(os.path.join(repo, "src", "a.go"), "w").write(
    "package main\n// uscha-spec: 001-covered\nfunc A() {}\n")
io.open(os.path.join(repo, "discovery", "001-covered.md"), "w").write(CAND)
io.open(os.path.join(repo, "discovery", "002-missing.md"), "w").write(CAND)
io.open(os.path.join(repo, "BEHAVIOR-LEDGER.md"), "w").write(
    "| # | candidate | evidence | confidence | verdict | adr |\n"
    "|---|-----------|----------|------------|---------|-----|\n"
    "| 1 | 001-covered.md | code | high | preserve | ADR-RD-001 |\n"
    "| 2 | 002-missing.md | code | high | fix | ADR-RD-002 |\n")
sh("git", "add", "-A"); sh("git", "commit", "-m", "x")
wr("c.json", json.dumps({"defaults": {"acceptance_file": "ACCEPTANCE.md"},
                         "repos": [{"name": "r", "path": "r", "type": "go"}],
                         "integration": {"enabled": False}}))
eng("init", "--config", "c.json", "--out", "L.json")
r = eng("roundtrip", "--ledger", "L.json", "--repo", "r", "--json")
d = json.loads(r.stdout)
res["AC-RD-11"] = (r.returncode == 0 and d["promoted"] == 2 and d["covered"] == 1
                   and d["missing"] == ["002-missing.md"] and d["advisory"] is True)

# --- AC-RD-12: the run PERSISTS (ledger + conditional dashboard); virgin ledger unchanged
L = json.load(open(os.path.join(w, "L.json")))
persisted = (L.get("roundtrip") or {}).get("covered") == 1
r = eng("dashboard", "--ledger", "L.json", "--json")
has = "roundtrip" in json.loads(r.stdout)
eng("init", "--config", "c.json", "--out", "Lv.json")
r = eng("dashboard", "--ledger", "Lv.json", "--json")
virgin = "roundtrip" in json.loads(r.stdout)
res["AC-RD-12"] = bool(persisted and has and not virgin)

side = os.path.join(kit, "reports", "junit")
os.makedirs(side, exist_ok=True)
io.open(os.path.join(side, ".oracle-cases.json"), "w", encoding="utf-8").write(json.dumps(res))
bad = [k for k, v in res.items() if not v]
print("OK %d cases" % len(res) if not bad else "BAD " + ",".join(sorted(bad)))
PY
)
case "$T121" in
  OK*) PASS=$((PASS+1)); echo "  ok   oracle: $T121";;
  *)   FAIL=$((FAIL+1)); echo "  FAIL $T121";;
esac

echo "== T122 (1.68.0): facts -- published claims become compiled artifacts (T0, ADR-012) =="
T122=$("$PY" - "$KIT" <<'PY'
import io, json, os, subprocess, sys, tempfile
kit = sys.argv[1]
ENG = os.path.join(kit, ".claude", "skills", "uscha-devloop", "qa_ledger.py")
res = {}
w = tempfile.mkdtemp()

def eng(*a):
    return subprocess.run([sys.executable, ENG] + list(a), cwd=w, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")

# --- AC-SF-01: derivation is deterministic -- two runs, byte-identical, well-formed
eng("facts", "--out", "f1.json")
eng("facts", "--out", "f2.json")
b1 = io.open(os.path.join(w, "f1.json"), "rb").read()
b2 = io.open(os.path.join(w, "f2.json"), "rb").read()
d = json.loads(b1)
res["AC-SF-01"] = (b1 == b2 and d["version"] and d["subcommands"]["count"] > 30
                   and "facts" in d["subcommands"]["list"]
                   and d["skills"]["count"] == len(d["skills"]["list"]))

# --- AC-SF-02: an injected wrong claim fails the check NAMING file, key and both values
io.open(os.path.join(w, "wrong.md"), "w").write(
    "the kit v9.9.9 ships with 999 subcommands and 99 skills\n")
r = eng("facts", "--check", "wrong.md", "--out", "f1.json")
out = r.stdout
res["AC-SF-02"] = (r.returncode == 1 and "wrong.md:1" in out and "9.9.9" in out
                   and "999" in out and "99" in out and "FACTUAL DRIFT" in out)

# --- AC-SF-03: a stale committed facts file is itself drift, named
stale = dict(d); stale["version"] = "0.0.0"
io.open(os.path.join(w, "stale.json"), "w").write(
    json.dumps(stale, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
io.open(os.path.join(w, "right.md"), "w").write(
    "the kit v%s ships %d subcommands and %d skills\n"
    % (d["version"], d["subcommands"]["count"], d["skills"]["count"]))
r = eng("facts", "--check", "right.md", "--out", "stale.json")
res["AC-SF-03"] = r.returncode == 1 and "stale" in r.stdout

# --- AC-SF-04: correct claims + fresh facts -> exit 0
r = eng("facts", "--check", "right.md", "--out", "f1.json")
res["AC-SF-04"] = r.returncode == 0

# --- AC-SF-05: the CODEX TWIN derives identical facts. The twins are byte-identical files,
# but a fixed-depth root walk made runtime behavior diverge by install location (fresh
# review, reproduced): version None and 0 skills from skills/uscha-devloop/.
TWIN = os.path.join(kit, "skills", "uscha-devloop", "qa_ledger.py")
rt = subprocess.run([sys.executable, TWIN, "facts", "--out", "ftwin.json"],
                    cwd=w, capture_output=True, text=True)
tb = io.open(os.path.join(w, "ftwin.json"), "rb").read() if rt.returncode == 0 else b""
res["AC-SF-05"] = rt.returncode == 0 and tb == b1

side = os.path.join(kit, "reports", "junit")
os.makedirs(side, exist_ok=True)
io.open(os.path.join(side, ".facts-cases.json"), "w", encoding="utf-8").write(json.dumps(res))
bad = [k for k, v in res.items() if not v]
print("OK %d cases" % len(res) if not bad else "BAD " + ",".join(sorted(bad)))
PY
)
case "$T122" in
  OK*) PASS=$((PASS+1)); echo "  ok   facts: $T122";;
  *)   FAIL=$((FAIL+1)); echo "  FAIL $T122";;
esac

echo "== T123 (1.69.0): CANDIDATE-DELTA -- typed observations, verdicts as ledger objects (ADR-013) =="
# The promotion refusal is ATTRIBUTABLE: pr-ready green before the delta exists, blocked by
# one uncurated OBS, and the same ledger promotes clean once every verdict lands.
T123=$("$PY" - "$KIT" <<'PY'
import io, json, os, subprocess, sys, tempfile
kit = sys.argv[1]
ENG = os.path.join(kit, ".claude", "skills", "uscha-devloop", "qa_ledger.py")
res = {}
w = tempfile.mkdtemp(); repo = os.path.join(w, "r")
os.makedirs(os.path.join(repo, "src")); os.makedirs(os.path.join(repo, "reports"))

def sh(*a):
    return subprocess.run(list(a), cwd=repo, capture_output=True, text=True)

def eng(*a):
    return subprocess.run([sys.executable, ENG] + list(a), cwd=w, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")

sh("git", "init", "-b", "main"); sh("git", "config", "user.email", "t@t")
sh("git", "config", "user.name", "t")
io.open(os.path.join(repo, "src", "app.py"), "w").write(
    "def facturar(cliente, total):\n    return total\n\nclass Cliente:\n    pass\n")
io.open(os.path.join(repo, "orphan.py"), "w").write("def _hidden():\n    return 0\n")
io.open(os.path.join(repo, "requirements.txt"), "w").write("requests==2.31.0\n")
io.open(os.path.join(repo, "ACCEPTANCE.md"), "w").write(
    "- [ ] AC-1 - facturar returns the total\n")
os.makedirs(os.path.join(repo, "goldens"))
io.open(os.path.join(repo, "goldens", "case.approved.json"), "w").write("{}\n")
sh("git", "add", "-A"); sh("git", "commit", "-m", "base")
io.open(os.path.join(repo, "reports", "junit.xml"), "w").write(
    '<testsuite tests="1" failures="0" errors="0" skipped="0"/>')

io.open(os.path.join(w, "c.json"), "w").write(json.dumps({
    "defaults": {"acceptance_file": "ACCEPTANCE.md",
                 "qa_tools_order": ["code-review", "judgment-day", "improve"]},
    "repos": [{"name": "r", "path": "r", "type": "python"}],
    "integration": {"enabled": False}}))
eng("init", "--config", "c.json", "--out", "L.json")
eng("snapshot", "--ledger", "L.json", "--repo", "r")
for tool in ("code-review", "judgment-day", "improve"):
    eng("log-step", "--ledger", "L.json", "--repo", "r", "--tool", tool,
        "--iteration", "1", "--gated-reported", "0", "--files-changed", "0",
        "--tests-passed", "true")
eng("log-gate", "--ledger", "L.json", "--repo", "r", "--iteration", "1",
    "--kind", "golden-diff", "--verdict", "pass")
before = eng("phase", "--ledger", "L.json", "--repo", "r",
             "--require", "pr-ready").returncode

io.open(os.path.join(w, "narr.json"), "w").write(json.dumps([
    {"type": "behavior", "statement": "facturar keeps AC-1: returns the total",
     "files": ["src/app.py:1"]},
    {"type": "decision_trace", "statement": "totals are never rounded", "files": []}]))
r = eng("discover", "--ledger", "L.json", "--repo", "r",
        "--narrated", os.path.join(w, "narr.json"))
DPATH = os.path.join(repo, "discovery", "CANDIDATE-DELTA.json")
delta = json.load(io.open(DPATH, encoding="utf-8"))
obs = delta["observations"]

# --- AC-DD-01: well-formed delta, every OBS fully typed
res["AC-DD-01"] = (r.returncode == 0 and len(obs) >= 4 and
                   all(o.get("id") and o.get("type") and o.get("evidence_class")
                       and o.get("provenance") for o in obs))

# --- AC-DD-02: skill input stays narrated; a self-classifying input is refused (exit 2)
narr = [o for o in obs if o["provenance"].get("tool") == "skill"]
io.open(os.path.join(w, "bad.json"), "w").write(json.dumps(
    [{"type": "behavior", "statement": "x", "evidence_class": "measured"}]))
rb = eng("discover", "--ledger", "L.json", "--repo", "r",
         "--narrated", os.path.join(w, "bad.json"))
res["AC-DD-02"] = (len(narr) == 2
                   and all(o["evidence_class"] == "narrated" for o in narr)
                   and rb.returncode == 2 and "self-classify" in rb.stderr)

# --- AC-DD-03: the measured OBS carries the ingested run's timestamp in its provenance
meas = [o for o in obs if o["evidence_class"] == "measured"]
res["AC-DD-03"] = (len(meas) == 1
                   and "ingested 20" in meas[0]["provenance"]["derivation"])

# --- AC-DD-04: re-running discovery over the unchanged fixture is byte-identical
b1 = io.open(DPATH, "rb").read()
eng("discover", "--ledger", "L.json", "--repo", "r",
    "--narrated", os.path.join(w, "narr.json"))
res["AC-DD-04"] = io.open(DPATH, "rb").read() == b1

# --- AC-DD-05: canonical_match populated exactly when an AC id matches
withm = [o for o in obs if o.get("canonical_match")]
res["AC-DD-05"] = len(withm) == 1 and withm[0]["canonical_match"] == "AC-1"

# --- AC-DD-06: the .md twin regenerates; a hand edit is overwritten AND named -- on
# stderr, so --json stdout stays parseable on this exact path (fresh-review MEDIUM)
TWIN = os.path.join(repo, "discovery", "CANDIDATE-DELTA.md")
orig = io.open(TWIN, encoding="utf-8").read()
io.open(TWIN, "a").write("HAND EDIT\n")
rt = eng("discover", "--ledger", "L.json", "--repo", "r",
         "--narrated", os.path.join(w, "narr.json"), "--json")
try:
    json.loads(rt.stdout)
    parseable = True
except ValueError:
    parseable = False
res["AC-DD-06"] = (io.open(TWIN, encoding="utf-8").read() == orig
                   and "overwritten" in rt.stderr and parseable)

ids = [o["id"] for o in obs]
# --- AC-CU-06: no batch path -- a comma list is refused, and the CLI offers no bulk flag
rc = eng("curate", "--ledger", "L.json", "--repo", "r",
         "--obs", ids[0] + "," + ids[1], "--verdict", "preserve")
hp = eng("curate", "--help")
res["AC-CU-06"] = (rc.returncode == 2 and "batch" in rc.stderr.lower()
                   and "--all" not in hp.stdout and "--accept" not in hp.stdout)

# --- AC-CU-01: promote over uncurated OBS refuses naming them; nothing moves; pr-ready
# blocks (attributable: it was green before the delta existed)
eng("curate", "--ledger", "L.json", "--repo", "r", "--obs", meas[0]["id"],
    "--verdict", "preserve")
rp = eng("promote", "--ledger", "L.json", "--repo", "r")
blocked = eng("phase", "--ledger", "L.json", "--repo", "r", "--require", "pr-ready")
res["AC-CU-01"] = (before == 0 and rp.returncode == 1 and "REFUSED" in rp.stderr
                   and any(i in rp.stderr for i in ids if i != meas[0]["id"])
                   and not os.path.isfile(os.path.join(repo, "discovery",
                                                       "CANONICAL.json"))
                   and blocked.returncode == 1
                   and "INV-CURATION-01" in blocked.stdout + blocked.stderr)

# --- judge the rest: one fix, one undefined, the rest preserve
fix_id, und_id = narr[0]["id"], narr[1]["id"]
for oid in ids:
    if oid == meas[0]["id"]:
        continue
    v = "fix" if oid == fix_id else ("undefined" if oid == und_id else "preserve")
    eng("curate", "--ledger", "L.json", "--repo", "r", "--obs", oid, "--verdict", v)
rp = eng("promote", "--ledger", "L.json", "--repo", "r", "--json")
canon = json.load(io.open(os.path.join(repo, "discovery", "CANONICAL.json"),
                          encoding="utf-8"))
lineage = set(it.get("derived_from") for it in canon["items"])
# --- AC-CU-02: preserve promoted with derived_from lineage
res["AC-CU-02"] = (rp.returncode == 0 and meas[0]["id"] in lineage
                   and all(it.get("derived_from") for it in canon["items"]))
# --- AC-CU-03: fix -> ISSUES-DEFERRED work item, never canonical
issues = io.open(os.path.join(repo, "ISSUES-DEFERRED.md"), encoding="utf-8").read()
res["AC-CU-03"] = fix_id in issues and fix_id not in lineage
# --- AC-CU-04: undefined stays OPEN in the readouts
rd = eng("dashboard", "--ledger", "L.json", "--json")
dash = json.loads(rd.stdout)
res["AC-CU-04"] = und_id in (dash.get("candidate_delta", {}).get("r", {})
                             .get("undefined_open") or [])
# --- AC-CU-05: re-curation SUPERSEDES; both records stay retrievable
eng("curate", "--ledger", "L.json", "--repo", "r", "--obs", und_id,
    "--verdict", "preserve")
led = json.load(io.open(os.path.join(w, "L.json"), encoding="utf-8"))
recs = [c for c in led.get("curation", []) if c["obs_id"] == und_id]
res["AC-CU-05"] = (len(recs) == 2 and recs[0]["verdict"] == "undefined"
                   and recs[1]["verdict"] == "preserve")

# --- AC-DD-07: --path bounds the mechanical scans; empty match refuses named; the bound
# is recorded in the delta AND surfaced in the human-facing twin (field-found before
# FIELD-RUN-001; twin/seal/empty gaps closed after the fresh review)
rb1 = eng("discover", "--ledger", "L.json", "--repo", "r", "--path", "src/app.py",
          "--narrated", os.path.join(w, "narr.json"), "--json")
db = json.load(io.open(DPATH, encoding="utf-8"))
bnd = [o for o in db["observations"] if o["evidence_class"] != "narrated"]
TWINB = io.open(os.path.join(repo, "discovery", "CANDIDATE-DELTA.md"),
                encoding="utf-8").read()
rb2 = eng("discover", "--ledger", "L.json", "--repo", "r", "--path", "no/such/dir")
# empty bound must refuse, not silently scan the whole repo (fresh-review MEDIUM)
rb3 = eng("discover", "--ledger", "L.json", "--repo", "r", "--path", "",
          "--narrated", os.path.join(w, "narr.json"))
# ./src normalizes rather than being misattributed to a nonexistent path (fresh-review LOW)
rb4 = eng("discover", "--ledger", "L.json", "--repo", "r", "--path", "./src/app.py",
          "--narrated", os.path.join(w, "narr.json"))
# the bound is SEALED: hand-editing path in a bounded delta breaks the seal (fresh-review MED)
raw_b = json.load(io.open(DPATH, encoding="utf-8"))    # rb4 left a bounded delta
raw_b["path"] = "totally/other"
io.open(DPATH, "w", encoding="utf-8").write(json.dumps(raw_b, indent=2))
rb5 = eng("curate", "--ledger", "L.json", "--repo", "r", "--obs",
          raw_b["observations"][0]["id"], "--verdict", "preserve")
res["AC-DD-07"] = (rb1.returncode == 0 and db.get("path") == "src/app.py"
                   and bnd and all(o["provenance"]["files"][0].startswith("src/app.py")
                                   for o in bnd)
                   and "BOUNDED" in TWINB and "src/app.py" in TWINB
                   and rb2.returncode == 2 and "matches no tracked file" in rb2.stderr
                   and rb3.returncode == 2 and "empty" in rb3.stderr
                   and rb4.returncode == 0
                   and rb5.returncode == 2 and "seal" in rb5.stderr)
# restore the unbounded delta for the cases below; the rerun must succeed or the seal
# regressions afterward would silently run against a bounded delta (fresh-review nit)
rr0 = eng("discover", "--ledger", "L.json", "--repo", "r",
          "--narrated", os.path.join(w, "narr.json"))
res["AC-DD-07"] = bool(res["AC-DD-07"] and rr0.returncode == 0)

# --- regression: malformed narrated input (non-string ref) is a NAMED exit-2 refusal,
# never a TypeError traceback (fresh-review MEDIUM, reproduced pre-release)
io.open(os.path.join(w, "badref.json"), "w").write(json.dumps(
    [{"type": "behavior", "statement": "x", "files": [3]}]))
rr = eng("discover", "--ledger", "L.json", "--repo", "r",
         "--narrated", os.path.join(w, "badref.json"))
res["review-m1"] = rr.returncode == 2 and "list of strings" in rr.stderr

# --- regression: a class-flip hand edit (narrated -> measured) breaks the integrity
# seal even though the OBS id survives; curate refuses exit 2 (fresh-review MEDIUM)
raw = json.load(io.open(DPATH, encoding="utf-8"))
for o in raw["observations"]:
    if o["evidence_class"] == "narrated":
        o["evidence_class"] = "measured"
        break
io.open(DPATH, "w", encoding="utf-8").write(json.dumps(raw, indent=2))
rf = eng("curate", "--ledger", "L.json", "--repo", "r", "--obs", ids[0],
         "--verdict", "preserve")
res["review-m3"] = rf.returncode == 2 and "seal" in rf.stderr

# --- regression: a STRUCTURALLY broken observation (provenance as a list) is a named
# malformation everywhere -- curate exit 2, dashboard/phase never traceback
# (fresh-review HIGH, reproduced pre-release)
raw["observations"][0]["provenance"] = ["not", "a", "dict"]
io.open(DPATH, "w", encoding="utf-8").write(json.dumps(raw, indent=2))
rh = eng("curate", "--ledger", "L.json", "--repo", "r", "--obs", ids[0],
         "--verdict", "preserve")
rdash = eng("dashboard", "--ledger", "L.json", "--json")
rph = eng("phase", "--ledger", "L.json", "--repo", "r", "--require", "pr-ready")
res["review-h1"] = (rh.returncode == 2 and "shape invalid" in rh.stderr
                    and rdash.returncode == 0
                    and "Traceback" not in rdash.stderr
                    and rph.returncode == 1 and "Traceback" not in rph.stderr
                    and "CANDIDATE-DELTA invalido" in rph.stdout + rph.stderr)

side = os.path.join(kit, "reports", "junit")
os.makedirs(side, exist_ok=True)
io.open(os.path.join(side, ".delta-cases.json"), "w", encoding="utf-8").write(
    json.dumps(res))
bad = [k for k, v in res.items() if not v]
print("OK %d cases" % len(res) if not bad else "BAD " + ",".join(sorted(bad)))
PY
)
case "$T123" in
  OK*) PASS=$((PASS+1)); echo "  ok   candidate-delta: $T123";;
  *)   FAIL=$((FAIL+1)); echo "  FAIL $T123";;
esac

echo "== T124 (1.69.0): fidelity -- a vector of measured dimensions; advisory can NEVER gate (ADR-014) =="
T124=$("$PY" - "$KIT" <<'PY'
import io, json, os, subprocess, sys, tempfile
kit = sys.argv[1]
ENG = os.path.join(kit, ".claude", "skills", "uscha-devloop", "qa_ledger.py")
res = {}
w = tempfile.mkdtemp(); repo = os.path.join(w, "r")
os.makedirs(os.path.join(repo, "src"))

def sh(*a):
    return subprocess.run(list(a), cwd=repo, capture_output=True, text=True)

def eng(*a):
    return subprocess.run([sys.executable, ENG] + list(a), cwd=w, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")

sh("git", "init", "-b", "main"); sh("git", "config", "user.email", "t@t")
sh("git", "config", "user.name", "t")
io.open(os.path.join(repo, "src", "app.py"), "w").write(
    "def facturar(total):\n    return total\n")
io.open(os.path.join(repo, "orphan.py"), "w").write("def _hidden():\n    return 0\n")
# a PUBLIC def OUTSIDE src -> a canonical static item outside the src bound, so AC-FV-06
# exercises the DENOMINATOR scoping, not just the file scan (fresh-review LOW)
os.makedirs(os.path.join(repo, "pkg"))
io.open(os.path.join(repo, "pkg", "mod.py"), "w").write("def exported():\n    return 1\n")
os.makedirs(os.path.join(repo, "goldens"))
io.open(os.path.join(repo, "goldens", "case.approved.json"), "w").write("{}\n")
sh("git", "add", "-A"); sh("git", "commit", "-m", "base")
io.open(os.path.join(w, "c.json"), "w").write(json.dumps({
    "defaults": {},
    "repos": [{"name": "r", "path": "r", "type": "python"}],
    "integration": {"enabled": False}}))
eng("init", "--config", "c.json", "--out", "L.json")
eng("log-gate", "--ledger", "L.json", "--repo", "r", "--iteration", "1",
    "--kind", "golden-diff", "--verdict", "pass")
io.open(os.path.join(w, "narr.json"), "w").write(json.dumps([
    {"type": "behavior", "statement": "facturar returns the total",
     "files": ["src/app.py:1"]}]))
eng("discover", "--ledger", "L.json", "--repo", "r",
    "--narrated", os.path.join(w, "narr.json"))
delta = json.load(io.open(os.path.join(repo, "discovery", "CANDIDATE-DELTA.json"),
                          encoding="utf-8"))
ids = [o["id"] for o in delta["observations"]]

# --- AC-FV-04 first half: uncurated OBS exist -> closure strictly < 1.0
r1 = eng("fidelity", "--ledger", "L.json", "--repo", "r", "--json")
f1 = json.loads(r1.stdout)["dimensions"]
half1 = (f1["curation_closure"]["value"] is not None
         and f1["curation_closure"]["value"] < 1.0)

for oid in ids:
    eng("curate", "--ledger", "L.json", "--repo", "r", "--obs", oid,
        "--verdict", "preserve")
eng("promote", "--ledger", "L.json", "--repo", "r")
r2 = eng("fidelity", "--ledger", "L.json", "--repo", "r", "--json")
f2 = json.loads(r2.stdout)["dimensions"]

# --- AC-FV-01: every v0 dimension present, each with provenance and class
want = {"traceability", "behavior", "contracts", "curation_closure",
        "unexplained_code", "semantic"}
res["AC-FV-01"] = (set(f2) == want
                   and all(d.get("provenance") and d.get("class") in
                           ("measured", "advisory") for d in f2.values())
                   and f2["semantic"]["class"] == "advisory")
# --- AC-FV-02: a file with no lineage -> unexplained_code > 0, file NAMED
res["AC-FV-02"] = (f2["unexplained_code"]["value"] is not None
                   and f2["unexplained_code"]["value"] > 0
                   and "orphan.py" in f2["unexplained_code"]["files"])
# --- AC-FV-04 second half: all curated -> exactly 1.0
res["AC-FV-04"] = half1 and f2["curation_closure"]["value"] == 1.0
# --- AC-FV-05: deterministic -- same inputs, byte-identical output
r3 = eng("fidelity", "--ledger", "L.json", "--repo", "r", "--json")
res["AC-FV-05"] = r2.stdout == r3.stdout and r2.stdout
# --- AC-FV-03: advisory-as-blocking is an ENGINE refusal on both doors
io.open(os.path.join(w, "cg.json"), "w").write(json.dumps(
    {"defaults": {"fidelity": {"gate": ["semantic"]}}}))
rg = eng("fidelity", "--ledger", "L.json", "--repo", "r",
         "--config", os.path.join(w, "cg.json"))
rl = eng("log-gate", "--ledger", "L.json", "--repo", "r", "--iteration", "2",
         "--kind", "semantic", "--verdict", "fail")
res["AC-FV-03"] = (rg.returncode == 2 and "INV-ADVISORY-01" in rg.stderr
                   and rl.returncode == 2 and "invalid choice" in rl.stderr)
res["AC-FV-05"] = bool(res["AC-FV-05"])

# --- regression: a config that cannot be PARSED cannot silently disable the refusal
# door (fresh-review HIGH, reproduced pre-release)
io.open(os.path.join(w, "broken.json"), "w").write("{ not json")
rb = eng("fidelity", "--ledger", "L.json", "--repo", "r",
         "--config", os.path.join(w, "broken.json"))
res["review-h2"] = rb.returncode == 2 and "unreadable" in rb.stderr

# --- AC-FV-06: fidelity respects the SAME --path bound the delta was produced with (user
# decision, FR-001) -- unexplained_code measures only files under the bound, and the scope
# is NAMED. Unbounded, orphan.py is unexplained; bounded to src, it is out of scope.
eng("discover", "--ledger", "L.json", "--repo", "r", "--path", "src",
    "--narrated", os.path.join(w, "narr.json"))
dl = json.load(io.open(os.path.join(repo, "discovery", "CANDIDATE-DELTA.json"),
                       encoding="utf-8"))
for o in dl["observations"]:
    eng("curate", "--ledger", "L.json", "--repo", "r", "--obs", o["id"],
        "--verdict", "preserve")
eng("promote", "--ledger", "L.json", "--repo", "r")
rbnd = eng("fidelity", "--ledger", "L.json", "--repo", "r", "--json")
fb = json.loads(rbnd.stdout)
uc = fb["dimensions"]["unexplained_code"]
ct = fb["dimensions"]["contracts"]
# CANONICAL still holds exported@pkg/mod.py (unbounded promote in AC-FV-01..05 merged it),
# but a src-bounded fidelity must NOT count it against contracts -- denominator scoped too
res["AC-FV-06"] = (fb.get("path") == "src"
                   and "orphan.py" not in (uc.get("files") or [])
                   and "pkg/mod.py" not in (uc.get("files") or [])
                   and "bounded to src" in uc["provenance"]
                   and uc["value"] == 0.0
                   and ct["value"] == 1.0 and "bounded to src" in ct["provenance"])

# --- regression: a malformed delta is exit 2 for fidelity too, never mislabeled as
# "no delta" (fresh-review MEDIUM, reproduced pre-release)
io.open(os.path.join(repo, "discovery", "CANDIDATE-DELTA.json"), "w").write("{ nope")
rm = eng("fidelity", "--ledger", "L.json", "--repo", "r")
res["review-m4"] = (rm.returncode == 2 and "malformed" in rm.stderr
                    and "no delta" not in rm.stdout)

side = os.path.join(kit, "reports", "junit")
os.makedirs(side, exist_ok=True)
io.open(os.path.join(side, ".fidelity-cases.json"), "w", encoding="utf-8").write(
    json.dumps(res))
bad = [k for k, v in res.items() if not v]
print("OK %d cases" % len(res) if not bad else "BAD " + ",".join(sorted(bad)))
PY
)
case "$T124" in
  OK*) PASS=$((PASS+1)); echo "  ok   fidelity: $T124";;
  *)   FAIL=$((FAIL+1)); echo "  FAIL $T124";;
esac

echo "== T125 (1.72.0): IR -- the canonical package extracts into a typed graph (M2, ADR-015) =="
T125=$("$PY" - "$KIT" <<'PY'
import io, json, os, subprocess, sys, tempfile
kit = sys.argv[1]
ENG = os.path.join(kit, ".claude", "skills", "uscha-devloop", "qa_ledger.py")
res = {}
w = tempfile.mkdtemp(); repo = os.path.join(w, "r")
os.makedirs(os.path.join(repo, "src")); os.makedirs(os.path.join(repo, "docs", "adr"))

def sh(*a):
    return subprocess.run(list(a), cwd=repo, capture_output=True, text=True)

def eng(*a):
    return subprocess.run([sys.executable, ENG] + list(a), cwd=w, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")

sh("git", "init", "-b", "main"); sh("git", "config", "user.email", "t@t")
sh("git", "config", "user.name", "t")
io.open(os.path.join(repo, "src", "app.py"), "w").write(
    "def facturar(total):\n    return total\n")
# ACCEPTANCE: two id'd criteria + one checkbox WITHOUT an id (must land in untyped)
io.open(os.path.join(repo, "ACCEPTANCE.md"), "w").write(
    "# Acceptance\n\n- [x] AC-01 - facturar returns the total\n"
    "- [ ] AC-DD-07 - a bounded scan\n- [ ] a checkbox with no traceable id\n")
# CONSTITUTION: one invariant heading
io.open(os.path.join(repo, "CONSTITUTION.md"), "w").write(
    "# Constitution\n\n- **INV-CURATION-01 \x2d\x2d nothing promotes unjudged.** body\n")
# an ADR that governs the invariant and references an AC
io.open(os.path.join(repo, "docs", "adr", "ADR-001-x.md"), "w").write(
    "---\ngovity: x\n---\n# ADR-001: the curation gate\n\n## Status: Accepted\n\n"
    "Enforces INV-CURATION-01. Verifies (AC-01).\n")
io.open(os.path.join(repo, "ACCEPTANCE.md"), "a").write("")
sh("git", "add", "-A"); sh("git", "commit", "-m", "base")
io.open(os.path.join(w, "c.json"), "w").write(json.dumps({
    "defaults": {}, "repos": [{"name": "r", "path": "r", "type": "python"}],
    "integration": {"enabled": False}}))
eng("init", "--config", "c.json", "--out", "L.json")

# --- AC-IR-01: well-formed typed graph; every node has id/type/source, edges resolvable
r1 = eng("ir-extract", "--ledger", "L.json", "--repo", "r", "--json")
IRP = os.path.join(repo, "ir", "IR.json")
g = json.load(io.open(IRP, encoding="utf-8"))
node_ids = {nd["id"] for nd in g["nodes"]}
res["AC-IR-01"] = (r1.returncode == 0 and g["schema_version"] == "0.1"
                   and g["nodes"] and all(nd.get("id") and nd.get("type") in
                       ("REQ", "INV", "AC", "CONTRACT", "DECISION", "NFR", "GOLDEN",
                        "OBS", "CURATION", "EVIDENCE") and nd.get("source", {}).get("file")
                       for nd in g["nodes"])
                   and all(e["from"] in node_ids and e["to"] in node_ids
                           for e in g["edges"] if e["type"] != "supersedes"))

# --- AC-IR-02: the id-less checkbox lands in untyped, counted, never guessed
res["AC-IR-02"] = (any("no traceable id" in u["text"] for u in g["untyped"])
                   and g["stats"]["untyped"] >= 1
                   and g["stats"]["untyped_rate"] > 0
                   and not any(nd["statement"] == "a checkbox with no traceable id"
                               for nd in g["nodes"]))

# --- AC-IR-03: native ids reused (not content-addressed); re-extraction byte-identical;
# edges derived from real references (ADR-001 governs INV-CURATION-01, references AC-01)
have = {nd["id"] for nd in g["nodes"]}
b1 = io.open(IRP, "rb").read()
eng("ir-extract", "--ledger", "L.json", "--repo", "r")
res["AC-IR-03"] = ({"AC-01", "AC-DD-07", "INV-CURATION-01", "ADR-001"} <= have
                   and io.open(IRP, "rb").read() == b1
                   and any(e["from"] == "ADR-001" and e["to"] == "INV-CURATION-01"
                           and e["type"] == "DECISION->INV" for e in g["edges"])
                   and any(e["from"] == "ADR-001" and e["to"] == "AC-01"
                           for e in g["edges"]))

# --- AC-IR-04: ir-render regenerates; extract -> render -> extract is stable
eng("ir-render", "--ledger", "L.json", "--repo", "r")
eng("ir-extract", "--ledger", "L.json", "--repo", "r")
res["AC-IR-04"] = io.open(IRP, "rb").read() == b1 and os.path.isfile(
    os.path.join(repo, "ir", "IR.md"))

# --- AC-IR-05: an unknown schema_version / hand edit is exit 2, never mis-read
gg = json.load(io.open(IRP, encoding="utf-8"))
gg["schema_version"] = "9.9"
io.open(IRP, "w", encoding="utf-8").write(json.dumps(gg))
r5a = eng("ir-render", "--ledger", "L.json", "--repo", "r")
gg["schema_version"] = "0.1"; gg["nodes"][0]["statement"] = "TAMPERED"
io.open(IRP, "w", encoding="utf-8").write(json.dumps(gg))
r5b = eng("ir-render", "--ledger", "L.json", "--repo", "r")
# a doctored SUMMARY (stats) must also trip the seal -- ir-render would faithfully print a
# lie otherwise (fresh-review MEDIUM, reproduced pre-release)
eng("ir-extract", "--ledger", "L.json", "--repo", "r")
gg2 = json.load(io.open(IRP, encoding="utf-8"))
gg2["stats"]["nodes"] = 999; gg2["stats"]["untyped_rate"] = 0.9999
io.open(IRP, "w", encoding="utf-8").write(json.dumps(gg2))
r5c = eng("ir-render", "--ledger", "L.json", "--repo", "r")
res["AC-IR-05"] = (r5a.returncode == 2 and "schema_version" in r5a.stderr
                   and r5b.returncode == 2 and "seal" in r5b.stderr
                   and r5c.returncode == 2 and "seal" in r5c.stderr)

# --- AC-IR-06: fidelity --ir reproduces v0's curation_closure via graph path query
eng("ir-extract", "--ledger", "L.json", "--repo", "r")     # restore a valid graph
io.open(os.path.join(w, "narr.json"), "w").write(json.dumps([
    {"type": "behavior", "statement": "facturar returns the total",
     "files": ["src/app.py:1"]}]))
eng("discover", "--ledger", "L.json", "--repo", "r", "--narrated",
    os.path.join(w, "narr.json"))
dl = json.load(io.open(os.path.join(repo, "discovery", "CANDIDATE-DELTA.json"),
                       encoding="utf-8"))
for o in dl["observations"]:
    eng("curate", "--ledger", "L.json", "--repo", "r", "--obs", o["id"],
        "--verdict", "preserve")
eng("promote", "--ledger", "L.json", "--repo", "r")
v0 = json.loads(eng("fidelity", "--ledger", "L.json", "--repo", "r",
                    "--json").stdout)["dimensions"]["curation_closure"]["value"]
vir = json.loads(eng("fidelity", "--ledger", "L.json", "--repo", "r", "--ir",
                     "--json").stdout)["dimensions"]["curation_closure"]
res["AC-IR-06"] = (v0 == 1.0 and vir["value"] == v0
                   and "IR path query" in vir["provenance"])

side = os.path.join(kit, "reports", "junit")
os.makedirs(side, exist_ok=True)
io.open(os.path.join(side, ".ir-cases.json"), "w", encoding="utf-8").write(json.dumps(res))
bad = [k for k, v in res.items() if not v]
print("OK %d cases" % len(res) if not bad else "BAD " + ",".join(sorted(bad)))
PY
)
case "$T125" in
  OK*) PASS=$((PASS+1)); echo "  ok   ir: $T125";;
  *)   FAIL=$((FAIL+1)); echo "  FAIL $T125";;
esac

echo "== T126 (1.73.0): compiler contract -- the LLM is a validated backend; only facts gate (M3, ADR-016) =="
T126=$("$PY" - "$KIT" <<'PY'
import io, json, os, shutil, subprocess, sys, tempfile
kit = sys.argv[1]
ENG = os.path.join(kit, ".claude", "skills", "uscha-devloop", "qa_ledger.py")
FIX = os.path.join(kit, "tests", "fixtures", "compile-ref")
IR = os.path.join(FIX, "IR.json")
res = {}
w = tempfile.mkdtemp()

def comp(name):
    return os.path.join(FIX, name, "COMPILATION.json")

def cv(name):
    r = subprocess.run([sys.executable, ENG, "compile-validate", "--ir", IR,
                        "--compilation", comp(name), "--json"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    try:
        rep = json.loads(r.stdout)
    except ValueError:
        rep = {}
    return r.returncode, rep

def eng(*a):
    return subprocess.run([sys.executable, ENG] + list(a), cwd=w, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")

# --- AC-CC-01: the opus reference compilation validates; ids resolve, hashes match; and the
# reference IR genuinely reproduces from canonical/ via ir-extract (guards fixture drift)
rc, rep = cv("opus")
shutil.copytree(os.path.join(FIX, "canonical"), os.path.join(w, "canon"))
io.open(os.path.join(w, "cir.json"), "w").write(json.dumps({
    "defaults": {}, "repos": [{"name": "c", "path": "canon", "type": "python"}],
    "integration": {"enabled": False}}))
eng("init", "--config", "cir.json", "--out", "Lir.json")
eng("ir-extract", "--ledger", "Lir.json", "--repo", "c")
gen_ir = json.load(io.open(os.path.join(w, "canon", "ir", "IR.json"), encoding="utf-8"))
committed_ir = json.load(io.open(IR, encoding="utf-8"))
res["AC-CC-01"] = (rc == 0 and rep.get("valid") is True and not rep.get("errors")
                   and gen_ir.get("_integrity") == committed_ir.get("_integrity"))

# --- AC-CC-02: the manifest cannot lie -- an unknown IR id, a hash that does not match the
# bytes on disk, a hand-edited seal, and a unit path that escapes the compilation directory
# each exit 2 naming the fault (violations print to stderr, exit code is the machine signal)
rc_uid, rep_uid = cv("bad-unknown-id")
rc_h, rep_h = cv("bad-hash")
shutil.copytree(os.path.join(FIX, "opus"), os.path.join(w, "opus"))
cp = os.path.join(w, "opus", "COMPILATION.json")
tc = json.load(io.open(cp, encoding="utf-8"))
tc["unresolved_intent"][0]["decision"] = "TAMPERED after production"
io.open(cp, "w", encoding="utf-8").write(json.dumps(tc))
rseal = subprocess.run([sys.executable, ENG, "compile-validate", "--ir", IR,
                        "--compilation", cp], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
# a unit that escapes the compilation directory (a `..` path) must be refused -- otherwise a
# manifest can name any file on disk as a "source" unit and pass on that file's hash
esc = os.path.join(w, "escape")
shutil.copytree(os.path.join(FIX, "opus"), esc)
ecp = os.path.join(esc, "COMPILATION.json")
ec = json.load(io.open(ecp, encoding="utf-8"))
ec["source"][0]["unit"] = "../secret.py"
io.open(ecp, "w", encoding="utf-8").write(json.dumps(ec))
re_esc = subprocess.run([sys.executable, ENG, "compile-validate", "--ir", IR,
                         "--compilation", ecp, "--json"], capture_output=True, text=True,
                        encoding="utf-8", errors="replace")
try:
    rep_esc = json.loads(re_esc.stdout)
except ValueError:
    rep_esc = {}
# a malformed element (a list of strings where objects are required) must be a clean exit-2
# mechanical refusal, NEVER an AttributeError traceback (exit 1) -- the trust boundary
mal = os.path.join(w, "malformed")
os.makedirs(mal)
io.open(os.path.join(mal, "COMPILATION.json"), "w").write(json.dumps({
    "schema_version": "compile/0.1",
    "canonical_ir": {"ir_hash": committed_ir.get("_integrity"), "schema_version": "0.1"},
    "target_stack": "python", "implementation_constraints": [],
    "source": ["source/x.py"], "tests": [], "trace_manifest": [],
    "unresolved_intent": [], "compilation_report": {}}))
r_mal = subprocess.run([sys.executable, ENG, "compile-validate", "--ir", IR,
                        "--compilation", os.path.join(mal, "COMPILATION.json"), "--json"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
try:
    rep_mal = json.loads(r_mal.stdout)
except ValueError:
    rep_mal = {}
res["AC-CC-02"] = (rc_uid == 2 and any("not an IR node" in e for e in rep_uid.get("errors", []))
                   and rc_h == 2 and any("hash mismatch" in e for e in rep_h.get("errors", []))
                   and rseal.returncode == 2 and "seal" in rseal.stderr
                   and re_esc.returncode == 2
                   and any("escapes the compilation directory" in e
                           for e in rep_esc.get("errors", []))
                   and r_mal.returncode == 2 and not r_mal.stderr.startswith("Traceback")
                   and any("must be an object" in e for e in rep_mal.get("errors", [])))

# --- AC-CC-03: an ir_hash this repo does not reproduce is refused, never assumed
rc_ir, rep_ir = cv("bad-ir-hash")
res["AC-CC-03"] = (rc_ir == 2 and any("reference IR seal" in e for e in rep_ir.get("errors", [])))

# --- AC-CC-04: a degenerate manifest + empty unresolved_intent are ADVISORY: flagged, exit 0
rc_d, rep_d = cv("degenerate")
adv = rep_d.get("advisory", {})
res["AC-CC-04"] = (rc_d == 0 and rep_d.get("valid") is True
                   and adv.get("degenerate") is True and adv.get("empty_unresolved") is True)

# --- AC-CC-05: ingest records unresolved_intent as content-addressed UINT objects + an
# ISSUES-DEFERRED mirror; re-ingest is idempotent PER REPO (never a duplicate), the same
# compilation into a DIFFERENT repo is its own record (no cross-repo collision), and two
# unresolved_intent entries that resolve to the same UINT dedupe within one ingest
os.makedirs(os.path.join(w, "r"))
os.makedirs(os.path.join(w, "r2"))
os.makedirs(os.path.join(w, "rd"))
io.open(os.path.join(w, "c.json"), "w").write(json.dumps({
    "defaults": {}, "repos": [{"name": "r", "path": "r", "type": "python"},
                              {"name": "r2", "path": "r2", "type": "python"},
                              {"name": "rd", "path": "rd", "type": "python"}],
    "integration": {"enabled": False}}))
eng("init", "--config", "c.json", "--out", "L.json")
i1 = json.loads(eng("compile-ingest", "--ledger", "L.json", "--repo", "r", "--ir", IR,
                    "--compilation", comp("opus"), "--json").stdout)
i2 = json.loads(eng("compile-ingest", "--ledger", "L.json", "--repo", "r", "--ir", IR,
                    "--compilation", comp("opus"), "--json").stdout)
# the SAME compilation into a different repo must NOT read as superseded (F1 regression)
i_r2 = json.loads(eng("compile-ingest", "--ledger", "L.json", "--repo", "r2", "--ir", IR,
                      "--compilation", comp("opus"), "--json").stdout)
# a compilation with two entries resolving to the same UINT dedupes to one (F3 regression)
i_dup = json.loads(eng("compile-ingest", "--ledger", "L.json", "--repo", "rd", "--ir", IR,
                       "--compilation", comp("dup-intent"), "--json").stdout)
dupm = io.open(os.path.join(w, "rd", "ISSUES-DEFERRED.md"), encoding="utf-8").read()
L = json.load(io.open(os.path.join(w, "L.json"), encoding="utf-8"))
idm = io.open(os.path.join(w, "r", "ISSUES-DEFERRED.md"), encoding="utf-8").read()
res["AC-CC-05"] = (len(i1["unresolved_intent"]) == 3
                   and all(u.startswith("UINT-") for u in i1["unresolved_intent"])
                   and len(i1["issues_deferred_new"]) == 3
                   and i2["superseded"] is True and i2["issues_deferred_new"] == []
                   and i_r2["superseded"] is False
                   and len(L.get("compilations", [])) == 3
                   and idm.count("UINT-") == 3
                   and len(i_dup["unresolved_intent"]) == 1
                   and dupm.count("UINT-") == 1)

# --- AC-CC-06: by-construction unexplained_code -- a source unit absent from the manifest
i3 = json.loads(eng("compile-ingest", "--ledger", "L.json", "--repo", "r", "--ir", IR,
                    "--compilation", comp("unexplained"), "--json").stdout)
res["AC-CC-06"] = (i3["unexplained_units"] == ["source/b.py"])

# --- AC-CC-07: two reference compilations, two different models, both validate: backend-blind
rc_o, rep_o = cv("opus")
rc_s, rep_s = cv("sonnet")
res["AC-CC-07"] = (rc_o == 0 and rep_o.get("valid") is True
                   and rc_s == 0 and rep_s.get("valid") is True
                   and rep_o.get("advisory", {}).get("degenerate") is False
                   and rep_s.get("advisory", {}).get("degenerate") is False)

side = os.path.join(kit, "reports", "junit")
os.makedirs(side, exist_ok=True)
io.open(os.path.join(side, ".compile-cases.json"), "w", encoding="utf-8").write(json.dumps(res))
bad = [k for k, v in res.items() if not v]
print("OK %d cases" % len(res) if not bad else "BAD " + ",".join(sorted(bad)))
PY
)
case "$T126" in
  OK*) PASS=$((PASS+1)); echo "  ok   compile: $T126";;
  *)   FAIL=$((FAIL+1)); echo "  FAIL $T126";;
esac

echo "== T127 (1.74.0): bootstrap -- a bounded subsystem's identity is its canonical package + a withheld oracle (M4, ADR-017) =="
T127=$("$PY" - "$KIT" <<'PY'
import io, json, os, subprocess, sys, tempfile
kit = sys.argv[1]
ENG = os.path.join(kit, ".claude", "skills", "uscha-devloop", "qa_ledger.py")
BF = os.path.join(kit, "tests", "fixtures", "bootstrap-golden-hook")
IR = os.path.join(BF, "IR.json")
ORACLE = os.path.join(BF, "oracle", "ORACLE.json")
ORIGINAL = os.path.join(kit, "hooks", "block-approved-writes.py")
res = {}
w = tempfile.mkdtemp()

def eng(*a):
    return subprocess.run([sys.executable, ENG] + list(a), cwd=w, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")

def oracle(impl):
    r = subprocess.run([sys.executable, ENG, "bootstrap-oracle", "--impl", impl,
                        "--oracle", ORACLE, "--json"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    try:
        rep = json.loads(r.stdout)
    except ValueError:
        rep = {}
    return r.returncode, rep

# AC-BS-01: the withheld oracle runs against a real impl and is a measured fact; the canonical
# system (the original guard) is all-green, exit 0
rc_o, rep_o = oracle(ORIGINAL)
res["AC-BS-01"] = (rc_o == 0 and rep_o.get("oracle_green") is True
                   and rep_o.get("passed") == rep_o.get("total") and rep_o.get("total", 0) >= 20)

# AC-BS-02: the oracle is decisive and names divergences -- a guard that allows a blocked case
# fails, case-by-case, exit 1; the runner consults no model
broken = os.path.join(BF, "broken", "source", "guard.py")
rc_b, rep_b = oracle(broken)
res["AC-BS-02"] = (rc_b == 1 and rep_b.get("oracle_green") is False
                   and rep_b.get("failed", 0) > 0
                   and any(not r["ok"] for r in rep_b.get("results", [])))

# AC-BS-03: the maker!=checker wall -- no compiled source references the withheld oracle
def refs_oracle(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            t = fh.read().lower()
        return "oracle" in t or "expected_exit" in t
    except OSError:
        return True
srcs = [os.path.join(BF, d, "source", "guard.py") for d in
        ("c-opus", "c-sonnet", "c-haiku", "c-opus-r2", "c-sonnet-r2")]
res["AC-BS-03"] = all(os.path.isfile(s) and not refs_oracle(s) for s in srcs)

# AC-BS-04: all three round-1 compilations compile-validate against the pinned canonical IR
def cv(comp):
    r = subprocess.run([sys.executable, ENG, "compile-validate", "--ir", IR,
                        "--compilation", comp, "--json"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    try:
        return json.loads(r.stdout).get("valid")
    except ValueError:
        return False
res["AC-BS-04"] = all(cv(os.path.join(BF, d, "COMPILATION.json")) is True
                      for d in ("c-opus", "c-sonnet", "c-haiku"))

# AC-BS-05: variance proves the three genuinely differ; advisory, never gates
rv = subprocess.run([sys.executable, ENG, "bootstrap-variance", "--impls",
                     os.path.join(BF, "c-opus", "source", "guard.py"),
                     os.path.join(BF, "c-sonnet", "source", "guard.py"),
                     os.path.join(BF, "c-haiku", "source", "guard.py"), "--json"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace")
try:
    vrep = json.loads(rv.stdout)
except ValueError:
    vrep = {}
res["AC-BS-05"] = (rv.returncode == 0 and vrep.get("all_distinct") is True
                   and vrep.get("advisory") is True
                   and len(vrep.get("implementations", [])) == 3)

# AC-BS-06: the S-gap loop is measured and bounded (N=2) -- a round-1 divergence records its
# failing cases to the ledger (the S-gap catalog is a measured fact, not narrated), and the
# improvement round closes the unanimous interpreter gap for at least one independent compiler
# (c-sonnet-r2 recompiled from the improved canonical package is oracle-green). Partial
# convergence is the honest outcome: the other round-2 recompile refines the gap rather than
# closing it, and N=2 reports that trajectory instead of chasing it.
os.makedirs(os.path.join(w, "r"))
io.open(os.path.join(w, "c.json"), "w").write(json.dumps({
    "defaults": {}, "repos": [{"name": "r", "path": "r", "type": "python"}],
    "integration": {"enabled": False}}))
eng("init", "--config", "c.json", "--out", "L.json")
eng("bootstrap-oracle", "--impl", os.path.join(BF, "c-haiku", "source", "guard.py"),
    "--oracle", ORACLE, "--ledger", "L.json", "--repo", "r")
L = json.load(io.open(os.path.join(w, "L.json"), encoding="utf-8"))
recs = L.get("bootstrap_oracle", [])
rc_r2, rep_r2 = oracle(os.path.join(BF, "c-sonnet-r2", "source", "guard.py"))
res["AC-BS-06"] = (len(recs) == 1 and recs[0].get("oracle_green") is False
                   and len(recs[0].get("failing", [])) > 0
                   and rc_r2 == 0 and rep_r2.get("oracle_green") is True)

side = os.path.join(kit, "reports", "junit")
os.makedirs(side, exist_ok=True)
io.open(os.path.join(side, ".bootstrap-cases.json"), "w", encoding="utf-8").write(json.dumps(res))
bad = [k for k, v in res.items() if not v]
print("OK %d cases" % len(res) if not bad else "BAD " + ",".join(sorted(bad)))
PY
)
case "$T127" in
  OK*) PASS=$((PASS+1)); echo "  ok   bootstrap: $T127";;
  *)   FAIL=$((FAIL+1)); echo "  FAIL $T127";;
esac

echo "== T128 (1.75.0): the Diamond Bench -- regeneration fidelity across archetypes; PASS/PARTIAL/FAIL/PENDING (M5, ADR-018) =="
T128=$("$PY" - "$KIT" <<'PY'
import hashlib, importlib.util, io, json, os, shutil, subprocess, sys, tempfile
kit = sys.argv[1]
ENG = os.path.join(kit, ".claude", "skills", "uscha-devloop", "qa_ledger.py")
BENCH = os.path.join(kit, "tests", "fixtures", "diamond-bench")
res = {}
spec = importlib.util.spec_from_file_location("qa_ledger_t128", ENG)
q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q)

def bench(dirpath):
    r = subprocess.run([sys.executable, ENG, "bench", "--dir", dirpath, "--json"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        return json.loads(r.stdout)
    except ValueError:
        return {}

# AC-DB-01: bench over the committed dir emits a table; a PASS entry's numbers are a real run;
# DIAMOND-BENCH.md is written
d = bench(BENCH)
byarch = {r["archetype"]: r for r in d.get("raw", [])}
oracle = os.path.join(BENCH, "parser", "oracle", "ORACLE.json")
impl = os.path.join(BENCH, "parser", "c-opus", "source", "impl.py")
rr = subprocess.run([sys.executable, ENG, "bootstrap-oracle", "--impl", impl, "--oracle", oracle,
                     "--json"], capture_output=True, text=True, encoding="utf-8", errors="replace")
direct = json.loads(rr.stdout)["passed"]
outp = os.path.join(tempfile.mkdtemp(), "DIAMOND-BENCH.md")
subprocess.run([sys.executable, ENG, "bench", "--dir", BENCH, "--out", outp],
               capture_output=True, text=True, encoding="utf-8", errors="replace")
res["AC-DB-01"] = (d.get("entries") == 10 and byarch.get("parser", {}).get("verdict") == "PASS"
                   and byarch.get("crud-store", {}).get("verdict") == "PASS"
                   and all(r["verdict"] != "PENDING" for r in d.get("raw", []))
                   and any(c["oracle"]["passed"] == direct
                           for c in byarch["parser"]["compilations"] if c["model"] == "opus")
                   and os.path.isfile(outp) and os.path.getsize(outp) > 0)

disc_ok = all((r.get("discrimination") or {}).get("stub_green") is False
              for r in d.get("raw", []) if r.get("discrimination"))

w = tempfile.mkdtemp()
EXIT0 = "import sys\nsys.exit(0)\n"

def mk_ir(entry):
    cdir = os.path.join(entry, "canonical")
    os.makedirs(cdir)
    io.open(os.path.join(cdir, "ACCEPTANCE.md"), "w").write("- [ ] AC-X-01 do the thing\n")
    io.open(os.path.join(cdir, "CONSTITUTION.md"), "w").write("- **INV-X-01 — an invariant.** b\n")
    g = q._extract_ir(cdir, {})
    io.open(os.path.join(entry, "IR.json"), "w", encoding="utf-8").write(json.dumps(g))
    return g

def mk_oracle(entry):
    odir = os.path.join(entry, "oracle")
    os.makedirs(odir)
    io.open(os.path.join(odir, "ORACLE.json"), "w").write(
        json.dumps({"cases": [{"name": "c", "raw_stdin": "x", "expected_exit": 0}]}))

def mk_stub(entry, code):
    sdir = os.path.join(entry, "stub")
    os.makedirs(sdir)
    io.open(os.path.join(sdir, "stub.py"), "w", newline="\n").write(code)

def mk_comp(entry, model, body, ir):
    sdir = os.path.join(entry, "c-" + model, "source")
    os.makedirs(sdir)
    p = os.path.join(sdir, "impl.py")
    io.open(p, "w", newline="\n").write(body)
    sha = hashlib.sha256(io.open(p, "rb").read()).hexdigest()
    ids = [n["id"] for n in ir["nodes"]]
    c = {"schema_version": q.COMPILE_SCHEMA,
         "canonical_ir": {"ir_hash": ir["_integrity"], "schema_version": q.IR_SCHEMA},
         "target_stack": "python", "implementation_constraints": ["x"],
         "source": [{"unit": "source/impl.py", "sha256": sha}], "tests": [],
         "trace_manifest": [{"unit": "source/impl.py", "implements": ids}],
         "unresolved_intent": [{"ir_region": "AC-X-01", "decision": "d", "rationale": "r"}],
         "compilation_report": {"stack": "python", "model": model, "model_version": model,
                                "timestamps": {}, "constraint_handling": "x"}}
    c["_integrity"] = q._compile_seal(c)
    io.open(os.path.join(entry, "c-" + model, "COMPILATION.json"), "w",
            encoding="utf-8").write(json.dumps(c))

nd = os.path.join(w, "nondiscrim")
os.makedirs(nd)
ir_nd = mk_ir(nd)
mk_oracle(nd)
mk_stub(nd, EXIT0)
for i, m in enumerate(("opus", "sonnet", "haiku")):
    mk_comp(nd, m, "# v%d\n" % i + EXIT0, ir_nd)

cv = os.path.join(w, "converged")
os.makedirs(cv)
ir_cv = mk_ir(cv)
mk_oracle(cv)
mk_stub(cv, "import sys\nsys.exit(1)\n")
mk_comp(cv, "opus", EXIT0, ir_cv)
mk_comp(cv, "sonnet", EXIT0, ir_cv)
mk_comp(cv, "haiku", "# different\n" + EXIT0, ir_cv)

p3 = os.path.join(w, "pass3")
os.makedirs(p3)
ir_p3 = mk_ir(p3)
mk_oracle(p3)
mk_stub(p3, "import sys\nsys.exit(1)\n")
for i, m in enumerate(("opus", "sonnet", "haiku")):
    mk_comp(p3, m, "# d%d\n" % i + EXIT0, ir_p3)

pd = os.path.join(w, "pending")
os.makedirs(pd)
mk_ir(pd)
mk_oracle(pd)

td = bench(w)
tv = {r["archetype"]: r["verdict"] for r in td.get("raw", [])}
# AC-DB-02: discrimination -- committed stubs never green; an oracle a stub satisfies is FAIL
res["AC-DB-02"] = (disc_ok and tv.get("nondiscrim") == "FAIL")
# AC-DB-03: PASS logic -- 3 green + distinct is PASS; a byte-identical pair is FAIL, not PASS
res["AC-DB-03"] = (byarch.get("parser", {}).get("verdict") == "PASS"
                   and tv.get("pass3") == "PASS" and tv.get("converged") == "FAIL")
# AC-DB-05: an entry with no compilations is PENDING, counted, not dropped
res["AC-DB-05"] = (tv.get("pending") == "PENDING")
# AC-DB-04: model identities anonymized in the headline; raw mapping present
res["AC-DB-04"] = (d.get("model_map") == {"haiku": "M1", "opus": "M2", "sonnet": "M3"}
                   and all(any(mm in t["compilers"] for mm in ("M1", "M2", "M3"))
                           for t in d["table"] if t["verdict"] in ("PASS", "PARTIAL")))

def refs(p):
    try:
        with open(p, encoding="utf-8", errors="replace") as fh:
            t = fh.read().lower()
        return "oracle" in t or "expected_exit" in t or "expected_stdout" in t
    except OSError:
        return True

srcs = [os.path.join(BENCH, a, "c-" + m, "source", "impl.py")
        for a in ("parser", "state-machine", "transformer")
        for m in ("opus", "sonnet", "haiku")]
# AC-DB-06: the maker!=checker wall holds across every bench entry
res["AC-DB-06"] = all(os.path.isfile(s) and not refs(s) for s in srcs)

# Bench-growth criteria (ADR-020): measured over the five new entries in the same run.
NEW5 = ("rest-handler", "crud-store", "worker", "ui-render", "protocol-adapter")
def entry_complete(e):
    p = os.path.join(BENCH, e)
    return all(os.path.isfile(os.path.join(p, *rel)) for rel in (
        ("canonical", "SPEC.md"), ("canonical", "ACCEPTANCE.md"),
        ("canonical", "CONSTITUTION.md"), ("IR.json",), ("oracle", "ORACLE.json"),
        ("stub", "stub.py")))
res["AC-BG-01"] = (d.get("entries") == 10 and all(entry_complete(e) for e in NEW5)
                   and all(r["verdict"] != "PENDING" for r in d.get("raw", [])))
res["AC-BG-02"] = all((byarch.get(e, {}).get("discrimination") or {}).get("stub_green") is False
                      for e in NEW5)
def refs_orc(p):
    try:
        with open(p, encoding="utf-8", errors="replace") as fh:
            t = fh.read().lower()
        return "oracle" in t or "expected_exit" in t or "expected_stdout" in t
    except OSError:
        return True
res["AC-BG-03"] = all(all(c["compile_valid"] for c in byarch.get(e, {}).get("compilations", []))
                      and len(byarch.get(e, {}).get("compilations", [])) == 3
                      and all(not refs_orc(os.path.join(BENCH, e, "c-" + m, "source", "impl.py"))
                              for m in ("opus", "sonnet", "haiku"))
                      for e in NEW5)
wk_spec = io.open(os.path.join(BENCH, "worker", "canonical", "SPEC.md"),
                  encoding="utf-8").read()
res["AC-BG-04"] = ("Stated boundary" in wk_spec and "not exercise real parallelism" in wk_spec
                   or ("Stated boundary" in wk_spec and "real parallelism" in wk_spec))
# AC-BG-05: the discrimination evidence is COMMITTED and reproducible -- every plausible-wrong
# implementation under each new entry's wrong/ must score below oracle-green (the ADR-020
# review finding: a prose note is not evidence; a red run of a committed fixture is)
def wrongs_red(e):
    wd = os.path.join(BENCH, e, "wrong")
    ws = sorted(f for f in os.listdir(wd) if f.endswith(".py")) if os.path.isdir(wd) else []
    if not ws:
        return False
    try:
        with io.open(os.path.join(BENCH, e, "oracle", "ORACLE.json"),
                     encoding="utf-8-sig") as fh:
            wcases = (json.load(fh) or {}).get("cases") or []
    except (OSError, ValueError):
        return False
    for wf in ws:
        r = subprocess.run([sys.executable, ENG, "bootstrap-oracle", "--impl",
                            os.path.join(wd, wf), "--oracle",
                            os.path.join(BENCH, e, "oracle", "ORACLE.json"), "--json"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        try:
            if json.loads(r.stdout).get("oracle_green") is not False:
                return False
        except ValueError:
            return False
    return True
res["AC-BG-05"] = d.get("entries") == 10 and all(wrongs_red(e) for e in NEW5)

# Fidelity-per-compiler criteria (ADR-022): advisory descriptor, opt-in, UNMEASURED named.
def bench_fid():
    r = subprocess.run([sys.executable, ENG, "bench", "--dir", BENCH, "--fidelity", "--json"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        return json.loads(r.stdout)
    except ValueError:
        return {}
df1 = bench_fid()
# determinism re-run over the guard entry ONLY (a full second 27-compilation bench pass is
# minutes of subprocess launches on Windows; one entry proves determinism at 1/9 the cost)
gdir = os.path.join(w, "fidsub")
os.makedirs(gdir)
shutil.copytree(os.path.join(BENCH, "guard"), os.path.join(gdir, "guard"))
rf2 = subprocess.run([sys.executable, ENG, "bench", "--dir", gdir, "--fidelity", "--json"],
                     capture_output=True, text=True, encoding="utf-8", errors="replace")
try:
    df2 = json.loads(rf2.stdout)
except ValueError:
    df2 = {}
allc1 = [c for r in df1.get("raw", []) for c in r["compilations"]]
allc0 = [c for r in d.get("raw", []) for c in r["compilations"]]
res["AC-FC-01"] = (bool(allc1) and all("fidelity" in c for c in allc1)
                   and all("fidelity" not in c for c in allc0))
def fid_ok(rec):
    ir_g = json.load(io.open(os.path.join(BENCH, rec["archetype"], "IR.json"),
                             encoding="utf-8"))
    node_ids_g = set(nd["id"] for nd in ir_g["nodes"])
    for c in rec["compilations"]:
        fd = c["fidelity"]
        want = (round(c["oracle"]["passed"] / c["oracle"]["total"], 3)
                if c["oracle"]["total"] else None)
        if fd["oracle_passrate"] != want:
            return False
        cj_g = json.load(io.open(os.path.join(BENCH, rec["archetype"], c["dir"],
                                              "COMPILATION.json"), encoding="utf-8-sig"))
        cov = set(nid for e3 in cj_g.get("trace_manifest") or []
                  for nid in (e3.get("implements") or []) if nid in node_ids_g)
        if fd["trace_coverage"] != round(len(cov) / max(len(node_ids_g), 1), 3):
            return False
    return True
g1 = [r for r in df1.get("raw", []) if r["archetype"] == "guard"][0]
g2 = [r for r in df2.get("raw", []) if r["archetype"] == "guard"][0]
res["AC-FC-02"] = (fid_ok(g1) and all(
    a["fidelity"]["static_surface"] == b["fidelity"]["static_surface"]
    for a, b in zip(g1["compilations"], g2["compilations"])))
v_flag = dict((r["archetype"], r["verdict"]) for r in df1.get("raw", []))
v_none = dict((r["archetype"], r["verdict"]) for r in d.get("raw", []))
# closure is the literal UNMEASURED where no human verdict exists, and exactly
# judged/total where one does (ADR-023) -- never any other shape, never a fabricated 0.0
def closure_ok(c):
    cl = c["fidelity"]["curation_closure"]
    if cl == "UNMEASURED":
        return "curation" not in c["fidelity"]
    cu = c["fidelity"].get("curation") or {}
    return (isinstance(cl, float) and cu.get("judged", 0) >= 1
            and cl == round(float(cu["judged"]) / max(cu.get("total", 1), 1), 3))
res["AC-FC-03"] = (all(closure_ok(c) for c in allc1) and v_flag == v_none)

side = os.path.join(kit, "reports", "junit")
os.makedirs(side, exist_ok=True)
io.open(os.path.join(side, ".bench-cases.json"), "w", encoding="utf-8").write(json.dumps(res))
bad = [k for k, v in res.items() if not v]
print("OK %d cases" % len(res) if not bad else "BAD " + ",".join(sorted(bad)))
PY
)
case "$T128" in
  OK*) PASS=$((PASS+1)); echo "  ok   bench: $T128";;
  *)   FAIL=$((FAIL+1)); echo "  FAIL $T128";;
esac

echo "== T129 (1.76.0): the controlled-language arm -- free prose vs EARS+STE, same withheld oracle (ADR-019) =="
T129=$("$PY" - "$KIT" <<'PY'
import hashlib, importlib.util, io, json, os, subprocess, sys, tempfile
kit = sys.argv[1]
ENG = os.path.join(kit, ".claude", "skills", "uscha-devloop", "qa_ledger.py")
CL = os.path.join(kit, "tests", "fixtures", "controlled-language")
FREE = os.path.join(CL, "free")
CTRL = os.path.join(CL, "controlled")
res = {}
spec = importlib.util.spec_from_file_location("qa_ledger_t129", ENG)
q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q)

def lc(free, ctrl):
    r = subprocess.run([sys.executable, ENG, "lang-compare", "--free", free,
                        "--controlled", ctrl, "--json"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    try:
        return r.returncode, json.loads(r.stdout)
    except ValueError:
        return r.returncode, {}

# AC-CL-01: lang-compare over the two committed arms emits report + per-arm + delta + verdict
outp = os.path.join(tempfile.mkdtemp(), "CL.md")
r = subprocess.run([sys.executable, ENG, "lang-compare", "--free", FREE, "--controlled", CTRL,
                    "--out", outp, "--json"], capture_output=True, text=True, encoding="utf-8",
                   errors="replace")
try:
    rep = json.loads(r.stdout)
except ValueError:
    rep = {}
res["AC-CL-01"] = (r.returncode == 0 and "free" in rep and "controlled" in rep
                   and "delta" in rep and rep.get("verdict") in ("REDUCED", "MIXED", "NO EFFECT", "WORSE")
                   and os.path.isfile(outp) and os.path.getsize(outp) > 0)

# AC-CL-02: two arms with DIFFERENT oracles are refused (exit 2); committed arms share the oracle
w = tempfile.mkdtemp()
a1 = os.path.join(w, "a1")
a2 = os.path.join(w, "a2")
for a, txt in ((a1, json.dumps({"cases": [{"name": "x", "raw_stdin": "a", "expected_exit": 0}]})),
               (a2, json.dumps({"cases": [{"name": "x", "raw_stdin": "b", "expected_exit": 2}]}))):
    os.makedirs(os.path.join(a, "oracle"))
    io.open(os.path.join(a, "oracle", "ORACLE.json"), "w").write(txt)
rc_mm = subprocess.run([sys.executable, ENG, "lang-compare", "--free", a1, "--controlled", a2],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
shared = (q._oracle_hash(FREE) == q._oracle_hash(CTRL))
res["AC-CL-02"] = (rc_mm.returncode == 2 and "DIFFERENT oracles" in rc_mm.stderr and shared)

# AC-CL-03: both arms' 3 compilations compile-validate against their pinned IR; no leakage
def cv(arm, m):
    r = subprocess.run([sys.executable, ENG, "compile-validate", "--ir",
                        os.path.join(arm, "IR.json"), "--compilation",
                        os.path.join(arm, "c-" + m, "COMPILATION.json"), "--json"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        return json.loads(r.stdout).get("valid")
    except ValueError:
        return False

def refs(p):
    try:
        with open(p, encoding="utf-8", errors="replace") as fh:
            t = fh.read().lower()
        return "oracle" in t or "expected_exit" in t
    except OSError:
        return True

allvalid = all(cv(arm, m) is True for arm in (FREE, CTRL) for m in ("opus", "sonnet", "haiku"))
noleak = all(not refs(os.path.join(arm, "c-" + m, "source", "guard.py"))
             for arm in (FREE, CTRL) for m in ("opus", "sonnet", "haiku"))
res["AC-CL-03"] = allvalid and noleak

# AC-CL-04: the verdict is behaviour-first. A zero delta is NO EFFECT (a null, first-class); and
# reduced variance WITH a behavioural regression (a lost all-green) is MIXED, never REDUCED -- the
# regression cannot be masked as a win (the M4 convergence-toward-worse lesson).
def mk_arm(entry, bodies, cases):
    cdir = os.path.join(entry, "canonical")
    os.makedirs(cdir)
    io.open(os.path.join(cdir, "ACCEPTANCE.md"), "w").write("- [ ] AC-X-01 do the thing\n")
    io.open(os.path.join(cdir, "CONSTITUTION.md"), "w").write("- **INV-X-01 — an inv.** b\n")
    g = q._extract_ir(cdir, {})
    io.open(os.path.join(entry, "IR.json"), "w", encoding="utf-8").write(json.dumps(g))
    os.makedirs(os.path.join(entry, "oracle"))
    io.open(os.path.join(entry, "oracle", "ORACLE.json"), "w").write(json.dumps({"cases": cases}))
    ids = [n["id"] for n in g["nodes"]]
    for m, body in bodies.items():
        sdir = os.path.join(entry, "c-" + m, "source")
        os.makedirs(sdir)
        p = os.path.join(sdir, "impl.py")
        io.open(p, "w", newline="\n").write(body)
        sha = hashlib.sha256(io.open(p, "rb").read()).hexdigest()
        c = {"schema_version": q.COMPILE_SCHEMA,
             "canonical_ir": {"ir_hash": g["_integrity"], "schema_version": q.IR_SCHEMA},
             "target_stack": "python", "implementation_constraints": ["x"],
             "source": [{"unit": "source/impl.py", "sha256": sha}], "tests": [],
             "trace_manifest": [{"unit": "source/impl.py", "implements": ids}],
             "unresolved_intent": [{"ir_region": "AC-X-01", "decision": "d", "rationale": "r"}],
             "compilation_report": {"stack": "python", "model": m, "model_version": m,
                                    "timestamps": {}, "constraint_handling": "x"}}
        c["_integrity"] = q._compile_seal(c)
        io.open(os.path.join(entry, "c-" + m, "COMPILATION.json"), "w",
                encoding="utf-8").write(json.dumps(c))

EXIT0 = "import sys\nsys.exit(0)\n"
ONE = [{"name": "c", "raw_stdin": "x", "expected_exit": 0}]
TWO = [{"name": "a", "raw_stdin": "x", "expected_exit": 0},
       {"name": "b", "raw_stdin": "y", "expected_exit": 0}]
bodies = {"opus": "# a\n" + EXIT0, "sonnet": "# bb\n" + EXIT0, "haiku": "# ccc\n" + EXIT0}
ne_free = os.path.join(w, "nef")
os.makedirs(ne_free)
ne_ctrl = os.path.join(w, "nec")
os.makedirs(ne_ctrl)
mk_arm(ne_free, bodies, ONE)
mk_arm(ne_ctrl, bodies, ONE)
rc_ne, rep_ne = lc(ne_free, ne_ctrl)
# MIXED: free = 3 varied impls, all oracle-green (high variance); controlled = 3 near-identical
# impls that pass only case a (lost the all-green, low variance) -> MIXED, not REDUCED
BAD = "import sys\nsys.exit(0 if 'x' in sys.stdin.read() else 2)\n"
mx_free = os.path.join(w, "mxf")
os.makedirs(mx_free)
mx_ctrl = os.path.join(w, "mxc")
os.makedirs(mx_ctrl)
mk_arm(mx_free, {"opus": "# aaaa\nimport json\n" + EXIT0, "sonnet": "# b\n" + EXIT0,
                 "haiku": "# ccccccc\nimport re\n" + EXIT0}, TWO)
mk_arm(mx_ctrl, {"opus": "# a\n" + BAD, "sonnet": "# a\n" + BAD + " \n",
                 "haiku": "# a\n" + BAD + "  \n"}, TWO)
rc_mx, rep_mx = lc(mx_free, mx_ctrl)
res["AC-CL-04"] = (rc_ne == 0 and rep_ne.get("verdict") == "NO EFFECT"
                   and rep_ne["delta"]["variance_score"] == 0.0
                   and rc_mx == 0 and rep_mx.get("verdict") == "MIXED"
                   and rep_mx["delta"]["variance_score"] < 0
                   and rep_mx["delta"]["oracle_green"] < 0)

# AC-CL-05: the unresolved_intent proxy is deterministic and per-arm
rc_a, rep_a = lc(FREE, CTRL)
rc_b, rep_b = lc(FREE, CTRL)
def proxy(a):
    return (a["ui_count"], a["ui_distinct_regions"], a["ui_rationale_len"])
res["AC-CL-05"] = (all(k in rep_a["free"] for k in ("ui_count", "ui_distinct_regions",
                                                    "ui_rationale_len"))
                   and proxy(rep_a["free"]) == proxy(rep_b["free"])
                   and proxy(rep_a["controlled"]) == proxy(rep_b["controlled"]))

# AC-CL-06: the reference guard passes the shared oracle; controlled IR differs from free IR
# while the oracle is byte-identical
rg = subprocess.run([sys.executable, ENG, "bootstrap-oracle", "--impl",
                     os.path.join(kit, "hooks", "block-approved-writes.py"),
                     "--oracle", os.path.join(FREE, "oracle", "ORACLE.json"), "--json"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace")
try:
    ref_green = json.loads(rg.stdout).get("oracle_green")
except ValueError:
    ref_green = None
free_ir = json.load(io.open(os.path.join(FREE, "IR.json"), encoding="utf-8"))["_integrity"]
ctrl_ir = json.load(io.open(os.path.join(CTRL, "IR.json"), encoding="utf-8"))["_integrity"]
res["AC-CL-06"] = (ref_green is True and free_ir != ctrl_ir
                   and q._oracle_hash(FREE) == q._oracle_hash(CTRL))

# Controlled-language v0.2 criteria (ADR-021): the control arm and the de-confounded re-run,
# measured live and pinned to the recorded verdicts.
PF = os.path.join(CL, "parser-free")
PC = os.path.join(CL, "parser-controlled")
GR2 = os.path.join(CL, "guard-free-r2")
def cv2(arm, m, unit):
    r = subprocess.run([sys.executable, ENG, "compile-validate", "--ir",
                        os.path.join(arm, "IR.json"), "--compilation",
                        os.path.join(arm, "c-" + m, "COMPILATION.json"), "--json"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        ok = json.loads(r.stdout).get("valid") is True
    except ValueError:
        return False
    return ok and not refs(os.path.join(arm, "c-" + m, unit.replace("/", os.sep)))
pf_ir = json.load(io.open(os.path.join(PF, "IR.json"), encoding="utf-8"))["_integrity"]
pc_ir = json.load(io.open(os.path.join(PC, "IR.json"), encoding="utf-8"))["_integrity"]
res["AC-CL2-01"] = (pf_ir != pc_ir and q._oracle_hash(PF) == q._oracle_hash(PC)
                    and all(cv2(PC, m, "source/impl.py") for m in ("opus", "sonnet", "haiku"))
                    and all(cv2(GR2, m, "source/guard.py") for m in ("opus", "sonnet", "haiku")))
rc_ctl, rep_ctl = lc(PF, PC)
res["AC-CL2-02"] = (rc_ctl == 0 and rep_ctl.get("verdict") == "NO EFFECT"
                    and rep_ctl["free"]["greens"] == 3 and rep_ctl["controlled"]["greens"] == 3)
rc_dc, rep_dc = lc(GR2, os.path.join(CL, "controlled"))
# The variance signal is version-stable (-0.263 on 3.8 and 3.13 alike) and is the pin. The
# VERDICT is runtime-dependent by a measured fact: controlled/c-haiku's guard declares
# "Python 3.8+" but uses a `tuple[bool, str]` annotation, which crashes at def-time on 3.8
# (0/23 there) -- a real portability defect OF THAT BLIND COMPILATION, caught by the matrix
# cell and recorded here; the artifact stays untouched (editing a blind compilation would
# fabricate the experiment). Expected verdict: REDUCED on >=3.9 (the experiment's stated
# runtime), MIXED on 3.8 where that one artifact is broken.
expected_dc = "REDUCED" if sys.version_info >= (3, 9) else "MIXED"
res["AC-CL2-03"] = (rc_dc == 0 and rep_dc.get("verdict") == expected_dc
                    and rep_dc["delta"]["variance_score"] < -0.05
                    and q._oracle_hash(GR2) == q._oracle_hash(os.path.join(CL, "controlled")))
res["AC-CL2-04"] = all(os.path.isfile(os.path.join(kit, "..", f)) for f in
                       ("CONTROLLED-LANGUAGE-REPORT.md", "CONTROLLED-LANGUAGE-CONTROL.md",
                        "CONTROLLED-LANGUAGE-DECONFOUNDED.md"))

side = os.path.join(kit, "reports", "junit")
os.makedirs(side, exist_ok=True)
io.open(os.path.join(side, ".lang-cases.json"), "w", encoding="utf-8").write(json.dumps(res))
bad = [k for k, v in res.items() if not v]
print("OK %d cases" % len(res) if not bad else "BAD " + ",".join(sorted(bad)))
PY
)
case "$T129" in
  OK*) PASS=$((PASS+1)); echo "  ok   lang: $T129";;
  *)   FAIL=$((FAIL+1)); echo "  FAIL $T129";;
esac

echo "== T130 (1.80.0): bench-curate -- ONE human verdict per observation, measured closure, fail-closed store (ADR-023) =="
T130=$("$PY" - "$KIT" <<'PY'
import io, json, os, re, shutil, subprocess, sys, tempfile
kit = sys.argv[1]
ENG = os.path.join(kit, ".claude", "skills", "uscha-devloop", "qa_ledger.py")
BENCH = os.path.join(kit, "tests", "fixtures", "diamond-bench")
res = {}
w = tempfile.mkdtemp(prefix="uscha-bc-")
try:
    shutil.copytree(os.path.join(BENCH, "guard"), os.path.join(w, "guard"))
    def run(*a):
        return subprocess.run([sys.executable, ENG] + list(a), capture_output=True,
                              text=True, encoding="utf-8", errors="replace")
    def bc(*a):
        return run("bench-curate", "--bench", w, "--entry", "guard", *a)
    lst = bc("--dir", "c-opus", "--list")
    obs_lines = [ln for ln in lst.stdout.splitlines() if ln.strip().startswith("OBS-")]
    ids = [ln.split()[0] for ln in obs_lines]
    if len(ids) < 2 or lst.returncode != 0:
        raise RuntimeError("no curable observations listed")
    # --dir and its --compilation alias must behave identically (1.82.0): bench --dir means
    # the bench root, bench-curate --dir means the compilation subdir -- a copy-paste hazard
    # the 1.80.0 review flagged; --compilation disambiguates without breaking --dir.
    lst_alias = bc("--compilation", "c-opus", "--list")
    res["AC-BC-04"] = (lst_alias.returncode == lst.returncode
                       and lst_alias.stdout == lst.stdout)
    r1 = bc("--dir", "c-opus", "--obs", ids[0], "--verdict", "preserve", "--human", "smoke")
    r2 = bc("--dir", "c-opus", "--obs", ids[1], "--verdict", "fix", "--human", "smoke")
    rb = bc("--dir", "c-opus", "--obs", "OBS-a,OBS-b", "--verdict", "preserve")
    ru = bc("--dir", "c-opus", "--obs", "OBS-000000000000", "--verdict", "preserve")
    store_p = os.path.join(w, "BENCH-CURATION.json")
    def nrec():
        with io.open(store_p, encoding="utf-8") as fh:
            return len(json.load(fh)["records"])
    n2 = nrec()
    rs = bc("--dir", "c-opus", "--obs", ids[1], "--verdict", "preserve", "--human", "smoke")
    n3 = nrec()
    good = io.open(store_p, encoding="utf-8").read()
    io.open(store_p, "w", encoding="utf-8").write(json.dumps({"records": "nope"}))
    rml = bc("--dir", "c-opus", "--list")
    rmb = run("bench", "--dir", w, "--fidelity", "--json")
    # a plain bench run never reads the store: a corrupt store must not block it (the
    # review caught the unconditional load exceeding what ADR-023 promises)
    rplain = run("bench", "--dir", w, "--json")
    # a directory occupying the store path is malformed, not absent: exit 2 everywhere,
    # never a silent UNMEASURED read or an unhandled traceback on write (review catch)
    os.remove(store_p)
    os.makedirs(store_p)
    rdl = bc("--dir", "c-opus", "--list")
    rdf = run("bench", "--dir", w, "--fidelity", "--json")
    rdw = bc("--dir", "c-opus", "--obs", ids[0], "--verdict", "preserve")
    os.rmdir(store_p)
    rws = bc("--dir", "c-opus", "--obs", " " + ids[0] + " ", "--verdict", "preserve")
    io.open(store_p, "w", encoding="utf-8").write(good)
    res["AC-BC-01"] = (r1.returncode == 0 and r2.returncode == 0
                       and rb.returncode == 2 and ru.returncode == 2
                       and n2 == 2 and rs.returncode == 0 and n3 == 3
                       and "supersedes" in rs.stdout
                       and rml.returncode == 2 and rmb.returncode == 2
                       and rplain.returncode == 0
                       and rdl.returncode == 2 and rdf.returncode == 2
                       and rdw.returncode == 2 and "Traceback" not in rdw.stderr
                       and rws.returncode == 2 and "whitespace" in rws.stderr)
    rf = run("bench", "--dir", w, "--fidelity", "--json")
    raw = json.loads(rf.stdout)["raw"]
    comps = dict((c["dir"], c) for r in raw for c in r["compilations"])
    op = comps["c-opus"].get("fidelity") or {}
    others_un = all((comps[x].get("fidelity") or {}).get("curation_closure") == "UNMEASURED"
                    and "curation" not in (comps[x].get("fidelity") or {})
                    for x in ("c-sonnet", "c-haiku"))
    cl, cu = op.get("curation_closure"), op.get("curation") or {}
    verd_store = dict((r["archetype"], r["verdict"]) for r in raw)
    os.remove(store_p)
    rf0 = run("bench", "--dir", w, "--fidelity", "--json")
    verd_none = dict((r["archetype"], r["verdict"]) for r in json.loads(rf0.stdout)["raw"])
    io.open(store_p, "w", encoding="utf-8").write(good)
    res["AC-BC-02"] = (isinstance(cl, float) and cu.get("judged") == 2
                       and cl == round(2.0 / max(cu.get("total", 1), 1), 3)
                       and others_un and verd_store == verd_none)
    m = re.search(r"defines function (\w+)", obs_lines[0])
    if not m:
        raise RuntimeError("first observation is not a function definition")
    fname = m.group(1)
    gp = os.path.join(w, "guard", "c-opus", "source", "guard.py")
    src = io.open(gp, encoding="utf-8").read()
    io.open(gp, "w", encoding="utf-8").write(
        src.replace("def " + fname + "(", "def " + fname + "_zz(", 1))
    r3 = bc("--dir", "c-opus", "--obs", ids[0], "--verdict", "preserve")
    lst2 = bc("--dir", "c-opus", "--list")
    res["AC-BC-03"] = (r3.returncode == 2 and lst2.returncode == 0
                       and "STALE" in lst2.stdout)
finally:
    shutil.rmtree(w, ignore_errors=True)
side = os.path.join(kit, "reports", "junit")
os.makedirs(side, exist_ok=True)
io.open(os.path.join(side, ".bench-curate-cases.json"), "w",
        encoding="utf-8").write(json.dumps(res))
bad = [k for k, v in res.items() if not v]
print("OK %d cases" % len(res) if not bad else "BAD " + ",".join(sorted(bad)))
PY
)
case "$T130" in
  OK*) PASS=$((PASS+1)); echo "  ok   bench-curate: $T130";;
  *)   FAIL=$((FAIL+1)); echo "  FAIL $T130";;
esac

echo "== T131 (1.81.0): controlled-language v0.3 -- replication across archetypes; the aggregate is 1 of 4 (ADR-024) =="
T131=$("$PY" - "$KIT" "$ROOT" <<'PY'
import io, json, os, subprocess, sys
kit, root = sys.argv[1], sys.argv[2]
ENG = os.path.join(kit, ".claude", "skills", "uscha-devloop", "qa_ledger.py")
CL = os.path.join(kit, "tests", "fixtures", "controlled-language")
res = {}
PAIRS = [("state-machine-free-r2", "state-machine-controlled"),
         ("transformer-free-r2", "transformer-controlled")]
def readb(p):
    with io.open(p, "rb") as fh:
        return fh.read()
def run(*a):
    return subprocess.run([sys.executable, ENG] + list(a), capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
# AC-CL3-01: oracle byte-identical across each pair; every compilation validates against its
# arm's IR and carries a NON-EMPTY unresolved_intent, distinct across the three models
ok1 = True
for free, ctrl in PAIRS:
    if readb(os.path.join(CL, free, "oracle", "ORACLE.json")) != readb(
            os.path.join(CL, ctrl, "oracle", "ORACLE.json")):
        ok1 = False
    for arm in (free, ctrl):
        fps = []
        for m in ("c-opus", "c-sonnet", "c-haiku"):
            cj = os.path.join(CL, arm, m, "COMPILATION.json")
            rv = run("compile-validate", "--ir", os.path.join(CL, arm, "IR.json"),
                     "--compilation", cj)
            if rv.returncode != 0:
                ok1 = False
            c = json.load(io.open(cj, encoding="utf-8-sig"))
            ui = c.get("unresolved_intent") or []
            if not (2 <= len(ui) <= 5):
                ok1 = False
            fps.append(json.dumps(ui, sort_keys=True))
        if len(set(fps)) != 3:
            ok1 = False                    # identical UI across models = synthesized, not returned
res["AC-CL3-01"] = ok1
# AC-CL3-02: computed verdicts pinned -- state-machine NO EFFECT (deltas inside the margins),
# transformer WORSE (an oracle-green lost); the divergence is the extra-field-tolerated case
# on the controlled opus compilation. Interpreter-stable (verified 3.8 + 3.13 before pinning).
def compare(free, ctrl):
    r = run("lang-compare", "--free", os.path.join(CL, free),
            "--controlled", os.path.join(CL, ctrl), "--json")
    try:
        return json.loads(r.stdout)
    except ValueError:
        return {}
sm = compare(*PAIRS[0])
tf = compare(*PAIRS[1])
sm_ok = (sm.get("verdict") == "NO EFFECT"
         and abs(sm.get("delta", {}).get("variance_score", 9)) <= sm.get("margin", 0)
         and sm.get("delta", {}).get("mean_passrate") == 0.0
         and sm.get("delta", {}).get("oracle_green") == 0)
tf_ok = (tf.get("verdict") == "WORSE"
         and tf.get("delta", {}).get("oracle_green") == -1
         and tf.get("delta", {}).get("mean_passrate", 0) < 0)
ro = run("bootstrap-oracle", "--impl",
         os.path.join(CL, "transformer-controlled", "c-opus", "source", "impl.py"),
         "--oracle", os.path.join(CL, "transformer-controlled", "oracle", "ORACLE.json"),
         "--json")
try:
    od = json.loads(ro.stdout)
except ValueError:
    od = {}
red = [r.get("name") for r in od.get("results") or [] if not r.get("ok")]
case_ok = (od.get("passed") == 13 and od.get("total") == 14
           and red == ["extra-field-tolerated"])
res["AC-CL3-02"] = sm_ok and tf_ok and case_ok
# AC-CL3-03: the v0.3 summary states the aggregate (now 5 deconfounded archetypes after
# ADR-025) with per-archetype rows; the negative row is present with the same prominence as
# the positive. The "1 of 4" phrasing was superseded when the scheduler's IMPROVED row landed
# (ADR-025/1.83.0) and the aggregate doc was rewritten -- this pin follows the live document.
v3 = os.path.join(root, "CONTROLLED-LANGUAGE-V03.md")
try:
    body = io.open(v3, encoding="utf-8").read()
except OSError:
    body = ""
res["AC-CL3-03"] = ("5 deconfounded archetypes" in body
                    and "| guard |" in body and "**REDUCED**" in body
                    and "| parser |" in body and "| state-machine |" in body
                    and "| transformer |" in body and "**WORSE**" in body
                    and body.count("**NO EFFECT**") >= 2)
side = os.path.join(kit, "reports", "junit")
os.makedirs(side, exist_ok=True)
io.open(os.path.join(side, ".lang3-cases.json"), "w",
        encoding="utf-8").write(json.dumps(res))
bad = [k for k, v in res.items() if not v]
print("OK %d cases" % len(res) if not bad else "BAD " + ",".join(sorted(bad)))
PY
)
case "$T131" in
  OK*) PASS=$((PASS+1)); echo "  ok   lang-v03: $T131";;
  *)   FAIL=$((FAIL+1)); echo "  FAIL $T131";;
esac

echo "== T132 (1.83.0): the slack hypothesis, tested -- scheduler enters the bench + controlled-language, IMPROVED is a named verdict (ADR-025, ADR-026) =="
T132=$("$PY" - "$KIT" "$ROOT" <<'PY'
import io, json, os, subprocess, sys
kit, root = sys.argv[1], sys.argv[2]
ENG = os.path.join(kit, ".claude", "skills", "uscha-devloop", "qa_ledger.py")
BENCH = os.path.join(kit, "tests", "fixtures", "diamond-bench")
CL = os.path.join(kit, "tests", "fixtures", "controlled-language")
SCHED = os.path.join(BENCH, "scheduler")
res = {}
def readb(p):
    with io.open(p, "rb") as fh:
        return fh.read()
def run(*a):
    return subprocess.run([sys.executable, ENG] + list(a), capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
def oracle(impl):
    r = run("bootstrap-oracle", "--impl", impl, "--oracle",
            os.path.join(SCHED, "oracle", "ORACLE.json"), "--json")
    try:
        return json.loads(r.stdout)
    except ValueError:
        return {}
def bench(dirpath):
    r = run("bench", "--dir", dirpath, "--json")
    try:
        return json.loads(r.stdout)
    except ValueError:
        return {}

# AC-SH-01: the scheduler oracle discriminates -- the degenerate stub is red, EVERY wrong/
# implementation is red (each breaks exactly one rule), and the bench's own discrimination
# gate over the entry agrees. No reference impl is committed here (the "reference passes 100%"
# half of the discrimination gate is evidenced by c-opus 30/30 under AC-SH-02).
stub_ok = oracle(os.path.join(SCHED, "stub", "stub.py")).get("oracle_green") is False
wd = os.path.join(SCHED, "wrong")
wrongs = sorted(f for f in os.listdir(wd) if f.endswith(".py"))
wrong_ok = bool(wrongs) and all(oracle(os.path.join(wd, f)).get("oracle_green") is False
                                for f in wrongs)
d0 = bench(BENCH)
sched_raw = [r for r in d0.get("raw", []) if r["archetype"] == "scheduler"]
disc_ok = (bool(sched_raw)
           and (sched_raw[0].get("discrimination") or {}).get("stub_green") is False)
res["AC-SH-01"] = stub_ok and wrong_ok and disc_ok and len(wrongs) == 9

# AC-SH-02: the three blind compilations validate against the pinned IR; unresolved_intent is
# non-empty, bounded, and model-distinct (verbatim, not synthesized); the bench verdict for
# scheduler is PARTIAL with the pinned per-compiler oracle counts; entries == 10 (the ninth
# archetype landed).
cv_ok = True
ui_fps = []
for m in ("opus", "sonnet", "haiku"):
    rv = run("compile-validate", "--ir", os.path.join(SCHED, "IR.json"), "--compilation",
             os.path.join(SCHED, "c-" + m, "COMPILATION.json"))
    if rv.returncode != 0:
        cv_ok = False
    c = json.load(io.open(os.path.join(SCHED, "c-" + m, "COMPILATION.json"),
                          encoding="utf-8-sig"))
    ui = c.get("unresolved_intent") or []
    if not (2 <= len(ui) <= 5):
        cv_ok = False
    ui_fps.append(json.dumps(ui, sort_keys=True))
distinct_ok = len(set(ui_fps)) == 3
sched_entry = sched_raw[0] if sched_raw else {}
per_comp = dict((c["model"], c["oracle"]["passed"]) for c in sched_entry.get("compilations", []))
counts_ok = (per_comp == {"opus": 30, "sonnet": 26, "haiku": 25}
            and all(c["oracle"]["total"] == 30 for c in sched_entry.get("compilations", [])))
res["AC-SH-02"] = (cv_ok and distinct_ok and sched_entry.get("verdict") == "PARTIAL"
                   and counts_ok and d0.get("entries") == 10)

# AC-SH-03: lang-compare over scheduler-free vs scheduler-controlled (shared byte-identical
# oracle, also byte-identical to the bench entry's own oracle -- one dispatch feeds both
# instruments) yields the pinned IMPROVED verdict; the aggregate doc states 5 archetypes with
# the full row set.
FREE = os.path.join(CL, "scheduler-free")
CTRL = os.path.join(CL, "scheduler-controlled")
rc_sh = run("lang-compare", "--free", FREE, "--controlled", CTRL, "--json")
try:
    rep_sh = json.loads(rc_sh.stdout)
except ValueError:
    rep_sh = {}
oracle_shared = (readb(os.path.join(FREE, "oracle", "ORACLE.json"))
                 == readb(os.path.join(CTRL, "oracle", "ORACLE.json"))
                 == readb(os.path.join(SCHED, "oracle", "ORACLE.json")))
v03 = os.path.join(root, "CONTROLLED-LANGUAGE-V03.md")
try:
    v03_body = io.open(v03, encoding="utf-8").read()
except OSError:
    v03_body = ""
res["AC-SH-03"] = (rc_sh.returncode == 0 and rep_sh.get("verdict") == "IMPROVED"
                   and rep_sh.get("improved") is True and rep_sh.get("regressed") is False
                   and rep_sh.get("delta", {}).get("oracle_green") == 1
                   and rep_sh.get("delta", {}).get("mean_passrate", 0) > 0.02
                   and rep_sh.get("delta", {}).get("variance_score", 0) > 0.05
                   and oracle_shared
                   and "5 deconfounded archetypes" in v03_body
                   and "| scheduler |" in v03_body and "**IMPROVED**" in v03_body
                   and "| transformer |" in v03_body and "**WORSE**" in v03_body
                   and "**REDUCED**" in v03_body)

# AC-LI-01 / AC-LI-02: the IMPROVED/MIXED symmetric rule (ADR-026), exercised via every
# committed pair that reaches a distinct branch -- no synthetic arms needed, the five
# same-generation pairs already on disk cover REDUCED, NO EFFECT (x2), WORSE and IMPROVED.
# Every JSON report now carries the "improved"/"regressed" booleans.
# The guard pair reads MIXED on Python 3.8 (controlled/c-haiku crashes at def-time on a 3.9+
# annotation -> 0/23 -> behaviour regressed), REDUCED on 3.9+ -- the same interpreter-pinned
# expectation AC-CL2-03 (T129) already carries; the artifact is never edited (1.78.0 rule).
GUARD_WANT = "REDUCED" if sys.version_info >= (3, 9) else "MIXED"
PAIRS5 = [("guard-free-r2", "controlled", GUARD_WANT),
          ("parser-free", "parser-controlled", "NO EFFECT"),
          ("state-machine-free-r2", "state-machine-controlled", "NO EFFECT"),
          ("transformer-free-r2", "transformer-controlled", "WORSE"),
          ("scheduler-free", "scheduler-controlled", "IMPROVED")]
rule_ok = True
bools_ok = True
verdicts = {}
for free, ctrl, want in PAIRS5:
    r = run("lang-compare", "--free", os.path.join(CL, free), "--controlled",
            os.path.join(CL, ctrl), "--json")
    try:
        rp = json.loads(r.stdout)
    except ValueError:
        rp = {}
    verdicts[free] = rp.get("verdict")
    if rp.get("verdict") != want:
        rule_ok = False
    if not (isinstance(rp.get("improved"), bool) and isinstance(rp.get("regressed"), bool)):
        bools_ok = False
res["AC-LI-01"] = rule_ok and bools_ok
res["AC-LI-02"] = (verdicts.get("guard-free-r2") == GUARD_WANT
                   and verdicts.get("parser-free") == "NO EFFECT"
                   and verdicts.get("state-machine-free-r2") == "NO EFFECT"
                   and verdicts.get("transformer-free-r2") == "WORSE")

# AC-LI-03: the rendered scheduler report states the IMPROVED verdict in prose and names the
# convergence-on-a-shared-error failure mode. Regenerated fresh via --out and compared against
# the committed CONTROLLED-LANGUAGE-SCHED.md.
import tempfile
outp = os.path.join(tempfile.mkdtemp(), "SCHED.md")
run("lang-compare", "--free", FREE, "--controlled", CTRL, "--out", outp)
fresh = io.open(outp, encoding="utf-8").read() if os.path.isfile(outp) else ""
committed = os.path.join(root, "CONTROLLED-LANGUAGE-SCHED.md")
try:
    committed_body = io.open(committed, encoding="utf-8").read()
except OSError:
    committed_body = ""
res["AC-LI-03"] = ("## Verdict: IMPROVED" in fresh and "convergence on a shared reading" in fresh
                   and "## Verdict: IMPROVED" in committed_body
                   and "convergence on a shared reading" in committed_body)

side = os.path.join(kit, "reports", "junit")
os.makedirs(side, exist_ok=True)
io.open(os.path.join(side, ".sched-cases.json"), "w",
        encoding="utf-8").write(json.dumps(res))
bad = [k for k, v in res.items() if not v]
print("OK %d cases" % len(res) if not bad else "BAD " + ",".join(sorted(bad)))
PY
)
case "$T132" in
  OK*) PASS=$((PASS+1)); echo "  ok   slack-hypothesis: $T132";;
  *)   FAIL=$((FAIL+1)); echo "  FAIL $T132";;
esac

echo "== T133 (1.84.0): the noise floor -- intra-model variance under the bench, bench-r2 (ADR-027) =="
T133=$("$PY" - "$KIT" "$ROOT" <<'PY'
import importlib.util, io, json, os, shutil, subprocess, sys, tempfile
kit, root = sys.argv[1], sys.argv[2]
ENG = os.path.join(kit, ".claude", "skills", "uscha-devloop", "qa_ledger.py")
BENCH = os.path.join(kit, "tests", "fixtures", "diamond-bench")
res = {}
spec = importlib.util.spec_from_file_location("qa_ledger_t133", ENG)
q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q)

def run(*a):
    return subprocess.run([sys.executable, ENG] + list(a), capture_output=True,
                          text=True, encoding="utf-8", errors="replace")

def bench_json(dirpath):
    r = run("bench", "--dir", dirpath, "--json")
    try:
        return json.loads(r.stdout)
    except ValueError:
        return {}

def bench_r2_json(dirpath):
    r = run("bench-r2", "--dir", dirpath, "--json")
    try:
        return json.loads(r.stdout)
    except ValueError:
        return {}

# AC-R2-01: bench --json is byte-identical with r2/ present vs r2/ hidden -- bench ignores the
# second-run dirs entirely. The real bench still reports 10 entries, PARTIAL exactly
# {guard, rest-handler, scheduler}.
# byte-identity is proven over a ONE-entry copy (protocol-adapter: 3 run-1 + 3 r2
# compilations) -- a full 10-entry double bench pass is minutes of subprocess launches on
# Windows and proves nothing more; the real bench is run once below for the pins.
tcopy = os.path.join(tempfile.mkdtemp(), "bench")
os.makedirs(tcopy)
shutil.copytree(os.path.join(BENCH, "protocol-adapter"), os.path.join(tcopy, "protocol-adapter"))
with_r2 = run("bench", "--dir", tcopy, "--json")
shutil.rmtree(os.path.join(tcopy, "protocol-adapter", "r2"))
without_r2 = run("bench", "--dir", tcopy, "--json")
d0 = bench_json(BENCH)
partial = sorted(r["archetype"] for r in d0.get("raw", []) if r["verdict"] == "PARTIAL")
res["AC-R2-01"] = (with_r2.stdout == without_r2.stdout and with_r2.returncode == 0
                   and d0.get("entries") == 10
                   and partial == ["guard", "rest-handler", "scheduler"])

# AC-R2-02: bench-r2 --json shape and per-entry class-from-ratio recomputation; an entry with
# its r2/ removed reports has_r2 False, class None, a non-empty reason (absent, never 0).
r2d0 = bench_r2_json(BENCH)
raw = r2d0.get("raw", [])
def expect_class(ratio):
    if ratio is None:
        return None
    if ratio < 0.5:
        return "SIGNAL"
    if ratio < 1.0:
        return "NOISY"
    return "NOISE"
shape_ok = True
for r in raw:
    if not r.get("has_r2"):
        shape_ok = False
        continue
    if r.get("class") not in ("SIGNAL", "NOISY", "NOISE"):
        shape_ok = False
    if not isinstance(r.get("intra_mean"), float):
        shape_ok = False
    if not isinstance(r.get("inter"), float):
        shape_ok = False
    if not isinstance(r.get("intra_over_inter"), float):
        shape_ok = False
    if r.get("class") != expect_class(r.get("intra_over_inter")):
        shape_ok = False
    models = r.get("models") or []
    if len(models) != 3:
        shape_ok = False
    for m in models:
        if not isinstance(m.get("intra_distance"), float):
            shape_ok = False
        if not isinstance(m.get("behaviour_stable"), bool):
            shape_ok = False

# absence is proven over the SAME one-entry copy (its r2/ is already removed above): the
# instrument must report has_r2 False / class None / a reason -- absent, never 0.
absent_dir = tcopy
absd = bench_r2_json(absent_dir)
absrec = next((r for r in absd.get("raw", []) if r["archetype"] == "protocol-adapter"), {})
absent_ok = (absrec.get("has_r2") is False and absrec.get("class") is None
            and bool(absrec.get("reason")))
# the 1.84.0 review found the silent-gap case: r2/ PRESENT but no model pair measurable
# (unparseable r2 sources) left class None AND reason None -- a silent absence. Rebuild the
# r2/ dir on the copy with broken sources and demand a named reason.
os.makedirs(os.path.join(tcopy, "protocol-adapter", "r2"))
for m in ("c-opus", "c-sonnet", "c-haiku"):
    shutil.copytree(os.path.join(BENCH, "protocol-adapter", "r2", m),
                    os.path.join(tcopy, "protocol-adapter", "r2", m))
    bad_src = os.path.join(tcopy, "protocol-adapter", "r2", m, "source", "impl.py")
    io.open(bad_src, "w", encoding="utf-8").write("def (" + chr(10))
gapd = bench_r2_json(tcopy)
gaprec = next((r for r in gapd.get("raw", []) if r["archetype"] == "protocol-adapter"), {})
gap_ok = (gaprec.get("has_r2") is True and gaprec.get("class") is None
          and bool(gaprec.get("reason")))

pa_dir = os.path.join(BENCH, "protocol-adapter")
run1_metrics = []
for m in ("c-opus", "c-sonnet", "c-haiku"):
    cj = os.path.join(pa_dir, m, "COMPILATION.json")
    with io.open(cj, encoding="utf-8-sig") as fh:
        c = json.load(fh)
    unit = (c.get("source") or [{}])[0].get("unit")
    impl = os.path.join(pa_dir, m, unit.replace("/", os.sep))
    run1_metrics.append(q._impl_metrics(impl))
dists = []
for i in range(len(run1_metrics)):
    for j in range(i + 1, len(run1_metrics)):
        dists.append(q._struct_distance(run1_metrics[i], run1_metrics[j]))
inter_recomputed = round(sum(dists) / len(dists), 4)
pa_rec = next((r for r in raw if r["archetype"] == "protocol-adapter"), {})
commensurable_ok = round(pa_rec.get("inter", -1), 4) == round(inter_recomputed, 4)

res["AC-R2-02"] = shape_ok and absent_ok and gap_ok and commensurable_ok

# AC-R2-03: all 30 r2 COMPILATION.json compile-validate against their entry's IR; each
# unresolved_intent has 2..6 entries, the three per entry are pairwise distinct; the aggregate
# and every per-entry class are pinned exactly as measured for 1.84.0.
cv_ok = True
ui_bounds_ok = True
entries = sorted(d for d in os.listdir(BENCH) if os.path.isdir(os.path.join(BENCH, d, "r2")))
for e in entries:
    r2 = os.path.join(BENCH, e, "r2")
    ir = os.path.join(BENCH, e, "IR.json")
    fps = []
    for m in ("c-opus", "c-sonnet", "c-haiku"):
        cj = os.path.join(r2, m, "COMPILATION.json")
        rv = run("compile-validate", "--ir", ir, "--compilation", cj)
        if rv.returncode != 0:
            cv_ok = False
        with io.open(cj, encoding="utf-8-sig") as fh:
            c = json.load(fh)
        ui = c.get("unresolved_intent") or []
        if not (2 <= len(ui) <= 6):
            ui_bounds_ok = False
        fps.append(json.dumps(ui, sort_keys=True))
    if len(set(fps)) != 3:
        ui_bounds_ok = False
res["AC-R2-03-compile"] = cv_ok and ui_bounds_ok and len(entries) == 10

WANT_CLASS = {"crud-store": "NOISY", "guard": "NOISY", "parser": "NOISE",
             "protocol-adapter": "SIGNAL", "rest-handler": "NOISY", "scheduler": "NOISE",
             "state-machine": "NOISE", "transformer": "NOISY", "ui-render": "NOISY",
             "worker": "NOISE"}
classes_ok = all(next((r for r in raw if r["archetype"] == a), {}).get("class") == c
                 for a, c in WANT_CLASS.items())
agg = r2d0.get("aggregate", {})
agg_ok = (agg.get("verdict") == "NOISY" and agg.get("signal") == 1 and agg.get("noisy") == 5
         and agg.get("noise") == 4 and agg.get("stable") == 26 and agg.get("reruns") == 30
         and len(WANT_CLASS) == 10)
res["AC-R2-03"] = res["AC-R2-03-compile"] and classes_ok and agg_ok
del res["AC-R2-03-compile"]

side = os.path.join(kit, "reports", "junit")
os.makedirs(side, exist_ok=True)
io.open(os.path.join(side, ".r2-cases.json"), "w", encoding="utf-8").write(json.dumps(res))
bad = [k for k, v in res.items() if not v]
print("OK %d cases" % len(res) if not bad else "BAD " + ",".join(sorted(bad)))
PY
)
case "$T133" in
  OK*) PASS=$((PASS+1)); echo "  ok   noise-floor: $T133";;
  *)   FAIL=$((FAIL+1)); echo "  FAIL $T133";;
esac

echo "== T0 live: every published claim must match the derived facts (FACTUAL DRIFT = red) =="
# The REAL check over the REAL claim surfaces -- the founding fixture (site said 1.65.0/32
# while the repo was 1.67.0/35) went red on this exact command before being fixed.
# Historical changelogs are archives, deliberately out of scope (ADR-012).
chk "site+README+manifests+docs claims match SYSTEM-FACTS" 0 \
  "$PY" "$QL" facts --check \
    "$ROOT/README.md" "$ROOT/uscha-kit/README.md" \
    "$ROOT/site/index.html" "$ROOT/site/es/index.html" "$ROOT/site/llms.txt" \
    "$ROOT/.claude-plugin/marketplace.json" "$ROOT/uscha-kit/.claude-plugin/plugin.json" \
    "$ROOT/docs/uscha-claude-code-doc.html" "$ROOT/docs/uscha-claude-code-doc-EN.html" \
    "$ROOT/site/docs/uscha-claude-code-doc.html" "$ROOT/site/docs/uscha-claude-code-doc-EN.html" \
    --out "$ROOT/SYSTEM-FACTS.json"

echo "== T112 (1.56.1): XML reports are parsed behind a size ceiling =="
# The engine ingests reports produced by SOMEONE ELSE\'s build, with a stdlib parser and no
# defusedxml (stdlib-only is a hard contract). An unbounded read is a denial of service against
# the operator\'s own machine. A byte ceiling is the honest mitigation; the honest LIMIT is that
# entity expansion under the ceiling still expands, which SECURITY.md states rather than
# implying the parser is hardened.
T112=$("$PY" - "$KIT/.claude/skills/uscha-devloop/qa_ledger.py" <<'PY'
import importlib.util, io, os, sys, tempfile
spec = importlib.util.spec_from_file_location("ql", sys.argv[1])
ql = importlib.util.module_from_spec(spec); spec.loader.exec_module(ql)
bad = []
if not hasattr(ql, "_parse_xml"):   bad.append("sin _parse_xml")
if getattr(ql, "MAX_REPORT_BYTES", 0) <= 0: bad.append("sin MAX_REPORT_BYTES")
# every parse site must go through the guard
src = io.open(sys.argv[1], encoding="utf-8").read()
direct = src.count("ET.parse(")
if direct != 1:   # exactly one: the helper's own call
    bad.append("quedan %d ET.parse directos (deben ir por _parse_xml)" % (direct - 1))
d = tempfile.mkdtemp()
small = os.path.join(d, "ok.xml")
io.open(small, "w", encoding="utf-8").write("<testsuite name=\'x\'><testcase name=\'a\'/></testsuite>")
try:
    ql._parse_xml(small).getroot()
except Exception as exc:
    bad.append("un reporte normal fallo: %s" % exc)
# an oversized report must raise, not be parsed
big = os.path.join(d, "big.xml")
with io.open(big, "wb") as fh:
    fh.write(b"<testsuite>")
    fh.write(b" " * (ql.MAX_REPORT_BYTES + 16))
    fh.write(b"</testsuite>")
try:
    ql._parse_xml(big)
    bad.append("un reporte sobre el techo se parseo igual")
except ql.ReportTooLarge:
    pass
except Exception as exc:
    bad.append("techo: excepcion inesperada %s" % type(exc).__name__)
import shutil; shutil.rmtree(d, ignore_errors=True)
print("OK" if not bad else "BAD " + " | ".join(bad[:4]))
PY
)
if [ "$T112" = "OK" ]; then
  PASS=$((PASS+1)); echo "  ok   techo de tamano activo, todos los parse pasan por el guard, un reporte normal sigue funcionando"; \
else FAIL=$((FAIL+1)); echo "  FAIL $T112"; fi

echo "== T111 (1.56.0): uninstall removes ONLY what the kit wrote =="
# The installer writes into someone else uscha home: skill dirs, a settings.json entry and a
# blocking hook. Shipping that without an uninstall put the burden of a clean removal on the
# user, by hand, in files they did not write. The risk here is not failing to delete OURS --
# it is deleting THEIRS, so the test plants a foreign hook, a foreign setting and a foreign
# skill and asserts all three survive.
T111H="$(mktemp -d)"
T111=$("$PY" - "$KIT" "$T111H" <<'PY'
import json, os, subprocess, sys
kit, home = sys.argv[1], sys.argv[2]
INST = os.path.join(kit, "install-uscha.py")
def run(*a):
    return subprocess.run([sys.executable, INST] + list(a), capture_output=True, text=True)

bad = []
run("install", "--target", "all", "--home", home)
sp = os.path.join(home, ".claude", "settings.json")
s = json.load(open(sp, encoding="utf-8"))
s["hooks"]["PreToolUse"].append({"matcher": "*", "hooks": [{"type": "command", "command": "my-own-linter"}]})
s["mySetting"] = "keep me"
json.dump(s, open(sp, "w", encoding="utf-8"), indent=2)
mine = os.path.join(home, ".claude", "skills", "my-own-skill")
os.makedirs(mine, exist_ok=True)
open(os.path.join(mine, "SKILL.md"), "w").write("mine\n")

# --dry-run must plan without touching anything
r = run("uninstall", "--target", "all", "--home", home, "--dry-run", "--json")
if r.returncode: bad.append("dry-run exit %d" % r.returncode)
if not os.path.exists(os.path.join(home, ".claude", "skills", "uscha-devloop")):
    bad.append("dry-run BORRO archivos")

r = run("uninstall", "--target", "all", "--home", home, "--json")
if r.returncode: bad.append("uninstall exit %d" % r.returncode)

s2 = json.load(open(sp, encoding="utf-8"))
cmds = [h.get("command") for g in s2.get("hooks", {}).get("PreToolUse", []) for h in g.get("hooks", [])]
if "my-own-linter" not in cmds:      bad.append("borro un hook AJENO")
if any("block-approved" in str(c) for c in cmds): bad.append("dejo el hook nuestro")
if s2.get("mySetting") != "keep me": bad.append("perdio un setting ajeno")
if not os.path.isfile(os.path.join(mine, "SKILL.md")): bad.append("borro una skill AJENA")
for t_ in ("claude", "codex", "cursor", "pi"):
    leftover = {"claude": os.path.join(home, ".claude", "skills", "uscha-devloop"),
                "codex": os.path.join(home, "plugins", "uscha"),
                "cursor": os.path.join(home, ".cursor", "skills", "uscha-devloop"),
                "pi": os.path.join(home, ".agents", "skills", "uscha-devloop")}[t_]
    if os.path.exists(leftover): bad.append("%s: quedaron archivos nuestros" % t_)

# without a marker it must REFUSE rather than guess -- deleting a stranger tree is the worse bug
empty = os.path.join(home, "empty"); os.makedirs(empty, exist_ok=True)
os.makedirs(os.path.join(empty, ".cursor", "skills"), exist_ok=True)
r = run("uninstall", "--target", "cursor", "--home", empty)
if r.returncode == 0: bad.append("sin marker NO se nego")
r = run("uninstall", "--target", "cursor", "--home", empty, "--force")
if r.returncode != 0: bad.append("--force no pudo forzar")
print("OK" if not bad else "BAD " + " | ".join(bad[:5]))
PY
)
rm -rf "$T111H"
if [ "$T111" = "OK" ]; then
  PASS=$((PASS+1)); echo "  ok   uninstall: saca lo nuestro en los 7 targets, preserva hook/setting/skill ajenos, dry-run no toca, sin marker se niega"; \
else FAIL=$((FAIL+1)); echo "  FAIL $T111"; fi

echo "== T110 (1.55.2): the INV-GOLDEN hook, adversarially -- fail-closed, case, read vs write =="
# An external review showed the previous hook was fail-OPEN on a malformed payload,
# case-SENSITIVE (so a capitalised golden slipped past on case-insensitive filesystems),
# blocked harmless READS, and only inspected five tool names. Each of those is a case here.
# The honest limit stays: this matches TEXT, so an indirect write cannot be caught -- that
# case is asserted too, so nobody mistakes the guard for a sandbox.
T110=$("$PY" - "$KIT/hooks/block-approved-writes.py" <<'PY'
import importlib.util, io, json, subprocess, sys
hook = sys.argv[1]
G = "." + "approved"

def run(payload):
    p = subprocess.run([sys.executable, hook], input=json.dumps(payload),
                       capture_output=True, text=True)
    return p.returncode          # 2 = blocked, 0 = allowed

def raw(text):
    p = subprocess.run([sys.executable, hook], input=text, capture_output=True, text=True)
    return p.returncode

def bash(cmd):  return run({"tool_name": "Bash", "tool_input": {"command": cmd}})
def write(path): return run({"tool_name": "Write", "tool_input": {"file_path": path}})

cases = []
def expect(label, got, want):
    cases.append((label, got, want))

# writes must BLOCK
expect("Write to a golden",            write("tests/golden/x" + G + ".json"), 2)
expect("Write, UPPERCASE extension",   write("tests/golden/x" + G.upper() + ".json"), 2)
expect("Write, MixedCase",             write("tests/golden/x.Approved.json"), 2)
expect("bash redirect",                bash("echo hi > x" + G), 2)
expect("bash append",                  bash("echo hi >> x" + G), 2)
expect("bash mv",                      bash("mv a.received x" + G), 2)
expect("bash cp",                      bash("cp a b" + G), 2)
expect("bash rm",                      bash("rm x" + G), 2)
expect("bash tee",                     bash("echo x | tee y" + G), 2)
expect("reader THEN redirect",         bash("cat a" + G + " > b" + G), 2)
expect("sed in-place",                 bash("sed -i s/a/b/ x" + G), 2)
expect("unknown write-capable tool",   run({"tool_name": "SomeFutureEditor",
                                            "tool_input": {"target": "x" + G}}), 2)
expect("nested arg in unknown tool",   run({"tool_name": "Weird",
                                            "tool_input": {"edits": [{"path": "x" + G}]}}), 2)
# fail-CLOSED
expect("malformed payload",            raw("{not json"), 2)
expect("non-dict payload",             raw("[1,2,3]"), 2)

# legitimate reads must PASS -- golden-diff has to read the file it compares
expect("cat a golden",                 bash("cat x" + G), 0)
expect("diff two goldens",             bash("diff a" + G + " b.received"), 0)
expect("grep inside a golden",         bash("grep -n foo x" + G), 0)
expect("Read tool",                    run({"tool_name": "Read",
                                            "tool_input": {"file_path": "x" + G}}), 0)
expect("unrelated command",            bash("echo hello world"), 0)
expect("unrelated Write",              write("src/main.py"), 0)

# the documented BLIND SPOT: text matching cannot see an indirect write. Asserted so the
# limit is measured, not merely written in a docstring.
indirect = "python -c " + chr(34) + "open('x'+'.appro'+'ved','w')" + chr(34)
expect("indirect write (KNOWN blind spot)", bash(indirect), 0)

bad = ["%s: got %s want %s" % (l, g, w) for l, g, w in cases if g != w]
print("OK" if not bad else "BAD " + " | ".join(bad[:5]))
PY
)
if [ "$T110" = "OK" ]; then
  PASS=$((PASS+1)); echo "  ok   hook: bloquea escrituras (todo case), fail-closed, deja pasar lecturas; blind spot indirecto asertado"; \
else FAIL=$((FAIL+1)); echo "  FAIL $T110"; fi

echo "== T109 (1.54.0): first contact -- the 7 conversational skills orient a newcomer, ONCE =="
# Field feedback: a newcomer typing /uscha-discovery gets interrogated with no idea what it
# costs, what comes out, or that they can stop. The banner closes that. It is gated on the
# project having NO uscha artifacts yet, because a banner on every run is the ceremony the
# method forbids -- and the readouts (mirador/status) are excluded on purpose: their own
# contract is "one compact block, nothing else".
T109=$("$PY" - "$KIT" <<'PY'
import io, os, sys
kit = sys.argv[1]
READOUT = {"mirador", "status"}
LABELS = ("START]", "Method:", "Here:", "Output:", "Next:", "Stop:")
bad = []
for tree in (os.path.join(".claude", "skills"), "skills"):
    root = os.path.join(kit, tree)
    for d in sorted(x for x in os.listdir(root) if x.startswith("uscha-")):
        short = d[len("uscha-"):]
        txt = io.open(os.path.join(root, d, "SKILL.md"), encoding="utf-8").read()
        where = "%s/%s" % (tree, d)
        if short in READOUT:
            if "First contact" in txt:
                bad.append(where + ": readout NO debe llevar banner (contradice su contrato)")
            continue
        if "First contact" not in txt:
            bad.append(where + ": sin banner de primer contacto"); continue
        # scope the label check to the BANNER section: 'Next:' also lives in the close block,
        # so scanning the whole file made that one label unfalsifiable.
        i = txt.find("## First contact")
        j = txt.find("\n## ", i + 1)
        banner = txt[i:j if j != -1 else len(txt)]
        if ("[uscha · %s · START]" % short) not in banner:
            bad.append(where + ": el banner no nombra '%s'" % short)
        missing = [l for l in LABELS if l not in banner]
        if missing:
            bad.append(where + ": faltan labels " + ",".join(missing))
        # the ONCE gate must survive future edits, or the banner becomes ceremony
        if "QA-LEDGER.json" not in txt or "no uscha artifacts yet" not in txt:
            bad.append(where + ": perdio la condicion de primera-vez")
print("OK" if not bad else "BAD " + " | ".join(bad[:5]))
PY
)
if [ "$T109" = "OK" ]; then
  PASS=$((PASS+1)); echo "  ok   7 skills con banner propio + gate de primera-vez; los 2 readouts sin banner"; \
else FAIL=$((FAIL+1)); echo "  FAIL $T109"; fi

echo "== T108 (1.53.1): the macOS branch is EXECUTED from any OS (the kit's only darwin code) =="
# The whole kit branches win32-vs-POSIX except for exactly one thing, duplicated: the darwin
# arm of _open_best_effort. Since the CI matrix went manual, macOS is UNMEASURED -- but this
# arm does not need a Mac to be exercised: patch sys.platform, stub the syscall, and RUN it.
# That turns the kit's only mac-specific line from "never executed" into "executed every run",
# on every OS. It is NOT a substitute for a real macOS run (the doc still says UNMEASURED);
# it removes the one divergence that a Linux+Windows suite structurally could not reach.
T108=$("$PY" - "$KIT" <<'PY'
import importlib.util, subprocess, sys, os
kit = sys.argv[1]
targets = [os.path.join(kit, "install-uscha.py"),
           os.path.join(kit, ".claude", "skills", "uscha-mirador", "mirador-render.py"),
           os.path.join(kit, "skills", "uscha-mirador", "mirador-render.py")]
bad = []
for path in targets:
    name = os.path.relpath(path, kit).replace("\\", "/")
    spec = importlib.util.spec_from_file_location("m_" + str(abs(hash(path))), path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    if not hasattr(mod, "_open_best_effort"):
        bad.append(name + ": sin _open_best_effort"); continue
    real_platform, real_popen, real_startfile = sys.platform, subprocess.Popen, getattr(os, "startfile", None)
    calls = []
    try:
        mod.subprocess.Popen = lambda argv, *a, **k: calls.append(list(argv))
        # 1) darwin must shell out to `open` -- the kit's ONLY mac-specific instruction
        sys.platform = "darwin"
        calls[:] = []; mod._open_best_effort("/tmp/x.html")
        if calls != [["open", "/tmp/x.html"]]:
            bad.append("%s: darwin no llamo a open (%r)" % (name, calls))
        # 2) other POSIX must NOT get the mac command
        sys.platform = "linux"
        calls[:] = []; mod._open_best_effort("/tmp/x.html")
        if calls != [["xdg-open", "/tmp/x.html"]]:
            bad.append("%s: linux no llamo a xdg-open (%r)" % (name, calls))
        # 3) a mac WITHOUT `open` reachable must not take the process down (headless/CI)
        sys.platform = "darwin"
        def boom(*a, **k): raise OSError("no such file: open")
        mod.subprocess.Popen = boom
        try:
            mod._open_best_effort("/tmp/x.html")
        except Exception as exc:
            bad.append("%s: darwin propago la excepcion (%s)" % (name, exc))
    finally:
        sys.platform = real_platform
        mod.subprocess.Popen = real_popen
print("OK" if not bad else "BAD " + " | ".join(bad[:4]))
PY
)
if [ "$T108" = "OK" ]; then
  PASS=$((PASS+1)); echo "  ok   rama darwin ejecutada en los 3 archivos: llama a 'open', no pisa xdg-open, y falla en silencio"; \
else FAIL=$((FAIL+1)); echo "  FAIL $T108"; fi

echo "== T107 (1.53.0): every Agent-Skills target installs + measures from ONE table row =="
# cursor/copilot/gemini/cline joined pi as skills-only targets. They share one transactional
# installer and one doctor branch, so the risk is not the code -- it is the TABLE: a row whose
# root is wrong, or a target that silently never installs. This walks every row for real.
T107H="$(mktemp -d)"
python "$KIT/install-uscha.py" install --target all --home "$T107H" >/dev/null 2>&1
T107=$("$PY" - "$KIT" "$T107H" <<'PY'
import importlib.util, json, os, subprocess, sys
kit, home = sys.argv[1], sys.argv[2]
spec = importlib.util.spec_from_file_location("iu", os.path.join(kit, "install-uscha.py"))
iu = importlib.util.module_from_spec(spec); spec.loader.exec_module(iu)
bad = []
# the table must cover the newcomers and stay in TARGETS
for name in ("pi", "cursor", "copilot", "gemini", "cline"):
    if name not in iu.SKILL_ROOTS: bad.append("falta la fila %s" % name)
    elif name not in iu.TARGETS:   bad.append("%s no esta en TARGETS" % name)
# every row must have landed its 9 skills + marker at ITS OWN root
for name, parts in iu.SKILL_ROOTS.items():
    root = os.path.join(home, *parts)
    missing = [s for s in iu.SKILLS if not os.path.isfile(os.path.join(root, s, "SKILL.md"))]
    if missing: bad.append("%s: faltan %d skills en %s" % (name, len(missing), os.path.join(*parts)))
    if not os.path.isfile(os.path.join(root, "uscha-install.json")):
        bad.append("%s: sin marker" % name)
# no two rows may share a root -- a copy-paste typo would make one target clobber another
roots = ["/".join(p) for p in iu.SKILL_ROOTS.values()]
if len(set(roots)) != len(roots): bad.append("dos targets comparten root: %s" % roots)
out = subprocess.check_output([sys.executable, os.path.join(kit, "install-uscha.py"),
                               "doctor", "--target", "all", "--home", home, "--json"], text=True)
d = json.loads(out)
for name in iu.SKILL_ROOTS:
    st = d["targets"].get(name) or {}
    if not st.get("healthy"):        bad.append("doctor: %s no healthy" % name)
    if st.get("golden_guard") != "advisory":
        bad.append("%s: golden_guard=%r (debe ser advisory: no hay hook bloqueante)" % (name, st.get("golden_guard")))
# `both` must NOT grow as targets are added -- it is a legacy alias, that is the whole point
if iu.selected_targets("both") != ["codex", "claude"]: bad.append("'both' dejo de ser codex+claude")
if set(iu.selected_targets("all")) != set(iu.TARGETS): bad.append("'all' no cubre TARGETS")
print("OK" if not bad else "BAD " + " | ".join(bad[:5]))
PY
)
rm -rf "$T107H"
if [ "$T107" = "OK" ]; then
  PASS=$((PASS+1)); echo "  ok   5 targets Agent-Skills instalan en su root, doctor healthy, guard advisory, 'both' intacto"; \
else FAIL=$((FAIL+1)); echo "  FAIL $T107"; fi

echo "== T106 (1.52.1): the suite reads the version, it never pins it (no release toll) =="
# Every release used to edit six version literals in THIS file. That was pure toll: it proved
# nothing (install-uscha.py's source_version() reads the same VERSION file) and it broke the
# suite on each bump until someone retyped them. The version now flows from $KIT_VERSION.
# This check keeps a future edit from quietly pinning one again.
T106=$("$PY" - "$KIT/tests/smoke-engine.sh" "$KIT" "$KIT_VERSION" <<'PY'
import io, re, sys
smoke, kit, kit_version = sys.argv[1], sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else "")
src = io.open(smoke, encoding="utf-8").read()
version = io.open(kit + "/VERSION", encoding="utf-8").readline().split()[-1]
bad = []
# a version-shaped literal compared against a version / source_version key = a pin.
# EITHER quote style: a re-pin written with double quotes used to slip through this check.
# The quote chars are written as \x27 / \x22 ON PURPOSE: a LITERAL ' or " inside this
# heredoc-in-$() makes bash 3.2 -- the one macOS still ships -- hunt for a matching quote
# to the end of the file and die with "unexpected EOF". Linux/git-bash (4/5) parse it fine,
# which is exactly why only the macOS cell caught it.
Q = "[\x27\x22]"
for m in re.finditer(r"\[" + Q + r"(?:source_)?version" + Q + r"\]\s*==\s*" + Q + r"(\d+\.\d+\.\d+)" + Q, src):
    bad.append("version fijada en linea %d: %s" % (src[:m.start()].count("\n") + 1, m.group(1)))
# the changelog filename must be derived too
if re.search(r"CHANGELOG-\d+\.\d+\.\d+\.md", src):
    bad.append("nombre de CHANGELOG fijado (debe derivarse de VERSION)")
# the derivation must exist AND have produced the right value: kit_version is the REAL
# runtime value the shell computed, not a re-derivation of it (that would be circular).
if not re.search(r"^KIT_VERSION=", src, flags=re.M):
    bad.append("falta KIT_VERSION derivado de VERSION")
elif kit_version != version:
    bad.append("KIT_VERSION=%r no coincide con VERSION=%r" % (kit_version, version))
print("OK" if not bad else "BAD " + " | ".join(bad[:4]))
PY
)
if [ "$T106" = "OK" ]; then
  PASS=$((PASS+1)); echo "  ok   cero versiones fijadas: la suite las lee de VERSION ($KIT_VERSION)"; \
else FAIL=$((FAIL+1)); echo "  FAIL $T106"; fi

echo "== T105 (1.52.0): every skill declares the orientation markers (breadcrumb + close block) =="
# Field feedback: the operator got lost -- no in-flow signal of WHERE they were, and a phase
# that converged and then went silent instead of saying what came next. The markers are a
# CONVENTION, so they only work if all nine skills carry them identically; a skill that quietly
# drops one is exactly the drift T57 mechanized for skill counts. Checked on BOTH twin trees.
T105=$("$PY" - "$KIT" <<'PY'
import io, os, sys
kit = sys.argv[1]
# Two variants on purpose: mirador/status are one-shot read-only readouts whose own contract is
# "this block IS the answer, never pad it", so the conversational close block would contradict
# the skill it was added to. They carry the routing pair only.
READOUT = {"mirador", "status"}
bad = []
for tree in (os.path.join(".claude", "skills"), "skills"):
    root = os.path.join(kit, tree)
    skills = sorted(d for d in os.listdir(root) if d.startswith("uscha-"))
    if len(skills) != 9:
        bad.append("%s: %d skills (esperaba 9)" % (tree, len(skills))); continue
    for d in skills:
        short = d[len("uscha-"):]
        txt = io.open(os.path.join(root, d, "SKILL.md"), encoding="utf-8").read()
        where = "%s/%s" % (tree, d)
        if "Orientation markers" not in txt:
            bad.append(where + ": sin seccion de marcadores"); continue
        # the breadcrumb must name THIS skill -- a copy-paste from a sibling is drift
        if ("[uscha · %s ·" % short) not in txt:
            bad.append(where + ": breadcrumb no nombra '%s'" % short)
        for label in ("Next:", "Run:"):
            if label not in txt:
                bad.append(where + ": falta label " + label)
        if short in READOUT:
            # the readout variant must NOT carry the conversational block that its own
            # "nothing else" contract forbids
            if "CLOSED]" in txt or "Produced:" in txt:
                bad.append(where + ": readout no debe llevar el bloque conversacional")
        else:
            # assert the CLOSED HEADER itself, not just the bare word: a header naming another
            # skill used to slip through while the breadcrumb line stayed correct
            if ("[uscha · %s · CLOSED]" % short) not in txt:
                bad.append(where + ": header CLOSED ausente o nombra otra skill")
            for label in ("Produced:", "Blocks:"):
                if label not in txt:
                    bad.append(where + ": falta label " + label)
            # the anti-narration rules must survive future edits of this block
            if "Never write a denominator" not in txt:
                bad.append(where + ": perdio la regla anti-denominador")
            if "loop_count" not in txt:
                bad.append(where + ": perdio la regla de usar el conteo MEDIDO")
print("OK" if not bad else "BAD " + " | ".join(bad[:6]))
PY
)
if [ "$T105" = "OK" ]; then
  PASS=$((PASS+1)); echo "  ok   las 9 skills (x2 gemelos) declaran breadcrumb propio + bloque de cierre con sus 5 labels"; \
else FAIL=$((FAIL+1)); echo "  FAIL $T105"; fi

echo "== T104 (1.51.3): every published manifest points at the public site (no homepage drift) =="
# The kit is published on FOUR surfaces (npm, the Claude plugin, the Codex plugin, the
# marketplace) and each carries its own homepage. They drifted apart before (T57 mechanized the
# same class of drift for skill counts), so the site link is asserted, not trusted.
T104=$("$PY" - "$ROOT" "$KIT" <<'PY'
import importlib.util, io, json, os, sys
root, kit = sys.argv[1], sys.argv[2]
SITE = "https://uscha.dev"
manifests = {
    "package.json": ("homepage",),
    os.path.join("uscha-kit", ".claude-plugin", "plugin.json"): ("homepage",),
    os.path.join("uscha-kit", ".codex-plugin", "plugin.json"): ("homepage",),
}
bad = []
for rel, keys in manifests.items():
    d = json.load(io.open(os.path.join(root, rel), encoding="utf-8"))
    for k in keys:
        if d.get(k) != SITE:
            bad.append("%s:%s=%r" % (rel, k, d.get(k)))
mk = json.load(io.open(os.path.join(root, ".claude-plugin", "marketplace.json"), encoding="utf-8"))
if mk["plugins"][0].get("homepage") != SITE:
    bad.append("marketplace.json:homepage=%r" % mk["plugins"][0].get("homepage"))
# the READMEs a human actually lands on must name the site too
for rel in ("README.md", os.path.join("uscha-kit", "README.md")):
    if SITE not in io.open(os.path.join(root, rel), encoding="utf-8").read():
        bad.append("%s: no menciona %s" % (rel, SITE))
# The Codex manifest that actually lands on disk is GENERATED, not copied -- checking only the
# repo file let the installed one keep pointing at GitHub for a whole release (kit 1.53.0).
# Assert the generator too, or this check measures the wrong artifact.
spec = importlib.util.spec_from_file_location("iu", os.path.join(kit, "install-uscha.py"))
iu = importlib.util.module_from_spec(spec); spec.loader.exec_module(iu)
if iu.plugin_manifest().get("homepage") != SITE:
    bad.append("plugin_manifest() GENERADO: homepage=%r" % iu.plugin_manifest().get("homepage"))
print("OK" if not bad else "BAD " + "; ".join(bad))
PY
)
if [ "$T104" = "OK" ]; then
  PASS=$((PASS+1)); echo "  ok   npm + ambos plugins + marketplace + los READMEs apuntan a uscha.dev"; \
else FAIL=$((FAIL+1)); echo "  FAIL $T104"; fi

echo "== T103 (1.51.x): doctor recognizes the hook across an interpreter change (install vs doctor) =="
# install-uscha.py's doctor used to EXACT-match the hook command, which embeds sys.executable
# (an absolute interpreter path). When install-time and doctor-time run under different pythons
# -- e.g. a `python` that resolves to a different sys.executable between two invocations, seen
# on Windows CI -- the exact-match false-reported a healthy claude hook as `hook_registered:
# False`, failing the real-installer end-to-end step. hook_registered now matches by the guard
# SCRIPT (block-approved-writes.py), not the full command string, like the N-1 prune does.
T103=$("$PY" - "$KIT/install-uscha.py" <<'PY'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("iu", sys.argv[1])
iu = importlib.util.module_from_spec(spec); spec.loader.exec_module(iu)
# settings as INSTALL wrote them: command references the hook via interpreter A
settings = {"hooks": {"PreToolUse": [{"matcher": "*", "hooks": [{"type": "command",
    "command": "C:/py-A/python.exe C:/Users/u/.claude/hooks/block-approved-writes.py"}]}]}}
# doctor recomputes hook_command under interpreter B (different absolute path) -- same script
doctor_cmd = "C:/py-B/python.exe C:/Users/u/.claude/hooks/block-approved-writes.py"
mismatch_ok = iu.hook_registered(settings, doctor_cmd) is True
# a DIFFERENT script must NOT be treated as our hook (no false positive)
foreign = {"hooks": {"PreToolUse": [{"matcher": "*", "hooks": [{"type": "command",
    "command": "python /home/u/.claude/hooks/some-other-linter.py"}]}]}}
foreign_ok = iu.hook_registered(foreign, doctor_cmd) is False
# path-anchored: a SUFFIX-collision script and a bare mention in a -c snippet must NOT match --
# the match anchors on a path separator before HOOK_NAME, else golden_guard could read enforced
# off a foreign or spoofed entry.
suffix = {"hooks": {"PreToolUse": [{"matcher": "*", "hooks": [{"type": "command",
    "command": "python /home/u/.claude/hooks/not-block-approved-writes.py"}]}]}}
mention = {"hooks": {"PreToolUse": [{"matcher": "*", "hooks": [{"type": "command",
    "command": "python -c \"print('block-approved-writes.py')\""}]}]}}
anchor_ok = (iu.hook_registered(suffix, doctor_cmd) is False
             and iu.hook_registered(mention, doctor_cmd) is False)
# a None command in a group must be skipped, not crash
noneish = {"hooks": {"PreToolUse": [{"matcher": "*", "hooks": [{"type": "command", "command": None}]}]}}
none_ok = iu.hook_registered(noneish, doctor_cmd) is False
# empty settings -> not registered
empty_ok = iu.hook_registered({}, doctor_cmd) is False
print("OK" if mismatch_ok and foreign_ok and anchor_ok and none_ok and empty_ok else
      "BAD mismatch=%s foreign=%s anchor=%s none=%s empty=%s"
      % (mismatch_ok, foreign_ok, anchor_ok, none_ok, empty_ok))
PY
)
if [ "$T103" = "OK" ]; then
  PASS=$((PASS+1)); echo "  ok   hook_registered matches by script across interpreter change; no false positive on a foreign hook"; \
else FAIL=$((FAIL+1)); echo "  FAIL $T103"; fi

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
import filecmp, json, os, re, subprocess, sys
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
    # AC-03 used to be UNMEASURED in CI: the name list lived only in an untracked
    # .uscha-private-names, so every public run emitted <skipped/>. That hid a real miss --
    # names sat in four TRACKED files for weeks, in audits/ and formats/, which this check
    # did not even walk (it only looked at uscha-kit/ and README.md). Two holes, both fixed:
    #   1. a COMMITTED hash list (.uscha-private-names.sha256) makes the criterion runnable
    #      anywhere without publishing the names -> no more <skipped/> in CI;
    #   2. the walk now covers the WHOLE repo, not the kit alone.
    # The untracked plaintext list is still read when present: it is the stricter superset
    # (it may carry prefixes/regexes, which a hash cannot express).
    import hashlib
    hashed_file = os.path.join(root, ".uscha-private-names.sha256")
    plain_file = os.path.join(root, ".uscha-private-names")
    hashes = set()
    try:
        with open(hashed_file, encoding="utf-8") as fh:
            for ln in fh:
                s = ln.strip()
                if s and not s.startswith("#"):
                    hashes.add(s.lower())
    except OSError:
        pass
    names = []
    try:
        with open(plain_file, encoding="utf-8") as fh:
            names = [ln.strip() for ln in fh
                     if ln.strip() and not ln.lstrip().startswith("#")]
    except OSError:
        pass
    if not hashes and not names:
        return SKIP  # sentinel: emitted as <skipped/>, closes nothing -- absence is not success
    pat = re.compile("|".join(names), re.I) if names else None
    token_re = re.compile(r"[A-Za-z][A-Za-z0-9_]{2,}")

    def token_hit(text):
        if not hashes:
            return False
        for tok in token_re.findall(text):
            low = tok.lower()
            if hashlib.sha256(low.encode("utf-8")).hexdigest() in hashes:
                return True
            if "_" in low:   # a listed term may be one part of a compound token
                for part in low.split("_"):
                    if len(part) > 2 and hashlib.sha256(part.encode("utf-8")).hexdigest() in hashes:
                        return True
        return False

    skip_files = {".uscha-private-names", ".uscha-private-names.sha256",
                  "private-names-hash.py"}
    exts = (".md", ".py", ".sh", ".json", ".html", ".ps1", ".txt", ".yml", ".yaml", ".tex", ".js")
    # TRACKED files only. The criterion is about what the kit and its docs CONTAIN -- i.e. what
    # is published -- not about whatever sits in someone's working tree. Scanning the filesystem
    # flagged an untracked local transcript and handoff, which can never leak; keeping untracked
    # noise here would train the operator to ignore a red AC-03, which is worse than not having
    # it. Untracked local artifacts are .gitignore's job (and it covers them).
    try:
        listing = subprocess.run(["git", "-C", root, "ls-files"], capture_output=True,
                                 text=True, encoding="utf-8", errors="replace")
        files = [f for f in listing.stdout.splitlines() if f.strip()]
    except Exception:
        files = []
    if not files:      # no git available -> cannot establish what is published
        return SKIP
    hits = []
    for rel in files:
        if not rel.endswith(exts) or os.path.basename(rel) in skip_files:
            continue
        p = os.path.join(root, rel)
        try:
            body = open(p, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        if (pat and pat.search(body)) or token_hit(body):
            hits.append(rel)
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

# Fast-path feature criteria (ADR-003): measured by T113 against real git fixtures; the
# sidecar carries one verdict per criterion so each closes on its OWN testcase. Absent
# sidecar or a null case (the golden not yet human-approved) -> skipped, never green.
def _fastpath_cases():
    p = os.path.join(kit, "reports", "junit", ".fastpath-cases.json")
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None
_fpc = _fastpath_cases()
for _fid in ("AC-FP-01", "AC-FP-02", "AC-FP-03", "AC-FP-05", "AC-FP-06",
             "AC-FP-07", "AC-FP-08", "AC-FP-09", "AC-FP-10", "AC-FP-11"):
    if _fpc is None or _fpc.get(_fid) is None:
        results.append((_fid, "fastpath", SKIP))
    elif _fpc.get(_fid) is True:
        results.append((_fid, "fastpath", None))
    else:
        results.append((_fid, "fastpath", "T113 case failed or missing"))

# Spec-drift criteria (ADR-005): measured by T114, same sidecar contract as T113.
def _specdrift_cases():
    p = os.path.join(kit, "reports", "junit", ".specdrift-cases.json")
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None
_sdc = _specdrift_cases()
for _sid in ("AC-SD-01", "AC-SD-02", "AC-SD-03", "AC-SD-04", "AC-SD-05"):
    if _sdc is None or _sdc.get(_sid) is None:
        results.append((_sid, "specdrift", SKIP))
    elif _sdc.get(_sid) is True:
        results.append((_sid, "specdrift", None))
    else:
        results.append((_sid, "specdrift", "T114 case failed or missing"))

# Golden-coverage criteria (ADR-006): measured by T117, same sidecar contract.
def _goldencov_cases():
    p = os.path.join(kit, "reports", "junit", ".goldencov-cases.json")
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None
_gcc = _goldencov_cases()
for _gid in ("AC-GM-01", "AC-GM-02", "AC-GM-03", "AC-GM-04",
             "AC-GM-05", "AC-GM-06", "AC-GM-07", "AC-GM-08"):
    if _gcc is None or _gcc.get(_gid) is None:
        results.append((_gid, "goldencov", SKIP))
    elif _gcc.get(_gid) is True:
        results.append((_gid, "goldencov", None))
    else:
        results.append((_gid, "goldencov", "T117 case failed or missing"))

# Evidence-origin criteria (ADR-007): measured by T118, same sidecar contract.
def _origin_cases():
    p = os.path.join(kit, "reports", "junit", ".origin-cases.json")
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None
_oc = _origin_cases()
for _oid in ("AC-EP-01", "AC-EP-02", "AC-EP-03", "AC-EP-04", "AC-EP-05"):
    if _oc is None or _oc.get(_oid) is None:
        results.append((_oid, "evidence-origin", SKIP))
    elif _oc.get(_oid) is True:
        results.append((_oid, "evidence-origin", None))
    else:
        results.append((_oid, "evidence-origin", "T118 case failed or missing"))

# Clean-room criteria (ADR-008): measured by T119, same sidecar contract.
def _cleanroom_cases():
    p = os.path.join(kit, "reports", "junit", ".cleanroom-cases.json")
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None
_crc = _cleanroom_cases()
for _cid in ("AC-CR-01", "AC-CR-02", "AC-CR-03", "AC-CR-04",
             "AC-CR-05", "AC-CR-06", "AC-CR-07", "AC-CR-08"):
    if _crc is None or _crc.get(_cid) is None:
        results.append((_cid, "cleanroom", SKIP))
    elif _crc.get(_cid) is True:
        results.append((_cid, "cleanroom", None))
    else:
        results.append((_cid, "cleanroom", "T119 case failed or missing"))

# Curation criteria (ADR-009/010): measured by T120, same sidecar contract.
def _curation_cases():
    p = os.path.join(kit, "reports", "junit", ".curation-cases.json")
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None
_cuc = _curation_cases()
for _uid in ("AC-RD-01", "AC-RD-02", "AC-RD-03", "AC-RD-04",
             "AC-RD-05", "AC-RD-06", "AC-RD-07", "AC-RD-13"):
    if _cuc is None or _cuc.get(_uid) is None:
        results.append((_uid, "curation", SKIP))
    elif _cuc.get(_uid) is True:
        results.append((_uid, "curation", None))
    else:
        results.append((_uid, "curation", "T120 case failed or missing"))

# Oracle criteria (slice 2): measured by T121, same sidecar contract.
def _oracle_cases():
    p = os.path.join(kit, "reports", "junit", ".oracle-cases.json")
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None
_orc = _oracle_cases()
for _oid in ("AC-RD-08", "AC-RD-09", "AC-RD-10", "AC-RD-11", "AC-RD-12"):
    if _orc is None or _orc.get(_oid) is None:
        results.append((_oid, "oracle", SKIP))
    elif _orc.get(_oid) is True:
        results.append((_oid, "oracle", None))
    else:
        results.append((_oid, "oracle", "T121 case failed or missing"))

# SYSTEM-FACTS criteria (T0, ADR-012): measured by T122, same sidecar contract.
def _facts_cases():
    p = os.path.join(kit, "reports", "junit", ".facts-cases.json")
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None
_sfc = _facts_cases()
for _sfid in ("AC-SF-01", "AC-SF-02", "AC-SF-03", "AC-SF-04", "AC-SF-05"):
    if _sfc is None or _sfc.get(_sfid) is None:
        results.append((_sfid, "system-facts", SKIP))
    elif _sfc.get(_sfid) is True:
        results.append((_sfid, "system-facts", None))
    else:
        results.append((_sfid, "system-facts", "T122 case failed or missing"))

# CANDIDATE-DELTA criteria (Diamond M1, ADR-013): measured by T123, same sidecar contract.
def _delta_cases():
    p = os.path.join(kit, "reports", "junit", ".delta-cases.json")
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None
_dlc = _delta_cases()
for _did in ("AC-DD-01", "AC-DD-02", "AC-DD-03", "AC-DD-04", "AC-DD-05", "AC-DD-06",
             "AC-DD-07",
             "AC-CU-01", "AC-CU-02", "AC-CU-03", "AC-CU-04", "AC-CU-05", "AC-CU-06"):
    if _dlc is None or _dlc.get(_did) is None:
        results.append((_did, "candidate-delta", SKIP))
    elif _dlc.get(_did) is True:
        results.append((_did, "candidate-delta", None))
    else:
        results.append((_did, "candidate-delta", "T123 case failed or missing"))

# Fidelity criteria (Diamond M1, ADR-014): measured by T124, same sidecar contract.
def _fidelity_cases():
    p = os.path.join(kit, "reports", "junit", ".fidelity-cases.json")
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None
_fvc = _fidelity_cases()
for _fid in ("AC-FV-01", "AC-FV-02", "AC-FV-03", "AC-FV-04", "AC-FV-05", "AC-FV-06"):
    if _fvc is None or _fvc.get(_fid) is None:
        results.append((_fid, "fidelity", SKIP))
    elif _fvc.get(_fid) is True:
        results.append((_fid, "fidelity", None))
    else:
        results.append((_fid, "fidelity", "T124 case failed or missing"))

# IR criteria (Diamond M2, ADR-015): measured by T125, same sidecar contract.
def _ir_cases():
    p = os.path.join(kit, "reports", "junit", ".ir-cases.json")
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None
_irc = _ir_cases()
for _iid in ("AC-IR-01", "AC-IR-02", "AC-IR-03", "AC-IR-04", "AC-IR-05", "AC-IR-06"):
    if _irc is None or _irc.get(_iid) is None:
        results.append((_iid, "ir", SKIP))
    elif _irc.get(_iid) is True:
        results.append((_iid, "ir", None))
    else:
        results.append((_iid, "ir", "T125 case failed or missing"))

# Compiler-contract criteria (Diamond M3, ADR-016): measured by T126, same sidecar contract.
def _compile_cases():
    p = os.path.join(kit, "reports", "junit", ".compile-cases.json")
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None
_ccc = _compile_cases()
for _cid in ("AC-CC-01", "AC-CC-02", "AC-CC-03", "AC-CC-04", "AC-CC-05", "AC-CC-06",
             "AC-CC-07"):
    if _ccc is None or _ccc.get(_cid) is None:
        results.append((_cid, "compile", SKIP))
    elif _ccc.get(_cid) is True:
        results.append((_cid, "compile", None))
    else:
        results.append((_cid, "compile", "T126 case failed or missing"))

# Bootstrap criteria (Diamond M4, ADR-017): measured by T127, same sidecar contract.
def _bootstrap_cases():
    p = os.path.join(kit, "reports", "junit", ".bootstrap-cases.json")
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None
_bsc = _bootstrap_cases()
for _bid in ("AC-BS-01", "AC-BS-02", "AC-BS-03", "AC-BS-04", "AC-BS-05", "AC-BS-06"):
    if _bsc is None or _bsc.get(_bid) is None:
        results.append((_bid, "bootstrap", SKIP))
    elif _bsc.get(_bid) is True:
        results.append((_bid, "bootstrap", None))
    else:
        results.append((_bid, "bootstrap", "T127 case failed or missing"))

# Diamond Bench criteria (Diamond M5, ADR-018): measured by T128, same sidecar contract.
def _bench_cases():
    p = os.path.join(kit, "reports", "junit", ".bench-cases.json")
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None
_dbc = _bench_cases()
for _dbid in ("AC-DB-01", "AC-DB-02", "AC-DB-03", "AC-DB-04", "AC-DB-05", "AC-DB-06",
              "AC-BG-01", "AC-BG-02", "AC-BG-03", "AC-BG-04", "AC-BG-05",
              "AC-FC-01", "AC-FC-02", "AC-FC-03"):
    if _dbc is None or _dbc.get(_dbid) is None:
        results.append((_dbid, "bench", SKIP))
    elif _dbc.get(_dbid) is True:
        results.append((_dbid, "bench", None))
    else:
        results.append((_dbid, "bench", "T128 case failed or missing"))

# Bench-curation criteria (ADR-023): measured by T130, same sidecar contract.
def _bench_curate_cases():
    p = os.path.join(kit, "reports", "junit", ".bench-curate-cases.json")
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None
_bcc = _bench_curate_cases()
for _bcid in ("AC-BC-01", "AC-BC-02", "AC-BC-03", "AC-BC-04"):
    if _bcc is None or _bcc.get(_bcid) is None:
        results.append((_bcid, "bench-curation", SKIP))
    elif _bcc.get(_bcid) is True:
        results.append((_bcid, "bench-curation", None))
    else:
        results.append((_bcid, "bench-curation", "T130 case failed or missing"))

# Controlled-language criteria (Diamond, ADR-019): measured by T129, same sidecar contract.
def _lang_cases():
    p = os.path.join(kit, "reports", "junit", ".lang-cases.json")
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None
_lcc = _lang_cases()
for _lid in ("AC-CL-01", "AC-CL-02", "AC-CL-03", "AC-CL-04", "AC-CL-05", "AC-CL-06",
             "AC-CL2-01", "AC-CL2-02", "AC-CL2-03", "AC-CL2-04"):
    if _lcc is None or _lcc.get(_lid) is None:
        results.append((_lid, "controlled-language", SKIP))
    elif _lcc.get(_lid) is True:
        results.append((_lid, "controlled-language", None))
    else:
        results.append((_lid, "controlled-language", "T129 case failed or missing"))

# Controlled-language v0.3 criteria (ADR-024): measured by T131, same sidecar contract.
def _lang3_cases():
    p = os.path.join(kit, "reports", "junit", ".lang3-cases.json")
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None
_l3c = _lang3_cases()
for _l3id in ("AC-CL3-01", "AC-CL3-02", "AC-CL3-03"):
    if _l3c is None or _l3c.get(_l3id) is None:
        results.append((_l3id, "controlled-language-v03", SKIP))
    elif _l3c.get(_l3id) is True:
        results.append((_l3id, "controlled-language-v03", None))
    else:
        results.append((_l3id, "controlled-language-v03", "T131 case failed or missing"))

# Slack hypothesis criteria (ADR-025, ADR-026): measured by T132, same sidecar contract.
def _sched_cases():
    p = os.path.join(kit, "reports", "junit", ".sched-cases.json")
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None
_shc = _sched_cases()
for _shid in ("AC-SH-01", "AC-SH-02", "AC-SH-03", "AC-LI-01", "AC-LI-02", "AC-LI-03"):
    if _shc is None or _shc.get(_shid) is None:
        results.append((_shid, "slack-hypothesis", SKIP))
    elif _shc.get(_shid) is True:
        results.append((_shid, "slack-hypothesis", None))
    else:
        results.append((_shid, "slack-hypothesis", "T132 case failed or missing"))

# Intra-model variance criteria (ADR-027): measured by T133, same sidecar contract.
def _r2_cases():
    p = os.path.join(kit, "reports", "junit", ".r2-cases.json")
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None
_r2c = _r2_cases()
for _r2id in ("AC-R2-01", "AC-R2-02", "AC-R2-03"):
    if _r2c is None or _r2c.get(_r2id) is None:
        results.append((_r2id, "intra-model-variance", SKIP))
    elif _r2c.get(_r2id) is True:
        results.append((_r2id, "intra-model-variance", None))
    else:
        results.append((_r2id, "intra-model-variance", "T133 case failed or missing"))

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
