#!/usr/bin/env python3
"""Model-checked designs -- THIS repo's thin wrapper over the engine (ADR-059, ADR-061).

Since 2.15.0 the logic lives once, in the engine: `qa_ledger.py model-check`. This wrapper keeps
the 2.13.0 command line and passes the repo's own arrangement (ADR-061 decision 7): the rule
starts at ADR-059, every replayed AC id must appear quoted in the smoke suite, and a run is not
recorded in the repo's ledger -- the CI `models` job is this repo's gate.

  python tools/model-check.py check [--root DIR]
  python tools/model-check.py run --tier ci|deep --jar tla2tools.jar [--root DIR]
"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
ENGINE = os.path.join(os.path.dirname(HERE), "uscha-kit", ".claude", "skills", "uscha-devloop",
                      "qa_ledger.py")
FROM_ADR = "ADR-059"
SUITE = os.path.join("uscha-kit", "tests", "smoke-engine.sh")
# the 2.13.0 rule: a replayed id is a criterion the suite EMITS (res["AC-..."]), not a mention
SUITE_PATTERN = r'res\[\s*["\x27]{id}["\x27]\s*\]'


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    pc = sub.add_parser("check")
    pc.add_argument("--root", default=".")
    pr = sub.add_parser("run")
    pr.add_argument("--root", default=".")
    pr.add_argument("--tier", choices=("ci", "deep"), default="ci")
    pr.add_argument("--jar", default=None)
    pr.add_argument("--java", default="java")
    pr.add_argument("--tlc-cmd", default=None)
    pr.add_argument("--timeout", type=int, default=120)
    pr.add_argument("--limit", type=int, default=60)
    a = p.parse_args(argv)
    cmd = [sys.executable, ENGINE, "model-check", "--root", a.root, "--from-adr", FROM_ADR,
           "--suite", SUITE, "--strict-names", "--suite-pattern", SUITE_PATTERN]
    if a.cmd == "run":
        cmd += ["--run", "--no-record", "--tier", a.tier, "--java", a.java,
                "--timeout", str(a.timeout), "--limit", str(a.limit)]
        if a.jar:
            cmd += ["--jar", a.jar]
        if a.tlc_cmd:
            cmd += ["--tlc-cmd", a.tlc_cmd]
    return subprocess.call(cmd)


if __name__ == "__main__":
    sys.exit(main())
