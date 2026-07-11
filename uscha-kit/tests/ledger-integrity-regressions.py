#!/usr/bin/env python3
"""Focused public-CLI regressions for P1 ledger integrity."""

import json
import pathlib
import subprocess
import sys
import tempfile


QL = pathlib.Path(sys.argv[1]).resolve()


def run(root, *args):
    return subprocess.run(
        [sys.executable, str(QL), *args], cwd=root, text=True,
        encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def config(defaults=None, integration=False):
    return {
        "defaults": defaults or {},
        "repos": [{"name": "app", "path": "app", "type": "python"}],
        "integration": {"enabled": integration},
    }


def assert_rejected_before_ledger(root, label, payload):
    cfg = root / (label + ".json")
    ledger = root / (label + ".ledger.json")
    cfg.write_text(payload if isinstance(payload, str) else json.dumps(payload),
                   encoding="utf-8")
    result = run(root, "init", "--config", str(cfg), "--out", str(ledger))
    assert result.returncode != 0, (label, result.stdout, result.stderr)
    assert not ledger.exists(), (label, "invalid config created a ledger")


def assert_init_accepts(root, label, payload):
    cfg = root / (label + ".json")
    ledger = root / (label + ".ledger.json")
    cfg.write_text(json.dumps(payload), encoding="utf-8")
    result = run(root, "init", "--config", str(cfg), "--out", str(ledger))
    assert result.returncode == 0, (label, result.stdout, result.stderr)
    assert ledger.exists(), (label, "valid config did not create a ledger")
    result = run(root, "readiness", "--ledger", str(ledger), "--json")
    assert result.returncode == 0, (label, result.stdout, result.stderr)


def assert_second_resolve_preserves_bytes(root, command, create_args, resolve_args):
    ledger = root / (command + ".ledger.json")
    cfg = root / (command + ".json")
    cfg.write_text(json.dumps(config()), encoding="utf-8")
    assert run(root, "init", "--config", str(cfg), "--out", str(ledger)).returncode == 0
    assert run(root, *create_args, "--ledger", str(ledger)).returncode == 0
    assert run(root, *resolve_args, "--ledger", str(ledger)).returncode == 0
    before = ledger.read_bytes()
    result = run(root, *resolve_args, "--ledger", str(ledger))
    assert result.returncode != 0, (command, result.stdout, result.stderr)
    assert ledger.read_bytes() == before, (command, "second resolve mutated ledger")


with tempfile.TemporaryDirectory(prefix=".uscha-ledger-integrity-", dir=pathlib.Path.cwd()) as tmp:
    root = pathlib.Path(tmp)
    (root / "app").mkdir()

    bad = [
        ("weights-must-map", config({"readiness_weights": []})),
        ("weights-reject-unknown-key", config({"readiness_weights": {"typo": 1}})),
        ("weights-reject-bool", config({"readiness_weights": {"coverage": True}})),
        ("weights-reject-negative", config({"readiness_weights": {"coverage": -1}})),
        ("weights-reject-nan", '{"defaults":{"readiness_weights":{"coverage":NaN}},"repos":[],"integration":{"enabled":false}}'),
        ("caps-must-map", config({"readiness_caps": []})),
        ("caps-reject-unknown-key", config({"readiness_caps": {"typo": 1}})),
        ("caps-reject-out-of-range", config({"readiness_caps": {"tests_red": 101}})),
        ("caps-reject-infinite", '{"defaults":{"readiness_caps":{"tests_red":Infinity}},"repos":[],"integration":{"enabled":false}}'),
        ("static-zero-rejects-zero", config({"static_gate_zero_at": 0})),
        ("static-zero-rejects-bool", config({"static_gate_zero_at": False})),
        ("static-zero-rejects-nan", '{"defaults":{"static_gate_zero_at":NaN},"repos":[],"integration":{"enabled":false}}'),
        ("severity-gate-must-list", config({"severity_gate": "HIGH"})),
        ("severity-gate-rejects-unknown", config({"severity_gate": ["TYPO"]})),
        ("integration-must-map", {"defaults": {}, "repos": [], "integration": []}),
        ("integration-enabled-must-bool", {"defaults": {}, "repos": [], "integration": {"enabled": "yes"}}),
        ("weights-all-zero-integration-disabled", config({"readiness_weights": {k: 0 for k in ("acceptance", "adr", "coverage", "static_gate", "convergence", "integration")}}, False)),
        ("weights-only-integration-enabled", config({"readiness_weights": {"acceptance": 0, "adr": 0, "coverage": 0, "static_gate": 0, "convergence": 0}}, True)),
    ]
    for label, payload in bad:
        assert_rejected_before_ledger(root, label, payload)

    assert_init_accepts(root, "partial-readiness-overrides", config({
        "readiness_weights": {"coverage": 20},
        "readiness_caps": {"tests_red": 50},
        "static_gate_zero_at": 5,
        "severity_gate": ["HIGH", "CRITICAL", "BLOCKER"],
    }))
    print("ledger integrity: readiness config validation")

    assert_second_resolve_preserves_bytes(
        root, "production-finding",
        ("production-finding", "--repo", "app", "--title", "prod defect", "--evidence", "log:1"),
        ("production-finding", "--id", "PF-001", "--resolve", "--note", "triaged"),
    )
    assert_second_resolve_preserves_bytes(
        root, "spec-doubt",
        ("spec-doubt", "--repo", "app", "--note", "contract mismatch"),
        ("spec-doubt", "--id", "SD-001", "--resolve", "--decision", "SPEC amended"),
    )

    ledger = root / "spec-change-request.ledger.json"
    cfg = root / "spec-change-request.json"
    cfg.write_text(json.dumps(config()), encoding="utf-8")
    assert run(root, "init", "--config", str(cfg), "--out", str(ledger)).returncode == 0
    assert run(root, "production-finding", "--ledger", str(ledger), "--repo", "app", "--title", "source", "--evidence", "log:2").returncode == 0
    assert run(root, "spec-change-request", "--ledger", str(ledger), "--repo", "app", "--source", "PF-001", "--requested-change", "amend", "--evidence", "log:3").returncode == 0
    resolve_scr = ("spec-change-request", "--id", "SCR-001", "--resolve", "--decision", "accepted", "--amended", "SPEC.md")
    assert run(root, *resolve_scr, "--ledger", str(ledger)).returncode == 0
    before = ledger.read_bytes()
    result = run(root, *resolve_scr, "--ledger", str(ledger))
    assert result.returncode != 0, (result.stdout, result.stderr)
    assert ledger.read_bytes() == before, "spec-change-request second resolve mutated ledger"
    print("ledger integrity: second resolve preserves bytes for PF/SD/SCR")

    legacy = root / "legacy.ledger.json"
    cfg = root / "legacy.json"
    cfg.write_text(json.dumps(config()), encoding="utf-8")
    assert run(root, "init", "--config", str(cfg), "--out", str(legacy)).returncode == 0
    assert run(root, "production-finding", "--ledger", str(legacy), "--repo", "app", "--title", "legacy", "--evidence", "log:4").returncode == 0
    data = json.loads(legacy.read_text(encoding="utf-8"))
    del data["production_findings"][0]["status"]
    data.pop("integrity", None)  # deliberate legacy fixture mutation: accept it explicitly
    legacy.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    before = legacy.read_bytes()
    result = run(root, "production-finding", "--ledger", str(legacy), "--id", "PF-001", "--resolve", "--note", "triaged")
    assert result.returncode != 0, (result.stdout, result.stderr)
    assert "fail-closed" in (result.stdout + result.stderr), (result.stdout, result.stderr)
    assert legacy.read_bytes() == before, "legacy missing status resolve mutated ledger"
    print("ledger integrity: legacy rows without status fail closed")