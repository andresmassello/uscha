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
# y spikes (v1.19.0): rama spike/* jamas pasa el gate de PR.
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
QL="$KIT/.claude/skills/dev-loop/qa_ledger.py"
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

cat > dev-loop.config.json <<'EOF'
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
run init --config dev-loop.config.json >/dev/null || { echo "FAIL init"; exit 1; }

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
t = q._ac_tags(d, 'python')
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
run init --config dev-loop.config.json >/dev/null 2>&1

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
run init --config dev-loop.config.json >/dev/null 2>&1
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
run init --config dev-loop.config.json >/dev/null 2>&1
run log-step --repo repo-a --tool code-review --iteration 1 --fixed 3 --tests-passed true >/dev/null 2>&1
run regression-check --repo repo-a --diff fix-sin-test.diff --json 2>/dev/null | "$PY" -c "
import json, sys
d = json.load(sys.stdin)
sys.exit(0 if d['fixed'] == 3 and d['verdict'] == 'NARRATED' else 1)" \
  && { PASS=$((PASS+1)); echo "  ok   sin --fixed lee la ultima iteracion del ledger (fixed=3)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL lookup de fixed en el ledger"; }

echo ""
echo "RESULTADO: $PASS ok · $FAIL fail"
cd / && rm -rf "$SB"
[ "$FAIL" -eq 0 ]
