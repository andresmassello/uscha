#!/usr/bin/env bash
# smoke-engine.sh — suite de smoke del motor qa_ledger.py contra un ledger SINTÉTICO.
# Valida el cableado de los fact gates (v1.3.0): log-gate, flag-blocker,
# resolve-escalation, UNMEASURED, convergencia per-tool, gate-check, golden-diff,
# spec-check estructural, simplicity floor, oscillation — el adapter python
# (v1.4.0): coverage Cobertura, junit envuelto, LOC, ruff/mypy, UNMEASURED python —
# el adapter node (v1.5.0): lcov, jest-junit, LOC ts, eslint/tsc, UNMEASURED node —
# y el adapter go (v1.6.0): cover profile, gotestsum, LOC _test.go, golangci.
#
# Uso:   bash tests/smoke-engine.sh        (desde la raíz del kit)
# Exit:  0 = todos los checks verdes · 1 = algún check falló
#
# Nota INV-GOLDEN-01: el path CLEAN de golden-diff NO se auto-testea — crear un
# fixture aprobado es un acto HUMANO incluso en tests. Se cubren NOT-RUN y DIVERGE.

set -u
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
SB="$(mktemp -d 2>/dev/null || echo "${TMP:-/tmp}/smoke-$$")"; mkdir -p "$SB/repo-a" "$SB/repo-b" "$SB/repo-c" "$SB/repo-d" "$SB/repo-e"
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
             {"name":"repo-e","path":"repo-e","type":"go"} ],
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
run flag-blocker --repo repo-a --kind constitution --resolve >/dev/null
chk "blocker resuelto -> CONVERGED" 0 run converged --repo repo-a

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

echo ""
echo "RESULTADO: $PASS ok · $FAIL fail"
cd / && rm -rf "$SB"
[ "$FAIL" -eq 0 ]
