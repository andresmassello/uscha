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
SB="$(mktemp -d 2>/dev/null || echo "${TMP:-/tmp}/smoke-$$")"; mkdir -p "$SB/repo-a" "$SB/repo-b" "$SB/repo-c" "$SB/repo-d" "$SB/repo-e" "$SB/repo-f" "$SB/repo-g" "$SB/repo-h" "$SB/repo-i" "$SB/repo-j"
cd "$SB"

PASS=0; FAIL=0
chk() { # $1 = descripción, $2 = exit esperado, $3.. = comando
  local desc="$1" want="$2"; shift 2
  "$@" >/dev/null 2>&1; local got=$?
  if [ "$got" -eq "$want" ]; then PASS=$((PASS+1)); echo "  ok   $desc"
  else FAIL=$((FAIL+1)); echo "  FAIL $desc (exit $got, esperado $want)"; fi
}
run() { PYTHONIOENCODING=utf-8 "$PY" "$QL" "$@"; }

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
{"reason":"compiler-message","message":{"level":"error","code":{"code":"clippy::unwrap_used"},"spans":[{"file_name":"src/lib.rs","line_start":2,"is_primary":true}]}}
{"reason":"compiler-message","message":{"level":"warning","code":{"code":"clippy::needless_return"},"spans":[{"file_name":"src/lib.rs","line_start":3,"is_primary":true}]}}
{"reason":"compiler-message","message":{"level":"warning","code":{"code":"clippy::needless_return"},"spans":[{"file_name":"src/lib.rs","line_start":3,"is_primary":true}]}}
{"reason":"compiler-message","message":{"level":"error","code":null,"spans":[{"file_name":"src/lib.rs","line_start":1,"is_primary":true}]}}
{"reason":"compiler-message","message":{"level":"warning","code":null,"spans":[],"message":"1 warning emitted"}}
{"reason":"compiler-message","message":{"level":"error","code":null,"spans":[],"message":"aborting due to 1 previous error"}}
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
assert t['AC-1'] == {'green': 1, 'red': 0}, 'flaky-que-paso = verde'
assert t['AC-2'] == {'green': 0, 'red': 1}, 'fallo-tras-reruns = rojo'
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
mkdir -p repo-x
printf '{ "defaults": { "acceptance_file": "ACCEPTANCE.md", "qa_tools_order": ["code-review","judgment-day","improve"] },\n  "repos": [ {"name":"fsm","path":"repo-x","type":"go"} ], "integration": {"enabled": false} }\n' > c-fsm.json
run init --config c-fsm.json --out L-fsm.json >/dev/null 2>&1
chk "ledger virgen -> plan" 0 run phase --ledger L-fsm.json --repo fsm --require plan
run snapshot --ledger L-fsm.json --repo fsm >/dev/null 2>&1
chk "snapshot medido sin QA -> build" 0 run phase --ledger L-fsm.json --repo fsm --require build
run log-step --ledger L-fsm.json --repo fsm --tool code-review --iteration 1 \
  --gated-reported 2 --tests-passed true >/dev/null 2>&1
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
  && { PASS=$((PASS+1)); echo "  ok   doctor: 6/6 skills, install por proyecto, config y ACCEPTANCE leidos"; } \
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

echo "== T44 sync quintuple de version: VERSION = config = plugin.json = marketplace.json =="
"$PY" -c "
import json, sys, os, io
kit = os.path.dirname(os.path.dirname(os.path.dirname(sys.argv[1])))  # <kit>/.claude/skills/x -> <kit>
repo = os.path.dirname(kit)
v_file = io.open(os.path.join(kit, 'VERSION'), encoding='utf-8').read().split()[-1]
v_cfg = json.load(io.open(os.path.join(kit, 'uscha.config.json'), encoding='utf-8'))['version']
v_plug = json.load(io.open(os.path.join(kit, '.claude-plugin', 'plugin.json'), encoding='utf-8'))['version']
mk = json.load(io.open(os.path.join(repo, '.claude-plugin', 'marketplace.json'), encoding='utf-8'))
v_mkt = mk['plugins'][0]['version']
vs = {v_file, v_cfg, v_plug, v_mkt}
print('  versiones:', v_file, v_cfg, v_plug, v_mkt)
sys.exit(0 if len(vs) == 1 else 1)" "$(dirname "$QL")" \
  && { PASS=$((PASS+1)); echo "  ok   las cuatro fuentes de version coinciden"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL drift de version entre VERSION/config/plugin/marketplace"; }

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
keys = ['project','generated','readiness','subscores','phases','specs','adrs','inv','capas','loops','snapshots','evidence']
assert all(k in d for k in keys), 'faltan claves: ' + str([k for k in keys if k not in d])
assert isinstance(d['readiness']['score'], (int, float)), 'readiness.score'
assert d['specs'] == [] and d['capas'] == [], 'specs/capas deben ser [] (truth-pass, sin fuente)'
assert len(d['adrs']) == 2 and d['adrs'][0]['status'] == 'done' and d['adrs'][1]['status'] == 'prog', 'adrs glob'
assert d['snapshots'] == [], 'snapshots vacio antes de --record'
assert len(d['phases']) == 8 and len(d['inv']) == 7, 'esqueleto phases(8)/inv(7)'
sys.exit(0)" \
  && { PASS=$((PASS+1)); echo "  ok   contrato completo; specs/capas []; adrs del glob; snapshots vacio pre-record"; } \
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
"$PY" "$RENDER" --engine "$QL" --ledger L-mirp.json --template "$TPL" --out mir-out.html --sidecar tele/telemetry.jsonl --refresh 30 >/dev/null 2>&1
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
"$PY" "$RENDER" --engine "$QL" --ledger L-ep.json --template "$TPL" --out ep-mir.html >/dev/null 2>&1
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
## Hypothesis
El checkout nuevo reduce abandonos sin subir errores.
## Feedback Signal
Conversion rate y errores de pago en produccion.
## Review By: 2099-01-01
## Promote Criteria
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

echo "== T66 universal installer (1.40.0): Codex plugin + Claude adapter, dry-run safe =="
INST_HOME="$SB/home-installer"
mkdir -p "$INST_HOME"
"$PY" "$KIT/install-uscha.py" version --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
ok = (d['source_version'] == '1.40.0' and 'codex' in d['targets'] and 'claude' in d['targets'])
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
      json.load(open(manifest, encoding='utf-8'))['version'] == '1.40.0' and
      json.load(open(marker, encoding='utf-8'))['target'] == 'codex')
sys.exit(0 if ok else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   install codex crea plugin personal, marketplace y marker"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL install codex incompleto"; }
"$PY" "$KIT/install-uscha.py" doctor --target codex --home "$INST_HOME" --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
ok = (d['source_version'] == '1.40.0' and d['targets']['codex']['installed'] is True and d['targets']['codex']['version_match'] is True)
sys.exit(0 if ok else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   doctor detecta Codex instalado y version match"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL doctor no detecta install Codex"; }
diff -qr "$KIT/.claude/skills" "$KIT/skills" -x __pycache__ >/dev/null 2>&1 \
  && { PASS=$((PASS+1)); echo "  ok   Codex plugin skills mirror stays synced with canonical skills"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL uscha-kit/skills drifted from .claude/skills"; }


echo "== T67 npm router (1.40.0): npx package delegates to canonical installer =="
if command -v node >/dev/null 2>&1; then
  node "$ROOT/bin/uscha.js" version --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
ok = (d['source_version'] == '1.40.0' and 'codex' in d['targets'] and 'claude' in d['targets'])
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
ok = (d['name'] == '@andresmassello/uscha' and d['version'] == '1.40.0'
      and 'bin/uscha.js' in files and 'uscha-kit/install-uscha.py' in files
      and '.atl/skill-registry.md' not in files and 'handoff.md' not in files and 'mirador.html' not in files)
sys.exit(0 if ok else 1)" \
    && { PASS=$((PASS+1)); echo "  ok   npm pack dry-run incluye router/kit y excluye artefactos locales"; } \
    || { FAIL=$((FAIL+1)); echo "  FAIL npm pack dry-run no tiene el contenido esperado"; }
else
  FAIL=$((FAIL+1)); echo "  FAIL npm no esta disponible para probar package dry-run"
fi

echo ""
echo "RESULTADO: $PASS ok · $FAIL fail"
cd / && rm -rf "$SB"
[ "$FAIL" -eq 0 ]
